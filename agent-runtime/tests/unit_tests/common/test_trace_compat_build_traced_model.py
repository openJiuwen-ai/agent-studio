# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Tests for trace_compat.build_traced_model — 裸 Model 装饰工厂。

契约：
- 能力门槛：core 不具备壳合并能力（LLM_SPAN_MERGE_CAPABILITY 探测不到）
  时原样返回裸模型——旧 core 上宁可无 span 也不双计；
- session 已有则直接复用，否则按 ModelWrapper 范式新建轻量 agent session
  （session_id 透传）；
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

        def span(self):
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

    monkeypatch.setattr(core_tracer, "decorate_model_with_trace", _decorate)
    return calls


class TestGate:
    def test_gate_closed_returns_bare_model(self, monkeypatch, stub_decorate):
        """能力门槛不达标：原模型原样返回，不导入装饰入口、不建会话。"""
        monkeypatch.setattr(trace_compat, "_LLM_SHELL_MERGE_CAPABLE", False)

        def _boom(*args, **kwargs):
            raise AssertionError("gate closed must not create any session")

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _boom)
        model = object()
        assert build_traced_model(model) is model
        assert stub_decorate == []

    def test_gate_open_decorates_model(self, gate_open, stub_decorate, monkeypatch):
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

    def test_explicit_session_reused_no_fresh_one(self, gate_open, stub_decorate, monkeypatch):
        """显式传入 session：直接复用，不再新建轻量会话。"""
        monkeypatch.setattr(
            trace_compat,
            "create_agent_session_with_trace",
            lambda *a, **k: pytest.fail("explicit session must be reused as-is"),
        )
        model, session = object(), _StubSession()
        result = build_traced_model(model, session=session)
        assert result[2] is session


class TestDegrade:
    def test_decorate_entry_missing_returns_bare(self, gate_open, monkeypatch):
        """旧 core 无 decorate_model_with_trace 入口：降级返回裸模型。"""
        import openjiuwen.core.session.tracer as core_tracer

        monkeypatch.delattr(core_tracer, "decorate_model_with_trace")
        model = object()
        assert build_traced_model(model) is model

    def test_session_creation_failure_returns_bare(self, gate_open, stub_decorate, monkeypatch):
        """轻量会话创建抛错：吞掉并返回裸模型，绝不阻断模型创建。"""

        def _explode(*args, **kwargs):
            raise RuntimeError("session factory down")

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _explode)
        model = object()
        assert build_traced_model(model) is model
        assert stub_decorate == []


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
        calls = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "build_traced_model"
        ]
        assert len(calls) == self.SITES[rel_path], (
            f"{rel_path}: expected {self.SITES[rel_path]} build_traced_model call(s), "
            f"found {len(calls)}"
        )

    def test_resource_registration_model_stays_bare(self):
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
            nested = [
                n
                for n in ast.walk(node)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "build_traced_model"
            ]
            assert nested == [], (
                f"{node.name}: resource registration must not double-wrap models"
            )
