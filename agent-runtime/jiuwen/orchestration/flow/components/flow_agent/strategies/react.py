#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
from typing import AsyncIterator, Iterator

from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.context.history import ConversationHistory
from jiuwen.orchestration.flow.components.flow_agent.strategies.base import (
    AgentStrategy,
    AgentStrategyResult,
    AgentStrategyContext,
)
from jiuwen.orchestration.flow.components.util import filter_enable_history
from jiuwen.orchestration.flow.constant import WORKFLOW_API_CONFIGS
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.plugin import Param
from jiuwen.plugin.models.function import Function
from jiuwen.plugin.models.plugin import BasePlugin
from jiuwen.plugin.models.restfulapi import RestFulAPI
from jiuwen.prompt import Template, Prompt

DEFAULT_MAX_ITERATION = 10

MODEL_NAME = "modelName"
MODEL_TYPE = "modelType"
HYPER_PARA = "hyperParameters"
EXTENSION = "extension"

USER_FIELDS = "userFields"


class ReActStrategy(AgentStrategy):
    """ReAct策略实现"""

    def __init__(self):
        super().__init__()
        self.llm = None
        self.runtime_context = None

    @staticmethod
    def _get_prompt_instance_by_template(template) -> Prompt:
        return Prompt(template=Template(name="default", content=template))

    def init(self, conf: dict):
        """初始化ReAct策略"""
        self.runtime_context = RuntimeContext()
        self.llm = ModelFactory().get_model(
            model_type=conf.model_config.get(MODEL_TYPE),
            model_name=conf.model_config.get(MODEL_NAME),
            **conf.model_config.get(HYPER_PARA),
            **conf.model_config.get(EXTENSION),
        )

    def get_strategy_name(self) -> str:
        return "JiuWen_" + "ReAct"

    def invoke(self, context: AgentStrategyContext):
        pass

    async def ainvoke(
        self, context: AgentStrategyContext, **kwargs
    ) -> AgentStrategyResult:
        debug_info = dict(
            component_metadata=kwargs.get("component_metadata", {}),
            runtime_context=kwargs.get("runtime_context", {}),
            span=kwargs.get("span"),
        )
        messages = []
        final_output = dict()
        iteration = 0
        try:
            while iteration < context.max_iteration:
                llm_input = await self._prepare_llm_input(context, messages)

                llm_output = await self.llm.ainvoke(llm_input)
                if llm_output.tool_calls.name:
                    for plugin in context.plugins:
                        if plugin.name == llm_output.tool_calls.name:
                            inputs = llm_output.tool_calls.args
                            api_configs = self.runtime_context.get(WORKFLOW_API_CONFIGS)
                            result: dict = await plugin.ainvoke(
                                inputs=inputs,
                                span=debug_info.get("span"),
                                runtime_auth_headers=api_configs,
                            )
                            result_str = json.dumps(result)
                            messages.append(dict(role="function", content=result_str))
                else:
                    final_output = llm_output.content
                    break

                iteration += 1
            if not final_output:
                final_output = f"ReAct迭代次数超出最大限制：{context.max_iteration}次"
        except Exception as e:
            logger.error(
                f"ReAct strategy ainvoke failed: {str(e)}",
                exc_info=True,
                simple_log="ReAct strategy ainvoke failed",
            )
            raise JiuWenBaseException(
                message=StatusCode.AINVOKE_STRATEGY_ERROR.errmsg,
                error_code=StatusCode.AINVOKE_STRATEGY_ERROR.code,
            ) from e
        return {USER_FIELDS: {"output": final_output}}

    def stream(self, context: AgentStrategyContext) -> Iterator[str]:
        pass

    async def astream(self, context: AgentStrategyContext) -> AsyncIterator[str]:
        pass

    async def _get_model_input(
        self,
        inputs: dict,
        context: AgentStrategyContext,
        function: dict,
        formatted_tools: list,
    ) -> LanguageModelInput:
        """
        获取模型输入
        """
        # 将模型IR配置中的systemPrompt占位符替换为真实输入
        prompt_instance = self._get_prompt_instance_by_template(context.system_prompt)
        try:
            system_prompt = await prompt_instance.ainvoke(inputs)
        except JiuWenBaseException:
            raise
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.errmsg,
            ) from e

        # 根据IR中定义的模型输出格式获取对话历史列表
        final_prompt = self._get_final_prompt(context, system_prompt)
        if function:
            final_prompt.extend(function)
        return LanguageModelInput(
            messages=ModelUtil.switch_message(final_prompt), tools=formatted_tools
        )

    def _get_final_prompt(self, context: AgentStrategyContext, system_prompt: str):
        chat_history: ConversationHistory = context.chat_history
        if chat_history:
            chat_history = chat_history.get_conversation_history()
        else:
            chat_history = []
        history = filter_enable_history(chat_history)
        final_prompt = [dict(role="system", content=system_prompt)]
        final_prompt.extend(history)
        return final_prompt

    async def _prepare_llm_input(self, context: AgentStrategyContext, messages: list) -> dict:
        inputs = context.user_inputs.get(USER_FIELDS)

        formatted_tools = (
            [
                Param.format_functions(p)
                for p in context.plugins
                if isinstance(p, (Function, BasePlugin, RestFulAPI))
            ]
            if context.plugins
            else []
        )

        return await self._get_model_input(
            inputs=inputs,
            context=context,
            function=messages,
            formatted_tools=formatted_tools,
        )
