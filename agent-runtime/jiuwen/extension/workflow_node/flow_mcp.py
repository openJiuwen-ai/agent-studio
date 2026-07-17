#  Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowMcp - MCP 调用组件

迁移自商用版本 jiuwen/orchestration/flow/components/flow_mcp.py，
适配开源版本 openjiuwen 框架。

设计说明:
- 继承 WorkflowComponent（openjiuwen 标准组件基类）
- 直接实例化 Client（SSEClientNew/StreamableHttpClientNew）+ MCPTool，不注册到 ResourceMgr
- 新版本（有 arguments）：从 arguments 生成 input_params schema，跳过 list_tools
- 旧版本（无 arguments）：通过 list_tools 从 MCP Server 获取 card（含完整 inputSchema）
- 从 session 提取 runtime_auth，通过 JIUWEN_RUNTIME_KWARGS 机制传递到 SSE 底层
"""

import asyncio
from builtins import ExceptionGroup
from enum import Enum

from jiuwen.common.exception.status_code import StatusCode
from jiuwen.extension.workflow_node.utils import JiuWenBaseException, get_workflow_param
from jiuwen.extension.wrapper.mcp_server_loader import convert_ir_to_server_config
from jiuwen.extension.wrapper.mcp_tool_wrapper import JIUWEN_RUNTIME_KWARGS
from jiuwen.extension.wrapper.sse_client_new import SSEClientNew
from jiuwen.extension.wrapper.streamable_http_client_new import StreamableHttpClientNew
from jiuwen.plugin.common import constant
from jiuwen.plugin.common.utils.ir_utils import MCP_PARAM_LOCATIONS
from jiuwen.plugin.models.api_utils import transform_type
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.tool import MCPTool
from openjiuwen.core.foundation.tool.mcp.base import McpServerConfig, McpToolCard
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent

USER_FIELDS = "userFields"

TAG = " === FLOW_MCP === "


class FlowMcpStatusCode(Enum):
    """FlowMcp 组件专用错误码"""

    WORKFLOW_MCP_UNSUPPORTED_TYPE_ERROR = (101870, "Unsupported mcp type: {mcp_type}.")
    WORKFLOW_MCP_FIELD_EMPTY_TYPE_ERROR = (
        101872,
        "Field {field} should not be empty in {mcp_type}.",
    )
    WORKFLOW_MCP_EXECUTE_ERROR = (101873, "Mcp execute error, reason is {error}.")
    WORKFLOW_MCP_PARAM_METHOD_ERROR = (
        101874,
        "Unsupported mcp param method: {method}.",
    )
    WORKFLOW_MCP_PARAM_TYPE_ERROR = (
        101875,
        "Invalid mcp argument param type for {param}, expect type is {type}.",
    )
    WORKFLOW_MCP_INPUTS_ERROR = (101876, "FlowMcp inputs error, param is {param}")
    WORKFLOW_MCP_OUTPUTS_TYPE_ERROR = (101877, "FlowMcp outputs type error: {msg}")


def _build_flow_mcp_error(
    status: FlowMcpStatusCode,
    **kwargs,
) -> JiuWenBaseException:
    """构建 FlowMcp 组件异常

    Args:
        status: 错误状态码枚举
        **kwargs: 消息格式化参数

    Returns:
        JiuWenBaseException 实例
    """
    return JiuWenBaseException(
        error_code=status.value[0],
        message=status.value[1].format(**kwargs),
    )


def _create_mcp_client(config: McpServerConfig):
    """根据 client_type 创建对应的 MCP Client 实例"""
    client_type = config.client_type
    if client_type in ("sse", "sse_new"):
        return SSEClientNew(config)
    elif client_type in ("streamable_http", "streamable_http_new"):
        return StreamableHttpClientNew(config)
    else:
        raise _build_flow_mcp_error(
            FlowMcpStatusCode.WORKFLOW_MCP_UNSUPPORTED_TYPE_ERROR,
            mcp_type=client_type,
        )


class FlowMcp(WorkflowComponent):
    """MCP 调用组件

    封装 MCP Server 的工具调用过程。

    Args:
        conf: 组件配置字典
    """

    def __init__(self, conf: dict = None):
        super().__init__()
        self._conf: dict = {}
        self._client = None
        self.api: MCPTool = None
        self._is_older_version: bool = False
        self._header_params: dict = {}
        self._init_lock: asyncio.Lock = asyncio.Lock()
        if conf:
            self.init(conf)

    def init(self, conf: dict, **kwargs):
        """初始化组件配置

        Args:
            conf: 组件配置字典
            **kwargs: 可选参数
        """
        self._validate_configs(conf)
        self.runtime_context = kwargs.get("runtime_context")
        self._conf = conf
        self._is_older_version = not conf.get("arguments")
        self._create_client(conf)

    def extends_headers(self, headers: dict):
        """
        headers扩展, 不能删除，为ei特殊实现
        """
        return headers

    def _create_client(self, conf: dict):
        """同步创建 client（不连接，不获取工具列表）"""
        mcp_type = conf.get("type", "")
        if mcp_type not in ("sse", "streamable_http"):
            return

        config = convert_ir_to_server_config(conf)
        config.auth_headers = self.extends_headers(config.auth_headers)
        self._client = _create_mcp_client(config)

        tool_params = getattr(self._client, "_tool_params", None)
        if tool_params:
            for param in tool_params:
                if param.method not in MCP_PARAM_LOCATIONS:
                    raise _build_flow_mcp_error(
                        FlowMcpStatusCode.WORKFLOW_MCP_PARAM_METHOD_ERROR,
                        method=param.method,
                    )
                if not isinstance(param.required, bool):
                    if not isinstance(param.required, str) or str.lower(
                        param.required
                    ) not in ["true", "false"]:
                        raise _build_flow_mcp_error(
                            FlowMcpStatusCode.WORKFLOW_MCP_PARAM_TYPE_ERROR,
                            param="required",
                            type="bool",
                        )

    async def _init_api(self):
        """延迟异步初始化：构建 MCPTool

        旧版本（无 arguments）：通过 list_tools 从 MCP Server 获取 card（含完整 inputSchema）。
        新版本（有 arguments）：直接从 arguments 生成 input_params，跳过 list_tools。
        """
        if not self._client:
            return

        tool_name = self._conf.get("tool_name")
        server_name = self._conf.get("name", "")

        if self._is_older_version:
            matched_card = await self._fetch_card_from_server(tool_name, server_name)
        else:
            matched_card = McpToolCard(
                name=tool_name,
                server_name=server_name,
                description=self._conf.get("description", ""),
                input_params=self._build_input_params_from_arguments(),
            )

        self.api = MCPTool(mcp_client=self._client, tool_info=matched_card)

    async def _fetch_card_from_server(
        self, tool_name: str, server_name: str
    ) -> McpToolCard:
        """通过 list_tools 从 MCP Server 获取匹配的 McpToolCard"""
        tool_cards = await self._client.list_tools()
        for card in tool_cards:
            if card.name == tool_name:
                return card

        return McpToolCard(
            name=tool_name,
            server_name=server_name,
            description=self._conf.get("description", ""),
            input_params=None,
        )

    def _build_input_params_from_arguments(self) -> dict:
        """从 arguments（_tool_params）构建 input_params JSON Schema

        注意：只包含 method != Headers 的参数，method=Headers 的参数会被放到 HTTP 请求头
        """
        tool_params = getattr(self._client, "_tool_params", [])
        properties = {}
        required = []
        for param in tool_params:
            if param.method == "Headers":
                # method=Headers 的参数不加入 call_tool 的 arguments
                continue
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
                "default": param.default_value,
            }
            if param.required:
                required.append(param.name)
        properties[JIUWEN_RUNTIME_KWARGS] = {"type": "object"}

        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": True,
        }
        if required:
            schema["required"] = required
        return schema

    def _format_runtime_auth(self, session: Session) -> dict:
        """从 session 中提取 runtime_auth headers（参考 flow_api）"""
        all_headers = get_workflow_param(session, "runtime_auth_headers") or {}
        tool_name = self._conf.get("tool_name", "")
        return all_headers.get(tool_name) or all_headers.get("default", {})

    def _get_runtime_context_header(self, session: Session):
        """从 session 中提取 runtime_context（兼容旧版鉴权 fallback）

        _add_auth_params 在找不到 runtime_auth 时，
        会尝试 runtime_context.api_config 作为 fallback。
        """
        if session is None:
            return None
        return get_workflow_param(session, "api_config")

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """异步调用 MCP Server 工具

        Args:
            inputs: 输入数据，格式: {"userFields": {...}}
            session: 工作流会话
            context: 模型上下文

        Returns:
            Output: 输出数据，格式: {"userFields": {...}}
        """
        if not self._client:
            return {
                USER_FIELDS: {
                    "content": "not contain mcp api, not run",
                    "isError": False,
                }
            }

        if self.api is None:
            # 加锁防止并发 invoke 重复初始化 MCPTool（旧版路径会 await list_tools，
            # 让出协程期间其他协程可能同时进入 _init_api）
            async with self._init_lock:
                if self.api is None:
                    await self._init_api()

        inputs_data = inputs.get(USER_FIELDS, {})
        if not self._is_older_version:
            api_inputs = self._format_api_inputs(inputs_data)
        else:
            api_inputs = inputs_data

        # 从 session 提取运行时鉴权参数，注入到 inputs 中传递到底层
        # 兼容 runtime_auth（新版）和 runtime_context（旧版 fallback）
        jiuwen_kwargs = {}
        runtime_auth = self._format_runtime_auth(session)
        if runtime_auth:
            jiuwen_kwargs["runtime_auth"] = {"headers": runtime_auth}
        runtime_context_header = self._get_runtime_context_header(session)
        if runtime_context_header:
            jiuwen_kwargs["runtime_context"] = runtime_context_header

        # 合并 header_params 到 runtime_auth headers
        header_params = getattr(self, "_header_params", {})
        if header_params:
            if "runtime_auth" not in jiuwen_kwargs:
                jiuwen_kwargs["runtime_auth"] = {"headers": {}}
            jiuwen_kwargs["runtime_auth"]["headers"].update(header_params)

        if jiuwen_kwargs:
            api_inputs = dict(api_inputs)
            api_inputs[JIUWEN_RUNTIME_KWARGS] = jiuwen_kwargs

        try:
            result = await self.api.invoke(api_inputs)
            api_outputs = self._convert_mcp_result(result)
        except BaseError as tool_error:
            raise self._create_error_response(tool_error.cause)

        outputs = self._format_api_outputs(api_outputs)
        return {USER_FIELDS: outputs}

    def _format_api_inputs(self, inputs: dict) -> dict:
        """格式化 API 输入参数（基于 client._tool_params 的类型转换）

        注意：method=Headers 的参数会被提取到 _header_params，不作为 call_tool 的 arguments
        """
        tool_params = getattr(self._client, "_tool_params", None)
        api_params_dict = {param.name: param for param in tool_params}
        api_inputs = {}
        header_params = {}
        for name, value in inputs.items():
            param = api_params_dict.get(name)
            if param:
                if param.method == "Headers":
                    # method=Headers 的参数应该放到 HTTP 请求头
                    header_params[name] = transform_type(value, param.type, name)
                else:
                    api_inputs[name] = transform_type(value, param.type, name)
            else:
                workflow_logger.error(
                    f"{TAG} _format_api_inputs error: param not found",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="FlowMcp",
                    metadata={"param_name": name},
                )
                raise _build_flow_mcp_error(
                    FlowMcpStatusCode.WORKFLOW_MCP_INPUTS_ERROR,
                    param=name,
                )
        # 保存 header_params 到实例变量，供后续 invoke 使用
        self._header_params = header_params
        return api_inputs

    def _format_api_outputs(self, outputs: dict) -> dict:
        """格式化 MCP 输出结果

        对齐原版 orchestration flow_mcp 的 _format_api_outputs 逻辑，
        统一处理 errCode/errMessage/data 格式。
        """
        error_code = outputs.get(
            constant.ERR_CODE, StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code
        )
        if error_code != StatusCode.SUCCESS.code:
            error_msg = outputs.get(
                constant.ERR_MESSAGE,
                "plugin execution error, and no error information is specified",
            )
            if isinstance(error_code, int) and (
                error_code < 105000 or error_code > 105999
            ):
                error_msg = f"plugin flow execute inner failed, errCode={error_code}, errMessage={type(error_msg)}"
                error_code = StatusCode.WORKFLOW_API_EXECUTE_ERROR.code
            raise JiuWenBaseException(error_code=error_code, message=error_msg)

        output_data = outputs.get(constant.RESTFUL_DATA, [])
        if output_data is None:
            response_data = []
        elif isinstance(output_data, list):
            response_data = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in output_data
            ]
        elif isinstance(output_data, dict):
            return output_data
        else:
            raise _build_flow_mcp_error(
                FlowMcpStatusCode.WORKFLOW_MCP_OUTPUTS_TYPE_ERROR,
                msg=(
                    f"Expected list if 'content' field of CallToolResult is passed, "
                    f"or expected dict if 'structuredContent' field of CallToolResult is passed, "
                    f"got type: {type(output_data)}"
                ),
            )
        return {"content": response_data, "isError": False}

    def _convert_mcp_result(self, result: dict) -> dict:
        """将 MCPTool 返回格式转换为 McpAPI 返回格式

        MCPTool 返回: {"result": xxx}
        McpAPI 返回: {"errCode": 0, "errMessage": "success", "data": xxx}
        """
        data = result.get("result")
        return {
            constant.ERR_CODE: 0,
            constant.ERR_MESSAGE: "success",
            constant.RESTFUL_DATA: data,
        }

    def _create_error_response(self, error: Exception) -> JiuWenBaseException:
        """创建错误响应"""
        if isinstance(error, ExceptionGroup):
            error_type = "ExceptionGroup"
        else:
            error_type = "Exception"
        return JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code,
            message=StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.errmsg.format(
                error=error_type
            ),
        )

    def _validate_configs(self, config):
        """验证 MCP 配置"""
        mcp_type = config.get("type", "")
        if mcp_type not in ["sse", "streamable_http", "stdio"]:
            raise _build_flow_mcp_error(
                FlowMcpStatusCode.WORKFLOW_MCP_UNSUPPORTED_TYPE_ERROR,
                mcp_type=mcp_type,
            )
        if mcp_type in ["sse", "streamable_http"]:
            if "url" not in config or "tool_name" not in config:
                raise _build_flow_mcp_error(
                    FlowMcpStatusCode.WORKFLOW_MCP_FIELD_EMPTY_TYPE_ERROR,
                    field="url or tool_name",
                    mcp_type=mcp_type,
                )
