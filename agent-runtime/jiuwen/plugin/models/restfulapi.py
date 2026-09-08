#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Restful API class"""

import asyncio
import json
import os
import ssl
from abc import ABC
from enum import Enum
from json import JSONDecodeError
from typing import List, Iterator, AsyncIterator

import aiohttp
import requests
from aiohttp import FormData
from jiuwen.common.config import config
from jiuwen.common.configs.env_constants import (
    EXECUTION_NODE_TIMEOUT_KEY,
    PLUGIN_REQUEST_TIMEOUT_KEY,
    PLUGIN_SSL_API_CERT_KEY,
    STREAM_PLUGIN_BUFSIZE_KEY,
    JIUWEN_PROXY_ENABLE_KEY,
)
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.net import Connector
from jiuwen.common.utils.utils import (
    illegal_url,
    url_to_ip_with_protocol_and_port,
    format_exception_reason,
)
from jiuwen.insight.manager import TraceManager
from jiuwen.insight.utils import get_instance_info
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.flow.stream.base import SseStreamData
from jiuwen.orchestration.flow.string_utils import is_boolean_string, string_to_bool
from jiuwen.orchestration.utils import Input, Output
from jiuwen.plugin.common import constant
from jiuwen.plugin.common import exception
from jiuwen.plugin.common.constant import (
    HTTP_METHOD,
    AsyncPluginStatus,
    PLUGIN_DEFAULT_MAX_TIME_OUT,
    PLUGIN_DEFAULT_PERIOD_ROUND,
)
from jiuwen.plugin.models.api_utils import ApiUtils
from jiuwen.plugin.models.param import Param
from jiuwen.plugin.models.request_params import RequestParamsCreator, RequestParams
from pydantic import ValidationError

DATA_PREFIX = "data:"
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.options |= ssl.OP_NO_TLSv1
ssl_context.options |= ssl.OP_NO_TLSv1_1
ssl_context.options |= ssl.OP_NO_RENEGOTIATION
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
ssl_context.set_ciphers(
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256"
)
IS_CERT_LOADED = False

time_out_seconds = float(
    os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, constant.REQUEST_TIME_OUT)
)
time_out_aiohttp = aiohttp.ClientTimeout(total=time_out_seconds)

DEFAULT_STREAM_PLUGIN_BUFSIZE = 64 * 1024


class RestFulAPI(Invokable, ABC):
    """Restful API class"""

    IS_FROM_IR_KEY = "is_from_ir"

    class ParamLocation(Enum):
        """param location"""

        BODY = "Body"
        HEADERS = "Headers"
        QUERY = "Query"
        PATH = "Path"

    def __init__(
        self,
        name: str,
        description: str,
        params: List[Param],
        path: str,
        headers: dict,
        method: str,
        response: List[Param],
        plugin_name: str,
        plugin_desc: str,
        auth: dict,
        label: str = "",
        **kwargs,
    ):
        self.name: str = name
        self.description: str = description
        self.params: List[Param] = params
        self.path: str = path
        self.headers: dict = headers
        self.method: str = method.upper()
        self.response: List[Param] = response
        self.plugin_name = plugin_name
        self.plugin_desc = plugin_desc
        self.auth: dict = ApiUtils.encrypt_service_auth(auth or {})
        self.label = label
        self.related_info: dict = kwargs.get("related_info")
        self.status: int = kwargs.get("status")
        self.principle: str = kwargs.get("principle")
        self.query_params = {}
        self.user_id: str = kwargs.get("user_id", "")
        self.plugin_dependency: dict = kwargs.get("plugin_dependency", {})
        self.id: str = kwargs.get("id", "")
        self.async_conf = kwargs.get("async_conf", {})
        self.async_switch = self.async_conf and self.async_conf.get("async_switch")
        self.is_from_ir = kwargs.get(RestFulAPI.IS_FROM_IR_KEY, False)
        self.input_parameters = kwargs.get("input_parameters", {})
        self.plugin_reade_buffer_size = int(
            os.environ.get(STREAM_PLUGIN_BUFSIZE_KEY, DEFAULT_STREAM_PLUGIN_BUFSIZE)
        )
        if self.method not in HTTP_METHOD:
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.HttpMethodError,
            )
        self._cert = os.environ.get(PLUGIN_SSL_API_CERT_KEY)
        if self._cert and is_boolean_string(self._cert):
            self._cert = string_to_bool(self._cert)
        # 默认开启SSL校验
        if self._cert is None:
            self._cert = True
        self.request_params_creator = RequestParamsCreator(
            api_name=self.name,
            api_headers=self.headers,
            api_input_params=self.params,
            api_url=self.path,
            api_from_ir=self.is_from_ir,
            api_auth=self.auth,
            api_error_handler=self._log_and_raise_error,
            api_cert=self._cert,
            **kwargs,
        )

    @staticmethod
    def _check_status_ok(code):
        """检查响应状态是否成功 (200-299)"""
        return 200 <= code < 300

    def invoke(self, inputs: Input, **kwargs) -> Output:
        """invoke接口"""
        logger.error("restful api not support invoke, please use ainvoke instead")
        pass

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用
        """
        trace_manager = self._create_tracer_manager(**kwargs)
        try:
            await trace_manager.on_plugin_start(inputs)
            request_params = self.request_params_creator.create(
                inputs, file_params_list_type=False, **kwargs
            )
            self._validate_request_params(request_params)
            self._load_cert(request_params)
            has_multi_queries = (
                isinstance(inputs, dict) and "multi_queries" in inputs.keys()
            )
            if has_multi_queries:
                # 并行工具调用将参数合并为multi_queries参数
                response_data = await self._send_multi_queries_request(
                    request_params, inputs.get("multi_queries")
                )
            elif self.async_switch:
                # 异步post调用插件接口
                response_data = await self._send_async_post_request(request_params)
            else:
                # 异步调用插件接口
                response_data = await self._async_send_request(
                    request_params, trace_manager
                )
        except Exception as error:
            await trace_manager.on_plugin_error(error)
            response_data = self._create_error_invoke_response(error)
        return response_data

    def stream(self, inputs: Input, **kwargs) -> Iterator[Output]:
        """
        流式输出接口
        """
        logger.error("restful api not support stream, please use astream instead")
        pass

    async def astream(self, inputs: Input, **kwargs) -> AsyncIterator[Output]:
        """
        异步流式输出接口
        """
        trace_manager = self._create_tracer_manager(**kwargs)
        try:
            await trace_manager.on_plugin_start(inputs)
            request_params = self.request_params_creator.create(inputs, **kwargs)
            self._validate_request_params(request_params)

            # 处理files参数
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
                    **request, read_bufsize=self.plugin_reade_buffer_size
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
                            if line and line.startswith(DATA_PREFIX):
                                line = line.removeprefix(DATA_PREFIX)
                                yield line
                        except UnicodeDecodeError:
                            # 处理编码错误，跳过无效行
                            continue
        except Exception as error:
            await trace_manager.on_plugin_error(error)
            self._create_error_stream_response(error)

    def _create_post_request(self, request_params):
        request = dict(
            method=self.method,
            url=request_params.ip_address_url,
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(
                total=float(
                    os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, constant.REQUEST_TIME_OUT)
                )
            ),
            params=request_params.query_params_in_inputs,
            **request_params.request_arg,
        )

        # 根据是否有文件参数调整请求配置
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

    def _create_tracer_manager(self, **kwargs):
        return TraceManager.generate_manager(
            kwargs.pop("trace_handlers", None),
            get_instance_info(self, blacklist=["auth", "headers"]),
        )

    def _create_error_invoke_response(self, error):
        """生成invoke error response"""
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

    def _create_error_stream_response(self, error):
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
        if isinstance(error, exception.JiuWenBaseException):
            raise exception.JiuWenBaseException(
                error.error_code,
                error.message,
            ) from error
        raise exception.JiuWenBaseException(
            StatusCode.PLUGIN_UNEXPECTED_ERROR.code,
            f"{StatusCode.PLUGIN_UNEXPECTED_ERROR.errmsg}: {error}",
        ) from error

    def _format_output(self, status_code, message=None, output=None):
        return {
            constant.ERR_CODE: status_code,
            constant.ERR_MESSAGE: message,
            constant.RESTFUL_DATA: output if output is not None else {},
        }

    def _log_and_raise_error(self, err_msg):
        """raise plugin auth error"""
        err_msg = f"{err_msg}. plugin_name is {self.plugin_name}"
        logger.error(err_msg)
        raise exception.PluginRestfulAuthException(message=err_msg)

    async def _send_async_post_request(self, request_params):
        """调用异步接口，并轮询调用查询接口"""
        try:
            max_timeout = self.async_conf.get(
                "max_timeout", PLUGIN_DEFAULT_MAX_TIME_OUT
            )
            interval = self.async_conf.get(
                "period_of_round", PLUGIN_DEFAULT_PERIOD_ROUND
            )
            timeout = float(
                os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, constant.REQUEST_TIME_OUT)
            )
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
                # 待确认post的返回结构体，暂定 {"task_id": "xxxx"}
                if not post_result.get("task_id"):
                    raise exception.PluginCommonException(
                        code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                        message="async plugin taskid not exist",
                    )
                # 构造查询状态的 URL
                status_get_url = self.async_conf.get(
                    "callback_url", ""
                ) + post_result.get("task_id", "")
                # 循环查询任务状态
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
                # 如果超时，抛出超时异常
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

    async def _schedule_check_task(self, interval, check_request, session):
        async with session.get(**check_request) as status_response:
            status_result = await status_response.json()
            if status_result.get("status") == AsyncPluginStatus.complete.value:
                # 如果任务完成，返回结果
                result = status_result.get("result")
                if (
                    constant.ERR_CODE not in result
                    or constant.ERR_MESSAGE not in result
                    or constant.RESTFUL_DATA not in result
                ):
                    return self._format_output(0, "success", result)
                return result
            if status_result.get("status") == AsyncPluginStatus.fail.value:
                # 如果任务失败，抛出异常
                error = status_result.get("error")
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                    message=f"async plugin task failed {error}",
                )
            # 等待一段时间后再次查询
        await asyncio.sleep(interval)

    async def _async_send_request(self, request_params, trace_manager):
        connector = Connector().get_tcp_connector()
        proxy_enable = os.environ.get(JIUWEN_PROXY_ENABLE_KEY, "").lower() == "true"
        logger.info(f"{JIUWEN_PROXY_ENABLE_KEY} is {proxy_enable}")
        async with aiohttp.ClientSession(
            connector=connector,
            connector_owner=connector is None,
            trust_env=proxy_enable,
        ) as session:
            # 创建请求
            request = dict(
                method=self.method,
                url=request_params.ip_address_url,
                ssl=request_params.api_cert,
                allow_redirects=False,
                timeout=time_out_aiohttp,
                params=request_params.query_params_in_inputs,
            )
            if (
                request_params.file_params
                or self.headers.get("Content-Type") == "multipart/form-data"
            ):
                request["data"] = self._format_to_form_data(
                    request_params.file_params, request_params.request_arg
                )
            else:
                request["headers"] = request_params.headers
                request.update(**request_params.request_arg)
            # 异步发送请求
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

    async def _send_multi_queries_request(self, request_params, multi_queries) -> dict:
        result = []
        for simple_input in multi_queries:
            simple_arg = dict(json=simple_input) if simple_input else dict()
            response = await self._send_request(
                request_params, simple_arg, need_headers_when_has_file_params=True
            )
            result.append(response.get(constant.RESTFUL_DATA))
        return self._format_output(0, "success", result)

    async def _send_request(
        self,
        request_params,
        request_args,
        need_headers_when_has_file_params=False,
        trace_manager=None,
        is_stream=False,
    ):
        request = dict(
            method=self.method,
            url=request_params.ip_address_url,
            verify=request_params.api_cert,
            allow_redirects=False,
            timeout=float(
                os.getenv(PLUGIN_REQUEST_TIMEOUT_KEY, constant.REQUEST_TIME_OUT)
            ),
            stream=True,
            params=request_params.query_params_in_inputs,
        )
        if request_params.file_params:
            request["files"] = request_params.file_params
        if not request_params.file_params or need_headers_when_has_file_params:
            request["headers"] = request_params.headers
        response = requests.request(**request, **request_args)
        if is_stream:
            return await self._format_stream_response(response, trace_manager)
        return self._format_response(response, request_params)

    async def _format_stream_response(self, stream_response, trace_manager):
        if not self._check_status_ok(stream_response.status_code):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                message=f"plugin response code {stream_response.status_code} error.",
            )
        await trace_manager.on_plugin_end(stream_response)
        for line in stream_response.iter_lines():
            line = line.decode("utf-8")
            if line and line.startswith(DATA_PREFIX):
                line = line.removeprefix(DATA_PREFIX)
                try:
                    yield SseStreamData(**json.loads(line))
                except (ValidationError, JSONDecodeError):
                    yield line

    def _format_response(self, response, param_wrapper):
        if not self._check_status_ok(response.status_code):
            # code is not HTTP_CODE_OK
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                message=f"plugin response code {response.status_code} error.",
            )
        content = b""
        for chunk in response.iter_content(chunk_size=1024):
            content += chunk
            if len(content) > constant.MAX_RESULT_SIZE:
                # 如果超过限制字节数，直接报错
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_RESPONSE_TOO_BIG_ERROR,
                    message=StatusCode.PLUGIN_RESPONSE_TOO_BIG_ERROR.errmsg,
                )
        try:
            res = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError:
            return self._format_output(0, "success", response.text)
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
        self, response: aiohttp.ClientResponse, param_wrapper
    ):
        """
        异步收集 response 返回数据
        """
        if not self._check_status_ok(response.status):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_RESPONSE_HTTP_CODE_ERROR,
                message=f"plugin response code {response.status} error.",
            )

        content = b""
        async for chunk in response.content.iter_chunked(1024):
            content += chunk
            if len(content) > constant.MAX_RESULT_SIZE:
                # 如果超过限制字节数，直接报错
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
        self._check_url_validate(request_params.ip_address_url)
        self._validate_auth_hook_function(request_params, **kwargs)

    def _format_to_form_data(self, file_params, request_arg=None):
        """将变量转变成Form_data"""
        merged_data = FormData()
        for file_param in file_params:
            for key, item in file_param.items():
                merged_data.add_field(name=key, value=item[1], filename=item[0])
        for key, value in request_arg.get("json", {}).items():
            merged_data.add_field(
                key, json.dumps(value), content_type="application/json"
            )
        return merged_data

    def _load_cert(self, request_params):
        if isinstance(request_params.api_cert, str):
            global IS_CERT_LOADED
            if not IS_CERT_LOADED:  # 只加载一次
                ssl_context.load_cert_chain(
                    certfile=request_params.api_cert
                )  # 加载证书 PEM 证书
                IS_CERT_LOADED = True
            request_params.api_cert = ssl_context

    def _check_url_validate(self, url):
        if url and illegal_url(url):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="plugin's url is illegal",
            )
            # 获取url, 打开 SKIP_SSRF_CHECK 才会跳过SSRF检查
        skip_ssrf_check = config.get("restful_api", {}).get("skip_ssrf_check")
        if (
            not skip_ssrf_check
            or not is_boolean_string(skip_ssrf_check)
            or not string_to_bool(skip_ssrf_check)
        ):
            # check url
            url_to_ip_with_protocol_and_port(url)

    def _validate_auth_hook_function(self, request_params: RequestParams):
        plugin_auth_hook_function = self.plugin_dependency.get("hook_function", {}).get(
            "plugin_auth"
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
                self.id,
            )
        except Exception as e:
            logger.error(f"执行函数{plugin_auth_hook_function}失败")
            logger.error(e)
