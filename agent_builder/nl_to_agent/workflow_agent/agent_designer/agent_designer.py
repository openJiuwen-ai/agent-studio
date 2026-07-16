# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
from agent_builder.nl_to_agent.base import BaseOperator, OperatorInput
from agent_builder.nl_to_agent.workflow_agent.progress_bar import mermaid_msg
from agent_builder.adapter.jiuwen_bridge import HumanMessage, SystemMessage

from .post_process import clean_uml, extract_info
from .prompt import SYSTEM_PROMPT
from ..progress_bar import MERMAID

SUMMRY_CONTENT = "## 任务结果"
NAME_CONTENT = "中文名称："
NAME_EN_CONTENT = "英文名称："
DESCRIPTION_CONTENT = "描述："
RESPONSE_CONTENT = "工作流设计图如下，请您确认是否无误\n"


def update_prompt(inputs, jiuwen_info):
    """更新prompt"""
    prompt = SYSTEM_PROMPT
    if isinstance(inputs.plugin_info, (list, dict)):
        plugin_info = str(inputs.plugin_info)
    else:
        plugin_info = inputs.plugin_info
    for key, value in jiuwen_info.items():
        if key == "components":
            prompt = (
                prompt.replace("{{components_info}}", value)
                .replace("{{plugin_info}}", plugin_info or "")
                .replace("{{knowledge_info}}", inputs.knowledge_info or "")
                .replace("{{sub_workflow_info}}", inputs.sub_workflow_info or "")
            )
            break
    return prompt


class AgentDesigner(BaseOperator):
    def __init__(self, model, jiuwen_info, controller):
        super().__init__()
        self.model = model
        self.jiuwen_info = jiuwen_info
        self.controller = controller
        self.context_manager = controller.context_manager
        self.task_id = controller.task_id

    @staticmethod
    def post_process(full_response):
        """后处理"""
        info = extract_info(full_response)
        info["mermaid"] = clean_uml(info.get("mermaid"))
        response = (
            f"{NAME_CONTENT}{info.get('name')}\n"
            f"{NAME_EN_CONTENT}{info.get('name_en')}\n"
            f"{DESCRIPTION_CONTENT}{info.get('description')}\n"
            f"{RESPONSE_CONTENT}{info.get('mermaid')}"
        )
        return response

    @staticmethod
    def post_process_with_info(full_response):
        """后处理"""
        info = extract_info(full_response)
        info["mermaid"] = clean_uml(info.get("mermaid"))
        response = (
            f"{NAME_CONTENT}{info.get('name')}\n"
            f"{NAME_EN_CONTENT}{info.get('name_en')}\n"
            f"{DESCRIPTION_CONTENT}{info.get('description')}\n"
            f"{RESPONSE_CONTENT}{info.get('mermaid')}"
        )
        return response, info

    def invoke(self, inputs: OperatorInput):
        """执行agent design"""
        prompt = update_prompt(inputs, self.jiuwen_info)
        uml_prompts = [
            SystemMessage(content=prompt),
            HumanMessage(content=inputs.query),
        ]
        for item in self.model.chat(
            uml_prompts, method="stream", add_prefix=False, type="mermaid"
        ):
            if item.content:
                response = self.post_process(item.content)
                self.context_manager.add_assistant_message(
                    self.task_id, response, "分类1"
                )
                item.raw_content = response
                self.controller.refine_workflow()
                yield item
                yield inputs.query, "sop"

    async def ainvoke(self, inputs: OperatorInput):
        """执行agent design"""
        prompt = update_prompt(inputs, self.jiuwen_info)
        uml_prompts = [
            SystemMessage(content=prompt),
            HumanMessage(content=inputs.query),
        ]
        async for item in self.model.achat(
            uml_prompts, method="stream", add_prefix=False, type="mermaid"
        ):
            if item.content:
                response, info = self.post_process_with_info(
                    item.content
                )  # post_process_with_info 额外返回info消息
                self.context_manager.add_assistant_message(
                    self.task_id, response, "分类1"
                )
                await self.controller.async_refine_workflow()
                content = f"{SUMMRY_CONTENT}\n{response or ''}"
                yield mermaid_msg(content, MERMAID, info)
