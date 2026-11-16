# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""ToolUseMode.stream 的 trace_handlers 透传测试。

工具使用模式此前缺 execute_tool span 的供给根因：初始消息的 runtime_data
未带 trace_handlers，ToolUsePlanner 经 message.runtime_data 构造插件/MCP
任务（create_plugin_task/create_mcp_task 透传合并 runtime_data），包装器
ainvoke kwargs 里 pop 不到该键。本测试钉住 stream 入口把 StreamRequest 的
trace_handlers 写进初始消息 runtime_data（与 react_mode 同款供给、
与 !2618 的 plan_execute_mode 供给对齐）。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from jiuwen.controller.agent.control_mode import tool_use_mode as tum


def _make_mode():
    """绕过重初始化链，仅装配 stream 入口段触碰的状态。"""
    mode = tum.ToolUseMode.__new__(tum.ToolUseMode)
    mode.task_id = "task-tu"
    mode.task_planner = MagicMock()
    return mode


@pytest.mark.asyncio
async def test_stream_entry_forwards_trace_handlers_into_message(monkeypatch):
    """stream 入口必须把 trace_handlers 写进初始消息的 runtime_data。"""
    handlers = [SimpleNamespace(name="otel_handler")]
    mode = _make_mode()
    captured = {}

    def fake_create_user_input_message(query, runtime_data):
        captured["runtime_data"] = runtime_data
        message = MagicMock()
        message.runtime_data = runtime_data
        return message

    monkeypatch.setattr(
        tum.MessageConverter,
        "create_user_input_message",
        staticmethod(fake_create_user_input_message),
    )

    async def fake_stream_task_loop(message):
        captured["message"] = message
        if False:  # noqa: B011 -- 使其成为空 async 生成器
            yield

    monkeypatch.setattr(mode, "_stream_task_loop", fake_stream_task_loop)

    async for _ in mode.stream(query="你好", trace_handlers=handlers):
        pass

    assert captured["runtime_data"]["trace_handlers"] is handlers
    assert captured["message"].runtime_data["trace_handlers"] is handlers


@pytest.mark.asyncio
async def test_stream_entry_defaults_trace_handlers_to_none(monkeypatch):
    """未携带 trace_handlers 时键仍存在且为 None——包装器侧按空转处理。"""
    mode = _make_mode()
    captured = {}

    def fake_create_user_input_message(query, runtime_data):
        captured["runtime_data"] = runtime_data
        message = MagicMock()
        message.runtime_data = runtime_data
        return message

    monkeypatch.setattr(
        tum.MessageConverter,
        "create_user_input_message",
        staticmethod(fake_create_user_input_message),
    )

    async def fake_stream_task_loop(message):
        if False:  # noqa: B011 -- 使其成为空 async 生成器
            yield

    monkeypatch.setattr(mode, "_stream_task_loop", fake_stream_task_loop)

    async for _ in mode.stream(query="你好"):
        pass

    assert captured["runtime_data"]["trace_handlers"] is None
