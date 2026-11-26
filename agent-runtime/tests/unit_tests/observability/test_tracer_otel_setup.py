# -*- coding: UTF-8 -*-
# pylint: disable=protected-access  # 单测需直接验证内部函数与成员
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""setup_otel_tracer 导入隔离/回退单测。

M1 评审关注点固化：StudioOtelWorkflowHandler 子类导入失败（openjiuwen 升级后
私有符号缺失/改名）时，回退官方 OtelWorkflowHandler，OTel 不静默停用。
"""
import builtins
import threading
import time
from unittest.mock import MagicMock

import pytest

from openjiuwen.core.session.tracer import TracerHandlerRegistry
from openjiuwen.core.session.tracer.handler import TracerHandlerName
from openjiuwen.core.session.tracer.tracer import Tracer
from openjiuwen.extensions.tracer_otel.config import OtelTracerConfig
from openjiuwen.extensions.tracer_otel.handler import (
    OtelAgentHandler,
    OtelWorkflowHandler,
)
from openjiuwen.extensions.tracer_otel.semconv import OJ_WORKFLOW_OUTPUTS
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import agent_runtime.observability.tracer_otel as tracer_otel_mod

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


@pytest.mark.asyncio
async def test_fallbacks_to_official_handler_when_studio_unavailable(monkeypatch):
    prev_enabled = tracer_otel_mod.settings.otel.enabled
    tracer_otel_mod.settings.otel.enabled = True
    monkeypatch.setattr(builtins, "__import__", _block_studio_import)
    try:
        TracerHandlerRegistry.clear()
        tracer_otel_mod.setup_otel_tracer()
        handlers = TracerHandlerRegistry.get_workflow_handlers()
        assert isinstance(handlers.get("otel_workflow"), OtelWorkflowHandler)
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
        monkeypatch.setattr(tracer_otel_mod, "_per_tracer_isolation_installed", False)
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
        monkeypatch.setattr(tracer_otel_mod, "_per_tracer_isolation_installed", False)
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


class TestPerTracerHandlerIsolation:
    """Registry 模板单例 + Tracer.init 克隆：同 workflow_id 并发互不踩 span 状态。"""

    @staticmethod
    def _restore_tracer_init() -> None:
        """还原 Tracer.init；直接写模块全局，避免 monkeypatch 在 teardown 把 _orig 还原回来。"""
        orig = tracer_otel_mod._orig_tracer_init
        if orig is not None:
            Tracer.init = orig  # type: ignore[method-assign]
            tracer_otel_mod._orig_tracer_init = None
        tracer_otel_mod._per_tracer_isolation_installed = False

    @pytest.fixture(autouse=True)
    def _clean_global_state(self, monkeypatch):
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        self._restore_tracer_init()
        TracerHandlerRegistry.clear()
        yield
        TracerHandlerRegistry.clear()
        self._restore_tracer_init()

    @staticmethod
    def test_tracer_init_clones_registered_otel_handlers():
        """两个 Tracer.init 后持有不同 handler 实例，registry 模板保持不变。"""
        otel = TracerProvider().get_tracer("isolation-unit")
        try:
            cfg = OtelTracerConfig()
        except TypeError:
            cfg = OtelTracerConfig(service_name="isolation-unit")

        template_agent = OtelAgentHandler(otel, cfg)
        template_wf = OtelWorkflowHandler(otel, cfg)
        TracerHandlerRegistry.register_handler("otel_agent", template_agent)
        TracerHandlerRegistry.register_handler("otel_workflow", template_wf)
        tracer_otel_mod._install_per_tracer_handler_isolation()

        t1 = Tracer(session_id="s1", trace_id="trace-1")
        t1.init()
        t2 = Tracer(session_id="s2", trace_id="trace-2")
        t2.init()

        h1 = t1._workflow_handlers["otel_workflow"]
        h2 = t2._workflow_handlers["otel_workflow"]
        assert h1 is not template_wf
        assert h2 is not template_wf
        assert h1 is not h2
        assert t1._agent_handlers["otel_agent"] is not t2._agent_handlers["otel_agent"]
        assert TracerHandlerRegistry.get_workflow_handlers()["otel_workflow"] is template_wf
        assert h1._trace_id == "trace-1"
        assert h2._trace_id == "trace-2"

    @staticmethod
    def _register_workflow_handler(service_name: str):
        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        otel = provider.get_tracer(service_name)
        try:
            cfg = OtelTracerConfig()
        except TypeError:
            cfg = OtelTracerConfig(service_name=service_name)
        TracerHandlerRegistry.register_handler(
            "otel_workflow", OtelWorkflowHandler(otel, cfg)
        )
        tracer_otel_mod._install_per_tracer_handler_isolation()
        return exporter

    @staticmethod
    @pytest.mark.asyncio
    async def test_concurrent_same_invoke_id_via_tracer_trigger():
        """经 Tracer.trigger 注入路径：同 WF/COMP id 交错互不覆盖，outputs 分属两条 trace。"""
        wf_id = "wf_same"
        comp_id = "node_http"
        exporter = TestPerTracerHandlerIsolation._register_workflow_handler(
            "isolation-trigger"
        )

        t_a = Tracer(session_id="sess-A", trace_id="trace-A")
        t_a.init()
        t_b = Tracer(session_id="sess-B", trace_id="trace-B")
        t_b.init()
        h_a = t_a._workflow_handlers["otel_workflow"]
        h_b = t_b._workflow_handlers["otel_workflow"]
        assert h_a is not h_b

        root_meta = {"workflow_id": wf_id, "workflow_name": "wf"}
        comp_meta = {
            "workflow_id": wf_id,
            "component_id": comp_id,
            "component_type": "FlowApi",
            "component_name": "http_node",
        }

        await t_a.trigger(
            _WF, "on_call_start", invoke_id=wf_id, metadata=root_meta,
            inputs={"q": "A"}, parent_node_id="",
        )
        await t_a.trigger(
            _WF, "on_call_start", invoke_id=comp_id, metadata=comp_meta,
            inputs={"q": "A"}, parent_node_id=wf_id,
        )
        a_state_id = id(h_a._span_manager.get(comp_id))
        assert a_state_id

        await t_b.trigger(
            _WF, "on_call_start", invoke_id=wf_id, metadata=root_meta,
            inputs={"q": "B"}, parent_node_id="",
        )
        await t_b.trigger(
            _WF, "on_call_start", invoke_id=comp_id, metadata=comp_meta,
            inputs={"q": "B"}, parent_node_id=wf_id,
        )

        assert id(h_a._span_manager.get(comp_id)) == a_state_id
        assert h_b._span_manager.get(comp_id) is not None
        assert id(h_b._span_manager.get(comp_id)) != a_state_id

        await t_a.trigger(
            _WF, "on_call_done", invoke_id=comp_id,
            outputs={"node_output": "A_RESULT"}, parent_node_id=wf_id,
        )
        assert h_a._span_manager.get(comp_id) is None
        assert h_b._span_manager.get(comp_id) is not None

        await t_b.trigger(
            _WF, "on_call_done", invoke_id=comp_id,
            outputs={"node_output": "B_RESULT"}, parent_node_id=wf_id,
        )
        await t_a.trigger(
            _WF, "on_call_done", invoke_id=wf_id,
            outputs={"out": "A"}, parent_node_id="",
        )
        await t_b.trigger(
            _WF, "on_call_done", invoke_id=wf_id,
            outputs={"out": "B"}, parent_node_id="",
        )

        finished = list(exporter.get_finished_spans())
        comp_spans = [s for s in finished if s.name.startswith("component.")]
        assert len(comp_spans) == 2
        output_attrs = {
            (span.attributes or {}).get(OJ_WORKFLOW_OUTPUTS)
            for span in comp_spans
        }
        # 两条独立完成；内容经 redact 后仍应能区分 A/B（或至少为两条非空）
        assert len([attr for attr in output_attrs if attr]) == 2
        assert h_a._trace_id == "trace-A"
        assert h_b._trace_id == "trace-B"

    @staticmethod
    def test_concurrent_tracer_init_keeps_distinct_identity():
        """多线程同时 Tracer.init：各 handler 绑定自己的 trace/session，不串到模板上最后写入的身份。"""
        TestPerTracerHandlerIsolation._register_workflow_handler("isolation-racy-init")

        thread_count = 8
        barrier = threading.Barrier(thread_count)
        results = []
        errors = []
        result_lock = threading.Lock()

        def worker(idx: int):
            try:
                barrier.wait(timeout=10)
                tracer = Tracer(session_id=f"sess-{idx}", trace_id=f"trace-{idx}")
                tracer.init()
                handler = tracer._workflow_handlers["otel_workflow"]
                # 必须持有 tracer/handler 引用：只存 id() 会在对象回收后地址复用，误报「非独立」。
                with result_lock:
                    results.append(
                        (idx, tracer, handler, handler._trace_id, handler._session_id)
                    )
            except BaseException as exc:  # noqa: BLE001
                with result_lock:
                    errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(thread_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert errors == []
        assert len(results) == thread_count
        handlers = [row[2] for row in results]
        assert len({id(handler) for handler in handlers}) == thread_count
        template = TracerHandlerRegistry.get_workflow_handlers()["otel_workflow"]
        assert all(handler is not template for handler in handlers)
        for idx, _tracer, _handler, trace_id, session_id in results:
            assert trace_id == f"trace-{idx}"
            assert session_id == f"sess-{idx}"

    @staticmethod
    def test_setup_installs_isolation_before_publishing_singleton(monkeypatch):
        """_create_otel_tracer：隔离安装完成前不得发布 _otel_tracer（防快速路径窗口）。"""
        import openjiuwen.extensions.tracer_otel as extension

        fake_tracer = MagicMock(name="ordered-tracer")
        monkeypatch.setattr(extension, "init_otel_tracer", MagicMock(return_value=fake_tracer))
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)

        seen = {"published_before_install": False}
        real_install = tracer_otel_mod._install_per_tracer_handler_isolation

        def install_and_check():
            # 进入 install 时单例应仍为 None
            if tracer_otel_mod._otel_tracer is not None:
                seen["published_before_install"] = True
            real_install()

        monkeypatch.setattr(
            tracer_otel_mod, "_install_per_tracer_handler_isolation", install_and_check
        )

        assert tracer_otel_mod.setup_otel_tracer() is fake_tracer
        assert seen["published_before_install"] is False
        assert tracer_otel_mod._per_tracer_isolation_installed is True
