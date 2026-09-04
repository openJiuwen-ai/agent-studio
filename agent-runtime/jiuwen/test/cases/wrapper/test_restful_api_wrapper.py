# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
RestfulApiWrapper 单元测试。

测试范围：
1. 延迟加载机制：_get_tool 延迟获取 Tool 实例
2. 属性委托：所有 property 委托给内部 RestfulApiToolNew
3. invoke / stream 不支持（仅日志记录）
4. ainvoke / astream 委托给内部 RestfulApiToolNew
5. 工具未找到异常
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.wrapper.restful_api_new import (
    RestfulApiCardNew,
    RestfulApiToolNew,
)
from jiuwen.extension.wrapper.restful_api_wrapper import RestfulApiWrapper
from jiuwen.plugin.models.param import Param


def _make_card(**overrides) -> RestfulApiCardNew:
    defaults = dict(
        id="wrapper_test_tool",
        name="wrapper_test_tool",
        description="A test tool for wrapper",
        path="https://example.com/api",
        method="POST",
        params=[],
        response=[],
        headers={"Content-Type": "application/json"},
        auth={},
        query_params={},
        plugin_dependency={},
        async_conf={},
        input_parameters={},
        is_from_ir=True,
        plugin_name="wrapper_test_tool",
        plugin_desc="A test tool for wrapper",
        label="test_label",
        related_info={"logo": "logo.png"},
        status=1,
        principle="test principle",
        user_id="user123",
        file_handler="",
        cert=False,
    )
    defaults.update(overrides)
    return RestfulApiCardNew(**defaults)


def _make_tool(**card_overrides) -> RestfulApiToolNew:
    card = _make_card(**card_overrides)
    return RestfulApiToolNew(card)


class TestLazyLoading:
    def test_tool_not_loaded_on_init(self):
        wrapper = RestfulApiWrapper("tool_123", "agent_456", "session_789")
        assert wrapper._tool is None

    def test_get_tool_loads_on_first_access(self):
        wrapper = RestfulApiWrapper("wrapper_test_tool", "agent_123", "session_456")
        mock_tool = _make_tool()
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
                    "wrapper_test_tool", tag="agent_123", session=mock_session
                )

    def test_get_tool_caches_result(self):
        wrapper = RestfulApiWrapper("wrapper_test_tool", "agent_123", "session_456")
        mock_tool = _make_tool()
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
        wrapper = RestfulApiWrapper("nonexistent_tool", "agent_123", "session_456")
        mock_session = MagicMock()
        with patch("openjiuwen.core.runner.Runner") as mock_runner:
            with patch(
                "openjiuwen.core.session.agent.create_agent_session",
                return_value=mock_session,
            ):
                mock_runner.resource_mgr.get_tool.return_value = None
                with pytest.raises(ValueError, match="Tool not found"):
                    wrapper._get_tool()


class TestPropertyDelegation:
    def _make_wrapper_with_tool(self, **card_overrides):
        tool = _make_tool(**card_overrides)
        wrapper = RestfulApiWrapper(tool.id, "agent_123", "session_456")
        wrapper._tool = tool
        return wrapper, tool

    def test_name_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.name == tool.name

    def test_description_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.description == tool.description

    def test_params_property(self):
        p = Param(name="city", description="city name", param_type="string")
        wrapper, tool = self._make_wrapper_with_tool(params=[p])
        assert wrapper.params == tool.params
        assert len(wrapper.params) == 1
        assert wrapper.params[0].name == "city"

    def test_path_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.path == tool.path

    def test_headers_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.headers == tool.headers

    def test_method_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.method == tool.method

    def test_response_property(self):
        p = Param(name="result", description="result", param_type="string")
        wrapper, tool = self._make_wrapper_with_tool(response=[p])
        assert wrapper.response == tool.response
        assert len(wrapper.response) == 1

    def test_plugin_name_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.plugin_name == tool.plugin_name

    def test_plugin_desc_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.plugin_desc == tool.plugin_desc

    def test_auth_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.auth == tool.auth

    def test_label_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.label == tool.label

    def test_related_info_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.related_info == tool.related_info

    def test_status_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.status == tool.status

    def test_principle_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.principle == tool.principle

    def test_query_params_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.query_params == tool.query_params

    def test_user_id_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.user_id == tool.user_id

    def test_plugin_dependency_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.plugin_dependency == tool.plugin_dependency

    def test_id_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.id == tool.id

    def test_async_conf_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.async_conf == tool.async_conf

    def test_async_switch_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.async_switch == tool.async_switch

    def test_is_from_ir_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.is_from_ir == tool.is_from_ir

    def test_input_parameters_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.input_parameters == tool.input_parameters

    def test_plugin_reade_buffer_size_property(self):
        wrapper, tool = self._make_wrapper_with_tool()
        assert wrapper.plugin_reade_buffer_size == tool.plugin_reade_buffer_size


class TestInvokeNotSupported:
    def test_invoke_logs_error(self):
        wrapper = RestfulApiWrapper("tool_123", "agent_456", "session_789")
        with patch(
            "jiuwen.extension.wrapper.restful_api_wrapper.logger"
        ) as mock_logger:
            wrapper.invoke({"input": "test"})
            mock_logger.error.assert_called_once()
            assert "not support invoke" in mock_logger.error.call_args[0][0]


class TestStreamNotSupported:
    def test_stream_logs_error(self):
        wrapper = RestfulApiWrapper("tool_123", "agent_456", "session_789")
        with patch(
            "jiuwen.extension.wrapper.restful_api_wrapper.logger"
        ) as mock_logger:
            wrapper.stream({"input": "test"})
            mock_logger.error.assert_called_once()
            assert "not support stream" in mock_logger.error.call_args[0][0]


class TestAinvoke:
    @pytest.mark.asyncio
    async def test_ainvoke_delegates_to_tool(self):
        tool = _make_tool()
        wrapper = RestfulApiWrapper(tool.id, "agent_123", "session_456")
        wrapper._tool = tool
        mock_result = {"errCode": 0, "errMessage": "ok", "data": {"key": "value"}}
        with patch.object(
            tool, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ) as mock_ainvoke:
            result = await wrapper.ainvoke({"input": "test"})
            mock_ainvoke.assert_called_once_with({"input": "test"})
            assert result == mock_result

    @pytest.mark.asyncio
    async def test_ainvoke_passes_kwargs(self):
        tool = _make_tool()
        wrapper = RestfulApiWrapper(tool.id, "agent_123", "session_456")
        wrapper._tool = tool
        mock_result = {"errCode": 0, "errMessage": "ok", "data": {}}
        with patch.object(
            tool, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ) as mock_ainvoke:
            await wrapper.ainvoke({"input": "test"}, session_id="s1", extra_key="val")
            mock_ainvoke.assert_called_once_with(
                {"input": "test"}, session_id="s1", extra_key="val"
            )


class TestAstream:
    @pytest.mark.asyncio
    async def test_astream_delegates_to_tool(self):
        tool = _make_tool()
        wrapper = RestfulApiWrapper(tool.id, "agent_123", "session_456")
        wrapper._tool = tool

        async def mock_astream(inputs, **kwargs):
            yield "chunk1"
            yield "chunk2"

        with patch.object(tool, "astream", side_effect=mock_astream):
            chunks = []
            async for chunk in wrapper.astream({"input": "test"}):
                chunks.append(chunk)
            assert chunks == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_astream_empty_stream(self):
        tool = _make_tool()
        wrapper = RestfulApiWrapper(tool.id, "agent_123", "session_456")
        wrapper._tool = tool

        async def mock_astream(inputs, **kwargs):
            return
            yield

        with patch.object(tool, "astream", side_effect=mock_astream):
            chunks = []
            async for chunk in wrapper.astream({"input": "test"}):
                chunks.append(chunk)
            assert chunks == []

    @pytest.mark.asyncio
    async def test_astream_passes_kwargs(self):
        tool = _make_tool()
        wrapper = RestfulApiWrapper(tool.id, "agent_123", "session_456")
        wrapper._tool = tool

        async def mock_astream(inputs, **kwargs):
            assert kwargs.get("session_id") == "s1"
            yield "chunk"

        with patch.object(tool, "astream", side_effect=mock_astream):
            chunks = []
            async for chunk in wrapper.astream({"input": "test"}, session_id="s1"):
                chunks.append(chunk)
            assert chunks == ["chunk"]


class TestIsFromIrKey:
    def test_is_from_ir_key_constant(self):
        assert RestfulApiWrapper.IS_FROM_IR_KEY == "is_from_ir"
