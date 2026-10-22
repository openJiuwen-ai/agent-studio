# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for agent identity injection in the TraceManager dual-write bridge.

Locks the identity plumbing for studio #1583: the executing agent's flat
identity (id / real display name like "天气预测" / description) is carried by
the root TraceManager, inherited by derived / child managers with a
not-overwrite guard, and injected into the instance_info forwarded to the
openjiuwen tracer so spans are stamped with the real agent name instead of
component class names (e.g. "Model").
"""

import uuid

import pytest

from jiuwen.insight.manager import TraceManager, get_child_manager
from jiuwen.insight.utils import get_agent_identity


WEATHER_IDENTITY = {
    "agent_id": "agent-weather-001",
    "agent_name": "天气预测",
    "agent_description": "提供未来七日天气预报",
}


class _FakeSpan:
    def __init__(self):
        self.invoke_id = str(uuid.uuid4())
        self.child_invokes_id = []


class _FakeSpanManager:
    last_span = None

    def create_agent_span(self, parent):
        return _FakeSpan()

    def update_span(self, span, data):
        for key, value in data.items():
            setattr(span, key, value)

    def refresh_span_record(self, *args, **kwargs):
        pass


class _FakeTracer:
    """Records openjiuwen tracer events triggered by the dual-write bridge."""

    def __init__(self):
        self.tracer_agent_span_manager = _FakeSpanManager()
        self.events = []

    async def trigger(self, source, event_name, **kwargs):
        self.events.append((event_name, kwargs))


class _FakeAgent:
    """Minimal stand-in exposing the identity fields of jiuwen Agent."""

    def __init__(self, agent_id=None, name=None, description=None, with_config=True):
        self.agent_id = agent_id
        if with_config:
            metadata = type("Meta", (), {"name": name, "description": description})()
            self.agent_config = type("Cfg", (), {"metadata": metadata})()


def _make_manager(**kwargs):
    tracer = _FakeTracer()
    manager = TraceManager(trace_handlers=[], openjiuwen_tracer=tracer, **kwargs)
    return manager, tracer


class TestIdentityInjection:
    @pytest.mark.asyncio
    async def test_start_events_carry_flat_identity(self):
        manager, tracer = _make_manager(agent_identity=WEATHER_IDENTITY)
        manager.instance_info = {
            "class_name": "Model",
            "instance_attributes": {"model": "qwen-max"},
        }

        await manager.on_llm_start({"inputs": "hi"})

        event_name, kwargs = tracer.events[-1]
        assert event_name == "on_llm_start"
        info = kwargs["instance_info"]
        assert info["agent_id"] == "agent-weather-001"
        assert info["agent_name"] == "天气预测"
        assert info["agent_description"] == "提供未来七日天气预报"
        # 原有载荷内容不受影响：class_name 仍用于模型属性
        assert info["class_name"] == "Model"

    @pytest.mark.asyncio
    async def test_payload_keys_win_over_identity(self):
        manager, tracer = _make_manager(agent_identity=WEATHER_IDENTITY)
        manager.instance_info = {"class_name": "Model", "agent_name": "payload-name"}

        await manager.on_llm_start({"inputs": "hi"})

        info = tracer.events[-1][1]["instance_info"]
        assert info["agent_name"] == "payload-name"

    @pytest.mark.asyncio
    async def test_no_identity_keeps_payload_untouched(self):
        manager, tracer = _make_manager()
        manager.instance_info = {"class_name": "Agent"}

        await manager.on_chain_start({"inputs": "hi"})

        info = tracer.events[-1][1]["instance_info"]
        assert "agent_name" not in info
        assert info["class_name"] == "Agent"

    def test_identity_dict_copied_not_referenced(self):
        identity = dict(WEATHER_IDENTITY)
        manager, _ = _make_manager(agent_identity=identity)
        identity["agent_name"] = "mutated"
        assert manager._oj_agent_identity["agent_name"] == "天气预测"


class TestIdentityInheritance:
    def test_explicit_identity_not_overwritten_by_chain(self):
        """成员根 manager 自带成员身份，不得被 controller 链身份覆盖（守卫）。"""
        controller, _ = _make_manager(
            agent_identity={"agent_id": "controller", "agent_name": "控制器"}
        )

        member_root = TraceManager.generate_manager(
            controller,
            {"class_name": "Agent"},
            agent_identity=WEATHER_IDENTITY,
        )

        assert member_root._oj_agent_identity == WEATHER_IDENTITY

    def test_generate_manager_inherits_identity_without_explicit(self):
        """LLM / prompt 等 derive 出的 manager 继承根身份（真名可达 LLM span）。"""
        root, _ = _make_manager(agent_identity=WEATHER_IDENTITY)

        llm_manager = TraceManager.generate_manager(root, {"class_name": "Model"})

        assert llm_manager._oj_agent_identity == WEATHER_IDENTITY

    def test_get_child_manager_inherits_identity(self):
        root, _ = _make_manager(agent_identity=WEATHER_IDENTITY)

        child = get_child_manager(root, "sub")

        assert child._oj_agent_identity == WEATHER_IDENTITY

    @pytest.mark.asyncio
    async def test_derived_llm_manager_forwards_real_name(self):
        """端到端：planner 风格 LLM manager 转发时 agent_name 是真名而非 Model。"""
        root, tracer = _make_manager(agent_identity=WEATHER_IDENTITY)
        llm_manager = TraceManager.generate_manager(
            root,
            {"class_name": "Model", "instance_attributes": {"model": "qwen-max"}},
        )

        await llm_manager.on_llm_start({"inputs": "hi"})

        info = tracer.events[-1][1]["instance_info"]
        assert info["agent_name"] == "天气预测"
        assert info["class_name"] == "Model"


class TestGetAgentIdentity:
    def test_real_name_from_metadata(self):
        agent = _FakeAgent(agent_id="weather-001", name="天气预测", description="desc")

        identity = get_agent_identity(agent)

        assert identity == {
            "agent_id": "weather-001",
            "agent_name": "天气预测",
            "agent_description": "desc",
        }

    def test_name_falls_back_to_agent_id(self):
        agent = _FakeAgent(agent_id="weather-001", name=None)

        identity = get_agent_identity(agent)

        assert identity["agent_name"] == "weather-001"

    def test_missing_agent_id_returns_none(self):
        agent = _FakeAgent(agent_id=None, name="天气预测")

        assert get_agent_identity(agent) is None

    def test_missing_agent_config_uses_agent_id(self):
        agent = _FakeAgent(agent_id="weather-001", with_config=False)

        identity = get_agent_identity(agent)

        assert identity["agent_name"] == "weather-001"
