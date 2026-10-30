#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import ast
import json
import time
from typing import Dict, Any, AsyncGenerator, Union, List

from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.types import ValueTypeEnum
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
)
from jiuwen.controller.utils.utils import MessageConverter
from jiuwen.planner.common.plan_constants import TimerInfo
from jiuwen.plugin.models.restfulapi import RestFulAPI

NON_EXIST_FUNC = "大模型生成不存在的工具，无法执行"


class PluginHandler(BaseHandler):
    """插件处理器"""

    def __init__(self, context_manager: ContextManager):
        super().__init__(context_manager)
        self.plugins = None

    async def execute_plugin_from_function_call(self, function_call, plugin, **kwargs):
        """execute function from function call"""
        self._merge_plugin_arguments(function_call, plugin)
        tool_name = function_call.get("name")
        tool_arguments = function_call.get("arguments")
        if tool_name == "python_interpreter":
            tool_arguments_dict = json.loads(tool_arguments)
            tool_arguments = json.dumps(tool_arguments_dict, ensure_ascii=False)
        start_time = time.time()
        if tool_name == plugin.name or plugin.name.startswith(tool_name + "#*"):
            # planner tool_call 标识经 ainvoke kwargs 透传给插件侧 tracer，
            # 供 OTel 双写盖 gen_ai.tool.call.id / gen_ai.tool.type
            plugin_res = await plugin.ainvoke(
                inputs=json.loads(tool_arguments),
                tool_call_id=function_call.get("tool_call_id", ""),
                tool_type="plugin",
                **kwargs,
            )
            function_exec_res = self.function_filter(plugin, plugin_res)
            exec_latency = round(time.time() - start_time, 2)  # 工具执行耗时
            return function_exec_res, exec_latency
        return dict(errCode=-1, errMessage=NON_EXIST_FUNC), 0.0

    def function_filter(self, plugin, invocation_result: dict):
        """过滤visible为false的出参"""
        data = invocation_result.get("data")
        if not data:
            return invocation_result
        if plugin is not None and isinstance(plugin, RestFulAPI):
            self._function_filter_for_schema(plugin.response, invocation_result["data"])
        return invocation_result

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
            final_result = (
                output
                if isinstance(output, str)
                else json.dumps(output, ensure_ascii=False)
            )
            self.context_manager.add_function_message(
                name=function_call.get(NAME),
                intent=function_call.get(NAME),
                content=final_result,
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
        self.plugins = kwargs.get("plugins", [])

        if task.task_type == TaskType.PLUGIN_START:
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
        self.plugins = kwargs.get("plugins", [])

        if task.task_type == TaskType.PLUGIN_START:
            async for stream_res in self._stream_handle_plugin_start(task):
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

    async def _stream_handle_plugin_start(
        self, task: Task
    ) -> AsyncGenerator[Union[Dict, str, Message], None]:
        """流式处理调用插件

        Args:
            task: 任务对象

        Yields:
            流式处理结果
        """
        plugin = task.input_data.get("plugin")
        plugin_name = task.input_data.get("plugin_name")
        function_call = task.input_data.get("function_call", {})
        runtime_data = task.input_data.get("runtime_data", {})
        time_dict = task.input_data.get("time_dict", {})
        async for plugin_exec_result in self._exec_plugin(
            plugin_name, plugin, function_call, time_dict, **runtime_data
        ):
            yield plugin_exec_result

    async def _exec_plugin(
        self, plugin_name, plugin, function_call, time_dict, **kwargs
    ):
        args = function_call.get("arguments", "{}")
        check_result, trans_result = ModelUtil.check_and_trans2json(args)
        args = trans_result if check_result else ast.literal_eval(args)
        function_call["arguments"] = json.dumps(args, ensure_ascii=False)
        exec_result, exec_latency = await self.execute_plugin_from_function_call(
            function_call, plugin, **kwargs
        )
        for wrapped_result in self.stream_wrap_result(
            plugin_name, function_call, exec_result, exec_latency, time_dict
        ):
            yield wrapped_result
        yield MessageConverter.create_plugin_completion_message(
            plugin_name=plugin_name, exec_res=exec_result, runtime_data=kwargs
        )

    def _handle_plugin_start(self, task) -> Message:
        pass

    def _collect_leaves(self, params: List, prefix: str = "") -> List[tuple]:
        """递归收集所有叶子节点的 (full_path, param)"""
        leaves = []
        for param in params:
            full_path = f"{prefix}.{param.name}" if prefix else param.name
            schema = getattr(param, "schema", None)
            param_type = param.type
            # 判断是否为 object：有 schema, 且type正确
            is_object = (
                param_type in ["object", "Object", "obj", "Obj", "map", "Map"]
                and schema
            )
            if is_object and isinstance(schema, list) and len(schema) > 0:
                # 非叶子，递归
                leaves.extend(self._collect_leaves(schema, full_path))
            else:
                # 叶子节点
                leaves.append((full_path, param))
        return leaves

    def _merge_plugin_arguments(self, function_call: Dict[str, Any], plugin) -> None:
        # 1. 解析当前 arguments（可能为空或部分）
        try:
            current_args = json.loads(function_call["arguments"])
            if not isinstance(current_args, dict):
                current_args = {}
        except (json.JSONDecodeError, TypeError):
            current_args = {}

        # 2. 获取上下文
        agent_inputs = self.context_manager.get_global_variables("agent_inputs") or {}
        memory_variables = (
            self.context_manager.get_global_variables("memory_variables") or {}
        )
        input_parameters = getattr(plugin, "input_parameters", {}) or {}

        # 3. 收集所有叶子路径
        leaf_nodes = self._collect_leaves(plugin.params)

        # 4. 从 current_args 开始构建结果
        result = current_args.copy()

        # 5. 为每个叶子节点填充值
        self._form_merged_arguments(
            agent_inputs, input_parameters, leaf_nodes, memory_variables, result
        )

        # 6. 序列化回 function_call
        function_call["arguments"] = json.dumps(result, ensure_ascii=False)

    def _form_merged_arguments(
        self, agent_inputs, input_parameters, leaf_nodes, memory_variables, result
    ):
        """获取融合后的参数"""
        for full_path, _ in leaf_nodes:
            # 检查是否已存在（且非空字符串）
            existing = self._get_nested_value(result, full_path)
            if existing is not None and not (
                isinstance(existing, str) and existing == ""
            ):
                continue  # 已提供，跳过

            value = None
            # 仅当 input_parameters 显式声明了该叶子路径时，才从上下文取值
            if full_path in input_parameters:
                template = input_parameters[full_path].strip()
                if template.startswith("{{") and template.endswith("}}"):
                    inner = template[2:-2].strip()
                    if inner.startswith("inputs.") and len(inner) > 7:
                        path_in_inputs = inner[7:]
                        value = self._get_nested_value(agent_inputs, path_in_inputs)
                    elif inner.startswith("memory.") and len(inner) > 7:
                        path_in_memory = inner[7:]
                        value = self._get_nested_value(memory_variables, path_in_memory)

            # 如果没取到（或 input_parameters 没声明）
            if value is None:
                continue

            # 写入 result
            self._set_nested_value(result, full_path, value)
