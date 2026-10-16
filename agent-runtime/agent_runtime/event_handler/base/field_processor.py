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
        if error_message and error_message != error_msg:
            # NOTE: 不做 html.escape(与 Java 错误路径及 llm_chain 的既有约定一致)。
            # 前端纯文本插值({{ }})会原样显示实体(&#x27;/&amp;/&lt;),转义反而破坏展示;
            # XSS 防护由前端渲染上下文承担:插值自动编码,innerHTML 路径经 Angular DomSanitizer。
            error_msg = f"{error_msg}：{error_message}"
        error_data_field = ErrorEventDataField(
            code=code,
            message=error_message if error_message else "",
            error_msg=error_msg,
            error_reason=error_reason,
            error_suggestion=error_suggestion,
            error_code=error_code,
            workflow_id=trace.workflow_id,
            workflow_name=trace.workflow_name,
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
        """Convert trace conversation_info messages to persistence format.

        - content 只取消息正文，不再把整条消息 dict 序列化成 JSON 串。
        - agent_id: **保留** conversation_info["messages"] 里已有的 agent_id（来自
          controller 的 intermediate_message 流，是正确的 member agent_id）。
          只有没有 agent_id 的消息（trace.query 的 user、handle_message_end 的 assistant）
          才用 trace.instance_id 兜底。这样单层/双层 controller 都能正确按 member
          agent_id 过滤历史——旧 Java 路径靠 processOnEvent 原样存流里的消息
          （带 member agent_id）实现同样的效果。
        - 本轮 user query 由 trace.query 提供：conversation_info 中**已存在**相同
          query 的 user 消息（Controller 场景，engine 全量历史尾部即本轮 query）时
          保持原序不前置——旧实现"前置+去重"会把 query 从尾部搬到头部，逐轮累积
          导致持久化历史 user 倒序、意图流 messages 参数乱序；**不存在**（单
          agent/workflow 场景，conversation_info 只含本轮 assistant 消息）时前置
          写入，保证历史带上 user 一轮。
        """
        fallback_agent_id = getattr(trace, "instance_id", "") or ""

        def _msg(role: str, content: str, existing_agent_id=None, enable_history=None) -> dict:
            m = {"role": role, "content": content}
            aid = existing_agent_id if existing_agent_id else fallback_agent_id
            if aid:
                m["agent_id"] = aid
            # enable_history=False必须随消息落库，否则下一轮加载时
            # 被ConversationHistoryMessage默认补True，"本轮不入历史"语义失效
            if enable_history is False:
                m["enable_history"] = False
            return m

        def _norm_content(raw) -> str:
            if raw is None:
                return ""
            if isinstance(raw, str):
                return raw
            # 对 dict/list 使用标准 JSON 格式，其他类型用 str()
            if isinstance(raw, (dict, list)):
                return json.dumps(raw, ensure_ascii=False)
            return str(raw)

        raw_messages = trace.conversation_info.get("messages", [])
        query = getattr(trace, "query", "") or ""

        query_in_messages = bool(query) and any(
            isinstance(msg, dict)
            and msg.get("role") == "user"
            and _norm_content(msg.get("content")) == query
            for msg in raw_messages
        )

        messages = []
        if query and not query_in_messages:
            # 补写本轮query时带上请求级enable_history（trace透传），保持标志位
            messages.append(
                _msg("user", query, None, getattr(trace, "enable_history", None))
            )

        for msg in raw_messages:
            if not isinstance(msg, dict):
                continue
            role = "user" if msg.get("role", "") == "user" else "assistant"
            content = _norm_content(msg.get("content"))
            messages.append(_msg(role, content, msg.get("agent_id"), msg.get("enable_history")))
        return messages
