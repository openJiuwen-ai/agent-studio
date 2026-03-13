#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Plugin and tool template creation utilities.
"""

from typing import Dict, Any


def create_plugin_template(
    plugin_id: str,
    name: str,
    description: str,
    category: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create a basic plugin template.

    Args:
        plugin_id: Unique identifier for the plugin (lowercase, underscores)
        name: Display name of the plugin
        description: Description of what the plugin does
        category: Plugin category (social, productivity, ai, data, testing, other)
        metadata: Optional metadata dict with keys: icon, api_prefix, author, version

    Returns:
        Plugin configuration dictionary
    """
    if metadata is None:
        metadata = {}

    # "ready" is the first key; new plugins default to False until explicitly marked ready
    plugin_data = {
        "ready": metadata.get("ready", False),
        "plugin_id": plugin_id,
        "name": name,
        "description": description,
        "category": category,
        "category_name": category.replace('_', ' ').title(),
        "icon_uri": metadata.get("icon", "📦"),
        "plugin_type": 1,  # CLOUD_API
        "version": metadata.get("version", "1.0.0"),
        "author": metadata.get("author", "OpenJiuwen"),
        "tags": [category]
    }

    # Add api_prefix if provided
    api_prefix = metadata.get("api_prefix")
    if api_prefix:
        plugin_data["api_prefix"] = api_prefix

    # Add header_configuration if provided
    header_config = metadata.get("header_configuration")
    if header_config:
        plugin_data["header_configuration"] = header_config

    # Add tools (always last)
    plugin_data["tools"] = []

    return plugin_data


def create_tool_template(
    name: str,
    path: str,
    method: str,
    description: str
) -> Dict[str, Any]:
    """
    Create a basic tool template.

    Args:
        name: Tool display name
        path: API endpoint path (e.g., /api/users)
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        description: Description of what the tool does

    Returns:
        Tool configuration dictionary
    """
    return {
        "name": name,
        "path": path,
        "method": method.upper(),
        "description": description,
        "request_params": {}
    }


def add_tool_to_plugin(plugin: Dict[str, Any], tool: Dict[str, Any]):
    """
    Add a tool to a plugin configuration.

    Args:
        plugin: Plugin configuration dictionary
        tool: Tool configuration dictionary
    """
    if "tools" not in plugin:
        plugin["tools"] = []
    plugin["tools"].append(tool)


def add_header_configuration(
    plugin: Dict[str, Any],
    header_name: str,
    env_var: str,
    description: str = ""
):
    """
    Add a header configuration to a plugin.

    Args:
        plugin: Plugin configuration dictionary
        header_name: Name of the header (e.g., "API Key", "Authorization")
        env_var: Environment variable name (e.g., "BAIDU_MAPS_API_KEY")
        description: Description of the header configuration
    """
    if "header_configuration" not in plugin:
        plugin["header_configuration"] = {}

    plugin["header_configuration"][header_name] = {
        "value": env_var,
        "description": description
    }


def add_parameter_to_tool(
    tool: Dict[str, Any],
    name: str,
    param_type: str,
    config: Dict[str, Any] = None
):
    """
    Add a parameter to a tool.

    Args:
        tool: Tool configuration dictionary
        name: Parameter name
        param_type: Parameter type (string, integer, number, boolean, object, array)
        config: Optional config dict with keys: description, required, default, send_method, is_runtime
    """
    if config is None:
        config = {}

    if "request_params" not in tool:
        tool["request_params"] = {}

    param_config = {
        "type": param_type,
        "description": config.get("description", ""),
        "required": config.get("required", False)
    }

    if "default" in config:
        param_config["default"] = config["default"]

    # Handle send_method
    if "send_method" in config:
        param_config["send_method"] = config["send_method"]

    if "is_runtime" in config:
        param_config["is_runtime"] = config["is_runtime"]

    tool["request_params"][name] = param_config
