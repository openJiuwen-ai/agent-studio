#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""超长上下文压缩处理器（issue #1475）

在现有 ContextEngine 处理管道（ProcessorFactory / AsyncContextProcessor /
ContextHandler.UPDATE_COMPRESSED_HISTORY）基础上落地"分层压缩 + 智能摘要 +
可配置策略"：

- 分层压缩：历史被切为三层——锚点层（首条用户消息，任务目标原样保留）、
  压缩层（中间历史，被摘要或截断）、保护层（最近 keep_recent_turns 轮对话
  原样保留）。切分保证保留层不以孤立 function 消息开头，避免工具消息无法
  溯源。
- 智能摘要：压缩层由 LLM 生成信息密集的摘要；模型缺失、超时或失败时自动
  回退为截断，压缩过程永不阻塞对话。
- 可配置策略：触发阈值（token 估算）、保留轮数、策略（summarize/truncate）、
  摘要 prompt、摘要超时均可通过 IR context 配置（见 ContextConfig）。

压缩产物为单条 assistant 消息（带 [对话历史压缩摘要] 前缀），并合并压缩层
的全部 intent，保证按 intent 过滤历史的消费方不丢失语义入口。
"""

import asyncio
import json
import math
import re
from typing import List, Optional, Tuple

from jiuwen.common.log.base import logger
from jiuwen.context.base import (
    ContextConstant,
    ContextHandleType,
    ContextWindow,
)
from jiuwen.context.history import ConversationMessage
from jiuwen.context.processor.base import (
    AsyncContextProcessor,
    BaseAsyncProcessorConfig,
)
from jiuwen.context.processor.factory import ProcessorFactory
from jiuwen.controller.common.constants import FUNCTION_ROLE
from pydantic import Field

COMPRESSOR_PROCESSOR_TYPE = "compressor"
SUMMARY_STRATEGY = "summarize"
TRUNCATE_STRATEGY = "truncate"

DEFAULT_KEEP_RECENT_TURNS = 5
DEFAULT_SUMMARY_TIMEOUT_SECONDS = 60.0

SUMMARY_MESSAGE_PREFIX = "[对话历史压缩摘要]"

DEFAULT_SUMMARY_PROMPT = (
    "你是对话历史压缩器。请将下面的对话历史压缩为一段简洁、信息密度高的"
    "摘要，用于替代原始历史继续对话。摘要必须保留：\n"
    "1. 用户的任务目标与关键约束；\n"
    "2. 已得出的重要结论与决策；\n"
    "3. 关键工具/函数调用及其结果要点（名称、关键参数、结论）；\n"
    "4. 尚未解决的问题或待办事项。\n"
    "直接输出摘要正文，不要任何前后缀说明。\n\n"
    "【待压缩的对话历史】\n{history}"
)

_ASCII_PATTERN = re.compile(r"[\x00-\x7f]")


def estimate_text_tokens(text: str) -> int:
    """依赖无关的保守 token 估算。

    ASCII 文本约 4 字符/token，非 ASCII（中日韩）约 1.5 字符/token；
    估算偏高时只会提前触发压缩，不会漏触发。
    """
    if not text:
        return 0
    ascii_len = len(_ASCII_PATTERN.findall(text))
    non_ascii_len = len(text) - ascii_len
    return math.ceil(ascii_len / 4.0 + non_ascii_len / 1.5)


def estimate_message_tokens(message: ConversationMessage) -> int:
    """估算单条消息的 token 数（content + function_call + name）。"""
    total = estimate_text_tokens(getattr(message, "content", None) or "")
    function_call = getattr(message, "function_call", None)
    if function_call:
        try:
            total += estimate_text_tokens(
                json.dumps(function_call, ensure_ascii=False, default=str)
            )
        except (TypeError, ValueError):
            total += 64
    name = getattr(message, "name", None)
    if name:
        total += estimate_text_tokens(str(name))
    return total


def estimate_history_tokens(messages: List[ConversationMessage]) -> int:
    """估算整个历史窗口的 token 数。"""
    return sum(estimate_message_tokens(message) for message in messages or [])


def split_compress_boundary(
    messages: List[ConversationMessage], keep_recent_turns: int
) -> Tuple[int, int]:
    """计算分层边界，返回 (anchor_end, boundary)。

    - anchor_end：锚点层结束位置。首条消息为 user 时保留整条（任务目标），
      否则锚点层为空（0）。
    - boundary：压缩层结束位置（即保护层起始位置）。保护层为最近
      keep_recent_turns 轮对话（1 轮 = 1 条 user 消息及其后继非 user 消息，
      与 ConversationHistory.get_messages_by_turn 语义一致）。若保护层以
      孤立 function 消息开头，这些消息划入压缩层（boundary 后移），避免
      保留层出现无法溯源的工具消息。

    当 boundary <= anchor_end 时表示没有可压缩的中间层。
    """
    if not messages:
        return 0, 0

    anchor_end = 1 if messages[0].role == "user" else 0

    start = 0
    user_count = 0
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == "user":
            user_count += 1
            if user_count == keep_recent_turns:
                start = index
                break
    if user_count < keep_recent_turns:
        start = 0

    boundary = start
    while boundary < len(messages) and messages[boundary].role == FUNCTION_ROLE:
        boundary += 1

    return anchor_end, boundary


def format_messages_for_summary(messages: List[ConversationMessage]) -> str:
    """将压缩层消息格式化为摘要 prompt 的对话转录文本。"""
    lines = []
    for message in messages or []:
        role = getattr(message, "role", "") or ""
        content = getattr(message, "content", None) or ""
        name = getattr(message, "name", None)
        function_call = getattr(message, "function_call", None)
        if function_call:
            try:
                content += "\n[调用] " + json.dumps(
                    function_call, ensure_ascii=False, default=str
                )
            except (TypeError, ValueError):
                pass
        if role == FUNCTION_ROLE and name:
            lines.append(f"function[{name}]: {content}")
        else:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


class CompressProcessorConfig(BaseAsyncProcessorConfig):
    """压缩处理器配置。"""

    processor_type: str = COMPRESSOR_PROCESSOR_TYPE
    trigger_token_num: int = ContextConstant.DEFAULT_ASYNC_COMPRESS_TRIGGER_TOKEN_NUM
    keep_recent_turns: int = DEFAULT_KEEP_RECENT_TURNS
    strategy: str = SUMMARY_STRATEGY
    summary_prompt: str = DEFAULT_SUMMARY_PROMPT
    summary_timeout_seconds: float = DEFAULT_SUMMARY_TIMEOUT_SECONDS
    update_strategy: str = Field(
        default=ContextHandleType.UPDATE_COMPRESSED_HISTORY.value
    )


@ProcessorFactory.register(COMPRESSOR_PROCESSOR_TYPE, CompressProcessorConfig)
class CompressProcessor(AsyncContextProcessor):
    """超长上下文压缩处理器。

    condition：历史 token 估算超过 trigger_token_num 且存在可压缩中间层。
    arun/run：分层压缩，返回新的 ContextWindow（不修改输入窗口）。
    """

    def __init__(self, config: Optional[CompressProcessorConfig] = None, model=None):
        if config is None:
            config = CompressProcessorConfig()
        super().__init__(config, model)

    async def condition(self, context: ContextWindow) -> bool:
        """超过触发阈值且存在可压缩中间层时返回 True。"""
        return self._should_compress(context)

    async def arun(self, context: ContextWindow) -> ContextWindow:
        """异步压缩：摘要由 model.ainvoke 生成。"""
        messages, anchor_end, boundary = self._split(context)
        if boundary <= anchor_end:
            return context
        summary_text = await self._summarize_layer(
            messages[anchor_end:boundary]
        )
        return ContextWindow(
            chat_history=self._assemble(messages, anchor_end, boundary, summary_text)
        )

    def run(self, context: ContextWindow) -> ContextWindow:
        """同步压缩：摘要由 model.invoke 生成（无超时保护，慎在事件循环内使用）。"""
        messages, anchor_end, boundary = self._split(context)
        if boundary <= anchor_end:
            return context
        summary_text = self._summarize_layer_sync(messages[anchor_end:boundary])
        return ContextWindow(
            chat_history=self._assemble(messages, anchor_end, boundary, summary_text)
        )

    def _should_compress(self, context: ContextWindow) -> bool:
        messages = getattr(context, "chat_history", None) or []
        if not messages:
            return False
        anchor_end, boundary = split_compress_boundary(
            messages, self._config.keep_recent_turns
        )
        if boundary <= anchor_end:
            return False
        return estimate_history_tokens(messages) > self._config.trigger_token_num

    def _split(self, context: ContextWindow):
        messages = list(getattr(context, "chat_history", None) or [])
        anchor_end, boundary = split_compress_boundary(
            messages, self._config.keep_recent_turns
        )
        return messages, anchor_end, boundary

    async def _summarize_layer(
        self, messages: List[ConversationMessage]
    ) -> Optional[str]:
        """摘要压缩层；策略为 truncate、无模型或失败时返回 None（回退截断）。"""
        if self._config.strategy != SUMMARY_STRATEGY or self._model is None:
            return None
        try:
            return await asyncio.wait_for(
                self._asummarize(format_messages_for_summary(messages)),
                timeout=self._config.summary_timeout_seconds,
            )
        except Exception as e:
            logger.error(
                f"history summarize failed, fallback to truncate: {str(e)}",
                simple_log="history summarize failed, fallback to truncate",
            )
            return None

    def _summarize_layer_sync(
        self, messages: List[ConversationMessage]
    ) -> Optional[str]:
        if self._config.strategy != SUMMARY_STRATEGY or self._model is None:
            return None
        try:
            result = self._model.invoke(
                self._build_summary_input(format_messages_for_summary(messages))
            )
            content = str(getattr(result, "content", None) or "").strip()
            if not content:
                raise ValueError("empty summary content")
            return content
        except Exception as e:
            logger.error(
                f"history summarize failed, fallback to truncate: {str(e)}",
                simple_log="history summarize failed, fallback to truncate",
            )
            return None

    def _build_summary_input(self, transcript: str) -> str:
        # replace 而非 str.format，避免自定义 prompt 中的花括号引发 KeyError
        return self._config.summary_prompt.replace("{history}", transcript)

    async def _asummarize(self, transcript: str) -> str:
        result = await self._model.ainvoke(self._build_summary_input(transcript))
        content = str(getattr(result, "content", None) or "").strip()
        if not content:
            raise ValueError("empty summary content")
        return content

    def _assemble(
        self,
        messages: List[ConversationMessage],
        anchor_end: int,
        boundary: int,
        summary_text: Optional[str],
    ) -> List[ConversationMessage]:
        """重组历史：锚点层 + [摘要消息] + 保护层。

        摘要消息合并压缩层全部 intent（去重），保证按 intent 过滤历史的
        消费方仍能命中；strategy=truncate 或摘要失败时不插入摘要消息。
        """
        compressed = messages[anchor_end:boundary]
        intents: List[str] = []
        for message in compressed:
            for intent in message.intent or []:
                if intent not in intents:
                    intents.append(intent)

        new_messages: List[ConversationMessage] = list(messages[:anchor_end])
        if summary_text:
            new_messages.append(
                ConversationMessage(
                    role="assistant",
                    content=f"{SUMMARY_MESSAGE_PREFIX}\n{summary_text}",
                    intent=intents or None,
                )
            )
        new_messages.extend(messages[boundary:])
        return new_messages
