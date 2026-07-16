# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
from enum import Enum

from agent_builder.nl_to_agent.base import BaseOperator, OperatorInput
from agent_builder.nl_to_agent.workflow_agent.progress_bar import (
    content_msg,
    result_msg,
    SOP_CHUNK,
    SOP,
)
from agent_builder.adapter.jiuwen_bridge import HumanMessage, SystemMessage

from .prompt import TRANSFORM_SYSTEM_PROMPT, GENERATE_SYSTEM_PROMPT

SOP_RESPONSE_CONTENT = "工作流SOP：\n"


class SopMode(Enum):
    TRANSFORM = "transform"
    GENERATE = "generate"


class SopGenerator(BaseOperator):
    def __init__(self, model, controller, mode: SopMode):
        super().__init__()
        self.model = model
        self.controller = controller
        self.context_manager = controller.context_manager
        self.task_id = controller.task_id
        self.mode = mode

    def invoke(self, inputs: OperatorInput):
        if self.mode == SopMode.TRANSFORM:
            sop_prompts = [
                SystemMessage(content=TRANSFORM_SYSTEM_PROMPT),
                HumanMessage(content=inputs.query),
            ]
        else:
            dialogue_history = self.context_manager.get_formatted_history(
                session_id=self.task_id, intent="分类1"
            )
            sop_prompts = [
                SystemMessage(content=GENERATE_SYSTEM_PROMPT),
                HumanMessage(content=dialogue_history),
            ]
        for item in self.model.chat(
            sop_prompts, method="stream", add_prefix=False, type="sop"
        ):
            if item.content:
                sop_content = item.content
                self.context_manager.add_assistant_message(
                    self.task_id, SOP_RESPONSE_CONTENT + sop_content, "分类1"
                )
                return sop_content
        return ""

    async def ainvoke(self, inputs: OperatorInput):
        if self.mode == SopMode.TRANSFORM:
            sop_prompts = [
                SystemMessage(content=TRANSFORM_SYSTEM_PROMPT),
                HumanMessage(content=inputs.query),
            ]
        else:
            dialogue_history = self.context_manager.get_formatted_history(
                session_id=self.task_id, intent="分类1"
            )
            sop_prompts = [
                SystemMessage(content=GENERATE_SYSTEM_PROMPT),
                HumanMessage(content=dialogue_history),
            ]
        async for item in self.model.achat(
            sop_prompts, method="stream", add_prefix=False, type="sop"
        ):
            yield content_msg(item.raw_content, SOP_CHUNK)  # 展示SOP流式信息到前端
            if item.content:
                sop_content = item.content
                self.context_manager.add_assistant_message(
                    self.task_id, SOP_RESPONSE_CONTENT + sop_content, "分类1"
                )
                yield result_msg(sop_content, SOP)
