#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

"""
This module contains the FlowApi class, which is a subclass of Invokable.
FlowApi is responsible for invoking a specific API based on the configuration provided.
"""
import json
from typing import Any

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.flow.constant import USER_FIELDS
from jiuwen.orchestration.utils import Input, Output
from jiuwen.plugin import Param
from jiuwen.plugin.common.utils.ir_utils import Plugin, MCP_PARAM_LOCATIONS
from jiuwen.plugin.models.api_utils import transform_type
from jiuwen.plugin.models.mcpapi import McpAPI

TAG = " === FLOW_MCP === "


class FlowMcp(Invokable):
    """
    This class is used to encapsulate the API invoking process, making API invoking more convenient and concise.
    """

    def __init__(self):
        super().__init__()
        self._conf: dict = {}
        self.api: McpAPI = None
        self._is_older_version: bool = False

    def init(self, conf: dict, **kwargs):
        self._validate_configs(conf)
        self.runtime_context = kwargs.get("runtime_context")
        self._conf = conf
        self._init_api()

    def extends_headers(self, headers: dict):
        """
        headers扩展, 不能删除，为ei特殊实现
        """
        return headers

    def invoke(self, inputs: dict[str, Any], **kwargs):
        pass

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用mcp server
        """
        inputs = inputs.get(USER_FIELDS, {})
        if self.api:
            if not self._is_older_version:
                api_inputs = self._format_api_inputs(inputs)
            else:
                # 兼容老版本ir
                api_inputs = inputs
            api_outputs = await self.api.ainvoke(api_inputs, **kwargs)
            outputs = self._format_api_outputs(api_outputs)
            return {USER_FIELDS: outputs}
        return {
            USER_FIELDS: {"content": "not contain mcp api, not run", "isError": False}
        }

    def _init_api(self):
        if self._conf.get("type") in ["sse", "streamable_http"]:
            self._is_older_version = not self._conf.get("arguments")
            self.api = McpAPI(
                server_url=self._conf.get("url"),
                name=self._conf.get("tool_name"),
                parameters={},
                headers=self.extends_headers(self._conf.get("headers", {})),
                server_name=self._conf.get("name"),
                description=self._conf.get("description", ""),
                auth=self._conf.get("auth", {}),
                params=Plugin.param_deserialization(
                    self._conf.get("arguments", []), allow_schema_is_empty=True
                ),
                transport_type=self._conf.get("type"),
                plugin_dependency=self._conf.get("pluginDependency", {}),
            )
            if not self.api.params:
                return
            for param in self.api.params:
                if param.method not in MCP_PARAM_LOCATIONS:
                    raise JiuWenBaseException(
                        error_code=StatusCode.WORKFLOW_MCP_PARAM_METHOD_ERROR.code,
                        message="parameter's request type only supports {}".format(
                            MCP_PARAM_LOCATIONS
                        ),
                    )
                if not isinstance(param.required, bool):
                    if not isinstance(param.required, str) or str.lower(
                        param.required
                    ) not in ["true", "false"]:
                        raise JiuWenBaseException(
                            error_code=StatusCode.WORKFLOW_MCP_PARAM_TYPE_ERROR.code,
                            message=StatusCode.WORKFLOW_MCP_PARAM_TYPE_ERROR.errmsg.format(
                                param="required", type="bool"
                            ),
                        )

    def _format_api_inputs(self, inputs: dict) -> dict:
        api_params_dict = {param.name: param for param in self.api.params}
        api_inputs = {}
        for name, value in inputs.items():
            param: Param = api_params_dict.get(name)
            if param:
                api_inputs[name] = transform_type(value, param.type, name)
            else:
                logger.error("%s _prepare_inputs ERR", TAG)
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_API_INPUTS_ERROR.code,
                    message=f"{StatusCode.WORKFLOW_API_INPUTS_ERROR.errmsg}, param is {name}",
                )
        return api_inputs

    def _format_api_outputs(self, outputs: dict) -> dict:
        # 插件invoke的结果统一为data, errCode, errMessage，需要的字段都在data里头，需要额外做一层解析
        error_code = outputs.get("errCode", StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code)
        if error_code != StatusCode.SUCCESS.code:
            error_msg = outputs.get(
                "errMessage",
                "plugin execution error, and no error information is specified",
            )
            if isinstance(error_code, int) and (
                error_code < 105000 or error_code > 105999
            ):
                # 如果error code 不是内部插件的错误返回码，就统一一个错误码，并把原来的code和msg合并
                error_msg = f"plugin flow execute inner failed, errCode={error_code}, errMessage={type(error_msg)}"
                error_code = StatusCode.WORKFLOW_API_EXECUTE_ERROR.code
            raise JiuWenBaseException(error_code=error_code, message=error_msg)

        output_data = outputs.get("data", [])
        if output_data is None:
            response_data = []
        elif isinstance(output_data, list):
            response_data = [item.model_dump() for item in output_data]
        elif isinstance(output_data, dict):
            try:
                output_ids = {item.get("id") for item in self._conf.get("userFields", {}).get("outputs", [])}
            except Exception:
                output_ids = set()
            if "content" in output_ids and "content" not in output_data:
                return {"content": [{"type": "text", "text": json.dumps(output_data, ensure_ascii=False)}],
                        "isError": False}
            return output_data
        else:
            error_msg = (
                f"Expected list if 'content' field of CallToolResult is passed, \
                or expected dict if 'structuredContent' field of CallToolResult is passed, \
                got type: {type(output_data)}"
            )
            error_code = StatusCode.WORKFLOW_API_EXECUTE_ERROR.code
            raise JiuWenBaseException(error_code=error_code, message=error_msg)
        return {"content": response_data, "isError": False}

    def _validate_configs(self, config):
        mcp_type = config.get("type", "")
        if mcp_type not in ["sse", "streamable_http", "stdio"]:
            raise JiuWenBaseException(
                StatusCode.WORKFLOW_MCP_UNSUPPORTED_TYPE_ERROR.code,
                StatusCode.WORKFLOW_MCP_UNSUPPORTED_TYPE_ERROR.errmsg.format(
                    mcp_type=mcp_type
                ),
            )
        if mcp_type in ["sse", "streamable_http"]:
            if "url" not in config or "tool_name" not in config:
                raise JiuWenBaseException(
                    StatusCode.WORKFLOW_MCP_FIELD_EMPTY_TYPE_ERROR.code,
                    StatusCode.WORKFLOW_MCP_FIELD_EMPTY_TYPE_ERROR.errmsg.format(
                        field="url or tool_name", mcp_type=mcp_type
                    ),
                )
