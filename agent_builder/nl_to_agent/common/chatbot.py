#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
from agent_builder.nl_to_agent.base import BaseOperator, OperatorInput
from agent_builder.nl_to_agent.workflow_agent.progress_bar import (
    CHITCHAT,
    CHITCHAT_CHUNK,
    content_msg,
    result_msg,
)
from agent_builder.adapter.jiuwen_bridge import HumanMessage, SystemMessage


class ChatBot(BaseOperator):
    """基于大语言模型的聊天机器人。

    该类继承自 BaseOperator，用于处理用户输入并生成对应的助手响应。
    内部维护系统提示词和上下文管理器，用于管理对话历史。

    Attributes:
        model: 大语言模型实例，用于生成聊天回复。
        context_manager (ContextManager): 对话上下文管理器，记录历史消息。
        task_id (str): 当前任务的标识符。
        system_prompt (str): 系统角色提示词，用于引导模型行为。
    """

    def __init__(self, model, context_manager, task_id="task_id"):
        """初始化 ChatBot 实例。

        Args:
            model: 大语言模型实例。
            context_manager (ContextManager): 对话上下文管理器。
            task_id (str, optional): 当前任务标识符，默认为 'task_id'。
        """
        super().__init__()
        self.model = model
        self.task_id = task_id
        self.context_manager = context_manager
        self.system_prompt = "你是一个助手"

    def invoke(self, inputs: OperatorInput):
        """执行聊天操作。

        根据输入的用户 query，调用大语言模型生成响应，并将助手消息
        添加到上下文管理器中。

        Args:
            inputs (OperatorInput): 包含用户输入 query 的数据对象。

        Yields:
            生成器对象：在流式调用模式下逐条返回模型输出。
        """
        for item in self.model.chat(
            [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=inputs.query),
            ],
            method="stream",
            add_prefix=False,
            type="message",
        ):
            if item.content:
                self.context_manager.add_assistant_message(
                    self.task_id, item.content, "分类2"
                )
            else:
                yield item

    async def ainvoke(self, inputs: OperatorInput):
        """执行聊天操作。

        根据输入的用户 query，调用大语言模型生成响应，并将助手消息
        添加到上下文管理器中。

        Args:
            inputs (OperatorInput): 包含用户输入 query 的数据对象。

        Yields:
            生成器对象：在流式调用模式下逐条返回模型输出。
        """
        async for item in self.model.achat(
            [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=inputs.query),
            ],
            method="stream",
            add_prefix=False,
            type="message",
        ):
            if item.content:
                yield result_msg(item.content, CHITCHAT)
                self.context_manager.add_assistant_message(
                    self.task_id, item.content, "分类2"
                )
            else:
                yield content_msg(item.raw_content, CHITCHAT_CHUNK)
