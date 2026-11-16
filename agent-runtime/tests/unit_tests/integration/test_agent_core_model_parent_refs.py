# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""同步入口显式父级契约：node executor 上下文里捕获 refs，随 kwargs 过桥。

背景（部署实证 ②）：嵌入双写桥的 llm span 父级依赖环境回退，而
create_agent_session 会把桥线程的 current span 换成死根（recording=False），
llm span 因此与 node span 并列、误挂工作流死根。修复在同步入口（桥启动
前、node executor 上下文内）显式捕获 (trace_id, span_id, trace_flags)，
走与 agent_id 同一条 get_model(identity=) 通道——core 端显式 > 逻辑 >
环境三级定父。本文件钉死捕获与注入契约，防回归。
"""

import types

import pytest
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace

from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer

# 套件既有惯例：契约测试直接触达受保护成员，经 getattr 规避
# G.CLS.11（pylint pragma 对 CodeCheck 不生效）
_ambient_span_refs = getattr(AgentCoreModelLayer, "_ambient_span_refs")


def _make_recording_span(name: str):
    """独立 TracerProvider（不经全局注册）产真实 recording span，可取 hex id。"""
    from opentelemetry.sdk.trace import TracerProvider

    tracer = TracerProvider().get_tracer("parent-refs-test")
    return tracer.start_span(name=name)


def _hex_ids(span) -> tuple[str, str]:
    ctx = span.get_span_context()
    return f"{ctx.trace_id:032x}", f"{ctx.span_id:016x}"


def _make_runtime(captured: dict):
    """记录 ainvoke/astream 收到的 kwargs、回放假结果的 runtime 替身。"""

    class _FakeResult:
        content = "ok"

    async def _ainvoke(inputs, **kwargs):
        captured.setdefault("ainvoke", []).append(dict(kwargs))
        return _FakeResult()

    async def _astream(inputs, **kwargs):
        captured.setdefault("astream", []).append(dict(kwargs))
        yield _FakeResult()

    return types.SimpleNamespace(ainvoke=_ainvoke, astream=_astream)


class TestDefaultAgentNameRides:
    """①身份补透：默认 agent_name 随调用带出，调用方显式值优先。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_default_agent_name_reaches_runtime():
        captured: dict = {}
        layer = AgentCoreModelLayer(
            runtime=_make_runtime(captured), default_agent_name="问答智能体"
        )
        layer.invoke([{"role": "user", "content": "hi"}], "m1", "s1")
        assert captured["ainvoke"][0]["agent_name"] == "问答智能体"

    @staticmethod
    @pytest.mark.asyncio
    async def test_caller_agent_name_wins():
        captured: dict = {}
        layer = AgentCoreModelLayer(
            runtime=_make_runtime(captured), default_agent_name="默认名"
        )
        layer.invoke(
            [{"role": "user", "content": "hi"}], "m1", "s1", agent_name="调用方名"
        )
        assert captured["ainvoke"][0]["agent_name"] == "调用方名"

    @staticmethod
    @pytest.mark.asyncio
    async def test_no_default_name_keeps_wire_unchanged():
        captured: dict = {}
        layer = AgentCoreModelLayer(runtime=_make_runtime(captured))
        layer.invoke([{"role": "user", "content": "hi"}], "m1", "s1")
        assert "agent_name" not in captured["ainvoke"][0]


class TestAmbientSpanRefsCapture:
    """refs 捕获：活动 span → 三键 hex；无合法 span → 空（wire 不变）。"""

    @staticmethod
    def test_refs_inside_active_span():
        span = _make_recording_span("node-llm")
        token = otel_context.attach(otel_trace.set_span_in_context(span))
        try:
            refs = _ambient_span_refs()
        finally:
            otel_context.detach(token)
            span.end()
        trace_hex, span_hex = _hex_ids(span)
        assert refs == {
            "parent_trace_id": trace_hex,
            "parent_span_id": span_hex,
            "parent_trace_flags": f"{span.get_span_context().trace_flags:02x}",
        }

    @staticmethod
    def test_refs_empty_without_valid_span():
        assert _ambient_span_refs() == {}


class TestRefsRideModelCalls:
    """同步入口注入：refs 随 kwargs 到 runtime；调用方显式值优先。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_invoke_injects_refs_into_runtime_kwargs():
        captured: dict = {}
        layer = AgentCoreModelLayer(runtime=_make_runtime(captured))
        span = _make_recording_span("node-llm")
        token = otel_context.attach(otel_trace.set_span_in_context(span))
        try:
            layer.invoke([{"role": "user", "content": "hi"}], "m1", "s1")
        finally:
            otel_context.detach(token)
            span.end()
        trace_hex, span_hex = _hex_ids(span)
        assert captured["ainvoke"], "runtime.ainvoke must be called"
        assert captured["ainvoke"][0]["parent_span_id"] == span_hex
        assert captured["ainvoke"][0]["parent_trace_id"] == trace_hex
        assert "parent_trace_flags" in captured["ainvoke"][0]

    @staticmethod
    @pytest.mark.asyncio
    async def test_stream_injects_refs_into_runtime_kwargs():
        captured: dict = {}
        layer = AgentCoreModelLayer(runtime=_make_runtime(captured))
        span = _make_recording_span("node-llm")
        token = otel_context.attach(otel_trace.set_span_in_context(span))
        try:
            for _item in layer.stream([{"role": "user", "content": "hi"}], "m1", "s1"):
                break
        finally:
            otel_context.detach(token)
            span.end()
        trace_hex, span_hex = _hex_ids(span)
        assert captured["astream"], "runtime.astream must be called"
        assert captured["astream"][0]["parent_span_id"] == span_hex
        assert captured["astream"][0]["parent_trace_id"] == trace_hex

    @staticmethod
    @pytest.mark.asyncio
    async def test_caller_explicit_refs_win_over_ambient():
        captured: dict = {}
        layer = AgentCoreModelLayer(runtime=_make_runtime(captured))
        span = _make_recording_span("node-llm")
        token = otel_context.attach(otel_trace.set_span_in_context(span))
        try:
            layer.invoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                parent_trace_id="0" * 32,
                parent_span_id="1" * 16,
            )
        finally:
            otel_context.detach(token)
            span.end()
        assert captured["ainvoke"][0]["parent_span_id"] == "1" * 16
        assert captured["ainvoke"][0]["parent_trace_id"] == "0" * 32
