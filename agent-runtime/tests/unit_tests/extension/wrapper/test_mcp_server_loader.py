# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""MCP server_id 唯一性测试（issue #1481）

server_id 是 ResourceMgr 进程级全局注册表的唯一 key（add_tool_server 按
其去重、get_mcp_tool_id 按其索引）。SSO 多用户共享同一 runtime 进程，
若用用户可编辑的显示名作 server_id，跨用户同名 MCP 会互相遮蔽：后注册
者被去重逻辑吞掉，静默复用先注册者的连接与工具（甚至打到别人的 server）。

修复后：有 IR id（平台侧实例主键，全局唯一）时 server_id/server_name 均
用 id；原始名仅存 params["display_name"] 供展示。
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.extension.wrapper.mcp_server_loader import (
    convert_ir_to_server_config,
    load_mcp_server_from_ir,
)

OPENAI_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _make_ir_config(*, mcp_id: str = "", name: str = "天气查询") -> dict:
    conf = {
        "name": name,
        "type": "streamable_http",
        "url": "http://127.0.0.1:3000/mcp",
        "headers": {},
        "auth": {},
        "pluginDependency": {},
        "arguments": [],
    }
    if mcp_id:
        conf["id"] = mcp_id
    return conf


class TestConvertIrToServerConfigServerId:
    def test_server_id_uses_ir_id_when_present(self):
        config = convert_ir_to_server_config(_make_ir_config(mcp_id="mcp-uuid-a"))

        assert config.server_id == "mcp-uuid-a"
        assert config.server_name == "mcp-uuid-a"
        assert config.params["display_name"] == "天气查询"

    def test_server_id_falls_back_to_name_without_id(self):
        config = convert_ir_to_server_config(_make_ir_config())

        assert config.server_id == "天气查询"
        assert config.server_name == "天气查询"
        assert config.params["display_name"] == "天气查询"

    def test_server_name_ascii_safe_with_chinese_display_name(self):
        config = convert_ir_to_server_config(_make_ir_config(mcp_id="mcp-uuid-a"))

        assert config.server_name == "mcp-uuid-a"
        assert OPENAI_NAME_PATTERN.match(config.server_name)

    def test_same_name_different_ids_do_not_collide(self):
        config_a = convert_ir_to_server_config(_make_ir_config(mcp_id="mcp-uuid-a"))
        config_b = convert_ir_to_server_config(_make_ir_config(mcp_id="mcp-uuid-b"))

        assert config_a.server_id != config_b.server_id
        assert config_a.server_name != config_b.server_name
        assert config_a.params["display_name"] == config_b.params["display_name"]


class TestLoadMcpServerFromIr:
    @pytest.mark.asyncio
    async def test_same_name_servers_register_and_query_by_own_id(self):
        """同名不同实例的两个 MCP 先后注册，各自按自身 server_id 查询工具。

        修复前：两者 server_id 均为显示名，第二次注册命中第一次的注册槽
        （add_tool_server 去重），get_mcp_tool_id 返回的是先注册者的工具。
        """
        tool_ids_by_server = {
            "mcp-uuid-a": ["mcp-uuid-a.mcp-uuid-a.tool_a"],
            "mcp-uuid-b": ["mcp-uuid-b.mcp-uuid-b.tool_b"],
        }
        registered_configs = []

        resource_mgr = MagicMock()
        resource_mgr.add_mcp_server = AsyncMock(
            side_effect=lambda config, **kwargs: registered_configs.append(config)
        )
        resource_mgr._resource_registry.tool.return_value.get_mcp_tool_id = MagicMock(
            side_effect=lambda server_id: tool_ids_by_server.get(server_id)
        )

        with patch(
            "jiuwen.extension.wrapper.mcp_server_loader.Runner"
        ) as mock_runner:
            mock_runner.resource_mgr = resource_mgr

            ids_a = await load_mcp_server_from_ir(
                _make_ir_config(mcp_id="mcp-uuid-a"), tag="agent-a"
            )
            ids_b = await load_mcp_server_from_ir(
                _make_ir_config(mcp_id="mcp-uuid-b"), tag="agent-b"
            )

        assert ids_a == ["mcp-uuid-a.mcp-uuid-a.tool_a"]
        assert ids_b == ["mcp-uuid-b.mcp-uuid-b.tool_b"]
        assert resource_mgr.add_mcp_server.await_count == 2
        assert [c.server_id for c in registered_configs] == ["mcp-uuid-a", "mcp-uuid-b"]
        queried = [
            call.args[0]
            for call in resource_mgr._resource_registry.tool.return_value
            .get_mcp_tool_id.call_args_list
        ]
        assert queried == ["mcp-uuid-a", "mcp-uuid-b"]
