#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""SYNC-01 P7.1: 敏感日志调用点扫描（Python AST + 文件遍历）。

从 test_outbound_header_log_guard.py 泛化：全表达式树扫描 log 调用参数,
检测 Header 容器名（headers/*_headers）入日志。输出 path:line 格式
（仓库相对路径,便于与 [P1.2 203 候选全集逐项分类表](../../../../../工作记录/20260818-日志机制整改/代码合并规划/验证报告/SYNC-01-P1.2-203候选全集逐项分类表.md) 对照做双向差集）。

口径：调用点级、敏感词于内容、含非常规 logger 变量名、排除测试路径。
Java 守卫口径由 SensitiveLogSentinelTest 覆盖（本脚本仅 Python）。

用法:
  python scan_sensitive_log_callsites.py <root> [--include-tests] [--json]
"""
from __future__ import annotations
import ast
import json
import sys
from pathlib import Path

_LOG_METHODS = {
    "debug", "info", "warning", "warn", "error",
    "exception", "critical", "trace", "log",
}
_SAFE_FUNCS = {"len", "sorted", "any", "all"}
_SAFE_ATTRS = {"keys", "size"}

# P1.2 扩口径:敏感词于内容(日志参数字面量/格式串含敏感词)
_SENSITIVE_WORDS = {
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "auth_token", "access_token", "refresh_token",
    "credential", "private_key", "session_id",
}
# 敏感凭据变量名(精确匹配 Name.id,直传作 log 参数即命中)
_SENSITIVE_VAR_NAMES = {
    "token", "password", "passwd", "secret", "api_key", "apikey",
    "authorization", "auth_token", "access_token", "refresh_token",
    "credential", "credentials", "private_key", "session_id",
}
# NLP/performance token 变量名豁免(明确排除,非漏)— LLM 用量/分词器
_NLP_TOKEN_VARS = {
    "tokens", "token_usage", "total_token", "token_count", "n_tokens",
    "num_tokens", "tokens_used", "total_tokens", "total_token_ms",
    "prompt_tokens", "completion_tokens",
}
# NLP 上下文标志词—字符串字面量含敏感词且同时含这些词时豁免(token=tiktoken/jieba 等)
_NLP_MARKERS = {
    "tokenizer", "tiktoken", "jieba", "token_count", "token_usage",
    "total_token", "num_token", "prompt_token", "completion_token",
    "llm", "model_call", "nlp", "counter", "tokens",
}


def _is_header_name(name: str) -> bool:
    return name == "headers" or name.endswith("_headers")


def _sensitive_words_in_node(node) -> str | None:
    """检测节点树中任意字符串常量(含 f-string JoinedStr / % BinOp / .format() Call
    的格式串)是否含敏感词;NLP 上下文(tokenizer/tiktoken/jieba 等)豁免 token 命中。"""
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            low = n.value.lower()
            has_nlp = any(m in low for m in _NLP_MARKERS)
            for w in _SENSITIVE_WORDS:
                if w in low and not (w == "token" and has_nlp):
                    return w
    return None


def _sensitive_var_in_node(node) -> str | None:
    """检测节点树中是否有敏感凭据变量名/属性直传(精确匹配,排除 NLP token 豁免集)。

    覆盖 ast.Name.id(裸变量 token/password) + ast.Attribute.attr(属性访问
    user.password/self.token/cred.token——adversarial #5 属性访问盲区修复)。
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            lid = n.id.lower()
            if lid in _NLP_TOKEN_VARS:
                continue
            if lid in _SENSITIVE_VAR_NAMES:
                return n.id
        elif isinstance(n, ast.Attribute):
            attr = n.attr.lower()
            if attr in _NLP_TOKEN_VARS:
                continue
            if attr in _SENSITIVE_VAR_NAMES:
                return n.attr
    return None


def _is_header_container(node) -> bool:
    if isinstance(node, ast.Name):
        return _is_header_name(node.id)
    if isinstance(node, ast.Attribute):
        return _is_header_name(node.attr)
    return False


def _safe_container_ids(arg: ast.expr) -> set:
    safe = set()
    for node in ast.walk(arg):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _SAFE_FUNCS:
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
    if isinstance(call.func, ast.Attribute):
        return call.func.attr == "log"
    if isinstance(call.func, ast.Name):
        return call.func.id == "log"
    return False


def _value_args(call: ast.Call) -> list:
    args = list(call.args)
    if _is_log_level_call(call) and args:
        args = args[1:]
    if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
        args = args[1:]
    return args + [kw.value for kw in call.keywords]


def _call_violations(call: ast.Call) -> list:
    found = []
    all_args = list(call.args) + [kw.value for kw in call.keywords]
    # P1.2 扩口径:敏感词于格式串/字面量(覆盖 f-string JoinedStr / .format() / % / 普通 Constant)
    for a in all_args:
        w = _sensitive_words_in_node(a)
        if w:
            found.append((
                getattr(a, "lineno", call.lineno),
                f"<sensitive word: {w}>",
                ast.unparse(a)[:120],
            ))
    # 敏感凭据变量名直传(token/password/...,排除 NLP token_usage 等)
    for a in _value_args(call):
        v = _sensitive_var_in_node(a)
        if v:
            found.append((
                getattr(a, "lineno", call.lineno),
                f"<sensitive var: {v}>",
                ast.unparse(a)[:120],
            ))
    # Header 容器入日志(全表达式树扫描)
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
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [(-1, f"<unparseable: {e}>", "")]
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        is_log_call = (
            (isinstance(node.func, ast.Attribute)
             and node.func.attr in _LOG_METHODS)
            or (isinstance(node.func, ast.Name)
                and node.func.id in _LOG_METHODS)
        )
        if is_log_call:
            violations.extend(_call_violations(node))
    return violations


def _is_test_path(path: Path) -> bool:
    parts = path.parts
    name = path.name.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "conftest" in name
        or any(p.lower() in ("tests", "test", "__tests__") for p in parts)
    )


def scan_file(path: Path) -> list:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    violations = _scan_source(src)
    out = []
    seen = set()
    for lineno, val, ctx in violations:
        key = (path, lineno)
        if key in seen:
            continue
        seen.add(key)
        out.append({"path": str(path), "line": lineno, "value": val, "ctx": ctx})
    return out


def scan_tree(root: Path, include_tests: bool = False) -> list:
    root = root.resolve()
    results = []
    for py in sorted(root.rglob("*.py")):
        if not include_tests and _is_test_path(py):
            continue
        if "__pycache__" in py.parts or ".venv" in py.parts or "site-packages" in py.parts:
            continue
        for r in scan_file(py):
            r["path"] = str(py.relative_to(root))
            results.append(r)
    return results


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    root = Path(args[0]) if args else Path(".")
    include_tests = "--include-tests" in flags
    as_json = "--json" in flags
    results = scan_tree(root, include_tests=include_tests)
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r['path']}:{r['line']}")
    print(f"# total {len(results)} violations (include_tests={include_tests})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
