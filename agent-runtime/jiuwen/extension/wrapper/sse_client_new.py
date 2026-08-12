# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
新版 SSE Client

设计要点：
- __client_name__ = "sse_new" 用于自动注册
- 每次调用新建 client/session（参考 mcpapi.py）
- 通过 headers 参数传入认证信息
- 支持 mcp_choose_tools 参数过滤工具列表
"""

import copy
import os
from builtins import ExceptionGroup
from typing import Any, List, Optional
from urllib.parse import urlencode

from jiuwen.common.configs.env_constants import PLUGIN_SSL_API_CERT_KEY
from jiuwen.common.log.base import get_x_request_id, get_x_execution_id
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS
from jiuwen.orchestration.flow.constant import X_EXECUTION_ID, X_REQUEST_ID
from jiuwen.orchestration.flow.string_utils import is_boolean_string, string_to_bool
from jiuwen.plugin.common import exception
from jiuwen.plugin.models.api_utils import ApiUtils
from jiuwen.plugin.models.request_params import RequestParamsCreator, RequestParams
from mcp import ClientSession
from mcp.client.sse import sse_client
from openjiuwen.core.common.logging import logger
from openjiuwen.core.foundation.tool.mcp.base import (
    McpServerConfig,
    NO_TIMEOUT,
    McpToolCard,
)
from openjiuwen.core.foundation.tool.mcp.client.mcp_client import McpClient

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


class SSEClientNew(McpClient):
    """
    新版 SSE Client

    设计要点：
    - __client_name__ = "sse_new" 用于自动注册到 ClientRegistry
    - 每次调用新建 client/session（参考 mcpapi.py 模式）
    - 通过 headers 参数传入认证信息
    - 支持 mcp_choose_tools 参数过滤工具列表
    """

    __client_name__ = "sse_new"

    def __init__(self, config: McpServerConfig):
        super().__init__(config)
        self._config = config
        self._server_path = config.server_path
        self._name = config.server_name

        self._plugin_dependency = config.params.get("plugin_dependency", {})
        self._tool_params = config.params.get("tool_params", [])
        self._mcp_choose_tools = config.params.get("mcp_choose_tools")
        self._auth = config.params.get("auth", {})
        self._input_parameters = config.params.get("input_parameters", {})

        self._auth_headers = dict(config.auth_headers or {})
        self._auth_query_params = dict(config.auth_query_params or {})

        cert = os.environ.get(PLUGIN_SSL_API_CERT_KEY)
        if cert and is_boolean_string(cert):
            cert = string_to_bool(cert)
        if cert is None:
            cert = True
        self._cert = cert

    async def connect(
        self, *, retry_times: int = 1, timeout: float = NO_TIMEOUT
    ) -> bool:
        """
        连接方法（保持接口兼容，实际每次调用都新建 session）

        注意：此方法仅用于 list_tools 获取工具列表，
        实际 call_tool 每次都会新建 client/session
        """
        return True

    async def disconnect(self, *, timeout: float = NO_TIMEOUT) -> bool:
        """断开连接（保持接口兼容）"""
        return True

    def _prepare_request_params(self, inputs: dict = None, **kwargs) -> RequestParams:
        """
        准备请求参数

        包括：
        - 创建请求参数对象
        - 注入请求ID和执行ID
        - 执行自定义鉴权钩子
        """
        inputs = inputs or {}
        request_params_creator = RequestParamsCreator(
            api_name=kwargs.get("name", ""),
            api_headers=self._auth_headers,
            api_input_params=self._tool_params,
            api_url=self._server_path,
            api_auth=self._auth,
            api_error_handler=self._raise_error,
            ignore_default_not_exit=False,
            api_cert=self._cert,
            plugin_dependency=self._plugin_dependency,
        )
        request_params = request_params_creator.create(inputs, **kwargs)

        request_params.headers[X_REQUEST_ID] = get_x_request_id()
        request_params.headers[X_EXECUTION_ID] = get_x_execution_id()

        self._replace_mcp_headers_extra(request_params, **kwargs)

        self._execute_auth_hook(request_params, kwargs.get("name"))

        #  同构：MCP 出站剥 auth_keys 的 cust- 前缀 + captured 覆盖（auth_hook 后、出站前）
        from jiuwen.extension.wrapper.customer_header_inject import inject_customer_headers_to_mcp
        inject_customer_headers_to_mcp(request_params)

        return request_params

    def _build_mcp_url(self, request_params: RequestParams) -> str:
        """构建MCP请求URL"""
        tmp_url = copy.copy(request_params.ip_address_url)
        if request_params.query_params_in_inputs.items():
            if "?" in tmp_url:
                tmp_url = (
                    f"{tmp_url}&{urlencode(request_params.query_params_in_inputs)}"
                )
            else:
                tmp_url = (
                    f"{tmp_url}?{urlencode(request_params.query_params_in_inputs)}"
                )
        logger.info(f"MCP Request url {tmp_url}")
        return tmp_url

    def _execute_auth_hook(self, request_params: RequestParams, name: str):
        """执行认证钩子函数"""
        hook_function = self._plugin_dependency.get("hook_function", {}).get("mcp_auth")
        if not hook_function:
            return

        auth_provider = None
        try:
            auth_provider = ApiUtils.get_hook_func(hook_function)
        except Exception as e:
            logger.error(f"根据路径{hook_function}获取函数失败")
            logger.error(e)

        if not auth_provider:
            return

        try:
            auth_provider(
                self._auth,
                request_params.headers,
                request_params.query_params_in_inputs,
                name,
            )
        except Exception as e:
            logger.error(f"执行函数{hook_function}失败")
            logger.error(e)

    def _replace_mcp_headers_extra(self, request_params: RequestParams, **kwargs):
        """
        动态替换 headers 中的变量引用

        支持在 MCP 请求头中使用变量引用语法 {{inputs.xxx}}
        从 runtime_context 中获取全局变量进行替换

        Args:
            request_params: 请求参数对象
            **kwargs: 包含 runtime_context 的参数（通过 jiuwen_kwargs 传入）
        """
        headers = request_params.headers
        updates = {}

        input_parameters = self._input_parameters

        runtime_context = kwargs.get("runtime_context")
        if runtime_context and hasattr(runtime_context, "agent_workflow_context"):
            from jiuwen.controller.common.constants import WorkflowConstants

            agent_workflow_context = runtime_context.get("agent_workflow_context", {})
            req_params = agent_workflow_context.get(
                WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
            )
            updates = req_params.get("global_variables", {})

        if not input_parameters:
            return

        for key, value in input_parameters.items():
            if not isinstance(value, str):
                continue
            if len(value) > 4 and value.startswith("{{") and value.endswith("}}"):
                inner = value[2:-2].strip()
                if inner.startswith("inputs.") and len(inner) > 7:
                    path_in_inputs = inner[7:]
                    actual_value = updates.get(path_in_inputs, "")
                    if (
                        actual_value is not None
                        and actual_value != ""
                        and key in headers
                    ):
                        headers[key] = actual_value

    async def list_tools(self, *, timeout: float = NO_TIMEOUT) -> List[Any]:
        """
        获取工具列表

        每次调用新建 client/session，执行完毕后自动释放
        """
        request_params = self._prepare_request_params(inputs={}, name=self._name)
        tmp_url = self._build_mcp_url(request_params)

        try:
            async with sse_client(
                tmp_url,
                headers=request_params.headers,
                sse_read_timeout=mcp_time_out_seconds,
                timeout=mcp_time_out_seconds,
            ) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return self._process_tools_result(result)
        except ExceptionGroup as eg:
            eg_str = exception_group_to_str_simple(eg)
            logger.warning(f"get mcp tools list error, {eg_str}")
            return []
        except Exception:
            logger.warning("get mcp tools list error, please check mcp server.")
            return []

    def _process_tools_result(self, result) -> List[McpToolCard]:
        """处理工具列表结果，支持 mcp_choose_tools 过滤"""
        tools_list = []
        tools = result.tools if result else []

        if self._mcp_choose_tools is not None:
            tools = [t for t in tools if t.name in self._mcp_choose_tools]

        for tool in tools:
            input_schema = getattr(tool, "inputSchema", {})
            if not isinstance(input_schema, dict):
                input_schema = {}
            injected_schema = dict(input_schema)
            if "properties" not in injected_schema:
                injected_schema["type"] = "object"
                injected_schema["properties"] = {}
            injected_schema["properties"][JIUWEN_RUNTIME_KWARGS] = {
                "type": "object",
                "description": "jiuwen runtime kwargs",
            }

            tools_list.append(
                McpToolCard(
                    name=tool.name,
                    server_name=self._name,
                    description=getattr(tool, "description", ""),
                    input_params=injected_schema,
                    properties={
                        "headers": self._auth_headers,
                        "auth": self._auth,
                        "plugin_dependency": self._plugin_dependency,
                        "params": self._tool_params,
                        "input_parameters": self._input_parameters,
                    },
                )
            )

        logger.info(f"Retrieved {len(tools_list)} tools from SSE server")
        return tools_list

    async def call_tool(
        self, tool_name: str, arguments: dict, *, timeout: float = NO_TIMEOUT
    ) -> Any:
        """
        调用工具

        每次调用新建 client/session，执行完毕后自动释放
        """
        jiuwen_kwargs = arguments.pop(JIUWEN_RUNTIME_KWARGS, {}) or {}

        request_params = self._prepare_request_params(
            arguments, name=tool_name, **jiuwen_kwargs
        )
        tmp_url = self._build_mcp_url(request_params)

        logger.info(f"Calling tool '{tool_name}' via SSE with arguments: {arguments}")

        async with sse_client(
            tmp_url,
            headers=request_params.headers,
            sse_read_timeout=mcp_time_out_seconds,
            timeout=mcp_time_out_seconds,
        ) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                content = self._transform_result(result)
                logger.info(f"Tool '{tool_name}' call completed via SSE")
                return content

    async def get_tool_info(
        self, tool_name: str, *, timeout: float = NO_TIMEOUT
    ) -> Optional[Any]:
        tools = await self.list_tools(timeout=timeout)
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None

    def _transform_result(self, result: Any) -> Any:
        """转换结果（支持 structuredContent）"""
        if hasattr(result, "structuredContent") and result.structuredContent:
            return result.structuredContent
        if hasattr(result, "content") and result.content:
            return result.content
        return result

    def _raise_error(self, err_msg: str):
        """错误处理"""
        err_msg = f"{err_msg}. server_name is {self._name}"
        logger.error(err_msg)
        raise exception.PluginRestfulAuthException(message=err_msg)

    async def close(self) -> bool:
        return await self.disconnect()
