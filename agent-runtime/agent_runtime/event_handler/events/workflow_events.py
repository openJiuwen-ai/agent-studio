# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Workflow event processor"""

import time
import traceback
from typing import Dict, Any, List

from jiuwen.serve.controllers.execution.enum import ConversationEvent
from jiuwen.orchestration.flow.enum import NodeType
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.event_handler.base.enums import EventStatus, EventMapping
from agent_runtime.event_handler.base.constants import (
    NODE_TYPE_KEY,
    node_type_mapping,
    CODE,
    INTERACTION_NODE,
    EXCEPTION_NO_KEY,
    RESPONSE_CONTENT,
    EVENT_THROUGH,
)
from agent_runtime.event_handler.base.models import (
    WorkflowMessageDataField,
    WorkflowEndDataField,
    EventField,
    ErrorEventDataField,
)
from agent_runtime.event_handler.base.trace import Trace, ensure_ms
from agent_runtime.event_handler.base.mappers import ErrorContextBuilder
from agent_runtime.event_handler.base.field_processor import FieldDataProcessor
from agent_runtime.event_handler.events.base_events import BaseEventsProcessor

# Workflow blocked events — 不转发给客户端
_WORKFLOW_BLOCKED_EVENTS = {"start", "intermediate_message"}


class WorkflowEventsProcessor(BaseEventsProcessor):
    """Workflow event processor."""

    _initialized = False

    @classmethod
    def _initialize_handlers(cls):
        if not super()._initialized:
            super()._initialize_handlers()
        cls._handler_methods = {
            **cls._handler_methods,
            ConversationEvent.WORKFLOW_START.value: cls.process_workflow_start,
            ConversationEvent.MESSAGE.value: cls.process_message,
            ConversationEvent.MESSAGE_END.value: cls.process_message_end,
            ConversationEvent.ERROR.value: cls.process_error_message,
            ConversationEvent.WORKFLOW_END.value: cls.process_workflow_end,
            ConversationEvent.DONE.value: cls.process_done,
            ConversationEvent.EXCEPTION.value: cls.process_exception,
        }
        cls._initialized = True

    @classmethod
    def process_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        cls._ensure_initialized()
        event_type = full_data.get("event")
        if event_type in _WORKFLOW_BLOCKED_EVENTS:
            return None
        try:
            handler_method = cls._handler_methods.get(event_type, cls.process_default)
            if handler_method is None:
                workflow_logger.warning(
                    f"unknown jiuwen workflow event, use event through method, event type is {event_type}"
                )
                handler_method = cls._handler_methods.get(EVENT_THROUGH)
            result = handler_method(full_data, trace)
            return result
        except Exception as e:
            workflow_logger.error(f"workflow event process failed, event type is {event_type}")
            workflow_logger.error("".join(traceback.format_exception(e)))
            trace.error_code = CODE
            trace.error_message = f"workflow event process failed, event type is {event_type}"
            raise

    @classmethod
    def process_default(cls, full_data: Dict[str, Any], trace: Trace) -> Dict[str, Any]:
        if full_data.get("event") == ConversationEvent.WORKFLOW_START.value:
            trace.start_time = ensure_ms(
                full_data.get("createdTime", int(time.time() * 1000))
            )
        return full_data

    @classmethod
    def process_workflow_start(cls, full_data: Dict[str, Any], trace: Trace = None) -> Any:
        data = {"start_time": ensure_ms(full_data.get("createdTime"))}
        return EventField(
            event=EventMapping.WORKFLOW_START.value,
            data=data,
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_message(cls, full_data: Dict[str, Any], trace: Trace = None) -> Any:
        data = full_data.get("data", {})
        node_type = data.get(NODE_TYPE_KEY, "unknown")
        node_type = node_type_mapping.get(node_type, node_type)
        message_data = WorkflowMessageDataField(
            text=data.get("answer"),
            reasoning_content=data.get("think"),
            index=full_data.get("index"),
            node_id=data.get("node_id"),
            node_type=node_type,
            node_name=data.get("node_name"),
            workflow_id=data.get("workflow_id"),
            workflow_name=data.get("workflow_name"),
            enable_history=data.get("enable_history"),
            createdTime=full_data.get("createdTime"),
        )
        return EventField(
            event=ConversationEvent.MESSAGE.value,
            data=message_data.model_dump(exclude_none=True, by_alias=True),
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_message_end(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
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
            enable_history=data.get("enable_history"),
            createdTime=full_data.get("createdTime"),
        )
        if trace.metadata is None:
            trace.metadata = {}
        trace.metadata["enable_history"] = data.get("enable_history", True)
        # End node: capture final output
        if node_type == node_type_mapping.get(NodeType.END.value):
            final_msg = data.get("answer") if data.get("origin_answer") is None else data.get("origin_answer")
            if trace.outputs is None:
                trace.outputs = {}
            trace.outputs[RESPONSE_CONTENT] = final_msg
        else:
            FieldDataProcessor.process_node_message(node_type=node_type, full_data=full_data, trace=trace)
        FieldDataProcessor.process_history_message(node_type=node_type, full_data=full_data, trace=trace)
        # Interaction node: set waiting status
        if data.get("node_type") in INTERACTION_NODE:
            trace.status = EventStatus.WAITING.value
        return EventField(
            event=EventMapping.MESSAGE_END.value,
            data=message_data.model_dump(exclude_none=True, by_alias=True),
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_error_message(cls, full_data: Dict[str, Any], trace: Trace) -> List[Dict[str, Any]]:
        trace.task_end = True
        data = full_data.get("data", {})
        node_type = data.get(NODE_TYPE_KEY, "unknown")
        node_type = node_type_mapping.get(node_type, node_type)
        code = data.get("code", 999999)
        error_code, error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder.get_language_context(trace.language, code)
        )
        error_data_field = ErrorEventDataField(
            node_id=data.get("node_id"),
            node_name=data.get("node_name"),
            node_type=node_type,
            code=code,
            message=data.get("message", "unknown error"),
            workflow_id=data.get("workflow_id"),
            workflow_name=data.get("workflow_name"),
            error_msg=error_msg,
            error_reason=error_reason,
            error_suggestion=error_suggestion,
            error_code=error_code,
        )
        event = EventField(
            event=ConversationEvent.ERROR.value,
            data=error_data_field.model_dump(exclude_none=True, by_alias=True),
            createdTime=full_data.get("createdTime"),
        )
        error_field = [event.model_dump(exclude_none=True, by_alias=True)]
        # Build workflow_finished event
        trace.status = EventStatus.ERROR.value
        trace.error_code = data.get("code", CODE)
        trace.error_message = data.get("message", "unknown error")
        error_field.append(
            cls.process_workflow_end(full_data, trace).model_dump(exclude_none=True, by_alias=True)
        )
        return error_field

    @classmethod
    def process_workflow_end(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        current_time = ensure_ms(
            full_data.get("createdTime", int(time.time() * 1000))
        )
        trace.dialogue_end = True
        trace.end_time = current_time
        workflow_end_data = WorkflowEndDataField(
            status=trace.status,
            error_code=trace.error_code,
            error_message=trace.error_message,
            outputs={RESPONSE_CONTENT: full_data.get("data", {}).get("answer")},
            metadata=trace.metadata,
            start_time=trace.start_time,
            end_time=current_time,
            execution_id=full_data.get("executionId"),
        )
        return EventField(
            event=EventMapping.WORKFLOW_END.value,
            data=workflow_end_data.model_dump(exclude_none=True, by_alias=True),
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_done(cls, full_data: Dict[str, Any], trace: Trace = None) -> Any:
        return EventField(
            event=EventMapping.DONE.value,
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_exception(cls, full_data: Dict[str, Any], trace: Trace = None) -> Any:
        trace.task_end = True
        data = full_data.get("data", {})
        data.pop(EXCEPTION_NO_KEY, None)
        return EventField(
            event=ConversationEvent.EXCEPTION.value,
            data=data,
            createdTime=full_data.get("createdTime"),
        )
