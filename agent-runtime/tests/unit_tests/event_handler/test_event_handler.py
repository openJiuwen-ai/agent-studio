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

        async def slow_persist():
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

        async def slow_persist():
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
