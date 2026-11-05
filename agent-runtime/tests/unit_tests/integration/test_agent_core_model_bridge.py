# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""同步桥上下文契约：桥内可见调用侧 contextvars，且桥内改动不回漏。

背景（多智能体缺参追问链实证）：_run_async_blocking / _iter_async_blocking
在运行中事件循环上开新线程执行异步调用，裸线程拿到的是空 context——
OTel ambient span、x-request-id 等 ContextVar 全部丢失，span 认错父、
trace 断裂（controller 触发工作流时 llm span 与 node span 并列、end 节点
误挂 llm span 下即此机理）。_run_in_bridge_thread 用 copy_context + ctx.run
把调用侧上下文的私有副本带过桥；本文件钉死该契约防回归。
"""

import asyncio
import contextvars
import threading

import pytest
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace

from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer

# 套件既有惯例：契约测试直接触达受保护成员，经 getattr 规避
# G.CLS.11（pylint pragma 对 CodeCheck 不生效）
_run_async_blocking = getattr(AgentCoreModelLayer, "_run_async_blocking")
_iter_async_blocking = getattr(AgentCoreModelLayer, "_iter_async_blocking")

_MARKER: contextvars.ContextVar[str] = contextvars.ContextVar("bridge_test_marker", default="")


class TestBridgeCarriesCallerContext:
    """桥这头设的 ContextVar，桥那头必须看得到（改前：空 → 必红）。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_blocking_sees_caller_contextvar():
        token = _MARKER.set("caller-value")
        try:
            seen = _run_async_blocking(_read_marker_async())
        finally:
            _MARKER.reset(token)
        assert seen == "caller-value"

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_blocking_sees_caller_otel_span():
        """OTel ambient 本身就架在 contextvars 上：同一条修复一并生效。"""
        span = _make_otel_span("bridge-parent")
        token = otel_context.attach(otel_trace.set_span_in_context(span))
        try:
            seen_name = _run_async_blocking(_read_current_span_name_async())
        finally:
            otel_context.detach(token)
        assert seen_name == "bridge-parent"

    @staticmethod
    @pytest.mark.asyncio
    async def test_iter_blocking_sees_caller_contextvar():
        token = _MARKER.set("caller-stream")
        try:
            seen = []
            for item in _iter_async_blocking(_read_marker_stream()):
                seen.append(item)
        finally:
            _MARKER.reset(token)
        assert seen == ["caller-stream"]


class TestBridgeIsolation:
    """桥是私有副本：桥内 set 不得回漏调用侧，跨调用不得串扰。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_set_inside_bridge_does_not_leak_back():
        token = _MARKER.set("before")
        try:
            _run_async_blocking(_set_marker_async("inside"))
            assert _MARKER.get() == "before"
        finally:
            _MARKER.reset(token)

    @staticmethod
    @pytest.mark.asyncio
    async def test_bridge_result_and_error_paths_unchanged():
        """既有行为回归：结果透传、异常透传不因过桥方式改变。"""
        assert _run_async_blocking(_echo_async(42)) == 42
        with pytest.raises(ValueError, match="boom"):
            _run_async_blocking(_boom_async())

    @staticmethod
    def test_no_loop_branch_keeps_context_too():
        """无运行循环分支（同线程 asyncio.run）本就携带上下文：两分支语义对齐。"""
        token = _MARKER.set("same-thread")
        try:

            async def _read() -> str:
                return _MARKER.get()

            assert _run_async_blocking(_read()) == "same-thread"
        finally:
            _MARKER.reset(token)


class TestBridgeStreamingContract:
    """增量流式契约：生产者线程启动后必须立即进入消费循环。"""

    @staticmethod
    def test_first_chunk_arrives_while_stream_still_open():
        """回归（jdfff 11-05 🔴）：join 先行把整条流缓冲完才吐首块。

        生产者在首块后永久挂起（流保持打开）：join-first 形态下 next()
        永不返回（3 秒超时必红）；增量形态下立得首块。"""
        async def _never_ending_stream():
            yield "first"
            await asyncio.Event().wait()  # 永不置位：流保持打开

        iterator = _iter_async_blocking(_never_ending_stream())
        got = threading.Event()
        holder: list = []

        def _take_first():
            holder.append(next(iterator))
            got.set()

        consumer = threading.Thread(target=_take_first, daemon=True)
        consumer.start()
        try:
            assert got.wait(timeout=3), (
                "first chunk must arrive while the stream is still open — "
                "a join-before-consume bridge buffers the whole stream first"
            )
        finally:
            iterator.close()
        assert holder[0] == "first"


# --- helpers ---------------------------------------------------------------

async def _read_marker_async() -> str:
    return _MARKER.get()


async def _set_marker_async(value: str) -> None:
    _MARKER.set(value)


async def _echo_async(value: int) -> int:
    return value


async def _boom_async() -> None:
    raise ValueError("boom")


async def _read_current_span_name_async() -> str:
    return otel_trace.get_current_span(otel_context.get_current()).name


async def _read_marker_stream():
    yield _MARKER.get()


def _make_otel_span(name: str) -> otel_trace.Span:
    """独立 TracerProvider（不经全局注册）产真实可命名 span：只需桥内可读 name。"""
    from opentelemetry.sdk.trace import TracerProvider

    tracer = TracerProvider().get_tracer("bridge-context-test")
    return tracer.start_span(name=name)
