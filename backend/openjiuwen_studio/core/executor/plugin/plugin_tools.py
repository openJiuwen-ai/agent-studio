#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import re
from typing import List, Dict, Any

from openjiuwen.core.foundation.tool import Tool, ToolCard, Input, Output
from openjiuwen.core.foundation.tool import RestfulApiCard, RestfulApi

from openjiuwen_studio.core.common.dsl import PluginCodeConfig as DlPluginCodeConfig
from openjiuwen_studio.core.common.dsl import RestfulApiSchema as DlRestfulApiSchema, Param

from openjiuwen_studio.core.executor.component.component_impl.code_comp import CodeComponent
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode

TYPE = "type"
OBJECT = "object"
REQUIRED = "required"
PROPERTIES = "properties"


# OpenAI工具函数名称验证正则表达式
_FUNCTION_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def sanitize_tool_name(name: str) -> str:
    """
    清理工具名称，确保符合OpenAI API的命名规范 ^[a-zA-Z0-9_-]+$
    """
    if not name:
        return "unnamed_tool"

    if _FUNCTION_NAME_PATTERN.match(name):
        return name

    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)

    if sanitized and sanitized[0].isdigit():
        sanitized = 'tool_' + sanitized
    if not sanitized:
        sanitized = "unnamed_tool"
    if len(sanitized) > 64:
        sanitized = sanitized[:64]

    return sanitized


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
        if param.default_value is not None:
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
        for i in self.restfulapischema.params:
            if not i.runtime:
                if i.method == "query" and i.default_value is not None:
                    queries[i.name] = i.default_value
                elif i.method == "header" and i.default_value is not None:
                    headers[i.name] = i.default_value

        # 验证和清理工具名称
        raw_tool_name = self.restfulapischema.name or self.restfulapischema.tool_id
        tool_name = sanitize_tool_name(raw_tool_name)
        input_params = convert_params_to_json_schema(self.restfulapischema.params)
        restfulapi_card = RestfulApiCard(name=tool_name,
                                         description=self.restfulapischema.description, input_params=input_params,
                                         url=self.restfulapischema.path, method=self.restfulapischema.method,
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
        raw_name = conf.name or card.id
        self.name: str = sanitize_tool_name(raw_name)
        self.params = conf.input_params
        self.description = self.conf.description

    @classmethod
    def create(cls, conf: DlPluginCodeConfig):
        """工厂方法：从 DSL 配置创建符合 Tool 规范的实例"""
        # 转换参数 schema
        input_schema = convert_params_to_json_schema(conf.input_params)

        # 构建 ToolCard
        raw_name = conf.name or conf.tool_id
        sanitized_name = sanitize_tool_name(raw_name)
        card = PluginCodeCard(
            name=sanitized_name,
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

        error_body, response = await self._run(language, code, inputs, exception_config, execute_type)
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
