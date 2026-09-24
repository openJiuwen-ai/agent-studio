"""COM-03 §6.2/§10.3: SSE 出口模式测试——真实 guard + builder 集成。

证明生产可调用的 ``build_sse_error_event`` 使用 SSE builder 构建、
guard 原子控制唯一终态。覆盖:首帧后唯一 SSE error、error 后无 message、
取消无 error、发送失败不递归。
"""

import json

from agent_runtime.error_contract import factory
from agent_runtime.error_contract.stream_state import SseTerminalGuard, StreamState


def test_first_error_produces_sse_frame():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    event = factory.build_sse_error_event(
        "req-sse-001", RuntimeError("boom"), "zh-cn", guard)
    assert event is not None
    assert event.startswith("data: ")
    assert event.endswith("\n\n")
    envelope = json.loads(event[len("data: "):].strip())
    assert envelope["event"] == "error"
    assert envelope["data"]["error_code"] == "openjiuwen.12100004"
    assert envelope["data"]["request_id"] == "req-sse-001"
    assert envelope["data"]["error_msg"]  # non-empty


def test_second_error_blocked_by_guard():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    first = factory.build_sse_error_event("r1", RuntimeError("first"), "zh-cn", guard)
    second = factory.build_sse_error_event("r2", RuntimeError("second"), "zh-cn", guard)
    assert first is not None
    assert second is None  # guard blocked
    assert guard.state == StreamState.TERMINATED


def test_no_message_after_error():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    factory.build_sse_error_event("r", RuntimeError("boom"), "zh-cn", guard)
    assert not guard.allow_message()


def test_cancel_prevents_error():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    guard.cancel()
    event = factory.build_sse_error_event("r", RuntimeError("boom"), "zh-cn", guard)
    assert event is None
    assert guard.state == StreamState.CANCELLED


def test_not_started_no_error():
    guard = SseTerminalGuard()
    event = factory.build_sse_error_event("r", RuntimeError("boom"), "zh-cn", guard)
    assert event is None  # NOT_STARTED: go through HTTP instead


def test_cause_not_in_sse_output():
    guard = SseTerminalGuard()
    guard.begin_streaming()
    event = factory.build_sse_error_event(
        "r", ValueError("secret-detail"), "zh-cn", guard)
    assert "secret-detail" not in event


def test_en_locale_resolves():
    en_guard = SseTerminalGuard()
    en_guard.begin_streaming()
    en_event = factory.build_sse_error_event("r", RuntimeError("x"), "en-us", en_guard)
    zh_guard = SseTerminalGuard()
    zh_guard.begin_streaming()
    zh_event = factory.build_sse_error_event("r", RuntimeError("x"), "zh-cn", zh_guard)
    assert en_event is not None and zh_event is not None
    en_msg = json.loads(en_event[len("data: "):].strip())["data"]["error_msg"]
    zh_msg = json.loads(zh_event[len("data: "):].strip())["data"]["error_msg"]
    assert en_msg != zh_msg
