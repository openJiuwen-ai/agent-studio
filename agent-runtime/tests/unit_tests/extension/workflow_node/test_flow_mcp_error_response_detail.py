# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for FlowMcp._create_error_response 的错误信息保留。

背景 bug：原实现除 isinstance 判断外完全不使用 error 参数，str(error)/traceback
全部丢弃，所有 MCP 工具调用失败对用户一律呈现
"Mcp execute error, reason is Exception."，无法定位是网络、鉴权还是工具内部错误。
"""

from jiuwen.extension.workflow_node.flow_mcp import FlowMcp


def _make_flow_mcp():
    """绕过重量级 __init__，仅装配 _create_error_response 依赖。"""
    return FlowMcp.__new__(FlowMcp)


def _call_create_error_response(flow_mcp, error):
    return getattr(flow_mcp, "_create_error_response")(error)


class TestCreateErrorResponseDetail:
    @staticmethod
    def test_plain_exception_keeps_type_and_message():
        exc = _call_create_error_response(
            _make_flow_mcp(), TimeoutError("connect to mcp server timed out after 30s")
        )
        assert "TimeoutError" in exc.message
        assert "connect to mcp server timed out after 30s" in exc.message
        assert "reason is Exception." not in exc.message

    @staticmethod
    def test_exception_group_expands_sub_exceptions():
        group = ExceptionGroup("mcp calls", [ValueError("tool a failed"), KeyError("auth")])
        exc = _call_create_error_response(_make_flow_mcp(), group)
        assert "ExceptionGroup" in exc.message
        assert "tool a failed" in exc.message
        assert "auth" in exc.message

    @staticmethod
    def test_error_code_unchanged():
        exc = _call_create_error_response(_make_flow_mcp(), RuntimeError("boom"))
        assert exc.error_code == 101873
