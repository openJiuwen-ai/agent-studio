# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Tests for trace_compat.build_traced_model — 裸 Model 装饰工厂。

契约：
- 本线要求配套新版 core（identity 参数 + handler 数据面消费），能力/
  签名探测降级已按 2026-11-06 决策撤除：装饰无条件进行，identity 有则
  必透传；运行期任何失败（导入 / 建会话 / 装饰抛错，含旧 core 上
  identity 参数缺失引发的 TypeError）整体降级返回裸模型，绝不阻断业务；
- session 显式传入则直接复用；否则新建轻量 agent session：定义级产物
  （跨执行复用的组件/模型）落 DEFINITION_SCOPED_SESSION_ID 且不绑构建期
  请求 trace，请求级场景（react 每执行新建）透传当次会话 id、trace 走
  请求上下文；
- identity 归因：透传给装饰器（业务 workflow_id/agent_id 附到独立/子
  llm span，write-if-absent）；
- 五个裸 Model 构造点全部经工厂接线，资源注册路径（get_model 已装饰）除外；
  react 路径刻意不接线（多智能体同步桥线程下装饰会话与执行 trace 树脱钩
  产孤儿 llm span，缺参追问链已复现），由独立用例钉死防回归。
"""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider

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


@pytest.fixture
def stub_decorate(monkeypatch):
    calls = []

    def _decorate(model, session, identity=None):
        calls.append((model, session, identity))
        return ("decorated", model, session)

    import openjiuwen.core.session.tracer as core_tracer

    monkeypatch.setattr(core_tracer, "decorate_model_with_trace", _decorate, raising=False)
    return calls


class TestDecorate:
    @staticmethod
    def test_decorates_model_with_fresh_session(stub_decorate, monkeypatch):
        """无条件装饰：新建轻量会话并装饰，session_id 透传。"""
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
    def test_explicit_session_reused_no_fresh_one(stub_decorate, monkeypatch):
        """显式传入 session：直接复用，不再新建轻量会话。"""
        monkeypatch.setattr(
            trace_compat,
            "create_agent_session_with_trace",
            lambda *a, **k: pytest.fail("explicit session must be reused as-is"),
        )
        model, session = object(), _StubSession()
        result = build_traced_model(model, session=session)
        assert result[2] is session


class TestDefinitionScopedTrace:
    """定义级路径调用期解析：构建期零会话创建，会话延迟到首调。"""

    @staticmethod
    def test_definition_scoped_build_defers_session_creation(stub_decorate, monkeypatch):
        """定义级产物返回调用期代理，构建期不建任何会话（绑首请求会错归属）。"""

        def _fail_create(*args, **kwargs):
            pytest.fail("definition-scoped build must not create any session")

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _fail_create)
        result = build_traced_model(object(), session_id=trace_compat.DEFINITION_SCOPED_SESSION_ID)
        assert isinstance(result, trace_compat._CallScopedTracedModel)
        assert stub_decorate == []

    @staticmethod
    def test_request_scoped_session_keeps_ambient_trace(stub_decorate, monkeypatch):
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


class _AmbientShellSpan:
    """带 openjiuwen.session_id 属性的真 SDK span（作 ambient 壳，随进随出）。

    OTel API 的 get_current_span 按 isinstance(span, Span) 校验，duck-typed
    假 span 会被判 INVALID——必须用真 SDK span 才与生产同构。
    """

    _tracer = TracerProvider().get_tracer("test-ambient-shell")

    def __init__(self, session_id: str, with_session: bool = True):
        attrs = {trace_compat._OJ_SESSION_ID_ATTR: session_id} if with_session else None
        self._cm = self._tracer.start_as_current_span(f"shell.{session_id}", attributes=attrs)

    def __enter__(self):
        self._cm.__enter__()
        return self

    def __exit__(self, *exc):
        return self._cm.__exit__(*exc)


class _DecoratedStub:
    """装饰器替身的返回物：记录当次调用的路径/会话/身份。"""

    def __init__(self, session, identity, calls):
        self._session = session
        self._identity = identity
        self._calls = calls

    async def invoke(self, *args, **kwargs):
        self._calls.append(("invoke", self._session, self._identity))
        return "decorated-ok"

    async def stream(self, *args, **kwargs):
        self._calls.append(("stream", self._session, self._identity))
        for chunk in ("c1", "c2"):
            yield chunk


@pytest.fixture
def call_scope(monkeypatch):
    """调用期路径替身：捕获会话工厂/装饰器入参，装饰返回可调用替身。"""
    import openjiuwen.core.session.tracer as core_tracer

    state = {"created": [], "decorated": [], "calls": []}

    def _create(session_id=None, trace_id=None, **kwargs):
        state["created"].append(
            {"session_id": session_id, "trace_id": trace_id, "kwargs": kwargs}
        )
        return _StubSession()

    def _decorate(model, session, identity=None):
        state["decorated"].append(
            {"model": model, "session": session, "identity": identity}
        )
        return _DecoratedStub(session, identity, state["calls"])

    monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _create)
    monkeypatch.setattr(core_tracer, "decorate_model_with_trace", _decorate, raising=False)
    return state


class TestCallScopedInheritance:
    """定义级路径调用期解析：llm span 会话身份继承 ambient 上层 span。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_invoke_inherits_ambient_session_and_trace(call_scope):
        """壳 span 带 openjiuwen.session_id：当次调用建会话继承其会话/trace id。"""
        with _AmbientShellSpan("conv-9"):
            ambient_trace = otel_trace.get_current_span().get_span_context().trace_id
            proxy = build_traced_model(object())
            assert await proxy.invoke("q", temperature=0.7) == "decorated-ok"
        assert len(call_scope["created"]) == 1
        assert call_scope["created"][0]["session_id"] == "conv-9"
        assert call_scope["created"][0]["trace_id"] == format(ambient_trace, "032x")
        assert call_scope["calls"][0][0] == "invoke"

    @staticmethod
    @pytest.mark.asyncio
    async def test_no_ambient_falls_back_to_definition_sentinel(call_scope):
        """无 ambient 父（单组件调试等）：退哨兵会话、不绑请求 trace、只建一次。"""
        proxy = build_traced_model(
            object(), session_id=trace_compat.DEFINITION_SCOPED_SESSION_ID
        )
        assert await proxy.invoke("q1") == "decorated-ok"
        assert await proxy.invoke("q2") == "decorated-ok"
        assert len(call_scope["created"]) == 1
        assert call_scope["created"][0]["session_id"] == trace_compat.DEFINITION_SCOPED_SESSION_ID
        assert call_scope["created"][0]["trace_id"] is trace_compat._DEFINITION_NO_TRACE

    @staticmethod
    @pytest.mark.asyncio
    async def test_ambient_span_without_session_attr_uses_sentinel(call_scope):
        """有效父 span 但无会话属性：退哨兵，不臆造归属。"""
        with _AmbientShellSpan("ignored", with_session=False):
            proxy = build_traced_model(object())
            await proxy.invoke("q")
        assert call_scope["created"][0]["session_id"] == trace_compat.DEFINITION_SCOPED_SESSION_ID

    @staticmethod
    @pytest.mark.asyncio
    async def test_same_ambient_scope_decorated_once(call_scope):
        """同 (会话, trace) 连续调用命中缓存：只装饰一次。"""
        with _AmbientShellSpan("conv-9"):
            proxy = build_traced_model(object())
            await proxy.invoke("a")
            await proxy.invoke("b")
        assert len(call_scope["decorated"]) == 1

    @staticmethod
    @pytest.mark.asyncio
    async def test_distinct_scopes_attributed_separately(call_scope):
        """同一缓存模型在不同会话的执行各自归属（跨请求不错归）。"""
        proxy = build_traced_model(object())
        with _AmbientShellSpan("conv-1"):
            await proxy.invoke("a")
        with _AmbientShellSpan("conv-2"):
            await proxy.invoke("b")
        assert [c["session_id"] for c in call_scope["created"]] == ["conv-1", "conv-2"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_stream_routes_through_decorated_stream(call_scope):
        """stream 路径同走调用期装饰（usage/ttft 由 core 流式包装计）。"""
        with _AmbientShellSpan("conv-s"):
            proxy = build_traced_model(object())
            chunks = [chunk async for chunk in proxy.stream("q")]
        assert chunks == ["c1", "c2"]
        assert call_scope["calls"][0][0] == "stream"
        assert call_scope["created"][0]["session_id"] == "conv-s"

    @staticmethod
    @pytest.mark.asyncio
    async def test_user_id_read_at_call_time(call_scope):
        """user_id 逐调用取执行期播种值（显式传入优先），调用方字典不被改写。"""
        caller_identity = {"workflow_id": "wf-1"}
        token = trace_compat._CURRENT_USER_ID.set("u-77")
        try:
            with _AmbientShellSpan("conv-u"):
                proxy = build_traced_model(object(), identity=caller_identity)
                await proxy.invoke("q")
        finally:
            trace_compat._CURRENT_USER_ID.reset(token)
        captured = call_scope["decorated"][0]["identity"]
        assert captured["user_id"] == "u-77"
        assert captured["workflow_id"] == "wf-1"
        assert "user_id" not in caller_identity

    @staticmethod
    def test_attribute_passthrough_to_bare_model(call_scope):
        """未覆写属性透传裸模型（与 core _TraceProxy 同形）。"""

        class _Bare:
            def __init__(self):
                self.config = type("Cfg", (), {"model_name": "M-1"})()

        proxy = build_traced_model(_Bare())
        assert proxy.config.model_name == "M-1"

    @staticmethod
    @pytest.mark.asyncio
    async def test_fallback_rebuilt_per_user(call_scope):
        """无父路径装饰产物按调用期用户分桶：换用户重建，同用户复用。"""
        proxy = build_traced_model(object())

        async def invoke_as(user):
            token = trace_compat._CURRENT_USER_ID.set(user)
            try:
                await proxy.invoke("q")
            finally:
                trace_compat._CURRENT_USER_ID.reset(token)

        await invoke_as("u-1")
        await invoke_as("u-1")
        await invoke_as("u-2")
        # 首个用户的装饰产物绝不复用到第二个用户头上（身份串染防护）
        assert [d["identity"].get("user_id") for d in call_scope["decorated"]] == [
            "u-1",
            "u-2",
        ]
        assert len(call_scope["created"]) == 2

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_decorated_product_tolerated(call_scope, monkeypatch):
        """同步产物兼容：invoke 非 awaitable 直返、stream 同步可迭代直代。"""
        import openjiuwen.core.session.tracer as core_tracer

        def _sync_invoke(*args, **kwargs):
            return "sync-ok"

        def _sync_stream(*args, **kwargs):
            yield "s1"
            yield "s2"

        monkeypatch.setattr(
            core_tracer,
            "decorate_model_with_trace",
            lambda model, session, identity=None: SimpleNamespace(
                invoke=_sync_invoke, stream=_sync_stream
            ),
            raising=False,
        )
        proxy = build_traced_model(object())
        assert await proxy.invoke("q") == "sync-ok"
        assert [chunk async for chunk in proxy.stream("q")] == ["s1", "s2"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_falsy_session_id_stays_definition_scoped(call_scope):
        """空串等 falsy 会话 id 与缺省同落定义级路径（旧 falsy→哨兵语义）。"""
        proxy = build_traced_model(object(), session_id="")
        assert isinstance(proxy, trace_compat._CallScopedTracedModel)
        await proxy.invoke("q")
        assert call_scope["created"][0]["session_id"] == trace_compat.DEFINITION_SCOPED_SESSION_ID


class TestDegrade:
    @staticmethod
    def test_decorate_entry_missing_returns_bare(monkeypatch):
        """core 无 decorate_model_with_trace 入口：降级返回裸模型。"""
        import openjiuwen.core.session.tracer as core_tracer

        monkeypatch.delattr(core_tracer, "decorate_model_with_trace", raising=False)
        model = object()
        assert build_traced_model(model) is model

    @staticmethod
    @pytest.mark.asyncio
    async def test_call_time_session_failure_degrades_to_bare(stub_decorate, monkeypatch):
        """定义级路径轻量会话创建抛错：构建照常返代理，逐调用退裸模型直调。"""

        def _explode(*args, **kwargs):
            raise RuntimeError("session factory down")

        monkeypatch.setattr(trace_compat, "create_agent_session_with_trace", _explode)

        class _BareModel:
            async def invoke(self, *args, **kwargs):
                return "bare-ok"

        proxy = build_traced_model(_BareModel())
        assert isinstance(proxy, trace_compat._CallScopedTracedModel)
        assert await proxy.invoke("q") == "bare-ok"
        assert stub_decorate == []


class TestIdentityPassThrough:
    """identity 归因键：core 支持时有则必透传。"""

    @staticmethod
    def test_identity_forwarded_unconditionally(stub_decorate):
        """identity 原样透传给装饰器（llm span 附业务归因键与调用事实）。"""
        identity = {"workflow_id": "wf-1", "agent_id": "app-1"}
        build_traced_model(object(), session=_StubSession(), identity=identity)
        assert stub_decorate[-1][2] is identity

    @staticmethod
    def test_old_core_identity_type_error_degrades_to_bare(stub_decorate, monkeypatch):
        """运行期 TypeError（签名接受 identity 但执行抛错）→ 整体降级返回
        裸模型，不阻断模型创建——与签名能力门控（TestCapabilityGate）互补：
        门控管旧签名，本用例管运行期失败。
        """
        import openjiuwen.core.session.tracer as core_tracer

        def _decorate_old_signature(model, session, identity=None):
            raise TypeError(
                "decorate_model_with_trace() got an unexpected keyword argument 'identity'"
            )

        monkeypatch.setattr(
            core_tracer, "decorate_model_with_trace", _decorate_old_signature, raising=False
        )
        model = object()
        assert build_traced_model(model, session=_StubSession(), identity={"workflow_id": "wf-1"}) is model

    @staticmethod
    def test_no_identity_no_extra_call_shape(stub_decorate):
        """不传 identity：行为与旧签名完全一致（identity=None 不进装饰器）。"""
        build_traced_model(object(), session=_StubSession())
        assert stub_decorate[-1][2] is None


class TestCapabilityGate:
    """新 studio × 旧 core 组合兼容：identity 参数按签名能力门控。

    旧 core 装饰器无 identity 参数（且无 **kwargs），带上传即 TypeError。
    门控退既有两参调用——普通 llm span 照产（不退裸模型、不刷告警），
    四象限最差维持现状、绝不崩。
    """

    @staticmethod
    def test_old_signature_decorates_without_identity(monkeypatch):
        """旧 core 两参装饰器：identity 事实在手上也退两参调用，产出普通
        span（非裸模型）。
        """
        import openjiuwen.core.session.tracer as core_tracer

        calls = []

        def _decorate_two_arg(model, session):
            calls.append((model, session))
            return ("decorated", model, session)

        monkeypatch.setattr(
            core_tracer, "decorate_model_with_trace", _decorate_two_arg, raising=False
        )
        model = object()
        result = build_traced_model(
            model, session=_StubSession(), identity={"workflow_id": "wf-1"}
        )
        assert len(calls) == 1, "必须恰好装饰一次"
        assert calls[0][0] is model
        assert result == ("decorated", model, calls[0][1]), "两参调用照常装饰"

    @staticmethod
    def test_var_keyword_decorator_accepts_identity(monkeypatch):
        """**kwargs 形签名（无显式 identity 参数）同样放行透传。"""
        import openjiuwen.core.session.tracer as core_tracer

        seen = {}

        def _decorate(model, session, **kwargs):
            seen.update(kwargs)
            return model

        monkeypatch.setattr(core_tracer, "decorate_model_with_trace", _decorate, raising=False)
        identity = {"workflow_id": "wf-2"}
        build_traced_model(object(), session=_StubSession(), identity=identity)
        assert seen.get("identity") is identity

    @staticmethod
    def test_probe_accepts_variants_and_caches():
        """签名探测：显式/keyword-only/**kwargs 放行，无则拒；不可签名
        保守拒；结果进进程级缓存（绑定方法归一到底层函数，键唯一）。
        """
        def _plain(model, session, identity=None):
            return model

        def _kwonly(model, session=None, *, identity=None):
            return model

        def _no_identity(model, session=None):
            return model

        class _Mgr:
            # 旧 core resource_mgr.get_model 形态：keyword-only、无 identity。
            # classmethod 而非 staticmethod：取绑定对象才走 __func__ 归一路径
            @classmethod
            def get_model(cls, model_id=None, *, tag=None, session=None):
                return None

        assert trace_compat.callable_accepts_kwarg(_plain, "identity") is True
        assert trace_compat.callable_accepts_kwarg(_kwonly, "identity") is True
        assert trace_compat.callable_accepts_kwarg(_no_identity, "identity") is False
        assert trace_compat.callable_accepts_kwarg(None, "identity") is False

        bound = _Mgr().get_model
        assert trace_compat.callable_accepts_kwarg(bound, "identity") is False
        # 归一后缓存键是底层函数，绑定对象不重复建键
        underlying = getattr(_Mgr.get_model, "__func__")
        assert (underlying, "identity") in trace_compat._KWARG_SUPPORT_CACHE
        assert (_plain, "identity") in trace_compat._KWARG_SUPPORT_CACHE


class TestUserFactsSeeding:
    """user_id 播种：source_metadata 随会话透传 + ContextVar 同源记录。"""

    @staticmethod
    def test_seeded_source_metadata_passthrough_and_ambient_record(monkeypatch):
        """带 user_id 的 source_metadata：原样透传给 core 并记录 ambient 值。"""
        seen = {}

        def _fake_create(session_id=None, **kwargs):
            seen.update(kwargs)
            return "SESSION"

        monkeypatch.setattr(trace_compat, "_create_agent_session", _fake_create)
        try:
            trace_compat.create_agent_session_with_trace(
                session_id="s1", source_metadata={"user_id": "u-1"}
            )
            assert seen["source_metadata"] == {"user_id": "u-1"}
            assert trace_compat.current_user_id() == "u-1"
        finally:
            trace_compat._CURRENT_USER_ID.set(None)

    @staticmethod
    def test_absent_or_empty_user_id_never_seeds(monkeypatch):
        """未携带 / user_id 为空：不注入空键、不播种（不覆盖既有值）。"""
        seen = {}

        def _fake_create(session_id=None, **kwargs):
            seen.update(kwargs)
            return "SESSION"

        monkeypatch.setattr(trace_compat, "_create_agent_session", _fake_create)
        trace_compat.create_agent_session_with_trace(session_id="s1")
        assert "source_metadata" not in seen
        trace_compat.create_agent_session_with_trace(session_id="s2", source_metadata={})
        assert seen.get("source_metadata") == {}
        assert trace_compat.current_user_id() is None

    @staticmethod
    def test_seeded_value_survives_later_bare_session(monkeypatch):
        """播种后 per-call 轻量会话（不带 source_metadata）不得抹掉 ambient 值。"""

        def _fake_create(session_id=None, **kwargs):
            return "SESSION"

        monkeypatch.setattr(trace_compat, "_create_agent_session", _fake_create)
        try:
            trace_compat.create_agent_session_with_trace(
                session_id="s1", source_metadata={"user_id": "u-1"}
            )
            trace_compat.create_agent_session_with_trace(session_id="s2")
            assert trace_compat.current_user_id() == "u-1"
        finally:
            trace_compat._CURRENT_USER_ID.set(None)


RUNNER_SEED_SITES = [
    "agent_runtime/runner/controller_runner.py",
    "agent_runtime/runner/react_agent_runner.py",
]


class TestRunnerUserIdSeeding:
    """两 runner 建会话处播种 req.user_id（钉死，防接线回退）。"""

    @staticmethod
    def test_both_runners_seed_user_id_into_source_metadata():
        for rel_path in RUNNER_SEED_SITES:
            source = (_RUNTIME_ROOT / rel_path).read_text(encoding="utf-8")
            assert (
                'source_metadata={"user_id": req.user_id} if req.user_id else None'
                in source
            ), f"{rel_path}: runner must seed user_id into session source_metadata"


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
        待后续接线承接，接线回归时删本用例并恢复 SITES 条目。
        """
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
