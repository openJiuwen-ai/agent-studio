# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""StudioOtelWorkflowHandler 集成测试。

核心证明（在 openjiuwen 官方未改动环境下）：
- 官方 OtelWorkflowHandler：HTTP 500 业务失败（组件正常返回）span 不标红；
- StudioOtelWorkflowHandler（本仓子类）：同一场景 span 标红（ERROR）且
  openjiuwen.status 仍为 finish（业务结果不变，流程 COMPLETED）。
"""

from types import SimpleNamespace
from unittest.mock import patch

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

    getattr(handler, "_mark_business_error")(  # noqa: B009
        "not-registered", {"status_code": 500, "body": BODY_500}
    )

    assert exporter.get_finished_spans() == ()


def test_safe_code_whitelist():
    """_safe_code：None/bool/空串/超长/非法字符一律丢弃，仅保留短码。"""
    safe = getattr(StudioOtelWorkflowHandler, "_safe_code")  # noqa: B009

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
    safe = getattr(StudioOtelWorkflowHandler, "_safe_reason")  # noqa: B009

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


# ---------------------------------------------------------------------------
# issue #1749：组件异常导致本层工作流终止时，根 Span 的错误终态归属
# （_build_error_summary / on_invoke 挂起 / on_post_invoke 清除 / on_call_done 根判定）
# ---------------------------------------------------------------------------

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.graph.pregel import GraphInterrupt
from openjiuwen.core.session.tracer.data import NodeStatus
from openjiuwen.extensions.tracer_otel.handler import (
    _build_error_summary,
)
from openjiuwen.extensions.tracer_otel.semconv import (
    OJ_WORKFLOW_ERROR_MESSAGE,
    OJ_WORKFLOW_OUTPUTS,
)

import agent_runtime.observability.tracer_otel_studio as studio_module

ROOT_ID = "wf_root"
ROOT_SPAN_NAME = "wf-root"
COMP_ID = "node_comp"


class _CodedError(Exception):
    """最小可控异常：模拟携带 error_code 的业务异常（非 BaseError）。"""

    def __init__(self, code=None, msg="boom"):
        super().__init__(msg)
        if code is not None:
            self.error_code = code


def _new_handler():
    tracer, exporter = _make_tracer()
    TracerHandlerRegistry.clear()
    handler = StudioOtelWorkflowHandler(tracer, _make_config())
    TracerHandlerRegistry.register_handler("otel_workflow", handler)
    return handler, exporter


async def _open_root(handler, invoke_id=ROOT_ID):
    await handler.on_call_start(
        invoke_id,
        metadata={"workflow_id": "wf", "workflow_name": ROOT_SPAN_NAME},
        inputs={"query": "hi"},
        parent_node_id="",
    )


async def _open_component(handler, invoke_id=COMP_ID, parent_node_id=ROOT_ID):
    await handler.on_call_start(
        invoke_id,
        metadata={"workflow_id": "wf", "component_id": invoke_id, "node_id": invoke_id},
        inputs={"query": "hi"},
        parent_node_id=parent_node_id,
    )


def _finished_span(exporter, name, expected_count=1):
    spans = [s for s in exporter.get_finished_spans() if s.name == name]
    assert len(spans) == expected_count, (
        f"expected {expected_count} span(s) named {name!r}, "
        f"got {[s.name for s in exporter.get_finished_spans()]}"
    )
    return spans[0]


def _root_span_by_invoke_id(exporter, invoke_id):
    for span in exporter.get_finished_spans():
        if span.name != ROOT_SPAN_NAME:
            continue
        if (span.attributes or {}).get("openjiuwen.invoke_id") == invoke_id:
            return span
    raise AssertionError(f"root span not found: {invoke_id}")


def _description(span):
    return span.status.description or ""


# --- 1. _build_error_summary ------------------------------------------------


def test_build_error_summary_base_error_uses_status_code():
    """BaseError：摘要为 "<status.code> <类名>"，业务 message 不进入不脱敏字段。"""
    err = BaseError(StatusCode.ERROR, msg="boom with secret=CUSTOMER_TOKEN")
    summary = _build_error_summary(err)

    assert summary == f"{StatusCode.ERROR.code} BaseError"
    assert "CUSTOMER_TOKEN" not in summary
    assert "boom" not in summary


def test_build_error_summary_plain_exception_class_name_only():
    """普通 Exception：只输出类名，异常消息（可能含入参/凭据）不得进入摘要。"""
    summary = _build_error_summary(ValueError("token=abc123 /payload"))

    assert summary == "ValueError"
    assert "abc123" not in summary
    assert "/payload" not in summary


def test_build_error_summary_uses_error_code_when_no_status():
    """无 status 但有 error_code：输出 "<error_code> <类名>"。"""
    assert _build_error_summary(_CodedError("E_TIMEOUT")) == "E_TIMEOUT _CodedError"
    assert _build_error_summary(_CodedError(100010)) == "100010 _CodedError"


def test_build_error_summary_ignores_bool_error_code():
    """bool 不是合法错误码（isinstance(True, int) 为真），必须回落为纯类名。"""
    assert _build_error_summary(_CodedError(True)) == "_CodedError"


def test_build_error_summary_truncates_to_256():
    """超长错误码截断到 256 字符：硬上限，避免撑爆 status.description。"""
    summary = _build_error_summary(_CodedError("E" * 300))

    assert len(summary) == 256
    assert summary == "E" * 256
    assert "_CodedError" not in summary


# --- 2. on_invoke：挂起未处理异常 -------------------------------------------


@pytest.mark.asyncio
async def test_on_invoke_regular_exception_records_pending():
    """普通异常：既由上游 handler 标红组件 span，又挂起 pending 供根 Span 判定。"""
    handler, exporter = _new_handler()
    await _open_component(handler)

    await handler.on_invoke(COMP_ID, exception=RuntimeError("component blew up"))

    assert getattr(handler, "_unhandled_errors") == {  # noqa: B009
        ROOT_ID: {COMP_ID: "RuntimeError"}
    }
    span = _finished_span(exporter, f"component.{COMP_ID}")
    assert span.status.status_code == otel_trace.StatusCode.ERROR
    assert span.attributes[OJ_STATUS] == NodeStatus.ERROR.value
    # 摘要不含异常消息内容
    assert span.status.description == "RuntimeError"
    assert "component blew up" not in _description(span)


@pytest.mark.asyncio
async def test_on_invoke_graph_interrupt_not_recorded_as_pending():
    """GraphInterrupt 是控制流信号而非失败：不挂起 pending、组件 span 不标 ERROR。"""
    handler, exporter = _new_handler()
    await _open_component(handler)

    await handler.on_invoke(COMP_ID, exception=GraphInterrupt())

    assert getattr(handler, "_unhandled_errors", {}) == {}
    span = _finished_span(exporter, f"component.{COMP_ID}")
    assert span.status.status_code != otel_trace.StatusCode.ERROR
    assert span.attributes[OJ_STATUS] == NodeStatus.INTERRUPTED.value


# --- 3. on_post_invoke：降级后清除 pending ----------------------------------


@pytest.mark.asyncio
async def test_on_post_invoke_clears_pending_after_degrade():
    """defaultOutputs/errorBranch 降级后组件正常返回：on_post_invoke 清除 pending。"""
    handler, exporter = _new_handler()
    await _open_component(handler)
    await handler.on_invoke(COMP_ID, exception=RuntimeError("boom"))
    assert COMP_ID in getattr(handler, "_unhandled_errors")[ROOT_ID]  # noqa: B009

    await handler.on_post_invoke(COMP_ID, outputs={"degraded": True})

    assert getattr(handler, "_unhandled_errors", {}) == {}
    # 组件 span 已在异常路径收尾，不会被 on_post_invoke 重复创建
    assert len(exporter.get_finished_spans()) == 1


@pytest.mark.asyncio
async def test_on_post_invoke_without_pending_keeps_state_clean():
    """从未挂起 pending（_unhandled_errors 不存在）：不抛错、不产生脏数据。"""
    handler, exporter = _new_handler()
    await _open_component(handler)

    await handler.on_post_invoke(COMP_ID, outputs={"ok": True})

    assert getattr(handler, "_unhandled_errors", {}) == {}
    assert exporter.get_finished_spans() == ()


# --- 4a. 根 Span：pending + outputs=None → ERROR ----------------------------


@pytest.mark.asyncio
async def test_call_done_root_with_pending_and_no_outputs_marks_error():
    """组件异常导致本层终止：根 Span 同时写 ERROR/description 与 openjiuwen.status=error。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await _open_component(handler)
    await handler.on_invoke(COMP_ID, exception=RuntimeError("component blew up"))

    await handler.on_call_done(ROOT_ID, outputs=None)

    root = _finished_span(exporter, ROOT_SPAN_NAME)
    attrs = root.attributes or {}
    assert root.status.status_code == otel_trace.StatusCode.ERROR
    assert root.status.description == "RuntimeError"
    assert _description(root) != ""
    assert attrs[OJ_STATUS] == NodeStatus.ERROR.value
    # 失败终态不写入 outputs
    assert OJ_WORKFLOW_OUTPUTS not in attrs
    assert getattr(handler, "_unhandled_errors", {}) == {}


@pytest.mark.asyncio
async def test_call_done_root_with_pending_base_error_description_has_code():
    """根 Span 摘要沿用 _build_error_summary：BaseError 带错误码，便于按码筛选。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await _open_component(handler)
    await handler.on_invoke(COMP_ID, exception=BaseError(StatusCode.ERROR, msg="ignored"))

    await handler.on_call_done(ROOT_ID, outputs=None)

    root = _finished_span(exporter, ROOT_SPAN_NAME)
    assert root.status.status_code == otel_trace.StatusCode.ERROR
    assert root.status.description == f"{StatusCode.ERROR.code} BaseError"
    assert (root.attributes or {})[OJ_STATUS] == NodeStatus.ERROR.value


# --- 4b. 根 Span：无 pending → OK/finish -----------------------------------


@pytest.mark.asyncio
async def test_call_done_root_without_pending_is_ok_finish():
    """正常完成：根 Span 置 OK、openjiuwen.status=finish、无错误描述。"""
    handler, exporter = _new_handler()
    await _open_root(handler)

    await handler.on_call_done(ROOT_ID, outputs=None)

    root = _finished_span(exporter, ROOT_SPAN_NAME)
    assert root.status.status_code == otel_trace.StatusCode.OK
    assert _description(root) == ""
    assert (root.attributes or {})[OJ_STATUS] == NodeStatus.FINISH.value


@pytest.mark.asyncio
async def test_call_done_root_keeps_existing_error_status_but_marks_finish():
    """根 Span 已有 ERROR（business_error）且无 pending：保留标红、业务轴 finish。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await handler.on_invoke(
        ROOT_ID,
        on_invoke_data={"business_error": {"status_code": 503, "reason": "unavailable"}},
    )

    await handler.on_call_done(ROOT_ID, outputs={"ok": False})

    root = _finished_span(exporter, ROOT_SPAN_NAME)
    attrs = root.attributes or {}
    assert root.status.status_code == otel_trace.StatusCode.ERROR
    assert root.status.description == "HTTP request failed: status code 503, unavailable"
    assert attrs[OJ_STATUS] == NodeStatus.FINISH.value
    assert OJ_WORKFLOW_OUTPUTS in attrs


# --- 4c. 降级：pending 存在但正常返回 → 根 OK/finish 且 pending 清空 --------


@pytest.mark.asyncio
async def test_call_done_root_after_degrade_via_post_invoke_is_ok_finish():
    """降级链路（on_post_invoke 已清 pending）→ 根 outputs=None 也是 OK/finish。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await _open_component(handler)
    await handler.on_invoke(COMP_ID, exception=RuntimeError("boom"))
    await handler.on_post_invoke(COMP_ID, outputs={"fallback": "default"})

    await handler.on_call_done(ROOT_ID, outputs=None)

    root = _finished_span(exporter, ROOT_SPAN_NAME)
    assert root.status.status_code == otel_trace.StatusCode.OK
    assert _description(root) == ""
    assert (root.attributes or {})[OJ_STATUS] == NodeStatus.FINISH.value
    assert getattr(handler, "_unhandled_errors", {}) == {}


@pytest.mark.asyncio
async def test_call_done_root_with_outputs_clears_pending_and_is_ok_finish():
    """pending 残留但本层产出非空：不标终止失败，根 OK/finish，且 pending 被清空。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await _open_component(handler)
    await handler.on_invoke(COMP_ID, exception=RuntimeError("boom"))
    assert getattr(handler, "_unhandled_errors") == {  # noqa: B009
        ROOT_ID: {COMP_ID: "RuntimeError"}
    }

    await handler.on_call_done(ROOT_ID, outputs={"answer": "degraded"})

    root = _finished_span(exporter, ROOT_SPAN_NAME)
    attrs = root.attributes or {}
    assert root.status.status_code == otel_trace.StatusCode.OK
    assert _description(root) == ""
    assert attrs[OJ_STATUS] == NodeStatus.FINISH.value
    assert "degraded" in attrs[OJ_WORKFLOW_OUTPUTS]
    assert getattr(handler, "_unhandled_errors", {}) == {}


# --- 4d. 组件 Span（非 layer root）：pending 不得触发根终止语义 -------------


@pytest.mark.asyncio
async def test_call_done_component_with_pending_is_not_root_terminal():
    """组件 span 命中 pending 但非 layer root：不写 ERROR/description，也不清空 pending。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await _open_component(handler)
    # 直接注入 pending（真实异常路径会在 on_invoke 中提前收尾组件 span）
    setattr(handler, "_unhandled_errors", {ROOT_ID: {COMP_ID: "RuntimeError"}})  # noqa: B010

    await handler.on_call_done(COMP_ID, outputs=None)

    comp = _finished_span(exporter, f"component.{COMP_ID}")
    assert comp.status.status_code == otel_trace.StatusCode.OK
    assert _description(comp) == ""
    assert (comp.attributes or {})[OJ_STATUS] == NodeStatus.FINISH.value
    # 非 layer root 不清空 pending（清理责任归属根 span）
    assert getattr(handler, "_unhandled_errors") == {  # noqa: B009
        ROOT_ID: {COMP_ID: "RuntimeError"}
    }
    # 根 span 仍处于未收尾状态
    assert getattr(handler, "_layer_root_spans").get(ROOT_ID) is not None  # noqa: B009


# --- 4e. 跨层/并发隔离：收尾只清本层 pending（检视 P2 回归） -----------------


@pytest.mark.asyncio
async def test_pending_is_isolated_between_layer_roots():
    """一个层根收尾只清本层 pending：不挂他层摘要、不抹掉他层失败标记。"""
    handler, exporter = _new_handler()
    other_root = "wf-root-other"
    other_comp = "node_other"

    await _open_root(handler)
    await _open_component(handler)
    await _open_root(handler, invoke_id=other_root)
    await _open_component(handler, invoke_id=other_comp, parent_node_id=other_root)

    await handler.on_invoke(COMP_ID, exception=RuntimeError("root-a-boom"))
    await handler.on_invoke(other_comp, exception=RuntimeError("root-b-boom"))
    pending = getattr(handler, "_unhandled_errors")  # noqa: B009
    assert set(pending) == {ROOT_ID, other_root}

    # B 层先收尾：只清 B 层，A 层 pending 必须保留
    await handler.on_call_done(other_root, outputs=None)
    assert ROOT_ID in getattr(handler, "_unhandled_errors")  # noqa: B009
    root_b = _root_span_by_invoke_id(exporter, other_root)
    assert root_b.status.status_code == otel_trace.StatusCode.ERROR
    assert root_b.status.description == "RuntimeError"

    await handler.on_call_done(ROOT_ID, outputs=None)
    root_a = _root_span_by_invoke_id(exporter, ROOT_ID)
    assert root_a.status.status_code == otel_trace.StatusCode.ERROR
    assert root_a.status.description == "RuntimeError"
    assert getattr(handler, "_unhandled_errors") == {}  # noqa: B009


@pytest.mark.asyncio
async def test_unhandled_error_scope_falls_back_to_parent_span_context():
    """无 openjiuwen.parent_node_id 时按父 SpanContext 反查层根（不可哈希回归）。"""
    handler, exporter = _new_handler()  # noqa: RUF059
    await _open_root(handler)
    await _open_component(handler)
    root_span_id = getattr(handler, "_layer_root_spans")[ROOT_ID].span.get_span_context().span_id  # noqa: B009
    fake_state = SimpleNamespace(
        span=SimpleNamespace(parent=SimpleNamespace(span_id=root_span_id))
    )
    with patch.object(getattr(handler, "_span_manager"), "get", return_value=fake_state):  # noqa: B009
        assert getattr(handler, "_unhandled_error_scope")(COMP_ID) == ROOT_ID  # noqa: B009


# --- 4f. 根自身异常/提前收尾：不得跨轮残留（分支→场景反向核对补用例） ------


@pytest.mark.asyncio
async def test_root_exception_does_not_leak_pending_across_rounds():
    """层根自身异常不记录 pending；同 invoke_id 下一轮 outputs=None 不得被误标。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await handler.on_invoke(ROOT_ID, exception=RuntimeError("root-boom"))
    assert getattr(handler, "_unhandled_errors", {}) == {}

    await handler.on_call_done(ROOT_ID, outputs=None)
    assert getattr(handler, "_unhandled_errors", {}) == {}

    await _open_root(handler)
    await handler.on_call_done(ROOT_ID, outputs=None)
    named_spans = [s for s in exporter.get_finished_spans() if s.name == ROOT_SPAN_NAME]
    roots = [s for s in named_spans if s.attributes.get("openjiuwen.invoke_id") == ROOT_ID]
    assert roots[-1].status.status_code == otel_trace.StatusCode.OK
    assert (roots[-1].status.description or "") == ""
    assert (roots[-1].attributes or {}).get("openjiuwen.status") == "finish"


@pytest.mark.asyncio
async def test_early_finished_span_clears_pending_on_call_done():
    """组件 Span 已被异常分支提前收尾时，再次 on_call_done 必须清掉残留标记。"""
    handler, _ = _new_handler()
    await _open_root(handler)
    await _open_component(handler)
    await handler.on_invoke(COMP_ID, exception=RuntimeError("comp-boom"))
    assert COMP_ID in getattr(handler, "_unhandled_errors")[ROOT_ID]  # noqa: B009

    await handler.on_call_done(COMP_ID, outputs=None)
    assert getattr(handler, "_unhandled_errors", {}) == {}


# --- 5. 回归：正常组件 on_call_done 行为不变 --------------------------------


@pytest.mark.asyncio
async def test_call_done_component_normal_regression():
    """回归：普通组件正常完成仍写 outputs、OK、finish，不被根判定逻辑影响。"""
    handler, exporter = _new_handler()
    await _open_root(handler)
    await _open_component(handler)

    await handler.on_call_done(COMP_ID, outputs={"result": 42})

    comp = _finished_span(exporter, f"component.{COMP_ID}")
    attrs = comp.attributes or {}
    assert comp.status.status_code == otel_trace.StatusCode.OK
    assert _description(comp) == ""
    assert attrs[OJ_STATUS] == NodeStatus.FINISH.value
    assert "42" in attrs[OJ_WORKFLOW_OUTPUTS]
    assert OJ_WORKFLOW_ERROR_MESSAGE not in attrs
    assert (getattr(handler, "_component_spans") or {}) == {}  # noqa: B009


@pytest.mark.asyncio
async def test_call_done_root_normal_with_outputs_regression():
    """回归：根 Span 正常完成（有产出）仍写 outputs、OK、finish。"""
    handler, exporter = _new_handler()
    await _open_root(handler)

    await handler.on_call_done(ROOT_ID, outputs={"answer": "ok"})

    root = _finished_span(exporter, ROOT_SPAN_NAME)
    attrs = root.attributes or {}
    assert root.status.status_code == otel_trace.StatusCode.OK
    assert attrs[OJ_STATUS] == NodeStatus.FINISH.value
    assert "ok" in attrs[OJ_WORKFLOW_OUTPUTS]
    assert getattr(handler, "_layer_root_spans").get(ROOT_ID) is None  # noqa: B009


# --- 收尾健壮性 -------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_done_unknown_invoke_id_is_noop():
    """未登记的 invoke_id：静默返回，不抛错、不产生 span。"""
    handler, exporter = _new_handler()

    await handler.on_call_done("not-registered", outputs={"x": 1})

    assert exporter.get_finished_spans() == ()


@pytest.mark.asyncio
async def test_call_done_internal_error_is_swallowed_with_warning():
    """收尾内部异常（如属性刷新失败）：吞掉并告警，不向调用方抛出。"""
    handler, exporter = _new_handler()
    await _open_root(handler)

    with patch.object(
        handler, "_refresh_inputs_attribute", side_effect=RuntimeError("attr broken")
    ), patch.object(studio_module.session_logger, "warning") as warn:
        await handler.on_call_done(ROOT_ID, outputs=None)

    assert warn.call_count == 1
    assert "on_call_done failed" in warn.call_args[0][0]
    assert "attr broken" in str(warn.call_args[0][1])
    assert exporter.get_finished_spans() == ()
