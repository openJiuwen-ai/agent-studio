# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for AgentEventsProcessor._initialize_handlers 的 dict 归属。

背景缺陷：AgentEventsProcessor 用 ``cls._handler_methods.update({...})`` 原地
修改共享映射，而兄弟类 ControllerEventsProcessor / WorkflowEventsProcessor 均为
``cls._handler_methods = {**cls._handler_methods, ...}`` 拷贝语义。当 Base 先被
直接初始化（Base._initialized=True，如测试或后续代码直接引用 Base）时，Agent
的 update 会就地污染 Base 的共享 dict，随后初始化的 Controller 会快照到被污染
的映射（agent_node_message / summary_response / start / message 被换成 Agent 版
本）。修复后三个子类语义一致，各自持有独立 dict。
"""

from agent_runtime.event_handler.events.base_events import BaseEventsProcessor
from agent_runtime.event_handler.events.agent_events import AgentEventsProcessor
from agent_runtime.event_handler.events.controller_events import (
    ControllerEventsProcessor,
)
from jiuwen.serve.controllers.execution.enum import ConversationEvent


def _ensure_initialized(processor_cls):
    getattr(processor_cls, "_ensure_initialized")()


def _handler_methods(processor_cls):
    return getattr(processor_cls, "_handler_methods")


def _force_reinit(processor_cls):
    setattr(processor_cls, "_initialized", False)
    _ensure_initialized(processor_cls)


class TestSubclassOwnsHandlerDict:
    @staticmethod
    def test_agent_init_does_not_mutate_base_shared_dict():
        # 触发前提：Base 被直接初始化（此后 super() 链不会再为子类重建 dict）
        _ensure_initialized(BaseEventsProcessor)
        base_snapshot = dict(_handler_methods(BaseEventsProcessor))

        _force_reinit(AgentEventsProcessor)

        assert dict(_handler_methods(BaseEventsProcessor)) == base_snapshot
        assert (
            _handler_methods(AgentEventsProcessor)
            is not _handler_methods(BaseEventsProcessor)
        )

    @staticmethod
    def test_agent_dict_contains_own_handlers():
        _force_reinit(AgentEventsProcessor)
        handler_map = _handler_methods(AgentEventsProcessor)
        for event in (
            ConversationEvent.START,
            ConversationEvent.MESSAGE,
            ConversationEvent.SUMMARY_RESPONSE,
            ConversationEvent.AGENT_NODE_MSG,
        ):
            assert event.value in handler_map


class TestNoCrossTypePollution:
    @staticmethod
    def test_controller_does_not_inherit_agent_handlers():
        _ensure_initialized(BaseEventsProcessor)
        _force_reinit(AgentEventsProcessor)
        _force_reinit(ControllerEventsProcessor)

        handler_map = _handler_methods(ControllerEventsProcessor)
        assert (
            handler_map.get(ConversationEvent.AGENT_NODE_MSG.value)
            != AgentEventsProcessor.process_agent_node_message
        )
        assert (
            handler_map.get(ConversationEvent.SUMMARY_RESPONSE.value)
            != AgentEventsProcessor.process_summary_response_event
        )
