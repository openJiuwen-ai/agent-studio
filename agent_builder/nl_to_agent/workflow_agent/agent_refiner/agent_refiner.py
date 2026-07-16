# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
from agent_builder.nl_to_agent.base import BaseOperator, OperatorInput
from agent_builder.nl_to_agent.workflow_agent.agent_designer.post_process import (
    clean_uml,
)
from agent_builder.nl_to_agent.workflow_agent.progress_bar import mermaid_msg, MERMAID
from agent_builder.adapter.jiuwen_bridge import HumanMessage, SystemMessage

from .prompt import REFINE_SYSTEM_PROMPT

RESPONSE_CONTENT = "工作流设计图如下，请您确认是否无误\n"


class AgentRefiner(BaseOperator):
    def __init__(self, model, input_adapter, controller):
        super().__init__()
        self.model = model
        self.input_adapter = input_adapter
        self.controller = controller
        self.context_manager = controller.context_manager
        self.task_id = controller.task_id

    @staticmethod
    def post_process(full_response):
        """后处理"""
        mermaid_code = full_response.split("@Mermaid流程：")[-1].strip()
        mermaid_code = clean_uml(mermaid_code)
        return mermaid_code

    def invoke(self, inputs: OperatorInput):
        """执行agent_refine"""
        inputs.plugin_info = self.controller.resource_config.get("plugin", "")
        components_info = self.input_adapter.detail_config.get("components")
        system_prompt = REFINE_SYSTEM_PROMPT.replace(
            "{{components_info}}", components_info
        )

        dialogue_history = self.context_manager.get_filtered_messages(
            session_id=self.task_id, intent="分类1"
        )
        sop_content = ""
        for tmp in dialogue_history:
            if "工作流SOP：" in tmp["content"] and tmp["role"] == "assistant":
                sop_content = tmp["content"].split("工作流SOP：")[-1].strip()
                break
        last_mermaid = dialogue_history[-2]["content"]
        workflow_name_desc, mermaid_code = last_mermaid.split(RESPONSE_CONTENT)
        user_prompt = (
            f"# 原始工作流创建指令：\n{sop_content}\n\n# 待修改Mermaid流程：\n{mermaid_code.strip()}\n\n"
            f"# 用户修改意见：{inputs.query}"
        )
        refine_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        # 流式调用模型
        for item in self.model.chat(
            refine_messages, method="stream", add_prefix=False, type="mermaid"
        ):
            if item.content:
                mermaid_code = self.post_process(item.content)
                response = f"{workflow_name_desc}{RESPONSE_CONTENT}{mermaid_code}"
                self.context_manager.add_assistant_message(
                    self.task_id, response, "分类1"
                )
                item.raw_content = f"{RESPONSE_CONTENT}{mermaid_code}"
                self.controller.refine_workflow()
                yield item

    async def ainvoke(self, inputs: OperatorInput):
        """执行agent_refine"""
        inputs.plugin_info = self.controller.resource_config.get("plugin", "")
        components_info = self.input_adapter.detail_config.get("components")
        system_prompt = REFINE_SYSTEM_PROMPT.replace(
            "{{components_info}}", components_info
        )

        dialogue_history = self.context_manager.get_filtered_messages(
            session_id=self.task_id, intent="分类1"
        )
        sop_content = ""
        for tmp in dialogue_history:
            if "工作流SOP：" in tmp["content"] and tmp["role"] == "assistant":
                sop_content = tmp["content"].split("工作流SOP：")[-1].strip()
                break
        last_mermaid = dialogue_history[-2]["content"]
        workflow_name_desc, mermaid_code = last_mermaid.split(RESPONSE_CONTENT)
        user_prompt = (
            f"# 原始工作流创建指令：\n{sop_content}\n\n# 待修改Mermaid流程：\n{mermaid_code.strip()}\n\n"
            f"# 用户修改意见：{inputs.query}"
        )
        refine_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        # 流式调用模型
        async for item in self.model.achat(
            refine_messages, method="stream", add_prefix=False, type="mermaid"
        ):
            if item.content:
                mermaid_code = self.post_process(item.content)
                response = f"{workflow_name_desc}{RESPONSE_CONTENT}{mermaid_code}"
                self.context_manager.add_assistant_message(
                    self.task_id, response, "分类1"
                )
                item.raw_content = f"{RESPONSE_CONTENT}{mermaid_code}"
                await self.controller.async_refine_workflow()
                info = {"mermaid": mermaid_code}
                yield mermaid_msg(item.raw_content, MERMAID, info)
