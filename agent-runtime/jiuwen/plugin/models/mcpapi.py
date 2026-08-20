#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Restful API class"""

import copy
import os
from abc import ABC
from builtins import ExceptionGroup
from typing import Any
from urllib.parse import urlencode

import aiohttp
from jiuwen.common.configs.env_constants import (
    PLUGIN_REQUEST_TIMEOUT_KEY,
    PLUGIN_SSL_API_CERT_KEY,
)
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger, get_x_request_id, get_x_execution_id
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.insight.manager import TraceManager
from jiuwen.insight.utils import get_instance_info
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.flow.constant import X_EXECUTION_ID, X_REQUEST_ID
from jiuwen.orchestration.flow.string_utils import is_boolean_string, string_to_bool
from jiuwen.orchestration.utils import Input, Output
from jiuwen.plugin.common import constant
from jiuwen.plugin.common import exception
from jiuwen.plugin.models.api_utils import ApiUtils
from jiuwen.plugin.models.request_params import RequestParamsCreator, RequestParams
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

DATA_PREFIX = "data:"
IS_CERT_LOADED = False
time_out_seconds = float(
    os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, constant.REQUEST_TIME_OUT)
)
time_out_aiohttp = aiohttp.ClientTimeout(total=time_out_seconds)
mcp_time_out_seconds = float(os.getenv("MCP_TIME_OUT_SECONDS", 120))


def flatten_exception_group(eg: ExceptionGroup | BaseException) -> list[BaseException]:
    """将所有嵌套异常展开为平面列表"""
    if not isinstance(eg, ExceptionGroup):
        return [eg]

    result = []
    for exc in eg.exceptions:
        if isinstance(exc, ExceptionGroup):
            result.extend(flatten_exception_group(exc))
        else:
            result.append(exc)
    return result


def exception_group_to_str_simple(eg: ExceptionGroup) -> str:
    """将所有异常转为字符串列表并合并"""
    return "\n".join(
        f"{type(e).__name__}: {str(e)}" for e in flatten_exception_group(eg)
    )


class McpAPI(Invokable, ABC):
    """MCP API class"""

    def __init__(
        self,
        server_url: str,
        name: str,
        parameters: dict,
        headers: dict,
        server_name: str,
        transport_type: str,
        plugin_dependency: dict = None,
        auth: dict = None,
        description="",
        params: list = None,
        input_parameters: dict = None,
        **kwargs,
    ) -> None:
        self.server_url = server_url
        self.name = name
        self.parameters = parameters or {}
        self.params = params
        self.headers = headers
        self.description = description
        self.server_name = server_name
        self.transport_type = transport_type
        self.is_mcp = True
        self.auth: dict = ApiUtils.encrypt_service_auth(auth or {})
        self.plugin_dependency: dict = plugin_dependency
        self.input_parameters = input_parameters
        # 覆盖九问代码 九问默认开启SSL校验 修改为默认不开启
        cert = os.environ.get(PLUGIN_SSL_API_CERT_KEY)
        if cert and is_boolean_string(cert):
            cert = string_to_bool(cert)
        # 默认不开启SSL校验
        if cert is None:
            cert = False
        self.request_params_creator = RequestParamsCreator(
            api_name=self.name,
            api_headers=self.headers,
            api_input_params=self.params,
            api_url=self.server_url,
            api_auth=self.auth,
            api_error_handler=self._raise_error,
            ignore_default_not_exit=False,
            api_cert=cert,
        )

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用
        """
        trace_manager = TraceManager.generate_manager(
            kwargs.pop("trace_handlers", None),
            get_instance_info(self, blacklist=["auth", "headers", "query_params"]),
        )
        await trace_manager.on_plugin_start(inputs)

        try:
            request_params = await self.request_params_creator.create(inputs, **kwargs)
            request_params.headers[X_REQUEST_ID] = get_x_request_id()
            request_params.headers[X_EXECUTION_ID] = get_x_execution_id()

            # 处理自定义鉴权的请求头
            self.replace_mcp_headers_extra(request_params, **kwargs)

            # mcp自定义鉴权
            self._validate_auth_hook_function(request_params)

            #  同构：MCP 出站剥 auth_keys 的 cust- 前缀 + captured 覆盖（auth_hook 后、出站前）
            from jiuwen.extension.wrapper.customer_header_inject import inject_customer_headers_to_mcp
            inject_customer_headers_to_mcp(request_params)

            tmp_url = copy.copy(request_params.ip_address_url)
            if request_params.query_params_in_inputs.items():
                if "?" in tmp_url:
                    tmp_url = (
                        f"&{tmp_url}{urlencode(request_params.query_params_in_inputs)}"
                    )
                else:
                    tmp_url = (
                        f"{tmp_url}?{urlencode(request_params.query_params_in_inputs)}"
                    )
            logger.info(f"MCP Request url {tmp_url}")

            if self.transport_type == "streamable_http":
                logger.debug("McpAPI is using streamable_http")
                if "X-Studio-Apikey" in request_params.headers:
                    request_params.headers["Accept"] = (
                        "application/json,text/event-stream"
                    )
                async with streamablehttp_client(
                    tmp_url,
                    headers=request_params.headers,
                    sse_read_timeout=mcp_time_out_seconds,
                    timeout=mcp_time_out_seconds,
                ) as (
                    read_stream,
                    write_stream,
                    _,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(self.name, inputs)
                        content = self._transform_result(result)
                        await trace_manager.on_plugin_end(content)
                        return {
                            constant.ERR_CODE: 0,
                            constant.ERR_MESSAGE: "success",
                            constant.RESTFUL_DATA: content,
                        }
            elif self.transport_type == "sse":
                logger.debug("McpAPI is using sse")
                async with sse_client(
                    tmp_url,
                    headers=request_params.headers,
                    sse_read_timeout=mcp_time_out_seconds,
                    timeout=mcp_time_out_seconds,
                ) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        result = await session.call_tool(self.name, inputs)
                        content = self._transform_result(result)
                        await trace_manager.on_plugin_end(content)
                        return {
                            constant.ERR_CODE: 0,
                            constant.ERR_MESSAGE: "success",
                            constant.RESTFUL_DATA: content,
                        }
            else:
                logger.debug(
                    "McpAPI does not support transport_type: %s", self.transport_type
                )
                return {
                    constant.ERR_CODE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code,
                    constant.ERR_MESSAGE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.errmsg.format(
                        error="Unsupported mcp transport type: {mcp_type}".format(
                            mcp_type=self.transport_type
                        )
                    ),
                    constant.RESTFUL_DATA: "",
                }

        except ExceptionGroup as eg:
            logger.error("MCP client invocation failed :", exc_info=True)
            await trace_manager.on_plugin_error(eg)
            return {
                constant.ERR_CODE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code,
                constant.ERR_MESSAGE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.errmsg.format(
                    error="ExceptionGroup"
                ),
                constant.RESTFUL_DATA: "",
            }
        except Exception as error:
            logger.error("MCP client invocation failed :", exc_info=True)
            await trace_manager.on_plugin_error(error)
            return {
                constant.ERR_CODE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code,
                constant.ERR_MESSAGE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.errmsg.format(
                    error="Exception"
                ),
                constant.RESTFUL_DATA: "",
            }

    def invoke(self, inputs: dict[str, Any], **kwargs):
        pass

    def replace_mcp_headers_extra(self, request_params, **kwargs):
        """mcp参数替换"""
        headers = request_params.headers
        updates = {}

        input_parameters = self.input_parameters

        # 获取用户入参变量
        runtime_context = kwargs.get("runtime_context")
        if runtime_context and hasattr(runtime_context, "agent_workflow_context"):
            req_params = runtime_context.agent_workflow_context.get(
                WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
            )
            updates = req_params.get("global_variables", {})

        # 安全处理：input_parameters 可能为 None
        if not input_parameters:
            return

        for key, value in input_parameters.items():
            inner = value[2:-2].strip()
            if inner.startswith("inputs.") and len(inner) > 7:
                path_in_inputs = inner[7:]
                value = updates.get(path_in_inputs, "")
                if value is not None and value != "" and key in headers:
                    headers[key] = value

    def _validate_auth_hook_function(self, request_params: RequestParams):
        plugin_auth_hook_function = self.plugin_dependency.get("hook_function", {}).get(
            "mcp_auth"
        )
        if not plugin_auth_hook_function:
            return
        auth_provider = None
        try:
            auth_provider = ApiUtils.get_hook_func(plugin_auth_hook_function)
        except Exception as e:
            logger.error(f"根据路径{plugin_auth_hook_function}获取函数失败")
            logger.error(e)
        if not auth_provider:
            return
        try:
            auth_provider(
                self.auth,
                request_params.headers,
                request_params.query_params_in_inputs,
                self.name,
            )
        except Exception as e:
            logger.error(f"执行函数{plugin_auth_hook_function}失败")
            logger.error(e)

    def _raise_error(self, err_msg):
        """raise plugin auth error"""
        err_msg = f"{err_msg}. mcp_name is {self.name}"
        logger.error(err_msg)
        raise exception.PluginRestfulAuthException(message=err_msg)

    def _transform_result(self, result):
        if hasattr(result, "structuredContent") and result.structuredContent:
            return result.structuredContent
        return result.content


class McpServer(McpAPI, ABC):
    """
    MCP Server class
    此类覆盖了九问的实现，九问原始实现没有处理认证信息，改成继承McpAPI并复用相关逻辑!
    """

    def __init__(
        self,
        server_url: str,
        headers: dict,
        name: str,
        transport_type: str,
        combined_param: dict = None,
        mcp_choose_tools: list = None,
    ):
        self.mcp_choose_tools = mcp_choose_tools
        super().__init__(
            server_url,
            name,
            {},
            headers,
            "",
            transport_type,
            combined_param.get("plugin_dependency", {}),
            combined_param.get("auth", {}),
            "",
            params=combined_param.get("params", []),
            input_parameters=combined_param.get("input_parameters", {}),
        )

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用
        """
        trace_manager = TraceManager.generate_manager(
            kwargs.pop("trace_handlers", None),
            get_instance_info(self, blacklist=["auth", "headers"]),
        )
        await trace_manager.on_plugin_start(inputs)
        try:
            request_params = await self.request_params_creator.create(inputs, **kwargs)
            request_params.headers[X_REQUEST_ID] = get_x_request_id()
            request_params.headers[X_EXECUTION_ID] = get_x_execution_id()

            # 处理自定义鉴权的请求头
            self.replace_mcp_headers_extra(request_params, **kwargs)

            # mcp自定义鉴权
            self._validate_auth_hook_function(request_params)

            #  同构：MCP 出站剥 auth_keys 的 cust- 前缀 + captured 覆盖（auth_hook 后、出站前）
            from jiuwen.extension.wrapper.customer_header_inject import inject_customer_headers_to_mcp
            inject_customer_headers_to_mcp(request_params)

            tmp_url = copy.copy(request_params.ip_address_url)
            if request_params.query_params_in_inputs.items():
                if "?" in tmp_url:
                    tmp_url = (
                        f"&{tmp_url}{urlencode(request_params.query_params_in_inputs)}"
                    )
                else:
                    tmp_url = (
                        f"{tmp_url}?{urlencode(request_params.query_params_in_inputs)}"
                    )
            logger.info(f"MCP Request url {tmp_url}")

            if self.mcp_choose_tools == []:
                return []

            if self.transport_type == "streamable_http":
                logger.debug("McpServer is using streamable_http")
                async with streamablehttp_client(
                    tmp_url,
                    headers=request_params.headers,
                    sse_read_timeout=mcp_time_out_seconds,
                    timeout=mcp_time_out_seconds,
                ) as (
                    read_stream,
                    write_stream,
                    _,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return self.process_tools_result(result)
            elif self.transport_type == "sse":
                logger.debug("McpServer is using sse")
                async with sse_client(
                    tmp_url,
                    headers=request_params.headers,
                    sse_read_timeout=mcp_time_out_seconds,
                    timeout=mcp_time_out_seconds,
                ) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return self.process_tools_result(result)
            else:
                logger.debug(
                    "McpServer does not support transport_type: %s", self.transport_type
                )
                return []

        except ExceptionGroup as eg:
            eg_str = exception_group_to_str_simple(eg)
            await trace_manager.on_plugin_error(eg)
            logger.warning(f"get mcp tools list error, {eg_str}")
            return []
        except Exception as error:
            await trace_manager.on_plugin_error(error)
            logger.warning("get mcp tools list error, please check mcp server.")
            return []

    def process_tools_result(self, result):
        """
        仅选择配置的mcp工具
        """
        if self.mcp_choose_tools is None:
            return result
        if result and result.tools:
            new_tools = []
            for mcp_tool in result.tools:
                if mcp_tool.name in self.mcp_choose_tools:
                    new_tools.append(mcp_tool)
            result.tools = new_tools
        return result

    def invoke(self, inputs: dict[str, Any], **kwargs):
        pass
