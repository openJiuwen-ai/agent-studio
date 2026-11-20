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
    from opentelemetry.trace import SpanKind

    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    return memory, provider.get_tracer("agent-builder"), SpanKind


def test_extract_inbound_continues_w3c_parent():
    """Upstream traceparent must parent the builder HTTP span (same trace_id)."""
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    memory, tracer, SpanKind = _local_memory_tracer()
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
    memory, tracer, SpanKind = _local_memory_tracer()
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
