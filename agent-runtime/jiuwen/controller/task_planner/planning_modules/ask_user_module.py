#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
import time

from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.controller.common.message import Message
from jiuwen.controller.context_manager.context_manager import ContextManager
from jiuwen.planner.common.exception import LLMInvocationFailedException
from jiuwen.planner.common.stream_post_utils import _format_yield_result

SYSTEM_PROMPT = """# 角色
你是一个小助手，你可以通过向用户提问题完成任务。

# 任务目标
{task}

# 输出格式
1. 如果需要向用户提问，直接返回你的问题。
2. 如果不需要询问，请以markdown格式返回一个json字典。
"""
LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class AskUserModule:
    """
    Planning llm module class
    """

    def __init__(self, llm, context_manager: ContextManager):
        self.llm = llm
        self.context_manager = context_manager
        self.system_prompt = None

    def set_task(self, task):
        """设置询问用户的任务内容"""
        self.system_prompt = SYSTEM_PROMPT.format(task=task)

    async def stream(self, message: Message = None):
        """
        stream output calling result

        Args:
            :param message:
        """
        if message:
            self.context_manager.add_user_message(message.content)
        messages = self.context_manager.get_latest_k_chat_history(10)
        messages.insert(0, dict(role="system", content=self.system_prompt))
        llm_output_dict = dict()
        logger.info(f"\n<LLM Input>: {messages}", simple_log="\n<LLM Input>: messages")
        try:
            result = self.llm.astream(
                LanguageModelInput(
                    messages=ModelUtil.switch_message(messages), tools=[]
                )
            )
            async for result in _format_yield_result(result, llm_output_dict, {}):
                yield result

        except Exception as e:
            from model_service.env_resolver import friendly_message
            raise LLMInvocationFailedException(
                friendly_message(e)
            ) from e

        logger.info(
            f"LLM Response: Received {llm_output_dict}",
            simple_log="LLM Response: Received llm_output_dict successfully",
        )
        content = llm_output_dict.get("content")
        self.context_manager.add_assistant_message(content)

    async def invoke(self, message: Message):
        """
        forward

        Args:
            :param message:
        """
        pass


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
