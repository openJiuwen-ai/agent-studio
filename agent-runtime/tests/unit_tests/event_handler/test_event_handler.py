# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for event_handler.py — EventHandler main entry."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse

from agent_runtime.event_handler.event_handler import EventHandler
from agent_runtime.event_handler.base.trace import Trace
from agent_runtime.event_handler.base.field_processor import FieldDataProcessor
from agent_runtime.common.background_task import INFLIGHT_KEY_PREFIX


class TestParseSSELine:
    """SSE line parser tests."""

    @staticmethod
    def test_valid_data_line():
        result = EventHandler.parse_sse_line(b'data: {"event":"start"}')
        assert result == {"event": "start"}

    @staticmethod
    def test_valid_data_line_string():
        result = EventHandler.parse_sse_line('data: {"event":"message"}')
        assert result == {"event": "message"}

    @staticmethod
    def test_non_data_line():
        result = EventHandler.parse_sse_line(b"event: ping")
        assert result is None

    @staticmethod
    def test_empty_data():
        result = EventHandler.parse_sse_line(b"data: ")
        assert result is None

    @staticmethod
    def test_invalid_json():
        result = EventHandler.parse_sse_line(b"data: not-json")
        assert result is None

    @staticmethod
    def test_complex_payload():
        payload = {"event": "message", "data": {"answer": "hello", "node_type": "LLM"}}
        result = EventHandler.parse_sse_line(f"data: {json.dumps(payload)}".encode())
        assert result == payload


class TestSerializeSSE:
    """SSE serializer tests."""

    @staticmethod
    def test_basic_serialization():
        result = EventHandler.serialize_sse({"event": "start"})
        assert result == b'data: {"event": "start"}\n\n'

    @staticmethod
    def test_unicode_content():
        result = EventHandler.serialize_sse({"event": "message", "content": "你好"})
        assert "你好".encode("utf-8") in result

    @staticmethod
    def test_ends_with_double_newline():
        result = EventHandler.serialize_sse({"event": "done"})
        assert result.endswith(b"\n\n")


class TestGetEventHandler:
    """Handler dispatch tests."""

    @staticmethod
    def test_workflow_handler():
        handler = EventHandler()
        trace = Trace()
        processor = handler.get_event_handler("workflow", trace)
        assert processor is not None

    @staticmethod
    def test_react_handler():
        handler = EventHandler()
        trace = Trace()
        processor = handler.get_event_handler("ReAct", trace)
        assert processor is not None

    @staticmethod
    def test_controller_handler():
        handler = EventHandler()
        trace = Trace()
        processor = handler.get_event_handler("Controller", trace)
        assert processor is not None

    @staticmethod
    def test_planexecute_handler():
        handler = EventHandler()
        trace = Trace()
        processor = handler.get_event_handler("PlanExecute", trace)
        assert processor is not None

    @staticmethod
    def test_unsupported_handler_raises():
        handler = EventHandler()
        trace = Trace()
        with pytest.raises(ValueError, match="Unsupported handler type"):
            handler.get_event_handler("UnknownType", trace)
        assert trace.error_code == 121007


class TestInitTrace:
    """Trace initialization tests."""

    @staticmethod
    def test_init_trace_from_request():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-123", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="user-1", version_id="v1")
        request.headers = {"x-invoke-mode": "debug", "x-language": "zh-cn"}

        handler.init_trace("workflow", request, "workflow/ir/wf-1/wf-1_v1.json")

        assert handler.trace.conversation_id == "conv-123"
        assert handler.trace.user_id == "user-1"
        assert handler.trace.version_id == "v1"
        assert handler.trace.is_debug is True
        assert handler.trace.language == "zh-cn"
        assert handler.trace.instance_id == "wf-1"
        assert handler.trace.handler_type == "workflow"

    @staticmethod
    def test_init_trace_non_debug():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "agent_id": "a1"}
        request.state = MagicMock(user_id="", version_id="")
        request.headers = {"x-invoke-mode": "normal"}

        handler.init_trace("ReAct", request, "agent/ir/a1/a1.json")

        assert handler.trace.is_debug is False
        assert handler.trace.instance_id == "a1"

    @staticmethod
    def test_init_trace_default_language():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="", version_id="")
        request.headers = {}

        handler.init_trace("workflow", request, "ir/path.json")

        assert handler.trace.language == "en-us"

    @staticmethod
    def test_init_trace_missing_instance_id_raises():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1"}
        request.state = MagicMock(user_id="", version_id="")
        # Ensure getattr(request.state, "instance_id", "") returns ""
        del request.state.instance_id
        request.headers = {}

        with pytest.raises(ValueError, match="agent_id or workflow_id"):
            handler.init_trace("workflow", request, "ir/path.json")

    @staticmethod
    def test_init_trace_fallback_to_request_state_instance_id():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        # Web run path: short_code in path_params, no agent_id/workflow_id
        request.path_params = {"conversation_id": "conv-1", "short_code": "EdlN4z9G"}
        request.state = MagicMock(user_id="", version_id="", instance_id="wf-from-release")
        request.headers = {}

        handler.init_trace("workflow", request, "ir/path.json")

        assert handler.trace.instance_id == "wf-from-release"

    @staticmethod
    def test_init_trace_agent_id_preferred():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "agent_id": "agent-x"}
        request.state = MagicMock(user_id="u1", version_id="v2")
        request.headers = {}

        handler.init_trace("ReAct", request, "agent/ir/agent-x/agent-x_v2.json")

        assert handler.trace.instance_id == "agent-x"


class TestGenerateOutputData:
    """Output data generator tests."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_none_returns_nothing():
        chunks = []
        async for chunk in EventHandler.generate_output_data(None):
            chunks.append(chunk)
        assert len(chunks) == 0

    @staticmethod
    @pytest.mark.asyncio
    async def test_dict_yields_single_chunk():
        chunks = []
        async for chunk in EventHandler.generate_output_data({"event": "start"}):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert b'"event": "start"' in chunks[0]

    @staticmethod
    @pytest.mark.asyncio
    async def test_list_yields_one_chunk():
        items = [{"event": "a"}, {"event": "b"}]
        chunks = []
        async for chunk in EventHandler.generate_output_data(items):
            chunks.append(chunk)
        # 列表中的每个项都会生成一个 chunk
        assert len(chunks) == 2

    @staticmethod
    @pytest.mark.asyncio
    async def test_pydantic_model_yields_chunk():
        from agent_runtime.event_handler.base.models import EventField
        field = EventField(event="message", createdTime=1000)
        chunks = []
        async for chunk in EventHandler.generate_output_data(field):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert b'"event": "message"' in chunks[0]

    @staticmethod
    @pytest.mark.asyncio
    async def test_unsupported_type_returns_nothing():
        chunks = []
        async for chunk in EventHandler.generate_output_data(42):
            chunks.append(chunk)
        assert len(chunks) == 0


class TestGetNonStreamResult:
    """Non-stream result aggregation tests."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_returns_json_response():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="user-1", version_id="")
        request.headers = {"x-invoke-mode": "normal", "x-language": "en-us"}
        handler.init_trace("workflow", request, "wf/ir/wf-1/wf-1.json")

        async def empty_iterator():
            return
            yield  # make it an async generator

        result = await handler.get_non_stream_result("workflow", empty_iterator())
        assert isinstance(result, JSONResponse)

    @staticmethod
    @pytest.mark.asyncio
    async def test_excludes_none_fields():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="", version_id="")
        request.headers = {}
        handler.init_trace("workflow", request, "wf/ir/wf-1/wf-1.json")
        handler.trace.start_time = 1000

        async def empty_iterator():
            return
            yield

        result = await handler.get_non_stream_result("workflow", empty_iterator())
        assert isinstance(result, JSONResponse)

    @staticmethod
    @pytest.mark.asyncio
    async def test_processes_sse_events():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="", version_id="")
        request.headers = {}
        handler.init_trace("workflow", request, "wf/ir/wf-1/wf-1.json")

        start_event = json.dumps({"event": "workflow_start", "createdTime": 1784279771000})
        end_event = json.dumps({
            "event": "workflow_end",
            "createdTime": 1784279772000,
            "data": {"answer": "result"},
        })

        async def mock_iterator():
            yield f"data: {start_event}\n\n".encode()
            yield f"data: {end_event}\n\n".encode()

        with patch.object(handler, "_persist_conversation", new_callable=AsyncMock):
            result = await handler.get_non_stream_result("workflow", mock_iterator())

        assert isinstance(result, JSONResponse)
        # workflow_start 事件会设置 start_time 为 createdTime
        assert handler.trace.end_time == 1784279772000


class TestGetStreamResult:
    """Stream result tests."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_returns_streaming_response():
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="", version_id="")
        request.headers = {}
        handler.init_trace("workflow", request, "wf/ir/wf-1/wf-1.json")

        async def empty_iterator():
            return
            yield

        result = await handler.get_stream_result("workflow", empty_iterator())
        assert isinstance(result, StreamingResponse)
        assert result.media_type == "text/event-stream"


class TestEncapsulateStreamResponse:
    """Class-level stream encapsulation tests."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_encapsulate_stream_response():
        mock_response = MagicMock(spec=StreamingResponse)

        async def mock_body():
            return
            yield

        mock_response.body_iterator = mock_body()

        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="", version_id="")
        request.headers = {}

        result = await EventHandler.encapsulate_stream_response(
            mock_response, "workflow", request, "wf/ir/wf-1/wf-1.json"
        )
        assert isinstance(result, StreamingResponse)


class TestEncapsulateNonStreamResponse:
    """Class-level non-stream encapsulation tests."""

    @staticmethod
    @pytest.mark.asyncio
    async def test_encapsulate_non_stream_response():
        mock_response = MagicMock(spec=StreamingResponse)

        async def mock_body():
            return
            yield

        mock_response.body_iterator = mock_body()

        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="", version_id="")
        request.headers = {}

        result = await EventHandler.encapsulate_non_stream_response(
            mock_response, "workflow", request, "wf/ir/wf-1/wf-1.json"
        )
        assert isinstance(result, JSONResponse)


class TestPersistConversationInBackground:
    """终态事件不再被会话历史落库阻塞（fire-and-forget 后台执行）。"""

    @staticmethod
    def _make_react_handler() -> EventHandler:
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-1", "agent_id": "agent-1"}
        request.state = MagicMock(user_id="user-1", version_id="")
        request.headers = {}
        handler.init_trace("ReAct", request, "agent/ir/agent-1/agent-1.json")
        return handler

    @staticmethod
    @pytest.mark.asyncio
    async def test_done_emitted_before_persist_completes():
        """persist 被阻塞时 done 事件仍立即发出，且后台任务最终完成。"""
        handler = TestPersistConversationInBackground._make_react_handler()
        persist_started = asyncio.Event()
        persist_release = asyncio.Event()
        persist_finished = asyncio.Event()

        async def slow_persist(**_kwargs):
            persist_started.set()
            await persist_release.wait()
            persist_finished.set()

        async def body():
            summary = json.dumps({
                "event": "summary_response",
                "createdTime": 1784279772000,
                "data": {"answer": {"role": "assistant", "content": "ok"}},
            })
            yield f"data: {summary}\n\n".encode()

        with patch.object(handler, "_persist_conversation", side_effect=slow_persist):
            events = []
            async for chunk in handler.get_handler_body_iterator("ReAct", body()):
                payload = chunk.decode("utf-8")
                assert payload.startswith("data: ")
                events.append(json.loads(payload[6:]))

        # done 已在 persist 明确未完成（release 未触发）时送达
        assert not persist_finished.is_set()
        assert events, "stream should yield events"
        assert events[-1].get("event") == "done"

        # 后台任务随后执行并完成
        for _ in range(200):
            if persist_started.is_set():
                break
            await asyncio.sleep(0.01)
        assert persist_started.is_set()
        persist_release.set()
        for _ in range(200):
            if persist_finished.is_set():
                break
            await asyncio.sleep(0.01)
        assert persist_finished.is_set()

    @staticmethod
    @pytest.mark.asyncio
    async def test_controller_end_event_not_blocked_by_persist():
        """Controller 模式：终态 end 事件同样不等待 persist。"""
        handler = TestPersistConversationInBackground._make_react_handler()
        handler.trace.handler_type = "Controller"
        persist_release = asyncio.Event()

        async def slow_persist(**_kwargs):
            await persist_release.wait()

        async def body():
            task_end = json.dumps({
                "event": "task_end",
                "createdTime": 1784279773000,
                "data": {},
            })
            yield f"data: {task_end}\n\n".encode()

        with patch.object(handler, "_persist_conversation", side_effect=slow_persist):
            events = []
            async for chunk in handler.get_handler_body_iterator(
                "Controller", body()
            ):
                payload = chunk.decode("utf-8")
                events.append(json.loads(payload[6:]))

        assert events, "stream should yield events"
        assert events[-1].get("event") == "end"
        persist_release.set()
        # 给后台任务让出控制权完成，避免悬挂任务告警
        for _ in range(100):
            await asyncio.sleep(0)

    @staticmethod
    @pytest.mark.asyncio
    async def test_without_init_trace_workflow_mode_matches_old_behavior():
        """未 init_trace（conv_manager 为空）时跳过后台落库、无终态注入、不报错。"""
        handler = EventHandler()

        async def body():
            yield (
                b'data: {"event":"message","data":{"answer":"hi"},'
                b'"createdTime":1}\n\n'
            )

        events = []
        async for chunk in handler.get_handler_body_iterator("workflow", body()):
            payload = chunk.decode("utf-8")
            events.append(json.loads(payload[6:]))

        assert len(events) == 1
        assert events[0].get("event") == "message"

    @staticmethod
    @pytest.mark.asyncio
    async def test_kill_switch_persists_synchronously_before_done():
        """PERSIST_BACKGROUND_ENABLE=false 回退同步落库：done 发出前 persist 已完成。"""
        handler = TestPersistConversationInBackground._make_react_handler()
        persist_done = False

        async def slow_persist():
            nonlocal persist_done
            await asyncio.sleep(0.05)
            persist_done = True

        async def body():
            summary = json.dumps({
                "event": "summary_response",
                "createdTime": 1784279772000,
                "data": {"answer": {"role": "assistant", "content": "ok"}},
            })
            yield f"data: {summary}\n\n".encode()

        with patch.object(
            handler, "_persist_conversation", side_effect=slow_persist
        ):
            with patch(
                "agent_runtime.event_handler.event_handler."
                "backgrounding_enabled",
                return_value=False,
            ):
                events = []
                async for chunk in handler.get_handler_body_iterator(
                    "ReAct", body()
                ):
                    evt = json.loads(chunk.decode("utf-8")[6:])
                    events.append(evt)
                    if evt.get("event") == "done":
                        assert persist_done, "同步模式下 done 前 persist 应已完成"
        assert events[-1].get("event") == "done"


class _LeaseFakeRedis:
    """租约原语内存 Redis：bytes 语义，与 test_background_task._FakeRedis 同口径。"""

    def __init__(self):
        self.store = {}
        self.hset_calls = {}

    @staticmethod
    def _b(value):
        return value if isinstance(value, bytes) else str(value).encode()

    async def hset(self, key, field, value):
        self.store.setdefault(key, {})[self._b(field)] = self._b(value)
        self.hset_calls[key] = self.hset_calls.get(key, 0) + 1
        return 1

    async def hdel(self, key, *fields):
        entry = self.store.get(key)
        if entry is None:
            return 0
        removed = 0
        for field in fields:
            if entry.pop(self._b(field), None) is not None:
                removed += 1
        if not entry:
            self.store.pop(key, None)
        return removed

    async def hgetall(self, key):
        return dict(self.store.get(key, {}))

    async def expire(self, key, seconds):
        return True


def _workflow_terminal_body():
    """构造 workflow_end + done 两终态帧的上游 SSE 流（done 由 stream_response 保证唯一末尾）。"""
    frames = [
        {"event": "workflow_end", "createdTime": 1784279772000, "data": {"answer": "ok"}},
        {"event": "done", "createdTime": 1784279773000},
    ]

    async def body():
        for frame in frames:
            yield f"data: {json.dumps(frame)}\n\n".encode()

    return body()


class TestWorkflowTerminalFrameLeaseOrder:
    """workflow 终态帧转发前前置登记落库租约（消除「终态已可见、租约不可见」窗口）。"""

    _LEASE_KEY = f"{INFLIGHT_KEY_PREFIX}conv-wf"

    @staticmethod
    def _make_workflow_handler() -> EventHandler:
        handler = EventHandler()
        request = MagicMock(spec=Request)
        request.path_params = {"conversation_id": "conv-wf", "workflow_id": "wf-1"}
        request.state = MagicMock(user_id="user-1", version_id="")
        request.headers = {}
        handler.init_trace("workflow", request, "wf/ir/wf-1/wf-1.json")
        return handler

    @staticmethod
    @pytest.mark.asyncio
    async def test_lease_registered_before_terminal_frame_forwarded():
        """终态帧送达消费者时租约必须已 HSET；done 帧不二次登记；任务完成后 HDEL。"""
        handler = TestWorkflowTerminalFrameLeaseOrder._make_workflow_handler()
        fake_redis = _LeaseFakeRedis()
        persist_release = asyncio.Event()
        persist_started = asyncio.Event()

        async def slow_persist(**_kwargs):
            persist_started.set()
            await persist_release.wait()

        lease_key = TestWorkflowTerminalFrameLeaseOrder._LEASE_KEY
        with patch.object(handler, "_persist_conversation", side_effect=slow_persist):
            with patch(
                "agent_runtime.common.background_task._get_redis",
                return_value=fake_redis,
            ):
                chunks = 0
                async for chunk in handler.get_handler_body_iterator(
                    "workflow", _workflow_terminal_body()
                ):
                    chunks += 1
                    # 每个对外帧（首帧即 workflow_end 变换结果）送达时租约已可见
                    assert fake_redis.store.get(lease_key), (
                        "terminal frame forwarded before lease registered"
                    )
                assert chunks >= 1
                assert fake_redis.hset_calls.get(lease_key) == 1, (
                    "lease must be registered exactly once (no double registration)"
                )
                persist_release.set()
                for _ in range(200):
                    if not fake_redis.store.get(lease_key):
                        break
                    await asyncio.sleep(0.01)
                assert persist_started.is_set()
                assert not fake_redis.store.get(lease_key), (
                    "lease field must be HDEL-ed after persist task completes"
                )

    @staticmethod
    @pytest.mark.asyncio
    async def test_payload_snapshot_ignores_later_trace_mutation():
        """载荷在登记时刻快照：任务执行期不读可变 trace 字段。"""
        handler = TestWorkflowTerminalFrameLeaseOrder._make_workflow_handler()
        handler.trace.query = "hello"
        handler.trace.conversation_info = {
            "messages": [{"role": "assistant", "content": "round-1 answer"}],
        }
        fake_redis = _LeaseFakeRedis()
        persist_release = asyncio.Event()
        captured = {}

        async def blocking_persist(payload=None):
            captured["payload"] = payload
            await persist_release.wait()

        lease_key = TestWorkflowTerminalFrameLeaseOrder._LEASE_KEY
        with patch.object(handler, "_persist_conversation", side_effect=blocking_persist):
            with patch(
                "agent_runtime.common.background_task._get_redis",
                return_value=fake_redis,
            ):
                async for _ in handler.get_handler_body_iterator(
                    "workflow", _workflow_terminal_body()
                ):
                    pass
                # 落库被阻塞、流已结束：此刻突变 trace，证明任务执行不重读
                handler.trace.conversation_info["messages"].append(
                    {"role": "assistant", "content": "MUTATED"}
                )
                persist_release.set()
                for _ in range(200):
                    if not fake_redis.store.get(lease_key):
                        break
                    await asyncio.sleep(0.01)

        payload = captured.get("payload")
        assert payload is not None, "persist must receive registration-time snapshot"
        messages, dialogue_end = payload
        assert dialogue_end is True
        assert any(
            m.get("role") == "user" and m.get("content") == "hello" for m in messages
        )
        assert any(m.get("content") == "round-1 answer" for m in messages)
        assert not any("MUTATED" in str(m.get("content", "")) for m in messages)

    @staticmethod
    @pytest.mark.asyncio
    async def test_registration_failure_degrades_to_post_loop():
        """loop 内登记异常 → 流不中断，loop 后兜底登记恰好一次。"""
        handler = TestWorkflowTerminalFrameLeaseOrder._make_workflow_handler()
        mock_persist = AsyncMock()
        with patch.object(handler, "_persist_conversation", mock_persist):
            with patch.object(
                FieldDataProcessor,
                "generate_memory_history_messages",
                side_effect=[RuntimeError("snapshot boom"), []],
            ):
                events = []
                async for chunk in handler.get_handler_body_iterator(
                    "workflow", _workflow_terminal_body()
                ):
                    events.append(json.loads(chunk.decode("utf-8")[6:]))
        assert events, "stream should still deliver frames after registration failure"
        for _ in range(200):
            if mock_persist.await_count >= 1:
                break
            await asyncio.sleep(0.01)
        assert mock_persist.await_count == 1, (
            "post-loop fallback must register persist exactly once"
        )
        assert mock_persist.await_args.kwargs.get("payload") == ([], True)

    @staticmethod
    @pytest.mark.asyncio
    async def test_kill_switch_skips_in_loop_registration():
        """回滚开关关闭：workflow 模式不做 loop 内租约登记，loop 后同步落库（与后台化前一致）。"""
        handler = TestWorkflowTerminalFrameLeaseOrder._make_workflow_handler()
        fake_redis = _LeaseFakeRedis()
        persist_done = asyncio.Event()

        async def sync_persist(**_kwargs):
            persist_done.set()

        with patch.object(handler, "_persist_conversation", side_effect=sync_persist):
            with patch(
                "agent_runtime.event_handler.event_handler.backgrounding_enabled",
                return_value=False,
            ):
                with patch(
                    "agent_runtime.common.background_task._get_redis",
                    return_value=fake_redis,
                ):
                    events = []
                    async for chunk in handler.get_handler_body_iterator(
                        "workflow", _workflow_terminal_body()
                    ):
                        events.append(json.loads(chunk.decode("utf-8")[6:]))
                        # 同步模式下终态帧不等待落库（落库在 loop 后，与后台化前行为一致）
                        assert not persist_done.is_set()
        assert events
        assert persist_done.is_set(), "post-loop synchronous persist must complete"
        assert not fake_redis.store, "no lease registration when backgrounding disabled"
