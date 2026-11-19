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
    monkeypatch.setattr(tracer_otel_mod, "_INITIALIZED", False)
    monkeypatch.setattr(tracer_otel_mod, "_otel_settings", lambda: _fake_otel(enabled=False))
    tracer_otel_mod.setup_otel_tracer()
    assert tracer_otel_mod._INITIALIZED is False


def test_setup_raw_sdk_records_span(monkeypatch):
    monkeypatch.setattr(tracer_otel_mod, "_INITIALIZED", False)
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
    assert tracer_otel_mod._INITIALIZED is True

    from opentelemetry import trace

    tracer = trace.get_tracer("agent-builder")
    with tracer.start_as_current_span("e2e-builder-span") as span:
        span.set_attribute("http.method", "GET")
        assert span.is_recording()

    spans = memory.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "e2e-builder-span"
    assert spans[0].resource.attributes.get("service.name") == "agent-builder"
