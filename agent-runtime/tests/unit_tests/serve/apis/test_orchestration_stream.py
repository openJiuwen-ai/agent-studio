# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
stream_response 终态 done 幂等单元测试(R-20，策略 A)。

Controller 的 run_streaming 正常流产 SSE bytes，且自发一个带答案的 done#1(位于 task_end
之前，非末尾)。stream_response 必须吸收 runner 的 done，延迟到流末尾发送唯一一个 done，且
**原样保留 runner done 的 payload**(studio-runtime 的 processOnControllerDoneMessage 消费
done.data.answer 写入会话历史 getMessages→updateConversation)。仅当 runner 未发 done 时
才构造空兜底 done。bytes/dict 统一规则。
"""

# pylint: disable=no-self-use

import json
from unittest.mock import MagicMock

import pytest

from agent_runtime.serve.apis.orchestration import (
    _fallback_terminal_done,
    _serialize_stream_chunk,
    _stream_event_of,
    stream_response,
)


def _sse(event: str, data: dict | None = None) -> bytes:
    """构造 SSE bytes帧(runner 正常流产出的形态)。"""
    payload = {"event": event, "data": data or {}}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _dict(event: str, data: dict | None = None) -> dict:
    """构造 dict 帧(错误流 / 其他 runner 产出的形态)。"""
    return {"event": event, "data": data or {}}


class _FakeRunner:
    """fake runner:run_streaming 按给定 chunk 列表产出。"""

    def __init__(self, chunks):
        self._chunks = chunks

    async def run_streaming(self, req, execution_id):  # noqa: D401
        for chunk in self._chunks:
            yield chunk


async def _collect(gen) -> list:
    """把异步生成器的所有输出收集成列表。"""
    out = []
    async for frame in gen:
        out.append(frame)
    return out


def _parse_events(frames) -> list[dict]:
    """从输出帧解析出 event payload 序列；不可解析帧(坏 UTF-8/非 data:/坏 JSON)跳过。"""
    events = []
    for frame in frames:
        if isinstance(frame, (bytes, bytearray)):
            try:
                frame = bytes(frame).decode("utf-8")
            except UnicodeDecodeError:
                continue
        if not isinstance(frame, str) or not frame.startswith("data: "):
            continue
        try:
            payload = json.loads(frame[6:].strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


class TestStreamResponseTerminalDone:
    """策略 A:done 唯一、末尾，且原样保留 runner done 的 payload。"""

    @pytest.mark.asyncio
    async def test_r20_real_sequence_preserves_done_payload(self):
        """真实序列:done#1(带 answer/node_id/workflow_id，位于 task_end 前)→ 吸收，末尾原样发送。"""
        answer = "🔧【技术·child-B】已接单: 我需要技术支持"
        runner = _FakeRunner([
            _sse("start"),
            _sse("task_start"),
            _sse("workflow_start"),
            _sse("message", {"answer": "🔧"}),
            _sse("message", {"answer": "【技术"}),
            _sse("message", {"answer": "·child-B】"}),
            _sse("message_end", {"answer": answer}),
            _sse("workflow_end", {"answer": answer}),
            _sse("done", {"answer": answer, "node_id": "node_end", "workflow_id": "wf-1"}),  # done#1
            _sse("task_terminated"),
            _sse("task_end"),
        ])

        frames = await _collect(stream_response(MagicMock(), "exec-1", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names.count("done") == 1                       # 唯一
        assert ev_names[-1] == "done"                            # 末尾
        assert ev_names.index("task_terminated") < ev_names.index("task_end") < ev_names.index("done")
        # 策略 A:done#1 的 payload 原样保留(answer/node_id/workflow_id 都在，供 studio-runtime 写会话)
        done = events[-1]
        assert done["data"]["answer"] == answer
        assert done["data"]["node_id"] == "node_end"
        assert done["data"]["workflow_id"] == "wf-1"

    @pytest.mark.asyncio
    async def test_bytes_done_already_last_preserved(self):
        """bytes done 已是末帧:原 done 只发一次，payload 保留。"""
        runner = _FakeRunner([_sse("message", {"answer": "hi"}), _sse("done", {"answer": "hi"})])
        frames = await _collect(stream_response(MagicMock(), "exec-2", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names.count("done") == 1
        assert ev_names[-1] == "done"
        assert events[-1]["data"]["answer"] == "hi"             # payload 保留

    @pytest.mark.asyncio
    async def test_bytes_no_done_fallback_empty(self):
        """bytes 流无 done:末尾补发空兜底 done。"""
        runner = _FakeRunner([_sse("message", {"answer": "x"}), _sse("task_end")])
        frames = await _collect(stream_response(MagicMock(), "exec-3", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names.count("done") == 1
        assert ev_names[-1] == "done"
        assert events[-1]["data"] == {}                         # 无 runner done → 空兜底

    @pytest.mark.asyncio
    async def test_dict_normal_no_done_fallback_empty(self):
        """dict runner 正常无 done(ReactAgent/Workflow):末尾补空兜底，行为不变。"""
        runner = _FakeRunner([_dict("message", {"answer": "y"}), _dict("message_end", {"answer": "y"})])
        frames = await _collect(stream_response(MagicMock(), "exec-4", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names == ["message", "message_end", "done"]
        assert events[-1]["data"] == {}

    @pytest.mark.asyncio
    async def test_dict_error_done_payload_preserved(self):
        """dict 异常 done(workflow except):error 透传，原 done 延迟到末尾且 payload 保留。"""
        runner = _FakeRunner([_dict("error", {"message": "boom"}), _dict("done", {"answer": "boom"})])
        frames = await _collect(stream_response(MagicMock(), "exec-5", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names.count("done") == 1
        assert ev_names[-1] == "done"
        assert ev_names[0] == "error"                           # error 事件原样透传
        assert events[-1]["data"]["answer"] == "boom"           # 原 done payload 保留

    @pytest.mark.asyncio
    async def test_done_then_trailing_frame_deferred(self):
        """done 后有尾帧(bytes):输出 task_end、done，done 的 payload 保留。"""
        runner = _FakeRunner([_sse("done", {"answer": "z"}), _sse("task_end")])
        frames = await _collect(stream_response(MagicMock(), "exec-6", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names == ["task_end", "done"]                 # done 延迟到末尾
        assert events[-1]["data"]["answer"] == "z"

    @pytest.mark.asyncio
    async def test_raw_multi_done_keep_first_payload(self):
        """raw 多 done:保留第一个(带 answer)，只末尾发一次，payload 为第一个的。"""
        runner = _FakeRunner([
            _sse("done", {"answer": "first"}),
            _sse("done", {"answer": "second"}),
            _sse("task_end"),
        ])
        frames = await _collect(stream_response(MagicMock(), "exec-7", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names.count("done") == 1
        assert ev_names[-1] == "done"
        assert events[-1]["data"]["answer"] == "first"          # 保留第一个

    @pytest.mark.asyncio
    async def test_bytearray_non_done_passthrough(self):
        """非 done bytearray 帧原样输出为 bytes，不触发 JSON 序列化异常。"""
        runner = _FakeRunner([bytearray(_sse("message", {"answer": "ba"})), _sse("done", {"answer": "ba"})])
        frames = await _collect(stream_response(MagicMock(), "exec-8", runner))

        # bytearray 帧被原样输出为可 UTF-8 解码的 bytes(未走 json.dumps)
        assert any(
            isinstance(f, (bytes, bytearray)) and b'"event": "message"' in bytes(f)
            for f in frames
        )
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]
        assert ev_names.count("done") == 1
        assert ev_names[-1] == "done"

    @pytest.mark.asyncio
    async def test_bad_frames_do_not_crash(self):
        """非法帧(坏 UTF-8/非 data:/坏 JSON)+ 合法业务帧 + done:不崩溃，末尾一个合法 done。"""
        runner = _FakeRunner([
            b"\xff\xfe not utf-8",                              # 坏 UTF-8 → 透传，解析跳过
            _sse("message", {"answer": "ok"}),
            "data: {not json}\n\n".encode("utf-8"),             # 坏 JSON → 透传，解析跳过
            _sse("done", {"answer": "ok"}),
        ])
        frames = await _collect(stream_response(MagicMock(), "exec-9", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names.count("done") == 1
        assert ev_names[-1] == "done"
        assert events[-1]["data"]["answer"] == "ok"

    @pytest.mark.asyncio
    async def test_none_and_empty_stream_fallback(self):
        """None / 空流:只输出一个空兜底 done。"""
        runner = _FakeRunner([None, None])
        frames = await _collect(stream_response(MagicMock(), "exec-10", runner))
        events = _parse_events(frames)
        ev_names = [e.get("event") for e in events]

        assert ev_names == ["done"]
        assert events[-1]["data"] == {}


class TestStreamEventOf:
    """_stream_event_of 对 bytes/bytearray/dict/异常输入的事件识别。"""

    @staticmethod
    def test_dict_event():
        assert _stream_event_of({"event": "done", "data": {}}) == "done"
        assert _stream_event_of({"event": "message"}) == "message"
        assert _stream_event_of({}) == ""

    @staticmethod
    def test_bytes_sse_event():
        assert _stream_event_of(_sse("done", {"answer": "x"})) == "done"
        assert _stream_event_of(_sse("workflow_end")) == "workflow_end"

    @staticmethod
    def test_bytearray_sse_event():
        assert _stream_event_of(bytearray(_sse("done", {"answer": "x"}))) == "done"

    @staticmethod
    def test_bytes_non_data_frame():
        assert _stream_event_of(b"keep-alive\n\n") == ""

    @staticmethod
    def test_bad_utf8_bytes():
        assert _stream_event_of(b"\xff\xfe bad") == ""

    @staticmethod
    def test_bad_json_bytes():
        assert _stream_event_of("data: {not json}\n\n".encode("utf-8")) == ""

    @staticmethod
    def test_unsupported_type():
        assert _stream_event_of(12345) == ""
        assert _stream_event_of(None) == ""
        assert _stream_event_of("raw string") == ""


class TestSerializeStreamChunk:
    """_serialize_stream_chunk:bytes/bytearray 原样，dict 序列化。"""

    @staticmethod
    def test_bytes_passthrough():
        b = _sse("message", {"answer": "x"})
        assert _serialize_stream_chunk(b) == b

    @staticmethod
    def test_bytearray_to_bytes():
        ba = bytearray(_sse("message", {"answer": "x"}))
        out = _serialize_stream_chunk(ba)
        assert isinstance(out, bytes)
        assert out == bytes(ba)

    @staticmethod
    def test_dict_serialized():
        out = _serialize_stream_chunk({"event": "done", "data": {"answer": "y"}})
        assert isinstance(out, str)
        assert out.startswith("data: ")
        payload = json.loads(out[6:].strip())
        assert payload["data"]["answer"] == "y"


class TestFallbackTerminalDone:
    """_fallback_terminal_done:空 data 兜底终态。"""

    @staticmethod
    def test_empty_data():
        frame = _fallback_terminal_done("exec-x")
        assert frame.startswith("data: ")
        payload = json.loads(frame[6:].strip())
        assert payload["event"] == "done"
        assert payload["data"] == {}
        assert payload["executionId"] == "exec-x"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
