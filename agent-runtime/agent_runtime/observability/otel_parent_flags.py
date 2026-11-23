#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Synthetic OTel parent TraceFlags — GitHub #1644 / GitCode #1713.

Runtime 入口用 NonRecordingSpan 注入业务关联 trace_id 时，若一律
``TraceFlags.SAMPLED``，``ParentBasedTraceIdRatio`` 会跟随父决策，
导致 ``OTEL_SAMPLE_RATE=0`` 被静默绕过。应按配置采样率决定父 flags。
"""

from __future__ import annotations

import math

from opentelemetry.trace import TraceFlags


def _normalize_sample_rate(sample_rate: float) -> float:
    """有限且夹紧到 [0, 1]；nan/inf → 1.0（与 OtelSettings 校验一致）。"""
    try:
        rate = float(sample_rate)
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(rate):
        return 1.0
    if rate < 0.0:
        return 0.0
    if rate > 1.0:
        return 1.0
    return rate


def resolve_injected_trace_flags(
    trace_id: int, sample_rate: float | None = None
) -> TraceFlags:
    """按 ``OTEL_SAMPLE_RATE`` 决定注入逻辑父的 TraceFlags。

    - ``sample_rate <= 0`` → 未采样（rate=0 时子 span 跟随丢弃）
    - ``sample_rate >= 1`` → SAMPLED
    - ``(0, 1)`` → 用与 SDK 相同的 ``TraceIdRatioBased`` 对 ``trace_id`` 决策
    """
    if sample_rate is None:
        from agent_runtime.common.config import settings

        sample_rate = float(settings.otel.sample_rate)

    sample_rate = _normalize_sample_rate(sample_rate)

    if sample_rate <= 0.0:
        return TraceFlags(0x00)
    if sample_rate >= 1.0:
        return TraceFlags(TraceFlags.SAMPLED)

    # opentelemetry-sdk 在 tracer-otel extra；基础运行时可能未装。
    # 缺 SDK 时不可让 middleware 每请求 ImportError → 500。
    try:
        from opentelemetry.sdk.trace.sampling import Decision, TraceIdRatioBased
    except ImportError:
        # 降级：无法做比例采样时保守不采，避免硬失败
        return TraceFlags(0x00)

    decision = TraceIdRatioBased(rate=sample_rate).should_sample(
        parent_context=None,
        trace_id=trace_id,
        name="otel-parent-injection",
    ).decision
    if decision == Decision.RECORD_AND_SAMPLE:
        return TraceFlags(TraceFlags.SAMPLED)
    return TraceFlags(0x00)
