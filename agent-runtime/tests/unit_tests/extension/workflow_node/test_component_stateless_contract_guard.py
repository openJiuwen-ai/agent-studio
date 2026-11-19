# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""静态图复用契约守卫：ir_converter 分发组件的执行路径禁止落实例状态。

issue #1705 / P2-3：现有 ``test_*_stateless.py`` 逐组件钉住执行期状态隔离，
但新增组件没有强制门禁——P0-1 的 ``FlowCustomApi`` 末帧写实例即由此漏入。
本测试对 ``ir_converter._create_component`` / ``_convert_llm_react_node``
分发到的仓库内组件类（含仓库内基类）做源码级扫描：

- 生命周期/懒初始化/配置解析方法（``__init__`` / ``init`` / ``_init*`` /
  ``_initialize*`` / ``_ensure_*`` / ``ensure_*`` / ``_create_*`` /
  ``_build_*`` / ``_do_initialize*`` / ``_parse_*`` / ``set_*`` /
  ``load_state``）允许写实例（定义级初始化）；
- 其余方法禁止 ``self.xxx = ...``——执行路径上的实例写入按契约必须是
  定义级懒缓存（``llm`` / ``_llm`` / ``_model`` / ``_kb_config`` /
  ``_kb_provider``），或显式登记的历史缓存方法（见 ``_METHOD_EXCEPTIONS``）。

新增组件若在执行入口/辅助方法写 ``self.xxx``，本测试立即转红；确属定义级
缓存时，按白名单逐项登记并说明理由，避免静默复发。
"""
import ast
from pathlib import Path

import pytest

# 仓库内已声明的定义级懒缓存字段：执行路径上的首次构建允许写实例。
_DEFINITION_LEVEL_CACHE_FIELDS = {
    "llm",
    "_llm",
    "_model",
    "_kb_config",
    "_kb_provider",
}

# 历史遗留但确属定义级缓存的方法（issue #1705 扫描确认，非执行期状态）：
# - End._batch_template / _mix_coordinate / _template：模板解析缓存；
# - Extractor.initial_prompt：由定义级 extractor_config 构建 prompt；
# - IntentDetection.get_kg_instance：仅 __init__ 用静态 faq_config 调用。
_METHOD_EXCEPTIONS = {
    ("End", "_batch_template"),
    ("End", "_mix_coordinate"),
    ("End", "_template"),
    ("Extractor", "initial_prompt"),
    ("IntentDetection", "get_kg_instance"),
}

_ALLOWED_METHOD_NAMES = {"__init__", "init", "load_state"}
_ALLOWED_METHOD_PREFIXES = (
    "_init",  # 覆盖 _init_api / _init_from_conf / _init_*
    "initialize",
    "_initialize",
    "_ensure_",
    "ensure_",
    "_create_",
    "_build_",
    "_do_initialize",
    "_parse_",
    "set_",
    "_load_",
)

_IR_MODULE_SUFFIX = "jiuwen/serve/controllers/execution/ir_converter.py"
_DISPATCH_FUNCTIONS = {"_create_component", "_convert_llm_react_node"}


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "jiuwen").is_dir() and (parent / "agent_runtime").is_dir():
            return parent
    raise AssertionError("agent-runtime repo root not found from test path")


def _module_path(root: Path, module: str) -> Path:
    return root / (module.replace(".", "/") + ".py")


def _local_classes(tree: ast.Module) -> dict:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


def _file_imports(tree: ast.Module) -> dict:
    """模块内 import 别名 → (module, 原名)，仅仓库内包。"""
    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module.startswith(("jiuwen.", "agent_runtime.")):
                for alias in node.names:
                    imports[alias.asname or alias.name] = (node.module, alias.name)
    return imports


def _dispatch_class_refs(tree: ast.Module) -> set:
    """分发函数内实例化的类名（局部类名与 import 别名原始名）。"""
    refs = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in _DISPATCH_FUNCTIONS
        ):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    refs.add(sub.func.id)
    return refs


def _resolve_class(
    root: Path,
    module_path: Path,
    class_name: str,
    tree_cache: dict,
    resolved: set,
) -> None:
    """定位类定义并递归收集仓库内基类（外部基类如 WorkflowComponent 跳过）。"""
    key = (module_path, class_name)
    if key in resolved or not module_path.exists():
        return

    tree = tree_cache.get(module_path)
    if tree is None:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        tree_cache[module_path] = tree

    class_node = _local_classes(tree).get(class_name)
    if class_node is None:
        # 分发函数里的普通函数/外部类（如 adapt_* / build_*）不是组件
        return
    resolved.add(key)

    imports = _file_imports(tree)
    local = _local_classes(tree)
    for base in class_node.bases:
        if not isinstance(base, ast.Name):
            continue
        if base.id in local:
            _resolve_class(root, module_path, base.id, tree_cache, resolved)
        elif base.id in imports:
            module, original = imports[base.id]
            _resolve_class(
                root, _module_path(root, module), original, tree_cache, resolved
            )


def _collect_components(root: Path, ir_path: Path) -> list:
    """ir_converter 分发到的仓库内组件类（去重后返回 (path, class_name)）。"""
    ir_tree = ast.parse(ir_path.read_text(encoding="utf-8"))
    imports = _file_imports(ir_tree)
    local = _local_classes(ir_tree)
    tree_cache = {ir_path: ir_tree}
    resolved = set()

    for ref in _dispatch_class_refs(ir_tree):
        if ref in local:
            _resolve_class(root, ir_path, ref, tree_cache, resolved)
        elif ref in imports:
            module, original = imports[ref]
            _resolve_class(
                root, _module_path(root, module), original, tree_cache, resolved
            )

    assert len(resolved) >= 20, f"component registry scan too small: {len(resolved)}"
    return sorted(resolved)


def _is_definition_level_method(name: str) -> bool:
    if name in _ALLOWED_METHOD_NAMES:
        return True
    return any(name.startswith(prefix) for prefix in _ALLOWED_METHOD_PREFIXES)


def _instance_writes(method: ast.AST) -> set:
    writes = set()
    for node in ast.walk(method):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                writes.add(target.attr)
    return writes


def _violations_in_class(class_name: str, class_node: ast.ClassDef) -> list:
    violations = []
    for method in class_node.body:
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _is_definition_level_method(method.name):
            continue
        if (class_name, method.name) in _METHOD_EXCEPTIONS:
            continue
        writes = _instance_writes(method) - _DEFINITION_LEVEL_CACHE_FIELDS
        if writes:
            violations.append(f"{class_name}.{method.name}: {sorted(writes)}")
    return violations


def _scan(root: Path) -> list:
    tree_cache = {}
    violations = []
    for module_path, class_name in _collect_components(root, root / _IR_MODULE_SUFFIX):
        tree = tree_cache.get(module_path)
        if tree is None:
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            tree_cache[module_path] = tree
        class_node = _local_classes(tree).get(class_name)
        if class_node is None:
            continue
        violations.extend(_violations_in_class(class_name, class_node))
    return sorted(violations)


def test_dispatched_components_have_no_execution_state_writes():
    """ir_converter 分发的所有组件：执行路径不得写共享实例字段。"""
    root = _repo_root()
    violations = _scan(root)
    assert not violations, (
        "执行路径写入共享实例字段（静态图复用下会跨执行串扰）。"
        "若确为定义级缓存，请在 _DEFINITION_LEVEL_CACHE_FIELDS/_METHOD_EXCEPTIONS "
        "登记并说明理由：\n" + "\n".join(violations)
    )


def test_guard_scanner_detects_execution_state_write():
    """判别用例：扫描器必须能抓到「stream 内写实例末帧」这一原始缺陷形态。"""
    source = (
        "class FakeStreamComponent:\n"
        "    def stream(self, inputs):\n"
        "        self._final_stream_output = {'a': 1}\n"
    )
    class_node = ast.parse(source).body[0]
    violations = _violations_in_class("FakeStreamComponent", class_node)
    assert violations == [
        "FakeStreamComponent.stream: ['_final_stream_output']"
    ]


def test_guard_scanner_ignores_definition_level_lazy_fields():
    """判别用例：定义级懒缓存字段与生命周期方法不误报。"""
    source = (
        "class FakeComponent:\n"
        "    def __init__(self):\n"
        "        self._conf = {}\n"
        "    def _ensure_llm(self):\n"
        "        self.llm = object()\n"
        "    def invoke(self, inputs):\n"
        "        self.llm = self._build()\n"
    )
    class_node = ast.parse(source).body[0]
    assert _violations_in_class("FakeComponent", class_node) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
