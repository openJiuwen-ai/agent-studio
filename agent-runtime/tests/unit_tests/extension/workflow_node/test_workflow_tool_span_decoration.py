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

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.flow_custom_api import FlowCustomApi
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.workflow_node.utils import JiuWenBaseException
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS

USER_FIELDS = "userFields"


# ─── core 协议替身 ───


class _FakeSpanManager:
    """tracer_agent_span_manager 替身：create_agent_span 返回哑 span。"""

    @staticmethod
    def create_agent_span(parent_span):
        return SimpleNamespace(parent_invoke_id=getattr(parent_span, "invoke_id", None))


class _FakeTracer:
    """core Tracer 协议替身：只实现装饰器触碰的三个面。"""

    def __init__(self):
        self.events = []
        self.tracer_agent_span_manager = _FakeSpanManager()

    @staticmethod
    def agent_handler_valid():
        return True

    async def trigger(self, handler_class_name, event_name, **kwargs):
        self.events.append((handler_class_name, event_name, kwargs))


async def _no_op_trace(data=None, **kwargs):
    return None


def _no_op_span():
    return None


def _make_session(tracer, with_span_protocol: bool):
    """构造 node.Session 包装器形态的替身。

    with_span_protocol=True 建模新版 core（NodeSession.span() 存在），
    False 建模旧版 core（无 span 属性 → _should_decorate 拒绝）。
    """
    inner = SimpleNamespace(tracer=lambda: tracer)
    if with_span_protocol:
        inner.span = _no_op_span
    return SimpleNamespace(
        _inner=inner, trace=_no_op_trace, get_session_id=lambda: "session-1"
    )


class _StubApiTool:
    """RestfulApiToolNew / CustomPluginTool 形态替身：invoke 直通 ainvoke。"""

    def __init__(self, name: str):
        self.card = SimpleNamespace(name=name)
        self.response = []
        self.params = []
        self.invoke_calls = []
        self.ainvoke_calls = []

    async def ainvoke(self, inputs, **kwargs):
        self.ainvoke_calls.append((inputs, kwargs))
        return {"errCode": 0, "data": "ok"}

    async def invoke(self, inputs, **kwargs):
        # invoke 与 ainvoke 分别记录：生产调用位点（invoke）与内部委托
        # （ainvoke）可分辨，委托链不掩盖真实调用契约。
        self.invoke_calls.append((inputs, kwargs))
        return await self.ainvoke(inputs, **kwargs)


# ─── 断言辅助 ───


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


# ─── FlowApi / FlowCustomApi ───


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
    assert len(api_tool.invoke_calls) == 1, "生产位点必须经 invoke 入口"
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
    assert api_tool.invoke_calls[0][0] == {"query": "hi"}
    assert api_tool.ainvoke_calls[0][0] == {"query": "hi"}
    _assert_full_plugin_span(tracer, "custom_plugin", {"query": "hi"})


# ─── FlowMcp ───


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
async def test_flow_mcp_plugin_span_inputs_exclude_runtime_auth(mock_mcp_client):
    """鉴权头不进 execute_tool span：记录面剥离，转发真实调用时回填。"""
    tracer = _FakeTracer()
    flow_mcp = FlowMcp(_make_mcp_conf())
    with patch.object(
        flow_mcp,
        "_format_runtime_auth",
        return_value={"Authorization": "Bearer s3cr3t"},
    ):
        result = await flow_mcp.invoke(
            {USER_FIELDS: {"query": "hello"}},
            _make_session(tracer, with_span_protocol=True),
            None,
        )

    assert result[USER_FIELDS]["isError"] is False
    events = _plugin_events(tracer)
    assert [name for name, _kw in events] == ["on_plugin_start", "on_plugin_end"]
    recorded_inputs = events[0][1]["inputs"]["inputs"]
    assert JIUWEN_RUNTIME_KWARGS not in recorded_inputs, "鉴权键不得进入 span 记录面"

    # 真实调用不受剥离影响：call_tool 收到的 arguments 仍含回填的鉴权
    mock_mcp_client["call_tool"].assert_awaited_once()
    call_arguments = mock_mcp_client["call_tool"].await_args.kwargs["arguments"]
    assert call_arguments[JIUWEN_RUNTIME_KWARGS]["runtime_auth"]["headers"] == {
        "Authorization": "Bearer s3cr3t"
    }


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


# ─── stream 位点（流式执行模式）───


class _StubStreamApiTool(_StubApiTool):
    """带 astream 的工具替身：流式产出两个 chunk。"""

    def __init__(self, name: str):
        super().__init__(name)
        self.astream_calls = []

    async def astream(self, inputs, **kwargs):
        self.astream_calls.append((inputs, kwargs))
        yield {"errCode": 0, "data": "chunk-1"}
        yield {"errCode": 0, "data": "chunk-2"}


class _RecordingProxy:
    """新 core 装饰代理替身：stream 位点必须经它的 astream。

    事件发射在 core 侧由 async_trace_stream 包装承担，studio 侧只钉
    调用契约。
    """

    def __init__(self, tool):
        self._tool = tool
        self.astream_calls = []

    async def invoke(self, inputs, **kwargs):
        return await self._tool.invoke(inputs, **kwargs)

    async def astream(self, inputs, **kwargs):
        self.astream_calls.append((inputs, kwargs))
        async for item in self._tool.astream(inputs, **kwargs):
            yield item


async def _passthrough_transform(api_outputs, session):
    async for item in api_outputs:
        yield item


@pytest.mark.asyncio
async def test_flow_api_stream_path_uses_decorated_astream():
    """stream 调用点经装饰代理的 astream，入参与直连时一致。"""
    tracer = _FakeTracer()
    api_tool = _StubStreamApiTool("weather_api")
    flow = _make_flow_api(api_tool)
    proxy = _RecordingProxy(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ), patch.object(flow, "_format_api_header", return_value={}), patch.object(
        flow, "_transform_async_stream_data", new=_passthrough_transform
    ), patch(
        "jiuwen.extension.workflow_node.flow_api.decorate_tool_with_trace",
        return_value=proxy,
    ):
        schemas = []
        async for schema in flow.stream(
            dict(_API_INPUTS), _make_session(tracer, with_span_protocol=True), None
        ):
            schemas.append(schema)

    assert proxy.astream_calls == [
        ({"query": "hi"}, {"runtime_auth": {"headers": {}}})
    ]
    assert len(schemas) == 2, "chunk 数据仍完整流出"


@pytest.mark.asyncio
async def test_flow_custom_api_stream_path_uses_decorated_astream():
    """stream 调用点经装饰代理的 astream，入参与直连时一致。"""
    tracer = _FakeTracer()
    api_tool = _StubStreamApiTool("custom_plugin")
    flow = _make_flow_custom_api(api_tool)
    proxy = _RecordingProxy(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ), patch.object(
        flow, "_transform_async_stream_data", new=_passthrough_transform
    ), patch(
        "jiuwen.extension.workflow_node.flow_custom_api.decorate_tool_with_trace",
        return_value=proxy,
    ):
        schemas = []
        async for schema in flow.stream(
            dict(_API_INPUTS), _make_session(tracer, with_span_protocol=True), None
        ):
            schemas.append(schema)

    assert proxy.astream_calls == [({"query": "hi"}, {})]
    assert len(schemas) == 2, "chunk 数据仍完整流出"


@pytest.mark.asyncio
async def test_flow_api_stream_old_core_passthrough():
    """旧 core（装饰原样返回）：stream 仍直连工具 astream，不崩不漏数据。"""
    tracer = _FakeTracer()
    api_tool = _StubStreamApiTool("weather_api")
    flow = _make_flow_api(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ), patch.object(flow, "_format_api_header", return_value={}), patch.object(
        flow, "_transform_async_stream_data", new=_passthrough_transform
    ):
        schemas = []
        async for schema in flow.stream(
            dict(_API_INPUTS), _make_session(tracer, with_span_protocol=False), None
        ):
            schemas.append(schema)

    assert api_tool.astream_calls == [({"query": "hi"}, {"runtime_auth": {"headers": {}}})]
    assert len(schemas) == 2
    _assert_no_plugin_events(tracer)


@pytest.mark.asyncio
async def test_flow_api_stream_real_decorator_keeps_astream():
    """真实 decorate_tool_with_trace（不 patch）下 stream 位点仍拿得到 astream。

    跨 core 版本底线用例：配对 core 的代理要么显式包装 astream（新 core，
    execute_tool span 生效），要么仅包装 invoke、其余属性经
    ``_TraceProxy.__getattr__`` 透传（!3650 之前的 core）。两种形态下
    stream 位点的 astream 都必须可达且 chunk 不丢——「代理缺 astream →
    流式节点 100% 失败」的配对风险在此被实测排除，而非被替身代理抹掉。
    """
    tracer = _FakeTracer()
    api_tool = _StubStreamApiTool("weather_api")
    flow = _make_flow_api(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ), patch.object(flow, "_format_api_header", return_value={}), patch.object(
        flow, "_transform_async_stream_data", new=_passthrough_transform
    ):
        schemas = []
        async for schema in flow.stream(
            dict(_API_INPUTS), _make_session(tracer, with_span_protocol=True), None
        ):
            schemas.append(schema)

    assert api_tool.astream_calls == [
        ({"query": "hi"}, {"runtime_auth": {"headers": {}}})
    ]
    assert len(schemas) == 2, "真实装饰下 chunk 数据仍完整流出"


@pytest.mark.asyncio
async def test_flow_api_stream_error_through_decorator_still_maps():
    """装饰生效路径下 astream 抛错仍走既有异常映射，不被装饰吞掉。"""

    class _BoomStreamTool(_StubStreamApiTool):
        async def astream(self, inputs, **kwargs):
            self.astream_calls.append((inputs, kwargs))
            yield {"errCode": 0, "data": "partial"}
            raise RuntimeError("api exploded mid-stream")

    tracer = _FakeTracer()
    api_tool = _BoomStreamTool("weather_api")
    flow = _make_flow_api(api_tool)
    with patch.object(
        flow, "_format_api_inputs", new=AsyncMock(return_value={"query": "hi"})
    ), patch.object(flow, "_format_api_header", return_value={}), patch.object(
        flow, "_transform_async_stream_data", new=_passthrough_transform
    ):
        with pytest.raises(JiuWenBaseException):
            async for _schema in flow.stream(
                dict(_API_INPUTS), _make_session(tracer, with_span_protocol=True), None
            ):
                pass
