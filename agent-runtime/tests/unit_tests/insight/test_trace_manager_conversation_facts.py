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
    """Minimal stand-in exposing the openjiuwen Session fact surface.

    取值面与 core Session 对齐：公开访问器 get_source_metadata 返回
    副本（新 wave），私有名 _source_metadata 仅作旧 wave 兜底。
    """

    def __init__(self, session_id="conv-8848", source_metadata=None):
        self._session_id = session_id
        self._source_metadata = source_metadata or {}

    def get_session_id(self):
        return self._session_id

    def get_source_metadata(self):
        return dict(self._source_metadata)


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

    @staticmethod
    def test_public_accessor_preferred_over_private_name():
        """公开访问器优先（检视意见）：两处取值面不一致时以访问器为准。

        回归成直读 _source_metadata 私有名时取到 from-private，断言即败。
        """

        class _AccessorSession(_FakeSession):
            def get_source_metadata(self):
                return {"user_id": "from-accessor"}

        session = _AccessorSession(source_metadata={"user_id": "from-private"})

        assert get_conversation_facts(session)["user_id"] == "from-accessor"

    @staticmethod
    def test_legacy_session_without_accessor_falls_back():
        """旧 wave core Session 无公开访问器：私有名兜底仍能取到事实。

        本地 .testenv 安装的 openjiuwen 即该形态（已验证：构造入参
        source_metadata 落在 _source_metadata，无 get_source_metadata）。
        """

        class _LegacySession:
            def __init__(self):
                self._session_id = "conv-8848"
                self._source_metadata = {"user_id": "u-legacy"}

            def get_session_id(self):
                return self._session_id

        assert get_conversation_facts(_LegacySession())["user_id"] == "u-legacy"

    @staticmethod
    def test_real_core_session_contract():
        """真实 openjiuwen Session 集成锁定（检视意见）：不依赖自建替身。

        安装 wave 新旧皆可：新 wave 走 get_source_metadata 访问器，
        旧 wave 走 _source_metadata 兜底，事实都必须取到。
        """
        try:
            from openjiuwen.core.session.agent import create_agent_session
        except ImportError:  # pragma: no cover - 环境缺 core 时跳过
            pytest.skip("openjiuwen core session 不可用")
        session = create_agent_session(
            session_id="conv-real", card=None, source_metadata={"user_id": "u-real"}
        )

        assert get_conversation_facts(session) == {
            "conversation_id": "conv-real",
            "user_id": "u-real",
        }
