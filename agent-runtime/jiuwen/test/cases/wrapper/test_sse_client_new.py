# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
SSEClientNew 单元测试。

测试范围：
1. flatten_exception_group：异常组展开功能
2. exception_group_to_str_simple：异常组转字符串
3. SSEClientNew：
   - 构造函数与属性初始化
   - connect / disconnect / close 方法
   - _prepare_request_params 请求参数准备
   - _build_mcp_url URL 构建
   - _execute_auth_hook 认证钩子执行
   - list_tools 工具列表获取
   - _process_tools_result 工具结果处理与过滤
   - call_tool 工具调用
   - get_tool_info 工具信息获取
   - _transform_result 结果转换
   - _raise_error 错误处理
"""

import os
from builtins import ExceptionGroup
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.wrapper.sse_client_new import (
    SSEClientNew,
    flatten_exception_group,
    exception_group_to_str_simple,
)
from jiuwen.plugin.common.exception import PluginRestfulAuthException
from openjiuwen.core.foundation.tool.mcp.base import McpServerConfig, McpToolCard


def _make_config(**overrides) -> McpServerConfig:
    defaults = dict(
        server_name="test_server",
        server_path="https://example.com/mcp",
        client_type="sse",
        params={},
        auth_headers={},
        auth_query_params={},
    )
    defaults.update(overrides)
    return McpServerConfig(**defaults)


class TestFlattenExceptionGroup:
    def test_single_exception(self):
        exc = ValueError("test error")
        result = flatten_exception_group(exc)
        assert result == [exc]

    def test_exception_group_single_level(self):
        exc1 = ValueError("error 1")
        exc2 = TypeError("error 2")
        eg = ExceptionGroup("group", [exc1, exc2])
        result = flatten_exception_group(eg)
        assert len(result) == 2
        assert exc1 in result
        assert exc2 in result

    def test_exception_group_nested(self):
        exc1 = ValueError("error 1")
        exc2 = TypeError("error 2")
        exc3 = RuntimeError("error 3")
        inner_group = ExceptionGroup("inner", [exc2, exc3])
        outer_group = ExceptionGroup("outer", [exc1, inner_group])
        result = flatten_exception_group(outer_group)
        assert len(result) == 3
        assert exc1 in result
        assert exc2 in result
        assert exc3 in result

    def test_exception_group_deeply_nested(self):
        exc1 = ValueError("level 1")
        exc2 = TypeError("level 2")
        exc3 = RuntimeError("level 3")
        exc4 = KeyError("level 4")
        g3 = ExceptionGroup("g3", [exc3, exc4])
        g2 = ExceptionGroup("g2", [exc2, g3])
        g1 = ExceptionGroup("g1", [exc1, g2])
        result = flatten_exception_group(g1)
        assert len(result) == 4


class TestExceptionGroupToStrSimple:
    def test_single_exception(self):
        exc = ValueError("test error")
        eg = ExceptionGroup("group", [exc])
        result = exception_group_to_str_simple(eg)
        assert "ValueError" in result
        assert "test error" in result

    def test_multiple_exceptions(self):
        exc1 = ValueError("error 1")
        exc2 = TypeError("error 2")
        eg = ExceptionGroup("group", [exc1, exc2])
        result = exception_group_to_str_simple(eg)
        assert "ValueError" in result
        assert "TypeError" in result
        assert "error 1" in result
        assert "error 2" in result

    def test_nested_exceptions(self):
        exc1 = ValueError("outer error")
        exc2 = TypeError("inner error")
        inner = ExceptionGroup("inner", [exc2])
        outer = ExceptionGroup("outer", [exc1, inner])
        result = exception_group_to_str_simple(outer)
        assert "ValueError" in result
        assert "TypeError" in result


class TestSSEClientNewConstruction:
    def test_basic_construction(self):
        config = _make_config()
        client = SSEClientNew(config)
        assert client._config is config
        assert client._server_path == "https://example.com/mcp"
        assert client._name == "test_server"
        assert client._plugin_dependency == {}
        assert client._tool_params == []
        assert client._mcp_choose_tools is None
        assert client._auth == {}
        assert client._auth_headers == {}
        assert client._auth_query_params == {}

    def test_construction_with_params(self):
        config = _make_config(
            params={
                "plugin_dependency": {"dep": "v1"},
                "tool_params": [{"name": "param1"}],
                "mcp_choose_tools": ["tool1", "tool2"],
                "auth": {"scope": "SERVICE"},
            },
            auth_headers={"X-Auth": "token123"},
            auth_query_params={"api_key": "key123"},
        )
        client = SSEClientNew(config)
        assert client._plugin_dependency == {"dep": "v1"}
        assert client._tool_params == [{"name": "param1"}]
        assert client._mcp_choose_tools == ["tool1", "tool2"]
        assert client._auth == {"scope": "SERVICE"}
        assert client._auth_headers == {"X-Auth": "token123"}
        assert client._auth_query_params == {"api_key": "key123"}

    def test_client_name_attribute(self):
        config = _make_config()
        client = SSEClientNew(config)
        assert client.__client_name__ == "sse_new"

    def test_cert_default_true(self):
        config = _make_config()
        client = SSEClientNew(config)
        assert client._cert is True

    def test_cert_from_env_true(self):
        with patch.dict(os.environ, {"PLUGIN_SSL_API_CERT": "true"}):
            config = _make_config()
            client = SSEClientNew(config)
            assert client._cert is True

    def test_cert_from_env_false(self):
        with patch.dict(os.environ, {"PLUGIN_SSL_API_CERT": "false"}):
            config = _make_config()
            client = SSEClientNew(config)
            assert client._cert is False


class TestConnectDisconnectClose:
    @pytest.mark.asyncio
    async def test_connect_returns_true(self):
        config = _make_config()
        client = SSEClientNew(config)
        result = await client.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_with_retry_times(self):
        config = _make_config()
        client = SSEClientNew(config)
        result = await client.connect(retry_times=3)
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_returns_true(self):
        config = _make_config()
        client = SSEClientNew(config)
        result = await client.disconnect()
        assert result is True

    @pytest.mark.asyncio
    async def test_close_returns_disconnect_result(self):
        config = _make_config()
        client = SSEClientNew(config)
        result = await client.close()
        assert result is True


class TestPrepareRequestParams:
    def test_basic_prepare(self):
        config = _make_config()
        client = SSEClientNew(config)
        with patch(
            "jiuwen.extension.wrapper.sse_client_new.get_x_request_id",
            return_value="req-123",
        ):
            with patch(
                "jiuwen.extension.wrapper.sse_client_new.get_x_execution_id",
                return_value="exec-456",
            ):
                rp = client._prepare_request_params(
                    inputs={"arg1": "value1"}, name="test_tool"
                )
                assert rp is not None
                assert rp.headers.get("x-request-id") == "req-123"
                assert rp.headers.get("x-execution-id") == "exec-456"

    def test_prepare_with_empty_inputs(self):
        config = _make_config()
        client = SSEClientNew(config)
        with patch(
            "jiuwen.extension.wrapper.sse_client_new.get_x_request_id",
            return_value="req-123",
        ):
            with patch(
                "jiuwen.extension.wrapper.sse_client_new.get_x_execution_id",
                return_value="exec-456",
            ):
                rp = client._prepare_request_params(inputs=None, name="test_tool")
                assert rp is not None

    def test_prepare_with_auth_headers(self):
        config = _make_config(auth_headers={"Authorization": "Bearer token"})
        client = SSEClientNew(config)
        with patch(
            "jiuwen.extension.wrapper.sse_client_new.get_x_request_id",
            return_value="req-123",
        ):
            with patch(
                "jiuwen.extension.wrapper.sse_client_new.get_x_execution_id",
                return_value="exec-456",
            ):
                rp = client._prepare_request_params(inputs={}, name="test_tool")
                assert "Authorization" in rp.headers


class TestBuildMcpUrl:
    def test_basic_url(self):
        config = _make_config()
        client = SSEClientNew(config)
        rp = MagicMock()
        rp.ip_address_url = "https://example.com/mcp"
        rp.query_params_in_inputs = {}
        url = client._build_mcp_url(rp)
        assert url == "https://example.com/mcp"

    def test_url_with_query_params(self):
        config = _make_config()
        client = SSEClientNew(config)
        rp = MagicMock()
        rp.ip_address_url = "https://example.com/mcp"
        rp.query_params_in_inputs = {"key": "value", "id": "123"}
        url = client._build_mcp_url(rp)
        assert "key=value" in url
        assert "id=123" in url
        assert "?" in url

    def test_url_with_existing_query_params(self):
        config = _make_config()
        client = SSEClientNew(config)
        rp = MagicMock()
        rp.ip_address_url = "https://example.com/mcp?existing=param"
        rp.query_params_in_inputs = {"new_key": "new_value"}
        url = client._build_mcp_url(rp)
        assert "existing=param" in url
        assert "new_key=new_value" in url
        assert "&" in url


class TestExecuteAuthHook:
    def test_no_hook_function(self):
        config = _make_config(params={"plugin_dependency": {}})
        client = SSEClientNew(config)
        rp = MagicMock()
        rp.headers = {}
        rp.query_params_in_inputs = {}
        client._execute_auth_hook(rp, "test_tool")

    def test_hook_function_not_found(self):
        config = _make_config(
            params={
                "plugin_dependency": {
                    "hook_function": {"mcp_auth": "nonexistent.module.function"}
                }
            }
        )
        client = SSEClientNew(config)
        rp = MagicMock()
        rp.headers = {}
        rp.query_params_in_inputs = {}
        with patch(
            "jiuwen.extension.wrapper.sse_client_new.ApiUtils.get_hook_func",
            return_value=None,
        ):
            client._execute_auth_hook(rp, "test_tool")

    def test_hook_function_execution_success(self):
        config = _make_config(
            params={
                "plugin_dependency": {
                    "hook_function": {"mcp_auth": "test.module.auth_func"}
                },
                "auth": {"scope": "SERVICE"},
            }
        )
        client = SSEClientNew(config)
        rp = MagicMock()
        rp.headers = {}
        rp.query_params_in_inputs = {}
        mock_auth_provider = MagicMock()
        with patch(
            "jiuwen.extension.wrapper.sse_client_new.ApiUtils.get_hook_func",
            return_value=mock_auth_provider,
        ):
            client._execute_auth_hook(rp, "test_tool")
            mock_auth_provider.assert_called_once()

    def test_hook_function_execution_error(self):
        config = _make_config(
            params={
                "plugin_dependency": {
                    "hook_function": {"mcp_auth": "test.module.auth_func"}
                }
            }
        )
        client = SSEClientNew(config)
        rp = MagicMock()
        rp.headers = {}
        rp.query_params_in_inputs = {}
        mock_auth_provider = MagicMock(side_effect=RuntimeError("auth failed"))
        with patch(
            "jiuwen.extension.wrapper.sse_client_new.ApiUtils.get_hook_func",
            return_value=mock_auth_provider,
        ):
            client._execute_auth_hook(rp, "test_tool")


class TestProcessToolsResult:
    def test_empty_result(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_result = MagicMock()
        mock_result.tools = []
        tools = client._process_tools_result(mock_result)
        assert tools == []

    def test_single_tool(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_tool = MagicMock()
        mock_tool.name = "tool1"
        mock_tool.description = "A test tool"
        mock_tool.inputSchema = {"type": "object"}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        tools = client._process_tools_result(mock_result)
        assert len(tools) == 1
        assert tools[0].name == "tool1"
        assert tools[0].server_name == "test_server"
        assert tools[0].description == "A test tool"

    def test_multiple_tools(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_tools = []
        for i in range(3):
            t = MagicMock()
            t.name = f"tool{i}"
            t.description = f"Tool {i}"
            t.inputSchema = {"type": "object"}
            mock_tools.append(t)
        mock_result = MagicMock()
        mock_result.tools = mock_tools
        tools = client._process_tools_result(mock_result)
        assert len(tools) == 3

    def test_filter_with_mcp_choose_tools(self):
        config = _make_config(params={"mcp_choose_tools": ["tool1", "tool3"]})
        client = SSEClientNew(config)
        mock_tools = []
        for i in range(4):
            t = MagicMock()
            t.name = f"tool{i}"
            t.description = f"Tool {i}"
            t.inputSchema = {}
            mock_tools.append(t)
        mock_result = MagicMock()
        mock_result.tools = mock_tools
        tools = client._process_tools_result(mock_result)
        assert len(tools) == 2
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool3"

    def test_filter_with_empty_mcp_choose_tools(self):
        config = _make_config(params={"mcp_choose_tools": []})
        client = SSEClientNew(config)
        mock_tool = MagicMock()
        mock_tool.name = "tool1"
        mock_tool.description = "Tool"
        mock_tool.inputSchema = {}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        tools = client._process_tools_result(mock_result)
        assert len(tools) == 0

    def test_none_result(self):
        config = _make_config()
        client = SSEClientNew(config)
        tools = client._process_tools_result(None)
        assert tools == []

    def test_tool_without_description(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_tool = MagicMock(spec=["name", "inputSchema"])
        mock_tool.name = "tool_no_desc"
        mock_tool.inputSchema = {}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        tools = client._process_tools_result(mock_result)
        assert len(tools) == 1
        assert tools[0].description == ""


class TestTransformResult:
    def test_structured_content(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_result = MagicMock()
        mock_result.structuredContent = {"key": "value"}
        mock_result.content = None
        result = client._transform_result(mock_result)
        assert result == {"key": "value"}

    def test_content_without_structured_content(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_result = MagicMock()
        del mock_result.structuredContent
        mock_result.content = [{"type": "text", "text": "result"}]
        result = client._transform_result(mock_result)
        assert result == [{"type": "text", "text": "result"}]

    def test_empty_structured_content_falls_back(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_result = MagicMock()
        mock_result.structuredContent = None
        mock_result.content = [{"type": "text", "text": "fallback"}]
        result = client._transform_result(mock_result)
        assert result == [{"type": "text", "text": "fallback"}]

    def test_no_content_attributes(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_result = MagicMock(spec=[])
        result = client._transform_result(mock_result)
        assert result is mock_result


class TestRaiseError:
    def test_raises_auth_exception(self):
        config = _make_config(server_name="my_server")
        client = SSEClientNew(config)
        with pytest.raises(PluginRestfulAuthException):
            client._raise_error("test error")

    def test_error_message_includes_server_name(self):
        config = _make_config(server_name="my_server")
        client = SSEClientNew(config)
        with pytest.raises(PluginRestfulAuthException) as exc_info:
            client._raise_error("auth failed")
        assert "my_server" in exc_info.value.message


class TestListTools:
    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "desc"
        mock_tool.inputSchema = {}
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        with patch("jiuwen.extension.wrapper.sse_client_new.sse_client") as mock_sse:
            mock_sse.return_value.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock())
            )
            mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "jiuwen.extension.wrapper.sse_client_new.ClientSession",
                return_value=mock_session,
            ):
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                tools = await client.list_tools()
                assert len(tools) == 1
                assert tools[0].name == "test_tool"

    @pytest.mark.asyncio
    async def test_list_tools_exception_group(self):
        config = _make_config()
        client = SSEClientNew(config)
        with patch("jiuwen.extension.wrapper.sse_client_new.sse_client") as mock_sse:
            exc1 = ValueError("error 1")
            exc2 = TypeError("error 2")
            eg = ExceptionGroup("test", [exc1, exc2])
            mock_sse.return_value.__aenter__ = AsyncMock(side_effect=eg)
            mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)
            tools = await client.list_tools()
            assert tools == []

    @pytest.mark.asyncio
    async def test_list_tools_general_exception(self):
        config = _make_config()
        client = SSEClientNew(config)
        with patch("jiuwen.extension.wrapper.sse_client_new.sse_client") as mock_sse:
            mock_sse.return_value.__aenter__ = AsyncMock(
                side_effect=RuntimeError("connection failed")
            )
            mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)
            tools = await client.list_tools()
            assert tools == []


class TestCallTool:
    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = [{"type": "text", "text": "result"}]
        del mock_result.structuredContent
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        with patch("jiuwen.extension.wrapper.sse_client_new.sse_client") as mock_sse:
            mock_sse.return_value.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock())
            )
            mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "jiuwen.extension.wrapper.sse_client_new.ClientSession",
                return_value=mock_session,
            ):
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                result = await client.call_tool("test_tool", {"arg": "value"})
                assert result == [{"type": "text", "text": "result"}]

    @pytest.mark.asyncio
    async def test_call_tool_with_structured_content(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_result = MagicMock()
        mock_result.structuredContent = {"data": "structured"}
        mock_result.content = None
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        with patch("jiuwen.extension.wrapper.sse_client_new.sse_client") as mock_sse:
            mock_sse.return_value.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock())
            )
            mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "jiuwen.extension.wrapper.sse_client_new.ClientSession",
                return_value=mock_session,
            ):
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                result = await client.call_tool("test_tool", {"arg": "value"})
                assert result == {"data": "structured"}


class TestGetToolInfo:
    @pytest.mark.asyncio
    async def test_get_tool_info_found(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_tool = McpToolCard(
            name="target_tool",
            server_name="test_server",
            description="Target tool",
            input_params={},
        )
        with patch.object(
            client, "list_tools", new_callable=AsyncMock, return_value=[mock_tool]
        ):
            result = await client.get_tool_info("target_tool")
            assert result is mock_tool

    @pytest.mark.asyncio
    async def test_get_tool_info_not_found(self):
        config = _make_config()
        client = SSEClientNew(config)
        mock_tool = McpToolCard(
            name="other_tool",
            server_name="test_server",
            description="Other tool",
            input_params={},
        )
        with patch.object(
            client, "list_tools", new_callable=AsyncMock, return_value=[mock_tool]
        ):
            result = await client.get_tool_info("target_tool")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_tool_info_empty_list(self):
        config = _make_config()
        client = SSEClientNew(config)
        with patch.object(
            client, "list_tools", new_callable=AsyncMock, return_value=[]
        ):
            result = await client.get_tool_info("any_tool")
            assert result is None
