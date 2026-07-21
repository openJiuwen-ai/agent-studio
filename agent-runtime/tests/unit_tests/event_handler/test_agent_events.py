# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for agent_events.py — AgentEventsProcessor."""

from agent_runtime.event_handler.events.agent_events import (
    AgentEventsProcessor,
    _AGENT_BLOCKED_EVENTS,
    _AGENT_THROUGH_EVENTS,
)
from agent_runtime.event_handler.base.trace import Trace


class TestAgentBlockedEvents:
    """Blocked events should return None."""

    @staticmethod
    def test_done_is_blocked():
        assert "done" in _AGENT_BLOCKED_EVENTS

    @staticmethod
    def test_blocked_event_returns_none():
        trace = Trace(handler_type="ReAct")
        result = AgentEventsProcessor.process_event(
            {"event": "done", "createdTime": 1000}, trace
        )
        assert result is None


class TestAgentThroughEvents:
    """Through events should be forwarded as-is."""

    @staticmethod
    def test_through_events_list():
        expected = {
            "agent_interrupted", "scene_match", "plan_start", "plan_end",
            "step_start", "step_end", "task_complete", "task_start", "task_end",
            "workflow_blocked", "workflow_end", "workflow_resume", "workflow_start",
        }
        assert _AGENT_THROUGH_EVENTS == expected

    @staticmethod
    def test_through_event_returns_event_field():
        trace = Trace(handler_type="ReAct", conversation_id="conv-1")
        result = AgentEventsProcessor.process_event(
            {"event": "workflow_start", "data": {"key": "val"}, "createdTime": 1000},
            trace,
        )
        assert result is not None
        assert result.event == "workflow_start"

    @staticmethod
    def test_agent_interrupted_is_forwarded_with_resume_metadata():
        trace = Trace(handler_type="ReAct", conversation_id="conv-r01")
        data = {
            "reason": "waiting_user_input",
            "state": "interrupted",
            "interaction_id": "questioner-r01",
        }

        result = AgentEventsProcessor.process_event(
            {"event": "agent_interrupted", "data": data, "createdTime": 1000},
            trace,
        )

        assert result.event == "agent_interrupted"
        assert result.data == data


class TestProcessStartEvent:
    """Start event processing."""

    @staticmethod
    def test_sets_start_time():
        trace = Trace(handler_type="ReAct")
        result = AgentEventsProcessor.process_event(
            {"event": "start", "createdTime": 1784188116266}, trace
        )
        assert result is not None
        assert result.event == "start"
        assert trace.start_time == 1784188116266


class TestProcessMessageEvent:
    """Message event processing."""

    @staticmethod
    def test_extracts_answer():
        trace = Trace(handler_type="ReAct")
        result = AgentEventsProcessor.process_event(
            {
                "event": "message",
                "data": {"answer": "hello world"},
                "createdTime": 1000,
            },
            trace,
        )
        assert result.content == "hello world"

    @staticmethod
    def test_extracts_think_as_reasoning():
        trace = Trace(handler_type="ReAct")
        result = AgentEventsProcessor.process_event(
            {
                "event": "message",
                "data": {"answer": "answer", "think": "reasoning content"},
                "createdTime": 1000,
            },
            trace,
        )
        assert result.reasoning_content == "reasoning content"

    @staticmethod
    def test_empty_answer_is_none():
        trace = Trace(handler_type="ReAct")
        result = AgentEventsProcessor.process_event(
            {
                "event": "message",
                "data": {"answer": ""},
                "createdTime": 1000,
            },
            trace,
        )
        assert result.content is None


class TestProcessSummaryResponseEvent:
    """Summary response event — sets end_time, outputs, events, status."""

    @staticmethod
    def test_sets_end_time():
        trace = Trace(handler_type="ReAct")
        AgentEventsProcessor.process_event(
            {
                "event": "summary_response",
                "data": {"answer": {"content": "final", "role": "assistant"}},
                "createdTime": 1784279772000,
            },
            trace,
        )
        assert trace.end_time == 1784279772000

    @staticmethod
    def test_initializes_outputs_when_none():
        trace = Trace(handler_type="ReAct")
        assert trace.outputs is None
        AgentEventsProcessor.process_event(
            {
                "event": "summary_response",
                "data": {"answer": {"content": "final", "role": "assistant"}},
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.outputs == {}

    @staticmethod
    def test_initializes_events_when_none():
        trace = Trace(handler_type="ReAct")
        assert trace.events is None
        AgentEventsProcessor.process_event(
            {
                "event": "summary_response",
                "data": {"answer": {"content": "final", "role": "assistant"}},
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.events == []

    @staticmethod
    def test_preserves_existing_events():
        trace = Trace(handler_type="ReAct")
        trace.events = [{"node_id": "n1", "node_type": "llm"}]
        AgentEventsProcessor.process_event(
            {
                "event": "summary_response",
                "data": {"answer": {"content": "final", "role": "assistant"}},
                "createdTime": 2000,
            },
            trace,
        )
        assert len(trace.events) == 1

    @staticmethod
    def test_status_remains_default():
        trace = Trace(handler_type="ReAct")
        AgentEventsProcessor.process_event(
            {
                "event": "summary_response",
                "data": {"answer": {"content": "final", "role": "assistant"}},
                "createdTime": 2000,
            },
            trace,
        )
        # status 保持默认 SUCCESS，不被 summary_response 修改
        assert trace.status is not None

    @staticmethod
    def test_appends_to_messages():
        trace = Trace(handler_type="ReAct")
        AgentEventsProcessor.process_event(
            {
                "event": "summary_response",
                "data": {"answer": {"content": "hello", "role": "assistant"}},
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.messages is not None
        assert len(trace.messages) == 1
        assert trace.messages[0]["role"] == "assistant"
        assert trace.messages[0]["content"] == "hello"

    @staticmethod
    def test_no_message_when_role_missing():
        trace = Trace(handler_type="ReAct")
        AgentEventsProcessor.process_event(
            {
                "event": "summary_response",
                "data": {"answer": {"content": "hello"}},
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.messages is None


class TestProcessAgentNodeMessage:
    """Agent node message — 原样透传给客户端，LLM类型额外写trace.events."""

    @staticmethod
    def test_debug_mode_captures_llm():
        trace = Trace(handler_type="ReAct", is_debug=True)
        result = AgentEventsProcessor.process_event(
            {
                "event": "agent_node_message",
                "data": {
                    "invokeType": "llm",
                    "invokeId": "node-1",
                    "inputs": [{"role": "user", "content": "hi"}],
                    "outputs": {"role": "assistant", "content": "hello"},
                    "startTime": 1000,
                    "endTime": 2000,
                    "metaData": {
                        "instance_attributes": {
                            "model": "model-123",
                            "temperature": 0.0,
                        },
                    },
                },
                "createdTime": 2000,
            },
            trace,
        )
        # 流式模式：原样透传
        assert result is not None
        assert result["event"] == "agent_node_message"
        assert result["data"]["invokeId"] == "node-1"
        assert result["data"]["invokeType"] == "llm"
        # 非流式模式：同时存入 trace.events
        assert trace.events is not None
        assert len(trace.events) == 1
        event_info = trace.events[0]
        assert event_info["node_id"] == "node-1"
        assert event_info["node_type"] == "llm"
        assert event_info["node_status"] == "succeeded"
        assert event_info["model_deployment_id"] == "model-123"

    @staticmethod
    def test_non_debug_mode_passes_through():
        trace = Trace(handler_type="ReAct", is_debug=False)
        result = AgentEventsProcessor.process_event(
            {
                "event": "agent_node_message",
                "data": {
                    "invokeType": "llm",
                    "invokeId": "node-1",
                    "inputs": [],
                    "outputs": {},
                    "metaData": {},
                },
                "createdTime": 1000,
            },
            trace,
        )
        # 非 debug 模式也原样透传
        assert result is not None
        assert result["event"] == "agent_node_message"
        assert trace.events is None

    @staticmethod
    def test_non_llm_invoke_type_passes_through():
        trace = Trace(handler_type="ReAct", is_debug=True)
        result = AgentEventsProcessor.process_event(
            {
                "event": "agent_node_message",
                "data": {
                    "invokeType": "chain",
                    "invokeId": "node-2",
                    "inputs": [],
                    "outputs": {},
                    "metaData": {},
                },
                "createdTime": 1000,
            },
            trace,
        )
        # chain 类型原样透传，不写 trace.events
        assert result is not None
        assert result["event"] == "agent_node_message"
        assert result["data"]["invokeType"] == "chain"
        assert trace.events is None

    @staticmethod
    def test_appends_to_existing_events():
        trace = Trace(handler_type="ReAct", is_debug=True)
        trace.events = [{"node_id": "existing", "node_type": "llm"}]
        AgentEventsProcessor.process_event(
            {
                "event": "agent_node_message",
                "data": {
                    "invokeType": "llm",
                    "invokeId": "node-new",
                    "inputs": [],
                    "outputs": {},
                    "metaData": {"instance_attributes": {}},
                },
                "createdTime": 1000,
            },
            trace,
        )
        assert len(trace.events) == 2
        assert trace.events[1]["node_id"] == "node-new"


class TestProcessEventError:
    """Error handling in process_event."""

    @staticmethod
    def test_unknown_event_uses_through():
        trace = Trace(handler_type="ReAct", conversation_id="conv-1")
        result = AgentEventsProcessor.process_event(
            {"event": "some_unknown_event", "data": {}, "createdTime": 1000},
            trace,
        )
        # 未知事件返回 dict 而不是 EventField 对象
        assert result is not None
        assert result["event"] == "some_unknown_event"
