# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Tests for trace_compat.build_traced_model — 裸 Model 装饰工厂。

契约：
- 能力门槛：core handler 消费不了装饰器测量数据（LLM_SPAN_DECORATOR_CAPABILITY
  探测不到）时原样返回裸模型——旧 core 上宁可无 span 也不白发；探测是 getattr +
  ``>= 1`` 版本比较（版本化 int 契约，前向兼容）；
- session 显式传入则直接复用；否则新建轻量 agent session：定义级产物
  （跨执行复用的组件/模型）落 DEFINITION_SCOPED_SESSION_ID 且不绑构建期
  请求 trace，请求级场景（react 每执行新建）透传当次会话 id、trace 走
  请求上下文；
- identity 归因：core 装饰器支持 identity 参数时透传（业务 workflow_id/
  agent_id 附到独立/子 llm span，write-if-absent）；旧 core 不支持时自动
  丢弃 identity 保 span（不得因 TypeError 把整段装饰降级成裸模型）；
- 探测 / 导入 / 建会话 / 装饰任何一步失败都降级返回裸模型，绝不阻断业务；
- 五个裸 Model 构造点全部经工厂接线，资源注册路径（get_model 已装饰）除外；
  react 路径刻意不接线（多智能体同步桥线程下装饰会话与执行 trace 树脱钩
  产孤儿 llm span，缺参追问链已复现），由独立用例钉死防回归。
"""

import ast
import sys
import types
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
    """每个用例后复位能力/identity 探测缓存，避免用例间串扰。"""
    yield
    trace_compat._LLM_SPAN_DECORATOR_CAPABLE = None
    trace_compat._DECORATOR_ACCEPTS_IDENTITY = None


@pytest.fixture
def gate_open(monkeypatch):
    monkeypatch.setattr(trace_compat, "_LLM_SPAN_DECORATOR_CAPABLE", True)


@pytest.fixture
def stub_decorate(monkeypatch):
    calls = []

    def _decorate(model, session, identity=None):
        calls.append((model, session, identity))
        return ("decorated", model, session)

    import openjiuwen.core.session.tracer as core_tracer

    monkeypatch.setattr(core_tracer, "decorate_model_with_trace", _decorate, raising=False)
    return calls


class TestGate:
    @staticmethod
    def test_gate_closed_returns_bare_model(monkeypatch, stub_decorate):
        """能力门槛不达标：原模型原样返回，不导入装饰入口、不建会话。"""
        monkeypatch.setattr(trace_compat, "_LLM_SPAN_DECORATOR_CAPABLE", False)

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
    """真实探测分支（getattr + >= 1 版本比较）——不只直接注入缓存值。"""

    @staticmethod
    def test_probe_absent_constant_means_old_core(monkeypatch):
        """旧 core 无 LLM_SPAN_DECORATOR_CAPABILITY 常量：探测判为无能力。"""
        from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

        monkeypatch.delattr(OtelAgentHandler, "LLM_SPAN_DECORATOR_CAPABILITY", raising=False)
        monkeypatch.setattr(trace_compat, "_LLM_SPAN_DECORATOR_CAPABLE", None)
        assert trace_compat._llm_span_decorator_capable() is False

    @staticmethod
    def test_probe_capability_int_opens_gate(monkeypatch):
        from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

        monkeypatch.setattr(OtelAgentHandler, "LLM_SPAN_DECORATOR_CAPABILITY", 1, raising=False)
        monkeypatch.setattr(trace_compat, "_LLM_SPAN_DECORATOR_CAPABLE", None)
        assert trace_compat._llm_span_decorator_capable() is True

    @staticmethod
    @pytest.mark.parametrize("capable_int", [2, 3])
    def test_probe_higher_version_still_opens_gate(monkeypatch, capable_int):
        """版本化 int 契约：>= 1 均视为可消费（前向兼容）。"""
        from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

        monkeypatch.setattr(OtelAgentHandler, "LLM_SPAN_DECORATOR_CAPABILITY", capable_int, raising=False)
        monkeypatch.setattr(trace_compat, "_LLM_SPAN_DECORATOR_CAPABLE", None)
        assert trace_compat._llm_span_decorator_capable() is True

    @staticmethod
    @pytest.mark.parametrize("wrong", [0, -1, "1"])
    def test_probe_non_qualifying_values_keep_gate_closed(monkeypatch, wrong):
        """"1" 是已撤回合并线的字符串常量：str 与 int 比较抛 TypeError，
        按无能力处理（该线从未部署，探到也不该开门）。"""
        from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

        monkeypatch.setattr(OtelAgentHandler, "LLM_SPAN_DECORATOR_CAPABILITY", wrong, raising=False)
        monkeypatch.setattr(trace_compat, "_LLM_SPAN_DECORATOR_CAPABLE", None)
        assert trace_compat._llm_span_decorator_capable() is False


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


class TestIdentityPassThrough:
    """identity 归因键：新 core 透传，旧 core 丢 identity 保 span。"""

    @staticmethod
    def test_probe_reflects_core_signature(monkeypatch):
        """探测读真实签名：有 identity 参数判支持，无则不支持（缓存复位后）。"""
        mod_new = types.ModuleType("openjiuwen.core.session.tracer")

        def _decorate_new(model, session, identity=None):
            return model

        mod_new.decorate_model_with_trace = _decorate_new
        monkeypatch.setitem(sys.modules, "openjiuwen.core.session.tracer", mod_new)
        monkeypatch.setattr(trace_compat, "_DECORATOR_ACCEPTS_IDENTITY", None)
        assert trace_compat._decorator_accepts_identity() is True

        mod_old = types.ModuleType("openjiuwen.core.session.tracer")

        def _decorate_old(model, session):
            return model

        mod_old.decorate_model_with_trace = _decorate_old
        monkeypatch.setitem(sys.modules, "openjiuwen.core.session.tracer", mod_old)
        monkeypatch.setattr(trace_compat, "_DECORATOR_ACCEPTS_IDENTITY", None)
        assert trace_compat._decorator_accepts_identity() is False

    @staticmethod
    def test_identity_forwarded_when_core_accepts(gate_open, stub_decorate, monkeypatch):
        """新 core：identity 透传给装饰器（llm span 附业务归因键）。"""
        monkeypatch.setattr(trace_compat, "_DECORATOR_ACCEPTS_IDENTITY", True)
        identity = {"workflow_id": "wf-1", "agent_id": "app-1"}
        build_traced_model(object(), session=_StubSession(), identity=identity)
        assert stub_decorate[-1][2] is identity

    @staticmethod
    def test_old_core_drops_identity_keeps_spans(gate_open, stub_decorate, monkeypatch):
        """旧 core：丢 identity 仍装饰——span 全丢比缺身份键严重得多。"""
        monkeypatch.setattr(trace_compat, "_DECORATOR_ACCEPTS_IDENTITY", False)
        model = object()
        result = build_traced_model(model, session=_StubSession(), identity={"workflow_id": "wf-1"})
        assert result[0] == "decorated"
        assert stub_decorate[-1][2] is None

    @staticmethod
    def test_no_identity_no_extra_call_shape(gate_open, stub_decorate):
        """不传 identity：行为与旧签名完全一致（identity=None 不进装饰器）。"""
        build_traced_model(object(), session=_StubSession())
        assert stub_decorate[-1][2] is None


class TestWorkflowIdentity:
    """workflow_identity_from_session：只取 workflow_id，component_* 刻意不取。

    core 的组件壳分类器（_ambient_component_shell）以
    openjiuwen.workflow.component_id 判壳：llm span 带上它会在嵌套调用时被
    误当可合并壳（两次真实调用并成一个 span）。该约束在此钉死。
    """

    @staticmethod
    def test_session_workflow_id_extracted():
        session = type("S", (), {"get_workflow_id": staticmethod(lambda: "wf-biz-1")})()
        assert trace_compat.workflow_identity_from_session(session) == {"workflow_id": "wf-biz-1"}

    @staticmethod
    def test_component_keys_never_extracted():
        session = type(
            "S",
            (),
            {
                "get_workflow_id": staticmethod(lambda: "wf-1"),
                "get_component_id": staticmethod(lambda: "node-9"),
                "get_component_type": staticmethod(lambda: "LLMComponent"),
            },
        )()
        assert trace_compat.workflow_identity_from_session(session) == {"workflow_id": "wf-1"}

    @staticmethod
    def test_missing_empty_raising_yield_none():
        assert trace_compat.workflow_identity_from_session(None) is None
        empty = type("S", (), {"get_workflow_id": staticmethod(lambda: "")})()
        assert trace_compat.workflow_identity_from_session(empty) is None
        no_method = object()
        assert trace_compat.workflow_identity_from_session(no_method) is None

        class _Broken:
            @staticmethod
            def get_workflow_id():
                raise RuntimeError("no inner session")

        assert trace_compat.workflow_identity_from_session(_Broken()) is None


class TestResolveTraceIdentity:
    """resolve_trace_identity：显式注入优先，缺省从执行期 Session 提取。"""

    @staticmethod
    def test_explicit_injection_wins_over_session():
        component = type("C", (), {"_trace_identity": {"workflow_id": "wf-biz"}})()
        # 调试场景 Session 的 workflow_id 是 node_id：显式注入的业务 id 必须赢
        session = type("S", (), {"get_workflow_id": staticmethod(lambda: "node-1")})()
        assert trace_compat.resolve_trace_identity(component, session) == {"workflow_id": "wf-biz"}

    @staticmethod
    def test_session_fallback_via_component_attribute():
        session = type("S", (), {"get_workflow_id": staticmethod(lambda: "wf-run")})()
        component = type("C", (), {"_session": session})()
        assert trace_compat.resolve_trace_identity(component) == {"workflow_id": "wf-run"}

    @staticmethod
    def test_explicit_session_argument_preferred_over_attribute():
        session = type("S", (), {"get_workflow_id": staticmethod(lambda: "wf-arg")})()
        other = type("S", (), {"get_workflow_id": staticmethod(lambda: "wf-attr")})()
        component = type("C", (), {"_session": other})()
        assert trace_compat.resolve_trace_identity(component, session) == {"workflow_id": "wf-arg"}

    @staticmethod
    def test_nothing_available_returns_none():
        assert trace_compat.resolve_trace_identity(object()) is None


def _find_calls_by_name(tree, func_name: str):
    """按函数名收集 ast.Call 节点（显式循环，多判据不进推导式）。"""
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == func_name:
                calls.append(node)
    return calls


class TestSiteWiring:
    """裸 Model 构造点经 build_traced_model 接线（AST 契约）。"""

    SITES = {
        "jiuwen/extension/workflow_node/llm_chain.py": 1,
        # questioner 活副本（agent_runtime 包）：jiuwen/ 下的同名文件是死副本，
        # 不得接线（双接线=双计风险），此处钉住活副本唯一接线
        "agent_runtime/extension/workflow_node/questioner.py": 1,
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
    def test_dead_questioner_copy_stays_unwired():
        """jiuwen/ 下 questioner 是死副本：接线只落 agent_runtime 活副本，防回归。"""
        source = (
            _RUNTIME_ROOT / "jiuwen/extension/workflow_node/questioner.py"
        ).read_text(encoding="utf-8")
        assert _find_calls_by_name(ast.parse(source), "build_traced_model") == []

    @staticmethod
    def test_react_runner_stays_bare():
        """react 路径刻意不接线：多智能体同步桥线程下装饰会话的 ambient 上下文
        与执行 trace 树脱钩，产孤儿 llm span（缺参追问链复现）。react 覆盖
        待后续接线承接，接线回归时删本用例并恢复 SITES 条目。"""
        source = (
            _RUNTIME_ROOT / "agent_runtime/runner/react_agent_runner.py"
        ).read_text(encoding="utf-8")
        assert _find_calls_by_name(ast.parse(source), "build_traced_model") == []

    @staticmethod
    def test_definition_scoped_components_use_definition_session():
        """定义级组件（跨执行复用）的装饰会话一律 DEFINITION_SCOPED_SESSION_ID。

        组件实例由 IR 转换产生并被执行复用：装饰会话绑任一执行的会话 id，
        后续执行都会错归属（缓存模型保留首调会话的问题，检视 198236863）。
        """
        sites = [
            "jiuwen/extension/workflow_node/llm_chain.py",
            "agent_runtime/extension/workflow_node/questioner.py",
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
