# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for the OpenJiuwenAgentFacade bridge."""

from __future__ import annotations

from typing import Any

import pytest
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.integration.openjiuwen_agent_facade import OpenJiuwenAgentFacade


class _FakeDelegateAgent:
    """Minimal commercial-agent-like object for facade tests."""

    def __init__(self):
        self.task_id = "task_1"
        self.agent_id = "agent_1"
        self.control_mode_value = "Controller"
        self.task_end = False
        self.astream_calls: list[dict[str, Any]] = []
        self.saved_keys: list[str] = []
        self.loaded_states: list[Any] = []
        self.cleared = False

    async def astream(self, inputs, **kwargs):
        self.astream_calls.append({"inputs": inputs, "kwargs": kwargs})
        yield {"chunk": "hello"}
        yield {"chunk": "world"}

    def get_control_mode(self):
        return self.control_mode_value

    def get_task_end(self):
        return self.task_end

    async def save_state(self, key):
        self.saved_keys.append(key)

    async def load_state(self, state):
        self.loaded_states.append(state)

    async def get_state(self):
        return {"state": "ok"}

    def clear_state(self):
        self.cleared = True


@pytest.mark.asyncio
async def test_stream_delegates_to_commercial_agent():
    """Facade stream should decode dict-like inputs and forward kwargs."""
    delegate = _FakeDelegateAgent()
    facade = OpenJiuwenAgentFacade(delegate)

    inputs = {
        "query": "hello",
        "conversation_id": "conv_1",
        "_jiuwen_runtime_kwargs": {
            "stream": True,
            "runtime_context": {"foo": "bar"},
            "tool_switch_dict": {"wf_1": True},
            "trace_handlers": ["trace_handler"],
        },
    }

    items = []
    async for item in facade.stream(inputs):
        items.append(item)

    assert items == [{"chunk": "hello"}, {"chunk": "world"}]
    assert len(delegate.astream_calls) == 1
    call = delegate.astream_calls[0]
    assert call["inputs"] == inputs
    assert call["kwargs"]["stream"] is True
    assert call["kwargs"]["runtime_context"] == {"foo": "bar"}
    assert call["kwargs"]["tool_switch_dict"] == {"wf_1": True}
    assert call["kwargs"]["trace_handlers"] == ["trace_handler"]


@pytest.mark.asyncio
async def test_proxy_methods_are_forwarded():
    """Facade should continue exposing commercial-agent state methods."""
    delegate = _FakeDelegateAgent()
    facade = OpenJiuwenAgentFacade(delegate)

    assert facade.task_id == "task_1"
    assert facade.agent_id == "agent_1"
    assert facade.get_control_mode() == "Controller"
    assert facade.get_task_end() is False

    await facade.save_state("conv_1")
    await facade.load_state({"x": 1})
    state = await facade.get_state()
    facade.clear_state()

    assert delegate.saved_keys == ["conv_1"]
    assert delegate.loaded_states == [{"x": 1}]
    assert state == {"state": "ok"}
    assert delegate.cleared is True


@pytest.mark.asyncio
async def test_invoke_raises_blocking_not_supported():
    """Facade invoke should preserve current blocking-not-supported behavior."""
    delegate = _FakeDelegateAgent()
    facade = OpenJiuwenAgentFacade(delegate)

    with pytest.raises(JiuWenBaseException) as exc_info:
        await facade.invoke({"query": "hello"})

    assert exc_info.value.error_code == StatusCode.PARAM_CHECK_FAILED_ERROR.code
    assert "Blocking is not supported yet" in exc_info.value.message
