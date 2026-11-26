# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from __future__ import annotations

import threading
from typing import Any, Optional

from agent_runtime.common.config import settings
from openjiuwen.core.common.logging import workflow_logger as logger

# Core 的 init_otel_tracer 故意不设置全局 TracerProvider（handler 持有 tracer 引用），
# 因此请求级根 span 必须复用同一个 tracer 实例，否则拿到 NoOp tracer 导致 span 不导出。
_otel_tracer: Optional[Any] = None
_setup_lock = threading.Lock()


def setup_otel_tracer() -> Optional[Any]:
    """Return the process-wide OTel tracer, initializing it once on first use.

    Reads configuration from ``settings.otel``.  When ``OTEL_ENABLED`` is
    ``True`` and the ``openjiuwen[tracer-otel]`` extension is installed,
    creates an OTel TracerProvider + exporter and registers
    ``OtelAgentHandler`` / workflow handler into ``TracerHandlerRegistry``
    so that all subsequent ``Tracer`` instances automatically emit OTel spans.

    Workflow 侧注册 ``ExecutionScopedWorkflowHandler``：按 runner 写入的
    execution scope 分发到独立 ``StudioOtelWorkflowHandler``，避免同工作流
    并发共享 span 状态（不 monkeypatch ``Tracer.init``）。

    This function is idempotent and thread-safe; repeated calls return the
    tracer created by the first successful call.  Returns ``None`` when OTel
    is disabled or the extension is unavailable, so callers can skip creating
    their own spans.
    """
    if _otel_tracer is not None:
        return _otel_tracer
    with _setup_lock:
        if _otel_tracer is not None:
            return _otel_tracer
        return _create_otel_tracer()


def _create_otel_tracer() -> Optional[Any]:
    global _otel_tracer
    if not settings.otel.enabled:
        logger.info("OpenTelemetry tracer is disabled (OTEL_ENABLED=false)")
        return None

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
        return None

    try:
        # 本仓子类依赖上游扩展的私有符号（升级可能缺失/改名），与上游导入隔离，
        # 失败时回退官方 handler，避免 OTel 整体静默停用并被误报为"未安装扩展"
        from agent_runtime.observability.otel_handler_scope import (
            ExecutionScopedWorkflowHandler,
        )

        _workflow_handler_cls = ExecutionScopedWorkflowHandler
    except ImportError as import_exc:
        logger.warning(
            "ExecutionScopedWorkflowHandler unavailable (%s), "
            "fallback to official OtelWorkflowHandler",
            import_exc,
        )
        _workflow_handler_cls = OtelWorkflowHandler

    if _handlers_already_registered():
        logger.info("OpenTelemetry tracer handlers already registered, skipping")
        return _otel_tracer

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

    # 注册全部成功后再写入单例：否则注册抛异常会留下半初始化缓存，
    # 后续调用直接返回 tracer 而跳过注册，agent/workflow span 静默不再导出。
    _otel_tracer = otel_tracer

    logger.info(
        f"OpenTelemetry tracer initialized: "
        f"exporter_type={config.exporter_type}, "
        f"endpoint={config.exporter_endpoint or 'N/A'}, "
        f"protocol={config.protocol}, "
        f"service_name={config.service_name}, "
        f"sample_rate={config.sample_rate}, "
        f"workflow_handler={_workflow_handler_cls.__name__}"
    )
    return _otel_tracer


def get_otel_tracer() -> Optional[Any]:
    """Return the tracer singleton created by :func:`setup_otel_tracer`."""
    return _otel_tracer


def _handlers_already_registered() -> bool:
    from openjiuwen.core.session.tracer import TracerHandlerRegistry
    agent_handlers = TracerHandlerRegistry.get_agent_handlers()
    return "otel_agent" in agent_handlers
