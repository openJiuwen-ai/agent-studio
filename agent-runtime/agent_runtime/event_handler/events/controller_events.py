# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Controller event processor"""

import traceback
from typing import Dict, Any

from jiuwen.serve.controllers.execution.enum import ConversationEvent
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.event_handler.base.models import WorkflowMessageDataField, EventField
from agent_runtime.event_handler.base.trace import Trace
from agent_runtime.event_handler.base.constants import (
    node_type_mapping,
    NODE_TYPE_KEY,
    EVENT_THROUGH,
    CODE,
)
from agent_runtime.event_handler.events.base_events import BaseEventsProcessor

# Controller blocked events — 不转发给客户端
_CONTROLLER_BLOCKED_EVENTS = {"start", "done"}

# Controller through events — 透传给客户端
_CONTROLLER_THROUGH_EVENTS = {
    "workflow_blocked", "workflow_resume", "workflow_start", "workflow_end",
    "task_terminated", "scene_match", "plan_start", "plan_end", "step_start",
    "step_end", "task_complete",
}


class ControllerEventsProcessor(BaseEventsProcessor):
    """Controller event processor."""

    _initialized = False

    @classmethod
    def _initialize_handlers(cls):
        if not super()._initialized:
            super()._initialize_handlers()
        cls._handler_methods = {
            **cls._handler_methods,
            ConversationEvent.MESSAGE.value: cls.process_message_event,
            ConversationEvent.TASK_START.value: cls.process_task_start_event,
            ConversationEvent.WORKFLOW_NODE_MESSAGE.value: cls.process_workflow_node_message,
            ConversationEvent.AGENT_INTERRUPTED.value: cls.process_agent_interrupted_event,
            ConversationEvent.TASK_END.value: cls.process_task_end_event,
        }
        cls._initialized = True

    @classmethod
    def process_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        cls._ensure_initialized()
        event_type = full_data.get("event")
        if event_type in _CONTROLLER_BLOCKED_EVENTS:
            return None
        try:
            handler_method = cls._handler_methods.get(event_type, cls.process_default_event)
            if event_type in _CONTROLLER_THROUGH_EVENTS:
                handler_method = cls._handler_methods.get(EVENT_THROUGH)
            if handler_method is None:
                workflow_logger.warning(
                    f"unknown jiuwen controller event, use event through method, event type is {event_type}"
                )
                handler_method = cls._handler_methods.get(EVENT_THROUGH)
            result = handler_method(full_data, trace)
            # Skip pre_event tracking for debug events
            if event_type not in (
                ConversationEvent.AGENT_NODE_MSG.value,
                ConversationEvent.WORKFLOW_NODE_MESSAGE.value,
            ):
                trace.pre_event = event_type
            return result
        except Exception as e:
            workflow_logger.error(f"controller event process failed, event type is {event_type}")
            workflow_logger.error("".join(traceback.format_exception(e)))
            trace.error_code = CODE
            trace.error_message = f"controller event process failed, event type is {event_type}"
            raise

    @classmethod
    def process_message_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
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
        )
        return EventField(
            event=ConversationEvent.MESSAGE.value,
            data=message_data.model_dump(exclude_none=True, by_alias=True),
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_workflow_node_message(cls, full_data: Dict[str, Any], trace: Trace = None) -> Any:
        super().process_workflow_node_message(full_data, trace)
        return cls.process_default_event(full_data, trace)

    @classmethod
    def process_task_start_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        execution_id = full_data.get("executionId", "")
        trace.execution_id = execution_id
        data = {"executionId": execution_id}
        return EventField(
            event=ConversationEvent.TASK_START.value,
            conversation_id=trace.conversation_id,
            data=data,
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_agent_interrupted_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        trace.block = True
        return None

    @classmethod
    def process_task_end_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        data = {}
        if trace.pre_event != ConversationEvent.TASK_START.value:
            execution_id = trace.execution_id if trace.execution_id else full_data.get("executionId", "")
            if not execution_id:
                execution_id = "executionId"
            data["executionId"] = execution_id
        return EventField(
            event=ConversationEvent.TASK_END.value,
            conversation_id=trace.conversation_id,
            data=data,
            createdTime=full_data.get("createdTime"),
        )
