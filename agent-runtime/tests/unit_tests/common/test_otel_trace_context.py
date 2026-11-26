# -*- coding: UTF-8 -*-
"""issue 1754: 请求级 OTel trace 登记表与对外响应头。"""
import pytest

from agent_runtime.common import otel_trace_context as otc

TID = "a" * 32
SID = "b" * 16


@pytest.fixture(autouse=True)
def _clean():
    otc.clear_session_trace("s1")
    otc.clear_session_trace("s2")
    yield
    otc.clear_session_trace("s1")
    otc.clear_session_trace("s2")


def test_headers_from_registry():
    otc.register_session_trace("s1", TID, SID, "corr")
    assert otc.build_otel_trace_headers_for("s1") == {
        "X-OTel-Trace-Id": TID,
        "traceresponse": "00-%s-%s-01" % (TID, SID),
    }


def test_headers_missing_session_is_empty():
    assert otc.build_otel_trace_headers_for("unknown") == {}
    assert otc.build_otel_trace_headers_for("") == {}


def test_register_ignores_incomplete_trace():
    otc.register_session_trace("s2", "", SID)
    otc.register_session_trace("s2", TID, "")
    otc.register_session_trace("", TID, SID)
    assert otc.get_session_trace("s2") is None


def test_clear_session_trace_idempotent():
    otc.register_session_trace("s1", TID, SID)
    otc.clear_session_trace("s1")
    otc.clear_session_trace("s1")
    assert otc.get_session_trace("s1") is None


def test_registry_is_bounded(monkeypatch):
    monkeypatch.setattr(otc, "_REGISTRY_MAX_SIZE", 2)
    otc.register_session_trace("s1", TID, SID)
    otc.register_session_trace("s2", TID, SID)
    otc.register_session_trace("s3", TID, SID)
    assert otc.get_session_trace("s1") is None
    assert otc.get_session_trace("s2") is not None
    otc.clear_session_trace("s3")


def test_business_correlation_id_roundtrip():
    otc.set_business_trace_id("corr-1")
    assert otc.get_business_trace_id() == "corr-1"



def test_concurrent_executions_are_isolated():
    """同一 conversation 两个执行：各自读到自己条目，清理互不影响（检视意见）。"""
    tid_a, tid_b = "a" * 32, "c" * 32
    otc.register_session_trace("s1", tid_a, "b" * 16, "corr-a", "exec-a")
    otc.register_session_trace("s1", tid_b, "d" * 16, "corr-b", "exec-b")

    assert otc.build_otel_trace_headers_for("s1", "exec-a")["X-OTel-Trace-Id"] == tid_a
    assert otc.build_otel_trace_headers_for("s1", "exec-b")["X-OTel-Trace-Id"] == tid_b

    otc.clear_session_trace("s1", "exec-a")
    assert otc.get_session_trace("s1", "exec-a") is None
    assert otc.get_session_trace("s1", "exec-b") is not None


def test_latest_entry_when_execution_id_absent():
    otc.register_session_trace("s1", "a" * 32, "b" * 16, "corr-a", "exec-a")
    otc.register_session_trace("s1", "c" * 32, "d" * 16, "corr-b", "exec-b")
    assert otc.build_otel_trace_headers_for("s1")["X-OTel-Trace-Id"] == "c" * 32


def test_context_var_trace_helpers():
    otc.set_otel_trace_context(TID, SID, "corr")
    assert otc.get_otel_trace_id() == TID
    assert otc.get_otel_span_id() == SID
    assert otc.get_correlation_id() == "corr"
    assert otc.build_otel_trace_headers()["X-OTel-Trace-Id"] == TID
