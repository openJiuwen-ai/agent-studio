# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""DEF-03 / COM-05 Runtime 入口机制测试（SYNC-01 P3.2 从旧分支移植）。

覆盖：Header 选值与早期日志（§6.1）、生命周期与隔离（§6.2）、禁止行为回归
（§6.3）、COM-05 会话来源矩阵 / Header 回写 / 异常收口 / body 类型守卫。

SYNC-01 P3.2 adapt（2026-09-19）：
- 生成 ID 为 uuid.uuid4().hex（32 位十六进制，sync_01 OTel 直通保留），
  非 str(uuid.uuid4())（36 位带横线）；测试断言 32-hex。
- error 收口响应为 sync_01 裸 JSONResponse（error_code=internal_error），
  非 COM-03 canonical8（openjiuwen.12100004）—— COM-03 在 S3 后做。
  测试断言 internal_error + X-Request-Id header + 日志固定字段非空。

sync_01 现有 test_request_context_logging.py 的 OTel / jiuwen / 日志格式测试
保留不变，本文件补 DEF-03/COM-05 行为测试，不重复 OTel/format 覆盖。
"""

import asyncio
import logging
import re
import unittest
from unittest.mock import patch

from agent_runtime.common.logging_context import (
    install_log_formatter_patch,
    install_request_id_log_record_factory,
)
from agent_runtime.context import middleware as middleware_mod
from agent_runtime.context.middleware import RequestContextMiddleware
from agent_runtime.context.request_context import RequestContext, _request_ctx
from openjiuwen.core.common.logging import (
    get_session_id,
    reset_session_id,
    set_session_id,
)
from jiuwen.serve.common.context import request_ctx as _jiuwen_request_ctx
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.testclient import TestClient

from opentelemetry import context as otel_context, trace as otel_trace
from opentelemetry.trace import SpanContext, TraceFlags, TraceState
from opentelemetry.trace.span import NonRecordingSpan

_HEX32_PATTERN = re.compile(r"^[0-9a-f]{32}$")

# 可区分的外层 OTel trace_id，用于验证 middleware attach/detach 不误清外层
_OUTER_OTEL_TRACE_ID = 0x1234567890ABCDEF1234567890ABCDEF


def _outer_span():
    return NonRecordingSpan(
        SpanContext(
            trace_id=_OUTER_OTEL_TRACE_ID,
            span_id=0x1,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state=TraceState(),
        )
    )


class _OuterCarriers:
    """四载体外层值快照 + tokens，供建立期/恢复期测试断言全部恢复。

    审视 §2.2：不能只查 core trace/_request_ctx 就概括为四层无泄漏，需逐层
    断言已建立载体恢复、未建立载体不误 detach/reset。
    """

    def __init__(self):
        self.jiuwen_token = None
        self.otel_token = None
        self.ctx_token = None
        self.trace_token = None
        self.outer_ctx = RequestContext(request_id="outer-req")

    def __enter__(self):
        self.jiuwen_token = _jiuwen_request_ctx.set({"marker": "outer"})
        self.otel_token = otel_context.attach(otel_trace.set_span_in_context(_outer_span()))
        self.ctx_token = _request_ctx.set(self.outer_ctx)
        self.trace_token = set_session_id("outer-trace")
        return self

    def assert_restored(self, testcase):
        """断言四载体均恢复到外层值。"""
        testcase.assertEqual(get_session_id(), "outer-trace", "core trace 未恢复")
        testcase.assertIs(_request_ctx.get(), self.outer_ctx, "_request_ctx 未恢复")
        testcase.assertEqual(
            _jiuwen_request_ctx.get(), {"marker": "outer"}, "_jiuwen_request_ctx 未恢复"
        )
        span = otel_trace.get_current_span()
        testcase.assertEqual(
            span.get_span_context().trace_id,
            _OUTER_OTEL_TRACE_ID,
            "OTel span 未恢复（外层 detach 丢失或被误清）",
        )

    def __exit__(self, *exc):
        if self.trace_token is not None:
            reset_session_id(self.trace_token)
        if self.ctx_token is not None:
            _request_ctx.reset(self.ctx_token)
        if self.otel_token is not None:
            otel_context.detach(self.otel_token)
        if self.jiuwen_token is not None:
            _jiuwen_request_ctx.reset(self.jiuwen_token)
        return False



def _make_record(level: int, msg: str) -> logging.LogRecord:
    """用全局 LogRecordFactory 构造一条记录，复现当前上下文注入的字段值。"""
    return logging.getLogRecordFactory()(
        "workflow",
        level,
        __file__,
        1,
        msg,
        (),
        None,
    )


class _CapturingLogger:
    """假 workflow_logger：warning 时用全局 factory 构造真实 LogRecord 并收集。

    用于验证"告警 emit 时刻上下文是否已建立"——factory 读当前 ContextVar
    状态注入 trace_id/execution_id/request_id，据此判断早期日志是否带 ID。
    """

    def __init__(self):
        self.records: list[logging.LogRecord] = []

    def warning(self, msg, *args, **kwargs):
        self.records.append(_make_record(logging.WARNING, str(msg)))

    def info(self, msg, *args, **kwargs):
        self.records.append(_make_record(logging.INFO, str(msg)))

    def error(self, msg, *args, **kwargs):
        self.records.append(_make_record(logging.ERROR, str(msg)))

    def debug(self, *args, **kwargs):
        pass


class _RequestMixin:
    """共享的请求构造辅助（_body_receiver / _make_request）。"""

    @staticmethod
    def _body_receiver(body: bytes):
        received = False

        async def receive():
            nonlocal received
            if received:
                return {"type": "http.request", "body": b"", "more_body": False}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        return receive

    @staticmethod
    def _make_request(
        headers: list[tuple[str, str]], body: bytes = b"", method: str = "POST"
    ):
        return Request(
            {
                "type": "http",
                "method": method,
                "path": "/v1/orchestration/ir/execute",
                "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
            },
            receive=_RequestMixin._body_receiver(body),
        )


# 流式故障观察由 test_streaming_generator_fault_phases_observe_request_snapshot
# 内联 generator（带 observations 列表），不再用模块级 endpoint helper。


class Def03SelectionAndLifecycleTest(unittest.IsolatedAsyncioTestCase, _RequestMixin):
    """DEF-03 §6.1/§6.2/§6.3：Header 选值、早期日志、生命周期与隔离、禁止回归。"""

    def setUp(self):
        install_request_id_log_record_factory()
        install_log_formatter_patch()

    # ─────────────────────── §6.1 Header 选值与早期日志 ───────────────────────

    async def test_body_parse_warning_carries_ids(self):
        """JSON 解析失败告警必须带本次 execution_id/request_id/trace_id。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        capturer = _CapturingLogger()

        async def call_next(request):
            return Response("ok")

        request = self._make_request(
            headers=[("x-request-id", "req-1"), ("x-execution-id", "exec-1")],
            body=b"not-json",
        )
        with patch.object(middleware_mod, "workflow_logger", capturer):
            await middleware.dispatch(request, call_next)

        warnings = [r for r in capturer.records if r.levelno == logging.WARNING]
        body_warnings = [r for r in warnings if "parse" in r.getMessage().lower()]
        self.assertTrue(body_warnings, "应有 JSON 解析失败告警")
        rec = body_warnings[0]
        self.assertEqual(rec.execution_id, "exec-1")
        self.assertEqual(rec.request_id, "req-1")
        self.assertEqual(rec.trace_id, "req-1")

    async def test_trace_id_from_traceid_header(self):
        """入站带 TraceID 时 trace_id 跟随 TraceID，不再跟随 conversation_id。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            captured["trace_id"] = rec.trace_id
            captured["conversation_id"] = getattr(rec, "conversation_id", "")
            return Response("ok")

        request = self._make_request(
            headers=[
                ("x-request-id", "req-1"),
                ("x-execution-id", "exec-1"),
                ("TraceID", "t-abc"),
            ],
            body=b'{"conversationId":"conv-9"}',
        )
        await middleware.dispatch(request, call_next)

        self.assertEqual(captured["trace_id"], "t-abc")
        self.assertEqual(captured["conversation_id"], "conv-9")

    async def test_trace_id_missing_falls_back_to_request_id(self):
        """TraceID 缺失时以有效 request_id 初始化 trace_id。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            captured["trace_id"] = rec.trace_id
            return Response("ok")

        request = self._make_request(
            headers=[("x-request-id", "req-1"), ("x-execution-id", "exec-1")],
            body=b'{"conversationId":"conv-9"}',
        )
        await middleware.dispatch(request, call_next)

        self.assertEqual(captured["trace_id"], "req-1")

    async def test_illegal_header_warning_carries_replacement_not_original(self):
        """非法 Header 告警带替代 ID，不出现非法原值。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        capturer = _CapturingLogger()

        async def call_next(request):
            return Response("ok")

        illegal_value = "x" * 65  # 65 字符，超长非法
        request = self._make_request(
            headers=[("x-request-id", "req-1"), ("x-execution-id", illegal_value)],
            body=b"",
        )
        with patch.object(middleware_mod, "workflow_logger", capturer):
            await middleware.dispatch(request, call_next)

        warnings = [r for r in capturer.records if r.levelno == logging.WARNING]
        self.assertTrue(warnings, "应有非法 Header 告警")
        combined = " ".join(r.getMessage() for r in warnings)
        self.assertNotIn(illegal_value, combined)
        # 替代后的 execution_id 应是合法 32-hex（非空、非原值）
        self.assertTrue(warnings[0].execution_id)
        self.assertNotEqual(warnings[0].execution_id, illegal_value)

    async def test_execution_id_missing_generates_uuid(self):
        """X-Execution-Id 缺失时生成合法 UUID（sync_01: 32 位 hex），且不等于其他关联 ID。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            captured["execution_id"] = rec.execution_id
            captured["request_id"] = rec.request_id
            return Response("ok")

        request = self._make_request(
            headers=[("x-request-id", "req-1")],
            body=b"",
        )
        await middleware.dispatch(request, call_next)

        self.assertTrue(captured["execution_id"])
        self.assertRegex(captured["execution_id"], _HEX32_PATTERN)  # sync_01 .hex
        self.assertNotEqual(captured["execution_id"], captured["request_id"])

    async def test_header_boundary_1_and_64_chars_valid(self):
        """1 字符和 64 字符合法边界值原样通过。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        max_val = "a" * 64
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            captured["execution_id"] = rec.execution_id
            captured["request_id"] = rec.request_id
            captured["trace_id"] = rec.trace_id
            return Response("ok")

        request = self._make_request(
            headers=[
                ("x-request-id", "r"),
                ("x-execution-id", "e"),
                ("TraceID", max_val),
            ],
            body=b"",
        )
        await middleware.dispatch(request, call_next)

        self.assertEqual(captured["request_id"], "r")
        self.assertEqual(captured["execution_id"], "e")
        self.assertEqual(captured["trace_id"], max_val)

    async def test_header_boundary_65_chars_invalid(self):
        """65 字符按非法处理，生成替代值。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        over = "a" * 65
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            captured["request_id"] = rec.request_id
            return Response("ok")

        request = self._make_request(
            headers=[("x-request-id", over), ("x-execution-id", "exec-1")],
            body=b"",
        )
        await middleware.dispatch(request, call_next)

        self.assertNotEqual(captured["request_id"], over)
        self.assertTrue(captured["request_id"])

    # ─────────────────────── §6.2 生命周期与隔离 ───────────────────────

    async def test_context_reset_after_request(self):
        """call_next 正常返回后 trace 与外层 _request_ctx 均恢复原值。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        outer_ctx = RequestContext(request_id="outer-req")
        outer_ctx_token = _request_ctx.set(outer_ctx)
        outer_token = set_session_id("outer-trace")
        try:
            self.assertEqual(get_session_id(), "outer-trace")

            async def call_next(request):
                self.assertEqual(get_session_id(), "req-1")
                self.assertEqual(_request_ctx.get().request_id, "req-1")
                return Response("ok")

            request = self._make_request(
                headers=[("x-request-id", "req-1")],
                body=b"",
            )
            await middleware.dispatch(request, call_next)
            self.assertEqual(get_session_id(), "outer-trace")
            self.assertIs(_request_ctx.get(), outer_ctx)
        finally:
            reset_session_id(outer_token)
            _request_ctx.reset(outer_ctx_token)

    async def test_context_restored_on_exception(self):
        """call_next 抛异常时仍恢复。COM-05 起异常在 try 内收口为 500 响应，
        不再向调用方传播（DEF-03 的传播语义被 §3.5 内层收口取代）。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        outer_ctx = RequestContext(request_id="outer-req")
        outer_ctx_token = _request_ctx.set(outer_ctx)
        outer_token = set_session_id("outer-trace")
        try:

            async def call_next(request):
                raise ValueError("boom")

            request = self._make_request(
                headers=[("x-request-id", "req-1")],
                body=b"",
            )
            resp = await middleware.dispatch(request, call_next)
            self.assertEqual(resp.status_code, 500)
            self.assertEqual(resp.headers.get("x-request-id"), "req-1")
            self.assertEqual(get_session_id(), "outer-trace")
            self.assertIs(_request_ctx.get(), outer_ctx)
        finally:
            reset_session_id(outer_token)
            _request_ctx.reset(outer_ctx_token)

    async def test_nested_dispatch_restores_outer_trace(self):
        """嵌套调用 LIFO 恢复，不覆盖外层 trace 与请求 ctx。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        outer_ctx = RequestContext(request_id="outer-req")
        outer_ctx_token = _request_ctx.set(outer_ctx)
        outer_token = set_session_id("outer-trace")
        try:
            inner_captured = {}

            async def outer_call_next(request):
                self.assertEqual(get_session_id(), "req-1")

                async def inner_call_next(inner_request):
                    inner_captured["trace"] = get_session_id()
                    return Response("ok")

                inner_request = self._make_request(
                    headers=[("x-request-id", "req-2")],
                    body=b"",
                )
                await middleware.dispatch(inner_request, inner_call_next)
                self.assertEqual(get_session_id(), "req-1")
                self.assertEqual(_request_ctx.get().request_id, "req-1")
                return Response("ok")

            request = self._make_request(
                headers=[("x-request-id", "req-1")],
                body=b"",
            )
            await middleware.dispatch(request, outer_call_next)
            self.assertEqual(get_session_id(), "outer-trace")
            self.assertIs(_request_ctx.get(), outer_ctx)
            self.assertEqual(inner_captured["trace"], "req-2")
        finally:
            reset_session_id(outer_token)
            _request_ctx.reset(outer_ctx_token)

    async def test_concurrent_dispatch_no_cross_contamination(self):
        """两个并发请求各自记录自身 ID，不串号。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        results = {}
        barrier = asyncio.Event()

        async def call_next_a(request):
            await barrier.wait()
            rec = _make_record(logging.INFO, "m")
            results["a"] = rec.execution_id
            return Response("ok")

        async def call_next_b(request):
            rec = _make_record(logging.INFO, "m")
            results["b"] = rec.execution_id
            barrier.set()
            return Response("ok")

        req_a = self._make_request(
            headers=[("x-request-id", "ra-1"), ("x-execution-id", "exec-A")],
            body=b"",
        )
        req_b = self._make_request(
            headers=[("x-request-id", "rb-1"), ("x-execution-id", "exec-B")],
            body=b"",
        )
        await asyncio.gather(
            middleware.dispatch(req_a, call_next_a),
            middleware.dispatch(req_b, call_next_b),
        )
        self.assertEqual(results["a"], "exec-A")
        self.assertEqual(results["b"], "exec-B")

    async def test_outside_request_fields_empty(self):
        """请求外构造 LogRecord 时四字段为空，不出现 default_trace_id 哨兵。"""
        self.assertEqual(get_session_id(), "default_trace_id")
        rec = _make_record(logging.INFO, "m")
        self.assertEqual(rec.trace_id, "")
        self.assertEqual(rec.execution_id, "")
        self.assertEqual(rec.request_id, "")
        self.assertEqual(getattr(rec, "conversation_id", ""), "")

    async def test_warning_logger_exception_restores_context(self):
        """告警 logger 抛异常时两 token 仍 reset，不串号。

        COM-05 起异常在 try 内收口为 500 响应，不再向调用方传播。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        outer_token = set_session_id("outer-trace")
        try:
            capturer = _CapturingLogger()

            def raise_on_warning(msg, *args, **kwargs):
                raise RuntimeError("logger broke")

            capturer.warning = raise_on_warning

            async def call_next(request):
                return Response("ok")

            # 非法 header 会触发 warning → 抛异常 → except 收口 + finally reset
            request = self._make_request(
                headers=[("x-request-id", "req-1"), ("x-execution-id", "x" * 65)],
                body=b"",
            )
            with patch.object(middleware_mod, "workflow_logger", capturer):
                resp = await middleware.dispatch(request, call_next)
            self.assertEqual(resp.status_code, 500)
            self.assertEqual(resp.headers.get("x-request-id"), "req-1")
            self.assertEqual(get_session_id(), "outer-trace")
        finally:
            reset_session_id(outer_token)

    async def test_second_reset_runs_when_first_reset_raises(self):
        """trace reset 抛异常时，第二个 reset 仍执行并恢复 _request_ctx。

        嵌套 try/finally 保证：即使 reset_session_id 因编程错误抛出，
        _request_ctx.reset 也必须被尝试；reset 异常向上传播不被吞掉。
        """
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        outer_ctx = RequestContext(request_id="outer-req")
        outer_ctx_token = _request_ctx.set(outer_ctx)
        outer_token = set_session_id("outer-trace")
        try:

            async def call_next(request):
                return Response("ok")

            request = self._make_request(
                headers=[("x-request-id", "req-1")],
                body=b"",
            )

            def broken_reset(token):
                raise RuntimeError("reset failed")

            with (
                patch.object(middleware_mod, "reset_session_id", broken_reset),
                self.assertRaises(RuntimeError),
            ):
                await middleware.dispatch(request, call_next)

            # 关键断言：第一个 reset 抛异常后，第二个 reset 仍已执行
            self.assertIs(_request_ctx.get(), outer_ctx)
            self.assertEqual(_request_ctx.get().request_id, "outer-req")
        finally:
            reset_session_id(outer_token)
            _request_ctx.reset(outer_ctx_token)

    async def test_sequential_requests_no_cross_talk(self):
        """同一事件循环连续处理两个请求，第二个不读取第一个字段。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next_a(request):
            rec = _make_record(logging.INFO, "m")
            captured["a_exec"] = rec.execution_id
            return Response("ok")

        async def call_next_b(request):
            rec = _make_record(logging.INFO, "m")
            captured["b_exec"] = rec.execution_id
            captured["b_trace"] = rec.trace_id
            return Response("ok")

        await middleware.dispatch(
            self._make_request(
                headers=[("x-request-id", "ra-1"), ("x-execution-id", "exec-A")],
                body=b"",
            ),
            call_next_a,
        )
        # 请求 A 结束后上下文已清回默认，不残留
        self.assertEqual(_request_ctx.get().execution_id, "")
        await middleware.dispatch(
            self._make_request(
                headers=[("x-request-id", "rb-1"), ("x-execution-id", "exec-B")],
                body=b"",
            ),
            call_next_b,
        )
        self.assertEqual(captured["a_exec"], "exec-A")
        self.assertEqual(captured["b_exec"], "exec-B")
        self.assertEqual(captured["b_trace"], "rb-1")

    async def test_whitespace_and_illegal_chars_treated_as_missing(self):
        """空白、换行、制表符、控制字符及非法字符 Header 按缺失处理。"""
        for bad in [
            "abc def",  # 空格
            "abc\tdef",  # 制表符
            "abc\ndef",  # 换行
            "abc\x00def",  # 控制字符
            "abc/def",  # 非法字符 /
            "abc#def",  # 非法字符 #
        ]:
            self.assertFalse(middleware_mod._valid_header(bad), f"{bad!r} 应判定为非法")
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            captured["request_id"] = rec.request_id
            return Response("ok")

        request = self._make_request(
            headers=[("x-request-id", "abc def"), ("x-execution-id", "exec-1")],
            body=b"",
        )
        await middleware.dispatch(request, call_next)
        self.assertNotEqual(captured["request_id"], "abc def")
        self.assertTrue(captured["request_id"])

    async def test_triple_carrier_same_value(self):
        """三个合法 Header 在 request.state、RequestContext、LogRecord 三处同值。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            ctx = _request_ctx.get()
            captured["state"] = (
                request.state.execution_id,
                request.state.trace_id,
                request.state.request_id,
            )
            captured["ctx"] = (ctx.execution_id, ctx.trace_id, ctx.request_id)
            captured["record"] = (rec.execution_id, rec.trace_id, rec.request_id)
            return Response("ok")

        request = self._make_request(
            headers=[
                ("x-request-id", "rid-1"),
                ("x-execution-id", "eid-1"),
                ("TraceID", "tid-1"),
            ],
            body=b"",
        )
        await middleware.dispatch(request, call_next)
        expected = ("eid-1", "tid-1", "rid-1")
        self.assertEqual(captured["state"], expected)
        self.assertEqual(captured["ctx"], expected)
        self.assertEqual(captured["record"], expected)

    async def test_streaming_response_chunks_hold_request_snapshot(self):
        """真实 StreamingResponse：首块与父任务 reset 后的后续块都持有请求快照。

        Starlette BaseHTTPMiddleware 把下游应用跑在 call_next 内创建的子任务中，
        该子任务继承请求 ContextVar 快照——父任务 finally reset 不影响流式块。
        本测试固定该实测行为；若未来框架版本变化导致不再继承，应转为阻断项。
        """
        from starlette.applications import Starlette
        from starlette.routing import Route

        observations = []

        async def stream_endpoint(request):
            async def gen():
                observations.append(
                    ("chunk1", _request_ctx.get().request_id, get_session_id())
                )
                yield b"a"
                await asyncio.sleep(0.05)
                observations.append(
                    ("chunk2", _request_ctx.get().request_id, get_session_id())
                )
                yield b"b"

            return StreamingResponse(gen())

        app = Starlette(routes=[Route("/s", stream_endpoint, methods=["GET"])])
        app.add_middleware(RequestContextMiddleware)
        client = TestClient(app)
        resp = client.get(
            "/s", headers={"x-request-id": "req-stream", "TraceID": "trace-stream"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "ab")
        self.assertEqual(len(observations), 2)
        for name, rid, sid in observations:
            self.assertEqual(rid, "req-stream", f"{name} 应持有请求快照")
            self.assertEqual(sid, "trace-stream", f"{name} 应持有 trace 快照")

    # ─────────── §6.2.1 建立期故障恢复（审视 §1.1 + §2.2 全 4 载体） ───────────

    async def test_establish_failure_set_session_id_resets_all_carriers(self):
        """建立期 set_session_id（最后一步）抛错时，已得的 _jiuwen/OTel/_request_ctx
        token 由 finally 条件逆序恢复；core trace 因 set_session_id 未成功而未变更。

        审视 §2.2：逐层断言四载体恢复，不只查 core trace/_request_ctx。
        """
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)

        async def call_next(request):  # 不应到达——set_session_id 抛错在建立期
            return Response("ok")

        request = self._make_request(headers=[("x-request-id", "req-1")], body=b"")

        def broken_set(trace_id):
            raise RuntimeError("set_session_id failed")

        with _OuterCarriers() as outer:
            with patch.object(middleware_mod, "set_session_id", broken_set):
                resp = await middleware.dispatch(request, call_next)
            self.assertEqual(resp.status_code, 500)
            outer.assert_restored(self)

    async def test_establish_failure_otel_attach_resets_obtained_carriers(self):
        """OTel attach 抛错时，已得的 _jiuwen token 恢复；其后未建立的 OTel/
        _request_ctx/core trace 不被误 detach/reset（仍为外层值）。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)

        async def call_next(request):  # 不应到达
            return Response("ok")

        request = self._make_request(headers=[("x-request-id", "req-1")], body=b"")

        def broken_attach(context):
            raise RuntimeError("otel attach failed")

        with _OuterCarriers() as outer:
            # patch otel_context.attach 抛错；detach 保持真实（finally 对 _otel_token=None
            # 跳过，不会误清外层 OTel）
            with patch.object(middleware_mod.otel_context, "attach", broken_attach):
                resp = await middleware.dispatch(request, call_next)
            self.assertEqual(resp.status_code, 500)
            outer.assert_restored(self)

    # ─────────── §6.2.2 流式：同任务恢复 + 子任务故障观察（审视 §2.1） ───────────

    async def test_streaming_dispatch_restores_parent_carriers(self):
        """同任务恢复：call_next 返回 StreamingResponse 后父任务 finally 恢复四载体。

        审视 §2.1：直接 dispatch（同任务），不依赖 TestClient 的另一执行上下文；
        生成器不消费（call_next 仅返回 StreamingResponse 对象，finally 已跑）。
        失效注入反证：若 reset_session_id 为空操作，本测试因 core trace 未恢复而失败。
        """
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)

        async def call_next(request):
            async def gen():
                yield b"x"  # 不消费——仅使 gen 成为 async generator

            return StreamingResponse(gen())

        request = self._make_request(headers=[("x-request-id", "req-s")], body=b"")

        with _OuterCarriers() as outer:
            resp = await middleware.dispatch(request, call_next)
            self.assertEqual(resp.status_code, 200)
            outer.assert_restored(self)

    async def test_streaming_generator_fault_phases_observe_request_snapshot(self):
        """流式子任务故障观察：三阶段异常确实发生 + chunk 计数 + 子任务持请求快照。

        审视 §2：观察写在 raise 之前→删 raise 测试仍过（不能证明异常发生）。
        改为在 except/finally 记录异常类型 + chunk 计数，逐阶段断言：
        before_first→RuntimeError+0 chunk；after_first→RuntimeError+1 chunk；
        cancelled→CancelledError+1 chunk。删 raise 则 exc_type=None→断言失败。
        """
        from starlette.applications import Starlette
        from starlette.routing import Route

        observations = []

        def make_endpoint(phase):
            async def endpoint(request):
                async def gen():
                    chunks = 0
                    exc_type = None
                    try:
                        if phase == "before_first":
                            raise RuntimeError("before first chunk")
                        yield b"a"
                        chunks += 1
                        if phase == "after_first":
                            raise RuntimeError("after first chunk")
                        if phase == "cancelled":
                            raise asyncio.CancelledError()
                        yield b"b"  # 正常完成路径（故障阶段不可达）
                        chunks += 1
                    except BaseException as e:
                        exc_type = type(e).__name__
                    finally:
                        observations.append(
                            (phase, exc_type, chunks,
                             _request_ctx.get().request_id, get_session_id())
                        )

                return StreamingResponse(gen())

            return endpoint

        expected = {
            "before_first": ("RuntimeError", 0),
            "after_first": ("RuntimeError", 1),
            "cancelled": ("CancelledError", 1),
        }
        for phase in ("before_first", "after_first", "cancelled"):
            observations.clear()
            app = Starlette(routes=[Route("/s", make_endpoint(phase), methods=["GET"])])
            app.add_middleware(RequestContextMiddleware)
            client = TestClient(app, raise_server_exceptions=False)
            client.get(
                "/s",
                headers={"x-request-id": "req-s", "TraceID": "trace-s"},
            )
            self.assertTrue(observations, f"{phase}: 生成器未记录任何观测")
            obs_phase, obs_exc, obs_chunks, obs_rid, obs_sid = observations[-1]
            self.assertEqual(obs_phase, phase, f"{phase}: 阶段标记不符")
            self.assertEqual(
                obs_exc, expected[phase][0],
                f"{phase}: 异常类型应为 {expected[phase][0]}，实得 {obs_exc}",
            )
            self.assertEqual(
                obs_chunks, expected[phase][1],
                f"{phase}: chunk 计数应为 {expected[phase][1]}，实得 {obs_chunks}",
            )
            self.assertEqual(obs_rid, "req-s", f"{phase}: 子任务未持 request_id 快照")
            self.assertEqual(obs_sid, "trace-s", f"{phase}: 子任务未持 trace_id 快照")

    async def test_streaming_exception_propagates_to_framework_boundary(self):
        """流式生成器异常(非吞)到达 Starlette 框架边界→TestClient 传播 RuntimeError。

        审视 §2：非吞异常夹具，补"首帧前后/响应迭代失败到达框架边界"。
        生成器不带 except，异常真实传播（非被 `except BaseException` 吞掉）；
        ``raise_server_exceptions=True`` 使 Starlette 不吞流式异常，传播到 TestClient。
        反证：删 raise→生成器正常完成→TestClient 不抛→assertRaises 失败。
        """
        from starlette.applications import Starlette
        from starlette.routing import Route

        observations = []

        def make_endpoint(when):  # when: "before_first" / "after_first"
            async def endpoint(request):
                async def gen():
                    observations.append(
                        (when, _request_ctx.get().request_id, get_session_id())
                    )
                    if when == "before_first":
                        raise RuntimeError("before first chunk")
                    yield b"a"
                    raise RuntimeError("after first chunk")

                return StreamingResponse(gen())

            return endpoint

        for when in ("before_first", "after_first"):
            observations.clear()
            app = Starlette(routes=[Route("/s", make_endpoint(when), methods=["GET"])])
            app.add_middleware(RequestContextMiddleware)
            client = TestClient(app, raise_server_exceptions=True)
            with self.assertRaises(RuntimeError):
                client.get(
                    "/s", headers={"x-request-id": "req-s", "TraceID": "trace-s"}
                )
            # 异常传播到框架边界（TestClient 收到 RuntimeError）；子任务持请求快照
            self.assertTrue(observations, f"{when}: 生成器未执行")
            self.assertEqual(
                observations[0][1], "req-s", f"{when}: 子任务未持 request_id 快照"
            )
            self.assertEqual(
                observations[0][2], "trace-s", f"{when}: 子任务未持 trace_id 快照"
            )

    # ─────────────────────── §6.3 禁止行为回归 ───────────────────────

    async def test_conversation_id_does_not_override_trace(self):
        """含 conversationId 的请求也保持 Header 确定的 trace。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            rec = _make_record(logging.INFO, "m")
            captured["trace_id"] = rec.trace_id
            captured["conversation_id"] = getattr(rec, "conversation_id", "")
            return Response("ok")

        request = self._make_request(
            headers=[
                ("x-request-id", "req-1"),
                ("x-execution-id", "exec-1"),
                ("TraceID", "trace-x"),
            ],
            body=b'{"conversationId":"conv-z"}',
        )
        await middleware.dispatch(request, call_next)
        self.assertEqual(captured["trace_id"], "trace-x")
        self.assertEqual(captured["conversation_id"], "conv-z")


# ─────────────────── COM-05: 会话来源矩阵 / Header 回写 / 异常收口 ───────────────────


class TestCom05ConversationSource(unittest.IsolatedAsyncioTestCase, _RequestMixin):
    """COM-05 §3.4: conversation_id 只来自声明式来源矩阵。"""

    def setUp(self):
        install_request_id_log_record_factory()

    async def _dispatch(self, path, body=b"", method="POST", extra_headers=None):
        """直接 dispatch 一次请求，返回 (response, ctx_snapshot)。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            ctx = _request_ctx.get()
            captured["conversation_id"] = ctx.conversation_id
            captured["state_conversation_id"] = getattr(
                request.state, "conversation_id", "<unset>"
            )
            return Response("ok")

        scope_headers = [("x-request-id", "req-1")] + (extra_headers or [])
        request = Request(
            {
                "type": "http",
                "method": method,
                "path": path,
                "headers": [(k.lower().encode(), v.encode()) for k, v in scope_headers],
            },
            receive=self._body_receiver(body),
        )
        response = await middleware.dispatch(request, call_next)
        return response, captured

    async def test_path_source_conversation_id(self):
        resp, captured = await self._dispatch(
            "/v1/p1/workflows/wf1/conversations/conv-path-1"
        )
        self.assertEqual(captured["conversation_id"], "conv-path-1")
        self.assertEqual(captured["state_conversation_id"], "conv-path-1")
        self.assertEqual(resp.headers.get("x-request-id"), "req-1")

    async def test_body_source_conversation_id(self):
        _resp, captured = await self._dispatch(
            "/v1/orchestration/ir/execute",
            body=b'{"conversationId":"conv-body-1"}',
        )
        self.assertEqual(captured["conversation_id"], "conv-body-1")

    async def test_non_conversation_stays_empty_even_with_body_field(self):
        """非会话接口 body 含 conversationId 也不误取（删除全局误绑定）。"""
        _, captured = await self._dispatch(
            "/v1/inner-tools/document/create",
            body=b'{"conversationId":"should-be-ignored"}',
        )
        self.assertEqual(captured["conversation_id"], "")
        self.assertEqual(captured["state_conversation_id"], "")

    async def test_path_body_conflict_rejected_400(self):
        resp, _ = await self._dispatch(
            "/v1/p1/workflows/wf1/conversations/conv-path",
            body=b'{"conversationId":"conv-different"}',
        )
        self.assertEqual(resp.status_code, 400)
        body_text = resp.body.decode()
        self.assertNotIn("conv-path", body_text)
        self.assertNotIn("conv-different", body_text)
        self.assertEqual(resp.headers.get("x-request-id"), "req-1")

    async def test_path_with_consistent_body_uses_path(self):
        _, captured = await self._dispatch(
            "/v1/p1/workflows/wf1/conversations/conv-agree",
            body=b'{"conversationId":"conv-agree"}',
        )
        self.assertEqual(captured["conversation_id"], "conv-agree")

    async def test_delete_body_source_conversation_id(self):
        _resp, captured = await self._dispatch(
            "/v1/orchestration/ir/execute",
            body=b'{"conversationId":"conv-del-1"}',
            method="DELETE",
        )
        self.assertEqual(captured["conversation_id"], "conv-del-1")

    async def test_delete_does_not_extract_user_id(self):
        """DELETE body 只取会话字段，不扩大 userId/secretEnvKeys 适用方法。"""
        captured_state = {}

        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)

        async def call_next(request):
            captured_state["user_id"] = _request_ctx.get().user_id
            captured_state["secret"] = _request_ctx.get().secret_env_keys
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "DELETE",
                "path": "/v1/orchestration/ir/execute",
                "headers": [(b"x-request-id", b"req-1")],
            },
            receive=self._body_receiver(
                b'{"conversationId":"c1","userId":"should-not-apply"}'
            ),
        )
        await middleware.dispatch(request, call_next)
        self.assertEqual(captured_state["user_id"], "")
        self.assertEqual(captured_state["secret"], [])

    async def test_user_id_and_secret_env_keys_still_extracted(self):
        """POST 的 userId/secretEnvKeys 既有提取行为保持不变。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            captured["user_id"] = _request_ctx.get().user_id
            captured["secret"] = _request_ctx.get().secret_env_keys
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/some/other/route",
                "headers": [(b"x-request-id", b"req-1")],
            },
            receive=self._body_receiver(
                b'{"userId":"u1","params":{"secretEnvKeys":["k1"]}}'
            ),
        )
        await middleware.dispatch(request, call_next)
        self.assertEqual(captured["user_id"], "u1")
        self.assertEqual(captured["secret"], ["k1"])


class TestCom05HeaderWritebackAndException(unittest.TestCase):
    """COM-05 §3.5: X-Request-Id 回写 + 未处理异常 token 有效期内收口。"""

    def setUp(self):
        install_request_id_log_record_factory()

    @staticmethod
    def _make_app():
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/ok")
        async def ok_route():
            return {"status": "ok"}

        @app.get("/boom")
        async def boom_route():
            raise RuntimeError("route exploded")

        return app, TestClient(app)

    def test_success_response_carries_x_request_id(self):
        _, client = self._make_app()
        resp = client.get("/ok", headers={"X-Request-Id": "rid-hw-1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Request-Id"), "rid-hw-1")

    def test_generated_request_id_echoed_when_header_missing(self):
        _, client = self._make_app()
        resp = client.get("/ok")
        echoed = resp.headers.get("X-Request-Id")
        self.assertTrue(echoed)  # 生成的 UUID 非空且回写

    def test_404_response_carries_x_request_id(self):
        _, client = self._make_app()
        resp = client.get("/nonexistent", headers={"X-Request-Id": "rid-404"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.headers.get("X-Request-Id"), "rid-404")

    def test_unhandled_exception_caught_in_middleware_with_context(self):
        """未处理异常在 token 有效期内收口：500 + X-Request-Id + 日志固定字段非空。

        SYNC-01 P3.2 adapt：响应体为 sync_01 裸格式（error_code=internal_error），
        非 COM-03 canonical8（openjiuwen.12100004）—— COM-03 在 S3 后做。
        """
        import json as _json
        import logging as _logging

        _, client = self._make_app()
        captured_records = []

        class _CaptureHandler(_logging.Handler):
            def emit(self, record):
                captured_records.append(record)

        err_logger = _logging.getLogger("agent_runtime.serve.error_response")
        handler = _CaptureHandler()
        err_logger.addHandler(handler)
        try:
            resp = client.get(
                "/boom",
                headers={
                    "X-Request-Id": "rid-exc",
                    "TraceID": "trace-exc",
                    "X-Execution-Id": "exec-exc",
                },
            )
        finally:
            err_logger.removeHandler(handler)

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.headers.get("X-Request-Id"), "rid-exc")
        # P5-R3 落地（2026-09-21）：build_unhandled_error_response 升级为 COM-03
        # canonical8（openjiuwen.12100004 INTERNAL_ERROR，五字段 + X-Request-Id）。
        # P3.2 时为裸 internal_error 格式延后（S3 落 COM-03 后升级），本轮升级。
        body = _json.loads(resp.text)
        self.assertEqual(body.get("error_code"), "openjiuwen.12100004")
        self.assertTrue(body.get("error_msg"))
        self.assertTrue(body.get("error_reason"))
        self.assertTrue(body.get("error_suggestion"))
        self.assertEqual(body.get("request_id"), "rid-exc")

        # 异常日志的固定外层关联字段来自本请求 ContextVar（token 尚未 reset）
        self.assertTrue(captured_records)
        rec = captured_records[-1]
        self.assertEqual(rec.request_id, "rid-exc")
        self.assertEqual(rec.trace_id, "trace-exc")
        self.assertEqual(rec.execution_id, "exec-exc")


class TestCom05BodyConversationIdTypes(unittest.IsolatedAsyncioTestCase, _RequestMixin):
    """复审 §2.2: body 会话 ID 类型守卫——非字符串不写入统一字段。"""

    def setUp(self):
        install_request_id_log_record_factory()

    async def _dispatch_body_source(self, raw_body):
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            captured["conversation_id"] = _request_ctx.get().conversation_id
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/orchestration/ir/execute",
                "headers": [(b"x-request-id", b"req-1")],
            },
            receive=self._body_receiver(raw_body),
        )
        await middleware.dispatch(request, call_next)
        return captured

    async def test_string_conversation_id_accepted(self):
        captured = await self._dispatch_body_source(b'{"conversationId":"c-str"}')
        self.assertEqual(captured["conversation_id"], "c-str")

    async def test_empty_string_conversation_id_stays_empty(self):
        captured = await self._dispatch_body_source(b'{"conversationId":""}')
        self.assertEqual(captured["conversation_id"], "")

    async def test_number_conversation_id_not_written(self):
        captured = await self._dispatch_body_source(b'{"conversationId":12345}')
        self.assertEqual(captured["conversation_id"], "")

    async def test_dict_conversation_id_not_written(self):
        """业务对象内容不得经 str() 进入固定日志槽位（复审 §2.2 最小验证）。"""
        captured = await self._dispatch_body_source(
            b'{"conversationId":{"secret":"should-not-enter-id"}}'
        )
        self.assertEqual(captured["conversation_id"], "")

    async def test_list_conversation_id_not_written(self):
        captured = await self._dispatch_body_source(b'{"conversationId":["a","b"]}')
        self.assertEqual(captured["conversation_id"], "")

    async def test_null_conversation_id_not_written(self):
        captured = await self._dispatch_body_source(b'{"conversationId":null}')
        self.assertEqual(captured["conversation_id"], "")

    async def test_path_non_string_body_conversation_id_rejected_400(self):
        """路径来源 + 非字符串 body conversationId：安全 400，不回显原值。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)

        async def call_next(request):  # 不应到达——非字符串 body 在进入业务前被 400 拒绝
            return Response("ok")

        for raw_body in (
            b'{"conversationId":{"nested":"dict"}}',
            b'{"conversationId":12345}',
            b'{"conversationId":["a","b"]}',
            b'{"conversationId":null}',
        ):
            request = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/p1/workflows/wf1/conversations/conv-path",
                    "headers": [(b"x-request-id", b"req-1")],
                },
                receive=self._body_receiver(raw_body),
            )
            resp = await middleware.dispatch(request, call_next)
            self.assertEqual(resp.status_code, 400, f"应 400: {raw_body!r}")
            body_text = resp.body.decode()
            self.assertNotIn("conv-path", body_text)
            self.assertNotIn("nested", body_text)


if __name__ == "__main__":
    unittest.main()
