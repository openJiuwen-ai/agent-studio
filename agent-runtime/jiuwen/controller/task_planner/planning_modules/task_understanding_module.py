#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
任务理解模块

职责：
- 判断用户请求是简单意图还是复杂意图
"""

import re
from dataclasses import dataclass
from typing import List, Dict

from jiuwen.common.llm_service.messages import HumanMessage, SystemMessage
from jiuwen.common.log.base import logger
from jiuwen.prompt.template.template_manager import TemplateManager


@dataclass
class TaskUnderstandingOutput:
    """任务理解输出"""

    is_complex: bool


class TaskUnderstandingModule:
    """
    任务理解模块

    使用 LLM 判断用户请求是否为复杂意图
    """

    def __init__(self, llm, context_manager):
        """
        初始化任务理解模块

        Args:
            llm: 语言模型实例
            context_manager: 上下文管理器
        """
        self.llm = llm
        self.context_manager = context_manager
        self.template_manager = TemplateManager()

    @staticmethod
    def _parse_is_complex(output_text: str) -> bool:
        """
        解析 LLM 输出，返回是否复杂意图

        Args:
            output_text: LLM 输出的文本内容

        Returns:
            bool: 如果输出包含 "1" 则返回 True（复杂意图），否则返回 False
        """
        match = re.search(r"[01]", output_text)
        if not match:
            return False
        return match.group(0) == "1"

    async def invoke(
        self,
        query: str,
        chat_history: List[Dict],
        available_intents: List[str],
        task_id: str = "",
    ) -> TaskUnderstandingOutput:
        """
        判断用户请求是否为复杂意图

        Args:
            query: 用户查询
            chat_history: 对话历史
            available_intents: 可用意图名称列表
            task_id: 任务ID，用于日志追踪

        Returns:
            TaskUnderstandingOutput(is_complex: bool)
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query, chat_history, available_intents)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        llm_input = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        }
        logger.info(
            f"task_id: {task_id}| [TaskUnderstanding] <LLM Input> {llm_input}",
            simple_log=f"task_id: {task_id}| [TaskUnderstanding] <LLM Input>",
        )

        try:
            result = await self.llm.ainvoke(messages)
            output_text = (result.content or "").strip()
            logger.info(
                f"task_id: {task_id}| [TaskUnderstanding] <LLM Output> {output_text}",
                simple_log=f"task_id: {task_id}| [TaskUnderstanding] <LLM Output>",
            )
        except Exception as e:
            logger.error(
                f"task_id: {task_id}| Task understanding llm error: {e}",
                simple_log=f"task_id: {task_id}| Task understanding llm error",
            )
            return TaskUnderstandingOutput(is_complex=False)

        is_complex = self._parse_is_complex(output_text)
        logger.info(
            f"task_id: {task_id}| Task understanding result: is_complex={is_complex}",
            simple_log=f"task_id: {task_id}| Task understanding result",
        )
        return TaskUnderstandingOutput(is_complex=is_complex)

    def _build_system_prompt(self) -> str:
        template = self.template_manager.get("task_understanding")
        if template is None:
            # 默认系统提示词
            return """你是一个任务理解助手，负责判断用户的请求是简单意图还是复杂意图。
简单意图：可以通过单一操作完成，如查询余额、查看账单等。
复杂意图：需要多个步骤才能完成，如信用卡还款（需要查账单、查余额、可能转账、再还款）。

请分析用户请求，如果是复杂意图返回1，简单意图返回0。只返回数字，不要其他解释。"""
        for msg in template.content:
            if msg.get("role") == "system":
                return msg.get("content", "")
        return ""

    def _build_user_prompt(
        self, query: str, chat_history: List[Dict], available_intents: List[str]
    ) -> str:
        template = self.template_manager.get("task_understanding")
        user_prompt_template = ""
        if template is None:
            # 默认用户提示词模板
            user_prompt_template = """可用的简单意图: {{available_intents}}
对话历史:
{{chat_history}}
用户当前请求: {{query}}

请判断用户请求是复杂意图(1)还是简单意图(0)，只返回数字。"""
        else:
            for msg in template.content:
                if msg.get("role") == "user":
                    user_prompt_template = msg.get("content", "")
                    break

        history_text = ""
        if chat_history:
            for msg in chat_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n"

        intents_text = "\n".join(available_intents) if available_intents else ""

        user_prompt = user_prompt_template.replace(
            "{{available_intents}}", intents_text
        )
        user_prompt = user_prompt.replace("{{chat_history}}", history_text)
        user_prompt = user_prompt.replace("{{query}}", query)
        return user_prompt
