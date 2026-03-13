#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
import concurrent.futures
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from fastapi import status
from openjiuwen.core.common.logging import logger
from packaging import version
from pydantic import ValidationError

try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logger.warning("jsonschema library not available, plugin validation will be skipped")

from openjiuwen_studio.core.database import milliseconds
import openjiuwen_studio.core.manager.convertor.plugin as convert
from openjiuwen_studio.core.manager.convertor.components.plugin import param_type_mapping
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.repositories.plugin_repository import plugin_repository
from openjiuwen_studio.core.manager.repositories.tool_repository import tool_repository
from openjiuwen_studio.core.manager.repositories.agent_repository import agent_repository
from openjiuwen_studio.core.utils.exception import log_exception
from openjiuwen_studio.models.plugin import PluginBaseDBPd, ToolBaseDB, PluginPublishDBPd
from openjiuwen_studio.schemas.plugin import (
    PluginCreate, PluginId, PluginInfo, PluginInfoResponse, PluginApiBase,
    PluginApiInfo, PluginApiInfoCreate, PluginToolId, PluginApiInfoResponse,
    PluginListTool, PluginList, PluginListResponse, PluginListPagination,
    PluginType, PluginToolParam, ToolId, PluginCodeBase, PluginCodeInfo,
    PluginCodeInfoResponse, PluginApiInfoDB, PluginCodeInfoDB,
    PluginMcpBase, PluginMcpInfo, PluginMcpInfoDB, PluginMcpInfoResponse,
    PluginMcpTransport,
    PluginPublish, PluginPublishResponse, PluginPublishInfo,
    PluginPublishListResponse, PluginPublishInfoResponse, ParamType, ParamSendMethod
)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.manager.reference_extractor import check_referenced_dependencies
from openjiuwen_studio.core.manager.repositories.reference_repository import reference_repository


def with_exception_handling(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=type(e).__name__
            )
        except Exception as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=type(e).__name__
            )

    return wrapper


def _normalize_header_configuration(header_config: Any) -> Dict[str, Any]:
    """Normalize header_configuration to dict format regardless of whether it's an array or dict.

    Array format:  [{"name": "access-token", "value": "...", "description": "..."}]
    Dict format:   {"Authorization": {"value": "...", "description": "..."}}
    Both are normalized to dict format.
    """
    if isinstance(header_config, list):
        result = {}
        for item in header_config:
            if isinstance(item, dict) and "name" in item:
                name = item["name"]
                entry: Dict[str, Any] = {
                    "value": item.get("value", ""),
                    "description": item.get("description", ""),
                }
                if "type" in item:
                    entry["type"] = item["type"]
                if "send_method" in item:
                    entry["send_method"] = item["send_method"]
                result[name] = entry
        return result
    if isinstance(header_config, dict):
        return header_config
    return {}


def _header_configuration_to_plugin_params(header_config: Any) -> List[PluginToolParam]:
    """Convert header_configuration (array or dict) to PluginToolParam list for plugin-level inputs."""
    normalized = _normalize_header_configuration(header_config)
    params = []
    for header_name, header_details in normalized.items():
        if not isinstance(header_details, dict):
            continue

        # Resolve type: use declared type string if present, default to STRING
        type_str = header_details.get("type", "string")
        if isinstance(type_str, str):
            param_type = _JSON_SCHEMA_TYPE_TO_PARAM_TYPE.get(type_str.lower(), ParamType.PARAM_TYPE_STRING)
        else:
            param_type = ParamType.PARAM_TYPE_STRING

        # Resolve send_method: use declared string if present, default to HEADER
        method_str = header_details.get("send_method", "Header")
        if isinstance(method_str, str):
            method_int = _SEND_METHOD_STR_TO_INT.get(method_str, 1)
            method = ParamSendMethod(method_int)
        else:
            method = ParamSendMethod.PARAM_SEND_METHOD_HEADER

        param = PluginToolParam(
            name=header_name,
            desc=header_details.get("description", ""),
            type=param_type,
            is_required=True,
            method=method,
            is_runtime=False,
            value=header_details.get("value", ""),
        )
        params.append(param)
    return params


_JSON_SCHEMA_TYPE_TO_PARAM_TYPE: Dict[str, ParamType] = {
    "string": ParamType.PARAM_TYPE_STRING,
    "integer": ParamType.PARAM_TYPE_INT,
    "number": ParamType.PARAM_TYPE_FLOAT,
    "boolean": ParamType.PARAM_TYPE_BOOL,
    "object": ParamType.PARAM_TYPE_OBJECT,
    "array": ParamType.PARAM_TYPE_ARRAY_STRING,
}

_SEND_METHOD_STR_TO_INT: Dict[str, int] = {
    "None": 0,    # PARAM_SEND_METHOD_NONE
    "Header": 1,  # PARAM_SEND_METHOD_HEADER
    "Query": 2,   # PARAM_SEND_METHOD_QUERY
    "Body": 3,    # PARAM_SEND_METHOD_BODY
    "Path": 4,    # PARAM_SEND_METHOD_PATH
    "none": 0,
    "header": 1,
    "query": 2,
    "body": 3,
    "path": 4,
}


def _mcp_card_input_params_to_tool_params(input_params: dict) -> List[PluginToolParam]:
    """
    Convert a McpToolCard's JSON-Schema input_params dict into a list of PluginToolParam.

    input_params shape:
    {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"]
    }
    """
    if not input_params or not isinstance(input_params, dict):
        return []

    properties: Dict[str, Any] = input_params.get("properties", {})
    required_names: set = set(input_params.get("required", []))

    params: List[PluginToolParam] = []
    for name, prop in properties.items():
        json_type = prop.get("type", "string") if isinstance(prop, dict) else "string"
        param_type = _JSON_SCHEMA_TYPE_TO_PARAM_TYPE.get(json_type, ParamType.PARAM_TYPE_STRING)
        desc = prop.get("description", name) if isinstance(prop, dict) else name

        params.append(PluginToolParam(
            name=name,
            desc=desc or name,
            type=param_type,
            is_required=name in required_names,
            method=ParamSendMethod.PARAM_SEND_METHOD_NONE,
            is_runtime=True,
            value="",
        ))

    return params


def _extract_auth_headers(plugin_data: dict) -> Dict[str, str]:
    """
    Build a header dict from plugin inputs that have method == PARAM_SEND_METHOD_HEADER (1).

    Each qualifying input contributes one entry:  { input["name"]: input["value"] }

    Non-header inputs and inputs with an empty name or value are silently skipped.
    """
    inputs = plugin_data.get("inputs") or []
    headers: Dict[str, str] = {}
    for inp in inputs:
        if not isinstance(inp, dict):
            continue
        method = inp.get("method", 0)
        # Accept both the raw integer and the enum object.
        method_int = method.value if hasattr(method, "value") else int(method)
        if method_int != int(ParamSendMethod.PARAM_SEND_METHOD_HEADER):
            continue
        name = (inp.get("name") or "").strip()
        value = (inp.get("value") or "").strip()
        if name and value:
            headers[name] = value
    return headers


@dataclass
class _McpConnectionConfig:
    """MCP server connection parameters, grouped to keep function signatures concise."""
    transport: int
    url: str
    command: str = ""
    args: Optional[List[str]] = field(default_factory=list)
    env: Optional[dict] = None
    auth_headers: Optional[Dict[str, str]] = field(default_factory=dict)


async def _discover_and_create_mcp_tools(
        config: _McpConnectionConfig,
        plugin_id: str,
        space_id: str,
        current_user: dict,
) -> ResponseModel:
    """
    Connect to an MCP server using the appropriate transport, discover all available tools,
    and persist each one to the database with fully populated input_parameters.

    Supported transports (PluginMcpTransport):
        1 = STDIO          – spawns a local subprocess via StdioClient
        2 = SSE            – Server-Sent Events endpoint via SseClient
        3 = STREAMABLE_HTTP – Streamable HTTP endpoint via StreamableHttpClient
        4 = OPENAPI         – OpenAPI-compatible endpoint via OpenApiClient
        5 = PLAYWRIGHT     – Playwright browser session via PlaywrightClient
    """
    mcp_transport_enum = PluginMcpTransport(config.transport)
    server_name = plugin_id

    if mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO:
        from openjiuwen.core.foundation.tool.mcp.client.stdio_client import StdioClient

        client = StdioClient(
            server_path="",  # Not used for Stdio; command/args come from params
            name=server_name,
            params={
                "command": sys.executable,  # Current Python interpreter
                "args": [config.url],  # The server script to run
                "env": None,  # Inherit environment (or pass a dict)
                "cwd": os.getcwd(),  # Working directory
                "encoding_error_handler": "strict",  # 'strict' | 'ignore' | 'replace'
            },)
        transport_label = "STDIO"

    elif mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_SSE:
        from openjiuwen.core.foundation.tool.mcp.client.sse_client import SseClient
        client = SseClient(
            server_path=config.url,
            name=server_name,
            auth_headers=config.auth_headers or {},
        )
        transport_label = "SSE"

    elif mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STREAMABLE_HTTP:
        from openjiuwen.core.foundation.tool.mcp.client.streamable_http_client import StreamableHttpClient
        client = StreamableHttpClient(
            server_path=config.url,
            name=server_name,
            auth_headers=config.auth_headers or {},
        )
        transport_label = "Streamable HTTP"

    elif mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_OPENAPI:
        from openjiuwen.core.foundation.tool.mcp.client.openapi_client import OpenApiClient
        client = OpenApiClient(
            server_path=config.url,
            name=server_name,
        )
        transport_label = "OpenAPI"

    elif mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_PLAYWRIGHT:
        from openjiuwen.core.foundation.tool.mcp.client.playwright_client import PlaywrightClient
        client = PlaywrightClient(
            server_path=config.url,
            name=server_name,
        )
        transport_label = "Playwright"

    else:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"Unsupported MCP transport value: {config.transport}",
        )

    try:
        connected = await client.connect()
        if not connected:
            return ResponseModel(
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to connect to MCP {transport_label} server at '{config.url}'",
            )

        try:
            tool_cards = await client.list_tools()
        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(
            f"MCP {transport_label} discovery error for plugin '{plugin_id}': {e}",
            exc_info=True,
        )
        return ResponseModel(
            code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"MCP {transport_label} connection/discovery failed: {str(e)}",
        )

    # Discovery succeeded — purge every previously stored tool for this plugin
    # before inserting the freshly discovered set.
    _, existing_tools = plugin_repository.plugin_get(
        {"plugin_id": plugin_id, "space_id": space_id}
    )
    deleted_count = 0
    for existing in existing_tools or []:
        existing_tool_id = existing.get("tool_id", "") if isinstance(existing, dict) else ""
        if not existing_tool_id:
            continue
        del_res = tool_repository.tool_delete(
            {"tool_id": existing_tool_id, "space_id": space_id}
        )
        if ResponseModel(**del_res).code == status.HTTP_200_OK:
            deleted_count += 1
        else:
            logger.warning(
                f"Failed to delete old MCP tool '{existing_tool_id}' "
                f"for plugin '{plugin_id}' before re-discovery"
            )
    if deleted_count:
        logger.info(
            f"Deleted {deleted_count} existing MCP tool(s) for plugin '{plugin_id}' "
            f"before inserting newly discovered tools"
        )

    created_tool_ids: List[str] = []
    for card in tool_cards:
        tool_name = getattr(card, "name", "") or ""
        tool_desc = getattr(card, "description", "") or ""
        card_input_params = getattr(card, "input_params", None) or {}
        request_params = _mcp_card_input_params_to_tool_params(card_input_params)

        # Step 1: create the base record (available=False, input_parameters empty)
        mcp_req = PluginMcpBase(
            space_id=space_id,
            plugin_id=plugin_id,
            plugin_type=PluginType.PLUGIN_TYPE_CLOUD_MCP,
            name=tool_name,
            desc=tool_desc,
            transport=mcp_transport_enum,
            command=config.command,
            args=config.args or [],
            env=config.env,
            url=config.url,
            mcp_tool_name=tool_name,
        )

        create_result = plugin_create_mcp_tool(mcp_req, current_user)
        if create_result.code != status.HTTP_200_OK:
            logger.warning(
                f"Failed to create MCP tool '{tool_name}' for plugin '{plugin_id}': "
                f"{create_result.message}"
            )
            continue

        tool_id = create_result.data.get("tool_id") if isinstance(create_result.data, dict) else None
        if not tool_id:
            logger.warning(f"No tool_id returned for MCP tool '{tool_name}', skipping")
            continue

        # Step 2: update with parsed input_parameters so the column is properly populated.
        # plugin_update_mcp_tool() converts request_params → input_parameters via
        # _plugin_input_output_parameters(), which is what we need.
        mcp_info = PluginMcpInfo(
            space_id=space_id,
            plugin_id=plugin_id,
            plugin_type=PluginType.PLUGIN_TYPE_CLOUD_MCP,
            tool_id=tool_id,
            name=tool_name,
            desc=tool_desc,
            transport=mcp_transport_enum,
            command=config.command,
            args=config.args or [],
            env=config.env,
            url=config.url,
            mcp_tool_name=tool_name,
            request_params=request_params,
            response_params=[],
            available=False,
        )
        update_result = plugin_update_mcp_tool(mcp_info, current_user)
        if update_result.code != status.HTTP_200_OK:
            logger.warning(
                f"Failed to update input_parameters for MCP tool '{tool_name}' "
                f"(tool_id={tool_id}): {update_result.message}"
            )
            # Tool exists in DB, so still mark it available below.

        # Step 3: mark tool available
        plugin_tool_update_available(tool_id, space_id, True)
        created_tool_ids.append(tool_id)

    logger.info(
        f"MCP {transport_label} discovery complete for plugin '{plugin_id}': "
        f"{len(created_tool_ids)}/{len(tool_cards)} tools stored"
    )
    return ResponseModel(
        code=status.HTTP_200_OK,
        message=f"Discovered and stored {len(created_tool_ids)} MCP tools",
        data={"tool_ids": created_tool_ids},
    )


def _run_async_in_thread(coro) -> Any:
    """Run an async coroutine in a dedicated thread with its own event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


_JSON_SCHEMA_TYPE_TO_PARAM_TYPE: Dict[str, ParamType] = {
    "string": ParamType.PARAM_TYPE_STRING,
    "integer": ParamType.PARAM_TYPE_INT,
    "number": ParamType.PARAM_TYPE_FLOAT,
    "boolean": ParamType.PARAM_TYPE_BOOL,
    "object": ParamType.PARAM_TYPE_OBJECT,
    "array": ParamType.PARAM_TYPE_ARRAY_STRING,
}


def _mcp_card_input_params_to_tool_params(input_params: dict) -> List[PluginToolParam]:
    """
    Convert a McpToolCard's JSON-Schema input_params dict into a list of PluginToolParam.

    input_params shape:
    {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"]
    }
    """
    if not input_params or not isinstance(input_params, dict):
        return []

    properties: Dict[str, Any] = input_params.get("properties", {})
    required_names: set = set(input_params.get("required", []))

    params: List[PluginToolParam] = []
    for name, prop in properties.items():
        json_type = prop.get("type", "string") if isinstance(prop, dict) else "string"
        param_type = _JSON_SCHEMA_TYPE_TO_PARAM_TYPE.get(json_type, ParamType.PARAM_TYPE_STRING)
        desc = prop.get("description", name) if isinstance(prop, dict) else name

        params.append(PluginToolParam(
            name=name,
            desc=desc or name,
            type=param_type,
            is_required=name in required_names,
            method=ParamSendMethod.PARAM_SEND_METHOD_NONE,
            is_runtime=True,
            value="",
        ))

    return params


def _extract_auth_headers(plugin_data: dict) -> Dict[str, str]:
    """
    Build a header dict from plugin inputs that have method == PARAM_SEND_METHOD_HEADER (1).

    Each qualifying input contributes one entry:  { input["name"]: input["value"] }

    Non-header inputs and inputs with an empty name or value are silently skipped.
    """
    inputs = plugin_data.get("inputs") or []
    headers: Dict[str, str] = {}
    for inp in inputs:
        if not isinstance(inp, dict):
            continue
        method = inp.get("method", 0)
        # Accept both the raw integer and the enum object.
        method_int = method.value if hasattr(method, "value") else int(method)
        if method_int != int(ParamSendMethod.PARAM_SEND_METHOD_HEADER):
            continue
        name = (inp.get("name") or "").strip()
        value = (inp.get("value") or "").strip()
        if name and value:
            headers[name] = value
    return headers


@dataclass
class _McpConnectionConfig:
    """MCP server connection parameters, grouped to keep function signatures concise."""
    transport: int
    url: str
    params: Dict[str, Any] = field(default_factory=dict)
    auth_headers: Optional[Dict[str, str]] = field(default_factory=dict)


async def _discover_and_create_mcp_tools(
        config: _McpConnectionConfig,
        plugin_id: str,
        space_id: str,
        current_user: dict,
) -> ResponseModel:
    """
    Connect to an MCP server using the appropriate transport, discover all available tools,
    and persist each one to the database with fully populated input_parameters.

    Supported transports (PluginMcpTransport):
        1 = STDIO          – spawns a local subprocess via StdioClient
        2 = SSE            – Server-Sent Events endpoint via SseClient
        3 = STREAMABLE_HTTP – Streamable HTTP endpoint via StreamableHttpClient
        4 = OPENAPI         – OpenAPI-compatible endpoint via OpenApiClient
        5 = PLAYWRIGHT     – Playwright browser session via PlaywrightClient
    """
    mcp_transport_enum = PluginMcpTransport(config.transport)
    server_name = plugin_id

    from openjiuwen.core.foundation.tool.mcp.base import McpServerConfig

    _transport_to_client_type = {
        PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO: "stdio",
        PluginMcpTransport.PLUGIN_MCP_TRANSPORT_SSE: "sse",
        PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STREAMABLE_HTTP: "streamable-http",
        PluginMcpTransport.PLUGIN_MCP_TRANSPORT_OPENAPI: "openapi",
        PluginMcpTransport.PLUGIN_MCP_TRANSPORT_PLAYWRIGHT: "playwright",
    }
    client_type = _transport_to_client_type.get(mcp_transport_enum)
    if client_type is None:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"Unsupported MCP transport value: {config.transport}",
        )

    mcp_params = dict(config.params or {})
    if mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO:
        mcp_params.setdefault("command", sys.executable)
        mcp_params.setdefault("args", [config.url])
        mcp_params.setdefault("env", None)
        mcp_params.setdefault("cwd", os.getcwd())
        mcp_params.setdefault("encoding_error_handler", "strict")

    server_config = McpServerConfig(
        server_name=server_name,
        server_path=config.url or "",
        client_type=client_type,
        params=mcp_params,
        auth_headers=config.auth_headers or {},
    )

    if mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO:
        from openjiuwen.core.foundation.tool.mcp.client.stdio_client import StdioClient
        client = StdioClient(server_config)
        transport_label = "STDIO"
    elif mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_SSE:
        from openjiuwen.core.foundation.tool.mcp.client.sse_client import SseClient
        client = SseClient(server_config)
        transport_label = "SSE"
    elif mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STREAMABLE_HTTP:
        from openjiuwen.core.foundation.tool.mcp.client.streamable_http_client import StreamableHttpClient
        client = StreamableHttpClient(server_config)
        transport_label = "Streamable HTTP"
    elif mcp_transport_enum == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_OPENAPI:
        from openjiuwen.core.foundation.tool.mcp.client.openapi_client import OpenApiClient
        client = OpenApiClient(server_config)
        transport_label = "OpenAPI"
    else:  # PLAYWRIGHT
        from openjiuwen.core.foundation.tool.mcp.client.playwright_client import PlaywrightClient
        client = PlaywrightClient(server_config)
        transport_label = "Playwright"

    try:
        connected = await client.connect()
        if not connected:
            return ResponseModel(
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to connect to MCP {transport_label} server at '{config.url}'",
            )

        try:
            tool_cards = await client.list_tools()
        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(
            f"MCP {transport_label} discovery error for plugin '{plugin_id}': {e}",
            exc_info=True,
        )
        return ResponseModel(
            code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"MCP {transport_label} connection/discovery failed: {str(e)}",
        )

    # Discovery succeeded — purge every previously stored tool for this plugin
    # before inserting the freshly discovered set.
    _, existing_tools = plugin_repository.plugin_get(
        {"plugin_id": plugin_id, "space_id": space_id}
    )
    deleted_count = 0
    for existing in existing_tools or []:
        existing_tool_id = existing.get("tool_id", "") if isinstance(existing, dict) else ""
        if not existing_tool_id:
            continue
        del_res = tool_repository.tool_delete(
            {"tool_id": existing_tool_id, "space_id": space_id}
        )
        if ResponseModel(**del_res).code == status.HTTP_200_OK:
            deleted_count += 1
        else:
            logger.warning(
                f"Failed to delete old MCP tool '{existing_tool_id}' "
                f"for plugin '{plugin_id}' before re-discovery"
            )
    if deleted_count:
        logger.info(
            f"Deleted {deleted_count} existing MCP tool(s) for plugin '{plugin_id}' "
            f"before inserting newly discovered tools"
        )

    created_tool_ids: List[str] = []
    for card in tool_cards:
        tool_name = getattr(card, "name", "") or ""
        tool_desc = getattr(card, "description", "") or ""
        card_input_params = getattr(card, "input_params", None) or {}
        request_params = _mcp_card_input_params_to_tool_params(card_input_params)

        # Step 1: create the base record (available=False, input_parameters empty)
        mcp_req = PluginMcpBase(
            space_id=space_id,
            plugin_id=plugin_id,
            plugin_type=PluginType.PLUGIN_TYPE_CLOUD_MCP,
            name=tool_name,
            desc=tool_desc,
            transport=mcp_transport_enum,
            command=config.params.get("command", ""),
            args=config.params.get("args", []),
            env=config.params.get("env"),
            url=config.url,
            mcp_tool_name=tool_name,
        )

        create_result = plugin_create_mcp_tool(mcp_req, current_user)
        if create_result.code != status.HTTP_200_OK:
            logger.warning(
                f"Failed to create MCP tool '{tool_name}' for plugin '{plugin_id}': "
                f"{create_result.message}"
            )
            continue

        tool_id = create_result.data.get("tool_id") if isinstance(create_result.data, dict) else None
        if not tool_id:
            logger.warning(f"No tool_id returned for MCP tool '{tool_name}', skipping")
            continue

        # Step 2: update with parsed input_parameters so the column is properly populated.
        # plugin_update_mcp_tool() converts request_params → input_parameters via
        # _plugin_input_output_parameters(), which is what we need.
        mcp_info = PluginMcpInfo(
            space_id=space_id,
            plugin_id=plugin_id,
            plugin_type=PluginType.PLUGIN_TYPE_CLOUD_MCP,
            tool_id=tool_id,
            name=tool_name,
            desc=tool_desc,
            transport=mcp_transport_enum,
            command=config.params.get("command", ""),
            args=config.params.get("args", []),
            env=config.params.get("env"),
            url=config.url,
            mcp_tool_name=tool_name,
            request_params=request_params,
            response_params=[],
            available=False,
        )
        update_result = plugin_update_mcp_tool(mcp_info, current_user)
        if update_result.code != status.HTTP_200_OK:
            logger.warning(
                f"Failed to update input_parameters for MCP tool '{tool_name}' "
                f"(tool_id={tool_id}): {update_result.message}"
            )
            # Tool exists in DB, so still mark it available below.

        # Step 3: mark tool available
        plugin_tool_update_available(tool_id, space_id, True)
        created_tool_ids.append(tool_id)

    logger.info(
        f"MCP {transport_label} discovery complete for plugin '{plugin_id}': "
        f"{len(created_tool_ids)}/{len(tool_cards)} tools stored"
    )
    return ResponseModel(
        code=status.HTTP_200_OK,
        message=f"Discovered and stored {len(created_tool_ids)} MCP tools",
        data={"tool_ids": created_tool_ids},
    )


def _run_async_in_thread(coro) -> Any:
    """Run an async coroutine in a dedicated thread with its own event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


@with_exception_handling
def plugin_create(
        req: PluginCreate,
        current_user: dict
) -> ResponseModel:
    """创建新的插件"""
    _ = check_user_space(req.space_id, current_user)

    current_time = milliseconds()

    plugin_id = str(uuid.uuid4())

    rest_data: dict = {}
    if req.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_MCP and req.mcp_transport is not None:
        rest_data["mcp_transport"] = req.mcp_transport
        mcp_params = {}
        if req.command:
            mcp_params["command"] = req.command
        if req.args:
            mcp_params["args"] = req.args
        if req.env:
            mcp_params["env"] = req.env
        if mcp_params:
            rest_data["params"] = mcp_params

    plugin_dict = {
        "plugin_id": plugin_id,
        "name": req.name,
        "desc": req.desc,
        "desc_mk": req.desc_mk if hasattr(req, 'desc_mk') else "",
        "url": req.url,
        "icon_uri": req.icon_uri,
        "space_id": req.space_id,
        "plugin_type": req.plugin_type,
        "create_time": current_time,
        "update_time": current_time,
    }

    # Build plugin-level inputs from request_params and header_configuration
    all_inputs: List[PluginToolParam] = list(req.request_params or [])
    if hasattr(req, 'header_configuration') and req.header_configuration:
        header_params = _header_configuration_to_plugin_params(req.header_configuration)
        all_inputs = all_inputs + header_params
    if all_inputs:
        plugin_dict["inputs"] = [param.model_dump() for param in all_inputs]

    plugin = PluginBaseDBPd(**plugin_dict)
    logger.info(f"create plugin info: {plugin}")

    save_dict = plugin.model_dump()
    if rest_data:
        save_dict["_rest_"] = rest_data

    res = plugin_repository.plugin_create(save_dict)
    create_result = ResponseModel(**res)
    logger.info(f"create plugin info into db result: {create_result}")
    if create_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=create_result.code,
            message=create_result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create plugin success",
        data=PluginId(
            plugin_id=plugin_id,
            space_id=req.space_id,
        )
    )


@with_exception_handling
def plugin_discover_mcp_tools(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """
    Connect to an MCP server and discover its tools, persisting each one to the database.

    This is intentionally separate from plugin_create() so that the creation step
    is fast and the (potentially slow) MCP connection happens only when explicitly
    requested by the caller.
    """
    _ = check_user_space(req.space_id, current_user)

    # Load the plugin record from the database.
    res, _ = plugin_repository.plugin_get(req.model_dump())
    get_result = ResponseModel(**res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    data = get_result.data
    if hasattr(data, 'model_dump'):
        data_dict = data.model_dump()
    elif hasattr(data, 'dict'):
        data_dict = data.dict()
    else:
        data_dict = dict(data) if data else {}

    plugin_type = data_dict.get("plugin_type")
    if plugin_type != PluginType.PLUGIN_TYPE_CLOUD_MCP:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Plugin is not an MCP plugin",
        )

    url = data_dict.get("url", "")
    rest = data_dict.get("_rest_") or {}
    transport = rest.get("mcp_transport", PluginMcpTransport.PLUGIN_MCP_TRANSPORT_SSE)
    command = rest.get("command", "")
    args = rest.get("args", [])
    env = rest.get("env")

    # Collect header-type plugin inputs so they can be forwarded to the MCP client.
    auth_headers = _extract_auth_headers(data_dict)
    if auth_headers:
        logger.info(
            f"Passing {len(auth_headers)} auth header(s) to MCP client "
            f"for plugin '{req.plugin_id}': {list(auth_headers.keys())}"
        )

    is_stdio = transport == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO
    if not url and not (is_stdio and command):
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="MCP plugin requires a server URL (or a command for stdio transport)",
        )

    transport_name = (
        PluginMcpTransport(transport).name
        if transport in [t.value for t in PluginMcpTransport]
        else str(transport)
    )
    logger.info(
        f"Starting MCP {transport_name} tool discovery for plugin '{req.plugin_id}' at '{url}'"
    )

    mcp_result = _run_async_in_thread(
        _discover_and_create_mcp_tools(
            config=_McpConnectionConfig(
                transport=transport,
                url=url,
                command=command,
                args=args or [],
                env=env,
                auth_headers=auth_headers,
            ),
            plugin_id=req.plugin_id,
            space_id=req.space_id,
            current_user=current_user,
        )
    )

    logger.info(
        f"MCP {transport_name} tool discovery for plugin '{req.plugin_id}': {mcp_result.message}"
    )
    return mcp_result


@with_exception_handling
def plugin_discover_mcp_tools(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """
    Connect to an MCP server and discover its tools, persisting each one to the database.

    This is intentionally separate from plugin_create() so that the creation step
    is fast and the (potentially slow) MCP connection happens only when explicitly
    requested by the caller.
    """
    _ = check_user_space(req.space_id, current_user)

    # Load the plugin record from the database.
    res, _ = plugin_repository.plugin_get(req.model_dump())
    get_result = ResponseModel(**res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    data = get_result.data
    if hasattr(data, 'model_dump'):
        data_dict = data.model_dump()
    elif hasattr(data, 'dict'):
        data_dict = data.dict()
    else:
        data_dict = dict(data) if data else {}

    plugin_type = data_dict.get("plugin_type")
    if plugin_type != PluginType.PLUGIN_TYPE_CLOUD_MCP:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Plugin is not an MCP plugin",
        )

    url = data_dict.get("url", "")
    rest = data_dict.get("_rest_") or {}
    transport = rest.get("mcp_transport", PluginMcpTransport.PLUGIN_MCP_TRANSPORT_SSE)
    mcp_params = rest.get("params", {})

    # Collect header-type plugin inputs so they can be forwarded to the MCP client.
    auth_headers = _extract_auth_headers(data_dict)
    if auth_headers:
        logger.info(
            f"Passing {len(auth_headers)} auth header(s) to MCP client "
            f"for plugin '{req.plugin_id}': {list(auth_headers.keys())}"
        )

    is_stdio = transport == PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO
    if not url and not (is_stdio and mcp_params.get("command")):
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="MCP plugin requires a server URL (or params['command'] for stdio transport)",
        )

    transport_name = (
        PluginMcpTransport(transport).name
        if transport in [t.value for t in PluginMcpTransport]
        else str(transport)
    )
    logger.info(
        f"Starting MCP {transport_name} tool discovery for plugin '{req.plugin_id}' at '{url}'"
    )

    mcp_result = _run_async_in_thread(
        _discover_and_create_mcp_tools(
            config=_McpConnectionConfig(
                transport=transport,
                url=url,
                params=mcp_params,
                auth_headers=auth_headers,
            ),
            plugin_id=req.plugin_id,
            space_id=req.space_id,
            current_user=current_user,
        )
    )

    logger.info(
        f"MCP {transport_name} tool discovery for plugin '{req.plugin_id}': {mcp_result.message}"
    )
    return mcp_result


@with_exception_handling
def plugin_get(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """获取插件信息"""
    _ = check_user_space(req.space_id, current_user)

    res, _ = plugin_repository.plugin_get(req.model_dump())
    canvas_result = ResponseModel(**res)
    logger.info(f"get plugin info from db result: {canvas_result}")
    if canvas_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=canvas_result.code,
            message=canvas_result.message,
        )
    # 使用字段映射方法将数据库的 inputs 映射为 request_params
    plugin_info = PluginInfo.from_db_with_mapping(canvas_result.data)
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin success",
        data=PluginInfoResponse(plugin_info=plugin_info)
    )


@with_exception_handling
def plugin_update(
        req: PluginInfo,
        current_user: dict
) -> ResponseModel:
    """获取插件信息"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"update plugin: {req}")
    res, _ = plugin_repository.plugin_get(req.model_dump())
    get_result = ResponseModel(**res)
    logger.info(f"get plugin info from db result: {get_result}")
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )
    # Handle both dict and Pydantic model types
    data = get_result.data
    if hasattr(data, 'model_dump'):
        data_dict = data.model_dump()
    elif hasattr(data, 'dict'):
        data_dict = data.dict()
    else:
        data_dict = data
    plugin = PluginBaseDBPd(**data_dict)
    update_dict = {
        "name": req.name,
        "desc": req.desc,
        "url": req.url,
        "icon_uri": req.icon_uri,
    }

    if hasattr(req, 'desc_mk') and req.desc_mk is not None:
        update_dict["desc_mk"] = req.desc_mk

    # 将 request_params 映射到数据库字段 inputs
    if hasattr(req, 'request_params') and req.request_params is not None:
        update_dict["inputs"] = [param.model_dump() for param in req.request_params]

    for key, value in update_dict.items():
        setattr(plugin, key, value)

    res = plugin_repository.plugin_save(plugin.model_dump())
    result = ResponseModel(**res)
    logger.info(f"update plugin info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    # 同步更新引用了该插件的Agent中的插件名称
    try:
        if hasattr(req, 'name') and req.name:
            agent_repository.update_plugin_name_in_agents(
                space_id=req.space_id,
                plugin_id=req.plugin_id,
                new_plugin_name=req.name
            )
    except Exception as e:
        logger.error(f"Failed to sync plugin name to agents: {e}", exc_info=True)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="update plugin success",
    )


@with_exception_handling
def plugin_delete(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """删除插件"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"delete plugin: {req}")

    # 1. 检查该plugin是否被引用
    try:
        can_delete, message = check_referenced_dependencies(
            reference_repository, req.space_id, "PLUGIN", req.plugin_id
        )

        if not can_delete:
            logger.warning(f"plugin deletion blocked due to dependencies: {req.plugin_id} - {message}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=message,
            )
    except Exception as e:
        logger.error(f"Plugin dependency check failed for {req.plugin_id}: {e}")
        # 依赖检查失败时，为安全起见阻止删除
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unable to verify plugin dependencies, deletion blocked for safety",
        )

    # 2. 删除所有与该插件相关的工具
    try:
        tools_list_res = tool_repository.tool_list({
            "space_id": req.space_id
        })
        tools_result = ResponseModel(**tools_list_res)

        if tools_result.code == status.HTTP_200_OK and tools_result.data:
            tools = tools_result.data if isinstance(tools_result.data, list) else []

            for tool in tools:
                tool_dict = tool if isinstance(tool, dict) else tool.model_dump() if hasattr(tool,
                                                                                                 'model_dump') else {}
                if tool_dict.get("plugin_id") == req.plugin_id:
                    tool_id = tool_dict.get("tool_id", "")
                    if tool_id:
                        # Use plugin_delete_tool for proper validation and reference checking
                        delete_tool_result = plugin_delete_tool(
                            PluginToolId(
                                space_id=req.space_id,
                                plugin_id=req.plugin_id,
                                tool_id=tool_id
                            ),
                            current_user
                        )
                        if delete_tool_result.code != status.HTTP_200_OK:
                            logger.warning(
                                f"Failed to delete tool {tool_id} for plugin {req.plugin_id}: "
                                f"{delete_tool_result.message}")
    except Exception as e:
        logger.warning(f"Error deleting tools for plugin {req.plugin_id}: {e}", exc_info=True)

    # 3. 执行删除操作
    res = plugin_repository.plugin_delete(req.model_dump())
    delete_result = ResponseModel(**res)
    logger.info(f"delete plugin info in db result: {delete_result}")
    if delete_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete plugin success",
    )


@with_exception_handling
def plugin_list(
        req: PluginList,
        current_user: dict
) -> ResponseModel:
    """获取插件列表"""
    _ = check_user_space(req.space_id, current_user)

    res = plugin_repository.plugin_list(req.model_dump())
    list_result = ResponseModel(**res)
    logger.info(f"get plugin list from db result: {list_result}")
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    # 处理返回数据
    if list_result.data is None:
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get plugin success",
            data=PluginListResponse(
                plugin_infos=[],
                pagination={
                    "total": 0,
                    "total_pages": 1,
                    "page": req.page or 1,
                    "page_size": req.size or 10
                }
            )
        )

    # 转换插件信息
    infos: List[PluginInfo] = []
    plugin_data = list_result.data.get("plugin_infos", [])
    for info_dict in plugin_data:
        info = PluginInfo(**info_dict)
        infos.append(info)

    # 获取分页信息
    pagination_data = list_result.data.get("pagination", {})
    pagination = PluginListPagination(**pagination_data) if pagination_data else PluginListPagination(
        total=0,
        total_pages=1,
        page=req.page or 1,
        page_size=req.size or 10
    )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin success",
        data=PluginListResponse(
            plugin_infos=infos,
            pagination=pagination
        )
    )


@with_exception_handling
def plugin_convert(
        req: ToolId,
        current_user: dict
) -> ResponseModel:
    """转换插件"""
    _ = check_user_space(req.space_id, current_user)

    get_res, plugin_dict = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )
    tool_info = get_result.data
    plugin = convert.plugin_convert(PluginBaseDBPd(**plugin_dict), tool_info.model_dump())
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="convert plugin success",
        data=plugin
    )


@with_exception_handling
def plugin_create_api(
        req: PluginApiInfoCreate,
        current_user: dict
) -> ResponseModel:
    """创建插件API"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"create plugin api info: {req}")

    # Ensure request_params have proper method set for all parameter types
    request_params = req.request_params if hasattr(req, 'request_params') else []
    for param in request_params:
        # Only set method if it's not already set (NONE or falsy)
        if param.method == ParamSendMethod.PARAM_SEND_METHOD_NONE or not param.method:
            # Check if parameter name is in the path template
            if f"{{{param.name}}}" in req.path:
                param.method = ParamSendMethod.PARAM_SEND_METHOD_PATH
            else:
                # For non-path parameters, default to query if method is not set
                param.method = ParamSendMethod.PARAM_SEND_METHOD_QUERY
        # If method is already explicitly set (HEADER, QUERY, BODY, PATH), keep it as is

    api_info = PluginApiInfo(
        space_id=req.space_id,
        plugin_id=req.plugin_id,
        plugin_type=PluginType.PLUGIN_TYPE_CLOUD_API,
        tool_id=str(uuid.uuid4()),
        name=req.name,
        desc=req.desc,
        path=req.path,
        method=req.method,
        available=False,
        request_params=request_params,
        response_params=req.response_params if hasattr(req, 'response_params') else [],
        headers=req.headers if hasattr(req, 'headers') else [],
    )

    # Convert to PluginApiInfoDB format for database storage
    # This ensures request_params are converted to input_parameters for the database
    # Header-method params belong at the plugin level (plugin.inputs), not tool level
    tool_params = [p for p in request_params if p.method != ParamSendMethod.PARAM_SEND_METHOD_HEADER]
    api_info_db = PluginApiInfoDB(**(api_info.model_dump()))
    api_info_db.input_parameters = _plugin_input_output_parameters(tool_params)
    api_info_db.output_parameters = _plugin_input_output_parameters(req.response_params
                                                                    if hasattr(req, 'response_params') else [])

    res = tool_repository.tool_create(api_info_db.model_dump())
    result = ResponseModel(**res)
    logger.info(f"create plugin api info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create plugin api success",
        data={"tool_id": api_info.tool_id},
    )


def _plugin_input_output_parameters(params: List[PluginToolParam]) -> List[Dict[str, Any]]:
    input_output_params: List[Dict[str, Any]] = []
    for param in params:
        param_dict = param.model_dump()
        input_output_params.append(param_dict)

    return input_output_params


def _input_parameters_to_request_params(input_parameters: List[Dict[str, Any]]) -> List[PluginToolParam]:
    """Convert input_parameters from database to request_params for API response"""
    if not input_parameters:
        return []

    request_params = []
    for param in input_parameters:
        # Convert type field from string to enum if needed
        if isinstance(param.get("type"), str):
            for key, value in param_type_mapping.items():
                if value == param.get('type'):
                    param["type"] = key
                    break

        # Convert method field: if it's an integer, convert to ParamSendMethod enum
        if "method" in param and isinstance(param.get("method"), int):
            try:
                param["method"] = ParamSendMethod(param["method"])
            except (ValueError, KeyError):
                # If conversion fails, leave it as is
                pass

        request_param = PluginToolParam(**param)
        request_params.append(request_param)

    return request_params


def _plugin_update_tool(
        plugin_id: str,
        req: Dict[str, Any]
) -> ResponseModel:
    get_res, _ = tool_repository.tool_get(req)
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    # tool is already a dict from database, not a Pydantic model
    tool_plugin_id = tool.get('plugin_id') if isinstance(tool, dict) else tool.plugin_id
    tool_version = tool.get('plugin_version') if isinstance(tool, dict) else tool.plugin_version

    if tool_plugin_id != plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # 确保 req 中包含 plugin_version，因为唯一约束是 (tool_id, plugin_version)
    # 从已获取的 tool 对象中获取 plugin_version，确保更新时能正确找到记录
    if 'plugin_version' not in req or not req.get('plugin_version'):
        req['plugin_version'] = tool_version if tool_version else ToolBaseDB.__version_none__

    # 确保req中如果没有修改，则不修改available的状态
    # 将 tool 转换为 dict
    if not isinstance(tool, dict):
        tool_dict = tool.to_dict() if hasattr(tool, 'to_dict') else tool.model_dump()
    else:
        tool_dict = tool.copy()

    # 需要对比的字段
    need_compare_fields = {'name', 'desc', 'input_parameters', 'output_parameters', 'plugin_id', 'plugin_type',
                           'plugin_version', 'space_id', 'tool_id', 'headers', 'method', 'path', 'request_params',
                           'response_params'}

    def to_plain(val: Any) -> Any:
        # IntEnum/Enum -> int/基础值
        if isinstance(val, Enum):
            return val.value
        # Pydantic Model -> dict
        if isinstance(val, BaseModel):
            return to_plain(val.model_dump())
        if isinstance(val, dict):
            return {k: to_plain(v) for k, v in val.items()}
        if isinstance(val, list):
            return [to_plain(v) for v in val]
        return val

    # 创建用于比较的字典（指定字段）
    def normalize_for_db_comparison(data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for key in need_compare_fields:
            if key in data:
                normalized[key] = to_plain(data[key])
        return normalized

    tool_normalized = normalize_for_db_comparison(tool_dict)
    req_normalized = normalize_for_db_comparison(req)

    # 比较 req 和 tool 的内容
    if tool_normalized != req_normalized:
        # 内容不一致，设置 available=False
        req['available'] = False
    else:
        # 内容一致，保持 available 不变（从数据库中获取的值）
        req['available'] = tool_dict.get('available', False)

    res = tool_repository.tool_save(req)
    result = ResponseModel(**res)
    logger.info(f"update plugin tool info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    # 同步更新引用了该工具的Agent中的工具名称
    try:
        if 'name' in req:
            tool_id = req.get('tool_id')
            space_id = req.get('space_id')
            new_name = req.get('name')

            if tool_id and space_id and new_name:
                agent_repository.update_tool_name_in_agents(
                    space_id=space_id,
                    tool_id=tool_id,
                    new_tool_name=new_name
                )
    except Exception as e:
        logger.error(f"Failed to sync tool name to agents: {e}", exc_info=True)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="update plugin tool success",
    )


@with_exception_handling
def plugin_update_api(
        req: PluginApiInfo,
        current_user: dict
) -> ResponseModel:
    """更新插件API"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("update plugin api info")

    # Ensure request_params have proper method set for all parameter types
    request_params = req.request_params if hasattr(req, 'request_params') else []
    for param in request_params:
        # Only set method if it's not already set (NONE or falsy)
        if param.method == ParamSendMethod.PARAM_SEND_METHOD_NONE or not param.method:
            # Check if parameter name is in the path template
            if f"{{{param.name}}}" in req.path:
                param.method = ParamSendMethod.PARAM_SEND_METHOD_PATH
            else:
                # For non-path parameters, default to query if method is not set
                param.method = ParamSendMethod.PARAM_SEND_METHOD_QUERY
        # If method is already explicitly set (HEADER, QUERY, BODY, PATH), keep it as is

    # Create a dict from req - this properly serializes all fields including enums
    api_dict = req.model_dump()
    # Serialize the modified request_params to dicts (converts enums to integers)
    api_dict['request_params'] = [param.model_dump() for param in request_params]

    # Header-method params belong at plugin level (plugin.inputs), not tool level
    tool_params = [p for p in request_params if p.method != ParamSendMethod.PARAM_SEND_METHOD_HEADER]
    update_api = PluginApiInfoDB(**api_dict)
    update_api.input_parameters = _plugin_input_output_parameters(tool_params)
    update_api.output_parameters = _plugin_input_output_parameters(req.response_params)
    return _plugin_update_tool(req.plugin_id, update_api.model_dump())


@with_exception_handling
def plugin_delete_tool(
        req: PluginToolId,
        current_user: dict
) -> ResponseModel:
    """删除插件工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("delete plugin tool")
    get_res, _ = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    if tool.plugin_id != req.plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # 检查tool是否被其他资源引用
    can_delete, message = check_referenced_dependencies(
        reference_repository, req.space_id, "TOOL", req.tool_id
    )
    if not can_delete:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=message,
        )

    res = tool_repository.tool_delete(req.model_dump())
    result = ResponseModel(**res)
    logger.info(f"delete plugin tool info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete plugin tool success",
    )


@with_exception_handling
def plugin_get_api(
        req: PluginToolId,
        current_user: dict
) -> ResponseModel:
    """获取插件API"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("get plugin api")
    get_res, _ = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    if tool.plugin_id != req.plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # tool is already a dict from database, not a Pydantic model
    api_dict = tool if isinstance(tool, dict) else tool.model_dump()
    if 'available' not in api_dict or api_dict.get('available') is None:
        api_dict['available'] = True

    # Convert input_parameters to request_params with runtime and value
    if 'input_parameters' in api_dict and api_dict['input_parameters']:
        request_params = _input_parameters_to_request_params(api_dict['input_parameters'])
        api_dict['request_params'] = [param.model_dump() for param in request_params]

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin api success",
        data=PluginApiInfoResponse(
            api_info=[PluginApiInfo(**api_dict)],
            total=1,
        )
    )


@with_exception_handling
def plugin_list_api(
        req: PluginListTool,
        current_user: dict
) -> ResponseModel:
    """获取插件API列表"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("list plugin api")
    list_res, tool_list = plugin_repository.plugin_get(req.model_dump())
    list_result = ResponseModel(**list_res)
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    api_infos: List[PluginApiInfo] = []
    for info_dict in tool_list:
        logger.info(f"tool: {info_dict}")
        if 'available' not in info_dict or info_dict.get('available') is None:
            info_dict['available'] = True

        # Convert input_parameters to request_params with runtime and value
        if 'input_parameters' in info_dict and info_dict['input_parameters']:
            request_params = _input_parameters_to_request_params(info_dict['input_parameters'])
            info_dict['request_params'] = [param.model_dump() for param in request_params]

        info = PluginApiInfo(**info_dict)
        if info.plugin_id == req.plugin_id:
            api_infos.append(info)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="list plugin api success",
        data=PluginApiInfoResponse(
            api_info=api_infos,
            total=len(api_infos),
        )
    )


@with_exception_handling
def plugin_create_code(
        req: PluginCodeBase,
        current_user: dict
) -> ResponseModel:
    """创建插件code工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("create plugin code info")

    code_info = PluginCodeInfo(
        space_id=req.space_id,
        plugin_id=req.plugin_id,
        plugin_type=PluginType.PLUGIN_TYPE_CLOUD_CODE,
        tool_id=str(uuid.uuid4()),
        name=req.name,
        desc=req.desc,
        language=req.language,
        code=req.code,
        available=False,
    )

    res = tool_repository.tool_create(code_info.model_dump())
    result = ResponseModel(**res)
    logger.info(f"create plugin code info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create plugin code success",
        data={"tool_id": code_info.tool_id},
    )


@with_exception_handling
def plugin_update_code(
        req: PluginCodeInfo,
        current_user: dict
) -> ResponseModel:
    """更新插件code工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("update plugin code info")
    update_code = PluginCodeInfoDB(**(req.model_dump()))
    update_code.input_parameters = _plugin_input_output_parameters(req.request_params)
    update_code.output_parameters = _plugin_input_output_parameters(req.response_params)
    return _plugin_update_tool(req.plugin_id, update_code.model_dump())


@with_exception_handling
def plugin_get_code(
        req: PluginToolId,
        current_user: dict
) -> ResponseModel:
    """获取插件code工具信息"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("get plugin code")
    get_res, _ = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    # tool is already a dict from database, not a Pydantic model
    tool_plugin_id = tool.get('plugin_id') if isinstance(tool, dict) else tool.plugin_id

    if tool_plugin_id != req.plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    # tool is already a dict from database, not a Pydantic model
    tool_dict = tool if isinstance(tool, dict) else tool.model_dump()

    # Convert input_parameters to request_params with runtime and value
    if 'input_parameters' in tool_dict and tool_dict['input_parameters']:
        request_params = _input_parameters_to_request_params(tool_dict['input_parameters'])
        tool_dict['request_params'] = [param.model_dump() for param in request_params]

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin code success",
        data=PluginCodeInfoResponse(
            code_info=[PluginCodeInfo(**tool_dict)],
            total=1,
        )
    )


@with_exception_handling
def plugin_list_code(
        req: PluginListTool,
        current_user: dict
) -> ResponseModel:
    """获取插件code工具列表"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("list plugin code")
    list_res, tool_list = plugin_repository.plugin_get(req.model_dump())
    list_result = ResponseModel(**list_res)
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    code_infos: List[PluginCodeInfo] = []
    for info_dict in tool_list:
        info = PluginCodeInfo(**info_dict)
        if info.plugin_id == req.plugin_id:
            code_infos.append(info)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="list plugin code success",
        data=PluginCodeInfoResponse(
            code_info=code_infos,
            total=len(code_infos),
        )
    )


@with_exception_handling
def plugin_create_mcp_tool(
        req: PluginMcpBase,
        current_user: dict
) -> ResponseModel:
    """创建插件MCP工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("create plugin mcp tool info")

    mcp_info = PluginMcpInfo(
        space_id=req.space_id,
        plugin_id=req.plugin_id,
        plugin_type=PluginType.PLUGIN_TYPE_CLOUD_MCP,
        tool_id=str(uuid.uuid4()),
        name=req.name,
        desc=req.desc,
        transport=req.transport,
        command=req.command,
        args=req.args,
        env=req.env,
        url=req.url,
        headers=req.headers,
        mcp_tool_name=req.mcp_tool_name,
        available=False,
    )

    res = tool_repository.tool_create(mcp_info.model_dump())
    result = ResponseModel(**res)
    logger.info(f"create plugin mcp info in db result: {result}")
    if result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=result.code,
            message=result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create plugin mcp success",
        data={"tool_id": mcp_info.tool_id},
    )


@with_exception_handling
def plugin_update_mcp_tool(
        req: PluginMcpInfo,
        current_user: dict
) -> ResponseModel:
    """更新插件MCP工具"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("update plugin mcp tool info")
    update_mcp = PluginMcpInfoDB(**(req.model_dump()))
    update_mcp.input_parameters = _plugin_input_output_parameters(req.request_params)
    update_mcp.output_parameters = _plugin_input_output_parameters(req.response_params)
    return _plugin_update_tool(req.plugin_id, update_mcp.model_dump())


@with_exception_handling
def plugin_get_mcp_tool(
        req: PluginToolId,
        current_user: dict
) -> ResponseModel:
    """获取插件MCP工具信息"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("get plugin mcp tool")
    get_res, _ = tool_repository.tool_get(req.model_dump())
    get_result = ResponseModel(**get_res)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    tool = get_result.data
    tool_plugin_id = tool.get('plugin_id') if isinstance(tool, dict) else tool.plugin_id

    if tool_plugin_id != req.plugin_id:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="plugin id is not match",
        )

    tool_dict = tool if isinstance(tool, dict) else tool.model_dump()

    if 'input_parameters' in tool_dict and tool_dict['input_parameters']:
        request_params = _input_parameters_to_request_params(tool_dict['input_parameters'])
        tool_dict['request_params'] = [param.model_dump() for param in request_params]

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get plugin mcp success",
        data=PluginMcpInfoResponse(
            mcp_info=[PluginMcpInfo(**tool_dict)],
            total=1,
        )
    )


@with_exception_handling
def plugin_list_mcp_tools(
        req: PluginListTool,
        current_user: dict
) -> ResponseModel:
    """获取插件MCP工具列表"""
    _ = check_user_space(req.space_id, current_user)

    logger.info("list plugin mcp tools")
    list_res, tool_list = plugin_repository.plugin_get(req.model_dump())
    list_result = ResponseModel(**list_res)
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    mcp_infos: List[PluginMcpInfo] = []
    for info_dict in tool_list:
        if 'input_parameters' in info_dict and info_dict['input_parameters']:
            request_params = _input_parameters_to_request_params(info_dict['input_parameters'])
            info_dict['request_params'] = [param.model_dump() for param in request_params]
        info = PluginMcpInfo(**info_dict)
        if info.plugin_id == req.plugin_id:
            mcp_infos.append(info)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="list plugin mcp success",
        data=PluginMcpInfoResponse(
            mcp_info=mcp_infos,
            total=len(mcp_infos),
        )
    )


def _compare_versions(ver1, ver2):
    v1 = version.parse(ver1)
    v2 = version.parse(ver2)

    if v1 < v2:
        return True
    return False


@with_exception_handling
def plugin_publish(
        req: PluginPublish,
        current_user: dict
) -> ResponseModel:
    """
    发布插件

    Args:
        req: 插件发布请求
        current_user: 当前用户信息

    Returns:
        ResponseModel: 发布结果
    """
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    plugin_query = {
        "plugin_id": req.plugin_id,
        "space_id": req.space_id
    }

    # 2. 获取最新版本信息
    res = plugin_repository.plugin_publish_get(plugin_query)
    get_version_result = ResponseModel(**res)
    logger.info(f"get version plugin info: {get_version_result}")

    if get_version_result.code == status.HTTP_404_NOT_FOUND:
        latest_version = "0.0.0"  # 初始版本
    elif get_version_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_version_result.code,
            message=f"Get versioned plugin with id {req.plugin_id} failed, error: {get_version_result.message}",
            data=None
        )
    else:
        latest_version_data = PluginPublishDBPd(**get_version_result.data)
        latest_version = latest_version_data.plugin_version

    # 3. 检查版本格式和递增性（除非强制发布）
    if not req.force:
        is_valid = _compare_versions(latest_version, req.plugin_version)
        if not is_valid:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"Version check failed",
                data=None
            )

    # 4. 获取插件草稿内容
    plugin_draft_query = {
        "plugin_id": req.plugin_id,
        "space_id": req.space_id,
    }

    draft_result, tool_list = plugin_repository.plugin_get(plugin_draft_query)
    draft_response = ResponseModel(**draft_result)

    if draft_response.code != status.HTTP_200_OK:
        return ResponseModel(
            code=draft_response.code,
            message=f"Get plugin draft failed: {draft_response.message}",
            data=None
        )

    plugin_data = draft_response.data
    plugin_info = PluginBaseDBPd(**(plugin_data.model_dump()))

    # 5. 创建发布版本
    publish_data = {
        "plugin_id": req.plugin_id,
        "name": plugin_info.name,
        "desc": plugin_info.desc,
        "desc_mk": plugin_info.desc_mk,
        "plugin_version": req.plugin_version,
        "version_desc": req.version_desc,
        "url": plugin_info.url,
        "icon_uri": plugin_info.icon_uri,
        "plugin_type": plugin_info.plugin_type,
        "space_id": req.space_id,
        "inputs": plugin_info.inputs,
        "tools": tool_list,
        "create_time": milliseconds(),
        "update_time": milliseconds()
    }

    # 6. 保存发布版本
    publish_result = plugin_repository.plugin_publish_create(publish_data)
    publish_response = ResponseModel(**publish_result)

    if publish_response.code != status.HTTP_200_OK:
        return ResponseModel(
            code=publish_response.code,
            message=f"Create plugin publish version failed: {publish_response.message}",
            data=None
        )

    # 7. 返回发布结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Plugin published successfully",
        data=PluginPublishResponse(
            plugin_id=req.plugin_id,
            version=req.plugin_version,
            published_at=str(milliseconds())
        )
    )


@with_exception_handling
def plugin_publish_list(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """
    发布插件

    Args:
        req: 插件发布列表请求
        current_user: 当前用户信息

    Returns:
        ResponseModel: 发布列表查询结果
    """
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    res = plugin_repository.plugin_publish_list(req.model_dump())
    list_result = ResponseModel(**res)
    logger.info(f"get plugin list from db result: {list_result}")
    if list_result.code != status.HTTP_200_OK and list_result.code != status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    infos: List[PluginPublishInfo] = []
    if list_result.data is not None:
        for info_dict in list_result.data:
            # 使用 from_db_with_mapping 将 inputs 映射为 request_params
            info = PluginPublishInfo.from_db_with_mapping(info_dict)
            infos.append(info)
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="plugin publish list success",
        data=PluginPublishListResponse(plugin_infos=infos)
    )


@with_exception_handling
def plugin_publish_get(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """获取发布插件信息"""
    _ = check_user_space(req.space_id, current_user)

    res = plugin_repository.plugin_publish_get(req.model_dump())
    canvas_result = ResponseModel(**res)
    logger.info(f"get publish plugin info from db result: {canvas_result}")
    if canvas_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=canvas_result.code,
            message=canvas_result.message,
        )
    # 使用 from_db_with_mapping 将 inputs 映射为 request_params
    plugin_info = PluginPublishInfo.from_db_with_mapping(canvas_result.data)
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get publish plugin success",
        data=PluginPublishInfoResponse(plugin_info=plugin_info)
    )


@with_exception_handling
def plugin_publish_delete(
        req: PluginId,
        current_user: dict
) -> ResponseModel:
    """删除已发布的插件"""
    _ = check_user_space(req.space_id, current_user)

    logger.info(f"delete publish plugin: {req}")
    res = plugin_repository.plugin_publish_delete(req.model_dump())
    delete_result = ResponseModel(**res)
    logger.info(f"delete publish plugin info in db result: {delete_result}")
    if delete_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete publish plugin success",
    )


def _process_header_configuration(plugin_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process the header_configuration section of a plugin and extract header definitions.

    Returns a list of PluginApiHeader-compatible dicts that can be stored at plugin level
    and included with each API call.

    Args:
        plugin_data: Plugin configuration data

    Returns:
        List of header dicts with name, value, description fields
    """
    raw = plugin_data.get("header_configuration")
    if not raw:
        return []

    header_config = _normalize_header_configuration(raw)
    if not header_config:
        return []

    headers = []

    # Each key in header_configuration is a header name (e.g., "Authorization")
    for header_name, header_details in header_config.items():
        if not isinstance(header_details, dict):
            continue

        # Resolve type integer
        type_str = header_details.get("type", "string")
        if isinstance(type_str, str):
            param_type_enum = _JSON_SCHEMA_TYPE_TO_PARAM_TYPE.get(type_str.lower(), ParamType.PARAM_TYPE_STRING)
            type_int = param_type_enum.value
        else:
            type_int = ParamType.PARAM_TYPE_STRING.value

        # Resolve send_method integer
        method_str = header_details.get("send_method", "Header")
        if isinstance(method_str, str):
            method_int = _SEND_METHOD_STR_TO_INT.get(method_str, 1)
        else:
            method_int = 1  # PARAM_SEND_METHOD_HEADER

        header_dict = {
            "name": header_name,
            "value": header_details.get("value", ""),
            "description": header_details.get("description", ""),
            "type": type_int,
            "method": method_int,
        }

        headers.append(header_dict)
        logger.info(f"Processed header configuration for '{header_name}' (type={type_int}, method={method_int})")

    return headers


def _process_plugin_parameters(plugin_data: Dict[str, Any]) -> None:
    """
    Process plugin parameters to handle format conversion and path parameters.
    Converts marketplace JSON parameter format to database PluginToolParam format:
    - "description" -> "desc"
    - "required" -> "is_required"
    - "send_method" string (Path/Query/Body/Header/None) -> "method" integer (0-4)
    - "type" string values -> ParamType enum integers (e.g., "string" -> 1)

    Also processes the "header_configuration" section and stores headers at plugin level.
    Headers are NOT added to request_params - they are kept separate in a "headers" field.

    Args:
        plugin_data: Plugin configuration data (modified in place)
    """
    # Mapping from string type names to ParamType enum integer values
    # Using integer values directly so they serialize/deserialize correctly with JSON
    type_mapping = {
        "string": 1,  # PARAM_TYPE_STRING
        "integer": 2,  # PARAM_TYPE_INT
        "number": 3,  # PARAM_TYPE_FLOAT
        "boolean": 4,  # PARAM_TYPE_BOOL
        "object": 5,  # PARAM_TYPE_OBJECT
        "array": 6,  # PARAM_TYPE_ARRAY_STRING (default array type)
    }

    # Mapping for array element types to specific array enum values
    array_type_mapping = {
        "string": 6,   # PARAM_TYPE_ARRAY_STRING
        "integer": 7,  # PARAM_TYPE_ARRAY_INT
        "number": 8,   # PARAM_TYPE_ARRAY_FLOAT
        "boolean": 9,  # PARAM_TYPE_ARRAY_BOOL
        # Aliases
        "int": 7,
        "float": 8,
        "bool": 9,
    }

    # Mapping from send_method string to ParamSendMethod enum integer values
    send_method_mapping = {
        "None": 0,   # PARAM_SEND_METHOD_NONE
        "Header": 1,  # PARAM_SEND_METHOD_HEADER
        "Query": 2,   # PARAM_SEND_METHOD_QUERY
        "Body": 3,    # PARAM_SEND_METHOD_BODY
        "Path": 4,    # PARAM_SEND_METHOD_PATH
        # Lowercase variants for compatibility
        "none": 0,
        "header": 1,
        "query": 2,
        "body": 3,
        "path": 4,
    }

    # Process header_configuration section and store at plugin level
    # Headers are NOT added to request_params - they're kept separate
    headers = _process_header_configuration(plugin_data)
    if headers:
        plugin_data["headers"] = headers

    tools = plugin_data.get("tools", [])
    for tool in tools:
        request_params = tool.get("request_params", {})
        if not isinstance(request_params, dict):
            continue

        for param_name, param_config in request_params.items():
            if not isinstance(param_config, dict):
                continue

            # Convert "description" to "desc" if present
            if "description" in param_config and "desc" not in param_config:
                param_config["desc"] = param_config.pop("description")

            # Convert "required" to "is_required" if present
            if "required" in param_config and "is_required" not in param_config:
                param_config["is_required"] = param_config.pop("required")

            # Convert "type" from string to ParamType integer value
            if "type" in param_config and isinstance(param_config["type"], str):
                type_str = param_config["type"].lower()

                # Handle array types with item_type specification
                if type_str == "array":
                    if "item_type" in param_config:
                        # Specific array type based on item_type
                        item_type = param_config["item_type"].lower()
                        param_config["type"] = array_type_mapping.get(item_type, 6)  # Default to ARRAY_STRING
                        # Remove item_type as it's now encoded in the type value
                        del param_config["item_type"]
                    else:
                        # Array without item_type - default to ARRAY_STRING (generic array)
                        param_config["type"] = 6  # PARAM_TYPE_ARRAY_STRING
                else:
                    param_config["type"] = type_mapping.get(type_str, 1)  # Default to string type

            # Handle send_method field
            method_value = None

            # Check for send_method (standard)
            if "send_method" in param_config:
                method_str = param_config.pop("send_method")
                method_value = send_method_mapping.get(method_str, 2)  # Default to Query

            # Set method value if determined
            if method_value is not None:
                param_config["method"] = method_value
            elif "method" not in param_config or param_config.get("method") is None:
                # Default to Query if no method specified
                param_config["method"] = 2  # PARAM_SEND_METHOD_QUERY

        # Note: Headers are now stored at plugin level, not added to request_params
        # This keeps them separate from input parameters in the GUI


def _load_plugin_schema() -> Dict[str, Any]:
    """
    Load the JSON schema for plugin validation.

    Returns:
        Dict containing the JSON schema, or None if not found
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../marketplace/"))
    schema_file = os.path.join(base_dir, "ready_plugins", "schema.json")

    if not os.path.exists(schema_file):
        logger.warning(f"Plugin schema file not found: {schema_file}")
        return None

    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load plugin schema: {str(e)}")
        return None


def _validate_plugin_config(plugin_data: Dict[str, Any], plugin_file: str = "") -> tuple[bool, str]:
    """
    Validate a plugin configuration against the JSON schema.

    Args:
        plugin_data: The plugin configuration data
        plugin_file: The file path (for error messages)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not JSONSCHEMA_AVAILABLE:
        logger.debug("Skipping plugin validation (jsonschema not available)")
        return True, ""

    schema = _load_plugin_schema()
    if not schema:
        logger.debug("Skipping plugin validation (schema not found)")
        return True, ""

    try:
        jsonschema.validate(instance=plugin_data, schema=schema)
        return True, ""
    except jsonschema.ValidationError as e:
        error_msg = f"Validation error in {plugin_file}: {e.message} at path {'.'.join(str(p) for p in e.path)}"
        logger.error(error_msg)
        return False, error_msg
    except jsonschema.SchemaError as e:
        error_msg = f"Schema error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected validation error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def _load_legacy_plugins() -> Dict[str, Any]:
    """
    Load plugins from legacy config.json file.

    Returns:
        Dict of legacy plugins or empty dict if not found
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../conf/"))
    config_file_path = os.path.join(base_dir, "config.json")

    if not os.path.exists(config_file_path):
        return {}

    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        legacy_plugins = config_data.get("plugins", {})
        logger.info(f"Loaded {len(legacy_plugins)} legacy plugins from config.json")
        return legacy_plugins
    except Exception as e:
        logger.error(f"Failed to load legacy plugins from config.json: {str(e)}")
        return {}


def _load_plugins_from_directory() -> Dict[str, Any]:
    """
    Load plugins from the new multi-file structure.
    Reads index.json and loads individual plugin files from category directories.
    Also merges in legacy plugins from config.json if they exist.

    Returns:
        Dict containing merged plugin data with category metadata
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../marketplace/"))
    plugins_dir = os.path.join(base_dir, "ready_plugins")
    index_file = os.path.join(plugins_dir, "index.json")

    # Check if new structure exists
    if not os.path.exists(index_file):
        return None

    try:
        # Load index
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        # Merge all plugins
        all_plugins = {}
        categories_info = index_data.get("categories", {})

        # Load plugins from multi-file structure
        for category_key, category_info in categories_info.items():
            plugin_files = category_info.get("plugins", [])

            for plugin_file_path in plugin_files:
                plugin_full_path = os.path.join(plugins_dir, plugin_file_path)

                try:
                    with open(plugin_full_path, 'r', encoding='utf-8') as pf:
                        plugin_data = json.load(pf)

                    # Process plugin parameters (convert send_method strings to method integers)
                    _process_plugin_parameters(plugin_data)

                    # Validate plugin configuration
                    is_valid, validation_error = _validate_plugin_config(plugin_data, plugin_file_path)
                    if not is_valid:
                        logger.warning(f"Plugin validation failed for {plugin_file_path}: {validation_error}")
                        # Continue loading even if validation fails (non-blocking)
                        # You can change this to 'continue' if you want to skip invalid plugins

                    # Inject "ready": True for plugins missing the field (backward compat)
                    if "ready" not in plugin_data:
                        plugin_data["ready"] = True

                    # Add category metadata to plugin
                    plugin_data["category"] = category_key
                    plugin_data["category_name"] = category_info.get("name", category_key)
                    plugin_data["category_icon"] = category_info.get("icon", "📦")

                    # Use plugin_id as key, or filename if not present
                    plugin_id = plugin_data.get("plugin_id") or plugin_file_path.replace("/", "_").replace(".json", "")
                    all_plugins[plugin_id] = plugin_data

                    logger.info(f"Loaded plugin: {plugin_id} from {plugin_file_path}")
                except Exception as e:
                    logger.error(f"Failed to load plugin file {plugin_file_path}: {str(e)}")
                    continue

        # Merge legacy plugins from config.json
        legacy_plugins = _load_legacy_plugins()
        for plugin_key, plugin_config in legacy_plugins.items():
            # Only add if not already present in new structure
            if plugin_key not in all_plugins:
                # Convert legacy format to new format
                plugin_data = {
                    "ready": True,
                    "plugin_id": plugin_key,
                    "name": plugin_config.get("name", plugin_key),
                    "description": plugin_config.get("description", ""),
                    "api_prefix": plugin_config.get("api_prefix", ""),
                    "icon_uri": plugin_config.get("icon_uri", "🛠️"),
                    "plugin_type": plugin_config.get("plugin_type", 1),
                    "tools": plugin_config.get("tools", []),
                    "category": "testing",
                    "category_name": "Developer Testing & Legacy",
                    "category_icon": "🛠️",
                    "tags": ["legacy"]
                }
                # Process plugin parameters for legacy plugins as well
                _process_plugin_parameters(plugin_data)
                all_plugins[plugin_key] = plugin_data
                logger.info(f"Added legacy plugin: {plugin_key} from config.json")

        return {
            "version": index_data.get("version", "1.0.0"),
            "categories": categories_info,
            "plugins": all_plugins
        }
    except Exception as e:
        logger.error(f"Failed to load plugins from directory structure: {str(e)}")
        return None


@with_exception_handling
def plugin_read_market_json(
        req: PluginList,
        current_user: dict
) -> ResponseModel:
    """
    读取插件市场配置。
    优先从新的多文件结构 (marketplace/ready_plugins/) 加载，
    如果不存在则回退到旧的 config.json 单文件结构。

    Args:
        req: 用户空间
        current_user: 当前用户信息

    Returns:
        ResponseModel: 包含JSON文件内容的响应模型
    """
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    # 2. Try loading from new multi-file structure first
    plugins_data = _load_plugins_from_directory()

    if plugins_data:
        # New structure found, use it
        try:
            plugins_data["VITE_PLUGIN_SERVICE_URL"] = os.getenv("VITE_PLUGIN_SERVICE_URL", "")
            json_string = json.dumps(plugins_data, ensure_ascii=False, indent=2)

            logger.info(f"Loaded {len(plugins_data.get('plugins', {}))} plugins from multi-file structure")

            return ResponseModel(
                code=status.HTTP_200_OK,
                message="JSON file read successfully (multi-file)",
                data=json_string
            )
        except Exception as e:
            logger.error(f"Error processing multi-file plugin data: {str(e)}")
            # Fall through to legacy loading

    # 3. Fallback to legacy config.json (backward compatibility)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../conf/"))
    config_file_path = os.path.join(base_dir, "config.json")

    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
        json_content["VITE_PLUGIN_SERVICE_URL"] = os.getenv("VITE_PLUGIN_SERVICE_URL", "")
        json_string = json.dumps(json_content, ensure_ascii=False, indent=2)

        logger.info("Loaded plugins from legacy config.json")

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="JSON file read successfully (legacy)",
            data=json_string
        )
    except FileNotFoundError:
        logger.error(f"JSON file not found: {config_file_path}")
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message=f"No plugin configuration found (checked both multi-file and legacy)",
            data=""
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in file: {config_file_path}, error: {str(e)}")
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid JSON format in file: {config_file_path}",
            data=""
        )
    except Exception as e:
        logger.error(f"Error reading JSON file: {str(e)}")
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error reading JSON file: {str(e)}",
            data=""
        )


@with_exception_handling
def plugin_tool_update_available(
        tool_id: str,
        space_id: str,
        available: bool,
        plugin_version: str = None
) -> ResponseModel:
    """
    更新工具的可用状态（供运行面调用）

    当工具执行成功时，调用此方法将工具的 available 字段设置为 True
    当工具执行失败时，调用此方法将工具的 available 字段设置为 False

    Args:
        tool_id: 工具ID
        space_id: 空间ID
        available: 工具是否可用（True=可用，False=不可用）
        plugin_version: 插件版本（可选，默认使用 __version_none__）

    Returns:
        ResponseModel: 更新结果

    Example:
        # 工具执行成功后调用
        plugin_tool_update_available("tool_123", "space_456", True)

        # 工具执行失败后调用
        plugin_tool_update_available("tool_123", "space_456", False)
    """
    result = tool_repository.tool_update_available(
        tool_id=tool_id,
        space_id=space_id,
        available=available,
        plugin_version=plugin_version
    )

    if result.get("code") == status.HTTP_200_OK:
        logger.info(
            f"Tool available status updated: tool_id={tool_id}, "
            f"space_id={space_id}, available={available}"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Tool available status updated successfully",
            data=result
        )
    else:
        logger.error(
            f"Failed to update tool available status: tool_id={tool_id}, "
            f"space_id={space_id}, error={result.get('message')}"
        )
        return ResponseModel(
            code=result.get("code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            message=result.get("message", "Failed to update tool available status"),
            data=result
        )
