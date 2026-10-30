# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
MCP Tool 包装器

职责：
1. 从 ResourceMgr 获取 MCPTool
2. 转换返回格式: {"result"} -> {errCode, errMessage, data}
3. TraceManager 追踪
4. ExceptionGroup 处理
"""

from builtins import ExceptionGroup
from typing import Any, Dict, Optional

from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.insight.manager import TraceManager
from jiuwen.insight.utils import (
    extract_tool_trace_info,
    get_instance_info,
)
from jiuwen.plugin.common import constant
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.foundation.tool import MCPTool

JIUWEN_RUNTIME_KWARGS = "_jiuwen_runtime_kwargs"


def flatten_exception_group(eg) -> list:
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


def exception_group_to_str_simple(eg) -> str:
    """将所有异常转为字符串列表并合并"""
    return "\n".join(
        f"{type(e).__name__}: {str(e)}" for e in flatten_exception_group(eg)
    )


class McpToolWrapper:
    """
    MCP Tool 包装器

    从 Runner.resource_mgr.get_tool() 获取已注册的 MCPTool，
    适配旧版 McpAPI 的接口签名
    """

    def __init__(self, tool_id: str, agent_id: str, session_id: str):
        """
        初始化包装器

        Args:
            tool_id: 已注册到 ResourceMgr 的工具 ID
        """
        self._tool_id = tool_id
        self._agent_id = agent_id
        self._session_id = session_id
        self._tool: Optional[MCPTool] = None

    def _get_tool(self) -> MCPTool:
        """延迟获取 Tool 实例"""
        if self._tool is None:
            from openjiuwen.core.runner import Runner
            from openjiuwen.core.session.agent import create_agent_session

            session = create_agent_session(session_id=self._session_id)
            self._tool = Runner.resource_mgr.get_tool(
                self._tool_id, tag=self._agent_id, session=session
            )
            if self._tool is None:
                raise ValueError(f"MCP Tool not found: {self._tool_id}")
        return self._tool

    @property
    def name(self) -> str:
        return self._get_tool().card.name

    @property
    def description(self) -> str:
        return self._get_tool().card.description

    @property
    def server_name(self) -> str:
        return self._get_tool().card.server_name

    @property
    def parameters(self) -> dict:
        return self._get_tool().card.input_params

    @property
    def headers(self) -> dict:
        return self._get_tool().card.properties.get("headers", {})

    @property
    def auth(self) -> dict:
        return self._get_tool().card.properties.get("auth", {})

    @property
    def plugin_dependency(self) -> dict:
        return self._get_tool().card.properties.get("plugin_dependency", {})

    @property
    def params(self) -> list:
        return self._get_tool().card.properties.get("params", [])

    @property
    def input_parameters(self) -> dict:
        return self._get_tool().card.properties.get("input_parameters", {})

    @property
    def is_mcp(self) -> bool:
        return True

    def invoke(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """同步调用（不支持）"""
        logger.error("mcp tool not support invoke, please use ainvoke instead")

    async def ainvoke(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        异步调用主入口

        保持与旧版 McpAPI.ainvoke() 完全相同的行为
        """
        # 弹出须发生在调用方作用域：_create_tracer_manager(**kwargs) 的形参
        # 是副本，helper 内弹出不影响本方法 kwargs。tool_call_id/tool_type
        # 与 trace_handlers 同理摘出——不可序列化的 TraceManager 不得随
        # **kwargs 泄入 JIUWEN_RUNTIME_KWARGS 与 _get_tool().invoke 入参
        tool_trace_info = extract_tool_trace_info(kwargs)
        trace_handlers = kwargs.pop("trace_handlers", None)
        trace_manager = self._create_tracer_manager(
            tool_trace_info, trace_handlers=trace_handlers, **kwargs
        )

        try:
            await trace_manager.on_plugin_start(inputs)

            jiuwen_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k
                not in (
                    "skip_none_value",
                    "skip_inputs_validate",
                    "tool_call_id",
                    "tool_type",
                )
            }
            if jiuwen_kwargs:
                inputs = dict(inputs)
                inputs[JIUWEN_RUNTIME_KWARGS] = jiuwen_kwargs

            result = await self._get_tool().invoke(inputs, **kwargs)

            formatted_result = self._convert_result(result)

            await trace_manager.on_plugin_end(formatted_result)
            return formatted_result

        except BaseError as tool_error:
            await trace_manager.on_plugin_error(tool_error.cause)
            return self._create_error_response(tool_error.cause)
        except ExceptionGroup as eg:
            await trace_manager.on_plugin_error(eg)
            return self._create_error_response(eg)
        except Exception as e:
            await trace_manager.on_plugin_error(e)
            return self._create_error_response(e)

    def _convert_result(self, result: dict) -> dict:
        """
        转换返回格式

        MCPTool 返回: {"result": xxx}
        转换为: {"errCode": 0, "errMessage": "success", "data": xxx}
        """
        data = result.get("result")
        return {
            constant.ERR_CODE: 0,
            constant.ERR_MESSAGE: "success",
            constant.RESTFUL_DATA: data,
        }

    def _create_error_response(self, error: Exception) -> dict:
        """创建错误响应"""
        if isinstance(error, ExceptionGroup):
            error_type = "ExceptionGroup"
        else:
            error_type = "Exception"

        return {
            constant.ERR_CODE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.code,
            constant.ERR_MESSAGE: StatusCode.WORKFLOW_MCP_EXECUTE_ERROR.errmsg.format(
                error=error_type
            ),
            constant.RESTFUL_DATA: "",
        }

    def _create_tracer_manager(
        self, tool_trace_info=None, trace_handlers=None, **kwargs
    ):
        """创建追踪管理器"""
        instance_info = get_instance_info(self, blacklist=["auth", "headers"])
        # 工具标识与 handlers 均由调用方从自身 kwargs 摘出后显式传入：
        # 工具标识入扁平键供 core handler 盖 gen_ai.tool.call.id /
        # gen_ai.tool.type；handlers 形参化后不再从副本 kwargs 里 pop
        # （副本内 pop 不影响调用方，形参化后调用方无从漏传）
        if tool_trace_info:
            instance_info.update(tool_trace_info)
        return TraceManager.generate_manager(trace_handlers, instance_info)
