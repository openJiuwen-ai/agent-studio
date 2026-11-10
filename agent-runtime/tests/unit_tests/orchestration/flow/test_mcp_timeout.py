# coding: utf-8
"""mcp_timeout / exception_handler._get_mcp_timeout 单元测试。

覆盖：
1. parse_mcp_time_out_seconds — 默认值、非法字符串、0/负数/nan/inf
2. _get_mcp_timeout — 节点超时、keep-alive 超时、env is None、timeout<=0
3. 导入回归测试 — mcp_timeout 模块可独立导入，不触发循环

运行方式：
    cd agent-runtime
    pytest tests/unit_tests/orchestration/flow/test_mcp_timeout.py -v
"""

import os

import pytest

from jiuwen.orchestration.flow.constant import DEFAULT_MCP_TIME_OUT_SECONDS
from jiuwen.orchestration.flow.exception_handler import _get_mcp_timeout
from jiuwen.orchestration.flow.mcp_timeout import parse_mcp_time_out_seconds


# ─── 导入回归测试 ────────────────────────────────────────────────────


def test_mcp_timeout_module_importable():
    """mcp_timeout 模块可独立导入，不触发循环依赖。"""
    import jiuwen.orchestration.flow.mcp_timeout as mod

    assert hasattr(mod, "parse_mcp_time_out_seconds")
    assert callable(mod.parse_mcp_time_out_seconds)


# ─── parse_mcp_time_out_seconds ──────────────────────────────────────


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("MCP_TIME_OUT_SECONDS", raising=False)
    return monkeypatch


def test_default_when_env_missing(clean_env):
    assert parse_mcp_time_out_seconds() == DEFAULT_MCP_TIME_OUT_SECONDS


def test_valid_value(clean_env, monkeypatch):
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "600")
    assert parse_mcp_time_out_seconds() == 600.0


def test_non_numeric_string(clean_env, monkeypatch):
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "abc")
    assert parse_mcp_time_out_seconds() == DEFAULT_MCP_TIME_OUT_SECONDS


def test_zero(clean_env, monkeypatch):
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "0")
    assert parse_mcp_time_out_seconds() == DEFAULT_MCP_TIME_OUT_SECONDS


def test_negative(clean_env, monkeypatch):
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "-1")
    assert parse_mcp_time_out_seconds() == DEFAULT_MCP_TIME_OUT_SECONDS


def test_nan(clean_env, monkeypatch):
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "nan")
    assert parse_mcp_time_out_seconds() == DEFAULT_MCP_TIME_OUT_SECONDS


def test_inf(clean_env, monkeypatch):
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "inf")
    assert parse_mcp_time_out_seconds() == DEFAULT_MCP_TIME_OUT_SECONDS


def test_float_string(clean_env, monkeypatch):
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "120.5")
    assert parse_mcp_time_out_seconds() == 120.5


# ─── _get_mcp_timeout ────────────────────────────────────────────────


def _ka(val):
    """构造 keep-alive 环境变量 dict（毫秒）。"""
    return {"request_timeout_mcp": val}


def test_node_timeout_smaller_than_cap():
    """节点超时 < 兜底 → 返回节点超时。"""
    result = _get_mcp_timeout({}, "request_timeout_mcp", 10)
    assert result == 10


def test_node_timeout_larger_than_cap(clean_env, monkeypatch):
    """节点超时 > 兜底 → 返回兜底。"""
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "60")
    result = _get_mcp_timeout({}, "request_timeout_mcp", 7200)
    assert result == 60


def test_keepalive_smaller_than_node(clean_env, monkeypatch):
    """keep-alive < 节点超时 → 返回 keep-alive。"""
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "600")
    # keep-alive = 5000ms = 5s
    result = _get_mcp_timeout(_ka(5000), "request_timeout_mcp", 300)
    assert result == 5.0


def test_keepalive_larger_than_cap(clean_env, monkeypatch):
    """keep-alive > 兜底 → 返回兜底。"""
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "60")
    # keep-alive = 600000ms = 600s，但 cap=60s
    result = _get_mcp_timeout(_ka(600000), "request_timeout_mcp", 300)
    assert result == 60


def test_env_none_still_applies_cap():
    """env 为空 dict 时，兜底仍生效。"""
    result = _get_mcp_timeout({}, "request_timeout_mcp", 7200)
    assert result == DEFAULT_MCP_TIME_OUT_SECONDS


def test_timeout_zero_returns_cap():
    """timeout=0 时返回兜底值，不返回 0。"""
    result = _get_mcp_timeout({}, "request_timeout_mcp", 0)
    assert result == DEFAULT_MCP_TIME_OUT_SECONDS
    assert result > 0


def test_timeout_negative_returns_cap():
    """timeout 为负数时返回兜底值。"""
    result = _get_mcp_timeout({}, "request_timeout_mcp", -1)
    assert result == DEFAULT_MCP_TIME_OUT_SECONDS


def test_keepalive_zero_excluded():
    """keep-alive=0 不参与取小，被跳过。"""
    result = _get_mcp_timeout(_ka(0), "request_timeout_mcp", 100)
    # candidates = [cap, 100]，keep-alive=0 被排除
    assert result == min(DEFAULT_MCP_TIME_OUT_SECONDS, 100)


def test_keepalive_negative_excluded():
    """keep-alive 为负数不参与取小。"""
    result = _get_mcp_timeout(_ka(-100), "request_timeout_mcp", 100)
    assert result == min(DEFAULT_MCP_TIME_OUT_SECONDS, 100)


def test_all_three_take_min(clean_env, monkeypatch):
    """三者取小：节点 200s、keep-alive 10s（10000ms）、cap 60s → 10s。"""
    monkeypatch.setenv("MCP_TIME_OUT_SECONDS", "60")
    result = _get_mcp_timeout(_ka(10000), "request_timeout_mcp", 200)
    assert result == 10.0
