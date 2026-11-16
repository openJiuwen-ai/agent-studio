#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
"""
@Copyright: Copyright (C) 2023-2023 Huawei Inc
@Project:
@Author: jiuwen planner
@Date: 2023-10-18
@LastEditTime: 2023-10-18 17:03:17
@Description: Operator base class
"""

from abc import ABC, abstractmethod
from typing import List

from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.messages import AIMessage
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.planner.common.enum_class import ProviderType
from jiuwen.planner.common.exception import PromptFormatFail
from jiuwen.planner.common.stream_post_utils import (
    stream_function_call,
    convert_ai_message_to_llm_output,
    insert_contexts_before_user_query,
    create_trace_manager,
)
from jiuwen.plugin.models.param import Param
from jiuwen.plugin.models.tool import Tool
from jiuwen.prompt import (
    TemplateManager,
    PromptAssembler,
    Template,
    TemplateDuplicatedException,
    TemplateNotFoundException,
)


class ChatContent:
    """prompt engine chat content"""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class PlanningModuleBase(ABC):
    """
    Operator base class
    """

    def __init__(self, op_type, plan_config):
        self.op_type = op_type
        self.plan_config = plan_config
        self.op_config = getattr(plan_config, f"{self.op_type.value}_config", None)

    def __call__(self, **kwargs):
        return self.invoke(**kwargs)

    async def stream(self, **kwargs):
        """
        stream output calling result

        Args:
            kwargs (Any): Extra Parameters.
        """
        pass

    async def invoke(self, **kwargs):
        """
        forward

        Args:
            kwargs (Any): Extra Parameters.
        """
        pass


class PromptPlanningModule:
    """prompt engine sdk client"""

    def __init__(self):
        self.template_manager = TemplateManager()

    def format(
        self,
        keywords: dict,
        template_name: str = None,
        prompt_template: List[ChatContent] = None,
    ) -> List:
        """format prompt"""
        if template_name is not None:
            template = self.template_manager.get(name=template_name)
        else:
            if prompt_template is not None:
                content_list = [content.__dict__ for content in prompt_template]
                template = Template(name="", content=content_list)
            else:
                raise PromptFormatFail()
        assembler = PromptAssembler(template)
        input_keys = assembler.input_keys
        format_dict = {}
        for key in input_keys:
            if keywords and keywords.get(key) is not None:
                format_dict[key] = keywords.get(key)
        return assembler.assemble(**format_dict)

    def register_template(
        self, template_name: str, description: str, prompt_template: List[ChatContent]
    ) -> bool:
        """register prompt template"""
        content_list = [content.__dict__ for content in prompt_template]
        register_template_info = Template(name=template_name, content=content_list)
        try:
            return self.template_manager.register(register_template_info)
        except TemplateDuplicatedException:
            self.unregister_template(template_name)
            return self.template_manager.register(register_template_info)

    def unregister_template(self, template_name: str):
        """unregister prompt template"""
        try:
            return self.template_manager.delete(template_name)
        except TemplateNotFoundException:
            return False


class LlmPlanningModule(PlanningModuleBase, ABC):
    """
    Operator base class with LLM
    """

    def __init__(self, op_type, plan_config, model):
        super(LlmPlanningModule, self).__init__(op_type, plan_config)
        self.llm = model

    @staticmethod
    async def _format_yield_from_llm_output(result, llm_output: dict):
        async for item in result:
            if (
                isinstance(item, dict) and "llm_output" in item
            ):  # 大模型的最终输出，不需要流式输出
                llm_output.update(item.get("llm_output"))
            else:
                yield item

    @staticmethod
    async def _insights_llm_output(llm_message, llm_output, trace_manager):
        usage_metadata = llm_message.usage_metadata
        model_stat = dict()
        if usage_metadata is not None:
            model_stat = usage_metadata.model_stats
        await trace_manager.on_llm_end(
            dict(content=llm_output.content, model_stat=model_stat)
        )

    @staticmethod
    def format_tools(tools: List[Tool], **kwargs):
        """格式化tool invokable接口"""
        formatted_tools = []
        for tool in tools:
            if tool.provider_type.name == ProviderType.PLUGIN.name:
                formatted_tools.append(Param.format_functions(tool.invokable))
            elif tool.provider_type.name == ProviderType.WORKFLOW.name:
                formatted_tools.append(tool.parameters)
            elif tool.provider_type.name == ProviderType.MCP.name:
                formatted_tools.append(tool.parameters)
        return formatted_tools

    @abstractmethod
    def update_planning_state(self, **kwargs):
        """
        update planning state graph
        """
        pass

    def create_llm_input(self, **kwargs):
        """creat input for LLM"""
        prompt_info = kwargs.get("prompt_info")
        prompt_engine = PromptPlanningModule()
        prompt = prompt_engine.format(
            template_name=self.op_config.prompt_template_name, keywords=prompt_info
        )
        return prompt

    async def invoke(self, **kwargs):
        prompt = self.create_llm_input(**kwargs)
        if kwargs.get("contexts") is not None:
            prompt = insert_contexts_before_user_query(kwargs.get("contexts"), prompt)

        functions = kwargs.get("functions")
        functions = self.format_tools(functions, **kwargs) if functions else []
        trace_manager = create_trace_manager(
            self.llm, functions, kwargs.get("trace_handlers", None)
        )
        await trace_manager.on_llm_start(prompt)

        llm_message: AIMessage = await self.llm.ainvoke(
            LanguageModelInput(
                messages=ModelUtil.switch_message(prompt), tools=functions
            )
        )
        llm_output = convert_ai_message_to_llm_output(llm_message)
        logger.info("\n<LLM Response>:Received")
        updated_state = {
            "llm_output": llm_output.dict(exclude_defaults=True),
            "planning_state": kwargs.get("planning_state"),
        }
        await self._insights_llm_output(llm_message, llm_output, trace_manager)
        self.update_planning_state(**updated_state)

    async def stream(self, **kwargs):
        functions = kwargs.get("functions")
        prompt = self.create_llm_input(**kwargs)
        functions = self.format_tools(functions, **kwargs) if functions else []

        llm_output_dict = dict()
        res = await stream_function_call(
            prompt,
            functions,
            self.llm,
            contexts=kwargs.get("contexts"),
            trace_handlers=kwargs.get("trace_handlers", None),
            multimodal_image=kwargs.get("multimodal_image"),
            round_id=kwargs.get("round_id"),
            session_id=kwargs.get("session_id"),
        )
        async for output in self._format_yield_from_llm_output(res, llm_output_dict):
            yield output

        logger.info("LLM Response: Received")
        updated_state = {
            "llm_output": llm_output_dict,
            "planning_state": kwargs.get("planning_state"),
        }
        self.update_planning_state(**updated_state)
