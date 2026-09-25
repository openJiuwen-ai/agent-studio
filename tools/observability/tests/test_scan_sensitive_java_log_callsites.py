#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""SYNC-01 P7.1: Java 敏感日志扫描器直接单测(审视 §1.2 要求)。

断言声称的不变量:命中/不命中集合(状态),非调用次数。
失效注入:删规则(注入点),不 mock 被验证的扫描器函数本身。
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import pytest
import scan_sensitive_java_log_callsites as mod
from scan_sensitive_java_log_callsites import (
    _is_sensitive_arg, _merge_continuation_lines, scan_file,
)


# ---- 正例:声称命中的值直出路径(含别名泛化) ----

@pytest.mark.parametrize("arg", [
    "headers",
    "requestBody",
    "errorBody",
    "response.getBody()",          # 原 response 别名
    "resp.getBody()",              # resp 别名(adversarial 发现)
    "responseJson.getBody()",      # responseJson 别名
    "entity.getBody()",            # entity 别名
    "response.getBody())",         # 多余闭括号(clean_arg 处理)
])
def test_sensitive_arg_must_hit(arg):
    assert _is_sensitive_arg(arg), f"应命中: {arg}"


# ---- 反例:安全访问器不命中 ----

@pytest.mark.parametrize("arg", [
    "headers.size()",
    "headers.keySet()",
    "requestBody.length()",
    "response.getBody().size()",      # .size() 后缀保护(假阳口径:.getMessage() 是保守命中非反例)
    "e",                                    # 异常对象
    "statusCode",
    "response.getStatusCode()",
])
def test_safe_arg_must_not_hit(arg):
    assert not _is_sensitive_arg(arg), f"不应命中: {arg}"


# ---- 失效注入:删规则后正例必须 FAIL ----

def test_fault_injection_remove_sensitive_exprs():
    """删 _SENSITIVE_EXPRS → resp.getBody() 不再命中(证明泛化规则生效)。"""
    saved = list(mod._SENSITIVE_EXPRS)
    mod._SENSITIVE_EXPRS = ()
    try:
        assert not _is_sensitive_arg("resp.getBody()"), "删规则后不应命中"
        assert _is_sensitive_arg("headers"), "headers 仍应命中(变量名规则独立)"
    finally:
        mod._SENSITIVE_EXPRS = tuple(saved)


def test_fault_injection_remove_safe_suffix():
    """删 _SAFE_SUFFIXES → response.getBody().size() 从安全变命中(证明 .size() 豁免生效)。"""
    saved = list(mod._SAFE_SUFFIXES)
    mod._SAFE_SUFFIXES = ()
    try:
        # 删安全后缀后 response.getBody().size() 命中(因 regex 匹配 response.getBody() 且无 size 保护)
        assert _is_sensitive_arg("response.getBody().size()"), "删 SAFE_SUFFIXES 后应命中"
    finally:
        mod._SAFE_SUFFIXES = tuple(saved)


# ---- 不变量:行号映射保留源码真实起始行(审视 §1.2 行号漂移修复) ----

def test_claim_invariant_lineno_preserved_multiline():
    """声称不变量: 多行 log 调用合并后输出首行真实源码行号,非合并后列表序号。
    实际断言: 合并块 start_lineno == 首行真实行号(状态值,非序号)。"""
    src = "    log.error(\"msg: {}\",\n        response.getBody());\n"
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert log_blocks, "应有 log 调用块"
    start_ln, _ = log_blocks[0]
    # src 第 1 行(log.error 开头)即真实起始行
    assert start_ln == 1, f"多行块应保留首行真实行号 1,实际 {start_ln}"


def test_claim_invariant_lineno_preserved_single_line():
    """声称不变量: 单行 log 调用行号 == 源码真实行号。"""
    src = "\n\n    log.error(\"msg: {}\", headers);\n"
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert log_blocks
    start_ln, _ = log_blocks[0]
    assert start_ln == 3, f"单行块应在第 3 行,实际 {start_ln}"


def test_adv01_intermediate_paren_no_premature_close():
    """ADV-01 修复:中间行以 ) 结尾(无 ;)不提前关闭 buf,
    后续行的 response.getBody() 必被扫描到(声称不变量:检测所有 getBody() 参数)。"""
    src = '    log.error("msg: {}",\n        foo.getBar()\n        + response.getBody());\n'
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert len(log_blocks) == 1, f"应合并为 1 块,实际 {len(log_blocks)}: {log_blocks}"
    _, merged_line = log_blocks[0]
    assert "response.getBody()" in merged_line, f"合并后应含 response.getBody(): {merged_line}"
    import scan_sensitive_java_log_callsites as m
    args = m._extract_args(merged_line)
    assert any(m._is_sensitive_arg(a) for a in args), \
        f"应检出敏感参数, args={args}"


def test_review_s12_two_calls_with_paren_in_string_not_merged():
    """审视 §1.2:格式串含左括号 ( 时,两个独立 log 调用不得合并,
    两调用点分别保留真实行号(声称不变量:稳定 path:line + 不丢调用点)。"""
    src = 'log.info("begin ( {}",\n    headers);\nlog.info("body {}", response.getBody());\n'
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert len(log_blocks) == 2, f"应 2 块(独立调用),实际 {len(log_blocks)}: {log_blocks}"
    # 第一调用点行号=1(headers)
    assert log_blocks[0][0] == 1, f"第一调用应在行1,实际 {log_blocks[0][0]}"
    # 第二调用点行号=3(response.getBody())
    assert log_blocks[1][0] == 3, f"第二调用应在行3,实际 {log_blocks[1][0]}"
    # 两调用点各自命中敏感参数
    import scan_sensitive_java_log_callsites as m
    hits = []
    for ln, line in log_blocks:
        for arg in m._extract_args(line):
            if m._is_sensitive_arg(arg):
                hits.append((ln, arg))
                break
    assert len(hits) == 2, f"应 2 命中,实际 {hits}"
    assert hits[0] == (1, "headers)"), f"第一命中应 (1,headers),实际 {hits[0]}"
    assert "response.getBody()" in hits[1][1], f"第二命中应含 response.getBody(),实际 {hits}"


def test_review_s12_string_with_unbalanced_close_paren():
    """审视 §1.2:格式串含右括号 ) 时,不得提前闭合(字符串内括号不计 depth)。"""
    src = 'log.info("end ) {}",\n    response.getBody());\n'
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert len(log_blocks) == 1, f"应 1 块(多行单调用),实际 {len(log_blocks)}"
    assert log_blocks[0][0] == 1
    import scan_sensitive_java_log_callsites as m
    args = m._extract_args(log_blocks[0][1])
    assert any(m._is_sensitive_arg(a) for a in args), f"应检出 response.getBody(): {args}"


def _LOG_CALL_search(line):
    import re
    return mod._LOG_CALL.search(line)


# ---- 格式串含不平衡括号(adversarial #1: depth-corruption 级联回归) ----

def test_adv02_format_string_unbalanced_paren_no_cascade():
    """ADV-02:格式串字面量含 ( 无匹配 ) 不得腐蚀 depth tracking 致后续 log 调用粘连。

    声称不变量: 两相邻 log 调用,前一个格式串含 ( (在字符串内),扫描器输出 2 个独立块,
    第二块 start_lineno 为真实源码行且其敏感参数(response.getBody())被检出。
    失效注入点: _depth_outside_strings 引号状态机(不 mock _merge_continuation_lines 本身)。
    """
    src = 'log.error("failed (see log",\n    statusCode);\nlog.info("done", response.getBody());\n'
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert len(log_blocks) == 2, f"应 2 独立块,实际 {len(log_blocks)}: {log_blocks}"
    # 第一块 start=1,第二块 start=3(真实源码行)
    assert log_blocks[0][0] == 1, f"第一块 start 应 1,实际 {log_blocks[0][0]}"
    assert log_blocks[1][0] == 3, f"第二块 start 应 3(真实行),实际 {log_blocks[1][0]}"
    # 第二块检出 response.getBody()
    _, second_line = log_blocks[1]
    args = mod._extract_args(second_line)
    assert any(_is_sensitive_arg(a) for a in args),         f"第二块应检出 response.getBody(), args={args}"


def test_adv02_format_string_balanced_paren_control():
    """对照组:格式串括号平衡时同样 2 块(确保 ADV-02 不是偶然)。"""
    src = 'log.error("failed (see log)",\n    statusCode);\nlog.info("done", response.getBody());\n'
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert len(log_blocks) == 2, f"对照组也应 2 块,实际 {len(log_blocks)}"
    assert log_blocks[1][0] == 3, f"第二块 start 应 3,实际 {log_blocks[1][0]}"


# ---- ADV-R2-01: 闭合行 // 行注释不腐蚀合并(adversarial 第二轮) ----

def test_adv03_closing_line_line_comment_no_cascade():
    """ADV-03:闭合行含 // "see log" 行注释不得破坏合并。

    声称不变量: log.error(... headers); // "see log 后跟独立 log.info(..., response.getBody())
    → 2 独立块,第二块 start=3 真实行 + response.getBody() 检出。
    """
    src = 'log.error("msg {}",\n    headers); // "see log\nlog.info("done", response.getBody());\n'
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    assert len(log_blocks) == 2, f"应 2 块,实际 {len(log_blocks)}: {log_blocks}"
    assert log_blocks[1][0] == 3, f"第二块 start 应 3,实际 {log_blocks[1][0]}"
    _, second_line = log_blocks[1]
    args = mod._extract_args(second_line)
    assert any(_is_sensitive_arg(a) for a in args), f"应检出 response.getBody(), args={args}"


def test_adv03_block_comment_known_limitation():
    """ADV-R2-01 已知局限:闭合行 /* ( */ 块注释仍破坏合并(跨行块注释状态机未实现)。

    当前 9 callsite 全树无 /* */ 在闭合行的触发。本测试锚定边界:块注释场景当前合并为 1 块
    (已知不覆盖,future code 触发时需扩展块注释状态机)。
    """
    src = 'log.error("msg {}", headers); /* ( */\nlog.info("done", response.getBody());\n'
    merged = _merge_continuation_lines(src)
    log_blocks = [(ln, line) for ln, line in merged if _LOG_CALL_search(line)]
    # 已知局限:块注释破坏合并 → 1 块(非 2)。锚定此行为,扩展后改 assert == 2
    assert len(log_blocks) == 1, f"已知局限:块注释场景应 1 块,实际 {len(log_blocks)}(若已扩展块注释状态机,改本断言为 ==2)"
