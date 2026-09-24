"""COM-03 §6.2/§10.3: Builder SSE 出口模式测试——真实 guard + builder 集成。"""

import json

from agent_builder.common.error_contract import factory
from agent_builder.common.error_contract.stream_state import (
    SseTerminalGuard,
    StreamState,
)


def test_first_error_produces_sse_frame():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    event = factory.build_sse_error_event(
        "req-bld-sse", RuntimeError("boom"), "zh-cn", guard)
    assert event is not None
    assert event.startswith("data: ")
    envelope = json.loads(event[len("data: "):].strip())
    assert envelope["event"] == "error"
    assert envelope["data"]["error_code"] == "openjiuwen.13100004"
    assert envelope["data"]["request_id"] == "req-bld-sse"


def test_second_error_blocked():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    factory.build_sse_error_event("r1", RuntimeError("first"), "zh-cn", guard)
    second = factory.build_sse_error_event("r2", RuntimeError("second"), "zh-cn", guard)
    assert second is None
    assert guard.state == StreamState.TERMINATED


def test_no_message_after_error():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    factory.build_sse_error_event("r", RuntimeError("x"), "zh-cn", guard)
    assert not guard.allow_message()


def test_cancel_prevents_error():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    guard.cancel()
    assert factory.build_sse_error_event("r", RuntimeError("x"), "zh-cn", guard) is None


def test_cause_not_in_output():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    event = factory.build_sse_error_event("r", ValueError("secret"), "zh-cn", guard)
    assert "secret" not in event
