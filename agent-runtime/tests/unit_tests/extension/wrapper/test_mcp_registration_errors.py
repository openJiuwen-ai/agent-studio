# coding: utf-8
"""MCP discovery and registration failures must not degrade to empty tools."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.extension.wrapper.mcp_server_loader import (
    convert_ir_to_server_config,
    load_mcp_server_from_ir,
)
from jiuwen.extension.wrapper.sse_client_new import SSEClientNew
from jiuwen.extension.wrapper.streamable_http_client_new import (
    StreamableHttpClientNew,
)
from openjiuwen.core.runner import Runner


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("client_class", "transport_target"),
    [
        (
            StreamableHttpClientNew,
            "jiuwen.extension.wrapper.streamable_http_client_new.streamablehttp_client",
        ),
        (SSEClientNew, "jiuwen.extension.wrapper.sse_client_new.sse_client"),
    ],
)
async def test_list_tools_propagates_transport_error(client_class, transport_target):
    """A transport failure must reach the registration layer instead of returning []."""

    client = object.__new__(client_class)
    client._name = "calculate"
    client._prepare_request_params = MagicMock(  # pylint: disable=protected-access
        return_value=SimpleNamespace(headers={})
    )
    client._build_mcp_url = MagicMock(  # pylint: disable=protected-access
        return_value="http://unreachable.example/mcp"
    )

    @asynccontextmanager
    async def failing_transport(*_args, **_kwargs):
        raise RuntimeError("transport unavailable")
        yield  # pragma: no cover

    with patch(transport_target, failing_transport):
        with pytest.raises(RuntimeError, match="Failed to list MCP tools"):
            await client.list_tools()


def _mcp_ir() -> dict:
    return {
        "id": "mcp-id",
        "name": "calculate",
        "type": "streamable_http",
        "url": "http://unreachable.example/mcp",
        "headers": {},
        "auth": {},
        "arguments": [],
        "mcp_choose_tools": ["add"],
    }


def test_convert_config_resolves_environment_variables_in_url():
    """ReAct MCP registration must resolve the environment selected at runtime."""

    ir_config = _mcp_ir()
    ir_config["url"] = (
        "http://${_env.plugin_url_params.ip}:"
        "${_env.plugin_url_params.port}/mcp"
    )

    config = convert_ir_to_server_config(
        ir_config,
        environment_variables={
            "plugin_url_params": {"ip": "127.0.0.1", "port": "8766"}
        },
    )

    assert config.server_path == "http://127.0.0.1:8766/mcp"


def test_convert_config_keeps_fixed_url_unchanged():
    """Existing MCP configurations without placeholders remain compatible."""

    config = convert_ir_to_server_config(
        _mcp_ir(),
        environment_variables={
            "plugin_url_params": {"ip": "127.0.0.1", "port": "8766"}
        },
    )

    assert config.server_path == "http://unreachable.example/mcp"


@pytest.mark.asyncio
async def test_loader_propagates_resource_manager_error():
    """ResourceMgr returns Result.Error; the loader must not report success."""

    add_result = MagicMock()
    add_result.is_ok.return_value = False
    add_result.error.return_value = RuntimeError("MCP connection failed")

    with patch.object(
        Runner.resource_mgr,
        "add_mcp_server",
        new=AsyncMock(return_value=add_result),
    ):
        with pytest.raises(RuntimeError, match="MCP connection failed"):
            await load_mcp_server_from_ir(_mcp_ir(), tag="agent-id")


@pytest.mark.asyncio
async def test_loader_rejects_success_without_tools():
    """An empty discovery result is unusable for ReAct and must be an error."""

    add_result = MagicMock()
    add_result.is_ok.return_value = True
    tool_registry = Runner.resource_mgr._resource_registry.tool()  # pylint: disable=protected-access

    with patch.object(
        Runner.resource_mgr,
        "add_mcp_server",
        new=AsyncMock(return_value=add_result),
    ), patch.object(tool_registry, "get_mcp_tool_id", return_value=[]):
        with pytest.raises(RuntimeError, match="did not expose any available tools"):
            await load_mcp_server_from_ir(_mcp_ir(), tag="agent-id")
