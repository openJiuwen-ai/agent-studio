#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, Dict, List

from openjiuwen.core.common.exception.exception import JiuWenBaseException
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.utils.tool.base import Tool
from openjiuwen.core.utils.tool.param import Param
from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi

from openjiuwen_studio.core.common.dsl import PluginCodeConfig as DlPluginCodeConfig
from openjiuwen_studio.core.common.dsl import RestfulApiSchema as DlRestfulApiSchema
from openjiuwen_studio.core.executor.component.component_impl.code_comp import CodeComponent
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen.core.utils.tool.schema import ToolInfo


class ServiceTool:
    def __init__(self, restfulapischema: DlRestfulApiSchema) -> None:
        self.restfulapischema: DlRestfulApiSchema = restfulapischema

    def compile(self) -> RestfulApi:
        params: List[Param] = []
        builtin_params: List[Param] = []
        for i in self.restfulapischema.params:
            if i.runtime:
                param = Param(name=i.name, description=i.description, type=i.type, required=i.required, method=i.method)
                params.append(param)
            else:
                builtin_param = Param(name=i.name, description=i.description, type=i.type, required=i.required,
                                      method=i.method, default_value=i.default_value)
                builtin_params.append(builtin_param)
        responses: List[Param] = []
        for j in self.restfulapischema.response:
            response_param = Param(name=j.name, description=j.description, type=j.type, required=j.required)
            responses.append(response_param)
        # Use the existing name field if available, otherwise fall back to tool_id
        tool_name = self.restfulapischema.name or self.restfulapischema.tool_id
        tool = RestfulApi(name=tool_name, description=self.restfulapischema.description,
                          params=params, path=self.restfulapischema.path,
                          headers=self.restfulapischema.headers, method=self.restfulapischema.method,
                          response=responses, builtin_params=builtin_params)
        return tool


class CodeTool:
    def __init__(self, codeschema: DlPluginCodeConfig) -> None:
        self.codeschema: DlPluginCodeConfig = codeschema

    def compile(self) -> Tool:
        tool = PluginCodeTool(tool_id=self.codeschema.tool_id, conf=self.codeschema)
        return tool


class PluginCodeTool(CodeComponent, Tool):
    def __init__(self, tool_id: str, conf: DlPluginCodeConfig) -> None:
        super().__init__(node_id=tool_id, conf=conf)
        self.conf: DlPluginCodeConfig = conf
        self.tool_id: str = tool_id
        self.node_id: str = tool_id
        # Use the existing name field if available, otherwise fall back to tool_id
        self.name: str = conf.name or tool_id
        self.params: List[Param] = self.conf.input_params
        self.description = self.conf.description

    def get_tool_info(self) -> ToolInfo:
        tool_info_dict = Param.format_functions(self)
        tool_info = ToolInfo(**tool_info_dict)
        return tool_info

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
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
        final_result: Dict[str, Any] = {'errCode': err_code, 'errMessage': err_msg, 'data': result_data}
        return final_result
