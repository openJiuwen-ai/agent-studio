# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Base event processor"""

from typing import Dict, Any
from abc import ABC, abstractmethod

from jiuwen.serve.controllers.execution.enum import ConversationEvent
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.event_handler.base.enums import EventMapping, ToolType
from agent_runtime.event_handler.base.mappers import (
    NodeStatusMapper,
    LatencyMapper,
    ErrorContextBuilder,
    TimeConverter,
)
from agent_runtime.event_handler.base.models import (
    WorkflowMessageDataField,
    WorkflowNodeMessageDataField,
    EventField,
    PluginEventField,
    ErrorEventDataField,
)
from agent_runtime.event_handler.base.trace import Trace
from agent_runtime.event_handler.base.field_processor import FieldDataProcessor
from agent_runtime.event_handler.base.constants import (
    NODE_TYPE_KEY,
    node_type_mapping,
    FIELD_VALUES,
    DEBUG_NODE_KEY,
    EVENT_THROUGH,
    CODE,
)


class BaseEventsProcessor(ABC):
    """Base event processor with handler dispatch."""

    _initialized = False
    _handler_methods = {}

    @classmethod
    def _ensure_initialized(cls):
        if not cls._initialized:
            cls._initialize_handlers()

    @classmethod
    def _initialize_handlers(cls):
        if cls._initialized:
            return
        cls._handler_methods = {
            ConversationEvent.START.value: cls.process_start_event,
            ConversationEvent.MESSAGE_END.value: cls.process_message_end_event,
            ConversationEvent.FUNCTION_CALL.value: cls.process_function_call_event,
            ConversationEvent.API_EXEC_DATA.value: cls.process_api_exec_data_event,
            ConversationEvent.STATISTIC_DATA.value: cls.process_statistic_data_event,
            ConversationEvent.SUMMARY_RESPONSE.value: cls.process_summary_response_event,
            ConversationEvent.ERROR.value: cls.process_error_event,
            ConversationEvent.DONE.value: cls.process_done_event,
            ConversationEvent.WORKFLOW_NODE_MESSAGE.value: cls.process_workflow_node_message,
            ConversationEvent.INTERMEDIATE_MESSAGE.value: cls.process_intermediate_message_event,
            EVENT_THROUGH: cls.process_event_through,
        }
        cls._initialized = True

    @abstractmethod
    def process_event(self, full_data: Dict[str, Any], trace: Trace) -> Any:
        pass

    @classmethod
    def process_default_event(cls, full_data: Dict[str, Any], trace: Trace) -> Dict[str, Any]:
        return full_data

    @classmethod
    def process_start_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        start_time = full_data.get("createdTime")
        trace.start_time = start_time
        return full_data

    @classmethod
    def process_message_end_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        data = full_data.get("data", {})
        node_type = data.get(NODE_TYPE_KEY, "unknown")
        node_type = node_type_mapping.get(node_type, node_type)
        message_data = WorkflowMessageDataField(
            summary=data.get("answer"),
            origin=data.get("origin_answer"),
            node_id=data.get("node_id"),
            node_type=node_type,
            node_name=data.get("node_name"),
            is_finished=True,
            workflow_id=data.get("workflow_id"),
            workflow_name=data.get("workflow_name"),
        )
        FieldDataProcessor.process_node_message(node_type=node_type, full_data=full_data, trace=trace)
        return EventField(
            event=ConversationEvent.MESSAGE.value,
            data=message_data.model_dump(exclude_none=True, by_alias=True),
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_error_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        trace.task_end = True
        trace.end_time = full_data.get("createdTime")
        data = full_data.get("data", {})
        code = data.get("code", 999999)
        error_code, error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder.get_language_context(trace.language, code)
        )
        error_data_field = ErrorEventDataField(
            code=code,
            message=data.get("message", "unknown error"),
            error_msg=error_msg,
            error_reason=error_reason,
            error_suggestion=error_suggestion,
            error_code=error_code,
        )
        error_field = EventField(
            event=ConversationEvent.ERROR.value,
            data=error_data_field.model_dump(exclude_none=True, by_alias=True),
            createdTime=full_data.get("createdTime"),
        )
        event_list = [error_field.model_dump(exclude_none=True, by_alias=True)]
        # Agent needs statistic event
        if trace.handler_type in ("ReAct", "PlanExecute"):
            data[LatencyMapper.ANSWER_KEY] = {LatencyMapper.OVERALL_LATENCY: trace.overall_time()}
            static = cls.process_statistic_data_event(full_data, trace)
            event_list.append(static.model_dump(exclude_none=True, by_alias=True))
        trace.error_code = data.get("code", CODE)
        trace.error_message = data.get("message", "unknown error")
        workflow_logger.error(
            f"receive error event, error_code is {trace.error_code}, error_message is {trace.error_message}"
        )
        return event_list

    @classmethod
    def process_function_call_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        data = full_data.get("data", {})
        latency = LatencyMapper.get_function_call_latency(data)
        answer = data.get("answer", {})
        plugin_type = ToolType.PLUGIN.value
        if answer.get("is_mcp"):
            plugin_type = ToolType.MCP.value
        if answer.get("is_workflow"):
            plugin_type = ToolType.WORKFLOW.value
        plugin = answer.get("function_call")
        return PluginEventField(
            event=EventMapping.FUNCTION_CALL.value,
            type=plugin_type,
            latency=latency.to_dict(),
            plugin=plugin,
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_api_exec_data_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        data = full_data.get("data", {})
        content = data.get("answer", {}).get("content")
        role = data.get("answer", {}).get("role")
        latency = LatencyMapper.get_function_call_latency(data)
        return PluginEventField(
            event=EventMapping.API_EXEC_DATA.value,
            content=content,
            role=role,
            latency=latency.to_dict(),
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_statistic_data_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        data = full_data.get("data", {})
        latency = LatencyMapper.get_statistic_latency(data)
        return PluginEventField(
            event=ConversationEvent.STATISTIC_DATA.value,
            latency=latency.to_dict(),
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_summary_response_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        data = full_data.get("data", {})
        content = data.get("answer", {}).get("content")
        role = data.get("answer", {}).get("role")
        summary_response_field = EventField(
            event=ConversationEvent.SUMMARY_RESPONSE.value,
            content=content,
            role=role,
            createdTime=full_data.get("createdTime"),
            executionId=full_data.get("executionId"),
        )
        FieldDataProcessor.process_history_message(node_type="", full_data=full_data, trace=trace)
        return summary_response_field

    @classmethod
    def process_done_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        return EventField(
            event=ConversationEvent.DONE.value,
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_workflow_node_message(cls, full_data: Dict[str, Any], trace: Trace = None) -> Any:
        data = full_data.get("data", {})
        node_status, status = NodeStatusMapper.resolve_node_status(data.get("status", ""))
        inputs = FieldDataProcessor.process_field_data(data.get("inputs", {}), FIELD_VALUES)
        outputs = FieldDataProcessor.process_field_data(data.get("outputs", {}), FIELD_VALUES)
        start_time = TimeConverter.datetime_to_timestamp_ms(data.get("startTime"))
        end_time = TimeConverter.datetime_to_timestamp_ms(data.get("endTime"))
        node_type = data.get(DEBUG_NODE_KEY, "unknown")
        node_type = node_type_mapping.get(node_type, node_type)
        node_data = WorkflowNodeMessageDataField(
            agent_id=data.get("agentId"),
            node_id=data.get("componentId"),
            parent_node_id=data.get("parentNodeId"),
            node_status=node_status,
            parent_workflow_id=data.get("agentParentInvokeId"),
            status=status,
            node_name=data.get("componentName"),
            node_type=node_type,
            inputs=inputs,
            outputs=outputs,
            start_time=start_time,
            end_time=end_time,
            execution_id=data.get("traceId"),
        )
        invoke_data = data.get("onInvokeData")
        if invoke_data and isinstance(invoke_data, list):
            messages = []
            for dt in invoke_data:
                for key, value in dt.items():
                    if key in ["user", "assistant", "system"]:
                        messages.append({"role": key, "content": value or ""})
                    else:
                        messages.append({key: value or ""})
            node_data.messages = messages
        if data.get("metaData"):
            node_data.metadata = data.get("metaData")
        if trace and trace.is_debug:
            if trace.node_info is None:
                trace.node_info = []
            trace.node_info.append(node_data.model_dump(exclude_none=True, by_alias=True))
        return [
            EventField(
                event=node_status,
                data=node_data.model_dump(exclude_none=True, by_alias=True),
                createdTime=full_data.get("createdTime"),
            ).model_dump(exclude_none=True, by_alias=True),
            cls.process_default_event(full_data, trace),
        ]

    @classmethod
    def process_intermediate_message_event(cls, full_data: Dict[str, Any], trace: Trace = None):
        FieldDataProcessor.process_history_message(node_type="", full_data=full_data, trace=trace)
        return None

    @classmethod
    def process_event_through(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        if full_data.get("event") == ConversationEvent.WORKFLOW_BLOCKED.value:
            trace.block = True
        data = full_data.get("data", {})
        return EventField(
            event=full_data.get("event"),
            conversation_id=trace.conversation_id,
            data=data,
            createdTime=full_data.get("createdTime"),
        )
