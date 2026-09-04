import logging
import re
import unittest

from starlette.requests import Request
from starlette.responses import Response

from agent_runtime.context.middleware import RequestContextMiddleware, _to_otel_trace_id
from agent_runtime.common.logging_context import (
    COMMON_LOG_FORMAT,
    DEFAULT_LOG_FORMAT,
    PERFORMANCE_LOG_FORMAT,
    get_log_format,
    install_log_formatter_patch,
    install_request_id_log_record_factory,
)
from jiuwen.common.log.base import get_x_request_id, get_x_execution_id
from opentelemetry import trace as otel_trace

_HEX32_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class RequestContextLoggingTest(unittest.IsolatedAsyncioTestCase):
    async def test_request_id_is_available_to_log_records_inside_request(self):
        install_request_id_log_record_factory()
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        async def call_next(request):
            record = logging.getLogRecordFactory()(
                "workflow",
                logging.INFO,
                __file__,
                1,
                "message",
                (),
                None,
            )
            captured["trace_id"] = record.trace_id
            captured["execution_id"] = record.execution_id
            captured["request_id"] = record.request_id
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/orchestration/ir/execute",
                "headers": [
                    (b"x-request-id", b"00957491"),
                    (b"x-execution-id", b"exec-1"),
                ],
            },
            receive=self._body_receiver(
                b'{"conversationId":"122212412c92-6543-4c40-ac19-2f678995e7e9"}'
            ),
        )

        await middleware.dispatch(request, call_next)

        self.assertEqual(
            captured["trace_id"], "122212412c92-6543-4c40-ac19-2f678995e7e9"
        )
        self.assertEqual(captured["execution_id"], "exec-1")
        self.assertEqual(captured["request_id"], "00957491")

    async def test_jiuwen_context_receives_request_id_and_execution_id(self):
        """中间件 dispatch 后，jiuwen 上下文的 get_x_request_id / get_x_execution_id 应返回 header 值。"""
        from contextvars import ContextVar
        from unittest.mock import patch
        real_ctx = ContextVar("test_request_ctx", default={})
        with patch("jiuwen.common.log.base.request_ctx", real_ctx),              patch("jiuwen.serve.common.context.request_ctx", real_ctx),              patch("agent_runtime.context.middleware._jiuwen_request_ctx", real_ctx):
            middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
            captured = {}

            async def call_next(request):
                captured["request_id"] = get_x_request_id()
                captured["execution_id"] = get_x_execution_id()
                return Response("ok")

            request = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/v1/orchestration/ir/execute",
                    "headers": [
                        (b"x-request-id", b"req-from-header-123"),
                        (b"x-execution-id", b"exec-from-header-456"),
                    ],
                },
                receive=self._body_receiver(b'{"conversationId":"conv-abc"}'),
            )

            await middleware.dispatch(request, call_next)

            self.assertEqual(captured["request_id"], "req-from-header-123")
            self.assertEqual(captured["execution_id"], "exec-from-header-456")

    async def test_auto_generated_ids_are_32_char_hex_when_headers_missing(self):
        """X-Request-Id / X-Execution-Id 缺失时，自动生成的 ID 应为32位16进制格式。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)

        async def call_next(request):
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/orchestration/ir/execute",
                "headers": [],
            },
            receive=self._body_receiver(b'{"conversationId":"conv-xyz"}'),
        )

        await middleware.dispatch(request, call_next)

        self.assertRegex(request.state.request_id, _HEX32_PATTERN)
        self.assertRegex(request.state.execution_id, _HEX32_PATTERN)

    async def test_otel_context_trace_id_matches_request_id_hex32(self):
        """当 X-Request-Id 为32位16进制时，OTel 上下文的 trace_id 应与之完全一致。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        hex_trace_id = "aabbccdd11223344556677889900ff00"

        async def call_next(request):
            span = otel_trace.get_current_span()
            captured["trace_id"] = hex(span.get_span_context().trace_id)
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/orchestration/ir/execute",
                "headers": [
                    (b"x-request-id", hex_trace_id.encode()),
                ],
            },
            receive=self._body_receiver(b'{"conversationId":"conv-otel"}'),
        )

        await middleware.dispatch(request, call_next)

        self.assertEqual(captured["trace_id"], hex(int(hex_trace_id, 16)))

    async def test_otel_context_trace_id_hashed_for_non_hex_request_id(self):
        """当 X-Request-Id 非32位16进制时，OTel trace_id 应为 md5 哈希值。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        raw_request_id = "mytest-trace-123456"

        async def call_next(request):
            span = otel_trace.get_current_span()
            captured["trace_id"] = hex(span.get_span_context().trace_id)
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/orchestration/ir/execute",
                "headers": [
                    (b"x-request-id", raw_request_id.encode()),
                ],
            },
            receive=self._body_receiver(b'{"conversationId":"conv-hash"}'),
        )

        await middleware.dispatch(request, call_next)

        expected = _to_otel_trace_id(raw_request_id)
        self.assertEqual(captured["trace_id"], hex(expected))

    async def test_otel_context_detached_after_dispatch(self):
        """dispatch 结束后，OTel 上下文应恢复为注入前的状态。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)

        span_before = otel_trace.get_current_span()
        trace_id_before = span_before.get_span_context().trace_id

        async def call_next(request):
            return Response("ok")

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/orchestration/ir/execute",
                "headers": [
                    (b"x-request-id", b"aabbccdd11223344556677889900ff00"),
                ],
            },
            receive=self._body_receiver(b'{"conversationId":"conv-detach"}'),
        )

        await middleware.dispatch(request, call_next)

        span_after = otel_trace.get_current_span()
        self.assertEqual(span_after.get_span_context().trace_id, trace_id_before)

    def test_to_otel_trace_id_md5_fallback_for_non_hex(self):
        """Non-32-hex string should be hashed with md5 to produce valid 128-bit trace_id."""
        import hashlib
        result = _to_otel_trace_id("my-custom-request-id")
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)
        self.assertLess(result, 2**128)
        expected = int(hashlib.md5(b"my-custom-request-id").hexdigest(), 16)
        self.assertEqual(result, expected)

    def test_to_otel_trace_id_passthrough_valid_32hex(self):
        """Valid 32-char hex string should be used directly as trace_id."""
        valid_hex = "aabbccdd11223344556677889900ff00"
        result = _to_otel_trace_id(valid_hex)
        self.assertEqual(result, int(valid_hex, 16))

    def test_log_formats_align_with_jiuwen_field_order(self):
        self.assertEqual(
            COMMON_LOG_FORMAT,
            "%(asctime)s,%(msecs)03d|%(log_type)s|%(filename)s:%(lineno)d|%(funcName)s|"
            "%(trace_id)s|%(execution_id)s|%(request_id)s|%(levelname)s|"
            "%(message)s",
        )
        self.assertEqual(
            PERFORMANCE_LOG_FORMAT,
            "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(execution_id)s|"
            "%(request_id)s|%(levelname)s|%(message)s",
        )
        self.assertEqual(
            DEFAULT_LOG_FORMAT,
            "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(levelname)s|%(message)s",
        )

    def test_log_format_is_selected_by_log_type(self):
        self.assertEqual(get_log_format("common"), COMMON_LOG_FORMAT)
        self.assertEqual(get_log_format("performance"), PERFORMANCE_LOG_FORMAT)
        self.assertEqual(get_log_format("workflow"), COMMON_LOG_FORMAT)
        self.assertEqual(get_log_format("llm"), COMMON_LOG_FORMAT)

    def test_default_logger_uses_log_type_specific_format(self):
        install_log_formatter_patch()

        from openjiuwen.core.common.logging.default.default_impl import DefaultLogger

        config = {
            "format": COMMON_LOG_FORMAT,
            "level": "INFO",
            "log_file": "./logs/test.log",
            "output": [],
        }

        self.assertEqual(
            DefaultLogger("common", config)._get_formatter()._fmt,
            COMMON_LOG_FORMAT,
        )
        self.assertEqual(
            DefaultLogger("performance", config)._get_formatter()._fmt,
            PERFORMANCE_LOG_FORMAT,
        )
        self.assertEqual(
            DefaultLogger("workflow", config)._get_formatter()._fmt,
            COMMON_LOG_FORMAT,
        )
        self.assertEqual(
            DefaultLogger("llm", config)._get_formatter()._fmt,
            COMMON_LOG_FORMAT,
        )

    @staticmethod
    def _body_receiver(body):
        received = False

        async def receive():
            nonlocal received
            if received:
                return {"type": "http.request", "body": b"", "more_body": False}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        return receive
