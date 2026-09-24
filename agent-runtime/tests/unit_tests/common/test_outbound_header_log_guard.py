#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""SYNC-01 P1.3: 出站完整 Header 容器不入日志的静态防回归（AST 反转设计版）。

修正历程（p1 实审 → 三轮实审复核 → 7d3750bb 复核）：
1. 正则逐轮追漏（rstrip→%s→多行→参数级→值级）——表达式语法开放集合，
   正则枚举不完；
2. `82598163` 改 ast.parse 枚举节点类型——仍逐类追（嵌套字面量只递归一层、
   BoolOp/IfExp/Starred/`.log`/下标未覆盖），且 docstring 声明超过实现
   （"字面量递归"实为一层，7d3750bb 复核 §2.1 实证矛盾）；
3. 本版按用户决策 2026-09-19"反转设计全修"：**不再枚举节点类型**——
   对 log 调用的每个参数值做**全表达式树扫描**，任何位置出现的 Header
   容器名（Name/Attribute 末段 headers/_headers）都判敏感，只豁免被
   **安全上下文消费**的容器节点。

安全上下文（白名单，豁免且仅豁免其自身）：
- 作为 `len`/`sorted`/`any`/`all` 的直接参数（含关键字参数）
- 作为 `.keys`/`.size` 属性访问的接收者（`headers.keys`、`rp.headers.size`）

调用形态：属性调用（logger.debug）与直接导入（from logging import
 debug; debug(...)）两种。由此一次覆盖：嵌套容器（任意深度）、f-string（含 !r/!s/format spec）、
参数化/无格式串/冗余括号、`%` 预格式化、`.format` 位置+命名、布尔/条件
表达式、星号解包、下标访问（`headers["X-Auth-Token"]`）、推导式、walrus、
str()/copy() 等容器名出现在其中的任意调用——以及标准 `logger.log`/
`logging.log`（level 位次跳过）。

守卫边界（声明，留人工复扫 + P5 真实日志哨兵 + P7 最终树补扫）：
- 不含容器名的函数返回值（如 `inject_customer_headers(cfg)`——参数树里
  没有容器名，返回值是否含 Header 不可静态判定）
- 别名/数据流（`msg = f"...{headers}"; logger.debug(msg)`）
- **导入重命名**（`from logging import warning as w; w(headers)`——
  重命名后的调用名不在 _LOG_METHODS，跨模块别名追踪超出本守卫；
  66300b57 复核 §2.2 明示不要求，自审实证漏判后声明）
- 运行时动态构造的容器名
误杀倾向：本守卫偏保守（含容器名即拒，`[k for k in headers]` 键迭代也会
拒）——安全门宁可误拒，由人工改写或加白名单上下文。
**直接名称调用不追溯来源**（98b7cf9e 复核 §2 声明）：按调用名识别
`debug/info/...`，普通同名函数（`def debug(v)...` 或
`from unrelated import error`）传入 Header 也会被拒——保守取舍可接受；
同名调用 + 白名单安全值（`len` 等）不误拒。
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

_AGENT_RUNTIME_ROOT = Path(__file__).resolve().parents[3]

_LOG_METHODS = {
    "debug", "info", "warning", "warn", "error",
    "exception", "critical", "trace", "log",
}
# 安全上下文：容器名被以下消费时不判敏感（只豁免容器节点自身）
_SAFE_FUNCS = {"len", "sorted", "any", "all"}
_SAFE_ATTRS = {"keys", "size"}


def _is_header_name(name: str) -> bool:
    """名字末段为 headers 或 *_headers（custom_headers/headers/api_headers）。"""
    return name == "headers" or name.endswith("_headers")


def _is_header_container(node) -> bool:
    """表达式节点是否为完整 Header 容器名（Name 或点链 Attribute）。"""
    if isinstance(node, ast.Name):
        return _is_header_name(node.id)
    if isinstance(node, ast.Attribute):
        return _is_header_name(node.attr)
    return False


def _safe_container_ids(arg: ast.expr) -> set:
    """标记参数树中被安全上下文消费的容器节点 id 集合。"""
    safe = set()
    for node in ast.walk(arg):
        if isinstance(node, ast.Call):
            func = node.func
            is_safe_func = isinstance(func, ast.Name) and func.id in _SAFE_FUNCS
            if is_safe_func:
                for a in node.args:
                    if _is_header_container(a):
                        safe.add(id(a))
                for kw in node.keywords:
                    if _is_header_container(kw.value):
                        safe.add(id(kw.value))
        elif isinstance(node, ast.Attribute) and node.attr in _SAFE_ATTRS:
            if _is_header_container(node.value):
                safe.add(id(node.value))
    return safe


def _is_log_level_call(call: ast.Call) -> bool:
    """是否 log(level, ...) 形态（属性或直接导入两种调用形态）。"""
    if isinstance(call.func, ast.Attribute):
        return call.func.attr == "log"
    if isinstance(call.func, ast.Name):
        return call.func.id == "log"
    return False


def _value_args(call: ast.Call) -> list:
    """log 调用中作为值传入的参数表达式（跳过 level 与格式串）。"""
    args = list(call.args)
    # logger.log(level, msg, *args)：首参恒为 level，无条件跳过
    if _is_log_level_call(call) and args:
        args = args[1:]
    # 首参为字符串常量（格式串）时跳过；f-string/其他表达式本身即消息值
    if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
        args = args[1:]
    return args + [kw.value for kw in call.keywords]


def _call_violations(call: ast.Call) -> list:
    """一条 log 调用中，参数值表达式树内非安全消费的 Header 容器违规。

    函数名不是值：Call.func 节点本身跳过（如 `inject_customer_headers(cfg)`
    的函数名以 _headers 结尾不算容器），但其子表达式仍扫——`headers.get("x")`
    的接收者 Name(headers) 依旧会被抓。
    """
    found = []
    for a in _value_args(call):
        safe = _safe_container_ids(a)
        func_ids = {id(n.func) for n in ast.walk(a) if isinstance(n, ast.Call)}
        for node in ast.walk(a):
            if (_is_header_container(node)
                    and id(node) not in safe
                    and id(node) not in func_ids):
                found.append((
                    getattr(node, "lineno", call.lineno),
                    ast.unparse(node),
                    ast.unparse(a)[:120],
                ))
    return found


def _scan_source(src: str) -> list:
    """完整扫描入口：ast.parse → 定位 log 调用 → 参数值全树扫描。"""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:  # 守卫文件本身不可解析时显式失败，不静默跳过
        return [(-1, f"<unparseable source: {e}>", "")]
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # 两种调用形态：属性调用 logger.debug(...) 与直接导入 from logging
        # import debug; debug(...)（66300b57 复核 §2.2 覆盖）
        is_log_call = (
            (isinstance(node.func, ast.Attribute)
             and node.func.attr in _LOG_METHODS)
            or (isinstance(node.func, ast.Name)
                and node.func.id in _LOG_METHODS)
        )
        if is_log_call:
            violations.extend(_call_violations(node))
    return violations


def _assert_no_full_header_logging(rel_path: str) -> None:
    src = (_AGENT_RUNTIME_ROOT / rel_path).read_text(encoding="utf-8")
    violations = _scan_source(src)
    if violations:
        lineno, val, ctx = violations[0]
        raise AssertionError(
            f"{rel_path}:{lineno} 日志参数表达式含整个 Header 容器 `{val}`"
            f"（上下文：{ctx}）\n"
            f"完整 Header（含认证/凭据）不得进入日志；"
            f"如需诊断只允许 len/keys/键名。共 {len(violations)} 处。"
        )


class OutboundHeaderFileGuard(unittest.TestCase):
    """五个受保护生产文件当前无 Header 容器入日志。"""

    def test_model_providers_no_full_header_logging(self):
        _assert_no_full_header_logging("agent_runtime/common/model_providers.py")

    def test_sse_client_new_no_full_header_logging(self):
        _assert_no_full_header_logging("jiuwen/extension/wrapper/sse_client_new.py")

    def test_streamable_http_client_new_no_full_header_logging(self):
        _assert_no_full_header_logging("jiuwen/extension/wrapper/streamable_http_client_new.py")

    def test_mcpapi_no_full_header_logging(self):
        _assert_no_full_header_logging("jiuwen/plugin/models/mcpapi.py")

    def test_request_params_no_full_header_logging(self):
        _assert_no_full_header_logging("jiuwen/plugin/models/request_params.py")


# --- 坏例注入（走 _scan_source 完整入口；覆盖历轮复核点名 + 反转设计新增） ---


class HeaderLogGuardFaultInjection(unittest.TestCase):
    """验证坏代码经完整扫描入口被拒绝、好代码不被误杀。"""

    def _rejected(self, src: str) -> None:
        v = _scan_source(src)
        self.assertTrue(v, f"应拒绝（实未拒）：{src!r}")

    def _passed(self, src: str) -> None:
        v = _scan_source(src)
        self.assertFalse(v, f"应通过（实拒绝 {v}）：{src!r}")

    # --- 历轮点名路径（82598163 前的五族 + d24ecd27 复核五反例） ---

    def test_bad_fstring_rejected(self):
        """坏例：f-string（普通/原始样本/conversion/跨行）。"""
        self._rejected('logger.debug(f"headers: {custom_headers}")\n')
        self._rejected(
            'workflow_logger.debug(f"LLM custom_headers: {custom_headers}")\n')
        self._rejected('logger.debug(f"headers={custom_headers!r}")\n')
        self._rejected('logger.debug(f"{headers!s:>10}")\n')
        self._rejected('logger.debug(\n    f"headers: {headers}",\n)\n')

    def test_bad_parameterized_rejected(self):
        """坏例：参数化（双/单引号/冗余括号/跨行/属性链）。"""
        self._rejected('logger.debug("headers: %s", headers)\n')
        self._rejected("logger.debug('headers: %s', headers)\n")
        self._rejected('logger.debug("headers: %s", (custom_headers))\n')
        self._rejected('logger.debug(\n    "headers: %s",\n    headers,\n)\n')
        self._rejected('logger.debug("h: %s", request_params.headers)\n')
        self._rejected('logger.debug("auth: %s", self._auth_headers)\n')

    def test_bad_no_format_string_rejected(self):
        """坏例：无格式串直接消息。"""
        self._rejected('logger.debug(headers)\n')

    def test_bad_percent_preformat_rejected(self):
        """坏例：% 预格式化（单值/tuple）。"""
        self._rejected('logger.debug("headers=%s" % custom_headers)\n')
        self._rejected(
            'logger.debug("a=%s b=%s" % (status, custom_headers))\n')

    def test_bad_format_call_rejected(self):
        """坏例：.format 位置与命名参数。"""
        self._rejected('logger.debug("h: {}".format(headers))\n')
        self._rejected('logger.debug("h={h}".format(h=custom_headers))\n')

    def test_bad_mixed_safe_and_sensitive_rejected(self):
        """坏例：同句安全值不豁免裸容器。"""
        self._rejected(
            'logger.debug("h: %s, size=%s", headers, len(headers))\n')
        self._rejected(
            'logger.debug(f"h: {headers}, k: {sorted(headers.keys())}")\n')

    # --- 7d3750bb 复核点名（嵌套字面量 / .log / BoolOp / IfExp） ---

    def test_bad_nested_container_rejected(self):
        """坏例（7d3750bb 复核 §2.1）：嵌套容器字面量任意深度。"""
        self._rejected('logger.debug({"payload": [custom_headers]})\n')
        self._rejected('logger.debug([[custom_headers]])\n')
        self._rejected(
            'logger.debug("headers=%s", {"payload": [custom_headers]})\n')
        self._rejected('logger.debug([{"a": (headers,)}])\n')

    def test_bad_log_api_rejected(self):
        """坏例（7d3750bb 复核 §2.2）：标准 logger.log/logging.log（level 位次）。"""
        self._rejected('logger.log(10, "headers=%s", custom_headers)\n')
        self._rejected('logging.log(10, custom_headers)\n')
        self._rejected('logger.log(logging.DEBUG, f"h: {headers}")\n')

    def test_bad_bool_ifexp_rejected(self):
        """坏例（7d3750bb 复核 §2.3）：布尔/条件表达式。"""
        self._rejected('logger.debug("h %s", headers or {})\n')
        self._rejected('logger.debug("h %s", headers if flag else None)\n')

    # --- 反转设计新增覆盖（此前未声明未测试的标准静态写法） ---

    def test_bad_subscript_rejected(self):
        """坏例：下标取单个 Header 值。"""
        self._rejected('logger.debug("tok %s", headers["X-Auth-Token"])\n')

    def test_bad_starred_rejected(self):
        """坏例：星号解包（反转设计下不再豁免）。"""
        self._rejected('logger.debug("h", *custom_headers)\n')

    def test_bad_wrapped_call_rejected(self):
        """坏例：容器名出现在 str()/copy() 等非安全调用里。"""
        self._rejected('logger.debug("h: " + str(headers))\n')
        self._rejected('logger.debug("h %s", headers.copy())\n')

    def test_bad_comprehension_rejected(self):
        """坏例：推导式含容器（保守拒绝，宁可误拒）。"""
        self._rejected('logger.debug("hs %s", [h for h in headers])\n')

    def test_bad_direct_import_rejected(self):
        """坏例（66300b57 复核 §2.2）：直接导入的日志函数调用形态。"""
        self._rejected("from logging import debug\ndebug(headers)\n")
        self._rejected('from logging import info\ninfo("h %s", headers)\n')
        self._rejected("from logger import error\nerror(headers)\n")

    def test_conservative_name_call_boundary(self):  # pylint: disable=function-docstring-indents-four
        """边界（98b7cf9e 复核 §2）：直接名称调用不追溯来源——普通同名函数
        传 Header 保守误拒（有意行为，非 bug）；白名单安全值不误拒。"""
        # 保守误拒（有意）：普通同名函数/非日志来源传裸容器
        self._rejected("def debug(value):\n    return value\ndebug(headers)\n")
        self._rejected("from unrelated import error\nerror(headers)\n")
        # 同名调用 + 白名单安全值：不误拒
        self._passed("def debug(value):\n    return value\ndebug(len(headers))\n")

    # --- 好例：安全上下文不被误杀 ---

    def test_good_safe_context_not_rejected(self):
        """好例：len/sorted/keys/size 及纯文本/异常对象。"""
        self._passed('logger.debug(f"count: {len(headers)}")\n')
        self._passed('logger.debug("count: %s", len(headers))\n')
        self._passed('logger.debug(f"keys: {sorted(headers.keys())}")\n')
        self._passed('logger.debug("keys: %s", headers.keys())\n')
        self._passed('logger.debug("n %s", request_params.headers.size())\n')
        self._passed('logger.debug("start request")\n')
        self._passed('logger.debug("header missing: {0}", "X-Auth-Token")\n')
        self._passed('logger.debug("failed", e)\n')
        self._passed('logger.debug(f"count: {len(custom_headers)}")\n')


if __name__ == "__main__":
    unittest.main()
