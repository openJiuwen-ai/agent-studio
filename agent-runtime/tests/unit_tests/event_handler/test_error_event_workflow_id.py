# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for error event workflow_id / workflow_name propagation.

Covers fix b4566aeb: SSE error event was missing workflow_id field
in ReAct / PlanExecute / Controller modes (base class fallback path).
"""
from agent_runtime.event_handler.base.trace import Trace
from agent_runtime.event_handler.base.field_processor import FieldDataProcessor
from agent_runtime.event_handler.events.base_events import BaseEventsProcessor


class TestProcessErrorEventWorkflowId:
    """process_error_event should propagate workflow_id and workflow_name."""

    @staticmethod
    def test_error_event_contains_workflow_id():
        """error 事件中的 workflow_id 应透传到 ErrorEventDataField."""
        trace = Trace(handler_type="ReAct")
        full_data = {
            "event": "error",
            "createdTime": 1000,
            "data": {
                "code": 100001,
                "message": "test error",
                "workflow_id": "wf-123",
                "workflow_name": "测试工作流",
            },
        }
        result = BaseEventsProcessor.process_error_event(full_data, trace)

        assert result is not None
        event_list = result if isinstance(result, list) else [result]
        error_field = event_list[0]
        assert error_field["event"] == "error"
        assert error_field["data"]["workflow_id"] == "wf-123"
        assert error_field["data"]["workflow_name"] == "测试工作流"

    @staticmethod
    def test_error_event_workflow_id_recorded_in_trace():
        """error 事件处理后 trace 应记录 workflow_id 和 workflow_name."""
        trace = Trace(handler_type="PlanExecute")
        full_data = {
            "event": "error",
            "createdTime": 2000,
            "data": {
                "code": 200001,
                "message": "fail",
                "workflow_id": "wf-456",
                "workflow_name": "sub-flow",
            },
        }
        BaseEventsProcessor.process_error_event(full_data, trace)

        assert trace.workflow_id == "wf-456"
        assert trace.workflow_name == "sub-flow"

    @staticmethod
    def test_error_event_without_workflow_id():
        """没有 workflow_id 时应正常处理，不报错."""
        trace = Trace(handler_type="ReAct")
        full_data = {
            "event": "error",
            "createdTime": 3000,
            "data": {
                "code": 999999,
                "message": "unknown",
            },
        }
        result = BaseEventsProcessor.process_error_event(full_data, trace)

        assert result is not None
        event_list = result if isinstance(result, list) else [result]
        error_field = event_list[0]
        assert error_field["event"] == "error"
        # workflow_id / workflow_name 不在 exclude_none 后的输出中
        assert "workflow_id" not in error_field["data"]
        assert "workflow_name" not in error_field["data"]


class TestGenerateErrorEventFieldWorkflowId:
    """FieldDataProcessor.generate_error_event_field should read workflow_id from trace."""

    @staticmethod
    def test_generate_error_field_with_workflow_id():
        """兜底路径 generate_error_event_field 应从 trace 取 workflow_id."""
        trace = Trace(handler_type="Controller")
        trace.error_code = 100001
        trace.error_message = "controller error"
        trace.workflow_id = "wf-789"
        trace.workflow_name = "controller-flow"
        trace.end_time = 5000

        result = FieldDataProcessor.generate_error_event_field(trace)

        assert result.event == "error"
        assert result.data["workflow_id"] == "wf-789"
        assert result.data["workflow_name"] == "controller-flow"

    @staticmethod
    def test_generate_error_field_without_workflow_id():
        """trace 没有 workflow_id 时应正常生成 error field."""
        trace = Trace(handler_type="Controller")
        trace.error_code = 999999
        trace.error_message = "no workflow"
        trace.end_time = 6000

        result = FieldDataProcessor.generate_error_event_field(trace)

        assert result.event == "error"
        assert "workflow_id" not in result.data
        assert "workflow_name" not in result.data
