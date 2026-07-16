# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from agent_builder.nl_to_agent.base import OperatorInput
from agent_builder.nl_to_agent.llm_agent.utils import (
    call_model,
    format_dialogue_history,
    FINAL_MSG,
    CACHE_TOKEN,
)

from .prompt import update_designer_system_prompt, PREFIX_WAIT


class AgentDesigner:
    def __init__(self, llm, controller):
        self.controller = controller
        self.model = llm

    def llm_design(self, uml_prompts: list):
        """设计Agent初始提示词"""
        response = call_model(self.model, uml_prompts)
        messages = ""
        flag = True
        first_token = True
        result = {}
        for chunk_message in response:
            if chunk_message:
                messages += chunk_message
                if messages.startswith("["):
                    if flag and PREFIX_WAIT in messages:
                        flag = False
                        result[CACHE_TOKEN] = "agent设计中.."
                        yield result
                    if flag and len(messages) > 10:
                        if first_token:
                            cache_token = messages.split("]")[-1]
                            result[CACHE_TOKEN] = cache_token
                        else:
                            result[CACHE_TOKEN] = chunk_message
                        first_token = False
                        yield result
                else:
                    result[CACHE_TOKEN] = chunk_message
                    yield result
        result[CACHE_TOKEN] = "\n"
        yield result
        result[FINAL_MSG] = messages
        yield result

    def run(self, inputs: OperatorInput):
        """designer 运行函数"""
        dialogue_history = self.controller.context_manager.get_filtered_messages(
            self.controller.task_id, "分类3"
        )
        # 更新系统提示词
        system_prompt = {
            "role": "system",
            "content": update_designer_system_prompt(
                inputs.plugin_info, inputs.knowledge_info, inputs.sub_workflow_info
            ),
        }
        formatted_dialogue_history = format_dialogue_history(dialogue_history)
        user_prompt = {
            "role": "user",
            "content": f"请根据历史对话信息设计Agent提示词: {str(formatted_dialogue_history)}",
        }
        designer_prompt = [system_prompt, user_prompt]
        response = self.llm_design(designer_prompt)
        for item in response:
            if FINAL_MSG in item:
                self.controller.design_llm(item[FINAL_MSG])
            else:
                yield item[CACHE_TOKEN]

    async def arun(self, inputs: OperatorInput):
        """designer 运行函数"""
        dialogue_history = self.controller.context_manager.get_filtered_messages(
            self.controller.task_id, "分类3"
        )
        # 更新系统提示词
        system_prompt = {
            "role": "system",
            "content": update_designer_system_prompt(
                inputs.plugin_info, inputs.knowledge_info, inputs.sub_workflow_info
            ),
        }
        formatted_dialogue_history = format_dialogue_history(dialogue_history)
        user_prompt = {
            "role": "user",
            "content": f"请根据历史对话信息设计Agent提示词: {str(formatted_dialogue_history)}",
        }
        designer_prompt = [system_prompt, user_prompt]
        response = self.llm_design(designer_prompt)
        for item in response:
            if FINAL_MSG in item:
                await self.controller.async_design_llm(item[FINAL_MSG])
            else:
                yield item[CACHE_TOKEN]
