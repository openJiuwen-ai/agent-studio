#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""SYNC-01 P7.1: Java 敏感值日志直出全树补扫（正则 + 多行合并）。

从 test_sensitive_java_log_guard.py 泛化：9 文件守卫 → 全 backend 树扫描。
口径=值直出（headers/requestBody/errorBody 容器 + response.getBody()），
与守卫一致（非 P1.2 grep 的路径名/键名提及口径）。
输出 path:line 格式，便于与 P1.2 归档 203 Java 子集双向差集。

用法:
  python scan_sensitive_java_log_callsites.py <root> [--include-tests] [--json]
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

_SENSITIVE_VARS = ("headers", "requestBody", "errorBody")
# 泛化：任意 ResponseEntity 变量 .getBody()（不限于 response/responseEntity，
# 覆盖 resp/entity/result/res/rs 等别名——adversarial P7.4c 发现的盲区）
_SENSITIVE_EXPRS = (r"\b\w+\s*\.getBody\(\)",)
_SAFE_SUFFIXES = (".size()", ".keySet()", ".length()")
_LOG_CALL = re.compile(r"\.(debug|info|warn|warning|error|trace)\s*\(")


def _clean_arg(a: str) -> str:
    a = a.strip().rstrip(";").strip()
    while a.endswith(")") and a.count(")") > a.count("("):
        a = a[:-1].strip()
    return a


def _split_args(s: str) -> list:
    args, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def _is_sensitive_arg(arg: str) -> bool:
    a = _clean_arg(arg)
    if not a or a.endswith(_SAFE_SUFFIXES):
        return False
    if a in _SENSITIVE_VARS:
        return True
    for pat in _SENSITIVE_EXPRS:
        if re.search(pat, a):
            return True
    return False


def _extract_args(line: str) -> list:
    m = _LOG_CALL.search(line)
    if not m:
        return []
    rest = line[m.end():].rstrip(";").strip()
    q = re.search(r'"[^"]*"\s*,?\s*(.*)', rest)
    if not q:
        return _split_args(rest) if rest else []
    argstr = q.group(1).rstrip(";").strip()
    if not argstr:
        return []
    return _split_args(argstr)


def _depth_outside_strings(s: str, in_str: bool = False) -> tuple[int, bool]:
    """扫描 s,返回双引号字符串字面量**外**的括号深度 + 末尾是否仍在字符串内。

    排除字符串字面量内的括号(审视 §1.2:格式串含 ( 不得合并独立调用)。
    转义 \\\" 不闭合字符串。字符字面量 '...' 与 /* */ 跨行块注释内括号不覆盖(adversarial ADV-R2-01 已知局限:
    闭合行 /* ( */ 破坏合并;当前 9 callsite 全树无触发,future code 触发时需扩展块注释状态机)。
    // 行注释已处理(break)。
    """
    depth = 0
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if in_str:
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '/' and i + 1 < n and s[i + 1] == '/':
            break  # 行注释,剩余跳过(adversarial ADV-R2-01)
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        i += 1
    return depth, in_str


def _merge_continuation_lines(src: str) -> list:
    """合并多行 log 调用,返回 [(start_lineno, merged_line), ...]。

    start_lineno 为该块首行真实源码行号(非合并后列表序号),
    保证 path:line 与源码稳定对应(审视 §1.2 行号漂移修复)。
    闭合判定:字符串字面量**外**括号深度回 0 且以 ; 结尾
    (ADV-01 括号深度 + 审视 §1.2 引号状态:字符串内括号不计,独立调用不合并)。
    """
    merged = []
    buf = ""
    buf_start = 0
    depth = 0
    in_str = False
    for lineno, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if buf:
            buf += " " + stripped
            d, in_str = _depth_outside_strings(stripped, in_str)
            depth += d
            if depth <= 0 and re.sub(r'//.*$', '', stripped).rstrip().endswith(";") and not in_str:
                merged.append((buf_start, buf))
                buf = ""
                depth = 0
                in_str = False
            elif len(buf) > 2000:
                merged.append((buf_start, buf))
                buf = ""
                depth = 0
                in_str = False
        elif _LOG_CALL.search(line) and not re.sub(r'//.*$', '', line).rstrip().endswith(";"):
            buf = line.rstrip()
            buf_start = lineno
            depth, in_str = _depth_outside_strings(stripped)
        else:
            merged.append((lineno, line))
    if buf:
        merged.append((buf_start, buf))
    return merged


def _is_test_path(path: Path) -> bool:
    parts = path.parts
    return any(p.lower() in ("test", "tests", "__tests__") for p in parts) \
        or "/test/" in str(path).replace("\\", "/")


def scan_file(path: Path) -> list:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    merged = _merge_continuation_lines(src)
    out = []
    for start_lineno, line in merged:
        if not _LOG_CALL.search(line):
            continue
        for arg in _extract_args(line):
            if _is_sensitive_arg(arg):
                out.append({
                    "path": str(path), "line": start_lineno,
                    "value": _clean_arg(arg), "ctx": line.strip()[:120],
                })
                break
    return out


def scan_tree(root: Path, include_tests: bool = False) -> list:
    root = root.resolve()
    results = []
    for java in sorted(root.rglob("*.java")):
        if not include_tests and _is_test_path(java):
            continue
        if "target" in java.parts:
            continue
        for r in scan_file(java):
            r["path"] = str(java.relative_to(root))
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
