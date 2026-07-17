# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Field data processor — 事件字段转换核心逻辑."""

import json
import time
from typing import Dict, Any, List

from jiuwen.serve.controllers.execution.enum import ConversationEvent
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.event_handler.base.models import (
    ErrorEventDataField,
    EventField,
)
from agent_runtime.event_handler.base.trace import Trace, NodeMessage, HistoryMessage
from agent_runtime.event_handler.base.mappers import ErrorContextBuilder


class FieldDataProcessor:
    """Field data processor for event transformation."""

    @staticmethod
    def process_field_data(data_dict: dict, field_keys: list) -> dict:
        if not isinstance(data_dict, dict) or not isinstance(field_keys, list):
            return {}
        result = {}
        for key, value in data_dict.items():
            if key in field_keys and isinstance(value, dict):
                result.update(value)
            elif value is not None:
                result[key] = value
        return result

    @staticmethod
    def process_node_message(node_type: str, full_data: Dict[str, Any], trace: Trace):
        data = full_data.get("data", {})
        node_message = NodeMessage(
            node_id=data.get("node_id"),
            node_name=data.get("node_name"),
            node_type=node_type,
            content=data.get("answer"),
            origin=data.get("origin_answer"),
            role="assistant",
        )
        if trace.messages is None:
            trace.messages = []
        trace.messages.append(node_message.to_dict())

    @staticmethod
    def process_history_message(node_type: str, full_data: Dict[str, Any], trace: Trace):
        data = full_data.get("data", {})
        event = full_data.get("event")
        messages = trace.conversation_info.get("messages", [])

        if event == ConversationEvent.MESSAGE_END.value:
            FieldDataProcessor.handle_message_end(node_type, data, messages, trace)
        else:
            FieldDataProcessor.handle_other_message(data, messages, trace)

    @staticmethod
    def handle_message_end(node_type: str, data: Dict[str, Any], messages: List[Dict[str, Any]], trace: Trace):
        enable_history = data.get("enable_history", True)
        if not enable_history:
            return
        content = data.get("origin_answer") or data.get("answer")
        his_message = HistoryMessage(
            node_id=data.get("node_id"),
            node_name=data.get("node_name"),
            node_type=node_type,
            content=content,
            role="assistant",
        )
        messages.append(his_message.to_dict())
        trace.conversation_info.update({"messages": messages})

    @staticmethod
    def handle_other_message(data: Dict[str, Any], messages: List[Dict[str, Any]], trace: Trace):
        answer_messages = data.get("answer", [])
        if not answer_messages:
            return
        if isinstance(answer_messages, str):
            try:
                answer_messages = json.loads(answer_messages)
            except (json.JSONDecodeError, TypeError) as e:
                workflow_logger.warning(f"Failed to parse intermediate message answer: {e}")
                return
        if isinstance(answer_messages, dict):
            FieldDataProcessor.handle_summary_response(answer_messages, messages, trace)
            return
        if isinstance(answer_messages, list):
            messages = []
            for msg in answer_messages:
                if isinstance(msg, dict):
                    messages.append({k: v for k, v in msg.items() if v is not None})
            trace.conversation_info.update({"messages": messages})

    @staticmethod
    def handle_summary_response(answer_messages: dict, messages: List[Dict[str, Any]], trace: Trace):
        last_msg = None
        if messages:
            last_msg = messages[-1]
        if not (last_msg and last_msg.get("role") == answer_messages.get("role", "")
                and answer_messages.get("content", "")):
            messages.append(answer_messages)
        trace.conversation_info.update({"messages": messages})

    @staticmethod
    def generate_error_event_field(trace: Trace):
        code = trace.error_code
        error_message = trace.error_message
        error_code, error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder.get_language_context(trace.language, code)
        )
        error_data_field = ErrorEventDataField(
            code=code,
            message=error_message,
            error_msg=error_msg,
            error_reason=error_reason,
            error_suggestion=error_suggestion,
            error_code=error_code,
        )
        create_time = trace.end_time
        if create_time is None:
            create_time = int(time.time() * 1000)
        return EventField(
            event=ConversationEvent.ERROR.value,
            data=error_data_field.model_dump(exclude_none=True, by_alias=True),
            createdTime=create_time,
        )

    @staticmethod
    def generate_memory_history_messages(trace: Trace):
        """Convert trace conversation_info messages to persistence format."""
        messages = []
        for msg in trace.conversation_info.get("messages", []):
            role = "user" if msg.get("role", "") == "user" else "assistant"
            messages.append({"role": role, "content": json.dumps(msg, ensure_ascii=False)})
        return messages
