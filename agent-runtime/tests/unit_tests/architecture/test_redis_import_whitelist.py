# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""CI 白名单（设计文档 §六 最终目标 / §九 交付物 8）：redis-py 直接 import 收口。

规则：runtime 进程树（agent_runtime/ + jiuwen/）与 packages/ 内，除 redis_native
（唯一允许 import redis 的实现包）与下方白名单外，任何文件不得直接
``import redis`` / ``from redis import ...``——业务代码一律走 redis_spi
（接口/异常/类型），native 视图注入只允许出现在 Q3 兼容层。

白名单只减不增：每条注明豁免原因与下线计划；对应文件迁移完成后必须删条目
（test_whitelist_entries_all_exist_and_still_import_redis 会强制这一纪律）。
"""

import re
from pathlib import Path

_RUNTIME_ROOT = Path(__file__).resolve().parents[3]  # agent-runtime/
_REPO_ROOT = _RUNTIME_ROOT.parent  # agent-studio/

_SCAN_DIRS = [
    _RUNTIME_ROOT / "agent_runtime",
    _RUNTIME_ROOT / "jiuwen",
    _REPO_ROOT / "packages",
]

#: 白名单：仓库相对路径（/ 分隔，基数为 agent-studio/）→ 豁免原因与下线计划。
WHITELIST = {
    # —— Q3 兼容注入层（agent-core 零改动的前提：向其注入 native 视图）——
    "agent-runtime/agent_runtime/memory/adapter/redis_kv_store.py": (
        "Q3 兼容注入：agent-core BaseKVStore 适配 native 视图"
    ),
    "agent-runtime/agent_runtime/memory/adapter/ltm_manager.py": (
        "Q3 类型注解：native 视图注入 LTM"
    ),
    "agent-runtime/agent_runtime/runner/fast_redis_checkpointer.py": (
        "Q3 兼容注入 + §十一 scan_iter bypass 风险（先补特性测试再动）"
    ),
    # —— 过渡层本体（builder 进程仍走 legacy init，Q2/Q10 本期不纳入）——
    "packages/common_utils/common_utils/redis_manager.py": (
        "过渡层：builder 进程 legacy init 依赖（Q2），业务全量迁移后瘦身"
    ),
    # —— 测试工具链（非业务代码）——
    "packages/redis_contract_tests/redis_contract_tests/stubs/redis_py_stub.py": (
        "契约套件委托层替身：模拟 redis-py 客户端并抛原生异常（被测翻译链路）"
    ),
    "packages/redis_demo_provider/redis_demo_provider/errors.py": (
        "demo 异常翻译层：fakeredis（redis-py 兼容）抛原生异常须在边界捕获"
    ),
}

#: redis_native 整包豁免（前缀匹配，仓库相对路径）。
_NATIVE_PREFIX = "packages/redis_native"

#: builder 进程树（junction 挂载）：Q10 本期不纳入迁移范围，不扫描。
_BUILDER_DIRNAME = "agent_builder"

_REDIS_IMPORT = re.compile(
    r"^\s*(?:import redis(?:\.|\s|$)|from redis(?:\.|\s))", re.MULTILINE
)


def _relative(path: Path) -> str:
    return path.resolve().relative_to(_REPO_ROOT).as_posix()


def _iter_python_files():
    for scan_dir in _SCAN_DIRS:
        if not scan_dir.is_dir():
            continue
        for path in sorted(scan_dir.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if _BUILDER_DIRNAME in path.parts:
                continue  # builder 树（junction）：Q10 范围外
            yield path


def test_no_direct_redis_imports_outside_whitelist():
    offenders = []
    for path in _iter_python_files():
        rel = _relative(path)
        if rel.startswith(_NATIVE_PREFIX):
            continue  # redis_native 整包豁免
        if rel in WHITELIST:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _REDIS_IMPORT.search(text):
            offenders.append(rel)
    assert not offenders, (
        "以下文件直接 import redis-py（业务代码应改走 redis_spi；确需 native "
        "视图请走 Q3 兼容层并在 WHITELIST 登记原因与下线计划）：\n  "
        + "\n  ".join(offenders)
    )


def test_whitelist_entries_exist_and_still_import_redis():
    """白名单健康度：条目须存在且仍直接 import redis——迁移完成后删条目（只减不增）。"""
    for rel in WHITELIST:
        path = _REPO_ROOT / rel
        assert path.is_file(), (
            f"白名单条目不存在：{rel}（文件已删除/改名，请同步清理白名单）"
        )
        text = path.read_text(encoding="utf-8")
        assert _REDIS_IMPORT.search(text), (
            f"白名单条目 {rel} 已不再直接 import redis——迁移已完成，"
            f"请从 WHITELIST 删除该条目（白名单只减不增）"
        )
