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
            "%(trace_id)s|%(execution_id)s|%(request_id)s|%(conversation_id)s|"
            "%(levelname)s|%(message)s",
        )
        self.assertEqual(
            PERFORMANCE_LOG_FORMAT,
            "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(execution_id)s|"
            "%(request_id)s|%(conversation_id)s|%(levelname)s|%(message)s",
        )
        self.assertEqual(
            DEFAULT_LOG_FORMAT,
            "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(conversation_id)s|"
            "%(levelname)s|%(message)s",
        )

    def test_log_format_is_selected_by_log_type(self):
        self.assertEqual(get_log_format("common"), COMMON_LOG_FORMAT)
        self.assertEqual(get_log_format("performance"), PERFORMANCE_LOG_FORMAT)
        self.assertEqual(get_log_format("workflow"), COMMON_LOG_FORMAT)
        self.assertEqual(get_log_format("llm"), COMMON_LOG_FORMAT)

    def test_config_yaml_format_aligns_with_common_log_format(self):
        """jiuwen/config.yaml 的 logging.format 优先于常量生效（standalone 路径
        common logger），字段序列必须与 jiuwen COMMON_LOG_FORMAT 一致——否则
        conversation_id 等新增字段会在独立部署路径静默丢失。

        注意对账对象是 jiuwen 侧常量（裸 asctime）而非 runtime 侧
        logging_context 版本（含 msecs）：yaml 只覆盖 jiuwen 自己装配的
        common logger。"""
        from pathlib import Path

        import yaml

        from jiuwen.common.log.base import (
            COMMON_LOG_FORMAT as JIUWEN_COMMON_LOG_FORMAT,
        )

        config_path = (
            Path(__file__).resolve().parents[3] / "jiuwen" / "config.yaml"
        )
        with open(config_path, encoding="utf-8") as f:
            yaml_format = yaml.safe_load(f)["logging"]["format"]

        self.assertEqual(
            yaml_format.split("|"), JIUWEN_COMMON_LOG_FORMAT.split("|")
        )

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

    async def test_common_log_format_renders_conversation_id_segment(self):
        """格式串应把 body 来源的 conversation_id 渲染进前缀（request_id 与 levelname 之间）。"""
        install_request_id_log_record_factory()
        from jiuwen.common.log.base import MaskingFormatter

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
            # openjiuwen ContextFilter 正常会补 log_type；此处直接补齐以单测格式渲染
            record.log_type = "workflow"
            formatter = MaskingFormatter(
                fmt=COMMON_LOG_FORMAT,
                sensitive_words=None,
                sensitive_patterns=None,
                truncate_for_console=True,
            )
            captured["formatted"] = formatter.format(record)
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

        self.assertIn(
            "|122212412c92-6543-4c40-ac19-2f678995e7e9|INFO|",
            captured["formatted"],
        )
        self.assertIn("|00957491|", captured["formatted"])

    def test_jiuwen_thread_context_filter_injects_conversation_id(self):
        """jiuwen standalone 路径下 ThreadContextFilter 应注入 conversation_id（防格式化缺字段）。"""
        from contextvars import ContextVar
        from unittest.mock import patch

        from jiuwen.common.log.base import ThreadContextFilter

        install_request_id_log_record_factory()
        real_json = ContextVar("test_request_json", default={})
        record = logging.getLogRecordFactory()(
            "common", logging.INFO, __file__, 1, "m", (), None
        )
        with patch("jiuwen.common.log.base.request_json", real_json):
            self.assertTrue(ThreadContextFilter("common").filter(record))
            self.assertEqual(record.conversation_id, "")

            real_json.set({"conversationId": "conv-thread-filter"})
            record2 = logging.getLogRecordFactory()(
                "common", logging.INFO, __file__, 1, "m", (), None
            )
            self.assertTrue(ThreadContextFilter("common").filter(record2))
            self.assertEqual(record2.conversation_id, "conv-thread-filter")
            self.assertEqual(record2.trace_id, "conv-thread-filter")

    def test_update_conversation_id_backfills_only_when_empty(self):
        """handler 回写 helper：空则补、非空不覆盖、请求外（默认实例）不写入。"""
        from agent_runtime.context.request_context import (
            _DEFAULT_REQUEST_CONTEXT,
            _request_ctx,
            update_conversation_id,
        )
        from agent_runtime.context.request_context import RequestContext

        token = _request_ctx.set(RequestContext())
        try:
            update_conversation_id("conv-backfill")
            self.assertEqual(_request_ctx.get().conversation_id, "conv-backfill")

            update_conversation_id("conv-other")
            self.assertEqual(_request_ctx.get().conversation_id, "conv-backfill")

            _request_ctx.set(RequestContext())
            update_conversation_id("")
            self.assertEqual(_request_ctx.get().conversation_id, "")
        finally:
            _request_ctx.reset(token)

        update_conversation_id("conv-default-pollution")
        self.assertEqual(_DEFAULT_REQUEST_CONTEXT.conversation_id, "")

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
