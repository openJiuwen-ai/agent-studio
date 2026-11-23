#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""#1713：embedded refs 显式父不得缺省强制 SAMPLED。"""

from __future__ import annotations

from opentelemetry.sdk.trace.sampling import Decision, ParentBasedTraceIdRatio
from opentelemetry.trace import TraceFlags

from agent_runtime.observability.otel_explicit_parent_bridge import (
    build_explicit_parent_context,
    install_explicit_parent_bridge,
    resolve_explicit_parent_trace_flags,
)


class TestResolveExplicitParentTraceFlags:
    @staticmethod
    def test_rate_zero_forces_unsampled_even_if_flags_say_sampled():
        flags = resolve_explicit_parent_trace_flags(
            0xABC123, parent_trace_flags="01", sample_rate=0.0
        )
        assert int(flags) & TraceFlags.SAMPLED == 0

    @staticmethod
    def test_missing_flags_follow_sample_rate_not_default_sampled():
        flags = resolve_explicit_parent_trace_flags(
            0xABC123, parent_trace_flags=None, sample_rate=0.0
        )
        assert int(flags) & TraceFlags.SAMPLED == 0

    @staticmethod
    def test_missing_flags_with_rate_one_are_sampled():
        flags = resolve_explicit_parent_trace_flags(
            0xABC123, parent_trace_flags=None, sample_rate=1.0
        )
        assert int(flags) & TraceFlags.SAMPLED == TraceFlags.SAMPLED

    @staticmethod
    def test_explicit_unsampled_flags_passthrough_when_rate_positive():
        flags = resolve_explicit_parent_trace_flags(
            0xABC123, parent_trace_flags="00", sample_rate=1.0
        )
        assert int(flags) & TraceFlags.SAMPLED == 0


class TestBuildExplicitParentContext:
    @staticmethod
    def test_rate_zero_embedded_refs_child_drops():
        """看守：manager 风格缺 flags 的 refs + rate=0 → ParentBased DROP。"""
        from unittest.mock import patch

        from agent_runtime.observability import otel_explicit_parent_bridge as bridge

        with patch.object(
            bridge,
            "resolve_explicit_parent_trace_flags",
            return_value=TraceFlags(0x00),
        ):
            ctx = build_explicit_parent_context(
                {
                    "parent_trace_id": f"{0xABC123:032x}",
                    "parent_span_id": f"{0xDEF456:016x}",
                    # 故意不传 parent_trace_flags（上游旧行为会默认 SAMPLED）
                }
            )
        assert ctx is not None
        decision = ParentBasedTraceIdRatio(rate=0.0).should_sample(
            parent_context=ctx,
            trace_id=0xABC123,
            name="chain",
        ).decision
        assert decision == Decision.DROP

    @staticmethod
    def test_legacy_default_sampled_would_bypass():
        """对照：若仍强制 SAMPLED，rate=0 下子 span 仍 RECORD。"""
        from opentelemetry import trace
        from opentelemetry.trace import NonRecordingSpan, SpanContext

        parent = SpanContext(
            trace_id=0xABC123,
            span_id=0xDEF456,
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        ctx = trace.set_span_in_context(NonRecordingSpan(parent))
        decision = ParentBasedTraceIdRatio(rate=0.0).should_sample(
            parent_context=ctx,
            trace_id=0xABC123,
            name="chain",
        ).decision
        assert decision == Decision.RECORD_AND_SAMPLE


class TestInstallBridge:
    @staticmethod
    def test_install_patches_when_symbol_exists():
        import openjiuwen.extensions.tracer_otel.handler as otel_handler

        symbol = "_explicit_parent_context"
        handler_ns = getattr(otel_handler, "__dict__", {})
        if symbol not in handler_ns:
            # 部分构建已移除该符号：安装应安全跳过
            assert install_explicit_parent_bridge() is False
            return

        original = handler_ns[symbol]
        try:
            assert install_explicit_parent_bridge() is True
            assert getattr(otel_handler, "__dict__", {}).get(symbol) is (
                build_explicit_parent_context
            )
        finally:
            setattr(otel_handler, symbol, original)
