# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
MCP Server 加载器

从 IR 配置创建并注册 MCP Server 到 ResourceMgr
"""

from __future__ import annotations

import copy
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from jiuwen.extension.wrapper.mcp_tool_wrapper import McpToolWrapper

from openjiuwen.core.runner import Runner
from openjiuwen.core.foundation.tool.mcp.base import McpServerConfig
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import convert_camel_to_snake
from jiuwen.extension.wrapper.restful_api_loader import param_deserialization

HEADERS = "headers"
AUTH = "auth"


async def load_mcp_server_from_ir(
    ir_config: Dict[str, Any], tag: str | None = None
) -> List[str]:
    """
    从 IR 配置创建并注册 MCP Server

    Args:
        ir_config: IR 原始配置字典（驼峰命名），包含：
            - url: MCP Server URL
            - name: MCP Server 名称
            - type: 传输类型 (sse / streamable_http)
            - headers: 请求头
            - auth: 认证配置
            - pluginDependency: 插件依赖（包含钩子函数）
            - arguments: 工具参数列表
            - mcp_choose_tools: 工具过滤列表
        tag: 标签，用于标识 MCP Server

    Returns:
        注册后的 tool_id 列表
    """
    config = convert_ir_to_server_config(ir_config)

    try:
        await Runner.resource_mgr.add_mcp_server(config, tag=tag)
        server_id = config.server_id

        tool_ids = Runner.resource_mgr._resource_registry.tool().get_mcp_tool_id(
            server_id
        )

        logger.info(
            f"MCP Server registered: {server_id}, tools: {tool_ids}, tag: {tag}"
        )
        return tool_ids

    except Exception as e:
        logger.error(f"Failed to register MCP Server: {e}")
        raise


def convert_ir_to_server_config(ir_config: Dict[str, Any], **kwargs) -> McpServerConfig:
    """
    将 IR 配置转换为 McpServerConfig

    字段映射（与 McpIRConverter.ir_to_mcp 保持一致）：
    - url -> server_path
    - name -> server_name / server_id
    - type -> client_type (映射后)
    - headers -> auth_headers
    - pluginDependency -> params["plugin_dependency"]
    - arguments -> params["tool_params"]
    - mcp_choose_tools -> params["mcp_choose_tools"]

    client_type 映射：
    - sse / sse_new -> "sse_new" (使用 SSEClientNew)
    - streamable_http / streamable_http_new -> "streamable_http_new" (使用 StreamableHttpClientNew)

    Args:
        ir_config: IR 原始配置字典（驼峰命名）

    Returns:
        McpServerConfig 实例
    """
    ir_config = convert_camel_to_snake(ir_config, skip_fields=[HEADERS, AUTH])

    # headers 字段是嵌套的，里面有 crypt_method、headers、query、scope
    auth_headers = (
        ir_config.get(HEADERS, {}).get("headers", {})
        if isinstance(ir_config.get(HEADERS), dict)
        else {}
    )
    auth_headers = copy.deepcopy(auth_headers)
    auth_headers = extend_heads(auth_headers, ir_config, **kwargs)
    server_name = ir_config.get("name", "")

    # OpenAI-compatible APIs require function.name to match ^[a-zA-Z0-9_-]+$.
    # AbilityManager.list_tool_info generates tool names as f"mcp_{server_name}_{tool_name}",
    # so server_name must only contain ASCII alphanumeric, underscore, or hyphen.
    # Use the IR id (UUID) as server_name to guarantee compliance; keep the
    # original name as server_id for internal indexing and logging.
    server_id = server_name
    mcp_ir_id = ir_config.get("id", "")
    if mcp_ir_id:
        server_name = mcp_ir_id

    params = {
        "auth": ir_config.get(AUTH, {}),
        "plugin_dependency": ir_config.get("plugin_dependency", {}),
        "tool_params": param_deserialization(
            ir_config.get("arguments", []), allow_schema_is_empty=True
        ),
        "mcp_choose_tools": ir_config.get("mcp_choose_tools"),
        "input_parameters": ir_config.get("input_parameters", {}),
    }

    transport_type = ir_config.get("type", "sse")
    if transport_type in ("sse", "sse_new"):
        client_type = "sse_new"
    elif transport_type in ("streamable_http", "streamable_http_new"):
        client_type = "streamable_http_new"
    else:
        client_type = transport_type

    config = McpServerConfig(
        server_id=server_id,
        server_name=server_name,
        server_path=ir_config.get("url", ""),
        client_type=client_type,
        auth_headers=auth_headers,
        params=params,
    )

    return config


def extend_heads(mcp_headers, ir_data, **kwargs):
    """mcp header扩展"""
    return mcp_headers


def create_mcp_tool_wrapper(
    tool_id: str, agent_id: str, session_id: str
) -> "McpToolWrapper":
    """
    创建 MCP Tool 包装器

    Args:
        tool_id: 已注册的工具 ID
        agent_id: Agent ID
        session_id: Session ID

    Returns:
        McpToolWrapper 实例
    """
    from jiuwen.extension.wrapper.mcp_tool_wrapper import McpToolWrapper

    return McpToolWrapper(tool_id, agent_id, session_id)
