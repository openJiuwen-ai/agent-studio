#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import functools
from typing import Dict, Optional, Callable

from jiuwen.context.base import ContextWindow, ContextHandleType
from jiuwen.context.history import ConversationHistory
from jiuwen.context.memory import MemoryContext

_CONTEXT_HANDLERS: Dict[ContextHandleType, Callable] = dict()


def register_context_handler(name: ContextHandleType, func=None):
    """register a context handler function"""

    @functools.wraps(func)
    def register_context_handler_method(func: Callable):
        _CONTEXT_HANDLERS[name] = func
        return func

    return register_context_handler_method


class ContextHandler:
    def __init__(
        self,
        history: ConversationHistory,
        memory: MemoryContext,
    ) -> None:
        self._history = history
        self._memory = memory

    def get_handler(self, handle_type: ContextHandleType) -> Optional[Callable]:
        """get context operation handler"""
        handler = _CONTEXT_HANDLERS.get(handle_type, None)
        if handler is None:
            return None
        return functools.partial(handler, self)

    @register_context_handler(ContextHandleType.UPDATE_NOTHING)
    def update_nothing(self, context: ContextWindow):
        """update nothing to context"""
        pass

    @register_context_handler(ContextHandleType.UPDATE_COMPRESSED_HISTORY)
    def update_compressed_history(self, context: ContextWindow):
        """replace chat history with the compressed one"""
        if context is None or context.chat_history is None:
            return
        self._history.msgs = list(context.chat_history)

    def create_context_window(self):
        """create context window"""
        return ContextWindow(
            chat_history=self._history.get_messages(),
        )
