# -*- coding: UTF-8 -*-
# pylint: disable=protected-access  # 单测需直接验证内部函数与成员
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""setup_otel_tracer 导入隔离/回退与 execution-scope 隔离单测。"""
import builtins
import threading
import time
from unittest.mock import MagicMock

import pytest
from opentelemetry import context as otel_context

from openjiuwen.core.session.tracer import TracerHandlerRegistry
from openjiuwen.core.session.tracer.handler import TracerHandlerName
from openjiuwen.core.session.tracer.tracer import Tracer
from openjiuwen.extensions.tracer_otel.config import OtelTracerConfig
from openjiuwen.extensions.tracer_otel.handler import OtelWorkflowHandler
from openjiuwen.extensions.tracer_otel.semconv import OJ_WORKFLOW_OUTPUTS
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import agent_runtime.observability.tracer_otel as tracer_otel_mod
from agent_runtime.observability.otel_handler_scope import (
    ExecutionScopedWorkflowHandler,
    attach_execution_scope,
    current_execution_scope,
    release_execution_scope,
)

_WF = TracerHandlerName.TRACER_WORKFLOW.value

_real_import = builtins.__import__


def _block_studio_import(name, gdict=None, ldict=None, fromlist=(), level=0):
    if (
        name == "agent_runtime.observability.tracer_otel_studio"
        and fromlist
        and "StudioOtelWorkflowHandler" in fromlist
    ):
        raise ImportError("simulated: upstream private symbol missing")
    return _real_import(name, gdict, ldict, fromlist, level)


def _block_scope_import(name, gdict=None, ldict=None, fromlist=(), level=0):
    if name == "agent_runtime.observability.otel_handler_scope":
        raise ImportError("simulated: execution scope module missing")
    return _real_import(name, gdict, ldict, fromlist, level)


@pytest.mark.asyncio
async def test_registers_scoped_handler_when_studio_unavailable(monkeypatch):
    """studio 子类不可用：仍注册 ExecutionScoped（子 handler 回退官方实现）。"""
    prev_enabled = tracer_otel_mod.settings.otel.enabled
    tracer_otel_mod.settings.otel.enabled = True
    monkeypatch.setattr(builtins, "__import__", _block_studio_import)
    try:
        TracerHandlerRegistry.clear()
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        tracer_otel_mod.setup_otel_tracer()
        handlers = TracerHandlerRegistry.get_workflow_handlers()
        assert isinstance(handlers.get("otel_workflow"), ExecutionScopedWorkflowHandler)
    finally:
        tracer_otel_mod.settings.otel.enabled = prev_enabled
        TracerHandlerRegistry.clear()


@pytest.mark.asyncio
async def test_fallbacks_to_official_handler_when_scope_unavailable(monkeypatch):
    """execution-scope 模块不可用：回退官方 OtelWorkflowHandler，OTel 不静默停用。"""
    prev_enabled = tracer_otel_mod.settings.otel.enabled
    tracer_otel_mod.settings.otel.enabled = True
    monkeypatch.setattr(builtins, "__import__", _block_scope_import)
    try:
        TracerHandlerRegistry.clear()
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        tracer_otel_mod.setup_otel_tracer()
        handlers = TracerHandlerRegistry.get_workflow_handlers()
        assert isinstance(handlers.get("otel_workflow"), OtelWorkflowHandler)
        assert not isinstance(
            handlers.get("otel_workflow"), ExecutionScopedWorkflowHandler
        )
    finally:
        tracer_otel_mod.settings.otel.enabled = prev_enabled
        TracerHandlerRegistry.clear()


def _block_extension_import(name, gdict=None, ldict=None, fromlist=(), level=0):
    """模拟未安装 openjiuwen[tracer-otel] 扩展。"""
    if name == "openjiuwen.extensions.tracer_otel":
        raise ImportError("simulated: tracer-otel extension not installed")
    return _real_import(name, gdict, ldict, fromlist, level)


class TestSetupOtelTracerSingleton:
    """setup_otel_tracer 幂等单例、关闭降级、扩展缺失降级。"""

    @pytest.fixture(autouse=True)
    def _clean_global_state(self, monkeypatch):
        """每个用例前的全局单例/注册表复原，避免用例间相互污染。"""
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        TracerHandlerRegistry.clear()
        yield
        TracerHandlerRegistry.clear()

    @staticmethod
    def test_returns_none_without_creating_tracer_when_disabled(monkeypatch):
        """OTEL_ENABLED=false：返回 None、不创建 tracer，get_otel_tracer 同步为 None。"""
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", False)
        init_mock = MagicMock()
        monkeypatch.setattr(
            "openjiuwen.extensions.tracer_otel.init_otel_tracer", init_mock
        )

        assert tracer_otel_mod.setup_otel_tracer() is None
        assert tracer_otel_mod.get_otel_tracer() is None
        init_mock.assert_not_called()

    @staticmethod
    def test_creates_once_and_returns_same_instance(monkeypatch):
        """首次调用创建 tracer 并按 settings 注册 handler；重复调用返回同一实例且只初始化一次。"""
        import openjiuwen.extensions.tracer_otel as extension

        fake_tracer = MagicMock(name="fake-otel-tracer")
        init_mock = MagicMock(return_value=fake_tracer)
        monkeypatch.setattr(extension, "init_otel_tracer", init_mock)
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)

        first = tracer_otel_mod.setup_otel_tracer()
        second = tracer_otel_mod.setup_otel_tracer()

        assert first is fake_tracer
        assert second is fake_tracer
        init_mock.assert_called_once()
        # 入参必须是按当前 settings 组装的配置，而不是默认值
        config = init_mock.call_args[0][0]
        assert isinstance(config, extension.OtelTracerConfig)
        assert config.service_name == tracer_otel_mod.settings.otel.service_name
        assert config.sample_rate == tracer_otel_mod.settings.otel.sample_rate
        assert tracer_otel_mod.get_otel_tracer() is fake_tracer
        assert "otel_agent" in TracerHandlerRegistry.get_agent_handlers()
        assert "otel_workflow" in TracerHandlerRegistry.get_workflow_handlers()

    @staticmethod
    def test_returns_none_when_extension_not_installed(monkeypatch):
        """扩展缺失（ImportError）：返回 None 而不是抛错，调用方跳过自建 span。"""
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)
        monkeypatch.setattr(builtins, "__import__", _block_extension_import)

        assert tracer_otel_mod.setup_otel_tracer() is None
        assert tracer_otel_mod.get_otel_tracer() is None

    @staticmethod
    def test_skips_creation_when_handlers_already_registered(monkeypatch):
        """handler 已注册（进程内重复初始化）：直接返回、不再创建 tracer 与重复注册。"""
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)
        init_mock = MagicMock()
        monkeypatch.setattr(
            "openjiuwen.extensions.tracer_otel.init_otel_tracer", init_mock
        )
        monkeypatch.setattr(
            TracerHandlerRegistry,
            "get_agent_handlers",
            classmethod(lambda cls: {"otel_agent": object()}),
        )

        assert tracer_otel_mod.setup_otel_tracer() is None
        init_mock.assert_not_called()


class TestSetupOtelTracerThreadSafety:
    """setup_otel_tracer 的双层检查锁：并发只创建一次、已缓存时不进锁也不重建。"""

    @pytest.fixture(autouse=True)
    def _clean_global_state(self, monkeypatch):
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        TracerHandlerRegistry.clear()
        yield
        TracerHandlerRegistry.clear()

    @staticmethod
    def test_create_runs_once_under_concurrent_calls(monkeypatch):
        """8 线程同时调用：_create_otel_tracer 只执行一次，所有调用方拿到同一实例。"""
        fake_tracer = MagicMock(name="thread-safe-tracer")
        create_calls = []
        counter_lock = threading.Lock()

        def fake_create():
            with counter_lock:
                create_calls.append(1)
            # 放大竞态窗口：若没有锁，其余线程会在这里再次进入创建逻辑
            time.sleep(0.05)
            tracer_otel_mod._otel_tracer = fake_tracer
            return fake_tracer

        monkeypatch.setattr(tracer_otel_mod, "_create_otel_tracer", fake_create)

        thread_count = 8
        barrier = threading.Barrier(thread_count)
        results = []
        errors = []

        def worker():
            try:
                barrier.wait(timeout=10)
                results.append(tracer_otel_mod.setup_otel_tracer())
            except BaseException as exc:  # noqa: BLE001 - 线程异常必须回传主线程
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert errors == []
        assert len(results) == thread_count
        assert len(create_calls) == 1
        assert all(result is fake_tracer for result in results)
        assert tracer_otel_mod.get_otel_tracer() is fake_tracer

    @staticmethod
    def test_cached_tracer_short_circuits_without_creating(monkeypatch):
        """已缓存实例：直接返回缓存并跳过创建（双层检查的外层快速路径）。"""
        cached = MagicMock(name="cached-tracer")
        create_mock = MagicMock(name="_create_otel_tracer")
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", cached)
        monkeypatch.setattr(tracer_otel_mod, "_create_otel_tracer", create_mock)

        assert tracer_otel_mod.setup_otel_tracer() is cached
        assert tracer_otel_mod.setup_otel_tracer() is cached
        create_mock.assert_not_called()


class TestExecutionScopedWorkflowIsolation:
    """ExecutionScopedWorkflowHandler：同 workflow_id、不同 exec scope 互不踩 span。"""

    @pytest.fixture(autouse=True)
    def _clean_global_state(self, monkeypatch):
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        TracerHandlerRegistry.clear()
        yield
        TracerHandlerRegistry.clear()

    @staticmethod
    def _register_scoped(service_name: str):
        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        otel = provider.get_tracer(service_name)
        try:
            cfg = OtelTracerConfig()
        except TypeError:
            cfg = OtelTracerConfig(service_name=service_name)
        dispatcher = ExecutionScopedWorkflowHandler(otel, cfg)
        TracerHandlerRegistry.register_handler("otel_workflow", dispatcher)
        return exporter, dispatcher

    @staticmethod
    def test_setup_registers_execution_scoped_handler(monkeypatch):
        import openjiuwen.extensions.tracer_otel as extension

        fake_tracer = MagicMock(name="scoped-setup-tracer")
        monkeypatch.setattr(
            extension, "init_otel_tracer", MagicMock(return_value=fake_tracer)
        )
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)

        assert tracer_otel_mod.setup_otel_tracer() is fake_tracer
        handler = TracerHandlerRegistry.get_workflow_handlers().get("otel_workflow")
        assert isinstance(handler, ExecutionScopedWorkflowHandler)

    @staticmethod
    @pytest.mark.asyncio
    async def test_different_scopes_isolate_same_invoke_id_via_trigger():
        """共享同一 registry 分发器 + Tracer.trigger：不同 exec scope 下同 WF/COMP 不串号。"""
        wf_id = "wf_same"
        comp_id = "node_http"
        exporter, dispatcher = (
            TestExecutionScopedWorkflowIsolation._register_scoped("scope-trigger")
        )

        t_a = Tracer(session_id="sess-A", trace_id="trace-A")
        t_a.init()
        t_b = Tracer(session_id="sess-B", trace_id="trace-B")
        t_b.init()
        # 仍是同一个分发器实例（不再 monkeypatch Tracer.init）
        assert t_a._workflow_handlers["otel_workflow"] is dispatcher
        assert t_b._workflow_handlers["otel_workflow"] is dispatcher

        root_meta = {"workflow_id": wf_id, "workflow_name": "wf"}
        comp_meta = {
            "workflow_id": wf_id,
            "component_id": comp_id,
            "component_type": "FlowApi",
            "component_name": "http_node",
        }

        token_a = attach_execution_scope(
            "exec-A", trace_id="trace-A", session_id="sess-A"
        )
        try:
            assert current_execution_scope() == "exec-A"
            await t_a.trigger(
                _WF, "on_call_start", invoke_id=wf_id, metadata=root_meta,
                inputs={"q": "A"}, parent_node_id="",
            )
            await t_a.trigger(
                _WF, "on_call_start", invoke_id=comp_id, metadata=comp_meta,
                inputs={"q": "A"}, parent_node_id=wf_id,
            )
            sub_a = dispatcher._handlers["exec-A"]
            a_state_id = id(sub_a._span_manager.get(comp_id))
            assert a_state_id
        finally:
            otel_context.detach(token_a)

        token_b = attach_execution_scope(
            "exec-B", trace_id="trace-B", session_id="sess-B"
        )
        try:
            await t_b.trigger(
                _WF, "on_call_start", invoke_id=wf_id, metadata=root_meta,
                inputs={"q": "B"}, parent_node_id="",
            )
            await t_b.trigger(
                _WF, "on_call_start", invoke_id=comp_id, metadata=comp_meta,
                inputs={"q": "B"}, parent_node_id=wf_id,
            )
            sub_b = dispatcher._handlers["exec-B"]
            assert sub_b is not sub_a
            assert id(sub_b._span_manager.get(comp_id)) != a_state_id
            # A 的状态仍在（不同子 handler）
            assert id(sub_a._span_manager.get(comp_id)) == a_state_id
        finally:
            otel_context.detach(token_b)

        token_a = attach_execution_scope("exec-A", trace_id="trace-A", session_id="sess-A")
        try:
            await t_a.trigger(
                _WF, "on_call_done", invoke_id=comp_id,
                outputs={"node_output": "A_RESULT"}, parent_node_id=wf_id,
            )
            assert sub_a._span_manager.get(comp_id) is None
            assert sub_b._span_manager.get(comp_id) is not None
        finally:
            otel_context.detach(token_a)

        token_b = attach_execution_scope("exec-B", trace_id="trace-B", session_id="sess-B")
        try:
            await t_b.trigger(
                _WF, "on_call_done", invoke_id=comp_id,
                outputs={"node_output": "B_RESULT"}, parent_node_id=wf_id,
            )
            await t_b.trigger(
                _WF, "on_call_done", invoke_id=wf_id,
                outputs={"out": "B"}, parent_node_id="",
            )
        finally:
            otel_context.detach(token_b)

        token_a = attach_execution_scope("exec-A", trace_id="trace-A", session_id="sess-A")
        try:
            await t_a.trigger(
                _WF, "on_call_done", invoke_id=wf_id,
                outputs={"out": "A"}, parent_node_id="",
            )
        finally:
            otel_context.detach(token_a)
            release_execution_scope("exec-A")
            release_execution_scope("exec-B")

        finished = list(exporter.get_finished_spans())
        comp_spans = [s for s in finished if s.name.startswith("component.")]
        assert len(comp_spans) == 2
        output_attrs = {
            (span.attributes or {}).get(OJ_WORKFLOW_OUTPUTS)
            for span in comp_spans
        }
        assert len([attr for attr in output_attrs if attr]) == 2

    @staticmethod
    def test_attach_stamps_identity_onto_scoped_child():
        """attach 后 stamp：子 handler 拿到本次 trace/session，不被并发 pending 覆盖。"""
        _, dispatcher = TestExecutionScopedWorkflowIsolation._register_scoped(
            "scope-stamp"
        )
        # 模拟 Tracer.init 在 unscoped 下改写 pending（并发最后写入）
        dispatcher.set_trace_id("trace-stale")
        dispatcher.set_session_id("sess-stale")

        token = attach_execution_scope(
            "exec-1", trace_id="trace-1", session_id="sess-1"
        )
        try:
            child = dispatcher._handlers["exec-1"]
            assert child._trace_id == "trace-1"
            assert child._session_id == "sess-1"
        finally:
            otel_context.detach(token)
            release_execution_scope("exec-1", force=True)

    @staticmethod
    @pytest.mark.asyncio
    async def test_release_preserves_live_handler_for_resume():
        """有 live span 时 release 不 pop；同 exec_id 再 attach 复用子 handler 与 cached root。"""
        wf_id = "wf_resume"
        exporter, dispatcher = (
            TestExecutionScopedWorkflowIsolation._register_scoped("scope-resume")
        )
        tracer = Tracer(session_id="sess-r", trace_id="trace-r")
        tracer.init()
        root_meta = {"workflow_id": wf_id, "workflow_name": "wf"}

        token = attach_execution_scope(
            "exec-r", trace_id="trace-r", session_id="sess-r"
        )
        try:
            await tracer.trigger(
                _WF, "on_call_start", invoke_id=wf_id, metadata=root_meta,
                inputs={"q": "ask"}, parent_node_id="",
            )
            child = dispatcher._handlers["exec-r"]
            cached = child._cached_root_ctx
            assert cached is not None
            assert child._layer_root_spans
        finally:
            otel_context.detach(token)

        # 模拟 QA 中断 / 客户端关闭：finally 调用 release，但不得拆掉 live 状态
        assert release_execution_scope("exec-r") is False
        assert "exec-r" in dispatcher._handlers
        assert dispatcher._handlers["exec-r"] is child
        assert child._cached_root_ctx is cached

        # resume：同 exec/trace 再 attach，必须复用原子 handler 与 cached root
        token = attach_execution_scope(
            "exec-r", trace_id="trace-r", session_id="sess-r"
        )
        try:
            assert dispatcher._handlers["exec-r"] is child
            assert child._cached_root_ctx is cached
            await tracer.trigger(
                _WF, "on_call_done", invoke_id=wf_id,
                outputs={"out": "done"}, parent_node_id="",
            )
        finally:
            otel_context.detach(token)

        assert release_execution_scope("exec-r") is True
        assert "exec-r" not in dispatcher._handlers
        finished = list(exporter.get_finished_spans())
        assert any(s.name == wf_id for s in finished)
        # 只有一条 root（未被 release 提前 end 后再造一条）
        assert len([s for s in finished if s.name == wf_id]) == 1

@pytest.mark.asyncio
async def test_run_blocking_forwards_execution_id(monkeypatch):
    """非流式路径须把 API 层 execution_id 透传给 run_streaming（隔离 scope）。"""
    from agent_runtime.runner.workflow_runner import WorkflowRunner

    runner = WorkflowRunner(MagicMock())
    seen = {}

    async def fake_stream_gen(req, execution_id=None, env_scope=None):
        seen["execution_id"] = execution_id
        seen["env_scope"] = env_scope
        yield {"event": "done", "data": {"answer": "ok"}}

    monkeypatch.setattr(runner, "run_streaming", fake_stream_gen)
    text = await runner.run_blocking(
        MagicMock(), execution_id="exec-unique", env_scope={"k": 1}
    )
    assert text == "ok"
    assert seen["execution_id"] == "exec-unique"
    assert seen["env_scope"] == {"k": 1}

