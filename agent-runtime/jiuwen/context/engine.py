#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
from typing import Union, Dict, List, Optional, Any

from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import BaseMessage
from jiuwen.common.log.base import logger
from jiuwen.context.accessor.handler import ContextHandler
from jiuwen.context.accessor.memory_accessor import MemoryAccessor
from jiuwen.context.base import ContextConfig, ContextHandleType, ContextWindow
from jiuwen.context.executor.executor import ContextExecutor
from jiuwen.context.history import ConversationHistory, ConversationMessage
from jiuwen.context.memory import MemoryContext
from jiuwen.context.processor.compressor import CompressProcessor, CompressProcessorConfig
from jiuwen.serve.common.context import request_json
from jiuwen.serve.controllers.execution.enum import MessageRole


class ContextEngine:
    def __init__(
        self,
        context_config: ContextConfig = None,
        history: ConversationHistory = None,
        model: BaseChatModel = None,
    ):
        self.history = history if history else ConversationHistory()
        self.memory_context = MemoryContext()
        self.model = model
        self._handler: ContextHandler = ContextHandler(
            self.history, self.memory_context
        )
        self._executor: ContextExecutor = ContextExecutor(
            handler=self._handler, model=model
        )
        self.conf = (
            context_config if context_config else ContextConfig.from_config_dict({})
        )
        if self.conf.enable_memory and self.conf.mem_variables:
            self.__init_memory_accessor()
        self._compressor: Optional[CompressProcessor] = None
        self._compress_lock = asyncio.Lock()
        if self.conf.enable_compression:
            if self.model is not None:
                self._compressor = CompressProcessor(
                    CompressProcessorConfig(**(self.conf.compress_config or {})),
                    self.model,
                )
            else:
                logger.warning(
                    "context compression is enabled but no model provided, "
                    "compression disabled"
                )

    def add_messages(self, messages: Union[List[Dict], List[ConversationMessage]]):
        """add list messages to history"""
        self.history.add_messages(messages)
        self._schedule_compress()

    def get_messages(self, filters: Optional[Dict] = None) -> List[ConversationMessage]:
        """
        get history messages, If enable_memory configuration is enabled。
        If memory search enable configured:
        queries long-term memory and memory variables,
        and appends the messages as a user message.
        If memory user profile enabled:
        query user profile from memory client
        and appends the messages as a user message.
        :param filters: 过滤历史上下文的条件，支持字段：
                {
                    "agent_id": None,               是否通过agent_id过滤筛选
                    "intent": None,                 是否通过intent过滤筛选
                    "enable_history": True/False,   是否通过enable_history过滤筛选
                    "num": -1                       是否直接截断取倒数num轮对话记录
                }
        :return:
        """
        # 短期对话历史
        return (
            self.history.get_messages(**filters)
            if filters
            else self.history.get_all_messages()
        )

    def get_latest_k_chat_history_dict(self, k: int) -> List[Dict[str, Any]]:
        """Get recent 'k' turns of conversation history, in dictionary format."""
        messages = self.history.get_messages_by_turn(k)
        return self.history.convert_messages_to_chat_history_dict(messages)

    def add_message(self, message: ConversationMessage):
        """add one history message"""
        self.history.add(message)

        # 添加长期记忆
        if self.conf.enable_memory and self.conf.mem_variables:
            self.add_message_to_memory(message)

        self._schedule_compress()

    def add_user_message(
        self,
        content: str,
        intent: Optional[str] = None,
        files: Optional[List[Dict[str, Any]]] = None,
        enable_history: Optional[bool] = True,
        agent_id: Optional[str] = None,
    ):
        """add user message"""
        self.add_message(
            ConversationMessage(
                content=content,
                files=files,
                role=MessageRole.USER.value,
                enable_history=enable_history,
                function_call=[],
                agent_id=agent_id,
            )
        )
        if intent:
            self.history.set_latest_intent(intent)

    def add_assistant_message(
        self,
        content: str,
        intent: Optional[str] = None,
        function_call: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        enable_history: Optional[bool] = True,
    ):
        """add assistant message"""
        self.add_message(
            ConversationMessage(
                content=content,
                role=MessageRole.ASSISTANT.value,
                function_call=function_call if function_call else [],
                enable_history=enable_history,
                agent_id=agent_id,
            )
        )
        if intent:
            self.history.set_latest_intent(intent)

    def add_short_term_memory(self, key, state_key, val):
        """add short term memory"""
        self.memory_context.add_short_term_memory(key, state_key, val)

    def get_short_term_memory(self, key):
        """get short term memory"""
        return self.memory_context.memory_variable.get(key, None)

    def get_param_extraction_context(self, key):
        """get ExtractParamsState from memory variable"""
        return self.memory_context.get_param_extraction_context(key)

    def get_tool_results(self, key):
        """get tool results from memory variable"""
        return self.memory_context.get_tool_results(key)

    def add_message_to_memory(self, message: ConversationMessage):
        """add long term memory
        Args:
            message (ConversationMessage): conversation message
        """
        mem_content = message.content.strip()
        if not mem_content:
            return

        user_id = request_json.get().get("userId", "")
        agent_id = request_json.get().get("agentId", "")
        if not user_id or not agent_id:
            logger.error(
                "Failed to add memory: Missing userId or agentId in request_json."
            )
            return

        mem_message = BaseMessage(type=message.role, content=message.content)
        self.memory_accessor.add_memory(
            user_id=user_id, agent_id=agent_id, message=mem_message
        )
        return

    def __init_memory_accessor(self):
        """init memory accessor and set mem engine config"""
        self.memory_accessor = MemoryAccessor(self.model)
        self.memory_accessor.set_variable_config(self.conf.mem_variables)

    def _schedule_compress(self):
        """在事件循环内调度一次后台压缩（fire-and-forget）。

        压缩仅在存在运行中的事件循环时调度；同步上下文（无循环）下跳过，
        待下次异步上下文写入消息时重试。压缩失败只记录日志，不影响对话。
        """
        if self._compressor is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.acompress_history())

    async def acompress_history(self):
        """按配置压缩超长历史（幂等，可显式调用）。

        流程：快照历史 -> condition 判定 -> 分层压缩（摘要/截断）-> 带竞态
        保护地写回。写回前校验快照仍是当前历史的前缀（逐条对象同一性），
        压缩期间新增的消息会被保留，绝不丢失；前缀已变化则放弃本次结果，
        等待下次触发重试。
        """
        if self._compressor is None:
            return
        async with self._compress_lock:
            try:
                snapshot = list(self.history.msgs)
                window = ContextWindow(chat_history=snapshot)
                if not await self._compressor.condition(window):
                    return
                new_window = await self._compressor.arun(window)
                if new_window is window:
                    return
                current = self.history.msgs
                if len(current) < len(snapshot) or any(
                    old is not cur for old, cur in zip(snapshot, current)
                ):
                    logger.info(
                        "history changed during compression, skip applying result",
                        simple_log="history changed during compression, skip applying",
                    )
                    return
                merged = (
                    list(new_window.chat_history or [])
                    + list(current[len(snapshot):])
                )
                update = self._handler.get_handler(
                    ContextHandleType.UPDATE_COMPRESSED_HISTORY
                )
                if update is None:
                    logger.error(
                        "update_compressed_history handler not registered, "
                        "cannot apply compression"
                    )
                    return
                update(ContextWindow(chat_history=merged))
                logger.info(
                    f"history compressed: {len(snapshot)} -> {len(merged)} messages",
                    simple_log=f"history compressed: {len(snapshot)} -> "
                    f"{len(merged)} messages",
                )
            except Exception as e:
                logger.error(
                    f"history compression failed: {str(e)}",
                    simple_log="history compression failed",
                )
