# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""McpToolWrapper.ainvoke 的 trace 生命周期契约测试。

MCP 包装器的 on_plugin_start/end/error 发射机制为基线已有（规划/工具/
react 模式共用：plugin_handler 经 **runtime_data 把 trace_handlers 传入
ainvoke，包装器内部 TraceManager 发射）。本测试钉住三态成对契约，防止
后续改动破坏——多智能体调单智能体实测的"工具连续失败 21 次全程无
tool span"场景，错误形态可见性正依赖 on_plugin_error 这一路。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from jiuwen.extension.wrapper.mcp_tool_wrapper import McpToolWrapper


def _make_recording_handler():
    """构造记录 on_plugin_* 事件的 trace handler 替身。"""
    handler = MagicMock()
    handler.on_plugin_start = AsyncMock()
    handler.on_plugin_end = AsyncMock()
    handler.on_plugin_error = AsyncMock()
    return handler


def _make_wrapper(monkeypatch, tool):
    """绕过构造器依赖（resource_mgr 注册链），仅注入 _get_tool。"""
    wrapper = McpToolWrapper.__new__(McpToolWrapper)
    monkeypatch.setattr(wrapper, "_get_tool", lambda: tool)
    return wrapper


def test_ainvoke_success_emits_start_end_pair(monkeypatch):
    """成功路径：on_plugin_start/end 成对发射，结果格式不变。"""
    handler = _make_recording_handler()
    tool = SimpleNamespace(invoke=AsyncMock(return_value={"result": "ok"}))
    wrapper = _make_wrapper(monkeypatch, tool)

    import asyncio

    result = asyncio.run(wrapper.ainvoke({"q": 1}, trace_handlers=[handler]))

    assert result == {"errCode": 0, "errMessage": "success", "data": "ok"}
    handler.on_plugin_start.assert_awaited_once()
    handler.on_plugin_end.assert_awaited_once()
    # start 事件载荷：(instance_info, inputs)；instance_info 由 TraceManager 注入
    start_args = handler.on_plugin_start.await_args.args
    assert start_args[1] == {"q": 1}
    assert isinstance(start_args[0], dict)
    handler.on_plugin_error.assert_not_awaited()


def test_ainvoke_error_emits_error_and_wraps_response(monkeypatch):
    """工具异常：on_plugin_error 发射且不落 end，错误响应包装不变。"""
    handler = _make_recording_handler()
    tool = SimpleNamespace(invoke=AsyncMock(side_effect=RuntimeError("mcp down")))
    wrapper = _make_wrapper(monkeypatch, tool)

    import asyncio

    result = asyncio.run(wrapper.ainvoke({"q": 1}, trace_handlers=[handler]))

    assert result["errCode"] != 0
    handler.on_plugin_start.assert_awaited_once()
    handler.on_plugin_error.assert_awaited_once()
    assert isinstance(handler.on_plugin_error.await_args.args[0], RuntimeError)
    handler.on_plugin_end.assert_not_awaited()


def test_ainvoke_without_trace_handlers_still_executes(monkeypatch):
    """不传 trace_handlers：TraceManager 空转，工具调用行为不变。"""
    tool = SimpleNamespace(invoke=AsyncMock(return_value={"result": "ok"}))
    wrapper = _make_wrapper(monkeypatch, tool)

    import asyncio

    result = asyncio.run(wrapper.ainvoke({"q": 1}))

    assert result == {"errCode": 0, "errMessage": "success", "data": "ok"}
