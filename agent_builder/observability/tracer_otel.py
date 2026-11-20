# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""OpenTelemetry wiring for agent_builder (#1655 / #1724).

Mirrors agent-runtime's ``setup_otel_tracer``: consume ``settings.otel`` so
``OTEL_ENABLED`` / sample rate / exporter endpoint are no longer dead config.
Prefers ``openjiuwen.extensions.tracer_otel`` when installed; otherwise falls
back to the four ``opentelemetry-*`` packages already declared in requirements.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("agent_builder.observability.tracer_otel")

_INITIALIZED = False


def is_otel_tracer_initialized() -> bool:
    """Return whether ``setup_otel_tracer`` has already installed a provider."""
    return _INITIALIZED


def reset_otel_tracer_for_tests() -> None:
    """Clear the init flag so unit tests can re-enter ``setup_otel_tracer``."""
    global _INITIALIZED
    _INITIALIZED = False


def _otel_settings():
    from agent_builder.adapter.config_bridge import settings

    return settings.otel


def setup_otel_tracer() -> None:
    """Initialize the global OTel TracerProvider from ``settings.otel``.

    Idempotent. When ``OTEL_ENABLED`` is false, logs and returns without
    installing a provider.
    """
    global _INITIALIZED
    if _INITIALIZED:
        logger.info("OpenTelemetry tracer already initialized, skipping")
        return

    otel = _otel_settings()
    if not otel.enabled:
        logger.info("OpenTelemetry tracer is disabled (OTEL_ENABLED=false)")
        return

    try:
        if _try_setup_openjiuwen(otel):
            _INITIALIZED = True
            return
        _setup_raw_sdk(otel)
        _INITIALIZED = True
    except Exception as exc:  # noqa: BLE001 — startup must not crash on OTel
        logger.warning("OpenTelemetry tracer setup failed (non-critical): %s", exc)


def _try_setup_openjiuwen(otel) -> bool:
    """Return True when openjiuwen tracer-otel extension handled init.

    Returns False (so ``setup_otel_tracer`` can fall back to raw SDK) when the
    extension is missing **or** present but fails (API/config mismatch, etc.).
    """
    try:
        from openjiuwen.core.session.tracer import TracerHandlerRegistry
        from openjiuwen.extensions.tracer_otel import (
            OtelAgentHandler,
            OtelTracerConfig,
            OtelWorkflowHandler,
            init_otel_tracer,
        )
    except ImportError:
        logger.info(
            "openjiuwen tracer-otel extension unavailable; "
            "falling back to raw OpenTelemetry SDK"
        )
        return False

    try:
        agent_handlers = TracerHandlerRegistry.get_agent_handlers()
        if "otel_agent" in agent_handlers:
            logger.info("OpenTelemetry tracer handlers already registered, skipping")
            return True

        config = OtelTracerConfig(
            exporter_type=otel.exporter_type,
            exporter_endpoint=otel.exporter_endpoint or None,
            protocol=otel.protocol,
            headers=otel.headers,
            service_name=otel.service_name,
            service_version=otel.service_version or None,
            sample_rate=otel.sample_rate,
            schedule_delay_millis=otel.schedule_delay_millis,
            export_timeout_ms=otel.export_timeout_ms,
            max_export_batch_size=otel.max_export_batch_size,
            redaction_enabled=otel.redaction_enabled,
            redact_prompts=otel.redact_prompts,
            redact_completions=otel.redact_completions,
            max_attr_length=otel.max_attr_length,
        )
        otel_tracer = init_otel_tracer(config)
        TracerHandlerRegistry.register_handler(
            "otel_agent", OtelAgentHandler(otel_tracer, config)
        )
        TracerHandlerRegistry.register_handler(
            "otel_workflow", OtelWorkflowHandler(otel_tracer, config)
        )
        logger.info(
            "OpenTelemetry tracer initialized via openjiuwen: "
            "exporter_type=%s endpoint=%s service_name=%s sample_rate=%s",
            config.exporter_type,
            config.exporter_endpoint or "N/A",
            config.service_name,
            config.sample_rate,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — fall back to raw SDK instead of silent skip
        logger.warning(
            "openjiuwen tracer-otel setup failed (%s); "
            "falling back to raw OpenTelemetry SDK",
            exc,
        )
        return False


def _setup_raw_sdk(otel) -> None:
    """Install TracerProvider using the declared opentelemetry-* packages."""
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    resource_attrs = {"service.name": otel.service_name or "agent-builder"}
    if otel.service_version:
        resource_attrs["service.version"] = otel.service_version
    resource = Resource.create(resource_attrs)
    rate = max(0.0, min(1.0, float(otel.sample_rate)))
    sampler = ParentBased(root=TraceIdRatioBased(rate))
    provider = TracerProvider(resource=resource, sampler=sampler)

    exporter = _build_exporter(otel)
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            schedule_delay_millis=otel.schedule_delay_millis,
            max_export_batch_size=otel.max_export_batch_size,
            export_timeout_millis=otel.export_timeout_ms,
        )
    )
    trace.set_tracer_provider(provider)
    logger.info(
        "OpenTelemetry tracer initialized via raw SDK: "
        "exporter_type=%s endpoint=%s service_name=%s sample_rate=%s",
        otel.exporter_type,
        otel.exporter_endpoint or "N/A",
        otel.service_name,
        otel.sample_rate,
    )


def _build_exporter(otel):
    exporter_type = (otel.exporter_type or "console").lower()
    if exporter_type == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        return ConsoleSpanExporter()

    endpoint = otel.exporter_endpoint or ""
    headers = otel.headers or None
    protocol = (otel.protocol or "grpc").lower()
    if protocol == "http" or exporter_type in {"otlp_http", "http"}:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        kwargs = {}
        if endpoint:
            kwargs["endpoint"] = endpoint
        if headers:
            kwargs["headers"] = headers
        return OTLPSpanExporter(**kwargs)

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    kwargs = {}
    if endpoint:
        kwargs["endpoint"] = endpoint
    if headers:
        kwargs["headers"] = headers
    return OTLPSpanExporter(**kwargs)


def extract_inbound_trace_context(headers):
    """Extract W3C Trace Context from inbound HTTP headers.

    When the carrier has a valid ``traceparent``, the returned context parents
    a child span under the upstream trace; otherwise the context is empty and
    ``start_as_current_span`` creates a new root (same as before).
    """
    from opentelemetry.context import Context
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    if headers is None:
        return Context()
    try:
        carrier = {str(k).lower(): str(v) for k, v in headers.items()}
    except Exception:  # noqa: BLE001 — never break request path on header parse
        return Context()
    return TraceContextTextMapPropagator().extract(carrier)


def force_flush(timeout_millis: int = 5000) -> bool:
    """Flush pending spans (for tests / shutdown)."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider

        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            return bool(provider.force_flush(timeout_millis))
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenTelemetry force_flush failed: %s", exc)
    return False
