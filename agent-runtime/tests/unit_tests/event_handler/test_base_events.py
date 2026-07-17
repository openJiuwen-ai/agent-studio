# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for base_events.py — BaseEventsProcessor."""

from agent_runtime.event_handler.events.base_events import BaseEventsProcessor
from agent_runtime.event_handler.base.trace import Trace


class TestProcessStartEvent:
    """process_start_event — set trace.start_time."""

    @staticmethod
    def test_sets_start_time():
        trace = Trace()
        result = BaseEventsProcessor.process_start_event({"createdTime": 1784279775000}, trace)
        assert trace.start_time == 1784279775000
        assert result == {"createdTime": 1784279775000}


class TestProcessErrorEvent:
    """process_error_event — error handling with optional statistic event."""

    @staticmethod
    def test_react_handler_adds_statistic():
        trace = Trace(handler_type="ReAct", start_time=1000, end_time=2000)
        full_data = {
            "event": "error",
            "data": {"code": 103104, "message": "fail"},
            "createdTime": 3000,
        }
        result = BaseEventsProcessor.process_error_event(full_data, trace)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["event"] == "error"
        assert result[1]["event"] == "statistic_data"
        assert trace.task_end is True
        assert trace.error_code == 103104
        assert trace.error_message == "fail"

    @staticmethod
    def test_planexecute_handler_adds_statistic():
        trace = Trace(handler_type="PlanExecute", start_time=1000, end_time=2000)
        full_data = {
            "event": "error",
            "data": {"code": 999999, "message": "internal"},
            "createdTime": 3000,
        }
        result = BaseEventsProcessor.process_error_event(full_data, trace)
        assert len(result) == 2

    @staticmethod
    def test_workflow_handler_no_statistic():
        trace = Trace(handler_type="Workflow")
        full_data = {
            "event": "error",
            "data": {"code": 103104, "message": "fail"},
            "createdTime": 3000,
        }
        result = BaseEventsProcessor.process_error_event(full_data, trace)
        assert len(result) == 1
        assert result[0]["event"] == "error"

    @staticmethod
    def test_default_code_when_missing():
        trace = Trace(handler_type="Workflow")
        full_data = {"event": "error", "data": {}, "createdTime": 3000}
        BaseEventsProcessor.process_error_event(full_data, trace)
        # trace.error_code defaults to CODE (121007) when code is missing
        assert trace.error_code == 121007


class TestProcessFunctionCallEvent:
    """process_function_call_event — plugin/mcp/workflow tool events."""

    @staticmethod
    def test_default_plugin_type():
        trace = Trace()
        full_data = {
            "event": "function_call",
            "data": {"answer": {"function_call": {"name": "tool1"}}},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_function_call_event(full_data, trace)
        assert result.type == "plugin"
        assert result.plugin == {"name": "tool1"}

    @staticmethod
    def test_mcp_type():
        trace = Trace()
        full_data = {
            "event": "function_call",
            "data": {"answer": {"is_mcp": True, "function_call": {}}},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_function_call_event(full_data, trace)
        assert result.type == "mcp"

    @staticmethod
    def test_workflow_type():
        trace = Trace()
        full_data = {
            "event": "function_call",
            "data": {"answer": {"is_workflow": True, "function_call": {}}},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_function_call_event(full_data, trace)
        assert result.type == "workflow"


class TestProcessApiExecDataEvent:
    """process_api_exec_data_event — plugin execution result."""

    @staticmethod
    def test_extracts_content_and_role():
        trace = Trace()
        full_data = {
            "event": "api_exec_data",
            "data": {"answer": {"content": {"key": "value"}, "role": "tool"}},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_api_exec_data_event(full_data, trace)
        assert result.role == "tool"
        assert result.event == "plugin_end"
        assert result.content == {"key": "value"}


class TestProcessStatisticDataEvent:
    """process_statistic_data_event — latency statistics."""

    @staticmethod
    def test_extracts_latency():
        trace = Trace()
        full_data = {
            "event": "statistic_data",
            "data": {"answer": {"overall_latency": 1.5, "model_latency": 1.2}},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_statistic_data_event(full_data, trace)
        assert result.event == "statistic_data"
        assert result.latency.overall == 1.5
        assert result.latency.model == 1.2


class TestProcessDoneEvent:
    """process_done_event — return DONE event."""

    @staticmethod
    def test_returns_done_event():
        trace = Trace()
        result = BaseEventsProcessor.process_done_event({"createdTime": 6000}, trace)
        assert result.event == "done"
        assert result.created_time == 6000


class TestProcessWorkflowNodeMessage:
    """process_workflow_node_message — node status and debug tracking."""

    @staticmethod
    def test_start_status():
        trace = Trace(handler_type="Workflow", is_debug=True)
        full_data = {
            "event": "workflow_node_message",
            "data": {
                "status": "start",
                "componentId": "n1",
                "componentName": "Node 1",
                "componentType": "jiuwen.LLMComponent",
            },
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_workflow_node_message(full_data, trace)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["event"] == "node_started"
        assert trace.node_info is not None
        assert len(trace.node_info) == 1

    @staticmethod
    def test_error_status():
        trace = Trace(handler_type="Workflow")
        full_data = {
            "event": "workflow_node_message",
            "data": {"status": "error", "componentId": "n1"},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_workflow_node_message(full_data, trace)
        assert result[0]["event"] == "node_finished"

    @staticmethod
    def test_on_invoke_data_with_roles():
        trace = Trace(handler_type="Workflow", is_debug=True)
        full_data = {
            "event": "workflow_node_message",
            "data": {
                "status": "finish",
                "componentId": "n1",
                "onInvokeData": [
                    {"user": "hello"},
                    {"assistant": "world"},
                ],
            },
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_workflow_node_message(full_data, trace)
        node_data = result[0]["data"]
        assert "messages" in node_data
        assert len(node_data["messages"]) == 2
        assert node_data["messages"][0]["role"] == "user"
        assert node_data["messages"][1]["role"] == "assistant"

    @staticmethod
    def test_on_invoke_data_with_custom_keys():
        trace = Trace(handler_type="Workflow", is_debug=True)
        full_data = {
            "event": "workflow_node_message",
            "data": {
                "status": "finish",
                "componentId": "n1",
                "onInvokeData": [{"customKey": "value"}],
            },
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_workflow_node_message(full_data, trace)
        node_data = result[0]["data"]
        assert node_data["messages"][0] == {"customKey": "value"}

    @staticmethod
    def test_metadata_captured():
        trace = Trace(handler_type="Workflow", is_debug=True)
        full_data = {
            "event": "workflow_node_message",
            "data": {
                "status": "finish",
                "componentId": "n1",
                "metaData": {"key": "val"},
            },
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_workflow_node_message(full_data, trace)
        node_data = result[0]["data"]
        assert node_data["metadata"] == {"key": "val"}

    @staticmethod
    def test_non_debug_no_node_info():
        trace = Trace(handler_type="Workflow", is_debug=False)
        full_data = {
            "event": "workflow_node_message",
            "data": {"status": "finish", "componentId": "n1"},
            "createdTime": 1000,
        }
        BaseEventsProcessor.process_workflow_node_message(full_data, trace)
        assert trace.node_info is None


class TestProcessIntermediateMessageEvent:
    """process_intermediate_message_event — calls process_history_message."""

    @staticmethod
    def test_returns_none():
        trace = Trace()
        full_data = {
            "event": "intermediate_message",
            "data": {"answer": []},
        }
        result = BaseEventsProcessor.process_intermediate_message_event(full_data, trace)
        assert result is None


class TestProcessEventThrough:
    """process_event_through — passthrough with block flag."""

    @staticmethod
    def test_workflow_blocked_sets_block():
        trace = Trace(conversation_id="conv-1")
        full_data = {
            "event": "workflow_blocked",
            "data": {"key": "val"},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_event_through(full_data, trace)
        assert trace.block is True
        assert result.event == "workflow_blocked"
        assert result.conversation_id == "conv-1"

    @staticmethod
    def test_other_through_event_no_block():
        trace = Trace(conversation_id="conv-1")
        full_data = {
            "event": "workflow_resume",
            "data": {},
            "createdTime": 1000,
        }
        result = BaseEventsProcessor.process_event_through(full_data, trace)
        assert trace.block is False
        assert result.event == "workflow_resume"
