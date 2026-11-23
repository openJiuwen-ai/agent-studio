#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Bridge openjiuwen ``_explicit_parent_context`` for #1713.

上游缺省 ``parent_trace_flags or "1"``（强制 SAMPLED）会让
``ParentBasedTraceIdRatio`` 在 ``OTEL_SAMPLE_RATE=0`` 时仍跟随父采样。
本桥在 setup 时覆写该函数：采样率 0 强制未采样；有真实 flags 则透传；
缺省时按 ``resolve_injected_trace_flags`` 决策。
"""

from __future__ import annotations

from agent_runtime.observability.otel_parent_flags import (
    _normalize_sample_rate,
    resolve_injected_trace_flags,
)
from openjiuwen.core.common.logging import workflow_logger as logger
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags


def resolve_explicit_parent_trace_flags(
    trace_id: int, parent_trace_flags: str | None, sample_rate: float | None = None
) -> TraceFlags:
    """Decide TraceFlags for embedded-ref logical parents.

    - ``sample_rate <= 0`` → 未采样（验收：rate=0 不采）
    - 显式合法 flags → 透传真实采样位
    - 缺省/非法 → 按 ``OTEL_SAMPLE_RATE`` 对 ``trace_id`` 决策（禁止默认 SAMPLED）
    """
    if sample_rate is None:
        from agent_runtime.common.config import settings

        sample_rate = float(settings.otel.sample_rate)

    sample_rate = _normalize_sample_rate(sample_rate)

    if sample_rate <= 0.0:
        return TraceFlags(0x00)

    raw = None if parent_trace_flags is None else str(parent_trace_flags).strip()
    if raw:
        try:
            return TraceFlags(int(raw, 16) & TraceFlags.SAMPLED)
        except ValueError:
            pass
    return resolve_injected_trace_flags(trace_id, sample_rate=sample_rate)


def build_explicit_parent_context(instance_info: dict | None):
    """Studio 版 ``_explicit_parent_context``：不强制缺省 SAMPLED。"""
    info = instance_info or {}
    trace_hex = str(info.get("parent_trace_id") or "")
    span_hex = str(info.get("parent_span_id") or "")
    try:
        trace_id = int(trace_hex, 16)
        span_id = int(span_hex, 16)
    except ValueError:
        return None
    if not (0 < span_id < 2**64 and 0 < trace_id < 2**128):
        return None

    flags = resolve_explicit_parent_trace_flags(
        trace_id, info.get("parent_trace_flags")
    )
    ctx = SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=True,
        trace_flags=flags,
    )
    return trace.set_span_in_context(NonRecordingSpan(ctx))


def install_explicit_parent_bridge() -> bool:
    """Monkey-patch openjiuwen handler if ``_explicit_parent_context`` exists.

    Returns True when patched; False when symbol absent (e.g. newer package
    without this helper) or import failed.
    """
    try:
        import openjiuwen.extensions.tracer_otel.handler as otel_handler
    except ImportError:
        logger.warning(
            "otel explicit-parent bridge skipped: tracer_otel.handler unavailable"
        )
        return False

    # 上游符号名以下划线开头；经模块 __dict__ / setattr 桥接，避免
    # otel_handler._xxx 点号访问触发 G.CLS.11。
    symbol = "_explicit_parent_context"
    handler_ns = getattr(otel_handler, "__dict__", {})
    if symbol not in handler_ns:
        logger.info(
            "otel explicit-parent bridge skipped: "
            "_explicit_parent_context not present in this openjiuwen build"
        )
        return False

    setattr(otel_handler, symbol, build_explicit_parent_context)
    logger.info(
        "otel explicit-parent bridge installed: "
        "embedded refs honor OTEL_SAMPLE_RATE (no default SAMPLED)"
    )
    return True
