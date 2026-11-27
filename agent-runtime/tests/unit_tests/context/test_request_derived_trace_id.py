# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""X-Request-Id 派生 OTel trace_id 的回归用例（真实根节点，不虚构父 Span）。"""
import asyncio
import hashlib
import unittest

from starlette.requests import Request
from starlette.responses import Response
from opentelemetry import context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator

from agent_runtime.common.otel_request_trace_id import (
    RequestDerivedIdGenerator,
    current_request_trace_id,
    derive_trace_id,
    install_request_trace_id_generator,
)
from agent_runtime.context.middleware import RequestContextMiddleware


class RequestDerivedTraceIdTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.provider.get_tracer("request-derived-trace-id")
        self.assertTrue(install_request_trace_id_generator(self.tracer))
        self.middleware = RequestContextMiddleware(app=lambda scope, receive, send: None)
        self.token = context.attach(context.Context())

    def tearDown(self):
        context.detach(self.token)
        self.provider.shutdown()

    @staticmethod
    def request(headers=None):
        return Request({"type": "http", "method": "GET", "path": "/test",
                        "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()]})

    async def invoke(self, headers=None):
        async def downstream(_request):
            with self.tracer.start_as_current_span("workflow"):
                with self.tracer.start_as_current_span("component"):
                    await asyncio.sleep(0)
            return Response("ok")
        return await self.middleware.dispatch(self.request(headers), downstream)

    def root(self):
        return next(s for s in self.exporter.get_finished_spans() if s.name == "workflow")

    async def test_hex32_request_id_becomes_trace_id_of_a_real_root(self):
        request_id = "0123456789abcdef0123456789abcdef"
        await self.invoke({"x-request-id": request_id})
        root = self.root()
        child = next(s for s in self.exporter.get_finished_spans() if s.name == "component")
        self.assertIsNone(root.parent)
        self.assertEqual(format(root.context.trace_id, "032x"), request_id)
        self.assertEqual(child.context.trace_id, root.context.trace_id)
        self.assertEqual(child.parent.span_id, root.context.span_id)

    async def test_non_hex_request_id_is_hashed_with_md5(self):
        request_id = "order-2026:abc.1"
        await self.invoke({"x-request-id": request_id})
        expected = int(hashlib.md5(request_id.encode("utf-8"), usedforsecurity=False).hexdigest(), 16)
        self.assertEqual(self.root().context.trace_id, expected)
        self.assertIsNone(self.root().parent)

    async def test_missing_request_id_uses_returned_x_request_id(self):
        response = await self.invoke()
        returned = response.headers["x-request-id"]
        self.assertEqual(format(self.root().context.trace_id, "032x"), returned)

    async def test_valid_traceparent_wins_over_request_id(self):
        await self.invoke({"x-request-id": "f" * 32,
                           "traceparent": "00-123456789012345678901234567890ab-1234567890abcdef-01"})
        root = self.root()
        self.assertEqual(root.context.trace_id, int("123456789012345678901234567890ab", 16))
        self.assertTrue(root.parent.is_remote)

    async def test_invalid_traceparent_falls_back_to_request_id(self):
        await self.invoke({"x-request-id": "a" * 32, "traceparent": "bad"})
        root = self.root()
        self.assertIsNone(root.parent)
        self.assertEqual(format(root.context.trace_id, "032x"), "a" * 32)

    async def test_concurrent_requests_keep_their_own_trace_ids(self):
        ids = ["1" * 32, "2" * 32]
        await asyncio.gather(*(self.invoke({"x-request-id": i}) for i in ids))
        roots = sorted(format(s.context.trace_id, "032x")
                       for s in self.exporter.get_finished_spans() if s.parent is None)
        self.assertEqual(roots, ids)

    async def test_binding_does_not_leak_after_request(self):
        await self.invoke({"x-request-id": "b" * 32})
        self.assertIsNone(current_request_trace_id())
        with self.tracer.start_as_current_span("outside"):
            pass
        outside = next(s for s in self.exporter.get_finished_spans() if s.name == "outside")
        self.assertNotEqual(format(outside.context.trace_id, "032x"), "b" * 32)


class RequestDerivedIdGeneratorUnitTest(unittest.TestCase):
    def test_all_zero_request_id_is_not_used(self):
        self.assertIsNone(derive_trace_id("0" * 32))

    def test_install_is_idempotent(self):
        provider = TracerProvider(id_generator=RandomIdGenerator())
        tracer = provider.get_tracer("t")
        self.assertTrue(install_request_trace_id_generator(tracer))
        first = tracer.id_generator
        self.assertTrue(install_request_trace_id_generator(tracer))
        self.assertIs(tracer.id_generator, first)
        self.assertIsInstance(first, RequestDerivedIdGenerator)

    def test_install_on_tracer_without_id_generator_returns_false(self):
        self.assertFalse(install_request_trace_id_generator(object()))


if __name__ == "__main__":
    unittest.main()
