# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for conversation facts injection in the TraceManager dual-write bridge.

Locks the session-facts plumbing for studio #1583 (会话事实节): the flat
conversation_id / user_id keys ride the same dual-write channel as agent
identity, are merged below identity / payload keys on forward, and — unlike
identity — are inherited by derived / child / member-root managers whenever
absent (one conversation spans the whole run, so backfill is correct).
"""

import uuid

import pytest

from jiuwen.insight.manager import TraceManager, get_child_manager
from jiuwen.insight.utils import get_conversation_facts

WEATHER_IDENTITY = {
    "agent_id": "agent-weather-001",
    "agent_name": "天气预测",
    "agent_description": "提供未来七日天气预报",
}

CONVERSATION_FACTS = {
    "conversation_id": "conv-8848",
    "user_id": "u-42",
}


class _FakeSpan:
    def __init__(self):
        self.invoke_id = str(uuid.uuid4())
        self.child_invokes_id = []


class _FakeSpanManager:
    last_span = None

    @staticmethod
    def create_agent_span(parent):
        return _FakeSpan()

    @staticmethod
    def update_span(span, data):
        for key, value in data.items():
            setattr(span, key, value)

    @staticmethod
    def refresh_span_record(*args, **kwargs):
        pass


class _FakeTracer:
    """Records openjiuwen tracer events triggered by the dual-write bridge."""

    def __init__(self):
        self.tracer_agent_span_manager = _FakeSpanManager()
        self.events = []

    async def trigger(self, source, event_name, **kwargs):
        self.events.append((event_name, kwargs))


class _FakeSession:
    """Minimal stand-in exposing the openjiuwen Session fact surface."""

    def __init__(self, session_id="conv-8848", source_metadata=None):
        self._session_id = session_id
        self._source_metadata = source_metadata

    def get_session_id(self):
        return self._session_id


def _make_manager(**kwargs):
    tracer = _FakeTracer()
    manager = TraceManager(trace_handlers=[], openjiuwen_tracer=tracer, **kwargs)
    return manager, tracer


def _last_forwarded_info(tracer):
    return tracer.events[-1][1]["instance_info"]


class TestConversationFactsInjection:
    @pytest.mark.asyncio
    async def test_start_events_carry_flat_facts(self):
        manager, tracer = _make_manager(conversation_facts=CONVERSATION_FACTS)
        manager.instance_info = {"class_name": "Model"}

        await manager.on_llm_start({"inputs": "hi"})

        info = _last_forwarded_info(tracer)
        assert info["conversation_id"] == "conv-8848"
        assert info["user_id"] == "u-42"
        assert info["class_name"] == "Model"

    @pytest.mark.asyncio
    async def test_facts_coexist_with_identity(self):
        """身份与会话事实同 manager 携带：六个扁平键同时转发，互不覆盖。"""
        manager, tracer = _make_manager(
            agent_identity=WEATHER_IDENTITY, conversation_facts=CONVERSATION_FACTS
        )
        manager.instance_info = {"class_name": "Model"}

        await manager.on_llm_start({"inputs": "hi"})

        info = _last_forwarded_info(tracer)
        assert info["agent_name"] == "天气预测"
        assert info["conversation_id"] == "conv-8848"
        assert info["user_id"] == "u-42"

    @pytest.mark.asyncio
    async def test_payload_keys_win_over_facts(self):
        manager, tracer = _make_manager(conversation_facts=CONVERSATION_FACTS)
        manager.instance_info = {
            "class_name": "Model",
            "conversation_id": "payload-conv",
        }

        await manager.on_llm_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["conversation_id"] == "payload-conv"

    @pytest.mark.asyncio
    async def test_no_facts_keeps_payload_untouched(self):
        manager, tracer = _make_manager()
        manager.instance_info = {"class_name": "Agent"}

        await manager.on_chain_start({"inputs": "hi"})

        info = _last_forwarded_info(tracer)
        assert "conversation_id" not in info
        assert "user_id" not in info


class TestConversationFactsInheritance:
    @pytest.mark.asyncio
    async def test_generate_manager_inherits_facts_without_explicit(self):
        """派生 LLM manager（create_trace_manager 形态）继承根的会话事实。"""
        root, tracer = _make_manager(conversation_facts=CONVERSATION_FACTS)

        llm_manager = TraceManager.generate_manager(root, {"class_name": "Model"})

        await llm_manager.on_llm_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["conversation_id"] == "conv-8848"

    @pytest.mark.asyncio
    async def test_get_child_manager_inherits_facts(self):
        root, tracer = _make_manager(conversation_facts=CONVERSATION_FACTS)

        child = get_child_manager(root, "sub")

        await child.on_chain_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["user_id"] == "u-42"

    @pytest.mark.asyncio
    async def test_explicit_facts_not_overwritten_by_chain(self):
        """成员根 manager 自带事实（另有 session）时不被链上的覆盖（set-once）。"""
        controller, tracer = _make_manager(conversation_facts=CONVERSATION_FACTS)

        member_root = TraceManager.generate_manager(
            controller,
            {"class_name": "Agent"},
            conversation_facts={"conversation_id": "member-conv"},
        )

        await member_root.on_llm_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["conversation_id"] == "member-conv"

    @pytest.mark.asyncio
    async def test_facts_backfilled_from_chain_when_absent(self):
        """与身份的哨兵终态相反：成员根缺事实时由链补齐是正确语义。

        同一 conversation 贯穿 controller 与成员 agent——controller 侧
        session 上的会话事实对成员 span 同样成立。
        """
        controller, tracer = _make_manager(conversation_facts=CONVERSATION_FACTS)

        member_root = TraceManager.generate_manager(controller, {"class_name": "Agent"})

        await member_root.on_llm_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["conversation_id"] == "conv-8848"

    @pytest.mark.asyncio
    async def test_inherited_facts_are_independent_copy(self):
        """继承取拷贝：此后根事实变更不影响已继承的派生 manager。"""
        root, tracer = _make_manager(conversation_facts=dict(CONVERSATION_FACTS))

        llm_manager = TraceManager.generate_manager(root, {"class_name": "Model"})
        root.oj_conversation_facts["conversation_id"] = "mutated"

        await llm_manager.on_llm_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["conversation_id"] == "conv-8848"


class TestGetConversationFacts:
    @staticmethod
    def test_session_id_and_user_metadata():
        session = _FakeSession(source_metadata={"user_id": "u-42"})

        assert get_conversation_facts(session) == {
            "conversation_id": "conv-8848",
            "user_id": "u-42",
        }

    @staticmethod
    def test_no_source_metadata_yields_conversation_only():
        assert get_conversation_facts(_FakeSession()) == {"conversation_id": "conv-8848"}

    @staticmethod
    def test_empty_user_id_not_produced():
        session = _FakeSession(source_metadata={"user_id": ""})

        assert get_conversation_facts(session) == {"conversation_id": "conv-8848"}

    @staticmethod
    def test_none_session_returns_none():
        assert get_conversation_facts(None) is None

    @staticmethod
    def test_factless_session_returns_none():
        """无 session_id 且无 user_id → None（调用方跳过注入）。"""
        assert get_conversation_facts(_FakeSession(session_id="")) is None
