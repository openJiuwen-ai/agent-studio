#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from openjiuwen.core.common.logging import logger
from pydantic import ValidationError

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.routers.common import handle_response
import openjiuwen_studio.core.manager.plugin as mgr
# 插件相关模型
from openjiuwen_studio.schemas.plugin import (
    PluginCreate, PluginId, PluginInfoResponse, PluginApiBase,
    PluginApiInfoResponse, PluginListTool, PluginApiInfo, PluginApiInfoCreate, PluginListResponse,
    PluginList, PluginInfo, PluginToolId, ToolId, PluginCodeBase,
    PluginCodeInfo, PluginCodeInfoResponse, PluginPublishResponse, PluginPublish, PluginPublishListResponse,
    PluginPublishInfoResponse, PluginMcpBase, PluginMcpInfo, PluginMcpInfoResponse
)
from openjiuwen_studio.schemas.common import ResponseModel

plugin_router = APIRouter()


@plugin_router.post("/create", response_model=ResponseModel[PluginId])
async def plugin_create(
        request: PluginCreate,
        current_user: dict = Depends(get_current_user)
):
    """
    Create a plugin

    Args:
        request: Plugin creation request data
        current_user: Current user information

    Returns:
        ResponseModel[PluginId]: Creation result
    """
    try:
        logger.info(f"🔧 Plugin create start")
        logger.info(f"   Request data: {request.model_dump()}")
        logger.info(f"   User: {current_user.get('email', 'unknown')}")
        res = mgr.plugin_create(request, current_user)
        logger.info(f"✅ Plugin create successful")
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"❌ Plugin create validation failed")
        logger.error(f"   Errors: {e.errors()}")
        logger.error(f"   Request data: {request.model_dump() if hasattr(request, 'model_dump') else 'N/A'}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request validation failed: {e.errors()}"
        ) from e
    except Exception as e:
        logger.error(f"❌ Plugin create failed with unexpected error: {str(e)}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e


@plugin_router.post("/get", response_model=ResponseModel[PluginInfoResponse])
async def plugin_get(
        request: PluginId,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin information

    Args:
        request: Request data containing plugin ID
        current_user: Current user information

    Returns:
        ResponseModel[PluginInfoResponse]: Plugin information
    """
    try:
        logger.info(f"plugin get start")
        res = mgr.plugin_get(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/update", response_model=ResponseModel[Dict])
async def plugin_update(
        request: PluginInfo,
        current_user: dict = Depends(get_current_user)
):
    """
    Update plugin information

    Args:
        request: Plugin update information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Update result
    """
    try:
        logger.info(f"plugin update start")
        res = mgr.plugin_update(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/delete", response_model=ResponseModel[Dict])
async def plugin_delete(
        request: PluginId,
        current_user: dict = Depends(get_current_user)
):
    """
    Delete a plugin

    Args:
        request: Request data containing plugin ID
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Deletion result
    """
    try:
        logger.info(f"plugin delete start")
        res = mgr.plugin_delete(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/list", response_model=ResponseModel[PluginListResponse])
async def plugin_list(
        request: PluginList,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin list

    Args:
        request: Plugin list request parameters
        current_user: Current user information

    Returns:
        ResponseModel[PluginListResponse]: Plugin list result
    """
    try:
        logger.info(f"plugin list start")
        res = mgr.plugin_list(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/convert", response_model=ResponseModel[dsl.Plugin])
async def plugin_convert(
        request: ToolId,
        current_user: dict = Depends(get_current_user)
):
    """
    Convert plugin information

    Args:
        request: Tool ID information
        current_user: Current user information

    Returns:
        ResponseModel[dsl.Plugin]: Converted plugin data
    """
    try:
        logger.info(f"plugin convert start")
        res = mgr.plugin_convert(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/publish", response_model=ResponseModel[PluginPublishResponse])
async def plugin_publish(
        request: PluginPublish,
        current_user: dict = Depends(get_current_user)
):
    """
    Publish a plugin

    Args:
        request: Plugin publish request parameters
        current_user: Current user information

    Returns:
        ResponseModel[PluginPublishResponse]: Publish result
    """
    try:
        logger.info(f"plugin publish start")
        res = mgr.plugin_publish(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"plugin publish failed, error: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/publish_get", response_model=ResponseModel[PluginPublishInfoResponse])
async def plugin_publish_get(
        request: PluginId,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve published plugin information

    Args:
        request: Request data containing plugin ID
        current_user: Current user information

    Returns:
        ResponseModel[PluginInfoResponse]: Plugin information
    """
    try:
        logger.info(f"publish plugin get start")
        res = mgr.plugin_publish_get(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/publish_list", response_model=ResponseModel[PluginPublishListResponse])
async def plugin_publish_list(
        request: PluginId,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve published plugin list

    Args:
        request: Published plugin list request parameters
        current_user: Current user information

    Returns:
        ResponseModel[PluginPublishInfoResponse]: Published plugin information list
    """
    try:
        logger.info(f"publish plugin list start")
        res = mgr.plugin_publish_list(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"publish plugin list failed, error: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/publish_delete", response_model=ResponseModel[Dict])
async def plugin_publish_delete(
        request: PluginId,
        current_user: dict = Depends(get_current_user)
):
    """
    Delete a published plugin

    Args:
        request: Request data containing plugin ID
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Deletion result
    """
    try:
        logger.info(f"publish plugin delete start")
        res = mgr.plugin_publish_delete(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/create_api", response_model=ResponseModel[Dict])
async def plugin_create_api(
        request: PluginApiInfoCreate,
        current_user: dict = Depends(get_current_user)
):
    """
    Create plugin API

    Args:
        request: Plugin API creation information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Creation result
    """
    try:
        logger.info(f"🔧 Plugin create_api start")
        logger.info(f"   Request data: {request.model_dump()}")
        logger.info(f"   User: {current_user.get('email', 'unknown')}")
        res = mgr.plugin_create_api(request, current_user)
        logger.info(f"✅ Plugin create_api successful")
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"❌ Plugin create_api validation failed")
        logger.error(f"   Errors: {e.errors()}")
        logger.error(f"   Request: {request.model_dump() if hasattr(request, 'model_dump') else request}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request validation failed: {e.errors()}"
        ) from e
    except Exception as e:
        logger.error(f"❌ Plugin create_api error: {str(e)}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@plugin_router.post("/update_api", response_model=ResponseModel[Dict])
async def plugin_update_api(
        request: PluginApiInfo,
        current_user: dict = Depends(get_current_user)
):
    """
    Update plugin API

    Args:
        request: Plugin API update information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Update result
    """
    try:
        logger.info(f"🔧 Plugin update_api start")
        logger.info(f"   Request data: {request.model_dump()}")
        logger.info(f"   User: {current_user.get('email', 'unknown')}")
        res = mgr.plugin_update_api(request, current_user)
        logger.info(f"✅ Plugin update_api successful")
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"❌ Plugin update_api validation failed")
        logger.error(f"   Errors: {e.errors()}")
        logger.error(f"   Request: {request.model_dump() if hasattr(request, 'model_dump') else request}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request validation failed: {e.errors()}"
        ) from e
    except Exception as e:
        logger.error(f"❌ Plugin update_api error: {str(e)}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@plugin_router.post("/delete_api", response_model=ResponseModel[Dict])
async def plugin_delete_api(
        request: PluginToolId,
        current_user: dict = Depends(get_current_user)
):
    """
    Delete plugin API

    Args:
        request: Plugin API information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Deletion result
    """
    try:
        logger.info(f"plugin delete_api start")
        res = mgr.plugin_delete_tool(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/get_api", response_model=ResponseModel[PluginApiInfoResponse])
async def plugin_get_api(
        request: PluginToolId,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin API

    Args:
        request: Plugin API information
        current_user: Current user information

    Returns:
        ResponseModel[PluginApiInfoResponse]: Plugin API details
    """
    try:
        logger.info(f"plugin get_api start")
        res = mgr.plugin_get_api(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/list_api", response_model=ResponseModel[PluginApiInfoResponse])
async def plugin_list_api(
        request: PluginListTool,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin API list

    Args:
        request: Plugin list request parameters
        current_user: Current user information

    Returns:
        ResponseModel[PluginApiInfoResponse]: Plugin API list
    """
    try:
        logger.info(f"plugin list_api start")
        res = mgr.plugin_list_api(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/create_code", response_model=ResponseModel[Dict])
async def plugin_create_code(
        request: PluginCodeBase,
        current_user: dict = Depends(get_current_user)
):
    """
    Create plugin code tool

    Args:
        request: Plugin code tool creation information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Creation result
    """
    try:
        logger.info(f"plugin create_code start")
        res = mgr.plugin_create_code(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/update_code", response_model=ResponseModel[Dict])
async def plugin_update_code(
        request: PluginCodeInfo,
        current_user: dict = Depends(get_current_user)
):
    """
    Update plugin code tool

    Args:
        request: Plugin code tool update information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Update result
    """
    try:
        logger.info(f"plugin update_code start")
        res = mgr.plugin_update_code(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/delete_code", response_model=ResponseModel[Dict])
async def plugin_delete_code(
        request: PluginToolId,
        current_user: dict = Depends(get_current_user)
):
    """
    Delete plugin code tool

    Args:
        request: Plugin code tool information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Deletion result
    """
    try:
        logger.info(f"plugin delete_code start")
        res = mgr.plugin_delete_tool(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/get_code", response_model=ResponseModel[PluginCodeInfoResponse])
async def plugin_get_code(
        request: PluginToolId,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin code tool

    Args:
        request: Plugin code tool information
        current_user: Current user information

    Returns:
        ResponseModel[PluginCodeInfoResponse]: Plugin code tool details
    """
    try:
        logger.info(f"plugin get_code start")
        res = mgr.plugin_get_code(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/list_code", response_model=ResponseModel[PluginCodeInfoResponse])
async def plugin_list_code(
        request: PluginListTool,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin code tool list

    Args:
        request: Plugin list request parameters
        current_user: Current user information

    Returns:
        ResponseModel[PluginCodeInfoResponse]: Plugin code tool list
    """
    try:
        logger.info(f"plugin list_code start")
        res = mgr.plugin_list_code(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/get_market", response_model=ResponseModel[str])
async def plugin_read_json_file(
    request: PluginList,
    current_user: dict = Depends(get_current_user)
):
    """
    Read JSON file content and return as JSON string (non-frontend interface)

    Args:
        request: Request data containing space ID
        current_user: Current user information

    Returns:
        ResponseModel[str]: JSON file content as string
    """
    try:
        logger.info(f"plugin read json file start")
        res = mgr.plugin_read_market_json(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/create_mcp_tool", response_model=ResponseModel[Dict])
async def plugin_create_mcp_tool(
        request: PluginMcpBase,
        current_user: dict = Depends(get_current_user)
):
    """
    Create plugin MCP tool

    Args:
        request: Plugin MCP tool creation information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Creation result containing tool_id
    """
    try:
        logger.info(f"plugin create_mcp_tool start")
        res = mgr.plugin_create_mcp_tool(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e
    except Exception as e:
        logger.error(f"plugin create_mcp_tool error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@plugin_router.post("/update_mcp_tool", response_model=ResponseModel[Dict])
async def plugin_update_mcp_tool(
        request: PluginMcpInfo,
        current_user: dict = Depends(get_current_user)
):
    """
    Update plugin MCP tool

    Args:
        request: Plugin MCP tool update information
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Update result
    """
    try:
        logger.info(f"plugin update_mcp_tool start")
        res = mgr.plugin_update_mcp_tool(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e
    except Exception as e:
        logger.error(f"plugin update_mcp_tool error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@plugin_router.post("/delete_mcp_tool", response_model=ResponseModel[Dict])
async def plugin_delete_mcp_tool(
        request: PluginToolId,
        current_user: dict = Depends(get_current_user)
):
    """
    Delete plugin MCP tool

    Args:
        request: Plugin MCP tool identifier
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Deletion result
    """
    try:
        logger.info(f"plugin delete_mcp_tool start")
        res = mgr.plugin_delete_tool(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/get_mcp_tool", response_model=ResponseModel[PluginMcpInfoResponse])
async def plugin_get_mcp_tool(
        request: PluginToolId,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin MCP tool information

    Args:
        request: Plugin MCP tool identifier
        current_user: Current user information

    Returns:
        ResponseModel[PluginMcpInfoResponse]: Plugin MCP tool details
    """
    try:
        logger.info(f"plugin get_mcp_tool start")
        res = mgr.plugin_get_mcp_tool(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/list_mcp_tools", response_model=ResponseModel[PluginMcpInfoResponse])
async def plugin_list_mcp_tools(
        request: PluginListTool,
        current_user: dict = Depends(get_current_user)
):
    """
    Retrieve plugin MCP tool list

    Args:
        request: Plugin list request parameters
        current_user: Current user information

    Returns:
        ResponseModel[PluginMcpInfoResponse]: Plugin MCP tool list
    """
    try:
        logger.info(f"plugin list_mcp_tools start")
        res = mgr.plugin_list_mcp_tools(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e


@plugin_router.post("/discover_mcp_tools", response_model=ResponseModel[Dict])
async def plugin_discover_mcp_tools(
        request: PluginId,
        current_user: dict = Depends(get_current_user)
):
    """
    Connect to the MCP server for a previously created plugin, discover its tools,
    and persist them to the database.

    This endpoint is intentionally separate from /create so that plugin creation is
    instantaneous and the (potentially slow) MCP connection happens only when the
    caller is ready.

    Args:
        request: Plugin identifier (space_id + plugin_id)
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Discovery result containing tool_ids
    """
    try:
        logger.info(f"plugin discover_mcp_tools start for plugin_id={request.plugin_id}")
        res = mgr.plugin_discover_mcp_tools(request, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed") from e
    except Exception as e:
        logger.error(f"plugin discover_mcp_tools error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
