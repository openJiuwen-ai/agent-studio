#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""OTEL_SAMPLE_RATE=0 不得被注入逻辑父 SAMPLED 绕过 — #1644 / #1713。"""

from __future__ import annotations

from unittest.mock import patch

from opentelemetry.sdk.trace.sampling import Decision, ParentBasedTraceIdRatio
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, TraceState
from opentelemetry.trace import set_span_in_context

from agent_runtime.observability.otel_parent_flags import resolve_injected_trace_flags


class TestResolveInjectedTraceFlags:
    @staticmethod
    def test_rate_zero_not_sampled():
        flags = resolve_injected_trace_flags(0xABC123, sample_rate=0.0)
        assert int(flags) & TraceFlags.SAMPLED == 0

    @staticmethod
    def test_rate_one_sampled():
        flags = resolve_injected_trace_flags(0xABC123, sample_rate=1.0)
        assert int(flags) & TraceFlags.SAMPLED == TraceFlags.SAMPLED

    @staticmethod
    def test_reads_settings_when_rate_omitted():
        with patch("agent_runtime.common.config.settings") as settings:
            settings.otel.sample_rate = 0.0
            flags = resolve_injected_trace_flags(0xABC123)
            assert int(flags) & TraceFlags.SAMPLED == 0


class TestParentBasedHonorsInjectedFlags:
    """看守：rate=0 + 按修复后 flags 注入父 → 子决策 DROP。"""

    @staticmethod
    def _child_decision(parent_flags: TraceFlags):
        parent = SpanContext(
            trace_id=0xABC123,
            span_id=0xDEF456,
            is_remote=False,
            trace_flags=parent_flags,
            trace_state=TraceState(),
        )
        ctx = set_span_in_context(NonRecordingSpan(parent))
        return ParentBasedTraceIdRatio(rate=0.0).should_sample(
            parent_context=ctx,
            trace_id=0xABC123,
            name="chain",
        ).decision

    @staticmethod
    def test_legacy_forced_sampled_bypasses_rate_zero():
        """修复前对照：硬编码 SAMPLED 父 → 即便 rate=0 仍 RECORD。"""
        decision = TestParentBasedHonorsInjectedFlags._child_decision(
            TraceFlags(TraceFlags.SAMPLED)
        )
        assert decision == Decision.RECORD_AND_SAMPLE

    @staticmethod
    def test_rate_zero_flags_drop_child():
        flags = resolve_injected_trace_flags(0xABC123, sample_rate=0.0)
        decision = TestParentBasedHonorsInjectedFlags._child_decision(flags)
        assert decision == Decision.DROP


def test_middleware_rate_zero_injects_unsampled_parent():
    """dispatch 内当前 span 在 OTEL_SAMPLE_RATE=0 时不得带 SAMPLED。"""
    import asyncio

    from starlette.requests import Request
    from starlette.responses import Response
    from opentelemetry import trace as otel_trace
    from agent_runtime.context.middleware import RequestContextMiddleware

    middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
    captured = {}

    async def call_next(request):
        span = otel_trace.get_current_span()
        captured["sampled"] = span.get_span_context().trace_flags & TraceFlags.SAMPLED
        return Response("ok")

    async def _receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/orchestration/ir/execute",
            "headers": [(b"x-request-id", b"obs-sample0-guard")],
        },
        receive=_receive,
    )

    async def _run():
        with patch(
            "agent_runtime.context.middleware.resolve_injected_trace_flags",
            side_effect=lambda tid: resolve_injected_trace_flags(tid, sample_rate=0.0),
        ):
            await middleware.dispatch(request, call_next)

    asyncio.run(_run())
    assert captured.get("sampled") == 0
