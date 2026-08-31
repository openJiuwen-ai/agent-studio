#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import copy
import os
import time
from typing import List, Union

from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.messages import BaseMessage
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.controller.common.message import Message
from jiuwen.controller.context_manager.context_manager import ContextManager
from jiuwen.controller.task_planner.planning_modules.prompt_module import ChatContent
from jiuwen.controller.utils.utils import ToolFormatter
from jiuwen.planner.common import OpType
from jiuwen.planner.common.exception import LLMInvocationFailedException
from jiuwen.planner.common.stream_post_utils import (
    create_trace_manager,
    _process_time_info_by_llm_output,
    LATENCY,
    MODEL_STAT,
    _format_yield_result,
    MODEL_USAGE,
)
from jiuwen.planner.planning_modules.base import PromptPlanningModule
from jiuwen.plugin.models.function import Function
from jiuwen.plugin.models.plugin import BasePlugin
from jiuwen.plugin.models.restfulapi import RestFulAPI
from jiuwen.prompt import TemplateManager

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class LLMModule:
    """
    Planning llm module class
    """

    def __init__(self, plan_config, llm, context_manager: ContextManager):
        self.llm = llm
        self.context_manager = context_manager
        self.plan_config = plan_config
        self.op_type = OpType.ProposeNext
        self.op_config = getattr(plan_config, f"{self.op_type.value}_config", None)

    @staticmethod
    async def _format_yield_from_llm_output(result, llm_output: dict):
        """处理大模型输出"""
        async for item in result:
            if (
                isinstance(item, dict) and "llm_output" in item
            ):  # 大模型的最终输出，不需要流式输出
                llm_output.update(item.get("llm_output"))
            else:
                yield item

    @staticmethod
    def _filter_visible_parameters(workflow_info: dict) -> dict:
        # Step 1: 找出 arguments 中 visible 为 False 的参数名
        invisible_names = {
            arg["name"]
            for arg in workflow_info.get("arguments", [])
            if arg.get("visible") is False
        }

        # Step 2: 过滤 properties，移除 invisible 的项
        properties = workflow_info.get("parameters", {}).get("properties", {})
        filtered_properties = {}
        required_params = []

        for key, value in properties.items():
            if key not in invisible_names:
                # 复制 property 但删除其中的 required 字段（required 只在顶层）
                property_value = {k: v for k, v in value.items() if k != "required"}
                filtered_properties[key] = property_value
                # 如果参数标记为 required，添加到 required 列表
                if value.get("required", False):
                    required_params.append(key)

        # Step 3: 构建新的 parameters（保留原有 parameters 中除 properties 外的其他字段）
        new_parameters = {
            **workflow_info.get("parameters", {}),
            "properties": filtered_properties,
        }
        # 添加required字段
        new_parameters["required"] = required_params

        # Step 4: 构建最终结果：复制原 workflow_info，更新 parameters，并删除 arguments
        new_workflow_info = {**workflow_info, "parameters": new_parameters}
        # 显式删除 arguments
        new_workflow_info.pop("arguments", None)

        return new_workflow_info

    @staticmethod
    def _resolve_variable_references(
        template: str, agent_inputs: dict, memory_vars: dict
    ) -> str:
        """
        解析模板中的变量引用
        - {{inputs.xxx}} 或 {{inputs.xxx.yyy}} → 从 agent_inputs 获取值（支持嵌套）
        - {{memory.xxx}} 或 {{memory.xxx.yyy}} → 从 memory_vars 获取值（支持嵌套）
        若路径不存在，则保留原始占位符
        """
        import re

        def get_nested_value(data: dict, path: str):
            """安全获取嵌套字典的值，路径如 'a.b.c'；若任一节点缺失，返回 None"""
            if not isinstance(data, dict):
                return None
            keys = path.split(".")
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value

        def replace_inputs(match):
            path = match.group(1)  # e.g., "school.age"
            value = get_nested_value(agent_inputs, path)
            if value is not None:
                return str(value)
            return "none"

        def replace_memory(match):
            path = match.group(1)  # e.g., "user.profile.name"
            value = get_nested_value(memory_vars, path)
            if value is not None:
                return str(value)
            return "none"

        # 替换 inputs.*（支持嵌套）
        template = re.sub(r"\{\{inputs\.([\w.]+)\}\}", replace_inputs, template)

        # 替换 memory.*（现在也支持嵌套）
        template = re.sub(r"\{\{memory\.([\w.]+)\}\}", replace_memory, template)

        return template

    def format_tools(
        self, plugins: List[Union[Function, BasePlugin, RestFulAPI]] = None, mcps=None
    ):
        """
        格式化插件和工作流工具为标准接口格式

        遵循 OpenAI Function Calling 规范

        Args:
            plugins: 插件列表，可以是Function或BasePlugin对象的列表
            mcps: MCP 工具列表

        Returns:
            list: 格式化后的工具列表
        """
        # 使用公共的 ToolFormatter 格式化工具
        workflow_contexts = getattr(self.context_manager, "workflow_contexts", None)
        return ToolFormatter.format_tools(
            plugins=plugins, mcps=mcps, workflow_contexts=workflow_contexts
        )

    async def stream(self, message: Message):
        """
        stream output calling result

        Args:
            :param message:
        """
        plugins = message.runtime_data.get("plugins")
        mcps = message.runtime_data.get("mcps")
        prompt = await self.create_llm_input(message.runtime_data)
        formatted_functions = self.format_tools(plugins, mcps)

        llm_output_dict = dict()
        logger.info(
            f"\n<LLM Input>: {prompt}",
            simple_log="\n<LLM Input>: get prompt successfully",
        )
        res = self.stream_function_call(
            prompt, formatted_functions, message.runtime_data
        )
        async for output in self._format_yield_from_llm_output(res, llm_output_dict):
            yield output

        logger.info(
            f"LLM Response: Received {llm_output_dict}",
            simple_log="LLM Response: Received llm_output_dict successfully",
        )
        content = llm_output_dict.get("content")
        function_call = llm_output_dict.get("function_call")
        function_call_list = llm_output_dict.get("function_call_list", list())
        intent = self.context_manager.get_latest_intent()
        if function_call_list:
            logger.info(
                f"In ReAct, LLM generated function call list = {function_call_list}",
                simple_log="In ReAct, LLM generated function call list successfully",
            )
            intent_list = [item.get("name", "") for item in function_call_list]
            self.context_manager.add_assistant_message_with_multi_function_call(
                content, intent_list, function_call_list
            )
        else:
            if function_call and function_call.get("name"):
                intent = function_call.get("name")
                self.context_manager.add_assistant_message(
                    content, intent, function_call
                )
            else:
                self.context_manager.add_assistant_message(content, intent)

    def invoke(self, message: Message):
        """
        forward

        Args:
            :param message:
        """
        pass

    async def create_llm_input(self, runtime_data):
        """生成大模型输入"""
        prompt_info = runtime_data.get("prompt_info")
        # 从 ContextManager 获取变量
        agent_inputs = self.context_manager.get_global_variables("agent_inputs", {})
        memory_vars = self.context_manager.get_global_variables("memory_variables", {})
        template_manager = TemplateManager()
        template = template_manager.get(self.op_config.prompt_template_name)
        # 解析并替换变量引用
        processed_template = self._resolve_variable_references(
            template.content[0].get("content"), agent_inputs, memory_vars
        )
        prompt_engine = PromptPlanningModule()
        prompt = prompt_engine.format(
            prompt_template=[ChatContent(role="system", content=processed_template)],
            keywords=prompt_info,
        )

        if self.plan_config.plan_mode == "ReAct":
            prompt[-1]["content"] = prompt[-1].get("content", "") + add_time_info()
        prompt.extend(
            self.context_manager.get_latest_k_chat_history(
                self.op_config.reserved_max_chat_rounds
            )
        )
        # 处理文件，多模态场景需要转成文本和图片混合message
        if hasattr(self.llm, "vl_enable") and self.llm.vl_enable:
            for i, prompt_item in enumerate(prompt):
                if "files" in prompt_item:
                    mix_content = [{"type": "text", "text": prompt_item["content"]}]
                    mix_content.extend(
                        file
                        for file in prompt_item["files"]
                        if file.get("type") == "image_url"
                    )
                    prompt[i]["content"] = mix_content
                    prompt[i].pop("files")
        # user variable memory
        user_variable_str = await self.context_manager.get_memory_variables()
        if user_variable_str.strip():
            prompt.append(dict(role="user", content=user_variable_str))
        # user Profile memory
        memory_message = await self.context_manager.get_memory_message(
            self.context_manager.get_latest_user_content()
        )
        if isinstance(memory_message, BaseMessage):
            prompt.append(
                dict(role=memory_message.type, content=memory_message.content)
            )
        return prompt

    async def stream_function_call(
        self, messages: List[dict], functions, runtime_data: dict
    ):
        """Get llm stream output with functions"""
        trace_manager = create_trace_manager(
            self.llm, functions, runtime_data.get("trace_handlers")
        )
        await trace_manager.on_llm_start(messages)

        llm_output, time_dict, model_stat, model_usage = dict(), dict(), dict(), dict()
        try:
            result = self.llm.astream(
                LanguageModelInput(
                    messages=ModelUtil.switch_message(messages), tools=functions
                )
            )
            async for item in _format_yield_result(
                result,
                llm_output,
                time_dict,
                model_stat,
                model_usage,
                self._is_thinking_enabled(),
            ):
                yield item
        except Exception as e:
            await trace_manager.on_llm_error(e)
            # 始终透传真实原因：friendly_message 对 ModelServiceError 取 .msg 剥 [code] 前缀，
            # 其余异常保留 str(e)。避免非 verbose 模式吞成 "Failed to stream calling LLM"
            # 让用户无法定位（占位符未解析等）。
            from model_service.env_resolver import friendly_message
            raise LLMInvocationFailedException(friendly_message(e)) from e
        for output in _process_time_info_by_llm_output(llm_output, time_dict):
            yield output

        # display output on insights, including timer info
        output_on_insights: dict = copy.deepcopy(llm_output)
        output_on_insights.update({LATENCY: time_dict})
        output_on_insights.update({MODEL_STAT: model_stat})
        output_on_insights.update({MODEL_USAGE: model_usage})
        await trace_manager.on_llm_end(output_on_insights)

    def _is_thinking_enabled(self) -> bool:
        """检查是否开启了思考模式"""
        thinking_config = getattr(self.llm, "thinking", None)
        if (
            isinstance(thinking_config, dict)
            and thinking_config.get("type") == "enabled"
        ):
            return True
        return False


def add_time_info(language="zh"):
    """当前日期信息"""
    local_time = time.localtime()
    week_index = local_time.tm_wday
    form_time1 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    if language == "zh":
        week_list = [
            "星期一",
            "星期二",
            "星期三",
            "星期四",
            "星期五",
            "星期六",
            "星期日",
        ]
        week_str = week_list[week_index]
        addstr = "\n 今天日期：" + form_time1 + "，" + week_str + "。\n"
    else:
        week_list = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        week_str = week_list[week_index]
        addstr = "\n Current date and time: " + form_time1 + "," + week_str + "\n"
    return addstr
