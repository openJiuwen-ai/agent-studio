# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
# N2L临时九问补丁，若jiuwen已更新该代码，则删除
from typing import Dict, List, Iterator, Optional

from agent_builder.common.llm_service.utils import convert_message_to_dict
from agent_builder.adapter.model_bridge import get_nl2_model
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.jiuwen_bridge import StatusCode
from agent_builder.adapter.jiuwen_bridge import AIMessage, UsageMetadata


class Nl2AgentProcessor:
    """自然语言到智能体处理器接口

    该接口定义了将自然语言输入转换为智能体响应的核心功能，
    支持流式输出和批量处理模式。
    """

    def __init__(self, model_info):
        self.model_info = model_info
        self._model = None

    async def _get_model(self):
        """Lazy-constructed model instance (async factory)."""
        if self._model is None:
            self._model = await get_nl2_model(self.model_info)
        return self._model

    def chat(
        self,
        messages: List[dict],
        extra_info: Optional[Dict] = None,
        model_info: Optional[object] = None,
        method: str = "stream",
        add_prefix: bool = False,
        **kwargs,
    ) -> Iterator[object]:
        """处理聊天对话并生成响应

        该方法接收对话历史和相关参数，通过大语言模型生成连贯的响应，
        支持流式输出和一次性完整输出两种模式。

        Args:
            messages: 对话消息列表，包含历史对话记录和当前用户输入。
                    每条消息应为字典格式，包含角色和内容等信息。
            extra_info: 额外的上下文信息字典，用于提供模型生成所需的补充数据。
            model_info: 模型配置信息对象，包含模型参数、版本等设置。
            method: 生成模式，可选 "stream"（流式）或 "complete"（完整）。
            add_prefix: 是否在响应前添加前缀标识。
            **kwargs: 其他可选参数，如使用类型标识等。

        Yields:
            AIMessage: AI响应消息对象，包含以下属性：
                - raw_content: 流式的单个响应内容
                - content: 在流式结束时包含完整内容
                - usage_metadata: 使用情况元数据，包含token统计等信息
        """
        pass

    async def achat(
        self,
        messages: List[dict],
        extra_info: Optional[Dict] = None,
        model_info: Optional[object] = None,
        method: str = "stream",
        add_prefix: bool = False,
        **kwargs,
    ) -> Iterator[object]:
        """处理聊天对话并生成响应

        该方法接收对话历史和相关参数，通过大语言模型生成连贯的响应，
        支持流式输出和一次性完整输出两种模式。

        Args:
            messages: 对话消息列表，包含历史对话记录和当前用户输入。
                    每条消息应为字典格式，包含角色和内容等信息。
            extra_info: 额外的上下文信息字典，用于提供模型生成所需的补充数据。
            model_info: 模型配置信息对象，包含模型参数、版本等设置。
            method: 生成模式，可选 "stream"（流式）或 "complete"（完整）。
            add_prefix: 是否在响应前添加前缀标识。
            **kwargs: 其他可选参数，如使用类型标识等。

        Yields:
            AIMessage: AI响应消息对象，包含以下属性：
                - raw_content: 流式的单个响应内容
                - content: 在流式结束时包含完整内容
                - usage_metadata: 使用情况元数据，包含token统计等信息
        """
        messages = [convert_message_to_dict(msg) for msg in messages]
        usage_metadata = UsageMetadata()
        usage_metadata.type = kwargs.get("type")
        complete_content = ""
        model = await self._get_model()
        async for chunk in model.stream(messages=messages):
            content = chunk.content if isinstance(chunk.content, str) else ""
            if content:
                complete_content += content
                yield AIMessage(
                    raw_content=content, content="", usage_metadata=usage_metadata
                )
        yield AIMessage(
            raw_content="", content=complete_content, usage_metadata=usage_metadata
        )
