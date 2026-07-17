# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Agent ReAct && PlanExecute event processor — 处理业务逻辑"""

import traceback
from typing import Dict, Any

from jiuwen.serve.controllers.execution.enum import ConversationEvent, PlanModeType
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.event_handler.base.models import EventField
from agent_runtime.event_handler.base.trace import Trace, ensure_ms
from agent_runtime.event_handler.base.constants import EVENT_THROUGH, CODE
from agent_runtime.event_handler.events.base_events import BaseEventsProcessor

# Agent blocked events — 不转发给客户端
_AGENT_BLOCKED_EVENTS = {"done"}

# Agent through events — 直接透传
_AGENT_THROUGH_EVENTS = {
    "agent_interrupted", "scene_match", "plan_start", "plan_end", "step_start",
    "step_end", "task_complete", "task_start", "task_end", "workflow_blocked",
    "workflow_end", "workflow_resume", "workflow_start",
}


class AgentEventsProcessor(BaseEventsProcessor):
    """Agent ReAct && PlanExecute event processor."""

    _initialized = False

    @classmethod
    def _initialize_handlers(cls):
        """初始化处理器映射 - 子类扩展基类处理方法"""
        if not super()._initialized:
            super()._initialize_handlers()

        cls._handler_methods.update({
            ConversationEvent.START.value: cls.process_start_event,
            ConversationEvent.MESSAGE.value: cls.process_message_event,
            ConversationEvent.SUMMARY_RESPONSE.value: cls.process_summary_response_event,
            ConversationEvent.AGENT_NODE_MSG.value: cls.process_agent_node_message,
        })

        cls._initialized = True

    @classmethod
    def process_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        """处理事件的主入口方法"""
        # 自动触发初始化，确保只初始化一次
        cls._ensure_initialized()

        event_type = full_data.get("event")
        if event_type in _AGENT_BLOCKED_EVENTS:
            return None

        try:
            handler_method = cls._handler_methods.get(event_type, super().process_default_event)
            # 无需特殊处理的事件
            if event_type in _AGENT_THROUGH_EVENTS:
                handler_method = cls._handler_methods.get(EVENT_THROUGH)
            # Agent传回未知事件
            if handler_method is None:
                workflow_logger.warning(
                    f"unknown jiuwen agent event, use event through method, event type is {event_type}"
                )
                handler_method = cls._handler_methods.get(EVENT_THROUGH)
            result = handler_method(full_data, trace)
            return result
        except Exception as e:
            workflow_logger.error(f"agent event process failed, event type is {event_type}")
            workflow_logger.error("".join(traceback.format_exception(e)))
            trace.error_code = CODE
            trace.error_message = f"agent event process failed, event type is {event_type}"
            raise

    @classmethod
    def process_start_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        """start事件"""
        trace.start_time = ensure_ms(full_data.get("createdTime"))
        return EventField(
            event=ConversationEvent.START.value,
            createdTime=full_data.get("createdTime"),
        )

    @classmethod
    def process_message_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        """message事件"""
        data = full_data.get("data", {})
        content = data.get("answer") if data.get("answer") else None
        reasoning_content = data.get("think") if data.get("think") else None
        message_field = EventField(
            event=ConversationEvent.MESSAGE.value,
            content=content,
            reasoning_content=reasoning_content,
            createdTime=full_data.get("createdTime"),
        )

        return message_field

    @classmethod
    def process_summary_response_event(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        """summary_response事件"""
        summary_response_field = super().process_summary_response_event(full_data, trace)
        data = full_data.get("data", {})
        content = data.get("answer", {}).get("content")
        role = data.get("answer", {}).get("role")
        # agent 非流式记录
        if role and content:
            if trace.messages is None:
                trace.messages = []
            trace.messages.append({"role": role, "content": content})
        # summary_response 是 done 之前最后一个有效事件，在此设置非流式所需字段
        trace.end_time = ensure_ms(full_data.get("createdTime"))
        if trace.outputs is None:
            trace.outputs = {}
        if trace.events is None:
            trace.events = []
        return summary_response_field

    @classmethod
    def process_agent_node_message(cls, full_data: Dict[str, Any], trace: Trace) -> Any:
        """agent_node_message事件"""
        # LLM 调试事件写入 trace.events（用于非流式响应）
        if trace.is_debug:
            data = full_data.get("data", {})
            invoke_type = data.get("invokeType")
            if invoke_type == "llm":
                if trace.events is None:
                    trace.events = []
                meta_data = data.get("metaData", {})
                instance_attrs = meta_data.get("instance_attributes", {})
                event_info = {
                    "node_id": data.get("invokeId"),
                    "node_type": invoke_type,
                    "node_status": "succeeded",
                    "model_deployment_id": instance_attrs.get("model"),
                    "inputs": data.get("inputs", []),
                    "outputs": data.get("outputs", {}),
                    "start_time": data.get("startTime"),
                    "end_time": data.get("endTime"),
                    "meta_data": meta_data,
                }
                trace.events.append(event_info)

        # 原样透传给客户端
        return full_data
