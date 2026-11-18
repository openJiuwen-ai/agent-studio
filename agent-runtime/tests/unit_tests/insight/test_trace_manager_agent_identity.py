# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for agent identity injection in the TraceManager dual-write bridge.

Locks the identity plumbing for studio #1583: the executing agent's flat
identity (raw AgentMetaData.id / real display name like "天气预测" / description)
is carried by the root TraceManager, inherited by derived / child managers with
a not-overwrite guard (identity NO_AGENT_IDENTITY is final too), and injected
into the instance_info forwarded to the openjiuwen tracer so spans are stamped
with the real agent name instead of component class names (e.g. "Model").
"""

import ast
import os
import uuid

import pytest

from jiuwen.insight.manager import (
    NO_AGENT_IDENTITY,
    TraceManager,
    get_child_manager,
)
from jiuwen.insight.utils import get_agent_identity


WEATHER_IDENTITY = {
    "agent_id": "agent-weather-001",
    "agent_name": "天气预测",
    "agent_description": "提供未来七日天气预报",
}

CONTROLLER_IDENTITY = {
    "agent_id": "controller",
    "agent_name": "控制器",
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


class _FakeAgent:
    """Minimal stand-in exposing the identity fields of jiuwen Agent."""

    def __init__(
        self,
        agent_id=None,
        name=None,
        description=None,
        with_config=True,
        meta_id=None,
    ):
        self.agent_id = agent_id
        if with_config:
            metadata = type(
                "Meta", (), {"id": meta_id, "name": name, "description": description}
            )()
            self.agent_config = type("Cfg", (), {"metadata": metadata})()


def _make_manager(**kwargs):
    tracer = _FakeTracer()
    manager = TraceManager(trace_handlers=[], openjiuwen_tracer=tracer, **kwargs)
    return manager, tracer


def _last_forwarded_info(tracer):
    return tracer.events[-1][1]["instance_info"]


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

        info = _last_forwarded_info(tracer)
        assert info["agent_name"] == "payload-name"

    @pytest.mark.asyncio
    async def test_no_identity_keeps_payload_untouched(self):
        manager, tracer = _make_manager()
        manager.instance_info = {"class_name": "Agent"}

        await manager.on_chain_start({"inputs": "hi"})

        info = _last_forwarded_info(tracer)
        assert "agent_name" not in info
        assert info["class_name"] == "Agent"

    @pytest.mark.asyncio
    async def test_identity_dict_copied_not_referenced(self):
        identity = dict(WEATHER_IDENTITY)
        manager, tracer = _make_manager(agent_identity=identity)
        identity["agent_name"] = "mutated"

        await manager.on_llm_start({"inputs": "hi"})

        # 构造后修改入参字典不影响已持有的身份拷贝
        assert _last_forwarded_info(tracer)["agent_name"] == "天气预测"


class TestIdentityInheritance:
    @pytest.mark.asyncio
    async def test_explicit_identity_not_overwritten_by_chain(self):
        """成员根 manager 自带成员身份，不得被 controller 链身份覆盖（守卫）。"""
        controller, tracer = _make_manager(agent_identity=CONTROLLER_IDENTITY)

        member_root = TraceManager.generate_manager(
            controller,
            {"class_name": "Agent"},
            agent_identity=WEATHER_IDENTITY,
        )

        await member_root.on_llm_start({"inputs": "hi"})

        info = _last_forwarded_info(tracer)
        assert info["agent_id"] == "agent-weather-001"
        assert info["agent_name"] == "天气预测"

    @pytest.mark.asyncio
    async def test_generate_manager_inherits_identity_without_explicit(self):
        """LLM / prompt 等 derive 出的 manager 继承根身份（真名可达 LLM span）。"""
        root, tracer = _make_manager(agent_identity=WEATHER_IDENTITY)

        llm_manager = TraceManager.generate_manager(root, {"class_name": "Model"})

        await llm_manager.on_llm_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["agent_name"] == "天气预测"

    @pytest.mark.asyncio
    async def test_get_child_manager_inherits_identity(self):
        root, tracer = _make_manager(agent_identity=WEATHER_IDENTITY)

        child = get_child_manager(root, "sub")

        await child.on_chain_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["agent_name"] == "天气预测"

    @pytest.mark.asyncio
    async def test_derived_llm_manager_forwards_real_name(self):
        """端到端：planner 风格 LLM manager 转发时 agent_name 是真名而非 Model。"""
        root, tracer = _make_manager(agent_identity=WEATHER_IDENTITY)
        llm_manager = TraceManager.generate_manager(
            root,
            {"class_name": "Model", "instance_attributes": {"model": "qwen-max"}},
        )

        await llm_manager.on_llm_start({"inputs": "hi"})

        info = _last_forwarded_info(tracer)
        assert info["agent_name"] == "天气预测"
        assert info["class_name"] == "Model"

    @pytest.mark.asyncio
    async def test_no_identity_member_root_not_backfilled_by_chain(self):
        """无 agent_id 的成员根 manager（哨兵终态）不得被 controller 链身份补齐。

        评审指出：仅「已携带身份不覆盖」不足以覆盖成员根无身份的场景——
        继承会把 controller 身份悄悄盖进来，与「无 agent_id 不注入」语义
        矛盾（成员 span 冒名 controller）。
        """
        controller, tracer = _make_manager(agent_identity=CONTROLLER_IDENTITY)

        member_root = TraceManager.generate_manager(
            controller,
            {"class_name": "Agent"},
            agent_identity=NO_AGENT_IDENTITY,
        )

        await member_root.on_llm_start({"inputs": "hi"})

        info = _last_forwarded_info(tracer)
        assert "agent_id" not in info
        assert "agent_name" not in info
        assert info["class_name"] == "Agent"

    @pytest.mark.asyncio
    async def test_inherited_identity_is_independent_copy(self):
        """继承取拷贝：此后根身份变更不影响已继承的派生 manager。"""
        root, tracer = _make_manager(agent_identity=WEATHER_IDENTITY)

        llm_manager = TraceManager.generate_manager(root, {"class_name": "Model"})
        root.oj_agent_identity["agent_name"] = "mutated"

        await llm_manager.on_llm_start({"inputs": "hi"})

        assert _last_forwarded_info(tracer)["agent_name"] == "天气预测"


class TestGetAgentIdentity:
    @staticmethod
    def test_real_name_and_raw_id_from_metadata():
        agent = _FakeAgent(
            meta_id="weather-001",
            agent_id="weather-001_v3",
            name="天气预测",
            description="desc",
        )

        identity = get_agent_identity(agent)

        assert identity == {
            "agent_id": "weather-001",
            "agent_name": "天气预测",
            "agent_description": "desc",
        }

    @staticmethod
    def test_id_prefers_metadata_id_over_composite():
        """AgentConfig.agent_id 是 "<agentId>_<agentVersion>" 复合值，仅缺省回退。

        core 侧 LLM 标识 / 工作流组件 span / context_manager 均用 IR 原始
        agentId（即 AgentMetaData.id），取复合值会无法按 agent 关联。
        """
        agent = _FakeAgent(
            meta_id="weather-001", agent_id="weather-001_v3", name="天气预测"
        )

        assert get_agent_identity(agent)["agent_id"] == "weather-001"

    @staticmethod
    def test_missing_metadata_id_falls_back_to_composite():
        agent = _FakeAgent(
            meta_id=None, agent_id="weather-001_v3", name="天气预测"
        )

        identity = get_agent_identity(agent)

        assert identity["agent_id"] == "weather-001_v3"
        assert identity["agent_name"] == "天气预测"

    @staticmethod
    def test_metadata_id_only_without_agent_id_attr():
        """AgentMetaData.id 恒有（IR agentId），agent_id 属性为空也能取到身份。"""
        agent = _FakeAgent(meta_id="weather-001", agent_id=None, name="天气预测")

        identity = get_agent_identity(agent)

        assert identity["agent_id"] == "weather-001"

    @staticmethod
    def test_name_falls_back_to_agent_id():
        agent = _FakeAgent(meta_id="weather-001", agent_id="weather-001_v3", name=None)

        identity = get_agent_identity(agent)

        assert identity["agent_name"] == "weather-001"

    @staticmethod
    def test_missing_agent_id_returns_none():
        agent = _FakeAgent(meta_id=None, agent_id=None, name="天气预测")

        assert get_agent_identity(agent) is None

    @staticmethod
    def test_missing_agent_config_uses_agent_id():
        agent = _FakeAgent(agent_id="weather-001", with_config=False)

        identity = get_agent_identity(agent)

        assert identity["agent_id"] == "weather-001"
        assert identity["agent_name"] == "weather-001"


class TestSetupTraceManagerWiring:
    """Agent._setup_trace_manager 是身份注入的唯一生产接线点（agent.py）。

    该模块导入链穿透 plugin / store 层（psycopg2、SpiffWorkflow 等单测
    环境缺失，且 MagicMock 会打断 jiuwen.plugin 的真实循环引用），无法在
    单测里整体 import——以 AST 契约锁定接线形态：方法或 agent_identity
    传参被删时此处失败，防止行为用例全绿但接线静默丢失。
    """

    @staticmethod
    def _load_setup_method():
        source_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "jiuwen",
            "controller",
            "agent",
            "agent.py",
        )
        with open(source_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Agent":
                for item in node.body:
                    if (
                        isinstance(item, ast.AsyncFunctionDef)
                        and item.name == "_setup_trace_manager"
                    ):
                        return item
        return None

    @staticmethod
    def test_setup_trace_manager_passes_identity_or_sentinel():
        method = TestSetupTraceManagerWiring._load_setup_method()
        assert method is not None, "Agent._setup_trace_manager 缺失（身份接线被删？）"

        gen_calls = []
        for n in ast.walk(method):
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "generate_manager":
                gen_calls.append(n)
        assert gen_calls, "_setup_trace_manager 不再构造 TraceManager"
        keywords = []
        for call in gen_calls:
            for kw in call.keywords:
                if kw.arg == "agent_identity":
                    keywords.append(kw)
        assert keywords, "接线丢失：generate_manager 未传 agent_identity"
        value = keywords[0].value
        # 形态：get_agent_identity(self) or NO_AGENT_IDENTITY（无身份时哨兵终态）
        assert isinstance(value, ast.BoolOp) and isinstance(value.op, ast.Or)
        first, second = value.values
        assert (
            isinstance(first, ast.Call)
            and isinstance(first.func, ast.Name)
            and first.func.id == "get_agent_identity"
        ), "agent_identity 不再来自 get_agent_identity(self)"
        assert isinstance(second, ast.Name) and second.id == "NO_AGENT_IDENTITY", (
            "缺省分支必须传 NO_AGENT_IDENTITY 哨兵（防止成员根被继承补齐）"
        )
