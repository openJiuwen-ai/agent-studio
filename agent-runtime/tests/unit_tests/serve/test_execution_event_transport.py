# -*- coding: UTF-8 -*-
"""Protocol, ownership and lifecycle checks for the private event transport."""

import asyncio
import copy
import inspect
import json
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import anyio
import pytest
from fastapi import Request
from fastapi.responses import StreamingResponse

from agent_runtime.event_handler.base.trace import Trace
from agent_runtime.event_handler.event_handler import EventHandler
from agent_runtime.schemas.orchestration_mgr import ExecutionRequest
from agent_runtime.serve.apis import orchestration
from agent_runtime.serve.execution_events import ExecutionEventStream, copy_json_event


@pytest.fixture
def registry(monkeypatch):
    instance = SimpleNamespace(register=AsyncMock(), unregister=AsyncMock(), clear_suspension=AsyncMock())
    monkeypatch.setattr(orchestration, "get_execution_registry", lambda: instance)
    return instance


class Runner:
    def __init__(self, events):
        self.events = events
        self.closed = False

    async def run_streaming(self, req, execution_id):
        try:
            for event in self.events:
                yield event
        finally:
            self.closed = True


def handler(debug=False):
    result = EventHandler()
    result.trace = Trace(handler_type="workflow", instance_id="wf", is_debug=debug, start_time=1000)
    result._persist_conversation = AsyncMock()
    return result


def events(answer="中文🙂\\\"\n"):
    return [
        {"event": "workflow_start", "data": {}, "createdTime": 1000},
        {"event": "message", "data": {"answer": answer, "node_type": "Message"}, "createdTime": 1001},
        {"event": "message_end", "data": {"answer": answer, "origin_answer": answer,
         "enable_history": True, "node_type": "Message", "node_id": "message"}, "createdTime": 1002},
        {"event": "workflow_end", "data": {"answer": answer}, "createdTime": 1003},
        {"event": "done", "data": {}, "createdTime": 1004},
    ]


@pytest.mark.parametrize("payload", [
    {"data": {1: "integer", "1": "last", None: (True, 2), 1.5: "float"}},
    {"data": {False: "bool", -0.0: "zero", float("inf"): "infinity"}},
    {"data": ["中文🙂\\\"\n", {"nested": (1, None)}]},
])
def test_event_copy_matches_json_normalization(payload):
    expected = json.loads(json.dumps(payload, ensure_ascii=False))
    assert copy_json_event(payload) == expected


def test_event_copy_isolates_mutable_containers_and_shares_immutable_text():
    text = "x" * (4 * 1024 * 1024)
    original = {"data": {"text": text, "values": [{"secret": 1}]}}
    copied = copy_json_event(original)
    assert copied["data"]["text"] is text
    copied["data"]["values"][0].pop("secret")
    assert original["data"]["values"][0] == {"secret": 1}


@pytest.mark.parametrize("payload", [{"bad": object()}, {"bad": b"bytes"}, {("tuple",): "key"}])
def test_event_copy_preserves_json_validation(payload):
    with pytest.raises(TypeError):
        copy_json_event(payload)


@pytest.mark.parametrize("payload", [
    {"value": datetime(2026, 1, 1)},
    {b"key": "value"},
    {"value": frozenset({1})},
    {"value": Decimal("1.5")},
])
def test_event_copy_matches_json_error_type_and_message(payload):
    with pytest.raises(TypeError) as legacy:
        json.loads(json.dumps(payload, ensure_ascii=False))
    with pytest.raises(TypeError) as structured:
        copy_json_event(payload)
    assert str(structured.value) == str(legacy.value)


def test_event_copy_rejects_cycles_but_allows_repeated_containers():
    shared = [1]
    assert copy_json_event({"a": shared, "b": shared}) == {"a": [1], "b": [1]}
    shared.append(shared)
    with pytest.raises(ValueError, match="Circular reference"):
        copy_json_event({"data": shared})


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["中文🙂\\\"\n", "x" * (4 * 1024 * 1024)], ids=["unicode", "large"])
async def test_private_events_match_legacy_wire_and_history(registry, answer):
    legacy = handler()
    structured = handler()
    request = SimpleNamespace(conversation_id="conv")
    before = orchestration.stream_response(request, "exec", Runner(events(answer)))
    after = orchestration.stream_response(request, "exec", Runner(events(answer)), structured_output=True)
    old_wire = [chunk async for chunk in legacy.get_handler_body_iterator("workflow", before)]
    new_wire = [chunk async for chunk in structured.get_handler_body_iterator("workflow", after)]
    assert new_wire == old_wire
    assert structured.trace.conversation_info == legacy.trace.conversation_info
    assert structured.trace.outputs == legacy.trace.outputs
    assert registry.unregister.await_count == 2


@pytest.mark.asyncio
async def test_private_dict_path_does_not_call_intermediate_codecs(monkeypatch, registry):
    def forbidden(*args, **kwargs):
        raise AssertionError("intermediate SSE codec called")

    monkeypatch.setattr(orchestration, "_serialize_stream_chunk", forbidden)
    monkeypatch.setattr(EventHandler, "parse_sse_line", forbidden)
    runner = Runner(events())
    stream = orchestration.stream_response(SimpleNamespace(conversation_id="conv"), "exec", runner,
                                           structured_output=True)
    output = [chunk async for chunk in handler().get_handler_body_iterator("workflow", stream)]
    assert len(output) == 5
    assert all(isinstance(chunk, bytes) for chunk in output)
    assert runner.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("debug, expected_messages", [(False, None), (True, 1)])
async def test_stream_trace_skips_only_unused_node_messages(debug, expected_messages):
    consumer = handler(debug)

    async def source():
        for event in events():
            yield copy_json_event(event)

    wire = [chunk async for chunk in consumer.get_handler_body_iterator("workflow", source())]
    assert wire
    assert consumer.trace.conversation_info["messages"][0]["content"] == events()[2]["data"]["origin_answer"]
    if expected_messages is None:
        assert consumer.trace.messages is None
    else:
        assert len(consumer.trace.messages) == expected_messages
    consumer._persist_conversation.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_stream_keeps_messages_and_history_without_sse_encoding(monkeypatch):
    consumer = handler()

    def forbidden(*args, **kwargs):
        raise AssertionError("non-stream must not encode SSE")

    monkeypatch.setattr(consumer, "serialize_sse", forbidden)

    async def source():
        for event in events():
            yield copy_json_event(event)

    response = await consumer.get_non_stream_result("workflow", source())
    body = json.loads(response.body)
    assert len(consumer.trace.messages) == 1
    assert consumer.trace.end_time == 1003
    assert body["messages"][0]["content"] == events()[2]["data"]["answer"]
    assert body["outputs"] == {}
    assert body["node_info"] == []
    consumer._persist_conversation.assert_awaited_once()


@pytest.mark.asyncio
async def test_exception_processor_cannot_mutate_upstream_event(registry):
    source_event = {"event": "exception", "data": {"jiuwen_exception_node_id": "private", "message": "failed"}}
    original = copy.deepcopy(source_event)
    stream = orchestration.stream_response(SimpleNamespace(conversation_id="conv"), "exec", Runner([source_event]),
                                           structured_output=True)
    _ = [chunk async for chunk in handler().get_handler_body_iterator("workflow", stream)]
    assert source_event == original


@pytest.mark.asyncio
async def test_response_close_closes_runner_and_unregisters(registry):
    runner = Runner(events())
    source = orchestration.stream_response(SimpleNamespace(conversation_id="conv"), "exec", runner,
                                          structured_output=True)
    response = handler().get_handler_body_iterator("workflow", source)
    await anext(response)
    assert not runner.closed
    await response.aclose()
    assert runner.closed
    registry.unregister.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancellation_closes_runner_and_unregisters(registry):
    started = asyncio.Event()
    closed = asyncio.Event()

    class BlockingRunner:
        async def run_streaming(self, req, execution_id):
            try:
                yield events()[0]
                started.set()
                await asyncio.Future()
            finally:
                closed.set()

    async def consume():
        stream = orchestration.stream_response(SimpleNamespace(conversation_id="conv"), "exec", BlockingRunner(),
                                               structured_output=True)
        async for _ in handler().get_handler_body_iterator("workflow", stream):
            pass

    task = asyncio.create_task(consume())
    await asyncio.wait_for(started.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()
    registry.unregister.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [True, False], ids=["stream", "non-stream"])
async def test_level_cancellation_finishes_awaiting_body_close(streaming):
    blocked = anyio.Event()
    closed = []
    cancelled = []

    class Body:
        def __aiter__(self):
            return self

        async def __anext__(self):
            blocked.set()
            await anyio.sleep_forever()

        async def aclose(self):
            await anyio.sleep(0)
            closed.append(True)

    async def consume():
        consumer = handler()
        try:
            if streaming:
                async for _ in consumer.get_handler_body_iterator("workflow", Body()):
                    pass
            else:
                await consumer.get_non_stream_result("workflow", Body())
        except anyio.get_cancelled_exc_class():
            cancelled.append(True)
            raise

    with anyio.fail_after(2):
        async with anyio.create_task_group() as group:
            group.start_soon(consume)
            await blocked.wait()
            group.cancel_scope.cancel()
    assert closed == [True]
    assert cancelled == [True]


@pytest.mark.asyncio
async def test_cancelled_scope_closes_prefetched_runner_before_propagating(registry):
    closed = []

    class ClosingRunner:
        async def run_streaming(self, req, execution_id):
            try:
                yield events()[0]
            finally:
                await anyio.sleep(0)
                closed.append(True)

    source = orchestration.stream_response(SimpleNamespace(conversation_id="conv"), "exec", ClosingRunner(),
                                           structured_output=True)
    prefetched = orchestration._prefetched_stream(await anext(source), source)
    response = handler().get_handler_body_iterator("workflow", prefetched)
    await anext(response)
    cancelled = []
    with anyio.CancelScope() as scope:
        scope.cancel()
        await response.aclose()
        try:
            await anyio.sleep(0)
        except anyio.get_cancelled_exc_class():
            cancelled.append(True)
            raise
    assert closed == [True]
    registry.unregister.assert_awaited_once()
    assert cancelled == [True]


@pytest.mark.asyncio
async def test_starlette_disconnect_finishes_async_unregister(registry):
    blocked = anyio.Event()
    unregistered = []

    async def unregister(*args, **kwargs):
        await anyio.sleep(0)
        unregistered.append(True)

    registry.unregister.side_effect = unregister

    class BlockingRunner:
        async def run_streaming(self, req, execution_id):
            yield events()[0]
            blocked.set()
            await anyio.sleep_forever()

    source = orchestration.stream_response(SimpleNamespace(conversation_id="conv"), "exec", BlockingRunner(),
                                           structured_output=True)
    prefetched = orchestration._prefetched_stream(await anext(source), source)
    response = await handler().get_stream_result("workflow", prefetched)

    async def receive():
        await blocked.wait()
        return {"type": "http.disconnect"}

    sent = []

    async def send(message):
        sent.append(message)

    with anyio.fail_after(2):
        await response({"type": "http", "asgi": {"spec_version": "2.3"}}, receive, send)
    assert any(m["type"] == "http.response.body" and m.get("body") for m in sent)
    assert unregistered == [True]


@pytest.mark.asyncio
async def test_body_close_failure_logs_exception_details(monkeypatch):
    warnings = []

    class Body:
        async def aclose(self):
            raise RuntimeError("close failed")

    monkeypatch.setattr("agent_runtime.event_handler.event_handler.workflow_logger.warning",
                        lambda *args, **kwargs: warnings.append((args, kwargs)))
    await EventHandler._close_body_iterator(Body())
    assert len(warnings) == 1
    assert warnings[0][1].get("exc_info") is True


@pytest.mark.asyncio
async def test_private_entry_and_public_entry_keep_separate_transports(monkeypatch, registry):
    monkeypatch.setattr(orchestration, "async_ir_load", AsyncMock(return_value={"configs": {"mode": "workflow"}}))
    monkeypatch.setattr(orchestration, "init_moderation_from_ir", lambda _: None)
    monkeypatch.setattr(orchestration, "get_config", lambda: SimpleNamespace(enabled=False))
    monkeypatch.setattr(orchestration, "_get_runner_by_type", lambda _: Runner(events()))
    request = Request({"type": "http", "method": "POST", "path": "/test", "headers": [], "query_string": b""})
    request.state.instance_id = "wf"
    request.state.entry_type = "workflow"
    request.state.project_id = "project"
    private = await orchestration.execute_ir_events(ExecutionRequest(conversationId="conv", irPath="local"), request)
    assert isinstance(private, ExecutionEventStream)
    private_events = [item async for item in private.body_iterator]
    assert all(isinstance(item, dict) for item in private_events)
    public = await orchestration.ir_execute(ExecutionRequest(conversationId="conv", irPath="local"), request)
    assert isinstance(public, StreamingResponse)
    public_frames = [item async for item in public.body_iterator]
    assert all(isinstance(item, (bytes, str)) for item in public_frames)
    assert list(inspect.signature(orchestration.ir_execute).parameters) == ["req", "request"]


@pytest.mark.asyncio
async def test_moderated_structured_stream_closes_both_owned_iterators(monkeypatch, registry):
    closed = []

    async def moderate(source, engine):
        try:
            async for item in source:
                item = dict(item)
                item["data"] = {"answer": "moderated"}
                yield item
        finally:
            closed.append("moderator")

    monkeypatch.setattr(orchestration, "apply_stream_moderation", moderate)
    runner = Runner(events())
    stream = orchestration.stream_response(SimpleNamespace(conversation_id="conv"), "exec", runner,
                                           moderation_engine=object(), structured_output=True)
    item = await anext(stream)
    assert item["data"]["answer"] == "moderated"
    await stream.aclose()
    assert closed == ["moderator"]
    assert runner.closed
    registry.unregister.assert_awaited_once()


@pytest.mark.asyncio
async def test_structured_stream_preserves_terminal_done_payload_and_bytes_fallback(registry):
    terminal = {"event": "done", "data": {"answer": "keep-history"}}
    byte_frame = b'data: {"event": "message", "data": {"answer": "legacy"}}\n\n'
    runner = Runner([terminal, byte_frame, {"event": "task_end", "data": {}}, terminal])
    items = [item async for item in orchestration.stream_response(
        SimpleNamespace(conversation_id="conv"), "exec", runner, structured_output=True
    )]
    assert items[0] == byte_frame
    assert items[1]["event"] == "task_end"
    assert items[-1] == terminal
    assert sum(isinstance(item, dict) and item["event"] == "done" for item in items) == 1


@pytest.mark.asyncio
async def test_processing_error_closes_source_without_persisting_history(monkeypatch):
    consumer = handler()
    closed = []

    async def source():
        try:
            yield events()[0]
            yield events()[1]
        finally:
            closed.append(True)

    def fail(*args, **kwargs):
        raise RuntimeError("processor failed")

    monkeypatch.setattr(consumer, "_process_event", fail)
    output = [chunk async for chunk in consumer.get_handler_body_iterator("workflow", source())]
    assert len(output) == 1
    assert json.loads(output[0].decode()[6:])["event"] == "error"
    assert closed == [True]
    consumer._persist_conversation.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [True, False], ids=["stream", "non-stream"])
async def test_app_run_encapsulation_accepts_private_events(monkeypatch, streaming):
    from agent_runtime.serve.apis import app_run

    assert app_run.ir_execute is orchestration.execute_ir_events
    monkeypatch.setattr(EventHandler, "_persist_conversation", AsyncMock())

    async def source():
        for item in events():
            yield copy_json_event(item)

    request = Request({"type": "http", "method": "POST", "path": "/test", "headers": [],
                       "query_string": b"", "path_params": {"workflow_id": "wf", "conversation_id": "conv"}})
    request.state.user_id = "user"
    request.state.version_id = "version"
    response = ExecutionEventStream(source())
    if streaming:
        result = await app_run._encapsulate_stream_response(response, "workflow", request, "local")
        assert isinstance(result, StreamingResponse)
        frames = [chunk async for chunk in result.body_iterator]
        assert json.loads(frames[-1].decode()[6:])["event"] == "end"
    else:
        result = await app_run._encapsulate_non_stream_response(response, "workflow", request, "local")
        assert result.status_code == 200
        assert json.loads(result.body)["messages"][0]["content"] == events()[2]["data"]["answer"]


@pytest.mark.asyncio
async def test_private_prefetch_error_keeps_json_error_response(monkeypatch, registry):
    class BrokenRunner:
        async def run_streaming(self, *args):
            raise RuntimeError("private-first-event-failure")
            yield

    monkeypatch.setattr(orchestration, "async_ir_load", AsyncMock(return_value={"configs": {"mode": "workflow"}}))
    monkeypatch.setattr(orchestration, "init_moderation_from_ir", lambda _: None)
    monkeypatch.setattr(orchestration, "get_config", lambda: SimpleNamespace(enabled=False))
    monkeypatch.setattr(orchestration, "_get_runner_by_type", lambda _: BrokenRunner())
    request = Request({"type": "http", "method": "POST", "path": "/test", "headers": [], "query_string": b""})
    request.state.instance_id = "wf"
    request.state.entry_type = "workflow"
    request.state.project_id = "project"
    response = await orchestration.execute_ir_events(ExecutionRequest(conversationId="conv", irPath="local"), request)
    assert response.status_code >= 400
    assert not isinstance(response, ExecutionEventStream)
    assert "private-first-event-failure" not in response.body.decode()
    registry.unregister.assert_awaited_once()


def test_event_copy_uses_json_numeric_subclass_values():
    class Number(int):
        def __int__(self):
            return 99

    class DecimalNumber(float):
        def __float__(self):
            return 99.0

    event = {"integer": Number(1), "float": DecimalNumber(1.5)}
    assert copy_json_event(event) == json.loads(json.dumps(event))
