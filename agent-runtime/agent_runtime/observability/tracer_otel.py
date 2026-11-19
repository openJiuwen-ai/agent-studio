# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

from agent_runtime.common.config import settings
from openjiuwen.core.common.logging import workflow_logger as logger



def setup_otel_tracer() -> None:
    """Initialize OpenTelemetry tracer handlers and register them globally.

    Reads configuration from ``settings.otel``.  When ``OTEL_ENABLED`` is
    ``True`` and the ``openjiuwen[tracer-otel]`` extension is installed,
    creates an OTel TracerProvider + OTLP exporter and registers
    ``OtelAgentHandler`` / ``OtelWorkflowHandler`` into
    ``TracerHandlerRegistry`` so that all subsequent ``Tracer`` instances
    automatically emit OTel spans.

    This function is idempotent; calling it more than once is safe (the
    second call is a no-op if handlers are already registered).
    """
    if not settings.otel.enabled:
        logger.info("OpenTelemetry tracer is disabled (OTEL_ENABLED=false)")
        return

    try:
        from openjiuwen.core.session.tracer import TracerHandlerRegistry
        from openjiuwen.extensions.tracer_otel import (
            OtelAgentHandler,
            OtelTracerConfig,
            OtelWorkflowHandler,
            init_otel_tracer,
        )
    except ImportError:
        logger.warning(
            "OpenTelemetry tracer extension not installed. "
            "Install with: pip install openjiuwen[tracer-otel]"
        )
        return

    try:
        # 本仓子类依赖上游扩展的私有符号（升级可能缺失/改名），与上游导入隔离，
        # 失败时回退官方 handler，避免 OTel 整体静默停用并被误报为"未安装扩展"
        from agent_runtime.observability.tracer_otel_studio import (
            StudioOtelWorkflowHandler,
        )

        _workflow_handler_cls = StudioOtelWorkflowHandler
    except ImportError as import_exc:
        logger.warning(
            "StudioOtelWorkflowHandler unavailable (%s), "
            "fallback to official OtelWorkflowHandler",
            import_exc,
        )
        _workflow_handler_cls = OtelWorkflowHandler

    if _handlers_already_registered():
        logger.info("OpenTelemetry tracer handlers already registered, skipping")
        return

    otel_settings = settings.otel

    config = OtelTracerConfig(
        exporter_type=otel_settings.exporter_type,
        exporter_endpoint=otel_settings.exporter_endpoint or None,
        protocol=otel_settings.protocol,
        headers=otel_settings.headers,
        service_name=otel_settings.service_name,
        service_version=otel_settings.service_version or None,
        sample_rate=otel_settings.sample_rate,
        schedule_delay_millis=otel_settings.schedule_delay_millis,
        export_timeout_ms=otel_settings.export_timeout_ms,
        max_export_batch_size=otel_settings.max_export_batch_size,
        redaction_enabled=otel_settings.redaction_enabled,
        redact_prompts=otel_settings.redact_prompts,
        redact_completions=otel_settings.redact_completions,
        max_attr_length=otel_settings.max_attr_length,
    )

    otel_tracer = init_otel_tracer(config)

    TracerHandlerRegistry.register_handler(
        "otel_agent", OtelAgentHandler(otel_tracer, config)
    )
    TracerHandlerRegistry.register_handler(
        "otel_workflow", _workflow_handler_cls(otel_tracer, config)
    )

    logger.info(
        f"OpenTelemetry tracer initialized: "
        f"exporter_type={config.exporter_type}, "
        f"endpoint={config.exporter_endpoint or 'N/A'}, "
        f"protocol={config.protocol}, "
        f"service_name={config.service_name}, "
        f"sample_rate={config.sample_rate}"
    )


def _handlers_already_registered() -> bool:
    from openjiuwen.core.session.tracer import TracerHandlerRegistry
    agent_handlers = TracerHandlerRegistry.get_agent_handlers()
    return "otel_agent" in agent_handlers
