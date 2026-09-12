# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
McpServerLoader 单元测试。

测试范围：
1. convert_ir_to_server_config：IR 配置转换为 McpServerConfig（支持驼峰命名）
2. load_mcp_server_from_ir：从 IR 配置加载 MCP Server
3. create_mcp_tool_wrapper：创建 MCP Tool 包装器
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.wrapper.mcp_server_loader import (
    convert_ir_to_server_config,
    load_mcp_server_from_ir,
    create_mcp_tool_wrapper,
)
from openjiuwen.core.foundation.tool.mcp.base import McpServerConfig


class TestConvertIrToServerConfig:
    def test_basic_conversion_camel_case(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "id": "abc123",
            "type": "sse",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert isinstance(config, McpServerConfig)
        assert config.server_path == "https://example.com/mcp"
        assert config.server_name == "abc123"
        assert config.server_id == "test_server"
        assert config.client_type == "sse_new"

    def test_camel_case_plugin_dependency_conversion(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "pluginDependency": {"hook_function": {"mcp_auth": "test.module.auth"}},
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.params["plugin_dependency"] == {
            "hook_function": {"mcp_auth": "test.module.auth"}
        }

    def test_camel_case_mcp_choose_tools_conversion(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "mcpChooseTools": ["tool1", "tool2"],
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.params["mcp_choose_tools"] == ["tool1", "tool2"]

    def test_conversion_with_headers(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "headers": {"Authorization": "Bearer token"},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.auth_headers == {"Authorization": "Bearer token"}

    def test_conversion_with_auth(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "auth": {"scope": "SERVICE", "headers": {"X-Key": "value"}},
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.params["auth"] == {
            "scope": "SERVICE",
            "headers": {"X-Key": "value"},
        }

    def test_conversion_with_tool_params(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "arguments": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "param1 description",
                }
            ],
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        tool_params = config.params["tool_params"]
        assert len(tool_params) == 1
        assert tool_params[0].name == "param1"
        assert tool_params[0].type == "string"
        assert tool_params[0].description == "param1 description"

    def test_client_type_sse(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "type": "sse",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.client_type == "sse_new"

    def test_client_type_sse_new(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "type": "sse_new",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.client_type == "sse_new"

    def test_client_type_streamable_http(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "type": "streamable_http",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.client_type == "streamable_http_new"

    def test_client_type_streamable_http_new(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "type": "streamable_http_new",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.client_type == "streamable_http_new"

    def test_client_type_unknown_fallback(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "type": "unknown_type",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.client_type == "unknown_type"

    def test_client_type_default_sse(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.client_type == "sse_new"

    def test_empty_url_defaults_to_empty_string(self):
        ir_config = {
            "name": "test_server",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.server_path == ""

    def test_empty_name_defaults_to_empty_string(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.server_name == ""
        assert config.server_id == ""

    def test_full_config_conversion_camel_case(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "full_server",
            "id": "id_full",
            "type": "streamable_http",
            "headers": {"X-Auth": "token"},
            "auth": {"scope": "USER"},
            "pluginDependency": {"dep": "v1"},
            "arguments": [{"name": "p1", "description": "p1 param"}],
            "mcpChooseTools": ["tool1"],
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.server_path == "https://example.com/mcp"
        assert config.server_name == "id_full"
        assert config.server_id == "full_server"
        assert config.client_type == "streamable_http_new"
        assert config.auth_headers == {"X-Auth": "token"}
        assert config.params["auth"] == {"scope": "USER"}
        assert config.params["plugin_dependency"] == {"dep": "v1"}
        assert len(config.params["tool_params"]) == 1
        assert config.params["tool_params"][0].name == "p1"
        assert config.params["mcp_choose_tools"] == ["tool1"]

    def test_headers_not_converted(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "headers": {"X-Custom-Header": "value"},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.auth_headers == {"X-Custom-Header": "value"}

    def test_auth_not_converted(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "test_server",
            "auth": {"scope": "USER", "targetDomain": "headers"},
            "headers": {},
        }
        config = convert_ir_to_server_config(ir_config)
        assert config.params["auth"] == {"scope": "USER", "targetDomain": "headers"}


class TestLoadMcpServerFromIr:
    @pytest.mark.asyncio
    async def test_load_mcp_server_returns_tool_ids(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "unique_test_server_1",
            "type": "sse",
            "headers": {},
        }
        with patch("jiuwen.extension.wrapper.mcp_server_loader.Runner") as mock_runner:
            mock_resource_mgr = MagicMock()
            mock_resource_mgr.add_mcp_server = AsyncMock()
            mock_resource_mgr._resource_registry.tool.return_value.get_mcp_tool_id.return_value = [
                "tool1",
                "tool2",
            ]
            mock_runner.resource_mgr = mock_resource_mgr
            tool_ids = await load_mcp_server_from_ir(ir_config)
            assert tool_ids == ["tool1", "tool2"]
            mock_resource_mgr.add_mcp_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_mcp_server_empty_tools(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "unique_test_server_2",
            "type": "sse",
            "headers": {},
        }
        with patch("jiuwen.extension.wrapper.mcp_server_loader.Runner") as mock_runner:
            mock_resource_mgr = MagicMock()
            mock_resource_mgr.add_mcp_server = AsyncMock()
            mock_resource_mgr._resource_registry.tool.return_value.get_mcp_tool_id.return_value = []
            mock_runner.resource_mgr = mock_resource_mgr
            tool_ids = await load_mcp_server_from_ir(ir_config)
            assert tool_ids == []

    @pytest.mark.asyncio
    async def test_load_mcp_server_with_exception(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "unique_test_server_3",
            "type": "sse",
            "headers": {},
        }
        with patch("jiuwen.extension.wrapper.mcp_server_loader.Runner") as mock_runner:
            mock_resource_mgr = MagicMock()
            mock_resource_mgr.add_mcp_server = AsyncMock(
                side_effect=RuntimeError("connection failed")
            )
            mock_runner.resource_mgr = mock_resource_mgr
            with pytest.raises(RuntimeError, match="connection failed"):
                await load_mcp_server_from_ir(ir_config)

    @pytest.mark.asyncio
    async def test_load_mcp_server_uses_converted_config(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "unique_test_server_4",
            "type": "streamable_http",
            "headers": {"X-Auth": "token"},
        }
        with patch("jiuwen.extension.wrapper.mcp_server_loader.Runner") as mock_runner:
            mock_resource_mgr = MagicMock()
            mock_resource_mgr.add_mcp_server = AsyncMock()
            mock_resource_mgr._resource_registry.tool.return_value.get_mcp_tool_id.return_value = []
            mock_runner.resource_mgr = mock_resource_mgr
            await load_mcp_server_from_ir(ir_config)
            call_args = mock_resource_mgr.add_mcp_server.call_args
            config = call_args[0][0]
            assert isinstance(config, McpServerConfig)
            assert config.client_type == "streamable_http_new"
            assert config.auth_headers == {"X-Auth": "token"}

    @pytest.mark.asyncio
    async def test_load_mcp_server_with_tag(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "unique_test_server_5",
            "type": "sse",
            "headers": {},
        }
        with patch("jiuwen.extension.wrapper.mcp_server_loader.Runner") as mock_runner:
            mock_resource_mgr = MagicMock()
            mock_resource_mgr.add_mcp_server = AsyncMock()
            mock_resource_mgr._resource_registry.tool.return_value.get_mcp_tool_id.return_value = []
            mock_runner.resource_mgr = mock_resource_mgr
            await load_mcp_server_from_ir(ir_config, tag="agent_789")
            call_args = mock_resource_mgr.add_mcp_server.call_args
            tag = call_args.kwargs.get("tag")
            assert tag == "agent_789"

    @pytest.mark.asyncio
    async def test_load_mcp_server_camel_case_input(self):
        ir_config = {
            "url": "https://example.com/mcp",
            "name": "unique_test_server_6",
            "type": "streamable_http",
            "pluginDependency": {"hook": "test"},
            "mcpChooseTools": ["tool_a"],
            "headers": {},
        }
        with patch("jiuwen.extension.wrapper.mcp_server_loader.Runner") as mock_runner:
            mock_resource_mgr = MagicMock()
            mock_resource_mgr.add_mcp_server = AsyncMock()
            mock_resource_mgr._resource_registry.tool.return_value.get_mcp_tool_id.return_value = [
                "tool_a"
            ]
            mock_runner.resource_mgr = mock_resource_mgr
            tool_ids = await load_mcp_server_from_ir(ir_config, tag="agent_camel")
            assert tool_ids == ["tool_a"]
            call_args = mock_resource_mgr.add_mcp_server.call_args
            config = call_args[0][0]
            tag = call_args.kwargs.get("tag")
            assert config.params["plugin_dependency"] == {"hook": "test"}
            assert config.params["mcp_choose_tools"] == ["tool_a"]
            assert tag == "agent_camel"


class TestCreateMcpToolWrapper:
    def test_create_wrapper_returns_instance(self):
        from jiuwen.extension.wrapper.mcp_tool_wrapper import McpToolWrapper

        wrapper = create_mcp_tool_wrapper("tool_123", "agent_456", "session_789")
        assert isinstance(wrapper, McpToolWrapper)
        assert wrapper._tool_id == "tool_123"
        assert wrapper._agent_id == "agent_456"
        assert wrapper._session_id == "session_789"

    def test_create_wrapper_with_empty_id(self):
        from jiuwen.extension.wrapper.mcp_tool_wrapper import McpToolWrapper

        wrapper = create_mcp_tool_wrapper("", "agent_456", "session_789")
        assert isinstance(wrapper, McpToolWrapper)
        assert wrapper._tool_id == ""

    def test_create_wrapper_tool_not_loaded(self):
        wrapper = create_mcp_tool_wrapper("tool_123", "agent_456", "session_789")
        assert wrapper._tool is None
