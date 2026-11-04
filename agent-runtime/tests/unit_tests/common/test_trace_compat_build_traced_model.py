# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Tests for trace_compat.build_traced_model — 裸 Model 装饰工厂。

契约：
- 能力门槛：core 不具备壳合并能力（LLM_SPAN_MERGE_CAPABILITY 探测不到）
  时原样返回裸模型——旧 core 上宁可无 span 也不双计；探测是 getattr +
  ``== "1"`` 精确匹配（版本化字符串契约，非 truthy 判定）；
- session 显式传入则直接复用；否则新建轻量 agent session：定义级产物
  （跨执行复用的组件/模型）落 DEFINITION_SCOPED_SESSION_ID 且不绑构建期
  请求 trace，请求级场景（react 每执行新建）透传当次会话 id、trace 走
  请求上下文；
- 探测 / 导入 / 建会话 / 装饰任何一步失败都降级返回裸模型，绝不阻断业务；
- 六个裸 Model 构造点全部经工厂接线，资源注册路径（get_model 已装饰）除外。
"""

import ast
from pathlib import Path

import pytest

import agent_runtime.common.trace_compat as trace_compat
from agent_runtime.common.trace_compat import build_traced_model

_RUNTIME_ROOT = Path(__file__).resolve().parents[3]


class _StubSession:
    """满足 decorate_model_with_trace 的 _should_decorate 契约的会话替身。"""

    class _Inner:
        def tracer(self):
            return self

        @staticmethod
        def span():
            return None

        @staticmethod
        def agent_handler_valid():
            return True

    def __init__(self):
        self._inner = self._Inner()


@pytest.fixture(autouse=True)
def _restore_capability_cache():
    """每个用例后复位能力探测缓存，避免用例间串扰。"""
    yield
    trace_compat._LLM_SHELL_MERGE_CAPABLE = None


@pytest.fixture
def gate_open(monkeypatch):
    monkeypatch.setattr(trace_compat, "_LLM_SHELL_MERGE_CAPABLE", True)


@pytest.fixture
def stub_decorate(monkeypatch):
    calls = []

    def _decorate(model, session):
        calls.append((model, session))
        return ("decorated", model, session)

    import openjiuwen.core.session.tracer as core_tracer

    monkeypatch.setattr(core_tracer, "decorate_model_with_trace", _decorate, raising=False)
    return calls


class TestGate:
    @staticmethod
    def test_gate_closed_returns_bare_model(monkeypatch, stub_decorate):
        """能力门槛不达标：原模型原样返回，不导入装饰入口、不建会话。"""
        monkeypatch.setattr(trace_compat, "_LLM_SHELL_MERGE_CAPABLE", False)

        def _boom(*args, **kwargs):
            raise AssertionError("gate closed must not create any session")

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _boom)
        model = object()
        assert build_traced_model(model) is model
        assert stub_decorate == []

    @staticmethod
    def test_gate_open_decorates_model(gate_open, stub_decorate, monkeypatch):
        """门槛达标：新建轻量会话并装饰，session_id 透传。"""
        created = {}

        def _fake_create(session_id=None, **kwargs):
            created["session_id"] = session_id
            return _StubSession()

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _fake_create)
        model = object()
        result = build_traced_model(model, session_id="conv-1")
        assert result[0] == "decorated"
        assert result[1] is model
        assert isinstance(result[2], _StubSession)
        assert created["session_id"] == "conv-1"

    @staticmethod
    def test_explicit_session_reused_no_fresh_one(gate_open, stub_decorate, monkeypatch):
        """显式传入 session：直接复用，不再新建轻量会话。"""
        monkeypatch.setattr(
            trace_compat,
            "create_agent_session_with_trace",
            lambda *a, **k: pytest.fail("explicit session must be reused as-is"),
        )
        model, session = object(), _StubSession()
        result = build_traced_model(model, session=session)
        assert result[2] is session


class TestCapabilityProbe:
    """真实探测分支（getattr + == "1" 精确匹配）——不只直接注入缓存值。"""

    @staticmethod
    def test_probe_absent_constant_means_old_core(monkeypatch):
        """旧 core 无 LLM_SPAN_MERGE_CAPABILITY 常量：探测判为无能力。"""
        from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

        monkeypatch.delattr(OtelAgentHandler, "LLM_SPAN_MERGE_CAPABILITY", raising=False)
        monkeypatch.setattr(trace_compat, "_LLM_SHELL_MERGE_CAPABLE", None)
        assert trace_compat._llm_shell_merge_capable() is False

    @staticmethod
    def test_probe_exact_capability_string_opens_gate(monkeypatch):
        from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

        monkeypatch.setattr(OtelAgentHandler, "LLM_SPAN_MERGE_CAPABILITY", "1", raising=False)
        monkeypatch.setattr(trace_compat, "_LLM_SHELL_MERGE_CAPABLE", None)
        assert trace_compat._llm_shell_merge_capable() is True

    @staticmethod
    @pytest.mark.parametrize("wrong", ["2", True, 1])
    def test_probe_non_exact_values_keep_gate_closed(monkeypatch, wrong):
        """版本化字符串契约：非 "1"（含 truthy bool/int）一律按未达标处理。"""
        from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

        monkeypatch.setattr(OtelAgentHandler, "LLM_SPAN_MERGE_CAPABILITY", wrong, raising=False)
        monkeypatch.setattr(trace_compat, "_LLM_SHELL_MERGE_CAPABLE", None)
        assert trace_compat._llm_shell_merge_capable() is False


class TestDefinitionScopedTrace:
    """定义级会话不绑构建期请求 trace（跨执行复用，绑首请求会错归属）。"""

    @staticmethod
    def test_definition_scoped_session_binds_no_request_trace(gate_open, stub_decorate, monkeypatch):
        captured = {}

        def _fake_create(session_id=None, **kwargs):
            captured["session_id"] = session_id
            captured["kwargs"] = kwargs
            return _StubSession()

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _fake_create)
        monkeypatch.setattr(trace_compat, "get_x_request_id", lambda: "req-1")
        build_traced_model(object(), session_id=trace_compat.DEFINITION_SCOPED_SESSION_ID)
        # 显式定义级 id：即便构建期有请求上下文，也不得绑请求 trace
        assert captured["session_id"] == trace_compat.DEFINITION_SCOPED_SESSION_ID
        assert captured["kwargs"].get("trace_id") is trace_compat._DEFINITION_NO_TRACE

    @staticmethod
    def test_request_scoped_session_keeps_ambient_trace(gate_open, stub_decorate, monkeypatch):
        captured = {}

        def _fake_create(session_id=None, **kwargs):
            captured["session_id"] = session_id
            captured["kwargs"] = kwargs
            return _StubSession()

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _fake_create)
        build_traced_model(object(), session_id="conv-1")
        assert captured["session_id"] == "conv-1"
        # 请求级会话不显式传 trace_id（工厂内缺省沿用请求上下文）
        assert "trace_id" not in captured["kwargs"]

    @staticmethod
    def test_explicit_no_trace_not_forwarded_to_core(monkeypatch):
        forwarded = {}

        def _fake_core_create(session_id=None, **kwargs):
            forwarded.update(kwargs)

        monkeypatch.setattr(trace_compat, "_create_agent_session", _fake_core_create)
        monkeypatch.setattr(trace_compat, "_agent_accepts_trace_id", True)
        trace_compat.create_agent_session_with_trace(
            session_id="workflow-llm", trace_id=trace_compat._DEFINITION_NO_TRACE
        )
        assert "trace_id" not in forwarded
        trace_compat.create_agent_session_with_trace(session_id="conv-1", trace_id="t-9")
        assert forwarded.get("trace_id") == "t-9"


class TestDegrade:
    @staticmethod
    def test_decorate_entry_missing_returns_bare(gate_open, monkeypatch):
        """旧 core 无 decorate_model_with_trace 入口：降级返回裸模型。"""
        import openjiuwen.core.session.tracer as core_tracer

        monkeypatch.delattr(core_tracer, "decorate_model_with_trace", raising=False)
        model = object()
        assert build_traced_model(model) is model

    @staticmethod
    def test_session_creation_failure_returns_bare(gate_open, stub_decorate, monkeypatch):
        """轻量会话创建抛错：吞掉并返回裸模型，绝不阻断模型创建。"""

        def _explode(*args, **kwargs):
            raise RuntimeError("session factory down")

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _explode)
        model = object()
        assert build_traced_model(model) is model
        assert stub_decorate == []


def _find_calls_by_name(tree, func_name: str):
    """按函数名收集 ast.Call 节点（显式循环，多判据不进推导式）。"""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == func_name:
                calls.append(node)
    return calls


class TestSiteWiring:
    """六个裸 Model 构造点全部经 build_traced_model 接线（AST 契约）。"""

    SITES = {
        "agent_runtime/runner/react_agent_runner.py": 1,
        "jiuwen/extension/workflow_node/llm_chain.py": 1,
        "jiuwen/extension/workflow_node/questioner.py": 1,
        "jiuwen/extension/workflow_node/intent_detection.py": 1,
        "jiuwen/extension/workflow_node/flow_extractor.py": 1,
        # ir_converter: LLMReAct 节点经工厂；资源注册路径的 Model( 由
        # ModelMgr.get_model 装饰，不得包第二层（双装饰=双计）
        "jiuwen/serve/controllers/execution/ir_converter.py": 1,
    }

    @pytest.mark.parametrize("rel_path", sorted(SITES))
    def test_model_construction_routed_through_factory(self, rel_path):
        source = (_RUNTIME_ROOT / rel_path).read_text(encoding="utf-8")
        calls = _find_calls_by_name(ast.parse(source), "build_traced_model")
        assert len(calls) == self.SITES[rel_path], (
            f"{rel_path}: expected {self.SITES[rel_path]} build_traced_model call(s), "
            f"found {len(calls)}"
        )

    @staticmethod
    def test_resource_registration_model_stays_bare():
        """ir_converter 资源注册（get_model 出口已装饰）不得再包工厂。"""
        source = (
            _RUNTIME_ROOT / "jiuwen/serve/controllers/execution/ir_converter.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if "resource" not in node.name and "register" not in node.name:
                continue
            assert _find_calls_by_name(node, "build_traced_model") == [], (
                f"{node.name}: resource registration must not double-wrap models"
            )

    @staticmethod
    def test_definition_scoped_components_use_definition_session():
        """定义级组件（跨执行复用）的装饰会话一律 DEFINITION_SCOPED_SESSION_ID。

        组件实例由 IR 转换产生并被执行复用：装饰会话绑任一执行的会话 id，
        后续执行都会错归属（缓存模型保留首调会话的问题，检视 198236863）。
        """
        sites = [
            "jiuwen/extension/workflow_node/llm_chain.py",
            "jiuwen/extension/workflow_node/questioner.py",
            "jiuwen/extension/workflow_node/intent_detection.py",
            "jiuwen/extension/workflow_node/flow_extractor.py",
        ]
        for rel_path in sites:
            source = (_RUNTIME_ROOT / rel_path).read_text(encoding="utf-8")
            calls = _find_calls_by_name(ast.parse(source), "build_traced_model")
            assert calls, f"{rel_path}: build_traced_model call not found"
            for call in calls:
                sid = next((kw for kw in call.keywords if kw.arg == "session_id"), None)
                assert (
                    sid is not None
                    and isinstance(sid.value, ast.Name)
                    and sid.value.id == "DEFINITION_SCOPED_SESSION_ID"
                ), (
                    f"{rel_path}: cached definition-level component must bind "
                    f"DEFINITION_SCOPED_SESSION_ID, not an execution session id"
                )
