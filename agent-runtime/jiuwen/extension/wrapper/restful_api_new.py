# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
RestfulApiCardNew and RestfulApiToolNew -- 新版 RESTful API 工具实现。

基于 RestfulApiToolNew.md 设计方案，继承 openjiuwen 的 Tool 基类，
支持注册到 Runner.resource_mgr.add_tool()。

核心特点：
1. RestfulApiCardNew: 扩展的 RESTful API Card，包含旧版 RestFulAPI 所有配置信息
2. RestfulApiToolNew: 继承自 Tool，包含所有执行逻辑
"""

import asyncio
import json
import os
import ssl
from enum import Enum
from json import JSONDecodeError
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import aiohttp
import requests
from aiohttp import FormData
from jiuwen.common.config import config
from jiuwen.common.configs.env_constants import (
    EXECUTION_NODE_TIMEOUT_KEY,
    JIUWEN_PROXY_ENABLE_KEY,
    PLUGIN_REQUEST_TIMEOUT_KEY,
)
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.net import Connector
from jiuwen.common.utils.utils import (
    format_exception_reason,
    illegal_url,
    url_to_ip_with_protocol_and_port,
)
from jiuwen.insight.manager import TraceManager
from jiuwen.insight.utils import get_instance_info
from jiuwen.orchestration.flow.stream.base import SseStreamData
from jiuwen.orchestration.flow.string_utils import is_boolean_string, string_to_bool
from jiuwen.plugin.common import constant, exception
from jiuwen.plugin.common.constant import (
    HTTP_METHOD,
    PLUGIN_DEFAULT_MAX_TIME_OUT,
    PLUGIN_DEFAULT_PERIOD_ROUND,
    REQUEST_TIME_OUT,
)
from jiuwen.plugin.models.api_utils import ApiUtils
from jiuwen.plugin.models.param import Param
from jiuwen.plugin.models.request_params import RequestParams, RequestParamsCreator
from openjiuwen.core.foundation.tool import Tool
from openjiuwen.core.foundation.tool.base import Input, Output, ToolCard
from pydantic import Field, ValidationError

DATA_PREFIX = "data:"

_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
_ssl_context.options |= ssl.OP_NO_TLSv1
_ssl_context.options |= ssl.OP_NO_TLSv1_1
_ssl_context.options |= ssl.OP_NO_RENEGOTIATION
_ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
_ssl_context.set_ciphers(
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256"
)
_is_cert_loaded = False

DEFAULT_STREAM_PLUGIN_BUFSIZE = 64 * 1024

_time_out_seconds = float(os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, REQUEST_TIME_OUT))
_time_out_aiohttp = aiohttp.ClientTimeout(total=_time_out_seconds)


class RestfulApiCardNew(ToolCard):
    """
    扩展的 RESTful API Card

    包含旧版 RestFulAPI 所有配置信息，
    由 IR 解析后创建，用于初始化 RestfulApiToolNew
    """

    model_config = {"arbitrary_types_allowed": True}

    params: List[Param] = Field(default_factory=list, description="输入参数列表")
    path: str = Field(default="", description="API URL 路径")
    headers: Dict[str, Any] = Field(default_factory=dict, description="HTTP 请求头")
    method: str = Field(default="POST", description="HTTP 方法")
    response: List[Param] = Field(default_factory=list, description="输出参数列表")

    plugin_name: str = Field(default="", description="插件名称")
    plugin_desc: str = Field(default="", description="插件描述")
    auth: Dict[str, Any] = Field(default_factory=dict, description="认证配置")
    label: str = Field(default="", description="标签")

    related_info: Optional[Dict[str, Any]] = Field(default=None, description="相关信息")
    status: Optional[int] = Field(default=None, description="状态")
    principle: str = Field(default="", description="原则")
    query_params: Dict[str, Any] = Field(default_factory=dict, description="查询参数")
    user_id: str = Field(default="", description="用户 ID")
    plugin_dependency: Dict[str, Any] = Field(
        default_factory=dict, description="插件依赖"
    )
    async_conf: Dict[str, Any] = Field(default_factory=dict, description="异步配置")
    async_switch: bool = Field(default=False, description="异步开关")
    is_from_ir: bool = Field(default=False, description="是否来自 IR")
    input_parameters: Dict[str, str] = Field(
        default_factory=dict, description="输入参数映射"
    )
    file_handler: str = Field(default="", description="文件处理器")

    plugin_reade_buffer_size: int = Field(
        default=DEFAULT_STREAM_PLUGIN_BUFSIZE, description="流式插件读取缓冲区大小"
    )
    cert: Optional[Union[bool, str]] = Field(default=None, description="SSL 证书配置")
    timeout: float = Field(default=_time_out_seconds, description="请求超时时间")


class RestfulApiToolNew(Tool):
    """
    新版 RESTful API Tool

    继承自 Tool，可被 Runner.resource_mgr.add_tool() 注册
    支持文件上传、异步轮询、流式响应、multi_queries、SSL证书、URL验证、认证钩子等旧版所有功能
    """

    IS_FROM_IR_KEY = "is_from_ir"
    DATA_PREFIX = "data:"

    class ParamLocation(Enum):
        """参数位置枚举"""

        BODY = "Body"
        HEADERS = "Headers"
        QUERY = "Query"
        PATH = "Path"

    def __init__(self, card: RestfulApiCardNew):
        super().__init__(card)
        self._name: str = card.name
        self._description: str = card.description
        self._params: List[Param] = card.params
        self._path: str = card.path
        self._headers: dict = card.headers
        self._method: str = card.method.upper()
        self._response: List[Param] = card.response

        self._plugin_name: str = card.plugin_name
        self._plugin_desc: str = card.plugin_desc
        self._auth: dict = ApiUtils.encrypt_service_auth(card.auth or {})
        self._label: str = card.label

        self._related_info: dict = card.related_info
        self._status: int = card.status
        self._principle: str = card.principle
        self._query_params: dict = card.query_params
        self._user_id: str = card.user_id
        self._plugin_dependency: dict = card.plugin_dependency
        self._id: str = card.id
        self._async_conf: dict = card.async_conf
        self._async_switch: bool = card.async_conf and card.async_conf.get(
            "async_switch"
        )
        self._is_from_ir: bool = card.is_from_ir
        self._input_parameters: dict = card.input_parameters
        self._file_handler: str = card.file_handler

        self._plugin_reade_buffer_size: int = card.plugin_reade_buffer_size
        self._cert = card.cert
        self._timeout = card.timeout

        if self._method not in HTTP_METHOD:
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.HttpMethodError,
            )

        if self._cert and is_boolean_string(self._cert):
            self._cert = string_to_bool(self._cert)
        if self._cert is None:
            self._cert = False

        self._request_params_creator = RequestParamsCreator(
            api_name=self._name,
            api_headers=self._headers,
            api_input_params=self._params,
            api_url=self._path,
            api_from_ir=self._is_from_ir,
            api_auth=self._auth,
            api_error_handler=self._log_and_raise_error,
            api_cert=self._cert,
            plugin_dependency=self._plugin_dependency,
            file_handler=self._file_handler,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def params(self) -> List[Param]:
        return self._params

    @property
    def path(self) -> str:
        return self._path

    @property
    def headers(self) -> dict:
        return self._headers

    @property
    def method(self) -> str:
        return self._method

    @property
    def response(self) -> List[Param]:
        return self._response

    @property
    def plugin_name(self) -> str:
        return self._plugin_name

    @property
    def plugin_desc(self) -> str:
        return self._plugin_desc

    @property
    def auth(self) -> dict:
        return self._auth

    @property
    def label(self) -> str:
        return self._label

    @property
    def related_info(self) -> dict:
        return self._related_info

    @property
    def status(self) -> int:
        return self._status

    @property
    def principle(self) -> str:
        return self._principle

    @property
    def query_params(self) -> dict:
        return self._query_params

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def plugin_dependency(self) -> dict:
        return self._plugin_dependency

    @property
    def id(self) -> str:
        return self._id

    @property
    def async_conf(self) -> dict:
        return self._async_conf

    @property
    def async_switch(self) -> bool:
        return self._async_switch

    @property
    def is_from_ir(self) -> bool:
        return self._is_from_ir

    @property
    def input_parameters(self) -> dict:
        return self._input_parameters

    @property
    def plugin_reade_buffer_size(self) -> int:
        return self._plugin_reade_buffer_size

    @staticmethod
    def _check_status_ok(code: int) -> bool:
        """检查响应状态是否成功 (200-299)"""
        return 200 <= code < 300

    async def invoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用（Tool 接口）
        """
        return await self.ainvoke(inputs, **kwargs)

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用（与 RestFulAPI.ainvoke 完全一致）
        """
        trace_manager = self._create_tracer_manager(**kwargs)
        try:
            await trace_manager.on_plugin_start(inputs)
            request_params = self._request_params_creator.create(
                inputs, file_params_list_type=False, **kwargs
            )
            self._validate_request_params(request_params)
            self._load_cert(request_params)

            has_multi_queries = (
                isinstance(inputs, dict) and "multi_queries" in inputs.keys()
            )
            if has_multi_queries:
                response_data = self._send_multi_queries_request(
                    request_params, inputs.get("multi_queries")
                )
            elif self._async_switch:
                response_data = await self._send_async_post_request(request_params)
            else:
                response_data = await self._async_send_request(
                    request_params, trace_manager
                )
        except Exception as error:
            await trace_manager.on_plugin_error(error)
            response_data = self._create_error_invoke_response(error)
        return response_data

    def stream(self, inputs: Input, **kwargs) -> AsyncIterator[Output]:
        """
        流式输出接口（Tool 接口）
        """
        return self.astream(inputs, **kwargs)

    async def astream(self, inputs: Input, **kwargs) -> AsyncIterator[Output]:
        """
        异步流式输出接口（与 RestFulAPI.astream 完全一致）
        """
        trace_manager = self._create_tracer_manager(**kwargs)
        try:
            await trace_manager.on_plugin_start(inputs)
            request_params = self._request_params_creator.create(inputs, **kwargs)
            self._validate_request_params(request_params)

            request = self._create_post_request(request_params)
            connector = Connector().get_tcp_connector()
            proxy_enable = os.getenv(JIUWEN_PROXY_ENABLE_KEY, "").lower() == "true"
            logger.info(f"{JIUWEN_PROXY_ENABLE_KEY} is {proxy_enable}")
            async with aiohttp.ClientSession(
                connector=connector,
                connector_owner=connector is None,
                trust_env=proxy_enable,
            ) as session:
                async with session.request(
                    **request, read_bufsize=self._plugin_reade_buffer_size
                ) as response:
                    if not self._check_status_ok(response.status):
                        raise exception.PluginCommonException(
                            code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                            message=f"plugin response code {response.status} error.",
                        )
                    await trace_manager.on_plugin_end(response)
                    async for line_bytes in response.content:
                        try:
                            line = line_bytes.decode("utf-8").strip()
                            if line and line.startswith(self.DATA_PREFIX):
                                line = line.removeprefix(self.DATA_PREFIX)
                                yield line
                        except UnicodeDecodeError:
                            continue
        except Exception as error:
            await trace_manager.on_plugin_error(error)
            self._create_error_stream_response(error)

    def _create_post_request(self, request_params: RequestParams) -> dict:
        """创建 POST 请求"""
        request = dict(
            method=self._method,
            url=request_params.ip_address_url,
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(
                total=float(os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, REQUEST_TIME_OUT))
            ),
            params=request_params.query_params_in_inputs,
            **request_params.request_arg,
        )

        if request_params.file_params:
            form_data = aiohttp.FormData()
            for key, (
                filename,
                file_obj,
                content_type,
            ) in request_params.file_params.items():
                form_data.add_field(
                    key, file_obj, filename=filename, content_type=content_type
                )
            request["data"] = form_data
        else:
            request["headers"] = request_params.headers
        return request

    def _create_tracer_manager(self, **kwargs) -> TraceManager:
        """创建追踪管理器"""
        return TraceManager.generate_manager(
            kwargs.pop("trace_handlers", None),
            get_instance_info(self, blacklist=["auth", "headers"]),
        )

    def _create_error_invoke_response(self, error: Exception) -> dict:
        """生成 invoke error response"""
        if isinstance(
            error,
            (
                requests.exceptions.ReadTimeout,
                requests.exceptions.Timeout,
                asyncio.TimeoutError,
            ),
        ):
            return self._format_output(
                StatusCode.PLUGIN_REQUEST_TIMEOUT_ERROR.code,
                "plugin request time out",
                "",
            )
        if isinstance(
            error, (requests.exceptions.ProxyError, aiohttp.ClientHttpProxyError)
        ):
            return self._format_output(
                StatusCode.PLUGIN_PROXY_CONNECT_ERROR.code,
                StatusCode.PLUGIN_PROXY_CONNECT_ERROR.errmsg,
                output="",
            )
        if isinstance(error, exception.JiuWenBaseException):
            return self._format_output(
                error.error_code, error.message, f"{error.message}"
            )
        if hasattr(error, "error_code") and hasattr(error, "message"):
            return self._format_output(
                error.error_code, error.message, f"{error.message}"
            )
        return self._format_output(
            StatusCode.PLUGIN_UNEXPECTED_ERROR.code,
            f"plugin request unknown error: {error}",
            "",
        )

    def _create_error_stream_response(self, error: Exception):
        """生成 stream error response"""
        if isinstance(
            error,
            (
                requests.exceptions.ReadTimeout,
                requests.exceptions.Timeout,
                asyncio.TimeoutError,
                aiohttp.ServerTimeoutError,
            ),
        ):
            raise exception.JiuWenBaseException(
                StatusCode.PLUGIN_REQUEST_TIMEOUT_ERROR.code,
                f"{StatusCode.PLUGIN_REQUEST_TIMEOUT_ERROR.errmsg}: {error}",
            ) from error
        if isinstance(
            error, (requests.exceptions.ProxyError, aiohttp.ClientProxyConnectionError)
        ):
            raise exception.JiuWenBaseException(
                StatusCode.PLUGIN_PROXY_CONNECT_ERROR.code,
                f"{StatusCode.PLUGIN_PROXY_CONNECT_ERROR.errmsg}: {error}",
            ) from error
        raise exception.JiuWenBaseException(
            StatusCode.PLUGIN_UNEXPECTED_ERROR.code,
            f"{StatusCode.PLUGIN_UNEXPECTED_ERROR.errmsg}: {error}",
        ) from error

    def _format_output(
        self, status_code: int, message: str = None, output: Any = None
    ) -> dict:
        """格式化输出"""
        return {
            constant.ERR_CODE: status_code,
            constant.ERR_MESSAGE: message,
            constant.RESTFUL_DATA: output if output is not None else {},
        }

    def _log_and_raise_error(self, err_msg: str):
        """记录并抛出认证错误"""
        err_msg = f"{err_msg}. plugin_name is {self._plugin_name}"
        logger.error(err_msg)
        raise exception.PluginRestfulAuthException(message=err_msg)

    async def _send_async_post_request(self, request_params: RequestParams) -> dict:
        """调用异步接口，并轮询调用查询接口"""
        try:
            max_timeout = self._async_conf.get(
                "max_timeout", PLUGIN_DEFAULT_MAX_TIME_OUT
            )
            interval = self._async_conf.get(
                "period_of_round", PLUGIN_DEFAULT_PERIOD_ROUND
            )
            timeout = float(os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, REQUEST_TIME_OUT))

            if (
                int(
                    os.environ.get(
                        EXECUTION_NODE_TIMEOUT_KEY, constant.PLUGIN_MAX_TIME_OUT
                    )
                )
                < max_timeout
            ):
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message=f"async time {max_timeout} exceed node time",
                )

            proxy_enable = os.getenv(JIUWEN_PROXY_ENABLE_KEY, "").lower() == "true"
            logger.info(f"{JIUWEN_PROXY_ENABLE_KEY} is {proxy_enable}")
            connector = Connector().get_tcp_connector()

            async with aiohttp.ClientSession(
                connector=connector,
                connector_owner=connector is None,
                trust_env=proxy_enable,
            ) as session:
                request = dict(
                    url=request_params.ip_address_url,
                    ssl=request_params.api_cert,
                    allow_redirects=False,
                    timeout=timeout,
                )

                if request_params.file_params:
                    request["data"] = self._format_to_form_data(
                        request_params.file_params, request_params.request_arg
                    )
                else:
                    request["headers"] = request_params.headers
                    request["json"] = request_params.request_arg

                async with session.post(**request) as post_response:
                    post_result = await post_response.json()

                if not post_result.get("task_id"):
                    raise exception.PluginCommonException(
                        code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                        message="async plugin taskid not exist",
                    )

                status_get_url = self._async_conf.get(
                    "callback_url", ""
                ) + post_result.get("task_id", "")

                check_request = dict(
                    url=status_get_url,
                    ssl=request_params.api_cert,
                    timeout=timeout,
                    allow_redirects=False,
                )

                while max_timeout > 0:
                    result = await self._schedule_check_task(
                        interval, check_request, session
                    )
                    if result:
                        return result
                    max_timeout -= interval

                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                    message="async plugin request time out",
                )
        except Exception as e:
            logger.error(f"async post request failed: {e}")
            if isinstance(e, exception.JiuWenBaseException):
                err_code = e.error_code
            else:
                err_code = StatusCode.PLUGIN_UNEXPECTED_ERROR.code
            return self._format_output(
                err_code,
                format_exception_reason(e, reason="Async request processing failed"),
                {},
            )

    async def _schedule_check_task(
        self, interval: float, check_request: dict, session: aiohttp.ClientSession
    ):
        """调度检查任务"""
        async with session.get(**check_request) as status_response:
            status_result = await status_response.json()

            if status_result.get("status") == constant.AsyncPluginStatus.complete.value:
                result = status_result.get("result")
                if (
                    constant.ERR_CODE not in result
                    or constant.ERR_MESSAGE not in result
                    or constant.RESTFUL_DATA not in result
                ):
                    return self._format_output(0, "success", result)
                return result

            if status_result.get("status") == constant.AsyncPluginStatus.fail.value:
                error = status_result.get("error")
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                    message=f"async plugin task failed {error}",
                )

        await asyncio.sleep(interval)

    async def _async_send_request(
        self, request_params: RequestParams, trace_manager: TraceManager
    ) -> dict:
        """异步发送请求"""
        connector = Connector().get_tcp_connector()
        proxy_enable = os.environ.get(JIUWEN_PROXY_ENABLE_KEY, "").lower() == "true"
        logger.info(f"{JIUWEN_PROXY_ENABLE_KEY} is {proxy_enable}")

        async with aiohttp.ClientSession(
            connector=connector,
            connector_owner=connector is None,
            trust_env=proxy_enable,
        ) as session:
            request = dict(
                method=self._method,
                url=request_params.ip_address_url,
                ssl=request_params.api_cert,
                allow_redirects=False,
                timeout=_time_out_aiohttp,
                params=request_params.query_params_in_inputs,
            )

            if (
                request_params.file_params
                or self._headers.get("Content-Type") == "multipart/form-data"
            ):
                request["data"] = self._format_to_form_data(
                    request_params.file_params, request_params.request_arg
                )
            else:
                request["headers"] = request_params.headers
                request.update(**request_params.request_arg)

            async with session.request(**request) as response:
                response_data = await self._format_async_response(
                    response, request_params.param_wrapper
                )

        if (
            isinstance(response_data, dict)
            and response_data.get(constant.ERR_CODE, 0) != 0
        ):
            await trace_manager.on_plugin_error(
                exception.PluginCommonException(
                    message=response_data.get(constant.ERR_MESSAGE, "plugin error")
                )
            )
        else:
            await trace_manager.on_plugin_end(response_data)

        return response_data

    def _send_multi_queries_request(
        self, request_params: RequestParams, multi_queries: list
    ) -> dict:
        """发送多个查询请求"""
        result = []
        for simple_input in multi_queries:
            simple_arg = dict(json=simple_input) if simple_input else dict()
            response = self._send_request(
                request_params, simple_arg, need_headers_when_has_file_params=True
            )
            result.append(response.get(constant.RESTFUL_DATA))
        return self._format_output(0, "success", result)

    def _send_request(
        self,
        request_params: RequestParams,
        request_args: dict,
        need_headers_when_has_file_params: bool = False,
        trace_manager: TraceManager = None,
        is_stream: bool = False,
    ):
        """发送请求"""
        request = dict(
            method=self._method,
            url=request_params.ip_address_url,
            verify=request_params.api_cert,
            allow_redirects=False,
            timeout=float(os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, REQUEST_TIME_OUT)),
            stream=True,
            params=request_params.query_params_in_inputs,
        )

        if request_params.file_params:
            request["files"] = request_params.file_params

        if not request_params.file_params or need_headers_when_has_file_params:
            request["headers"] = request_params.headers

        response = requests.request(**request, **request_args)

        if is_stream:
            return self._format_stream_response(response, trace_manager)

        return self._format_response(response, request_params)

    def _format_stream_response(self, stream_response, trace_manager: TraceManager):
        """格式化流式响应"""
        if not self._check_status_ok(stream_response.status_code):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                message=f"plugin response code {stream_response.status_code} error.",
            )

        asyncio.ensure_future(trace_manager.on_plugin_end(stream_response))

        for line in stream_response.iter_lines():
            line = line.decode("utf-8")
            if line and line.startswith(self.DATA_PREFIX):
                line = line.removeprefix(self.DATA_PREFIX)
                try:
                    yield SseStreamData(**json.loads(line))
                except (ValidationError, JSONDecodeError):
                    yield line

    def _format_response(self, response, request_params: RequestParams) -> dict:
        """格式化响应"""
        if not self._check_status_ok(response.status_code):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                message=f"plugin response code {response.status_code} error.",
            )

        content = b""
        for chunk in response.iter_content(chunk_size=1024):
            content += chunk
            if len(content) > constant.MAX_RESULT_SIZE:
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_TOO_BIG_ERROR,
                    message=StatusCode.PLUGIN_RESPONSE_TOO_BIG_ERROR.errmsg,
                )

        try:
            res = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError:
            return self._format_output(0, "success", response.text)

        param_wrapper = request_params.param_wrapper
        if (
            isinstance(param_wrapper, dict)
            and param_wrapper.get("output_list", False) is True
        ):
            if not res or not isinstance(res, list):
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_FORMAT_ERROR,
                    message=StatusCode.PLUGIN_RESPONSE_FORMAT_ERROR.errmsg,
                )
            res = res[0]

        if (
            constant.ERR_CODE not in res
            or constant.ERR_MESSAGE not in res
            or constant.RESTFUL_DATA not in res
        ):
            return self._format_output(0, "success", res)

        return res

    async def _format_async_response(
        self, response: aiohttp.ClientResponse, param_wrapper: dict
    ) -> dict:
        """异步格式化响应"""
        if not self._check_status_ok(response.status):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                message=f"plugin response code {response.status} error.",
            )

        content = b""
        async for chunk in response.content.iter_chunked(1024):
            content += chunk
            if len(content) > constant.MAX_RESULT_SIZE:
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_TOO_BIG_ERROR,
                    message=StatusCode.PLUGIN_RESPONSE_TOO_BIG_ERROR.errmsg,
                )

        try:
            res = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError:
            return self._format_output(0, "success", content.decode("utf-8"))

        if (
            isinstance(param_wrapper, dict)
            and param_wrapper.get("output_list", False) is True
        ):
            if not res or not isinstance(res, list):
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_FORMAT_ERROR,
                    message=StatusCode.PLUGIN_RESPONSE_FORMAT_ERROR.errmsg,
                )
            res = res[0]

        if (
            constant.ERR_CODE not in res
            or constant.ERR_MESSAGE not in res
            or constant.RESTFUL_DATA not in res
        ):
            return self._format_output(0, "success", res)

        return res

    def _validate_request_params(self, request_params: RequestParams, **kwargs):
        """验证请求参数"""
        self._check_url_validate(request_params.ip_address_url)
        self._validate_auth_hook_function(request_params, **kwargs)

    def _format_to_form_data(self, file_params, request_arg: dict = None) -> FormData:
        """将变量转变成 FormData"""
        merged_data = FormData()
        for file_param in file_params:
            for key, item in file_param.items():
                merged_data.add_field(name=key, value=item[1], filename=item[0])
        for key, value in (request_arg or {}).get("json", {}).items():
            merged_data.add_field(
                key, json.dumps(value), content_type="application/json"
            )
        return merged_data

    def _load_cert(self, request_params: RequestParams):
        """加载证书"""
        global _is_cert_loaded
        if isinstance(request_params.api_cert, str):
            if not _is_cert_loaded:
                _ssl_context.load_cert_chain(certfile=request_params.api_cert)
                _is_cert_loaded = True
            request_params.api_cert = _ssl_context

    def _check_url_validate(self, url: str):
        """检查 URL 验证"""
        if url and illegal_url(url):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="plugin's url is illegal",
            )

        skip_ssrf_check = config.get("restful_api", {}).get("skip_ssrf_check")
        if (
            not skip_ssrf_check
            or not is_boolean_string(skip_ssrf_check)
            or not string_to_bool(skip_ssrf_check)
        ):
            url_to_ip_with_protocol_and_port(url)

    def _validate_auth_hook_function(self, request_params: RequestParams, **kwargs):
        """验证认证钩子函数"""
        plugin_auth_hook_function = self._plugin_dependency.get(
            "hook_function", {}
        ).get("plugin_auth")
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
                self._auth,
                request_params.headers,
                request_params.query_params_in_inputs,
                self._id,
            )
        except Exception as e:
            logger.error(f"执行函数{plugin_auth_hook_function}失败")
            logger.error(e)
