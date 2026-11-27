#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import ast
import json
import time
from typing import Dict, Any, AsyncGenerator, Union

from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.types import ValueTypeEnum
from jiuwen.controller.common.constants import FUNCTION_ROLE
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.common.task import Task
from jiuwen.controller.common.task_type import TaskType
from jiuwen.controller.context_manager.context_manager import ContextManager
from jiuwen.controller.task_executor import BaseHandler
from jiuwen.controller.task_executor.constants import (
    NAME,
    RESPONSE_EMPTY_RESULT,
    LATENCY,
    NON_EXIST_FUNC,
)
from jiuwen.controller.utils.utils import MessageConverter
from jiuwen.planner.common.plan_constants import TimerInfo
from mcp.types import TextContent


class McpHandler(BaseHandler):
    """插件处理器"""

    def __init__(self, context_manager: ContextManager):
        super().__init__(context_manager)
        self.mcps = None

    async def execute_mcp_from_function_call(self, function_call, mcp, **kwargs):
        """execute function from function call"""
        tool_name = function_call.get("name")
        tool_arguments = function_call.get("arguments")
        start_time = time.time()
        if tool_name == mcp.name:
            kwargs_new = kwargs.copy()
            # planner tool_call 标识经 ainvoke kwargs 透传给 MCP 侧 tracer，
            # 供 OTel 双写盖 gen_ai.tool.call.id / gen_ai.tool.type
            function_exec_res = await mcp.ainvoke(
                inputs=json.loads(tool_arguments),
                tool_id=mcp.tool_id,
                agent_id=mcp.agent_id,
                session_id=mcp.session_id,
                tool_call_id=function_call.get("tool_call_id", ""),
                tool_type="mcp",
                **kwargs_new,
            )
            exec_latency = round(time.time() - start_time, 2)  # 工具执行耗时
            return function_exec_res, exec_latency
        return dict(errCode=-1, errMessage=NON_EXIST_FUNC), 0.0

    def stream_wrap_result(
        self, plugin_name, function_call, result, exec_latency, time_dict
    ):
        """处理流式结果"""
        if isinstance(result, dict):
            error_code = result.get("errCode")
            error_message = result.get("errMessage")
        else:
            error_code = (
                result.err_code
                if result is not None and hasattr(result, "err_code")
                else -1
            )
            error_message = (
                result.err_msg
                if result is not None and hasattr(result, "err_msg")
                else "工具执行异常"
            )

        if error_code != 0:
            output = error_message
            self.context_manager.add_function_message(
                name=function_call.get(NAME),
                intent=function_call.get(NAME),
                content="工具执行失败",
                role=FUNCTION_ROLE,
                tool_call_id=function_call.get("tool_call_id", ""),
            )
        else:
            output = result.get("data")

        exec_result = dict(error_code=error_code, result=output, latency=exec_latency)
        yield {
            "function_call": function_call,
            "time_consumption": TimerInfo(**time_dict),
            "is_workflow": False,
        }
        yield {
            "plugin_name": plugin_name,
            "function_name": function_call.get(NAME),
            "result": exec_result,
            "latency": exec_result.get(LATENCY),
        }
        if error_code == 0:
            output = RESPONSE_EMPTY_RESULT if not (output or output == []) else output
            if isinstance(output, str):
                final_result = output
            elif (
                isinstance(output, list)
                and len(output) > 0
                and isinstance(output[0], TextContent)
            ):
                final_result = json.dumps([r.text for r in output], ensure_ascii=False)
            else:
                final_result = json.dumps(output, ensure_ascii=False)
            self.context_manager.add_function_message(
                name=function_call.get(NAME),
                intent=function_call.get(NAME),
                content=final_result,
                role=FUNCTION_ROLE,
                tool_call_id=function_call.get("tool_call_id", ""),
            )

    def handle(self, task: Task, context: Dict[str, Any], **kwargs) -> Message:
        """非流式处理插件相关任务

        Args:
            task: 任务对象
            context: 当前上下文
            **kwargs: 额外参数，包含plugins

        Returns:
            Message: 处理结果消息
        """
        # 从kwargs中获取plugins
        self.mcps = kwargs.get("mcps", [])

        if task.task_type == TaskType.MCP_START:
            return self._handle_plugin_start(task)
        raise ValueError(f"不支持的任务类型: {task.task_type}")

    async def astream_handle(
        self, task: Task, **kwargs
    ) -> AsyncGenerator[Union[Dict, str, Message], None]:
        """流式处理插件相关任务

        Args:
            task: 任务对象
            **kwargs: 额外参数，包含plugins

        Yields:
            流式处理结果，可以是字典、字符串或消息对象
        """
        # 从kwargs中获取plugins
        self.mcps = kwargs.get("mcps", [])

        if task.task_type == TaskType.MCP_START:
            async for stream_res in self._stream_handle_mcp_start(task):
                yield stream_res
        else:
            error_msg = f"不支持的任务类型: {task.task_type}"
            yield {"type": "error", "content": error_msg}
            yield Message(
                message_type=MessageType.ERROR,
                content=error_msg,
                runtime_data={"task_id": task.id, "error": error_msg},
            )

    def _function_filter_for_schema(self, output_params: list, data: dict):
        """基于schema过滤参数"""
        for output_param in output_params:
            if not output_param.visible and output_param.name in data:
                del data[output_param.name]
            elif (
                ValueTypeEnum.is_object(output_param.type) and output_param.name in data
            ):
                self._function_filter_for_schema(
                    output_param.schema, data[output_param.name]
                )

    async def _stream_handle_mcp_start(
        self, task: Task
    ) -> AsyncGenerator[Union[Dict, str, Message], None]:
        """流式处理调用MCP

        Args:
            task: 任务对象

        Yields:
            流式处理结果
        """
        mcp = task.input_data.get("mcp")
        mcp_name = task.input_data.get("mcp_name")
        function_call = task.input_data.get("function_call")
        runtime_data = task.input_data.get("runtime_data")
        time_dict = task.input_data.get("time_dict")
        async for mcp_exec_res in self._exec_mcp(
            mcp_name, mcp, function_call, time_dict, **runtime_data
        ):
            yield mcp_exec_res

    async def _exec_mcp(self, mcp_name, mcp, function_call, time_dict, **kwargs):
        args = function_call.get("arguments", "{}")
        check_result, trans_result = ModelUtil.check_and_trans2json(args)
        args = trans_result if check_result else ast.literal_eval(args)
        function_call["arguments"] = json.dumps(args, ensure_ascii=False)
        exec_result, exec_latency = await self.execute_mcp_from_function_call(
            function_call, mcp, **kwargs
        )
        for wrapped_result in self.stream_wrap_result(
            mcp_name, function_call, exec_result, exec_latency, time_dict
        ):
            yield wrapped_result
        yield MessageConverter.create_mcp_completion_message(
            mcp_name=mcp_name, exec_res=exec_result, runtime_data=kwargs
        )

    def _handle_plugin_start(self, task) -> Message:
        pass
