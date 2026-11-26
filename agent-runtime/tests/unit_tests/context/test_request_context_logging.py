import logging
import re
import unittest

from starlette.requests import Request
from starlette.responses import Response

from agent_runtime.context.request_context import _request_ctx
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
            captured["conversation_id"] = record.conversation_id
            captured["ir_load_cache"] = _request_ctx.get().ir_load_cache
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

        # DEF-03：trace_id 只来自合法 TraceID，缺失时回退 request_id；
        # 不得用 conversation_id 派生/覆盖 trace_id。conversation_id 独立字段，
        # /v1/orchestration/ir/execute 是 BODY 来源路由 → 从请求体取值。
        self.assertEqual(captured["trace_id"], "00957491")
        self.assertEqual(captured["execution_id"], "exec-1")
        self.assertEqual(captured["request_id"], "00957491")
        self.assertEqual(
            captured["conversation_id"], "122212412c92-6543-4c40-ac19-2f678995e7e9"
        )
        self.assertEqual(captured["ir_load_cache"], {})

    async def test_jiuwen_context_receives_request_id_and_execution_id(self):
        """中间件 dispatch 后，jiuwen 上下文的 get_x_request_id / get_x_execution_id 应返回 header 值。"""
        from contextvars import ContextVar
        from unittest.mock import patch
        real_ctx = ContextVar("test_request_ctx", default={})
        with patch("jiuwen.common.log.base.request_ctx", real_ctx), \
             patch("jiuwen.serve.common.context.request_ctx", real_ctx), \
             patch("agent_runtime.context.middleware._jiuwen_request_ctx", real_ctx):
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

    async def test_hex_request_id_does_not_create_an_unexported_otel_parent(self):
        """业务 Request ID 不能通过虚构父 Span 强制变成 OTel Trace ID。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        hex_trace_id = "aabbccdd11223344556677889900ff00"

        async def call_next(request):
            span = otel_trace.get_current_span()
            captured["valid_parent"] = span.get_span_context().is_valid
            captured["request_id"] = _request_ctx.get().request_id
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

        self.assertFalse(captured["valid_parent"])
        self.assertEqual(captured["request_id"], hex_trace_id)

    async def test_non_hex_request_id_does_not_create_an_unexported_otel_parent(self):
        """非十六进制业务 ID 同样不应创建无记录父 Span。"""
        middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        captured = {}

        raw_request_id = "mytest-trace-123456"

        async def call_next(request):
            span = otel_trace.get_current_span()
            captured["valid_parent"] = span.get_span_context().is_valid
            captured["request_id"] = _request_ctx.get().request_id
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

        self.assertFalse(captured["valid_parent"])
        self.assertEqual(captured["request_id"], raw_request_id)

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
            "%(conversation_id)s|%(execution_id)s|%(request_id)s|%(levelname)s|"
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

    def test_performance_logger_disabled_when_switch_false(self):
        """PERFORMANCE_LOG_ENABLED=false 时 install_log_formatter_patch 应禁用 performance logger。"""
        import agent_runtime.common.logging_context as lc
        from agent_runtime.common.config import settings
        from unittest.mock import patch

        perf_logger = logging.getLogger("performance")
        with patch("agent_runtime.common.logging_context._FORMATTER_PATCH_INSTALLED", False), \
             patch("agent_runtime.common.logging_context._OPENJIUWEN_LOGGING_MANAGED", False), \
             patch.object(settings.server, "performance_log_enabled", False), \
             patch.object(perf_logger, "disabled", False):
            lc.install_log_formatter_patch()
            self.assertTrue(perf_logger.disabled)

    def test_performance_logger_enabled_when_switch_true(self):
        """PERFORMANCE_LOG_ENABLED=true（默认）时 install_log_formatter_patch 不应禁用 performance logger。"""
        import agent_runtime.common.logging_context as lc
        from agent_runtime.common.config import settings
        from unittest.mock import patch

        perf_logger = logging.getLogger("performance")
        with patch("agent_runtime.common.logging_context._FORMATTER_PATCH_INSTALLED", False), \
             patch("agent_runtime.common.logging_context._OPENJIUWEN_LOGGING_MANAGED", False), \
             patch.object(settings.server, "performance_log_enabled", True), \
             patch.object(perf_logger, "disabled", False):
            lc.install_log_formatter_patch()
            self.assertFalse(perf_logger.disabled)

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

    # ── BUG2026112312077-12127：对外日志第 5 段恢复为 conversation_id ──

    def test_common_log_format_places_conversation_id_in_fifth_slot(self):
        """COMMON 格式第 5 段必须是 conversation_id，且整体仍为 9 段、levelname 在第 8 段。"""
        segments = COMMON_LOG_FORMAT.split("|")
        self.assertEqual(len(segments), 9)
        self.assertEqual(segments[4], "%(conversation_id)s")
        self.assertEqual(segments[5], "%(execution_id)s")
        self.assertEqual(segments[6], "%(request_id)s")
        self.assertEqual(segments[7], "%(levelname)s")
        # 第 5 槽是“替换”而非“新增”：trace_id 不得再出现在 COMMON 格式中
        self.assertNotIn("%(trace_id)s", COMMON_LOG_FORMAT)

    def test_performance_log_format_keeps_trace_id_in_third_slot(self):
        """PERFORMANCE 格式保持 7 段，第 3 段仍为 trace_id（不受本次改动影响）。"""
        segments = PERFORMANCE_LOG_FORMAT.split("|")
        self.assertEqual(len(segments), 7)
        self.assertEqual(segments[2], "%(trace_id)s")
        self.assertEqual(segments[5], "%(levelname)s")
        self.assertNotIn("%(conversation_id)s", PERFORMANCE_LOG_FORMAT)

    def _make_record_with_ctx(self, context, msg="hello"):
        """真实链路：生产 record_factory 产出 LogRecord（注入 ctx 字段）。"""
        install_request_id_log_record_factory()
        token = _request_ctx.set(context)
        self.addCleanup(_request_ctx.reset, token)
        return logging.getLogRecordFactory()(
            "workflow",
            logging.INFO,
            __file__,
            1,
            msg,
            (),
            None,
        )

    def test_record_factory_injects_conversation_id_when_present(self):
        """conversation_id 有值时原样注入，不被 execution_id 覆盖。"""
        from agent_runtime.context.request_context import RequestContext

        record = self._make_record_with_ctx(
            RequestContext(
                conversation_id="conv-abc",
                execution_id="exec-abc",
                request_id="req-abc",
            )
        )

        self.assertEqual(record.conversation_id, "conv-abc")
        self.assertEqual(record.execution_id, "exec-abc")
        self.assertEqual(record.request_id, "req-abc")

    def test_record_factory_keeps_conversation_id_empty_when_absent(self):
        """无会话时第 5 段留空（对齐 Versatile lite），不回退 execution_id。"""
        from agent_runtime.context.request_context import RequestContext

        record = self._make_record_with_ctx(
            RequestContext(
                conversation_id="",
                execution_id="exec-fallback",
                request_id="req-fallback",
            )
        )

        self.assertEqual(record.conversation_id, "")
        self.assertEqual(record.execution_id, "exec-fallback")

    @staticmethod
    def _render_common(record):
        """走真实 core ContextFilter（补 log_type/trace_id）+ MaskingFormatter 渲染。"""
        from openjiuwen.core.common.logging.default.default_impl import ContextFilter
        from jiuwen.common.log.base import MaskingFormatter

        ContextFilter("common").filter(record)
        return MaskingFormatter(
            fmt=COMMON_LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S",
            truncate_for_console=False,
        ).format(record)

    def test_real_chain_renders_conversation_id_in_fifth_segment(self):
        """record_factory + ContextFilter + MaskingFormatter：conversation_id 落在第 5 段。"""
        from unittest.mock import patch
        from agent_runtime.context.request_context import RequestContext

        record = self._make_record_with_ctx(
            RequestContext(
                conversation_id="conv-real-1",
                trace_id="trace-real-1",
                execution_id="exec-real-1",
                request_id="req-real-1",
            )
        )
        with patch(
            "openjiuwen.core.common.logging.default.default_impl.get_session_id",
            return_value="trace-real-1",
        ):
            line = self._render_common(record)

        segments = line.split("|")
        self.assertEqual(len(segments), 9)
        self.assertEqual(segments[4], "conv-real-1")
        self.assertEqual(segments[5], "exec-real-1")
        self.assertEqual(segments[6], "req-real-1")
        self.assertEqual(segments[7], "INFO")
        self.assertEqual(segments[8], "hello")

    def test_real_chain_keeps_fifth_segment_empty_without_conversation(self):
        """真实链路下无会话时第 5 段留空，且不与第 6 段 execution_id 重复。"""
        from unittest.mock import patch
        from agent_runtime.context.request_context import RequestContext

        record = self._make_record_with_ctx(
            RequestContext(
                conversation_id="",
                execution_id="exec-real-fb",
                request_id="req-real-fb",
            )
        )
        with patch(
            "openjiuwen.core.common.logging.default.default_impl.get_session_id",
            return_value="trace-real-2",
        ):
            line = self._render_common(record)

        segments = line.split("|")
        self.assertEqual(segments[4], "")
        self.assertEqual(segments[5], "exec-real-fb")
        self.assertNotEqual(segments[4], segments[5])

    def test_real_chain_does_not_repeat_value_when_trace_equals_request(self):
        """trace_id 与 request_id 相同时，COMMON 行内该值最多出现 1 次（不再泄露 trace 段）。"""
        from unittest.mock import patch
        from agent_runtime.context.request_context import RequestContext

        duplicated = "same-value-12127"
        record = self._make_record_with_ctx(
            RequestContext(
                conversation_id="conv-unique",
                trace_id=duplicated,
                execution_id="exec-unique",
                request_id=duplicated,
            )
        )
        with patch(
            "openjiuwen.core.common.logging.default.default_impl.get_session_id",
            return_value=duplicated,
        ):
            line = self._render_common(record)

        segments = line.split("|")
        self.assertEqual(segments[4], "conv-unique")
        self.assertEqual(segments[6], duplicated)
        self.assertEqual(line.count(duplicated), 1)
        self.assertNotEqual(segments[4], duplicated)
        self.assertNotEqual(segments[5], duplicated)

    def test_vector_runtime_rules_are_aligned(self):
        """两份 Vector 的 runtime 列位规则必须同源，且不得回退到旧的 9 段 trace 规则。"""
        from pathlib import Path

        root = Path(__file__).resolve().parents[4]
        files = [
            root / "deploy/config/vector.yaml",
            root / "deploy/observability/config/vector.yaml",
        ]
        rules = []
        for f in files:
            text = f.read_text(encoding="utf-8")
            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip().startswith(("pos9_parts,", "perf7_parts,"))
            ]
            self.assertEqual(len(lines), 2, "%s 缺少 9 段/perf 列位规则" % f)
            joined = "\n".join(lines)
            self.assertIn("(?:[^|\\n]*\\|){4}", joined)
            self.assertIn("(?:perf|performance)", joined)
            self.assertIn("(?P<conversation_id>[^|\\n]*)", joined)
            self.assertIn("(?P<request_id>[^|\\n]*)", joined)
            self.assertNotIn("(?P<trace_id>[^|]+)\\|')", text)
            rules.append(lines)
        self.assertEqual(rules[0], rules[1], "两份 Vector 规则不一致")
