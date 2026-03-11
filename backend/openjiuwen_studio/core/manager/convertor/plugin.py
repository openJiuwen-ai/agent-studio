#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
from typing import Dict, List, Any

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.manager.convertor.components.plugin import plugin_api_tool_convert, \
    plugin_code_tool_convert, plugin_mcp_tool_convert, plugin_type_mapping
from openjiuwen_studio.models.plugin import PluginBaseDBPd
from openjiuwen_studio.schemas.plugin import PluginType


def _plugin_api_tools_convert(plugin_info, api_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    api_tools: List[Dict[str, Any]] = []
    convert_api = plugin_api_tool_convert(plugin_info, api_info)
    api_tools.append(convert_api)

    return api_tools


def _plugin_code_tools_convert(code_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    code_tools: List[Dict[str, Any]] = []
    convert_api = plugin_code_tool_convert(code_info)
    code_tools.append(convert_api)

    return code_tools


def _plugin_mcp_tools_convert(plugin_info, mcp_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    mcp_tools: List[Dict[str, Any]] = []
    convert_mcp = plugin_mcp_tool_convert(plugin_info, mcp_info)
    mcp_tools.append(convert_mcp)

    return mcp_tools


def plugin_tool_convert(plugin_info, tool: Dict[str, Any]) -> List[Dict[str, Any]]:
    if plugin_info.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_API:
        return _plugin_api_tools_convert(plugin_info, tool)
    elif plugin_info.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_MCP:
        return _plugin_mcp_tools_convert(plugin_info, tool)
    else:
        return _plugin_code_tools_convert(tool)


def plugin_convert(plugin_info: PluginBaseDBPd, tool: Dict[str, Any]) -> dsl.Plugin:
    try:
        convert_tools = plugin_tool_convert(plugin_info, tool)

        return dsl.Plugin(
            plugin_id=plugin_info.plugin_id,
            plugin_name=plugin_info.name,
            plugin_description=plugin_info.desc,
            plugin_type=plugin_type_mapping[plugin_info.plugin_type],
            tools=convert_tools,
            plugin_version=plugin_info.plugin_version,
        )
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        raise ValueError(f"Invalid plugin schema or input: {e}") from e
