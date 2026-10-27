# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for workflow_events.py — WorkflowEventsProcessor."""

from unittest.mock import patch, MagicMock

import pytest

from agent_runtime.event_handler.events.workflow_events import (
    WorkflowEventsProcessor,
    _WORKFLOW_BLOCKED_EVENTS,
)
from agent_runtime.event_handler.base.trace import Trace


class TestWorkflowBlockedEvents:
    """Blocked events should return None."""

    @staticmethod
    def test_start_is_blocked():
        assert "start" in _WORKFLOW_BLOCKED_EVENTS

    @staticmethod
    def test_intermediate_message_is_blocked():
        assert "intermediate_message" in _WORKFLOW_BLOCKED_EVENTS

    @staticmethod
    def test_blocked_event_returns_none():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {"event": "start", "createdTime": 1000}, trace
        )
        assert result is None


class TestProcessWorkflowStart:
    """Workflow start event."""

    @staticmethod
    def test_returns_workflow_started_event():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {"event": "workflow_start", "createdTime": 1784279771000}, trace
        )
        assert result.event == "workflow_started"
        assert result.data["start_time"] == 1784279771000

    @staticmethod
    def test_start_frame_propagates_workflow_id_and_name():
        """data 携带 workflow_id/workflow_name 时透传并写入 trace。"""
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "workflow_start",
                "data": {"workflow_id": "wf-123", "workflow_name": "test"},
                "createdTime": 1000,
            },
            trace,
        )
        assert result.data["workflow_id"] == "wf-123"
        assert result.data["workflow_name"] == "test"
        assert trace.workflow_id == "wf-123"
        assert trace.workflow_name == "test"

    @staticmethod
    def test_start_frame_falls_back_to_trace_instance_id():
        """data 为空时回退 trace.instance_id；workflow_name 缺省时不输出 null 键。"""
        trace = Trace(handler_type="Workflow", instance_id="wf-from-path")
        result = WorkflowEventsProcessor.process_event(
            {"event": "workflow_start", "data": {}, "createdTime": 1000},
            trace,
        )
        assert result.data["workflow_id"] == "wf-from-path"
        assert "workflow_name" not in result.data

    @staticmethod
    def test_preserves_workflow_id_and_name():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "workflow_start",
                "createdTime": 1784279771000,
                "data": {
                    "workflow_id": "child-wf-1",
                    "workflow_name": "子工作流",
                },
            },
            trace,
        )
        assert result.event == "workflow_started"
        assert result.data["start_time"] == 1784279771000
        assert result.data["workflow_id"] == "child-wf-1"
        assert result.data["workflow_name"] == "子工作流"


class TestProcessMessage:
    """Workflow message event."""

    @staticmethod
    def test_extracts_text():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "message",
                "data": {
                    "answer": "hello",
                    "node_type": "LLMChain",
                    "node_id": "n1",
                    "node_name": "LLM Node",
                },
                "createdTime": 1000,
            },
            trace,
        )
        assert result.event == "message"
        assert result.data["text"] == "hello"
        assert result.data["node_type"] == "LLM"

    @staticmethod
    def test_extracts_reasoning_content():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "message",
                "data": {"answer": "ans", "think": "reasoning"},
                "createdTime": 1000,
            },
            trace,
        )
        assert result.data["reasoning_content"] == "reasoning"

    @staticmethod
    def test_message_propagates_workflow_id_from_trace():
        """start 帧写入 trace 后，message 帧回退使用 trace.workflow_id/instance_id。"""
        trace = Trace(handler_type="Workflow", instance_id="wf-from-path")
        # 模拟 start 帧已写入 trace
        WorkflowEventsProcessor.process_event(
            {
                "event": "workflow_start",
                "data": {"workflow_id": "wf-123", "workflow_name": "test"},
                "createdTime": 1000,
            },
            trace,
        )
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "message",
                "data": {"answer": "hi", "node_type": "End", "node_id": "n1"},
                "createdTime": 2000,
            },
            trace,
        )
        assert result.data["workflow_id"] == "wf-123"
        assert result.data["workflow_name"] == "test"


class TestProcessMessageEnd:
    """Workflow message_end event — enable_history and end node handling."""

    @staticmethod
    def test_enable_history_defaults_to_true():
        trace = Trace(handler_type="Workflow")
        WorkflowEventsProcessor.process_event(
            {
                "event": "message_end",
                "data": {
                    "answer": "final answer",
                    "node_type": "LLMChain",
                    "node_id": "n1",
                },
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.metadata is not None
        assert trace.metadata["enable_history"] is True

    @staticmethod
    def test_enable_history_false():
        trace = Trace(handler_type="Workflow")
        WorkflowEventsProcessor.process_event(
            {
                "event": "message_end",
                "data": {
                    "answer": "final",
                    "node_type": "LLMChain",
                    "node_id": "n1",
                    "enable_history": False,
                },
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.metadata["enable_history"] is False

    @staticmethod
    def test_end_node_captures_output():
        trace = Trace(handler_type="Workflow")
        WorkflowEventsProcessor.process_event(
            {
                "event": "message_end",
                "data": {
                    "answer": "end output",
                    "node_type": "End",
                    "node_id": "end-1",
                },
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.outputs is not None
        assert trace.outputs["responseContent"] == "end output"

    @staticmethod
    def test_end_node_uses_origin_answer():
        trace = Trace(handler_type="Workflow")
        WorkflowEventsProcessor.process_event(
            {
                "event": "message_end",
                "data": {
                    "answer": "rendered",
                    "origin_answer": "raw output",
                    "node_type": "End",
                    "node_id": "end-1",
                },
                "createdTime": 2000,
            },
            trace,
        )
        assert trace.outputs["responseContent"] == "raw output"

    @staticmethod
    def test_returns_message_end_event():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "message_end",
                "data": {
                    "answer": "summary",
                    "node_type": "LLMChain",
                    "node_id": "n1",
                },
                "createdTime": 2000,
            },
            trace,
        )
        assert result.event == "message"
        assert result.data["is_finished"] is True


class TestProcessError:
    """Workflow error event."""

    @staticmethod
    def test_sets_error_state():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "error",
                "data": {
                    "code": 103104,
                    "message": "model call failed",
                    "node_type": "LLMChain",
                    "node_id": "n1",
                },
                "createdTime": 3000,
            },
            trace,
        )
        assert trace.task_end is True
        assert trace.error_code == 103104
        assert trace.error_message == "model call failed"

    @staticmethod
    def test_returns_error_and_workflow_end():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "error",
                "data": {
                    "code": 103104,
                    "message": "failed",
                    "node_type": "LLMChain",
                },
                "createdTime": 3000,
            },
            trace,
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["event"] == "error"
        assert result[1]["event"] == "workflow_finished"


class TestProcessWorkflowEnd:
    """Workflow end event."""

    @staticmethod
    def test_sets_end_time_and_dialogue_end():
        trace = Trace(handler_type="Workflow")
        trace.start_time = 1784279771000
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "workflow_end",
                "data": {"answer": "done"},
                "createdTime": 1784279775000,
            },
            trace,
        )
        assert trace.end_time == 1784279775000
        assert trace.dialogue_end is True
        assert result.event == "workflow_finished"


class TestProcessDone:
    """Workflow done event."""

    @staticmethod
    def test_returns_end_event():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {"event": "done", "createdTime": 6000}, trace
        )
        assert result.event == "end"
        assert result.created_time == 6000


class TestProcessException:
    """Workflow exception event."""

    @staticmethod
    def test_sets_task_end():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {
                "event": "exception",
                "data": {"jiuwen_exception_node_id": "n1", "detail": "error detail"},
                "createdTime": 4000,
            },
            trace,
        )
        assert trace.task_end is True
        assert result.event == "exception"
        assert "jiuwen_exception_node_id" not in result.data


class TestUnknownEvent:
    """Unknown events fall through to default handler."""

    @staticmethod
    def test_unknown_event_passthrough():
        trace = Trace(handler_type="Workflow")
        result = WorkflowEventsProcessor.process_event(
            {"event": "custom_event", "data": {"key": "val"}, "createdTime": 1000},
            trace,
        )
        assert result == {"event": "custom_event", "data": {"key": "val"}, "createdTime": 1000}
