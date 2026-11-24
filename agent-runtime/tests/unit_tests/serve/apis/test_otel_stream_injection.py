# -*- coding: UTF-8 -*-
"""issue 1754: SSE 帧注入真实 OTel id 并在流结束后清理登记。"""
import json
from types import SimpleNamespace

import pytest

from agent_runtime.common import otel_trace_context as otc
from agent_runtime.serve.apis.orchestration import _inject_otel_ids, _resolve_execution_id

TID = "c" * 32
SID = "d" * 16


async def _frames():
    yield {"event": "workflow_started", "data": {}}
    yield ("data: " + json.dumps({"event": "done", "data": {"text": "x"}}) + "\n\n").encode("utf-8")


@pytest.mark.asyncio
async def test_inject_dict_and_bytes_frames():
    otc.register_session_trace("s1", TID, SID)
    out = [c async for c in _inject_otel_ids(_frames(), "s1")]
    assert out[0]["otel_trace_id"] == TID and out[0]["otel_span_id"] == SID
    payload = json.loads(out[1].decode("utf-8")[6:].strip())
    assert payload["otel_trace_id"] == TID and payload["otel_span_id"] == SID
    assert otc.get_session_trace("s1") is None


@pytest.mark.asyncio
async def test_no_registry_passes_through_unchanged():
    out = [c async for c in _inject_otel_ids(_frames(), "s2")]
    assert out[0] == {"event": "workflow_started", "data": {}}
    assert b"otel_trace_id" not in out[1]


@pytest.mark.asyncio
async def test_cleanup_on_consumer_abort():
    otc.register_session_trace("s1", TID, SID)
    agen = _inject_otel_ids(_frames(), "s1")
    await agen.__anext__()
    await agen.aclose()
    assert otc.get_session_trace("s1") is None


def _fake_request(execution_id=None):
    state = SimpleNamespace()
    if execution_id is not None:
        state.execution_id = execution_id
    return SimpleNamespace(state=state)


def _fake_req(headers=None):
    return SimpleNamespace(headers=headers or {})


def test_resolve_execution_id_prefers_middleware_state():
    resolved = _resolve_execution_id(
        _fake_request("state-id"), _fake_req({"x-execution-id": "header-id"})
    )
    assert resolved == "state-id"


def test_resolve_execution_id_falls_back_to_inbound_header():
    assert _resolve_execution_id(_fake_request(), _fake_req({"x-execution-id": "header-id"})) == "header-id"


def test_resolve_execution_id_generates_isolated_ids_without_source():
    first = _resolve_execution_id(_fake_request(), _fake_req())
    second = _resolve_execution_id(_fake_request(), _fake_req())
    assert first and second
    assert first != second
