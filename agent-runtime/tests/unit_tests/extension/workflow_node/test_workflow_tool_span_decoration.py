# coding: utf-8
# pylint: disable=protected-access
"""工作流组件工具调用点的 tracer 装饰测试。

工具 span（execute_tool）此前在工作流内缺失的根因：FlowMcp / FlowApi /
FlowCustomApi 直连底层工具对象（MCPTool / RestfulApiToolNew /
CustomPluginTool），不经 ToolMgr.get_tool 的 decorate_tool_with_trace。
组件 invoke 现在主动补装饰；本文件钉住三处调用点的行为：

1. 新 core（NodeSession 带 span 协议）+ 已注册 agent handler →
   on_plugin_start / on_plugin_end 成对发射，instance_info 取 card 名；
2. 旧 core（NodeSession 无 span 协议）→ 装饰退化为原样返回，事件零发射，
   行为与接线前一致（新 studio × 旧 core 不崩的红线）。

session / tracer 用协议替身而非真实 core 类：装饰门槛只依赖
_inner.tracer() / _inner.span() / agent_handler_valid()，替身可同时建模
新旧两种 core 形态，测试不随配对 core 版本漂移。
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.flow_custom_api import FlowCustomApi
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp

USER_FIELDS = "userFields"


# ─── core 协议替身 ────────────────────────────────────────────────────


class _FakeSpanManager:
    """tracer_agent_span_manager 替身：create_agent_span 返回哑 span。"""

    def create_agent_span(self, parent_span):
        return SimpleNamespace(parent_invoke_id=getattr(parent_span, "invoke_id", None))


class _FakeTracer:
    """core Tracer 协议替身：只实现装饰器触碰的三个面。"""

    def __init__(self):
        self.events = []
        self.tracer_agent_span_manager = _FakeSpanManager()

    def agent_handler_valid(self):
        return True

    async def trigger(self, handler_class_name, event_name, **kwargs):
        self.events.append((handler_class_name, event_name, kwargs))


async def _no_op_trace(data=None, **kwargs):
    return None


def _make_session(tracer, with_span_protocol: bool):
    """构造 node.Session 包装器形态的替身。

    with_span_protocol=True 建模新版 core（NodeSession.span() 存在），
    False 建模旧版 core（无 span 属性 → _should_decorate 拒绝）。
    """
    inner = SimpleNamespace(tracer=lambda: tracer)
    if with_span_protocol:
        inner.span = lambda: None
    return SimpleNamespace(
        _inner=inner, trace=_no_op_trace, get_session_id=lambda: "session-1"
    )


class _StubApiTool:
    """RestfulApiToolNew / CustomPluginTool 形态替身：invoke 直通 ainvoke。"""

    def __init__(self, name: str):
        self.card = SimpleNamespace(name=name)
        self.response = []
        self.params = []
        self.ainvoke_calls = []

    async def ainvoke(self, inputs, **kwargs):
        self.ainvoke_calls.append((inputs, kwargs))
        return {"errCode": 0, "data": "ok"}

    async def invoke(self, inputs, **kwargs):
        return await self.ainvoke(inputs, **kwargs)


# ─── 断言辅助 ─────────────────────────────────────────────────────────


def _plugin_events(tracer):
    return [
        (event_name, kwargs)
        for _cls, event_name, kwargs in tracer.events
        if event_name.startswith("on_plugin")
    ]


def _assert_full_plugin_span(tracer, tool_name, expected_inputs):
    events = _plugin_events(tracer)
    names = [name for name, _kw in events]
    assert names == ["on_plugin_start", "on_plugin_end"], names

    start_kwargs = events[0][1]
    assert start_kwargs["instance_info"] == {
        "class_name": tool_name,
        "type": "tool",
    }
    assert start_kwargs["inputs"] == {"inputs": expected_inputs}
    end_kwargs = events[1][1]
    assert "outputs" in end_kwargs


def _assert_no_plugin_events(tracer):
    assert _plugin_events(tracer) == []


# ─── FlowApi / FlowCustomApi ──────────────────────────────────────────


def _make_flow_api(api_tool):
    flow = FlowApi(conf=None)
    flow._conf = {}
    flow._api = api_tool
    flow._api_id = "test-api-id"
    flow._enable_validate = False
    flow._enable_confirm = False
    flow._outputs = []
    flow._user_fields = {"outputs": []}
    return flow


def _make_flow_custom_api(api_tool):
    flow = FlowCustomApi(conf=None)
    flow._conf = {}
    flow._api = api_tool
    flow._api_id = "test-api-id"
    flow._enable_validate = False
    flow._enable_confirm = False
    flow._outputs = []
    flow._user_fields = {"outputs": []}
    return flow


_API_INPUTS = {USER_FIELDS: {"query": "hi"}, "validated": True, "confirmed": True}


@pytest.mark.asyncio
async def test_flow_api_emits_plugin_span_with_new_core_session():
    tracer = _FakeTracer()
    api_tool = _StubApiTool("weather_api")
    flow = _make_flow_api(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ), patch.object(flow, "_format_api_header", return_value={}):
        result = await flow.invoke(
            dict(_API_INPUTS), _make_session(tracer, with_span_protocol=True), None
        )

    assert result[USER_FIELDS]["errCode"] == 0
    assert len(api_tool.ainvoke_calls) == 1
    inputs, kwargs = api_tool.ainvoke_calls[0]
    assert inputs == {"query": "hi"}
    assert kwargs == {"runtime_auth": {"headers": {}}}
    _assert_full_plugin_span(tracer, "weather_api", {"query": "hi"})


@pytest.mark.asyncio
async def test_flow_api_noop_with_old_core_session():
    """旧 core（无 span 协议）：装饰退化，事件零发射，输出不变。"""
    tracer = _FakeTracer()
    api_tool = _StubApiTool("weather_api")
    flow = _make_flow_api(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ), patch.object(flow, "_format_api_header", return_value={}):
        result = await flow.invoke(
            dict(_API_INPUTS), _make_session(tracer, with_span_protocol=False), None
        )

    assert result[USER_FIELDS]["errCode"] == 0
    assert len(api_tool.ainvoke_calls) == 1
    _assert_no_plugin_events(tracer)


@pytest.mark.asyncio
async def test_flow_custom_api_emits_plugin_span_with_new_core_session():
    tracer = _FakeTracer()
    api_tool = _StubApiTool("custom_plugin")
    flow = _make_flow_custom_api(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ):
        result = await flow.invoke(
            dict(_API_INPUTS), _make_session(tracer, with_span_protocol=True), None
        )

    assert result["userFields"]["errCode"] == 0
    assert api_tool.ainvoke_calls[0][0] == {"query": "hi"}
    _assert_full_plugin_span(tracer, "custom_plugin", {"query": "hi"})


# ─── FlowMcp ─────────────────────────────────────────────────────────


def _make_mcp_conf():
    """旧版路径 conf（走 list_tools），复用并发初始化测试的形态。"""
    return {
        "type": "sse",
        "url": "http://localhost:3000/mcp",
        "name": "weather_mcp_server",
        "tool_name": "mock_tool",
        "description": "A mock MCP tool for testing",
        "headers": {},
        "auth": {},
        "pluginDependency": {},
    }


def _make_mock_card():
    from openjiuwen.core.foundation.tool.mcp.base import McpToolCard
    from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS

    return McpToolCard(
        name="mock_tool",
        server_name="weather_mcp_server",
        description="",
        input_params={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                JIUWEN_RUNTIME_KWARGS: {"type": "object"},
            },
            "additionalProperties": True,
        },
    )


@pytest.fixture
def mock_mcp_client():
    with patch(
        "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.list_tools",
        new_callable=AsyncMock,
    ) as mock_list_tools:
        mock_list_tools.return_value = [_make_mock_card()]
        with patch(
            "jiuwen.extension.wrapper.sse_client_new.SSEClientNew.call_tool",
            new_callable=AsyncMock,
        ) as mock_call_tool:
            mock_call_tool.return_value = [
                {"model_dump": lambda: {"type": "text", "text": "mock mcp response"}}
            ]
            yield {"list_tools": mock_list_tools, "call_tool": mock_call_tool}


@pytest.mark.asyncio
async def test_flow_mcp_emits_plugin_span_with_new_core_session(mock_mcp_client):
    tracer = _FakeTracer()
    flow_mcp = FlowMcp(_make_mcp_conf())

    result = await flow_mcp.invoke(
        {USER_FIELDS: {"query": "hello"}},
        _make_session(tracer, with_span_protocol=True),
        None,
    )

    assert result[USER_FIELDS]["isError"] is False
    mock_mcp_client["call_tool"].assert_awaited_once()
    events = _plugin_events(tracer)
    assert [name for name, _kw in events] == ["on_plugin_start", "on_plugin_end"]
    assert events[0][1]["instance_info"]["class_name"] == "mock_tool"


@pytest.mark.asyncio
async def test_flow_mcp_noop_with_old_core_session(mock_mcp_client):
    tracer = _FakeTracer()
    flow_mcp = FlowMcp(_make_mcp_conf())

    result = await flow_mcp.invoke(
        {USER_FIELDS: {"query": "hello"}},
        _make_session(tracer, with_span_protocol=False),
        None,
    )

    assert result[USER_FIELDS]["isError"] is False
    mock_mcp_client["call_tool"].assert_awaited_once()
    _assert_no_plugin_events(tracer)
