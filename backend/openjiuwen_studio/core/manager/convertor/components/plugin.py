#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import importlib.util
import json
import os
import urllib.parse
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

from fastapi import status
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.manager.repositories.plugin_repository import plugin_repository
from openjiuwen_studio.core.manager.repositories.tool_repository import tool_repository
from openjiuwen_studio.core.utils.iam_auth import auth as builtin_execute_auth
from openjiuwen_studio.models.plugin import PluginBaseDBPd
from openjiuwen_studio.schemas import ResponseModel
from openjiuwen_studio.schemas.node import Node
from openjiuwen_studio.core.manager.convertor.components.common import input_params_convert, exception_config_convert
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.schemas.plugin import PluginApiInfo, PluginApiHeader, PluginToolParam, ParamType, \
    PluginApiMethod, PluginId, PluginToolId, PluginType, PluginCodeInfo, PluginMcpInfo, \
    PluginMcpTransport, ParamSendMethod, Priority
from openjiuwen_studio.schemas.plugin import PluginPublishInfo

plugin_type_mapping = {
    PluginType.PLUGIN_TYPE_CLOUD_API: dsl.PluginType.SERVICE,
    PluginType.PLUGIN_TYPE_CLOUD_CODE: dsl.PluginType.CODE,
    PluginType.PLUGIN_TYPE_CLOUD_MCP: dsl.PluginType.MCP,
}

api_method_mapping = {
    PluginApiMethod.PLUGIN_API_METHOD_GET: "GET",
    PluginApiMethod.PLUGIN_API_METHOD_POST: "POST",
    PluginApiMethod.PLUGIN_API_METHOD_PUT: "PUT",
    PluginApiMethod.PLUGIN_API_METHOD_DELETE: "DELETE",
    PluginApiMethod.PLUGIN_API_METHOD_PATCH: "PATCH",
}

mcp_transport_mapping = {
    PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STDIO: "stdio",
    PluginMcpTransport.PLUGIN_MCP_TRANSPORT_SSE: "sse",
    PluginMcpTransport.PLUGIN_MCP_TRANSPORT_STREAMABLE_HTTP: "streamable_http",
    PluginMcpTransport.PLUGIN_MCP_TRANSPORT_OPENAPI: "openapi",
    PluginMcpTransport.PLUGIN_MCP_TRANSPORT_PLAYWRIGHT: "playwright",
}

param_type_mapping = {
    ParamType.PARAM_TYPE_STRING: "string",
    ParamType.PARAM_TYPE_INT: "integer",
    ParamType.PARAM_TYPE_FLOAT: "number",
    ParamType.PARAM_TYPE_BOOL: "boolean",
    ParamType.PARAM_TYPE_OBJECT: "object",
    ParamType.PARAM_TYPE_ARRAY_STRING: "array",
    ParamType.PARAM_TYPE_ARRAY_INT: "array",
    ParamType.PARAM_TYPE_ARRAY_FLOAT: "array",
    ParamType.PARAM_TYPE_ARRAY_BOOL: "array",
}

param_send_method_type_mapping = {
    ParamSendMethod.PARAM_SEND_METHOD_NONE: "",
    ParamSendMethod.PARAM_SEND_METHOD_HEADER: "header",
    ParamSendMethod.PARAM_SEND_METHOD_QUERY: "query",
    ParamSendMethod.PARAM_SEND_METHOD_BODY: "body",
    ParamSendMethod.PARAM_SEND_METHOD_PATH: "path",
}

# Reverse mapping: Convert marketplace JSON string values to ParamSendMethod enum integers
send_method_string_to_enum = {
    "None": ParamSendMethod.PARAM_SEND_METHOD_NONE,
    "Header": ParamSendMethod.PARAM_SEND_METHOD_HEADER,
    "Query": ParamSendMethod.PARAM_SEND_METHOD_QUERY,
    "Body": ParamSendMethod.PARAM_SEND_METHOD_BODY,
    "Path": ParamSendMethod.PARAM_SEND_METHOD_PATH,
    # Legacy lowercase support
    "none": ParamSendMethod.PARAM_SEND_METHOD_NONE,
    "header": ParamSendMethod.PARAM_SEND_METHOD_HEADER,
    "query": ParamSendMethod.PARAM_SEND_METHOD_QUERY,
    "body": ParamSendMethod.PARAM_SEND_METHOD_BODY,
    "path": ParamSendMethod.PARAM_SEND_METHOD_PATH,
}


def _load_callable_from_file(spec: str) -> Optional[Callable[[dict], dict]]:
    """Load callable from '<file_path>:<function_name>' spec."""
    if ":" not in spec:
        logger.warning("Invalid auth_function format, expect '<path>:<func>', got: %s", spec)
        return None

    file_path, func_name = spec.rsplit(":", 1)
    file_path = os.path.abspath(file_path.strip())
    func_name = func_name.strip()
    if not file_path or not func_name:
        logger.warning("Invalid auth_function content, got: %s", spec)
        return None
    if not os.path.isfile(file_path):
        logger.warning("auth_function file not found: %s", file_path)
        return None

    module_name = f"custom_auth_{abs(hash(spec))}"
    module_spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not module_spec or not module_spec.loader:
        logger.warning("Failed to load module spec from auth_function: %s", spec)
        return None

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    func = getattr(module, func_name, None)
    if not callable(func):
        logger.warning("auth_function target is not callable: %s", spec)
        return None
    return func


def _get_custom_auth_spec() -> str:
    direct_spec = (os.getenv("auth_function") or os.getenv("AUTH_FUNCTION") or "").strip()
    if direct_spec:
        return direct_spec

    runtime_userdata = (os.getenv("RUNTIME_USERDATA") or "").strip()
    if not runtime_userdata:
        return ""
    try:
        payload = json.loads(runtime_userdata)
    except Exception:
        return ""
    spec = payload.get("auth_function")
    return str(spec).strip() if spec else ""


@lru_cache(maxsize=1)
def _resolve_auth_executor() -> Callable[[dict], dict]:
    """Resolve auth executor from env; fallback to builtin implementation."""
    custom_spec = _get_custom_auth_spec()
    if not custom_spec:
        return builtin_execute_auth

    try:
        custom_callable = _load_callable_from_file(custom_spec)
        if custom_callable:
            logger.info("Using custom auth function: %s", custom_spec)
            return custom_callable
    except Exception as e:
        logger.warning("Failed to initialize custom auth function '%s': %s", custom_spec, str(e))

    return builtin_execute_auth


def _execute_auth(auth_payload: dict) -> dict:
    """Execute auth with custom executor when configured."""
    executor = _resolve_auth_executor()
    try:
        result = executor(auth_payload)
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.warning("Custom auth execution failed, fallback to builtin auth: %s", str(e))
        fallback = builtin_execute_auth(auth_payload)
        return fallback if isinstance(fallback, dict) else {}


def _plugin_tool_param_convert(params: List[PluginToolParam]) -> List[dsl.Param]:
    converted_params: List[dsl.Param] = []
    for param in params:
        converted_param = dsl.Param(
            name=param.name,
            description=param.desc,
            type=param_type_mapping.get(param.type),
            required=param.is_required,
            method=param_send_method_type_mapping.get(param.method),
            default_value=param.value,
            runtime=param.is_runtime,
        )
        converted_params.append(converted_param)

    return converted_params


def _plugin_api_header_convert(headers: List[PluginApiHeader]) -> Dict[str, Any]:
    converted_header: Dict[str, Any] = {}
    for header in headers:
        converted_header[header.name] = header.value
    return converted_header


def _merge_plugin_params(request_params: List[PluginToolParam], plugin_params: List[PluginToolParam]) -> List[
    PluginToolParam]:
    """
    合并两个参数列表，当存在相同name的参数时，根据priority决定使用哪个：
    """
    merged_params: Dict[str, PluginToolParam] = {}

    for param in request_params:
        merged_params[param.name] = param

    # 然后处理 plugin_params，根据priority决定是否覆盖
    if not plugin_params:
        return list(merged_params.values())

    for param in plugin_params:
        if param.name in merged_params:
            existing = merged_params[param.name]
            existing_priority = getattr(existing, 'priority', Priority.PRIORITY_TOOL)
            incoming_priority = getattr(param, 'priority', Priority.PRIORITY_PLUGIN)
            if incoming_priority < existing_priority:
                merged_params[param.name] = param
        else:
            merged_params[param.name] = param

    return list(merged_params.values())


def _build_auth_params(plugin_info: Any) -> List[PluginToolParam]:
    """Resolve auth first, then convert auth headers/query to non-runtime params."""
    auth_payload = getattr(plugin_info, "auth", None)
    if not isinstance(auth_payload, dict):
        return []

    auth_params: List[PluginToolParam] = []
    normalized_auth_payload = {"type": str(auth_payload.get("type") or "NONE").upper(), **auth_payload}
    resolved_auth = _execute_auth(normalized_auth_payload)
    method_mapping = {
        "headers": ParamSendMethod.PARAM_SEND_METHOD_HEADER,
        "query": ParamSendMethod.PARAM_SEND_METHOD_QUERY,
    }

    for source in ("headers", "query"):
        source_values = resolved_auth.get(source) if isinstance(resolved_auth, dict) else {}
        if not isinstance(source_values, dict):
            continue
        send_method = method_mapping.get(source)
        if send_method is None:
            continue
        for key, value in source_values.items():
            if not key:
                continue
            auth_params.append(PluginToolParam(
                name=str(key),
                desc=f"Auth parameter from {source}",
                type=ParamType.PARAM_TYPE_STRING,
                is_required=True,
                method=send_method,
                is_runtime=False,
                value=value,
                priority=Priority.PRIORITY_PLUGIN,
            ))

    return auth_params


def _resolve_auth_data(plugin_info: Any) -> Dict[str, Any]:
    auth_payload = getattr(plugin_info, "auth", None)
    if not isinstance(auth_payload, dict):
        return {}
    normalized_auth_payload = {"type": str(auth_payload.get("type") or "NONE").upper(), **auth_payload}
    resolved_auth = _execute_auth(normalized_auth_payload)
    return resolved_auth if isinstance(resolved_auth, dict) else {}


def _append_query_params(url: Optional[str], query: Dict[str, Any]) -> Optional[str]:
    if not isinstance(url, str) or not url:
        return url
    if not isinstance(query, dict) or not query:
        return url

    parsed = urllib.parse.urlparse(url)
    existing_query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in query.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        existing_query[key_str] = "" if value is None else str(value)

    encoded_query = urllib.parse.urlencode(existing_query)
    return urllib.parse.urlunparse(parsed._replace(query=encoded_query))


def _strip_auth_query_params(url: Optional[str], auth_payload: Any) -> Optional[str]:
    """Remove auth query keys from URL for DSL export."""
    if not isinstance(url, str) or not url:
        return url
    if not isinstance(auth_payload, dict):
        return url

    query_config = auth_payload.get("query")
    if not isinstance(query_config, dict) or not query_config:
        return url

    blocked_keys = {str(key).strip() for key in query_config.keys() if str(key).strip()}
    if not blocked_keys:
        return url

    parsed = urllib.parse.urlparse(url)
    existing_query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    filtered_query = {k: v for k, v in existing_query.items() if k not in blocked_keys}
    encoded_query = urllib.parse.urlencode(filtered_query)
    return urllib.parse.urlunparse(parsed._replace(query=encoded_query))


def plugin_api_tool_convert(
        plugin_info,
        api_info: Dict[str, Any],
        export_raw_auth: bool = False
) -> Dict[str, Any]:
    plugin_params: List[PluginToolParam] = []
    if hasattr(plugin_info, "inputs") and plugin_info.inputs:
        for i in plugin_info.inputs:
            plugin_params.append(PluginToolParam(**i))
    elif hasattr(plugin_info, "request_params") and plugin_info.request_params:
        for i in plugin_info.request_params:
            plugin_params.append(i)
    if not export_raw_auth:
        plugin_params.extend(_build_auth_params(plugin_info))
    api = PluginApiInfo(**api_info)
    merged_params = _merge_plugin_params(api.request_params, plugin_params)
    convert_api = dsl.RestfulApiSchema(
        tool_id=api.tool_id,
        name=api.name,
        description=api.desc,
        path=plugin_info.url + api.path,
        method=api_method_mapping.get(api.method),
        params=_plugin_tool_param_convert(merged_params),
        response=_plugin_tool_param_convert(api.response_params),
        headers=_plugin_api_header_convert(api.headers),
    )
    convert_api_dict = convert_api.model_dump()
    if export_raw_auth and getattr(plugin_info, "auth", None):
        convert_api_dict["auth"] = getattr(plugin_info, "auth")
    return convert_api_dict


def _plugin_code_output_param_convert(params: List[PluginToolParam]) -> List[dsl.ParamConfig]:
    converted_params: List[dsl.ParamConfig] = []
    for param in params:
        converted_param = dsl.ParamConfig(
            name=param.name,
            type=param_type_mapping.get(param.type),
        )
        converted_params.append(converted_param)

    return converted_params


def plugin_code_tool_convert(code_info: Dict[str, Any]) -> Dict[str, Any]:
    code = PluginCodeInfo(**code_info)
    convert_code = dsl.PluginCodeConfig(
        tool_id=code.tool_id,
        name=code.name,
        description=code.desc,
        language=code.language,
        code=code.code,
        input_params=_plugin_tool_param_convert(code.request_params),
        output_params=_plugin_code_output_param_convert(code.response_params),
    )
    return convert_code.model_dump()


def plugin_mcp_tool_convert(
        plugin_info,
        mcp_info: Dict[str, Any],
        export_raw_auth: bool = False
) -> Dict[str, Any]:
    plugin_params: List[PluginToolParam] = []
    if hasattr(plugin_info, "inputs") and plugin_info.inputs:
        for i in plugin_info.inputs:
            plugin_params.append(PluginToolParam(**i))
    elif hasattr(plugin_info, "request_params") and plugin_info.request_params:
        for i in plugin_info.request_params:
            plugin_params.append(i)
    mcp = PluginMcpInfo(**mcp_info)
    merged_params = _merge_plugin_params(mcp.request_params, plugin_params)
    resolved_auth = _resolve_auth_data(plugin_info) if not export_raw_auth else {}

    # For SSE/streamable_http, fall back to plugin-level URL if tool URL is empty
    url = mcp.url or (plugin_info.url if hasattr(plugin_info, "url") else None)
    if export_raw_auth:
        url = _strip_auth_query_params(url, getattr(plugin_info, "auth", None))
    resolved_query_any = resolved_auth.get("query")
    resolved_query: Dict[str, Any] = resolved_query_any if isinstance(resolved_query_any, dict) else {}
    url = _append_query_params(url, resolved_query)

    resolved_headers_any = resolved_auth.get("headers")
    resolved_headers: Dict[str, Any] = resolved_headers_any if isinstance(resolved_headers_any, dict) else {}
    merged_headers: Dict[str, str] = dict(mcp.headers or {})
    for key, value in resolved_headers.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        merged_headers[key_str] = "" if value is None else str(value)

    # Consolidate transport-specific parameters into a single params dict
    mcp_config_params = {}
    if mcp.command:
        mcp_config_params["command"] = mcp.command
    if mcp.args:
        mcp_config_params["args"] = mcp.args
    if mcp.env:
        mcp_config_params["env"] = mcp.env
    convert_mcp = dsl.McpConfig(
        tool_id=mcp.tool_id,
        name=mcp.name,
        description=mcp.desc,
        transport=mcp_transport_mapping.get(mcp.transport, "stdio"),
        url=url,
        headers=merged_headers or None,
        params=mcp_config_params,
        mcp_tool_name=mcp.mcp_tool_name,
        input_params=_plugin_tool_param_convert(merged_params),
    )
    convert_mcp_dict = convert_mcp.model_dump()
    if export_raw_auth and getattr(plugin_info, "auth", None):
        convert_mcp_dict["auth"] = getattr(plugin_info, "auth")
    return convert_mcp_dict


def plugin_tool_convert(
        plugin_info,
        tool: Dict[str, Any],
        export_raw_auth: bool = False
) -> Dict[str, Any]:
    if plugin_info.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_API:
        return plugin_api_tool_convert(plugin_info, tool, export_raw_auth=export_raw_auth)
    elif plugin_info.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_MCP:
        return plugin_mcp_tool_convert(plugin_info, tool, export_raw_auth=export_raw_auth)
    else:
        return plugin_code_tool_convert(tool)


def _plugin_config_convert(node: Node, space_id: str, export_raw_auth: bool = False) -> Dict:
    data = node.data
    exception_conf = dsl.ExceptConfig()
    if data.exception_config is not None:
        exception_conf = exception_config_convert(data.exception_config)

    plugin_param = data.inputs.plugin_param
    if plugin_param.plugin_version == "draft" or plugin_param.plugin_version == "":

        tool_id = PluginToolId(
            plugin_id=plugin_param.plugin_id,
            space_id=space_id,
            tool_id=plugin_param.tool_id,
            plugin_version=plugin_param.plugin_version,
        )
        res, plugin_dict = tool_repository.tool_get(tool_id.model_dump())
        get_result = ResponseModel(**res)
        if get_result.code != status.HTTP_200_OK:
            raise ValueError(f"get plugin failed, code: {get_result.code}, error: {get_result.message}")
        tool_info = get_result.data
        plugin_info = PluginBaseDBPd(**plugin_dict)

        configs = dsl.ToolCompConfig(
            type=plugin_type_mapping[plugin_info.plugin_type],
            tool=plugin_tool_convert(plugin_info, tool_info.model_dump(), export_raw_auth=export_raw_auth),
            exception_config=exception_conf,
        )
    else:
        req = PluginId(plugin_id=plugin_param.plugin_id, space_id=space_id, plugin_version=plugin_param.plugin_version)
        res = plugin_repository.plugin_publish_get(req.model_dump())
        get_result = ResponseModel(**res)
        if get_result.code != status.HTTP_200_OK:
            raise ValueError(f"get plugin publish failed, code: {get_result.code}, error: {get_result.message}")
        if get_result.data is None:
            raise ValueError(f"fetch plugin failed with version: {plugin_param.plugin_version}")
        if get_result.data.get("inputs") and get_result.data.get("inputs"):
            get_result.data["request_params"] = get_result.data.get("inputs")
        plugin_publish_info = PluginPublishInfo(**get_result.data)
        tools = plugin_publish_info.tools
        tool_info = None
        for tool in tools:
            if tool.get("tool_id") == plugin_param.tool_id:
                tool_info = tool
                break

        if not tool_info:
            raise ValueError(
                f"tool_id {plugin_param.tool_id} not found in plugin publish version {plugin_param.plugin_version}")

        configs = dsl.ToolCompConfig(
            type=plugin_type_mapping[plugin_publish_info.plugin_type],
            tool=plugin_tool_convert(plugin_publish_info, tool_info, export_raw_auth=export_raw_auth),
            exception_config=exception_conf,
        )
    return configs.model_dump()


def plugin_convert(node: Node, space_id: str, export_raw_auth: bool = False) -> dsl.Component:
    try:
        data = node.data
        inputs = data.inputs
        if inputs is None:
            raise TypeError("inputs is none")
        input_parameters = inputs.input_parameters
        convert_inputs: Dict[str, Any] = {}
        if input_parameters is not None:
            convert_inputs = input_params_convert(input_parameters)

        return dsl.Component(
            id=node.id,
            type=ComponentType.COMPONENT_TYPE_PLUGIN,
            type_version="1.0.0",
            description="",
            inputs=convert_inputs,
            configs=_plugin_config_convert(node, space_id, export_raw_auth=export_raw_auth),
            name=data.title
        )
    except Exception as e:
        raise RuntimeError(f"Failed to convert plugin tool node: {str(e)}") from e
