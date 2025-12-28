#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, Dict, List

from fastapi import status

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.manager.repositories.plugin_repository import plugin_repository
from openjiuwen_studio.core.manager.repositories.tool_repository import tool_repository
from openjiuwen_studio.models.plugin import PluginBaseDBPd
from openjiuwen_studio.schemas import ResponseModel
from openjiuwen_studio.schemas.node import Node
from openjiuwen_studio.core.manager.convertor.components.common import input_params_convert, exception_config_convert
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.schemas.plugin import PluginApiInfo, PluginApiHeader, PluginToolParam, ParamType, \
    PluginApiMethod, PluginId, PluginToolId, PluginType, PluginCodeInfo, ParamSendMethod
from openjiuwen_studio.schemas.plugin import PluginPublishInfo

plugin_type_mapping = {
    PluginType.PLUGIN_TYPE_CLOUD_API: dsl.PluginType.SERVICE,
    PluginType.PLUGIN_TYPE_CLOUD_CODE: dsl.PluginType.CODE,
}

plugin_type_mapping = {
    PluginType.PLUGIN_TYPE_CLOUD_API: dsl.PluginType.SERVICE,
    PluginType.PLUGIN_TYPE_CLOUD_CODE: dsl.PluginType.CODE,
}

api_method_mapping = {
    PluginApiMethod.PLUGIN_API_METHOD_GET: "GET",
    PluginApiMethod.PLUGIN_API_METHOD_POST: "POST",
    PluginApiMethod.PLUGIN_API_METHOD_PUT: "PUT",
    PluginApiMethod.PLUGIN_API_METHOD_DELETE: "DELETE",
}

param_type_mapping = {
    ParamType.PARAM_TYPE_STRING: "string",
    ParamType.PARAM_TYPE_INT: "integer",
    ParamType.PARAM_TYPE_BOOL: "boolean",
    ParamType.PARAM_TYPE_ARRAY_STRING: "array",
    ParamType.PARAM_TYPE_ARRAY_INT: "array",
    ParamType.PARAM_TYPE_ARRAY_BOOL: "array",
    ParamType.PARAM_TYPE_OBJECT: "object",
}

param_send_method_type_mapping = {
    ParamSendMethod.PARAM_SEND_METHOD_NONE: "",
    ParamSendMethod.PARAM_SEND_METHOD_HEADER: "Headers",
    ParamSendMethod.PARAM_SEND_METHOD_QUERY: "Query",
    ParamSendMethod.PARAM_SEND_METHOD_BODY: "Body",
}


def _plugin_tool_param_convert(params: List[PluginToolParam]) -> List[dsl.Param]:
    converted_params: List[dsl.Param] = []
    for param in params:
        converted_param = dsl.Param(
            name=param.name,
            description=param.desc,
            type=param_type_mapping.get(param.type),
            required=param.is_required,
            method=param_send_method_type_mapping.get(param.method),
        )
        converted_params.append(converted_param)

    return converted_params


def _plugin_api_header_convert(headers: List[PluginApiHeader]) -> Dict[str, Any]:
    converted_header: Dict[str, Any] = {}
    for header in headers:
        converted_header[header.name] = header.value
    return converted_header


def plugin_api_tool_convert(url: str, api_info: Dict[str, Any]) -> Dict[str, Any]:
    api = PluginApiInfo(**api_info)
    convert_api = dsl.RestfulApiSchema(
        tool_id=api.tool_id,
        name=api.name,
        description=api.desc,
        path=url + api.path,
        method=api_method_mapping.get(api.method),
        params=_plugin_tool_param_convert(api.request_params),
        response=_plugin_tool_param_convert(api.response_params),
        headers=_plugin_api_header_convert(api.headers),
    )
    return convert_api.model_dump()


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


def plugin_tool_convert(plugin_info: PluginBaseDBPd, tool: Dict[str, Any]) -> Dict[str, Any]:
    if plugin_info.plugin_type == PluginType.PLUGIN_TYPE_CLOUD_API:
        return plugin_api_tool_convert(plugin_info.url, tool)
    else:
        return plugin_code_tool_convert(tool)


def _plugin_config_convert(node: Node, space_id: str) -> Dict:
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
            tool=plugin_tool_convert(plugin_info, tool_info.model_dump()),
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

        plugin_info = PluginBaseDBPd(
            plugin_id=plugin_publish_info.plugin_id,
            plugin_type=plugin_publish_info.plugin_type,
            name=plugin_publish_info.name,
            desc=plugin_publish_info.desc,
            url=plugin_publish_info.url,
            plugin_version=plugin_publish_info.plugin_version,
        )

        configs = dsl.ToolCompConfig(
            type=plugin_type_mapping[plugin_info.plugin_type],
            tool=plugin_tool_convert(plugin_info, tool_info),
            exception_config=exception_conf,
        )
    return configs.model_dump()


def plugin_convert(node: Node, space_id: str) -> dsl.Component:
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
            configs=_plugin_config_convert(node, space_id),
            name=data.title
        )
    except Exception as e:
        raise RuntimeError(f"Failed to convert plugin tool node: {str(e)}") from e
