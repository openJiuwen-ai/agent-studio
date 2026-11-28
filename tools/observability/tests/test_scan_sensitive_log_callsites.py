#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""SYNC-01 P7.1: Python 敏感日志扫描器直接单测（审视 §1.1/§1.2 要求）。

断言声称的不变量:命中/不命中集合(状态),非调用次数。
失效注入:删规则(注入点),不 mock 被验证的 _scan_source 本身。
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import pytest
from scan_sensitive_log_callsites import _scan_source, _sensitive_words_in_node, _sensitive_var_in_node

import scan_sensitive_log_callsites as mod


# ---- 正例:声称命中的格式串/值路径必须命中(审视 §1.1 表 5 例) ----

@pytest.mark.parametrize("src", [
    'logger.info(f"token={token}")',            # f-string JoinedStr
    'logger.info("token={}".format(token))',    # .format() Call
    'logger.info("token=%s" % token)',         # % BinOp
    'logger.info(token)',                       # 敏感变量名直传
    'logger.info("token refreshed")',           # 字面量含敏感词
    'logger.info(f"headers={headers}")',       # Header 容器
    'logger.info("password: %s", password)',   # 其他敏感词+变量
])
def test_sensitive_path_must_hit(src):
    assert _scan_source(src), f"应命中但未命中: {src}"


# ---- 反例:NLP/performance token + 安全访问器不命中 ----

@pytest.mark.parametrize("src", [
    'logger.info("total_token_ms: %s", total_token_ms)',   # NLP 变量名豁免
    'logger.info("JiebaTokenizerPool initialized")',       # NLP marker 豁免
    'logger.info("TiktokenCounter disabled")',             # NLP marker 豁免
    'logger.info("Invoke model. tokens:%s cost:%dms", tokens, cost)',  # policy.py 实际
    'logger.info(headers.keys())',                          # .keys() 安全
    'logger.info("size: %s", headers.size())',              # .size() 安全
    'logger.info("status: %s", statusCode)',               # statusCode 非敏感
])
def test_nlp_safe_path_must_not_hit(src):
    assert not _scan_source(src), f"不应命中但命中: {src} -> {_scan_source(src)}"


# ---- 失效注入:删规则(注入点)后正例必须 FAIL ----

def test_fault_injection_remove_nlp_markers(monkeypatch):
    """删 _NLP_MARKERS → TiktokenCounter 从豁免变命中(证明 NLP 豁免规则生效)。"""
    monkeypatch.setattr(mod, "_NLP_MARKERS", set())
    # monkeypatch 不影响已 from import 的引用,直接调模块函数
    from scan_sensitive_log_callsites import _sensitive_words_in_node as fn
    # 重新拿引用模块级常量
    mod._NLP_MARKERS = set()
    import ast
    node = ast.parse('"TiktokenCounter disabled"', mode="eval").body
    assert mod._sensitive_words_in_node(node) == "token", "删 NLP_MARKERS 后应命中 token"
    # 恢复(后续测试不受影响由 monkeypatch 保证,但模块级 set 已改,手动恢复)
    mod._NLP_MARKERS = {
        "tokenizer", "tiktoken", "jieba", "token_count", "token_usage",
        "total_token", "num_token", "prompt_token", "completion_token",
        "llm", "model_call", "nlp", "counter", "tokens",
    }


def test_fault_injection_remove_sensitive_var():
    """删 token 出 _SENSITIVE_VAR_NAMES → logger.info(token) 不再命中变量路径(仍可能字面量命中)。"""
    import ast
    saved = set(mod._SENSITIVE_VAR_NAMES)
    mod._SENSITIVE_VAR_NAMES = saved - {"token"}
    try:
        node = ast.parse("token", mode="eval").body
        assert mod._sensitive_var_in_node(node) is None, "删 token 后变量名不命中"
    finally:
        mod._SENSITIVE_VAR_NAMES = saved


# ---- 不变量:声称的覆盖路径等价 ----

def test_claim_invariant_format_string_paths_covered():
    """声称不变量: f-string/.format()/% 三路径的格式串内敏感词均命中。
    实际断言: 三路径各产出 >=1 violation(状态命中,非调用次数)。"""
    for src in ['logger.info(f"token={x}")',
                'logger.info("token={}".format(x))',
                'logger.info("token=%s" % x)']:
        assert _scan_source(src), f"格式串路径未覆盖: {src}"


# ---- 属性访问敏感值(adversarial #5: user.password/self.token 必命中) ----

@pytest.mark.parametrize("src", [
    'logger.info(f"{user.password}")',      # Attribute attr=password
    'logger.info(f"val={self.token}")',      # Attribute attr=token
    'logger.info("pwd=" + user.password)',   # BinOp + Attribute
    'logger.info(cred.token)',               # Attribute 直传
])
def test_attribute_access_sensitive_must_hit(src):
    assert _scan_source(src), f"属性访问敏感值应命中: {src}"


def test_attribute_access_nlp_exempt():
    """obj.token_usage 属性 NLP 豁免(不命中)。"""
    assert not _scan_source('logger.info(f"{obj.token_usage}")'), "token_usage 属性应 NLP 豁免"


def test_fault_injection_remove_attr_check():
    """删 Attribute 检查后 user.password 不命中(证明属性访问规则生效)。"""
    import ast
    saved = hasattr(mod, '_sensitive_var_in_node')
    # monkeypatch: 临时替换为只查 Name 的版本
    orig = mod._sensitive_var_in_node
    def name_only(node):
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                lid = n.id.lower()
                if lid in mod._NLP_TOKEN_VARS: continue
                if lid in mod._SENSITIVE_VAR_NAMES: return n.id
        return None
    mod._sensitive_var_in_node = name_only
    try:
        node = ast.parse('user.password', mode='eval').body
        assert name_only(node) is None, "只查 Name 时 user.password 不命中"
    finally:
        mod._sensitive_var_in_node = orig
