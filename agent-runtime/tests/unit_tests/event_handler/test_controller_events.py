# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for controller_events.py — ControllerEventsProcessor."""

from agent_runtime.event_handler.events.controller_events import ControllerEventsProcessor
from agent_runtime.event_handler.base.trace import Trace


class TestProcessEvent:
    """process_event — dispatch and pre_event tracking."""

    @staticmethod
    def test_blocked_events():
        """start and done events should be blocked (return None)."""
        trace = Trace(handler_type="Controller")

        result = ControllerEventsProcessor.process_event(
            {"event": "start", "createdTime": 1000}, trace
        )
        assert result is None

        result = ControllerEventsProcessor.process_event(
            {"event": "done", "createdTime": 2000}, trace
        )
        assert result is None

    @staticmethod
    def test_through_events():
        """Through events should be forwarded as-is."""
        trace = Trace(handler_type="Controller", conversation_id="conv-1")

        result = ControllerEventsProcessor.process_event(
            {"event": "workflow_start", "data": {"key": "val"}, "createdTime": 1000},
            trace,
        )
        assert result is not None
        assert result.event == "workflow_start"

    @staticmethod
    def test_pre_event_tracking():
        """pre_event should be set for non-debug events."""
        trace = Trace(handler_type="Controller")

        ControllerEventsProcessor.process_event(
            {"event": "message", "data": {"answer": "hi"}, "createdTime": 1000},
            trace,
        )
        assert trace.pre_event == "message"

    @staticmethod
    def test_pre_event_not_tracked_for_debug_events():
        """pre_event should NOT be set for agent_node_message and workflow_node_message."""
        trace = Trace(handler_type="Controller")

        ControllerEventsProcessor.process_event(
            {
                "event": "agent_node_message",
                "data": {"invokeType": "llm", "invokeId": "node-1"},
                "createdTime": 1000,
            },
            trace,
        )
        assert trace.pre_event != "agent_node_message"

    @staticmethod
    def test_exception_handling():
        """Exception during processing should set error_code and error_message."""
        trace = Trace(handler_type="Controller")

        # Force an exception by passing invalid data
        try:
            ControllerEventsProcessor.process_event(
                {"event": "message", "data": None, "createdTime": 1000},
                trace,
            )
        except Exception:
            assert trace.error_code is not None
            assert "controller event process failed" in trace.error_message


class TestProcessMessageEvent:
    """process_message_event — message with text and reasoning."""

    @staticmethod
    def test_extracts_text_and_reasoning():
        trace = Trace(handler_type="Controller")
        result = ControllerEventsProcessor.process_event(
            {
                "event": "message",
                "data": {
                    "answer": "hello",
                    "think": "reasoning content",
                    "node_type": "LLMChain",
                    "node_id": "n1",
                    "node_name": "LLM Node",
                },
                "index": 0,
                "createdTime": 1000,
            },
            trace,
        )
        assert result.event == "message"
        assert result.data["text"] == "hello"
        assert result.data["reasoning_content"] == "reasoning content"
        assert result.data["node_type"] == "LLM"

    @staticmethod
    def test_node_type_mapping():
        trace = Trace(handler_type="Controller")
        result = ControllerEventsProcessor.process_event(
            {
                "event": "message",
                "data": {"answer": "test", "node_type": "FlowQA"},
                "createdTime": 1000,
            },
            trace,
        )
        assert result.data["node_type"] == "QA"


class TestProcessTaskStartEvent:
    """process_task_start_event — set execution_id."""

    @staticmethod
    def test_sets_execution_id():
        trace = Trace(handler_type="Controller", conversation_id="conv-1")
        result = ControllerEventsProcessor.process_event(
            {"event": "task_start", "executionId": "exec-123", "createdTime": 1000},
            trace,
        )
        assert trace.execution_id == "exec-123"
        assert result.event == "task_start"
        assert result.data["executionId"] == "exec-123"
        assert result.conversation_id == "conv-1"


class TestProcessAgentInterruptedEvent:
    """process_agent_interrupted_event — set block flag."""

    @staticmethod
    def test_sets_block_flag():
        trace = Trace(handler_type="Controller")
        result = ControllerEventsProcessor.process_event(
            {"event": "agent_interrupted", "createdTime": 1000},
            trace,
        )
        assert trace.block is True
        assert result is None


class TestProcessTaskEndEvent:
    """process_task_end_event — conditional execution_id logic."""

    @staticmethod
    def test_no_execution_id_after_task_start():
        """When pre_event is task_start, execution_id should not be included."""
        trace = Trace(
            handler_type="Controller",
            conversation_id="conv-1",
            pre_event="task_start",
        )
        result = ControllerEventsProcessor.process_event(
            {"event": "task_end", "createdTime": 2000},
            trace,
        )
        assert result.event == "task_end"
        assert result.data == {}

    @staticmethod
    def test_execution_id_from_trace():
        """When pre_event is not task_start, use trace.execution_id."""
        trace = Trace(
            handler_type="Controller",
            conversation_id="conv-1",
            execution_id="exec-5",
            pre_event="message",
        )
        result = ControllerEventsProcessor.process_event(
            {"event": "task_end", "createdTime": 2000},
            trace,
        )
        assert result.data["executionId"] == "exec-5"

    @staticmethod
    def test_execution_id_from_data():
        """When trace.execution_id is None, use data.executionId."""
        trace = Trace(
            handler_type="Controller",
            conversation_id="conv-1",
            execution_id=None,
            pre_event="message",
        )
        result = ControllerEventsProcessor.process_event(
            {"event": "task_end", "executionId": "exec-99", "createdTime": 2000},
            trace,
        )
        assert result.data["executionId"] == "exec-99"

    @staticmethod
    def test_execution_id_fallback():
        """When no execution_id anywhere, use 'executionId' as fallback."""
        trace = Trace(
            handler_type="Controller",
            conversation_id="conv-1",
            execution_id=None,
            pre_event="message",
        )
        result = ControllerEventsProcessor.process_event(
            {"event": "task_end", "createdTime": 2000},
            trace,
        )
        assert result.data["executionId"] == "executionId"


class TestProcessWorkflowNodeMessage:
    """process_workflow_node_message — controller version."""

    @staticmethod
    def test_calls_super_and_returns_default():
        trace = Trace(handler_type="Controller")
        result = ControllerEventsProcessor.process_event(
            {
                "event": "workflow_node_message",
                "data": {
                    "status": "start",
                    "componentId": "n1",
                    "componentName": "Node 1",
                },
                "createdTime": 1000,
            },
            trace,
        )
        # Controller version returns default event (passthrough dict), not the base list result
        assert result is not None
        assert result["event"] == "workflow_node_message"
