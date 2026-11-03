"""COM-03 §10.3: Runtime SSE builder + terminal guard 契约测试。"""

import os

from agent_runtime.error_contract.descriptor import ErrorDescriptor
from agent_runtime.error_contract.http_builder import I18nResolver
from agent_runtime.error_contract.sse_builder import build_sse_error_envelope, format_sse_event
from agent_runtime.error_contract.stream_state import StreamState, SseTerminalGuard
from agent_runtime.error_contract import catalog


_I18N_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "agent_runtime", "event_handler", "base", "resources", "i18n",
)
_RESOLVER = I18nResolver(
    _I18N_DIR,
    {"zh_cn": "runtime-msg_zh_CN.properties", "en_us": "runtime-msg_en_US.properties"},
)


def _descriptor(**overrides):
    defn = catalog.resolve("openjiuwen.12100004")
    defaults = dict(
        error_code=defn.error_code, http_status=defn.http_status,
        message_key=defn.message_key, reason_key=defn.reason_key,
        suggestion_key=defn.suggestion_key, request_id="req-sse-001",
    )
    defaults.update(overrides)
    return ErrorDescriptor(**defaults)


# ---- SSE envelope structure ----

def test_envelope_has_event_error():
    env = build_sse_error_envelope(_descriptor(), "zh_cn", _RESOLVER)
    assert env["event"] == "error"


def test_envelope_data_has_five_fields():
    env = build_sse_error_envelope(_descriptor(), "zh_cn", _RESOLVER)
    data = env["data"]
    for field in ("error_code", "error_msg", "error_reason", "error_suggestion", "request_id"):
        assert data[field], f"{field} should be non-empty"


def test_envelope_request_id_matches_descriptor():
    env = build_sse_error_envelope(_descriptor(request_id="req-xyz"), "zh_cn", _RESOLVER)
    assert env["data"]["request_id"] == "req-xyz"


def test_envelope_excludes_cause_and_downstream():
    env = build_sse_error_envelope(
        _descriptor(cause=ValueError("secret"),
                    downstream_service="builder",
                    downstream_error_code="test-fake"),
        "zh_cn", _RESOLVER,
    )
    env_str = str(env)
    assert "secret" not in env_str
    assert "downstream" not in env_str
    assert "cause" not in env["data"]


def test_format_sse_event_produces_data_prefix():
    env = build_sse_error_envelope(_descriptor(), "zh_cn", _RESOLVER)
    wire = format_sse_event(env)
    assert wire.startswith("data: ")
    assert wire.endswith("\n\n")


# ---- Terminal guard ----

def test_guard_initial_state_not_started():
    g = SseTerminalGuard()
    assert g.state == StreamState.NOT_STARTED


def test_guard_not_started_should_not_send_error():
    g = SseTerminalGuard()
    assert not g.should_send_error()


def test_guard_begin_streaming():
    g = SseTerminalGuard()
    assert g.begin_streaming()
    assert g.state == StreamState.STREAMING


def test_guard_begin_streaming_only_once():
    g = SseTerminalGuard()
    assert g.begin_streaming()
    assert not g.begin_streaming()


def test_guard_streaming_should_send_error():
    g = SseTerminalGuard()
    g.begin_streaming()
    assert g.should_send_error()


def test_guard_mark_error_sent_terminates():
    g = SseTerminalGuard()
    g.begin_streaming()
    g.mark_error_sent()
    assert g.state == StreamState.TERMINATED
    assert g.error_sent
    assert not g.should_send_error()


def test_guard_no_message_after_terminated():
    g = SseTerminalGuard()
    g.begin_streaming()
    g.mark_error_sent()
    assert not g.allow_message()


def test_guard_cancel_prevents_error():
    g = SseTerminalGuard()
    g.begin_streaming()
    g.cancel()
    assert g.state == StreamState.CANCELLED
    assert not g.should_send_error()


def test_guard_cancel_after_error_stays_terminated():
    g = SseTerminalGuard()
    g.begin_streaming()
    g.mark_error_sent()
    g.cancel()
    assert g.state == StreamState.TERMINATED


def test_guard_only_one_error():
    g = SseTerminalGuard()
    g.begin_streaming()
    assert g.should_send_error()
    g.mark_error_sent()
    assert not g.should_send_error()  # second error blocked
