#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""This module contains Plugin ir utils class"""

import copy
import json
import os
from typing import Optional, Dict, List, Any

from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.utils.utils import (
    illegal_agent_logo,
    illegal_url,
    convert_camel_to_snake,
    format_exception_reason,
)
from jiuwen.plugin import Param
from jiuwen.plugin.common import constant
from jiuwen.plugin.common.constant import (
    PLUGIN_MAX_TIME_OUT,
    PLUGIN_DEFAULT_MAX_TIME_OUT,
    PLUGIN_DEFAULT_PERIOD_ROUND,
    PLUGIN_MAX_PERIOD_ROUND,
)
from jiuwen.plugin.common.exception import PluginCommonException
from jiuwen.plugin.models.api_utils import ApiUtils
from jiuwen.plugin.models.mcpapi import McpServer
from jiuwen.plugin.models.restfulapi import RestFulAPI
from pydantic import BaseModel, Field, field_validator

FIELD_KEY = "audit_entity"
HEADERS = "headers"
AUTH = "auth"
DEFAULT_MAX_STR_LENGTH = 100
DEFAULT_MIN_STR_LENGTH = 0


class PluginIRConverter:
    @staticmethod
    def ir_to_plugin(ir_data, agent_id="", conversation_id=""):
        """function to convert plugin ir into plugin instance"""
        if os.environ.get("USE_TOOL_WRAPPER") == "true":
            from jiuwen.extension.wrapper.restful_api_loader import (
                load_restful_api_from_ir,
            )
            from jiuwen.integration import AgentCoreRestfulLayer

            tool_id = load_restful_api_from_ir(ir_data, tag=agent_id)
            return AgentCoreRestfulLayer(
                tool_id=tool_id,
                agent_id=agent_id,
                session_id=conversation_id,
            )
        if not isinstance(ir_data, dict):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="plugin ir info is not dict type",
            )
        ir_data = convert_camel_to_snake(ir_data, skip_fields=[HEADERS, AUTH])
        try:
            RestfulPluginInputValidate(**ir_data)
            # plugin的body和response支持Object类型不配置schema
            params = Plugin.param_deserialization(ir_data.get("arguments", []), True)
            response = Plugin.param_deserialization(ir_data.get("response", []), True)
        except PluginCommonException as e:
            raise e
        except Exception as e:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=format_exception_reason(
                    e, reason="Plugin parameter validation failed"
                ),
            ) from e
        if PluginIRConverter.is_knowledge_retrieval_ir(ir_data):
            from agent_runtime.extension.tool.knowledge_retrieval_tool import (
                build_knowledge_retrieval_tool,
            )
            from openjiuwen.core.common.logging import workflow_logger
            return build_knowledge_retrieval_tool(ir_data, params)
        url = ir_data.get("url", "").strip().strip("`").strip()
        description_key = "description"
        name_key = "name"
        headers = copy.deepcopy(ir_data.get(HEADERS, {}))

        # auth默认实现
        auth = ir_data.get(AUTH, {})
        # auth定制实现
        auth = PluginIRConverter.extend_auth(auth, ir_data)

        restful_api = RestFulAPI(
            name=ir_data.get(name_key),
            description=ir_data.get(description_key),
            plugin_name=ir_data.get(name_key),
            plugin_desc=ir_data.get(description_key),
            path=url,
            method=ir_data.get("method"),
            params=params,
            headers=headers,
            auth=auth,
            response=response,
            principle=ir_data.get("principle", ""),
            related_info={"logo": ir_data.get("logo", "")},
            plugin_dependency=ir_data.get("plugin_dependency", {}),
            id=ir_data.get("id"),
            async_conf=ir_data.get("async_invoke", {}),
            **{RestFulAPI.IS_FROM_IR_KEY: True},
            input_parameters=ir_data.get("input_parameters", {}),
            file_handler=ir_data.get("file_handler", ""),
        )

        Plugin.check_valid_value(restful_api)
        Plugin.check_async_conf(restful_api)
        return restful_api

    @staticmethod
    def extend_auth(auth, ir_data):
        """
        auth取值扩展点
        """
        return auth

    @staticmethod
    def is_knowledge_retrieval_ir(ir_data):
        from agent_runtime.extension.tool.knowledge_retrieval_tool import (
            is_knowledge_retrieval_ir,
        )

        return is_knowledge_retrieval_ir(ir_data)


class McpIRConverter:
    @staticmethod
    def ir_to_mcp(ir_data, **kwargs):
        """function to convert mcp ir into mcp instance"""
        ir_data = convert_camel_to_snake(ir_data, skip_fields=[HEADERS, AUTH])

        url = ir_data.get("url", "")
        mcp_headers = copy.deepcopy(ir_data.get(HEADERS, {}))
        mcp_headers = McpIRConverter.extend_heads(mcp_headers, ir_data, **kwargs)
        auth = ir_data.get("auth", {})
        server_name = ir_data.get("name", "")
        transport_type = ir_data.get("type", "")
        mcp_choose_tools = ir_data.get("mcp_choose_tools")

        plugin_dependency = ir_data.get("plugin_dependency", {})

        combined_param = {
            "plugin_dependency": plugin_dependency,
            "auth": auth,
        }

        if url and illegal_url(url):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="mcp's url is illegal",
            )
        mcps = McpServer(
            url,
            mcp_headers,
            server_name,
            transport_type,
            combined_param,
            mcp_choose_tools,
        )
        return mcps

    @staticmethod
    def extend_heads(mcp_headers, ir_data, **kwargs):
        """mcp header扩展，处理认证信息：service auth解密、iam-token透传"""
        import logging
        from jiuwen.plugin.models.api_utils import ApiUtils  # noqa: redefined-outer-name
        from jiuwen.plugin.common import constant  # noqa: redefined-outer-name

        x_auth_token = "x-auth-token"

        auth_type = mcp_headers.get(constant.AUTH_SCOPE)
        auth_params = {}
        if auth_type and auth_type == constant.AUTH_SERVICE:
            auth_params = ApiUtils.decrypt_service_auth(mcp_headers)
            if not auth_params.get("headers") and not auth_params.get("query"):
                logging.info(
                    "service auth mode, but dont have headers or query auth data"
                )

        mcp_headers.clear()
        mcp_headers.update(auth_params.get("headers", {}))

        auth_type = ir_data.get("auth_type")
        if auth_type and auth_type.lower() == "iam-token":
            cust_headers = kwargs.get("cust_headers")
            if cust_headers and cust_headers.get(x_auth_token):
                mcp_headers[x_auth_token] = cust_headers.get(x_auth_token)
        return mcp_headers


MCP_PARAM_LOCATIONS = [
    RestFulAPI.ParamLocation.BODY.value,
    RestFulAPI.ParamLocation.HEADERS.value,
    RestFulAPI.ParamLocation.QUERY.value,
]


class Plugin:
    _PARAM_LOCATIONS = [param_loc.value for param_loc in RestFulAPI.ParamLocation]

    _PARAM_LOCATIONS_STR = " ".join(_PARAM_LOCATIONS)

    @staticmethod
    def param_deserialization(arguments, allow_schema_is_empty: bool = False):
        """param deserialization"""
        params = []
        level_key = "level"
        for p in arguments:
            if "name" not in p or "description" not in p:
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="name and description needed",
                )
            if isinstance(p.get(level_key), str) and p.get(level_key).isdigit():
                p[level_key] = int(p.get(level_key))
            params.append(
                Param(
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    default_value=p.get("default_value"),
                    param_type=p.get("type", ""),
                    required=p.get("required", False),
                    visible=p.get("visible", True),
                    level=p.get(level_key, 0),
                    method=p.get("method", RestFulAPI.ParamLocation.BODY.value),
                    schema=p.get("schema", []),
                    actual_type=p.get("actual_type", ""),
                    allow_schema_is_empty=allow_schema_is_empty,
                )
            )
        return params

    @staticmethod
    def check_valid_value(plugin):
        """check if value is valid"""
        for param in plugin.params:
            if param.method not in Plugin._PARAM_LOCATIONS:
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="parameter's request type only supports {}".format(
                        Plugin._PARAM_LOCATIONS_STR
                    ),
                )
        if plugin.method.lower() not in ["post", "get"]:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="request method only supports post and get",
            )

    @staticmethod
    def check_valid_header(plugin):
        """check if there are duplicate names in the headers"""
        # 参数名 lower转换，主要是因为请求Header中会自动转化为首字母大写的形式。 这里通过lower对参数名做归一化后判断是否重复
        header_param_set = set()
        for param in plugin.params:
            if param.method == RestFulAPI.ParamLocation.HEADERS.value:
                if param.type != "string":
                    raise PluginCommonException(
                        code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                        message="parameter which request type is Headers only "
                        "supports string type",
                    )
                header_param_set.add(
                    param.name.lower() if isinstance(param.name, str) else param.name
                )
        for key in plugin.headers.keys():
            if key.lower() in header_param_set:
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="header and header param with the same name parameters",
                )
            header_param_set.add(key.lower() if isinstance(key, str) else key)
        auth_header_param_set = Plugin.get_header_param_from_auth(plugin)
        if header_param_set & auth_header_param_set:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="header, header param and auth with same name parameters",
            )

    @staticmethod
    def check_async_conf(plugin: RestFulAPI):
        """check async conf"""
        async_conf = plugin.async_conf
        if not isinstance(async_conf, dict):
            if not async_conf:
                return
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="async_conf should be dict",
            )
        async_switch = async_conf.get("async_switch", False)
        if async_switch is False:
            return
        if not isinstance(async_switch, bool):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="async switch should be bool",
            )
        call_back_url = async_conf.get("callback_url")
        if not call_back_url or not isinstance(call_back_url, str):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="async url should be str",
            )
        max_time_out = async_conf.get("max_timeout", PLUGIN_DEFAULT_MAX_TIME_OUT)
        if not max_time_out or not isinstance(max_time_out, int):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="max_time_out should be int",
            )
        if max_time_out <= 0 or max_time_out > PLUGIN_MAX_TIME_OUT:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=f"max_round_count should between [0, {PLUGIN_MAX_TIME_OUT}]",
            )
        period_of_round = async_conf.get("period_of_round", PLUGIN_DEFAULT_PERIOD_ROUND)
        if not period_of_round or not isinstance(period_of_round, int):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="period_of_round should be int",
            )
        if period_of_round <= 0 or period_of_round > PLUGIN_MAX_PERIOD_ROUND:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=f"period_of_round should between [0, {PLUGIN_MAX_PERIOD_ROUND}]",
            )
        return

    @staticmethod
    def get_header_param_from_auth(plugin):
        """get header param names from auth"""
        header_param_set = set()
        auth_type = plugin.auth.get(constant.AUTH_SCOPE, None)
        if not auth_type:
            return header_param_set
        if auth_type == constant.AUTH_USER:
            target = plugin.auth.get("target", {})
            target_domain_key = target.get("domain")
            if target_domain_key == "headers":
                for key in target.get("auth_keys", []):
                    header_param_set.add(key.lower() if isinstance(key, str) else key)
        elif auth_type == constant.AUTH_SERVICE:
            now_auth = ApiUtils.decrypt_service_auth(plugin.auth)
            headers = now_auth.get("headers")
            if headers and isinstance(headers, dict):
                for key in headers.keys():
                    header_param_set.add(key.lower() if isinstance(key, str) else key)
        return header_param_set


class Params(BaseModel):
    """Params Validator"""

    name: str
    description: str
    type: str
    method: Optional[str] = ""
    required: bool
    defaultValue: Optional[str] = ""
    schema: Optional[Any] = None


class RestfulPluginInputValidate(BaseModel):
    """RestfulPluginInput"""

    name: str = Field(..., min_length=1, max_length=2000)
    description: str = Field(..., min_length=1, max_length=20000)
    url: str = Field(..., min_length=1, max_length=1000)
    method: str = Field(..., min_length=1, max_length=20)
    headers: Optional[Dict] = Field(
        default={}, title="插件请求头", max_str_length=20000
    )
    principle: Optional[str] = Field(default="", min_length=1, max_length=1000)
    logo: Optional[str] = Field(default="", max_length=50000)
    auth: Optional[Dict] = Field(default={}, title="插件鉴权信息", max_str_length=20000)
    plugin_dependency: Optional[Dict] = Field(
        default={}, title="入参、出参wrapper信息", max_str_length=2000
    )
    arguments: Optional[List[Params]] = Field(
        default=[], title="插件请求入参列表", max_str_length=10000
    )
    response: Optional[List[Params]] = Field(
        default=[], title="插件返回结果列表", max_str_length=10000
    )
    id: str = Field(..., min_length=1, max_length=2000)
    input_parameters: Optional[Dict] = Field(
        default={}, title="插件参数引用信息", max_str_length=20000
    )

    @classmethod
    def validate_length(cls, field_name, value):
        """validate length"""
        max_str_length = cls.model_fields[field_name].json_schema_extra.get(
            "max_str_length", DEFAULT_MAX_STR_LENGTH
        )
        min_str_length = cls.model_fields[field_name].json_schema_extra.get(
            "min_str_length", DEFAULT_MIN_STR_LENGTH
        )
        if isinstance(value, str):
            return min_str_length <= len(value) <= max_str_length
        json_str = json.dumps(value, ensure_ascii=False)
        return min_str_length <= len(json_str) <= max_str_length

    @field_validator("headers", mode="before")
    @classmethod
    def validate_headers(cls, value):
        """validate headers"""
        if not cls.validate_length("headers", value):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="headers is too large or small",
            )
        return value

    @field_validator("auth", mode="before")
    @classmethod
    def validate_auth(cls, value):
        """validate auth"""
        if not cls.validate_length("auth", value):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="auth is too large or small",
            )
        if not isinstance(value, dict):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="auth should be dict type",
            )
        scope = value.get("scope")
        if scope == "USER":
            source = value.get("source")
            target = value.get("target")
            if not isinstance(source, dict) or not isinstance(target, dict):
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="auth user scope source and target shoudle be dict",
                )
            required_keys = ["domain", "auth_keys"]
            missing_source_keys = [key for key in required_keys if key not in source]
            missing_target_key = [key for key in required_keys if key not in target]
            # domain和auth_keys必须存在
            if missing_source_keys or missing_target_key:
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="auth user scope should contain auth_keys and domain",
                )
            if not isinstance(source.get("domain"), str) or not isinstance(
                target.get("domain"), str
            ):
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="auth user scope domain should be str",
                )
            if not isinstance(source.get("auth_keys"), list) or not isinstance(
                target.get("auth_keys"), list
            ):
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="auth user scope auth_keys should be list",
                )
        elif scope == "SERVICE":
            if "headers" not in value and "query" not in value:
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="auth service scope should contain query or headers",
                )
            for field in ["headers", "query"]:
                if field in value and not isinstance(value.get(field), dict):
                    raise PluginCommonException(
                        code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                        message=f"auth service scope {field} should be dict",
                    )
        return value

    @field_validator("plugin_dependency", mode="before")
    @classmethod
    def validate_dependency(cls, value):
        """validate plugin_dependency"""
        if not cls.validate_length("plugin_dependency", value):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="plugin_dependency is too large or small",
            )
        params_wrapper = value.get("params_wrapper", {})
        input_list = params_wrapper.get("input_list")
        output_list = params_wrapper.get("output_list")
        if input_list is not None and not isinstance(input_list, bool):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="input_list is not bool",
            )
        if output_list is not None and not isinstance(output_list, bool):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="output_list is not bool",
            )
        return value

    @field_validator("arguments", mode="before")
    @classmethod
    def validate_arguments(cls, value):
        """validate arguments"""
        if not cls.validate_length("arguments", value):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="arguments is too large or small",
            )
        return value

    @field_validator("response", mode="before")
    @classmethod
    def validate_response(cls, value):
        """validate response"""
        if not cls.validate_length("response", value):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="response is too large or small",
            )
        return value

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, value):
        """校验url合法性"""
        if value:
            # 清理 URL 前后的空白字符和反引号等格式标记
            value = value.strip().strip("`").strip()
            if not value.startswith(("http://", "https://")):
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="URL must start with http:// or https://",
                )
        return value

    @field_validator("logo", mode="before")
    @classmethod
    def validate_logo(cls, value):
        """校验url合法性"""
        if value and illegal_agent_logo(value):
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="plugin logo is illegal",
            )
        return value
