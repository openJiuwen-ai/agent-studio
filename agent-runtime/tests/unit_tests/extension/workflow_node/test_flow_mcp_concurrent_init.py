# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS
from openjiuwen.core.foundation.tool.mcp.base import McpToolCard
from openjiuwen.core.workflow import create_workflow_session


USER_FIELDS = "userFields"


# ─── helpers ──────────────────────────────────────────────────────────


def _make_flow_mcp_conf(*, older_version: bool = False) -> dict:
    """FlowMcp 组件的 IR 配置"""
    conf = {
        "type": "sse",
        "url": "http://localhost:3000/mcp",
        "name": "weather_mcp_server",
        "tool_name": "mock_tool",
        "description": "A mock MCP tool for testing",
        "headers": {"Authorization": "Bearer test-token"},
        "auth": {
            "headers": {},
            "query": {"key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx==="},
            "scope": "SERVICE",
        },
        "pluginDependency": {},
    }
    if not older_version:
        conf["arguments"] = [
            {
                "name": "query",
                "description": "查询内容",
                "type": "string",
                "required": True,
                "method": "Body",
            },
        ]
    return conf


def _make_mock_card() -> McpToolCard:
    """构造供 list_tools 返回的 Mock McpToolCard"""
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


# ─── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_mcp_client():
    """Mock SSEClientNew 的 list_tools 和 call_tool 方法，避免真实网络请求"""
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
                {
                    "model_dump": lambda: {
                        "type": "text",
                        "text": "mock mcp response",
                    }
                }
            ]
            yield {
                "list_tools": mock_list_tools,
                "call_tool": mock_call_tool,
            }


# ─── 测试类 ───────────────────────────────────────────────────────────


class TestFlowMcpConcurrentInit:
    """FlowMcp 并发初始化锁测试

    守护修复目标：_init_api 双重检查锁保证高并发 invoke 下
    MCPTool 只创建一次、list_tools 只调用一次，且不引入死锁/异常吞没。
    """

    @pytest.mark.asyncio
    async def test_concurrent_invoke_initializes_only_once(self, mock_mcp_client):
        """并发 invoke 时 list_tools / MCPTool 只初始化一次"""
        conf = _make_flow_mcp_conf(older_version=True)  # 旧版路径，走 list_tools
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        # list_tools 内真正 await，强制让出协程以复现竞态
        async def _slow_list_tools():
            await asyncio.sleep(0.01)
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _slow_list_tools

        inputs = {USER_FIELDS: {"query": "hello"}}
        results = await asyncio.gather(
            *(flow_mcp.invoke(inputs, session, None) for _ in range(20))
        )

        assert mock_mcp_client["list_tools"].await_count == 1  # 无锁时会远大于 1
        assert mock_mcp_client["call_tool"].await_count == 20
        assert all(r[USER_FIELDS]["isError"] is False for r in results)
        assert flow_mcp.api is not None

    @pytest.mark.asyncio
    async def test_second_waiter_skips_init_after_lock_release(self, mock_mcp_client):
        """等锁协程拿锁后 double-check 命中，不再 init"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        entered = asyncio.Event()
        release = asyncio.Event()

        async def _gated_list_tools():
            entered.set()  # 第一个协程已进入 list_tools（持有锁）
            await release.wait()  # 阻塞，让第二个协程排队抢锁
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _gated_list_tools

        inputs = {USER_FIELDS: {"query": "hello"}}
        t1 = asyncio.create_task(flow_mcp.invoke(inputs, session, None))
        await entered.wait()
        t2 = asyncio.create_task(flow_mcp.invoke(inputs, session, None))
        await asyncio.sleep(0.01)  # 让 t2 排到锁上
        release.set()  # 放行第一个

        r1, r2 = await asyncio.gather(t1, t2)

        assert mock_mcp_client["list_tools"].await_count == 1  # 第二个 double-check 跳过
        assert r1[USER_FIELDS]["isError"] is False
        assert r2[USER_FIELDS]["isError"] is False

    @pytest.mark.asyncio
    async def test_serial_invoke_does_not_re_initialize(self, mock_mcp_client):
        """初始化完成后，后续串行 invoke 不再调 list_tools（锁外快速路径）"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        inputs = {USER_FIELDS: {"query": "hello"}}
        await flow_mcp.invoke(inputs, session, None)
        await flow_mcp.invoke(inputs, session, None)
        await flow_mcp.invoke(inputs, session, None)

        assert mock_mcp_client["list_tools"].await_count == 1
        assert mock_mcp_client["call_tool"].await_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_invoke_all_succeed_without_deadlock(self, mock_mcp_client):
        """并发调用不死锁，结果全部成功"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        async def _fast_list_tools():
            await asyncio.sleep(0)
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _fast_list_tools

        inputs = {USER_FIELDS: {"query": "hello"}}
        results = await asyncio.wait_for(
            asyncio.gather(
                *(flow_mcp.invoke(inputs, session, None) for _ in range(50))
            ),
            timeout=5.0,
        )
        assert len(results) == 50
        assert all(r[USER_FIELDS]["isError"] is False for r in results)

    @pytest.mark.asyncio
    async def test_init_failure_releases_lock_and_propagates(self, mock_mcp_client):
        """_init_api 抛异常时锁被释放、异常透传，后续可重试"""
        conf = _make_flow_mcp_conf(older_version=True)
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        call_count = {"n": 0}

        async def _fail_then_ok():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("list_tools boom")
            return [_make_mock_card()]

        mock_mcp_client["list_tools"].side_effect = _fail_then_ok

        inputs = {USER_FIELDS: {"query": "hello"}}

        # 第一次：异常透传，锁已释放，api 仍为 None
        with pytest.raises(Exception, match="list_tools boom"):
            await flow_mcp.invoke(inputs, session, None)
        assert flow_mcp.api is None

        # 第二次：锁可用，重试成功
        r = await asyncio.wait_for(
            flow_mcp.invoke(inputs, session, None), timeout=3.0
        )
        assert r[USER_FIELDS]["isError"] is False
        assert flow_mcp.api is not None

    @pytest.mark.asyncio
    async def test_new_version_concurrent_skips_list_tools(self, mock_mcp_client):
        """新版（有 arguments）并发 invoke 不调 list_tools（对照路径）"""
        conf = _make_flow_mcp_conf()  # 默认带 arguments
        flow_mcp = FlowMcp(conf)
        session = create_workflow_session()

        inputs = {USER_FIELDS: {"query": "hello"}}
        results = await asyncio.gather(
            *(flow_mcp.invoke(inputs, session, None) for _ in range(20))
        )

        mock_mcp_client["list_tools"].assert_not_awaited()
        assert mock_mcp_client["call_tool"].await_count == 20
        assert all(r[USER_FIELDS]["isError"] is False for r in results)


# pylint: disable=protected-access

# ─── _format_api_inputs helpers ─────────────────────────────────────


class _MockParam:
    """Mock tool parameter for _format_api_inputs tests"""

    def __init__(self, name, param_type="string", method="Body", required=False, default_value=None):
        self.name = name
        self.type = param_type
        self.method = method
        self.required = required
        self.default_value = default_value


def _make_flow_mcp_for_format(params):
    """Create a FlowMcp instance with mock client and tool_params for _format_api_inputs tests"""
    mcp = FlowMcp.__new__(FlowMcp)
    mcp._conf = {"type": "sse", "url": "http://test", "tool_name": "test_tool"}
    mcp._is_older_version = False
    mcp._header_params = {}
    mock_client = MagicMock()
    mock_client._tool_params = params
    mcp._client = mock_client
    return mcp


# ─── _format_api_inputs: None 值处理 ────────────────────────────────


class TestFormatApiInputsNoneValue:
    """_format_api_inputs 对 None 值的处理

    核心修复：transform_type(None, "string") 会执行 str(None) 返回 "None" 字符串，
    导致 MCP server Pydantic 校验失败。修复后在 transform_type 之前拦截 None。
    """

    @staticmethod
    def test_none_value_object_type_returns_empty_dict():
        """None + object type → {} (not str(None) → "None")"""
        params = [_MockParam("arguments", param_type="object | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"arguments": None})
        assert result["arguments"] == {}

    @staticmethod
    def test_none_value_array_type_returns_empty_list():
        """None + array type → []"""
        params = [_MockParam("items", param_type="array | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"items": None})
        assert result["items"] == []

    @staticmethod
    def test_none_value_string_type_returns_none():
        """None + string type → None (not str(None) → "None")"""
        params = [_MockParam("name", param_type="string", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"name": None})
        assert result["name"] is None

    @staticmethod
    def test_none_value_integer_type_returns_none():
        """None + integer type → None"""
        params = [_MockParam("count", param_type="integer", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"count": None})
        assert result["count"] is None

    @staticmethod
    def test_none_value_boolean_type_returns_none():
        """None + boolean type → None"""
        params = [_MockParam("flag", param_type="boolean", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"flag": None})
        assert result["flag"] is None


# ─── _format_api_inputs: 空字符串处理 ──────────────────────────────


class TestFormatApiInputsEmptyString:
    """_format_api_inputs 对空字符串的处理"""

    @staticmethod
    def test_empty_string_object_type_returns_empty_dict():
        """'' + object type → {}"""
        params = [_MockParam("arguments", param_type="object | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"arguments": ""})
        assert result["arguments"] == {}

    @staticmethod
    def test_empty_string_array_type_returns_empty_list():
        """'' + array type → []"""
        params = [_MockParam("items", param_type="array | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"items": ""})
        assert result["items"] == []

    @staticmethod
    def test_empty_string_string_type_stays_empty():
        """'' + string type → '' (transform_type passes through)"""
        params = [_MockParam("name", param_type="string", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"name": ""})
        assert result["name"] == ""


# ─── _format_api_inputs: 有效值处理 ────────────────────────────────


class TestFormatApiInputsValidValue:
    """_format_api_inputs 对有效值的处理（含 JSON 字符串解析）"""

    @staticmethod
    def test_valid_dict_for_object_type():
        """Valid dict → dict (no transformation needed)"""
        params = [_MockParam("arguments", param_type="object | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"arguments": {"key": "value"}})
        assert result["arguments"] == {"key": "value"}

    @staticmethod
    def test_valid_list_for_array_type():
        """Valid list → list"""
        params = [_MockParam("items", param_type="array | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"items": [1, 2, 3]})
        assert result["items"] == [1, 2, 3]

    @staticmethod
    def test_json_string_for_object_type():
        """JSON string → parsed dict (for object type that comes as string)"""
        params = [_MockParam("arguments", param_type="object | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"arguments": '{"key": "value"}'})
        assert result["arguments"] == {"key": "value"}

    @staticmethod
    def test_json_string_for_array_type():
        """JSON string → parsed list"""
        params = [_MockParam("items", param_type="array | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"items": "[1, 2, 3]"})
        assert result["items"] == [1, 2, 3]

    @staticmethod
    def test_invalid_json_string_for_object_type_keeps_original():
        """Invalid JSON string → kept as-is (no crash)"""
        params = [_MockParam("arguments", param_type="object | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"arguments": "not valid json"})
        assert result["arguments"] == "not valid json"

    @staticmethod
    def test_empty_json_string_for_object_type_returns_empty_dict():
        """'' for object type → {}"""
        params = [_MockParam("arguments", param_type="object | null", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"arguments": ""})
        assert result["arguments"] == {}


# ─── _format_api_inputs: Headers 和异常 ────────────────────────────


class TestFormatApiInputsHeadersAndErrors:
    """_format_api_inputs 的 Headers 提取和参数不存在的场景"""

    @staticmethod
    def test_headers_extracted_separately():
        """method=Headers → extracted to _header_params, not in api_inputs"""
        params = [
            _MockParam("auth_token", param_type="string", method="Headers"),
            _MockParam("query", param_type="string", method="Body"),
        ]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"auth_token": "my_token", "query": "hello world"})
        assert "auth_token" not in result
        assert result["query"] == "hello world"
        assert mcp._header_params["auth_token"] == "my_token"

    @staticmethod
    def test_unknown_param_raises_error():
        """Input param not found in tool_params → raises JiuWenBaseException"""
        params = [_MockParam("query", param_type="string", method="Body")]
        mcp = _make_flow_mcp_for_format(params)
        with pytest.raises(Exception):
            mcp._format_api_inputs({"unknown_param": "value"})


# ─── _format_api_inputs: 回归测试 ──────────────────────────────────


class TestFormatApiInputsRegression:
    """MCP oneOf object|null 完整场景回归"""

    @staticmethod
    def test_mcp_oneof_object_null_full_scenario():
        """MCP 工具 oneOf [object, null] 参数不填 → 不应产生 "None" 字符串"""
        params = [
            _MockParam("query", param_type="string", method="Body", required=True),
            _MockParam("arguments", param_type="object | null", method="Body", required=False),
        ]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"query": "hello", "arguments": None})
        assert result["arguments"] != "None"
        assert result["arguments"] == {}

    @staticmethod
    def test_mcp_optional_string_param_with_none():
        """可选 string 参数为 None → None，不是 "None" 字符串"""
        params = [
            _MockParam("query", param_type="string", method="Body", required=True),
            _MockParam("optional_text", param_type="string", method="Body", required=False),
        ]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({"query": "hello", "optional_text": None})
        assert result["optional_text"] is None

    @staticmethod
    def test_multiple_none_params():
        """多个不同类型的 None 参数"""
        params = [
            _MockParam("query", param_type="string", method="Body"),
            _MockParam("arguments", param_type="object | null", method="Body"),
            _MockParam("items", param_type="array | null", method="Body"),
            _MockParam("count", param_type="integer", method="Body"),
        ]
        mcp = _make_flow_mcp_for_format(params)
        result = mcp._format_api_inputs({
            "query": None, "arguments": None, "items": None, "count": None,
        })
        assert result["query"] is None
        assert result["arguments"] == {}
        assert result["items"] == []
        assert result["count"] is None
