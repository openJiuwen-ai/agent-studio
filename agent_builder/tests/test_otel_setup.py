# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""#1655/#1724：builder OTel 接线单测（raw SDK 路径）。"""

from __future__ import annotations

from types import SimpleNamespace

import agent_builder.observability.tracer_otel as tracer_otel_mod


def _fake_otel(**overrides):
    base = dict(
        enabled=False,
        exporter_type="console",
        exporter_endpoint="",
        protocol="grpc",
        headers={},
        service_name="agent-builder",
        service_version="",
        sample_rate=1.0,
        schedule_delay_millis=5000,
        export_timeout_ms=30000,
        max_export_batch_size=512,
        redaction_enabled=True,
        redact_prompts=None,
        redact_completions=None,
        max_attr_length=4096,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_setup_disabled_is_noop(monkeypatch):
    tracer_otel_mod.reset_otel_tracer_for_tests()
    monkeypatch.setattr(tracer_otel_mod, "_otel_settings", lambda: _fake_otel(enabled=False))
    tracer_otel_mod.setup_otel_tracer()
    assert tracer_otel_mod.is_otel_tracer_initialized() is False


def test_openjiuwen_api_mismatch_falls_back_to_raw_sdk(monkeypatch):
    """TypeError after import (config API drift) → raw SDK still installs provider."""
    import sys
    from types import ModuleType

    tracer_otel_mod.reset_otel_tracer_for_tests()
    monkeypatch.setattr(
        tracer_otel_mod,
        "_otel_settings",
        lambda: _fake_otel(enabled=True, service_name="agent-builder"),
    )

    created = []

    def _ensure(name: str) -> ModuleType:
        if name not in sys.modules:
            sys.modules[name] = ModuleType(name)
            created.append(name)
        return sys.modules[name]

    for pkg in (
        "openjiuwen",
        "openjiuwen.core",
        "openjiuwen.core.session",
        "openjiuwen.core.session.tracer",
        "openjiuwen.extensions",
        "openjiuwen.extensions.tracer_otel",
    ):
        _ensure(pkg)

    tracer_pkg = sys.modules["openjiuwen.core.session.tracer"]
    ext_pkg = sys.modules["openjiuwen.extensions.tracer_otel"]
    saved_tracer = {
        k: getattr(tracer_pkg, k, None) for k in ("TracerHandlerRegistry",)
    }
    saved_ext = {
        k: getattr(ext_pkg, k, None)
        for k in (
            "OtelAgentHandler",
            "OtelTracerConfig",
            "OtelWorkflowHandler",
            "init_otel_tracer",
        )
    }

    class _Registry:
        @staticmethod
        def get_agent_handlers():
            return {}

        @staticmethod
        def register_handler(*_a, **_k):
            return None

    def _bad_config(**_kwargs):
        raise TypeError("OtelTracerConfig got an unexpected keyword argument")

    tracer_pkg.TracerHandlerRegistry = _Registry
    ext_pkg.OtelTracerConfig = _bad_config
    ext_pkg.OtelAgentHandler = type("OtelAgentHandler", (), {})
    ext_pkg.OtelWorkflowHandler = type("OtelWorkflowHandler", (), {})
    ext_pkg.init_otel_tracer = lambda _c: object()

    raw_calls = []
    monkeypatch.setattr(
        tracer_otel_mod,
        "_setup_raw_sdk",
        lambda otel: raw_calls.append(otel.service_name),
    )

    try:
        assert (
            tracer_otel_mod._try_setup_openjiuwen(_fake_otel(enabled=True)) is False
        )
        tracer_otel_mod.setup_otel_tracer()
        assert raw_calls == ["agent-builder"]
        assert tracer_otel_mod.is_otel_tracer_initialized() is True
    finally:
        for key, val in saved_tracer.items():
            if val is None and hasattr(tracer_pkg, key):
                delattr(tracer_pkg, key)
            elif val is not None:
                setattr(tracer_pkg, key, val)
        for key, val in saved_ext.items():
            if val is None and hasattr(ext_pkg, key):
                delattr(ext_pkg, key)
            elif val is not None:
                setattr(ext_pkg, key, val)
        for name in reversed(created):
            sys.modules.pop(name, None)


def test_setup_raw_sdk_records_span(monkeypatch):
    tracer_otel_mod.reset_otel_tracer_for_tests()
    monkeypatch.setattr(
        tracer_otel_mod,
        "_otel_settings",
        lambda: _fake_otel(enabled=True, service_name="agent-builder"),
    )
    monkeypatch.setattr(tracer_otel_mod, "_try_setup_openjiuwen", lambda _otel: False)

    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    memory = InMemorySpanExporter()

    def _install_memory(otel_settings):
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

        provider = TracerProvider(
            resource=Resource.create({"service.name": otel_settings.service_name}),
            sampler=ParentBased(root=TraceIdRatioBased(1.0)),
        )
        provider.add_span_processor(SimpleSpanProcessor(memory))
        trace.set_tracer_provider(provider)

    monkeypatch.setattr(tracer_otel_mod, "_setup_raw_sdk", _install_memory)

    tracer_otel_mod.setup_otel_tracer()
    assert tracer_otel_mod.is_otel_tracer_initialized() is True

    from opentelemetry import trace

    tracer = trace.get_tracer("agent-builder")
    with tracer.start_as_current_span("e2e-builder-span") as span:
        span.set_attribute("http.method", "GET")
        assert span.is_recording()

    spans = memory.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "e2e-builder-span"
    assert spans[0].resource.attributes.get("service.name") == "agent-builder"


def _local_memory_tracer():
    """Isolated TracerProvider — avoids global provider override across tests."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    return memory, provider.get_tracer("agent-builder")


def test_extract_inbound_continues_w3c_parent():
    """Upstream traceparent must parent the builder HTTP span (same trace_id)."""
    from opentelemetry.trace import SpanKind
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    memory, tracer = _local_memory_tracer()
    propagator = TraceContextTextMapPropagator()
    carrier: dict[str, str] = {}
    with tracer.start_as_current_span("upstream-service") as parent:
        propagator.inject(carrier)
        parent_trace_id = parent.get_span_context().trace_id
        parent_span_id = parent.get_span_context().span_id

    assert "traceparent" in carrier

    parent_context = tracer_otel_mod.extract_inbound_trace_context(carrier)
    with tracer.start_as_current_span(
        "GET /api/prompt",
        context=parent_context,
        kind=SpanKind.SERVER,
    ) as child:
        assert child.get_span_context().trace_id == parent_trace_id

    spans = {s.name: s for s in memory.get_finished_spans()}
    assert "upstream-service" in spans
    assert "GET /api/prompt" in spans
    child_span = spans["GET /api/prompt"]
    assert child_span.context.trace_id == parent_trace_id
    assert child_span.parent is not None
    assert child_span.parent.span_id == parent_span_id


def test_extract_inbound_without_traceparent_is_new_root():
    """No W3C carrier → extract yields empty context; span remains a root."""
    from opentelemetry.trace import SpanKind

    memory, tracer = _local_memory_tracer()
    parent_context = tracer_otel_mod.extract_inbound_trace_context(
        {"x-request-id": "abc"}
    )
    with tracer.start_as_current_span(
        "GET /orphan",
        context=parent_context,
        kind=SpanKind.SERVER,
    ):
        pass

    spans = memory.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "GET /orphan"
    assert spans[0].parent is None
