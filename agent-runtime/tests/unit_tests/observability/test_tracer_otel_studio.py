# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""StudioOtelWorkflowHandler 集成测试。

核心证明（在 openjiuwen 官方未改动环境下）：
- 官方 OtelWorkflowHandler：HTTP 500 业务失败（组件正常返回）span 不标红；
- StudioOtelWorkflowHandler（本仓子类）：同一场景 span 标红（ERROR）且
  openjiuwen.status 仍为 finish（业务结果不变，流程 COMPLETED）。
"""

import pytest
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from openjiuwen.core.session.tracer import TracerHandlerRegistry
from openjiuwen.core.session.workflow import create_workflow_session
from openjiuwen.core.workflow import Start, End, Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.tool.http import (
    HttpComponentConfig,
    HttpRequestParamConfig,
)
from openjiuwen.extensions.tracer_otel.config import OtelTracerConfig
from openjiuwen.extensions.tracer_otel.handler import OtelWorkflowHandler
from openjiuwen.extensions.tracer_otel.semconv import OJ_STATUS

from agent_runtime.observability.tracer_otel_studio import (
    OJ_BUSINESS_ERROR,
    StudioOtelWorkflowHandler,
)

HTTP_NODE_NAME = "HTTP业务节点"


async def start_mock():
    """aiohttp Web 异步 mock（随机空闲端口返回 500）：避免 BaseHTTPRequestHandler.do_GET，HttpObservedComponent 本为 aiohttp 客户端。"""
    from aiohttp import web

    async def _err_handler(_request):
        return web.json_response({"error": "server internal error"}, status=500)

    app = web.Application()
    app.router.add_get("/err500", _err_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)  # 随机空闲端口，避免固定端口冲突
    await site.start()
    port = runner.addresses[0][1]
    return runner, port


def _make_tracer():
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test-studio")
    return tracer, exporter


def _make_config():
    return OtelTracerConfig(redaction_enabled=False, sample_rate=1.0)


def _make_workflow(url):
    from jiuwen.extension.workflow_node.http_observed import HttpObservedComponent

    comp = HttpObservedComponent(
        HttpComponentConfig(request_params=HttpRequestParamConfig(url=url, method="GET"))
    )
    wf = Workflow(card=WorkflowCard(name="wf-studio", id="wf_studio", version="1.0"))
    wf.set_start_comp("start", Start(), inputs_schema={"q": "${query}"})
    wf.add_workflow_comp("http", comp, inputs_schema={"query": "${start.q}"}, name=HTTP_NODE_NAME)
    wf.set_end_comp("end", End(), inputs_schema={"output": "${http.output}"})
    wf.add_connection("start", "http")
    wf.add_connection("http", "end")
    return wf


def _http_span(exporter):
    spans = exporter.get_finished_spans()
    # 官方 openjiuwen 的 span_name 使用 node_id（span 名可读化不在本仓生效范围）
    match = [s for s in spans if s.name == "component.http"]
    assert match, f"no http span in {[s.name for s in spans]}"
    return match[0]


async def _run_once(handler_cls, url):
    tracer, exporter = _make_tracer()
    TracerHandlerRegistry.clear()
    TracerHandlerRegistry.register_handler("otel_workflow", handler_cls(tracer, _make_config()))
    out = await _make_workflow(url).invoke({"query": url}, create_workflow_session())
    return out, exporter


@pytest.mark.asyncio
async def test_studio_handler_marks_business_error_and_keeps_finish():
    """Studio 子类：HTTP 500 业务失败 span 标红（ERROR）、业务状态 finish、流程完成。"""
    runner, port = await start_mock()
    try:
        out, exporter = await _run_once(
            StudioOtelWorkflowHandler, f"http://127.0.0.1:{port}/err500"
        )
    finally:
        await runner.cleanup()

    assert out.state.value == "COMPLETED"
    span = _http_span(exporter)
    assert span.status.status_code == otel_trace.StatusCode.ERROR
    assert span.attributes.get(OJ_STATUS) == "finish"
    assert span.attributes.get(OJ_BUSINESS_ERROR) is not None
    assert "status code 500" in span.attributes.get("openjiuwen.workflow.error_message", "")


@pytest.mark.asyncio
async def test_official_handler_does_not_mark_business_error():
    """对照：官方 handler 对同一业务失败不标红（证明 runtime 覆盖是唯一增量）。"""
    runner, port = await start_mock()
    try:
        out, exporter = await _run_once(
            OtelWorkflowHandler, f"http://127.0.0.1:{port}/err500"
        )
    finally:
        await runner.cleanup()

    assert out.state.value == "COMPLETED"
    span = _http_span(exporter)
    assert span.status.status_code == otel_trace.StatusCode.OK


@pytest.mark.asyncio
async def test_trace_error_path_keeps_error_after_call_done():
    """trace_error（异常抑制/恢复路径）标红后，on_call_done 不再覆盖为 OK。

    评审关注点固化：on_call_done 对已 ERROR 的 span 保留标红（业务结果轴
    finish 独立于故障事实轴）。
    """
    tracer, exporter = _make_tracer()
    TracerHandlerRegistry.clear()
    handler = StudioOtelWorkflowHandler(tracer, _make_config())
    TracerHandlerRegistry.register_handler("otel_workflow", handler)

    invoke_id = "node_x"
    await handler.on_call_start(
        invoke_id,
        metadata={"workflow_id": "wf", "component_id": invoke_id, "node_id": invoke_id},
        inputs={},
        parent_node_id="",
    )
    await handler.on_invoke(invoke_id, exception=RuntimeError("suppressed"))
    await handler.on_call_done(invoke_id, outputs={"ok": False, "statusCode": 500})

    spans = exporter.get_finished_spans()
    span = next(s for s in spans if s.name == "component.node_x")
    assert span.status.status_code == otel_trace.StatusCode.ERROR


@pytest.mark.asyncio
async def test_business_error_non_json_serializable_falls_back_str():
    """M3 兜底：business_error 含 bytes 时不抛、属性回退字符串、span 仍标红。"""
    tracer, exporter = _make_tracer()
    TracerHandlerRegistry.clear()
    handler = StudioOtelWorkflowHandler(tracer, _make_config())
    TracerHandlerRegistry.register_handler("otel_workflow", handler)

    invoke_id = "node_y"
    await handler.on_call_start(
        invoke_id,
        metadata={"workflow_id": "wf", "component_id": invoke_id, "node_id": invoke_id},
        inputs={},
        parent_node_id="",
    )
    await handler.on_invoke(
        invoke_id,
        on_invoke_data={
            "business_error": {
                "status_code": 500,
                "body": b"raw bytes payload",
            },
        },
    )
    await handler.on_call_done(invoke_id, outputs={"ok": False, "statusCode": 500})

    spans = exporter.get_finished_spans()
    span = next(s for s in spans if s.name == "component.node_y")
    assert span.status.status_code == otel_trace.StatusCode.ERROR
    assert OJ_BUSINESS_ERROR in (span.attributes or {})