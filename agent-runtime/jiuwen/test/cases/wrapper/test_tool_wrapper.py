# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
ToolWrapper 单元测试。

测试范围：
1. 基本功能：创建不同类型的 ToolWrapper
2. 特殊属性：is_restful, is_mcp, tool_type
3. __getattr__ 魔术方法：动态属性访问
4. 公共属性访问：name, description, headers, auth, plugin_dependency
5. RestfulApiWrapper 独有属性访问
6. McpToolWrapper 独有属性访问
7. 属性不存在时的错误处理
8. 公共方法：invoke, ainvoke, stream, astream
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.wrapper import ToolWrapper, ToolType


class MockInput:
    def __init__(self, data):
        self.data = data


class MockOutput:
    def __init__(self, data):
        self.data = data


class TestToolWrapperBasic:
    """测试 ToolWrapper 基本功能"""

    def test_create_restful_wrapper(self):
        """测试创建 restful 类型的 ToolWrapper"""
        wrapper = ToolWrapper(
            tool_id="test_tool_id",
            agent_id="test_agent_id",
            session_id="test_session_id",
            tool_type=ToolType.RESTFUL,
        )
        assert wrapper.tool_type == ToolType.RESTFUL
        assert wrapper.is_restful is True
        assert wrapper.is_mcp is False

    def test_create_mcp_wrapper(self):
        """测试创建 mcp 类型的 ToolWrapper"""
        wrapper = ToolWrapper(
            tool_id="test_tool_id",
            agent_id="test_agent_id",
            session_id="test_session_id",
            tool_type=ToolType.MCP,
        )
        assert wrapper.tool_type == ToolType.MCP
        assert wrapper.is_restful is False
        assert wrapper.is_mcp is True

    def test_default_tool_type(self):
        """测试默认工具类型为 restful"""
        wrapper = ToolWrapper(
            tool_id="test_tool_id",
            agent_id="test_agent_id",
            session_id="test_session_id",
        )
        assert wrapper.tool_type == ToolType.RESTFUL
        assert wrapper.is_restful is True

    def test_string_tool_type_backward_compat(self):
        """测试字符串 tool_type 向后兼容"""
        restful_wrapper = ToolWrapper(
            tool_id="test_tool_id",
            agent_id="test_agent_id",
            session_id="test_session_id",
            tool_type="restful",
        )
        assert restful_wrapper.tool_type == ToolType.RESTFUL
        assert restful_wrapper.is_restful is True

        mcp_wrapper = ToolWrapper(
            tool_id="test_tool_id",
            agent_id="test_agent_id",
            session_id="test_session_id",
            tool_type="mcp",
        )
        assert mcp_wrapper.tool_type == ToolType.MCP
        assert mcp_wrapper.is_mcp is True

    def test_invalid_tool_type(self):
        """测试无效的工具类型"""
        with pytest.raises(ValueError, match="invalid_type"):
            ToolWrapper(
                tool_id="test_tool_id",
                agent_id="test_agent_id",
                session_id="test_session_id",
                tool_type="invalid_type",
            )


class TestToolWrapperSpecialProperties:
    """测试 ToolWrapper 特殊属性"""

    def test_is_restful_property(self):
        """测试 is_restful 属性"""
        restful_wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)
        mcp_wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        assert restful_wrapper.is_restful is True
        assert mcp_wrapper.is_restful is False

    def test_is_mcp_property(self):
        """测试 is_mcp 属性"""
        restful_wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)
        mcp_wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        assert restful_wrapper.is_mcp is False
        assert mcp_wrapper.is_mcp is True

    def test_tool_type_property(self):
        """测试 tool_type 属性"""
        restful_wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)
        mcp_wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        assert restful_wrapper.tool_type == ToolType.RESTFUL
        assert mcp_wrapper.tool_type == ToolType.MCP


class TestToolWrapperGetAttr:
    """测试 __getattr__ 魔术方法"""

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    def test_getattr_restful_public_attributes(self, mock_restful_wrapper):
        """测试 restful 类型访问公共属性"""
        mock_instance = MagicMock()
        mock_instance.name = "test_name"
        mock_instance.description = "test_description"
        mock_instance.headers = {"key": "value"}
        mock_instance.auth = {"type": "bearer"}
        mock_instance.plugin_dependency = {"plugin": "test"}
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        assert wrapper.name == "test_name"
        assert wrapper.description == "test_description"
        assert wrapper.headers == {"key": "value"}
        assert wrapper.auth == {"type": "bearer"}
        assert wrapper.plugin_dependency == {"plugin": "test"}

    @patch("jiuwen.extension.wrapper.mcp_tool_wrapper.McpToolWrapper")
    def test_getattr_mcp_public_attributes(self, mock_mcp_wrapper):
        """测试 mcp 类型访问公共属性"""
        mock_instance = MagicMock()
        mock_instance.name = "mcp_name"
        mock_instance.description = "mcp_description"
        mock_instance.headers = {"key": "value"}
        mock_instance.auth = {"type": "basic"}
        mock_instance.plugin_dependency = {"plugin": "mcp"}
        mock_mcp_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        assert wrapper.name == "mcp_name"
        assert wrapper.description == "mcp_description"
        assert wrapper.headers == {"key": "value"}
        assert wrapper.auth == {"type": "basic"}
        assert wrapper.plugin_dependency == {"plugin": "mcp"}

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    def test_getattr_restful_unique_attributes(self, mock_restful_wrapper):
        """测试 restful 独有属性访问"""
        mock_instance = MagicMock()
        mock_instance.params = [{"name": "param1"}]
        mock_instance.path = "/api/test"
        mock_instance.method = "POST"
        mock_instance.response = [{"name": "result"}]
        mock_instance.plugin_name = "test_plugin"
        mock_instance.plugin_desc = "Test plugin description"
        mock_instance.label = "test_label"
        mock_instance.related_info = {"key": "value"}
        mock_instance.status = 1
        mock_instance.principle = "test principle"
        mock_instance.query_params = {"q": "test"}
        mock_instance.user_id = "user123"
        mock_instance.id = "tool_id_123"
        mock_instance.async_conf = {"timeout": 30}
        mock_instance.async_switch = True
        mock_instance.is_from_ir = True
        mock_instance.input_parameters = {"param": "value"}
        mock_instance.plugin_reade_buffer_size = 1024
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        assert wrapper.params == [{"name": "param1"}]
        assert wrapper.path == "/api/test"
        assert wrapper.method == "POST"
        assert wrapper.response == [{"name": "result"}]
        assert wrapper.plugin_name == "test_plugin"
        assert wrapper.plugin_desc == "Test plugin description"
        assert wrapper.label == "test_label"
        assert wrapper.related_info == {"key": "value"}
        assert wrapper.status == 1
        assert wrapper.principle == "test principle"
        assert wrapper.query_params == {"q": "test"}
        assert wrapper.user_id == "user123"
        assert wrapper.id == "tool_id_123"
        assert wrapper.async_conf == {"timeout": 30}
        assert wrapper.async_switch is True
        assert wrapper.is_from_ir is True
        assert wrapper.input_parameters == {"param": "value"}
        assert wrapper.plugin_reade_buffer_size == 1024

    @patch("jiuwen.extension.wrapper.mcp_tool_wrapper.McpToolWrapper")
    def test_getattr_mcp_unique_attributes(self, mock_mcp_wrapper):
        """测试 mcp 独有属性访问"""
        mock_instance = MagicMock()
        mock_instance.server_name = "test_server"
        mock_instance.parameters = {"param1": "value1"}
        mock_instance.is_mcp = True
        mock_mcp_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        assert wrapper.server_name == "test_server"
        assert wrapper.parameters == {"param1": "value1"}
        assert wrapper.is_mcp is True

    @patch("jiuwen.extension.wrapper.mcp_tool_wrapper.McpToolWrapper")
    def test_getattr_restful_attribute_on_mcp_wrapper(self, mock_mcp_wrapper, caplog):
        """测试在 mcp 类型上访问 restful 独有属性"""
        mock_instance = MagicMock(spec=["name"])
        mock_instance.name = "mcp_name"
        mock_mcp_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        result = wrapper.path
        assert result is None

        assert any(
            "Attribute 'path' is not" in record.message for record in caplog.records
        )

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    def test_getattr_mcp_attribute_on_restful_wrapper(
        self, mock_restful_wrapper, caplog
    ):
        """测试在 restful 类型上访问 mcp 独有属性"""
        mock_instance = MagicMock(spec=["name"])
        mock_instance.name = "restful_name"
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        result = wrapper.server_name
        assert result is None

        assert any(
            "Attribute 'server_name' is not" in record.message
            for record in caplog.records
        )

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    def test_getattr_nonexistent_attribute(self, mock_restful_wrapper, caplog):
        """测试访问不存在的属性"""
        mock_instance = MagicMock(spec=["name"])
        mock_instance.name = "test_name"
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        result = wrapper.nonexistent_attribute
        assert result is None

        assert any(
            "Attribute 'nonexistent_attribute' is not" in record.message
            for record in caplog.records
        )


class TestToolWrapperMethods:
    """测试 ToolWrapper 公共方法"""

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    def test_invoke_method(self, mock_restful_wrapper):
        """测试 invoke 方法"""
        mock_instance = MagicMock()
        mock_result = MockOutput(data="test_result")
        mock_instance.invoke.return_value = mock_result
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        inputs = MockInput(data="test_input")
        result = wrapper.invoke(inputs)

        assert result.data == "test_result"
        mock_instance.invoke.assert_called_once_with(inputs)

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    @pytest.mark.asyncio
    async def test_ainvoke_method(self, mock_restful_wrapper):
        """测试 ainvoke 方法"""
        mock_instance = MagicMock()
        mock_result = MockOutput(data="async_result")
        mock_instance.ainvoke = AsyncMock(return_value=mock_result)
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        inputs = MockInput(data="test_input")
        result = await wrapper.ainvoke(inputs)

        assert result.data == "async_result"
        mock_instance.ainvoke.assert_called_once_with(inputs)

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    def test_stream_method_restful(self, mock_restful_wrapper):
        """测试 restful 类型的 stream 方法"""
        mock_instance = MagicMock()
        mock_instance.stream.return_value = iter(
            [MockOutput(data="chunk1"), MockOutput(data="chunk2")]
        )
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        inputs = MockInput(data="test_input")
        result = wrapper.stream(inputs)

        chunks = list(result)
        assert len(chunks) == 2
        assert chunks[0].data == "chunk1"
        assert chunks[1].data == "chunk2"
        mock_instance.stream.assert_called_once_with(inputs)

    @patch("jiuwen.extension.wrapper.mcp_tool_wrapper.McpToolWrapper")
    def test_stream_method_mcp(self, mock_mcp_wrapper, caplog):
        """测试 mcp 类型的 stream 方法（不支持）"""
        mock_instance = MagicMock()
        mock_mcp_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        inputs = MockInput(data="test_input")
        result = wrapper.stream(inputs)

        chunks = list(result)
        assert len(chunks) == 0

        assert any(
            "stream() is not available" in record.message for record in caplog.records
        )

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    @pytest.mark.asyncio
    async def test_astream_method_restful(self, mock_restful_wrapper):
        """测试 restful 类型的 astream 方法"""

        async def mock_async_stream(*args, **kwargs):
            yield MockOutput(data="async_chunk1")
            yield MockOutput(data="async_chunk2")

        mock_instance = MagicMock()
        mock_instance.astream = mock_async_stream
        mock_restful_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        inputs = MockInput(data="test_input")
        chunks = []
        async for chunk in wrapper.astream(inputs):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].data == "async_chunk1"
        assert chunks[1].data == "async_chunk2"

    @patch("jiuwen.extension.wrapper.mcp_tool_wrapper.McpToolWrapper")
    @pytest.mark.asyncio
    async def test_astream_method_mcp(self, mock_mcp_wrapper, caplog):
        """测试 mcp 类型的 astream 方法（不支持）"""
        mock_instance = MagicMock()
        mock_mcp_wrapper.return_value = mock_instance

        wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        inputs = MockInput(data="test_input")
        chunks = []
        async for chunk in wrapper.astream(inputs):
            chunks.append(chunk)

        assert len(chunks) == 0

        assert any(
            "astream() is not available" in record.message for record in caplog.records
        )


class TestToolWrapperLazyLoading:
    """测试 ToolWrapper 延迟加载机制"""

    @patch("jiuwen.extension.wrapper.restful_api_wrapper.RestfulApiWrapper")
    def test_lazy_loading(self, mock_restful_wrapper):
        """测试延迟加载机制"""
        wrapper = ToolWrapper("test", "agent", "session", ToolType.RESTFUL)

        mock_restful_wrapper.assert_not_called()

        _ = wrapper.name
        mock_restful_wrapper.assert_called_once()

    @patch("jiuwen.extension.wrapper.mcp_tool_wrapper.McpToolWrapper")
    def test_lazy_loading_mcp(self, mock_mcp_wrapper):
        """测试 mcp 类型的延迟加载机制"""
        wrapper = ToolWrapper("test", "agent", "session", ToolType.MCP)

        mock_mcp_wrapper.assert_not_called()

        _ = wrapper.name
        mock_mcp_wrapper.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
