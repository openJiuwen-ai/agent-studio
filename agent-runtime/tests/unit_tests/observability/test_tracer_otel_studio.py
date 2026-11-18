# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""StudioOtelWorkflowHandler 集成测试。

核心证明（在 openjiuwen 官方未改动环境下）：
- 官方 OtelWorkflowHandler：HTTP 500 业务失败（组件正常返回）span 不标红；
- StudioOtelWorkflowHandler（本仓子类）：同一场景 span 标红（ERROR）且
  openjiuwen.status 仍为 finish（业务结果不变，流程 COMPLETED）。
"""

import pytest
from openjiuwen.core.session.tracer import TracerHandlerRegistry
from openjiuwen.core.session.workflow import create_workflow_session
from openjiuwen.core.workflow import End, Start, Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.tool.http import (
    HttpComponentConfig,
    HttpRequestParamConfig,
)
from openjiuwen.extensions.tracer_otel.config import OtelTracerConfig
from openjiuwen.extensions.tracer_otel.handler import OtelWorkflowHandler
from openjiuwen.extensions.tracer_otel.semconv import (
    OJ_STATUS,
    OJ_WORKFLOW_COMPONENT_ID,
)
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agent_runtime.observability.tracer_otel_studio import (
    OJ_BUSINESS_ERROR,
    StudioOtelWorkflowHandler,
)

HTTP_NODE_NAME = "HTTP业务节点"


async def start_mock():
    """aiohttp Web 异步 mock（随机空闲端口）：避免 BaseHTTPRequestHandler.do_GET，HttpObservedComponent 本为 aiohttp 客户端。

    路由：
    - /err500：500 + 含敏感内容的 body；
    - /err404：404 + 含敏感内容的 body；
    - /ok200：正常 200，用于证明 2xx 不产生错误语义。
    """
    from aiohttp import web

    async def _err_handler(_request):
        return web.json_response({"error": "server internal error"}, status=500)

    async def _not_found_handler(_request):
        return web.json_response({"error": "resource missing detail"}, status=404)

    async def _ok_handler(_request):
        return web.json_response({"ok": True, "value": 42}, status=200)

    app = web.Application()
    app.router.add_get("/err500", _err_handler)
    app.router.add_get("/err404", _not_found_handler)
    app.router.add_get("/ok200", _ok_handler)
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


def _make_config(redaction_enabled=False):
    return OtelTracerConfig(redaction_enabled=redaction_enabled, sample_rate=1.0)


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
    # Span display names may use the configured node name; component ID is stable.
    match = [s for s in spans if s.attributes.get(OJ_WORKFLOW_COMPONENT_ID) == "http"]
    assert len(match) == 1, f"expected one http span in {[s.name for s in spans]}"
    return match[0]


async def _run_once(handler_cls, url, redaction_enabled=False):
    tracer, exporter = _make_tracer()
    TracerHandlerRegistry.clear()
    TracerHandlerRegistry.register_handler(
        "otel_workflow", handler_cls(tracer, _make_config(redaction_enabled=redaction_enabled))
    )
    out = await _make_workflow(url).invoke({"query": url}, create_workflow_session())
    return out, exporter


async def _run_handler_case(business_error, redaction_enabled=False, invoke_id="node_direct"):
    """直接驱动 handler 三阶段生命周期，返回该节点的 finished span（避免起 HTTP mock）。"""
    tracer, exporter = _make_tracer()
    TracerHandlerRegistry.clear()
    handler = StudioOtelWorkflowHandler(
        tracer, _make_config(redaction_enabled=redaction_enabled)
    )
    TracerHandlerRegistry.register_handler("otel_workflow", handler)

    await handler.on_call_start(
        invoke_id,
        metadata={"workflow_id": "wf", "component_id": invoke_id, "node_id": invoke_id},
        inputs={},
        parent_node_id="",
    )
    await handler.on_invoke(
        invoke_id, on_invoke_data={"business_error": business_error}
    )
    await handler.on_call_done(invoke_id, outputs={"ok": False})
    spans = exporter.get_finished_spans()
    return next(s for s in spans if s.name == f"component.{invoke_id}")


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
    # 异常路径由上游 handler 写 error 业务状态；关键是 span 不被 on_call_done 覆盖为 OK
    assert (span.attributes or {})[OJ_STATUS] == "error"
    assert OJ_BUSINESS_ERROR not in (span.attributes or {})


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


# ---------------------------------------------------------------------------
# issue 覆盖补充：description 白名单摘要 + 结构化错误字段 + 脱敏双态 + 注入防御
# ---------------------------------------------------------------------------

HTTP_500_DESC = "HTTP request failed: status code 500"
BODY_500 = "server internal error"
BODY_404 = "resource missing detail"


@pytest.mark.asyncio
async def test_business_error_http_500_description_and_structured_attrs():
    """HTTP 500 业务失败：ERROR + 精确摘要 + 结构化状态码/错误类型 + 业务输出不变。"""
    runner, port = await start_mock()
    url = f"http://127.0.0.1:{port}/err500"
    try:
        out, exporter = await _run_once(StudioOtelWorkflowHandler, url)
    finally:
        await runner.cleanup()

    assert out.state.value == "COMPLETED"
    span = _http_span(exporter)
    attrs = span.attributes or {}

    # 故障事实轴
    assert span.status.status_code == otel_trace.StatusCode.ERROR
    # description 必须精确等于白名单拼装的摘要
    assert span.status.description == HTTP_500_DESC
    # 结构化字段：状态码保持整数，error.type 保持字符串错误码
    assert attrs["http.response.status_code"] == 500
    assert isinstance(attrs["http.response.status_code"], int)
    assert not isinstance(attrs["http.response.status_code"], bool)
    assert attrs["error.type"] == "500"
    # 业务结果轴不被污染
    assert attrs[OJ_STATUS] == "finish"
    assert out.state.value == "COMPLETED"
    # 业务输出（组件返回值）未被篡改：仍为 ok=False / statusCode=500
    outputs_attr = attrs.get("openjiuwen.workflow.outputs", "")
    assert "'ok': False" in outputs_attr
    assert "500" in outputs_attr

    # description 是标准错误位且不做内容脱敏，绝不能出现 body / url / headers
    desc = span.status.description
    assert BODY_500 not in desc
    assert "127.0.0.1" not in desc
    assert "/err500" not in desc
    assert "Content-Type" not in desc


@pytest.mark.asyncio
async def test_business_error_http_404_description_and_structured_attrs():
    """HTTP 404 业务失败：非 500 同样有可读摘要 + 结构化状态码。"""
    runner, port = await start_mock()
    url = f"http://127.0.0.1:{port}/err404"
    try:
        out, exporter = await _run_once(StudioOtelWorkflowHandler, url)
    finally:
        await runner.cleanup()

    assert out.state.value == "COMPLETED"
    span = _http_span(exporter)
    attrs = span.attributes or {}

    assert span.status.status_code == otel_trace.StatusCode.ERROR
    assert span.status.description == "HTTP request failed: status code 404"
    assert attrs["http.response.status_code"] == 404
    assert attrs["error.type"] == "404"
    assert attrs[OJ_STATUS] == "finish"
    assert BODY_404 not in span.status.description
    assert "127.0.0.1" not in span.status.description


@pytest.mark.asyncio
async def test_business_error_description_identical_across_redaction_modes():
    """脱敏开关双态：description 完全一致且均不含 body/url；开启时错误信息为 sha256 指纹。"""
    runner, port = await start_mock()
    url = f"http://127.0.0.1:{port}/err500"
    try:
        _out_plain, exporter_plain = await _run_once(
            StudioOtelWorkflowHandler, url, redaction_enabled=False
        )
        _out_hashed, exporter_hashed = await _run_once(
            StudioOtelWorkflowHandler, url, redaction_enabled=True
        )
    finally:
        await runner.cleanup()

    span_plain = _http_span(exporter_plain)
    span_hashed = _http_span(exporter_hashed)
    attrs_plain = span_plain.attributes or {}
    attrs_hashed = span_hashed.attributes or {}

    # description 属标准错误位，不参与脱敏 → 两态完全一致
    assert span_plain.status.description == HTTP_500_DESC
    assert span_hashed.status.description == HTTP_500_DESC

    # 两态 description 均不得泄漏响应体/URL
    for span in (span_plain, span_hashed):
        assert BODY_500 not in span.status.description
        assert url not in span.status.description

    # 关闭脱敏：既有属性保留可读明文
    plain_message = attrs_plain["openjiuwen.workflow.error_message"]
    assert "status code 500" in plain_message
    assert BODY_500 in plain_message

    # 开启脱敏：error_message/business_error 均为 sha256 指纹，不含明文
    hashed_message = attrs_hashed["openjiuwen.workflow.error_message"]
    assert hashed_message.startswith("sha256:")
    assert BODY_500 not in hashed_message
    assert hashed_message != plain_message
    hashed_business = attrs_hashed[OJ_BUSINESS_ERROR]
    assert hashed_business.startswith("sha256:")
    assert BODY_500 not in hashed_business


@pytest.mark.asyncio
async def test_business_error_valid_reason_appended_to_description():
    """合法短英文 reason（对端可控但通过白名单）追加到摘要末尾。"""
    span = await _run_handler_case(
        {"status_code": 500, "reason": "upstream timeout"}
    )
    assert span.status.description == "HTTP request failed: status code 500, upstream timeout"
    assert (span.attributes or {})["error.type"] == "500"


@pytest.mark.parametrize(
    "reason",
    [
        pytest.param("服务器内部错误", id="chinese"),
        pytest.param("a" * 65, id="too-long"),
        pytest.param("evil\nreason", id="newline"),
        pytest.param("evil{inject}", id="braces"),
        pytest.param("bad;rm -rf /", id="shell-chars"),
        pytest.param('quote"json"', id="quotes"),
    ],
)
@pytest.mark.asyncio
async def test_business_error_malicious_reason_dropped(reason):
    """恶意/非法 reason：整段丢弃，description 回落到纯状态码摘要。"""
    span = await _run_handler_case({"status_code": 500, "reason": reason})
    desc = span.status.description

    assert span.status.status_code == otel_trace.StatusCode.ERROR
    assert desc == HTTP_500_DESC
    # 注入内容不得以任何形式进入 description
    assert "\n" not in desc
    assert "{" not in desc and "}" not in desc
    assert ";" not in desc
    assert reason not in desc
    assert "aaaaaaaa" not in desc


@pytest.mark.asyncio
async def test_http_2xx_ok_has_no_error_semantics():
    """HTTP 2xx 正常返回：span OK、无 description、无错误相关属性。"""
    runner, port = await start_mock()
    url = f"http://127.0.0.1:{port}/ok200"
    try:
        out, exporter = await _run_once(StudioOtelWorkflowHandler, url)
    finally:
        await runner.cleanup()

    assert out.state.value == "COMPLETED"
    span = _http_span(exporter)
    attrs = span.attributes or {}

    assert span.status.status_code == otel_trace.StatusCode.OK
    assert span.status.description in (None, "")
    assert OJ_BUSINESS_ERROR not in attrs
    assert "openjiuwen.workflow.error_message" not in attrs
    assert "http.response.status_code" not in attrs
    assert "error.type" not in attrs
    assert attrs[OJ_STATUS] == "finish"


@pytest.mark.asyncio
async def test_business_error_non_dict_payload_falls_back_to_str():
    """非 dict 的 business_error：不抛错，摘要退化为固定文本，仍标红。"""
    span = await _run_handler_case("upstream boom")
    attrs = span.attributes or {}

    assert span.status.status_code == otel_trace.StatusCode.ERROR
    assert span.status.description == "HTTP request failed"
    assert attrs["openjiuwen.workflow.error_message"] == "upstream boom"
    assert "http.response.status_code" not in attrs
    assert "error.type" not in attrs
    assert OJ_BUSINESS_ERROR in attrs


@pytest.mark.asyncio
async def test_business_error_error_code_fallback_and_bool_code():
    """status_code 缺失时回落 error_code；bool 不是合法状态码，不写结构化字段。"""
    span = await _run_handler_case(
        {"error_code": "E_TIMEOUT", "reason": "upstream timeout"}
    )
    attrs = span.attributes or {}
    assert span.status.description == (
        "HTTP request failed: status code E_TIMEOUT, upstream timeout"
    )
    assert attrs["error.type"] == "E_TIMEOUT"
    # 非整数错误码不写 http.response.status_code，避免下游按数值筛选时被污染
    assert "http.response.status_code" not in attrs

    bool_span = await _run_handler_case({"status_code": True}, invoke_id="node_bool_code")
    bool_attrs = bool_span.attributes or {}
    assert bool_span.status.description == "HTTP request failed"
    assert "http.response.status_code" not in bool_attrs
    assert "error.type" not in bool_attrs


@pytest.mark.asyncio
async def test_mark_business_error_ignores_unknown_invoke_id():
    """未登记的 invoke_id：静默返回，不抛错、不产生 span。"""
    tracer, exporter = _make_tracer()
    TracerHandlerRegistry.clear()
    handler = StudioOtelWorkflowHandler(tracer, _make_config())

    getattr(handler, "_mark_business_error")(
        "not-registered", {"status_code": 500, "body": BODY_500}
    )

    assert exporter.get_finished_spans() == ()


def test_safe_code_whitelist():
    """_safe_code：None/bool/空串/超长/非法字符一律丢弃，仅保留短码。"""
    safe = getattr(StudioOtelWorkflowHandler, "_safe_code")

    assert safe(None) is None
    assert safe(True) is None
    assert safe(False) is None
    assert safe("") is None
    assert safe(500) == "500"
    assert safe("500") == "500"
    assert safe("E_TIMEOUT") == "E_TIMEOUT"
    assert safe("a" * 32) == "a" * 32
    assert safe("a" * 33) is None
    # 码内部出现换行/空白视为非法内容（不进入不脱敏的 description）
    assert safe("50\n0") is None
    # 末尾换行同样必须拒绝（'$' 会放行末尾换行，故用 fullmatch）
    assert safe("500\n") is None
    assert safe(" 500") is None
    assert safe("500 ok") is None
    assert safe("{}") is None


def test_safe_reason_whitelist():
    """_safe_reason：仅接受短英文短语；中文/换行/花括号/超长/非字符串丢弃。"""
    safe = getattr(StudioOtelWorkflowHandler, "_safe_reason")

    assert safe(None) is None
    assert safe(123) is None
    assert safe(True) is None
    assert safe("") is None
    assert safe("  upstream timeout  ") == "upstream timeout"
    assert safe("a" * 64) == "a" * 64
    assert safe("a" * 65) is None
    assert safe("服务器内部错误") is None
    assert safe("evil\nreason") is None
    # 首尾空白被 strip 后仍为合法短语，换行不会进入 description
    assert safe("timeout\n") == "timeout"
    assert safe("evil{inject}") is None
    assert safe("bad;rm -rf /") is None
