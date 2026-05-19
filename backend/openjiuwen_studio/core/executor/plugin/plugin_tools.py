#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
import re
import sys
from typing import List, Dict, Any

from openjiuwen.core.foundation.tool import Tool, ToolCard, Input, Output
from openjiuwen.core.foundation.tool import RestfulApiCard, RestfulApi

from openjiuwen_studio.core.common.dsl import PluginCodeConfig as DlPluginCodeConfig
from openjiuwen_studio.core.common.dsl import RestfulApiSchema as DlRestfulApiSchema, Param
from openjiuwen_studio.core.common.dsl import McpConfig as DlMcpConfig, McpTransport
from openjiuwen_studio.core.common.mcp_transport_utils import merge_mcp_server_url_query_params

from openjiuwen_studio.core.executor.component.component_impl.code_comp import CodeComponent
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode

TYPE = "type"
OBJECT = "object"
REQUIRED = "required"
PROPERTIES = "properties"


def convert_params_to_json_schema(params: List[Param]) -> Dict[str, Any]:
    """
    将 RestfulApiSchema 中的 params 转换为 JSON Schema 格式的 input_params RestfulApiCard中的

    """
    properties = {}
    required_params = []

    for param in params:
        # 构建每个参数的属性
        param_schema = {
            "type": param.type,
            "description": param.description,
            "location": param.method,
        }

        # 添加默认值（如果存在）
        if param.default_value:
            param_schema["default"] = param.default_value

        # 将参数添加到properties中
        properties[param.name] = param_schema

        # 如果参数是必需的，添加到required列表中
        if param.required:
            required_params.append(param.name)

    # 构建完整的JSON Schema
    input_params = {
        TYPE: OBJECT,
        PROPERTIES: properties,
        REQUIRED: required_params
    }

    return input_params


class ServiceTool:
    def __init__(self, restfulapischema: DlRestfulApiSchema) -> None:
        self.restfulapischema: DlRestfulApiSchema = restfulapischema

    def compile(self) -> RestfulApi:
        queries = {}
        headers = self.restfulapischema.headers
        url = self.restfulapischema.path  # Start with URL template (may contain {param} placeholders)

        # Process parameters: handle non-runtime defaults for query, header, and path parameters
        for i in self.restfulapischema.params:
            if not i.runtime:
                # Non-runtime query parameter: add to queries dict
                if i.method == "query" and i.default_value is not None:
                    queries[i.name] = i.default_value
                # Non-runtime header parameter: add to headers dict
                elif i.method == "header" and i.default_value is not None:
                    headers[i.name] = i.default_value
                # Non-runtime path parameter: substitute into URL template
                elif i.method == "path" and i.default_value is not None:
                    # Replace {param_name} with actual value in the URL
                    placeholder = f"{{{i.name}}}"
                    if placeholder in url:
                        url = url.replace(placeholder, str(i.default_value))

        # Note: Runtime path parameters (is_runtime=True) are handled by RestfulApi at execution time
        # The input_params schema includes location="" for path params, which tells RestfulApi
        # to substitute {param} placeholders with values from runtime inputs

        tool_name = self.restfulapischema.name or self.restfulapischema.tool_id
        input_params = convert_params_to_json_schema(self.restfulapischema.params)
        restfulapi_card = RestfulApiCard(name=tool_name,
                                         description=self.restfulapischema.description, input_params=input_params,
                                         url=url,  # URL with non-runtime path params already substituted
                                         method=self.restfulapischema.method,
                                         headers=headers, queries=queries)  # 不能配置id,否则会跑到Runner.get_tool
        restfulapi_tool = RestfulApi(restfulapi_card)
        return restfulapi_tool


class CodeTool:
    def __init__(self, codeschema: DlPluginCodeConfig) -> None:
        self.codeschema: DlPluginCodeConfig = codeschema

    def compile(self) -> Tool:
        # 使用工厂方法创建，内部会自动处理 Card 的构造
        code_tool = PluginCodeTool.create(self.codeschema)
        return code_tool


class PluginCodeCard(ToolCard):
    """插件代码工具卡片，用于适配 Tool 框架的元数据管理"""
    pass


class PluginCodeTool(CodeComponent, Tool):
    def __init__(self, card: PluginCodeCard, conf: DlPluginCodeConfig) -> None:
        CodeComponent.__init__(self, node_id=card.id, conf=conf)
        Tool.__init__(self, card=card)
        self.conf: DlPluginCodeConfig = conf
        self.tool_id: str = card.id
        self.node_id: str = card.id
        # Use the existing name field if available, otherwise fall back to tool_id
        self.name: str = conf.name or card.id
        self.params = conf.input_params
        self.description = self.conf.description

    @classmethod
    def create(cls, conf: DlPluginCodeConfig):
        """工厂方法：从 DSL 配置创建符合 Tool 规范的实例"""
        # 转换参数 schema
        input_schema = convert_params_to_json_schema(conf.input_params)
        # 构建 ToolCard
        card = PluginCodeCard(
            name=conf.name,
            description=conf.description,
            input_params=input_schema
        )  # 不能配置id,否则会跑到Runner.get_tool
        return cls(card=card, conf=conf)

    async def invoke(self, inputs: Input, **kwargs) -> Output:
        code = self.conf.code
        language = self.conf.language
        execute_type = self.conf.execute_type
        exception_config = self.conf.exception_config

        if not code.strip():
            raise JiuWenExecuteException(
                StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.code,
                message=StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.errmsg.format(msg="No code provided for execution"),
                node_id=self.tool_id
            )
        input_params = self.conf.input_params
        for param in input_params:
            if param.required and not inputs.get(param.name):
                raise JiuWenExecuteException(
                    StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.code,
                    message=StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.errmsg.format(
                        msg=f"{param.name} is required in input params"),
                    node_id=self.tool_id
                )

        # Convert input types based on schema
        converted_inputs = {}
        for param in input_params:
            value = inputs.get(param.name)
            if value is not None:
                param_type = param.type.lower() if param.type else "string"
                try:
                    if param_type == "integer":
                        converted_inputs[param.name] = int(value)
                    elif param_type == "number" or param_type == "float":
                        converted_inputs[param.name] = float(value)
                    elif param_type == "boolean" or param_type == "bool":
                        if isinstance(value, str):
                            converted_inputs[param.name] = value.lower() in ("true", "1", "yes")
                        else:
                            converted_inputs[param.name] = bool(value)
                    else:
                        converted_inputs[param.name] = value
                except (ValueError, TypeError):
                    converted_inputs[param.name] = value
            else:
                converted_inputs[param.name] = value

        error_body, response = await self._run(language, code, converted_inputs, exception_config, execute_type)
        result = self._process_output(error_body, response, exception_config)
        if not error_body.error_code:
            err_code = 0
            err_msg = "success"
            result_data = result
        else:
            err_code = error_body.error_code
            err_msg = error_body.message
            result_data = {key: value for key, value in result.items() if key != "error_body"}
        final_result: Dict[str, Any] = {'code': err_code, 'message': err_msg, 'data': result_data}
        return final_result


class McpTool:
    def __init__(self, mcpconfig: DlMcpConfig) -> None:
        self.mcpconfig: DlMcpConfig = mcpconfig

    def compile(self) -> Tool:
        return PluginMcpTool.create(self.mcpconfig)


class PluginMcpCard(ToolCard):
    """插件MCP工具卡片，用于适配 Tool 框架的元数据管理"""
    pass


class PluginMcpTool(Tool):
    def __init__(self, card: PluginMcpCard, conf: DlMcpConfig) -> None:
        Tool.__init__(self, card=card)
        self.conf: DlMcpConfig = conf
        self.name: str = conf.name or conf.tool_id
        self.description = conf.description

    @classmethod
    def create(cls, conf: DlMcpConfig):
        """工厂方法：从 DSL 配置创建符合 Tool 规范的实例"""
        input_schema = convert_params_to_json_schema(conf.input_params)
        sanitized_name = conf.name or conf.tool_id
        card = PluginMcpCard(
            name=sanitized_name,
            description=conf.description,
            input_params=input_schema
        )  # 不能配置id,否则会跑到Runner.get_tool
        return cls(card=card, conf=conf)

    def _build_auth_headers(self, inputs: Input) -> Dict[str, str]:
        """Collect tool-level headers and let runtime header inputs override them."""
        merged: Dict[str, str] = dict(self.conf.headers or {})

        properties: Dict[str, Any] = (self.card.input_params or {}).get("properties", {})
        for name, prop in properties.items():
            if not isinstance(prop, dict):
                continue
            if prop.get("location") != "header":
                continue
            value = str((inputs or {}).get(name) or prop.get("default") or "").strip()
            if value:
                merged[name] = value

        return merged

    async def stream(self, inputs: Input, **kwargs):
        """Satisfy the abstract stream() contract by delegating to invoke().

        PluginMcpTool is not a streaming source — it performs a single
        request/response cycle.  Yielding the complete result as one chunk
        lets the workflow's streaming pipeline proceed normally.
        """
        result = await self.invoke(inputs, **kwargs)
        yield result

    async def invoke(self, inputs: Input, **kwargs) -> Output:
        from openjiuwen.core.foundation.tool.mcp.base import MCPTool
        from openjiuwen.core.foundation.tool.mcp.client.stdio_client import StdioClient
        from openjiuwen.core.foundation.tool.mcp.client.sse_client import SseClient
        from openjiuwen.core.foundation.tool.mcp.client.streamable_http_client import StreamableHttpClient
        from openjiuwen.core.foundation.tool.mcp.client.playwright_client import PlaywrightClient
        from openjiuwen.core.foundation.tool.mcp.client.openapi_client import OpenApiClient

        conf = self.conf
        tool_name = conf.mcp_tool_name or conf.name
        arguments = dict(inputs) if inputs else {}
        server_name = conf.tool_id or tool_name
        auth_headers = self._build_auth_headers(inputs)

        try:
            # ── 1. Build McpServerConfig and the appropriate transport client ──
            from openjiuwen.core.foundation.tool.mcp.base import McpServerConfig

            _transport_to_client_type = {
                McpTransport.STDIO: "stdio",
                McpTransport.SSE: "sse",
                McpTransport.STREAMABLE_HTTP: "streamable-http",
                McpTransport.OPENAPI: "openapi",
                McpTransport.PLAYWRIGHT: "playwright",
            }
            client_type = _transport_to_client_type.get(conf.transport)
            if client_type is None:
                raise JiuWenExecuteException(
                    StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.code,
                    message=StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.errmsg.format(
                        msg=f"Unsupported MCP transport: '{conf.transport}'"),
                    node_id=conf.tool_id
                )

            mcp_params = dict(conf.params or {})
            if conf.transport == McpTransport.STDIO:
                mcp_params.setdefault("command", sys.executable)
                mcp_params.setdefault("args", [conf.url])
                mcp_params.setdefault("env", None)
                mcp_params.setdefault("cwd", os.getcwd())
                mcp_params.setdefault("encoding_error_handler", "strict")
                server_url = conf.url or ""
                url_auth_query: Dict[str, str] = {}
            elif not conf.url:
                raise JiuWenExecuteException(
                    StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.code,
                    message=StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.errmsg.format(
                        msg=f"MCP {conf.transport} transport requires 'url'"),
                    node_id=conf.tool_id
                )
            else:
                server_url, url_auth_query = merge_mcp_server_url_query_params(conf.url, None)

            server_config = McpServerConfig(
                server_name=server_name,
                server_path=(conf.url or "") if conf.transport == McpTransport.STDIO else server_url,
                client_type=client_type,
                params=mcp_params,
                auth_headers=auth_headers or {},
                auth_query_params=url_auth_query if conf.transport != McpTransport.STDIO else {},
            )

            if conf.transport == McpTransport.STDIO:
                client = StdioClient(server_config)
            elif conf.transport == McpTransport.SSE:
                client = SseClient(server_config)
            elif conf.transport == McpTransport.OPENAPI:
                client = OpenApiClient(server_config)
            elif conf.transport == McpTransport.PLAYWRIGHT:
                client = PlaywrightClient(server_config)
            else:  # STREAMABLE_HTTP
                client = StreamableHttpClient(server_config)

            # ── 2. Connect ────────────────────────────────────────────────────
            connected = await client.connect()
            if not connected:
                raise JiuWenExecuteException(
                    StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.code,
                    message=StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.errmsg.format(
                        msg=f"Failed to connect to MCP server for tool '{tool_name}'"),
                    node_id=conf.tool_id
                )

            try:
                # ── 3. Discover tools and locate the target card ──────────────
                tool_cards = await client.list_tools()
                target_card = next((c for c in tool_cards if c.name == tool_name), None)
                if target_card is None:
                    available = [c.name for c in tool_cards]
                    raise JiuWenExecuteException(
                        StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.code,
                        message=StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.errmsg.format(
                            msg=f"Tool '{tool_name}' not found on MCP server. Available: {available}"),
                        node_id=conf.tool_id
                    )

                # ── 4. Wrap in MCPTool and invoke ─────────────────────────────
                mcp_tool = MCPTool(mcp_client=client, tool_info=target_card)
                result = await mcp_tool.invoke(arguments)
            finally:
                # ── 5. Disconnect ─────────────────────────────────────────────
                await client.disconnect()

        except JiuWenExecuteException as e:
            return {'code': e.code, 'message': e.message, 'data': None}
        except Exception as e:
            return {
                'code': StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.code,
                'message': StatusCode.PLUGIN_CODE_TOOL_INVOKE_ERROR.errmsg.format(
                    msg=f"MCP tool invocation failed: {str(e)}"),
                'data': None
            }

        return {'code': 0, 'message': 'success', 'data': result}
