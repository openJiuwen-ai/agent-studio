# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""Regression coverage for real OTel roots and incoming trace propagation."""
import asyncio
import unittest

from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from opentelemetry import context, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agent_runtime.context.middleware import RequestContextMiddleware


class RequestContextOtelTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.provider.get_tracer("middleware-regression")
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
        await self.middleware.dispatch(self.request(headers), downstream)

    async def test_standalone_request_exports_a_real_root_and_child(self):
        await self.invoke({"x-request-id": "a" * 32})
        spans = self.exporter.get_finished_spans()
        root = next(s for s in spans if s.name == "workflow")
        child = next(s for s in spans if s.name == "component")
        self.assertIsNone(root.parent)
        self.assertEqual(child.parent.span_id, root.context.span_id)
        self.assertEqual(child.context.trace_id, root.context.trace_id)
        self.assertFalse(trace.get_current_span().get_span_context().is_valid)

    async def test_concurrent_requests_have_independent_real_roots(self):
        await asyncio.gather(self.invoke(), self.invoke())
        roots = [s for s in self.exporter.get_finished_spans() if s.parent is None]
        self.assertEqual(len(roots), 2)
        self.assertNotEqual(roots[0].context.trace_id, roots[1].context.trace_id)

    async def test_valid_traceparent_preserves_real_remote_parent(self):
        await self.invoke({"traceparent": "00-123456789012345678901234567890ab-1234567890abcdef-01",
                           "tracestate": "vendor=value"})
        root = next(s for s in self.exporter.get_finished_spans() if s.name == "workflow")
        self.assertEqual(root.context.trace_id, int("123456789012345678901234567890ab", 16))
        self.assertEqual(root.parent.span_id, int("1234567890abcdef", 16))
        self.assertTrue(root.parent.is_remote)
        self.assertEqual(root.parent.trace_state.get("vendor"), "value")

    async def test_unsampled_traceparent_is_not_forced_to_sample(self):
        await self.invoke({"traceparent": "00-123456789012345678901234567890ab-1234567890abcdef-00"})
        self.assertEqual(len(self.exporter.get_finished_spans()), 0)

    async def test_invalid_traceparent_does_not_fabricate_parent(self):
        for value in ["bad", "00-" + "0" * 32 + "-1234567890abcdef-01"]:
            self.exporter.clear()
            await self.invoke({"traceparent": value})
            root = next(s for s in self.exporter.get_finished_spans() if s.name == "workflow")
            self.assertIsNone(root.parent)

    async def test_existing_instrumented_parent_is_preserved(self):
        with self.tracer.start_as_current_span("existing") as existing:
            await self.invoke()
            self.assertEqual(trace.get_current_span().get_span_context(), existing.get_span_context())
        root = next(s for s in self.exporter.get_finished_spans() if s.name == "workflow")
        self.assertEqual(root.parent.span_id, existing.context.span_id)

    async def test_exception_restores_incoming_context(self):
        async def failing(_request):
            raise RuntimeError("isolated-test-error")
        with self.tracer.start_as_current_span("existing") as existing:
            response = await self.middleware.dispatch(self.request(), failing)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(trace.get_current_span().get_span_context(), existing.get_span_context())

    async def test_streaming_response_retains_parent_without_synthetic_span(self):
        async def downstream(_request):
            async def body():
                with self.tracer.start_as_current_span("stream-workflow"):
                    yield b"ok"
            return StreamingResponse(body())
        with self.tracer.start_as_current_span("existing") as existing:
            response = await self.middleware.dispatch(self.request(), downstream)
            async for _ in response.body_iterator:
                pass
        span = next(s for s in self.exporter.get_finished_spans() if s.name == "stream-workflow")
        self.assertEqual(span.parent.span_id, existing.context.span_id)


if __name__ == "__main__":
    unittest.main()
