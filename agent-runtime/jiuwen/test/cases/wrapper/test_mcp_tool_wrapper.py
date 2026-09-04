# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
McpToolWrapper 单元测试。

测试范围：
1. flatten_exception_group：异常组展开功能
2. exception_group_to_str_simple：异常组转字符串
3. McpToolWrapper：
   - 构造函数与延迟加载
   - 属性委托
   - invoke（不支持）
   - ainvoke 异步调用
   - _convert_result 结果转换
   - _create_error_response 错误响应创建
   - _create_tracer_manager 追踪管理器创建
"""

from builtins import ExceptionGroup
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.extension.wrapper.mcp_tool_wrapper import (
    McpToolWrapper,
    flatten_exception_group,
    exception_group_to_str_simple,
)
from jiuwen.plugin.common import constant


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


class TestMcpToolWrapperConstruction:
    def test_basic_construction(self):
        wrapper = McpToolWrapper("tool_123", "agent_456", "session_789")
        assert wrapper._tool_id == "tool_123"
        assert wrapper._agent_id == "agent_456"
        assert wrapper._session_id == "session_789"
        assert wrapper._tool is None

    def test_tool_not_loaded_on_init(self):
        wrapper = McpToolWrapper("tool_123", "agent_456", "session_789")
        assert wrapper._tool is None


class TestLazyLoading:
    def test_get_tool_loads_on_first_access(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_tool = MagicMock()
        mock_tool.card.name = "test_tool"
        mock_tool.card.description = "A test tool"
        mock_tool.card.server_name = "test_server"
        mock_tool.card.input_params = {}
        mock_session = MagicMock()
        with patch("openjiuwen.core.runner.Runner") as mock_runner:
            with patch(
                "openjiuwen.core.session.agent.create_agent_session",
                return_value=mock_session,
            ) as mock_create_session:
                mock_runner.resource_mgr.get_tool.return_value = mock_tool
                tool = wrapper._get_tool()
                assert tool is mock_tool
                mock_create_session.assert_called_once_with(session_id="session_456")
                mock_runner.resource_mgr.get_tool.assert_called_once_with(
                    "test_tool", tag="agent_123", session=mock_session
                )

    def test_get_tool_caches_result(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_tool = MagicMock()
        mock_tool.card.name = "test_tool"
        mock_tool.card.description = "desc"
        mock_tool.card.server_name = "server"
        mock_tool.card.input_params = {}
        mock_session = MagicMock()
        with patch("openjiuwen.core.runner.Runner") as mock_runner:
            with patch(
                "openjiuwen.core.session.agent.create_agent_session",
                return_value=mock_session,
            ):
                mock_runner.resource_mgr.get_tool.return_value = mock_tool
                tool1 = wrapper._get_tool()
                tool2 = wrapper._get_tool()
                assert tool1 is tool2
                assert mock_runner.resource_mgr.get_tool.call_count == 1

    def test_get_tool_not_found_raises(self):
        wrapper = McpToolWrapper("nonexistent_tool", "agent_123", "session_456")
        mock_session = MagicMock()
        with patch("openjiuwen.core.runner.Runner") as mock_runner:
            with patch(
                "openjiuwen.core.session.agent.create_agent_session",
                return_value=mock_session,
            ):
                mock_runner.resource_mgr.get_tool.return_value = None
                with pytest.raises(ValueError, match="MCP Tool not found"):
                    wrapper._get_tool()


class TestPropertyDelegation:
    def _make_wrapper_with_tool(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_tool = MagicMock()
        mock_tool.card.name = "test_tool"
        mock_tool.card.description = "A test tool"
        mock_tool.card.server_name = "test_server"
        mock_tool.card.input_params = {"param1": "value1"}
        mock_tool.card.properties = {}
        wrapper._tool = mock_tool
        return wrapper, mock_tool

    def test_name_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.name == "test_tool"

    def test_description_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.description == "A test tool"

    def test_server_name_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.server_name == "test_server"

    def test_parameters_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.parameters == {"param1": "value1"}

    def test_headers_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.headers == {}

    def test_auth_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.auth == {}

    def test_plugin_dependency_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.plugin_dependency == {}

    def test_params_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.params == []

    def test_is_mcp_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.is_mcp is True


class TestInvokeNotSupported:
    def test_invoke_logs_error(self):
        wrapper = McpToolWrapper("tool_123", "agent_456", "session_789")
        with patch("jiuwen.extension.wrapper.mcp_tool_wrapper.logger") as mock_logger:
            wrapper.invoke({"input": "test"})
            mock_logger.error.assert_called_once()
            assert "not support invoke" in mock_logger.error.call_args[0][0]


class TestConvertResult:
    def test_convert_result_with_data(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        result = {"result": {"key": "value"}}
        converted = wrapper._convert_result(result)
        assert converted[constant.ERR_CODE] == 0
        assert converted[constant.ERR_MESSAGE] == "success"
        assert converted[constant.RESTFUL_DATA] == {"key": "value"}

    def test_convert_result_with_none(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        result = {"result": None}
        converted = wrapper._convert_result(result)
        assert converted[constant.ERR_CODE] == 0
        assert converted[constant.RESTFUL_DATA] is None

    def test_convert_result_with_string(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        result = {"result": "output string"}
        converted = wrapper._convert_result(result)
        assert converted[constant.ERR_CODE] == 0
        assert converted[constant.RESTFUL_DATA] == "output string"

    def test_convert_result_with_list(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        result = {"result": [1, 2, 3]}
        converted = wrapper._convert_result(result)
        assert converted[constant.ERR_CODE] == 0
        assert converted[constant.RESTFUL_DATA] == [1, 2, 3]


class TestCreateErrorResponse:
    def test_error_response_with_exception(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        error = RuntimeError("something went wrong")
        response = wrapper._create_error_response(error)
        assert response[constant.ERR_CODE] == StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code
        assert "Exception" in response[constant.ERR_MESSAGE]

    def test_error_response_with_exception_group(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        exc1 = ValueError("error 1")
        exc2 = TypeError("error 2")
        eg = ExceptionGroup("test", [exc1, exc2])
        response = wrapper._create_error_response(eg)
        assert response[constant.ERR_CODE] == StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code
        assert "ExceptionGroup" in response[constant.ERR_MESSAGE]

    def test_error_response_data_is_empty_string(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        error = ValueError("test error")
        response = wrapper._create_error_response(error)
        assert response[constant.RESTFUL_DATA] == ""


class TestAinvoke:
    @pytest.mark.asyncio
    async def test_ainvoke_success(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_tool = MagicMock()
        mock_tool.invoke = AsyncMock(return_value={"result": {"data": "value"}})
        mock_tool.card.name = "test_tool"
        mock_tool.card.description = "desc"
        mock_tool.card.server_name = "server"
        mock_tool.card.input_params = {}
        wrapper._tool = mock_tool
        with patch.object(wrapper, "_create_tracer_manager") as mock_tracer:
            mock_tracer.return_value.on_plugin_start = MagicMock()
            mock_tracer.return_value.on_plugin_end = MagicMock()
            result = await wrapper.ainvoke({"input": "test"})
            assert result[constant.ERR_CODE] == 0
            assert result[constant.RESTFUL_DATA] == {"data": "value"}

    @pytest.mark.asyncio
    async def test_ainvoke_with_exception(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_tool = MagicMock()
        mock_tool.invoke = AsyncMock(side_effect=RuntimeError("tool error"))
        mock_tool.card.name = "test_tool"
        mock_tool.card.description = "desc"
        mock_tool.card.server_name = "server"
        mock_tool.card.input_params = {}
        wrapper._tool = mock_tool
        with patch.object(wrapper, "_create_tracer_manager") as mock_tracer:
            mock_tracer.return_value.on_plugin_start = MagicMock()
            mock_tracer.return_value.on_plugin_error = MagicMock()
            result = await wrapper.ainvoke({"input": "test"})
            assert (
                result[constant.ERR_CODE] == StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code
            )

    @pytest.mark.asyncio
    async def test_ainvoke_with_exception_group(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_tool = MagicMock()
        exc1 = ValueError("error 1")
        exc2 = TypeError("error 2")
        eg = ExceptionGroup("test", [exc1, exc2])
        mock_tool.invoke = AsyncMock(side_effect=eg)
        mock_tool.card.name = "test_tool"
        mock_tool.card.description = "desc"
        mock_tool.card.server_name = "server"
        mock_tool.card.input_params = {}
        wrapper._tool = mock_tool
        with patch.object(wrapper, "_create_tracer_manager") as mock_tracer:
            mock_tracer.return_value.on_plugin_start = MagicMock()
            mock_tracer.return_value.on_plugin_error = MagicMock()
            result = await wrapper.ainvoke({"input": "test"})
            assert (
                result[constant.ERR_CODE] == StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code
            )
            assert "ExceptionGroup" in result[constant.ERR_MESSAGE]

    @pytest.mark.asyncio
    async def test_ainvoke_passes_kwargs(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_tool = MagicMock()
        mock_tool.invoke = AsyncMock(return_value={"result": "ok"})
        mock_tool.card.name = "test_tool"
        mock_tool.card.description = "desc"
        mock_tool.card.server_name = "server"
        mock_tool.card.input_params = {}
        wrapper._tool = mock_tool
        with patch.object(wrapper, "_create_tracer_manager") as mock_tracer:
            mock_tracer.return_value.on_plugin_start = MagicMock()
            mock_tracer.return_value.on_plugin_end = MagicMock()
            await wrapper.ainvoke({"input": "test"}, session_id="s1", extra_key="val")
            mock_tool.invoke.assert_called_once_with(
                {
                    "input": "test",
                    "_jiuwen_runtime_kwargs": {"session_id": "s1", "extra_key": "val"},
                },
                session_id="s1",
                extra_key="val",
            )


class TestCreateTracerManager:
    def test_create_tracer_manager(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        with patch("jiuwen.extension.wrapper.mcp_tool_wrapper.TraceManager") as mock_tm:
            mock_tm.generate_manager.return_value = MagicMock()
            manager = wrapper._create_tracer_manager()
            assert manager is not None
            mock_tm.generate_manager.assert_called_once()

    def test_create_tracer_manager_with_handlers(self):
        wrapper = McpToolWrapper("test_tool", "agent_123", "session_456")
        mock_handlers = [MagicMock()]
        with patch("jiuwen.extension.wrapper.mcp_tool_wrapper.TraceManager") as mock_tm:
            mock_tm.generate_manager.return_value = MagicMock()
            manager = wrapper._create_tracer_manager(trace_handlers=mock_handlers)
            assert manager is not None
