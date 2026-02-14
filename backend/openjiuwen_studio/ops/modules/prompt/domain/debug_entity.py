#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, model_validator

from openjiuwen_studio.ops.modules.prompt.domain.entities import BaseResponse


# ---------- 基础消息结构 ----------
class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    PLACEHOLDER = "placeholder"


class ContentType(str, Enum):
    TEXT = "text"
    IMAGE_URL = "image_url"


class ImageURL(BaseModel):
    uri: Optional[str] = None
    url: Optional[str] = None


class ContentPart(BaseModel):
    type: Optional[ContentType] = None
    text: Optional[str] = None
    image_url: Optional[ImageURL] = None


class ToolType(str, Enum):
    FUNCTION = "function"


class FunctionCall(BaseModel):
    name: Optional[str] = None
    arguments: Optional[str] = None


class ToolCall(BaseModel):
    index: Optional[str] = None
    id: Optional[str] = None
    type: Optional[ToolType] = None
    function_call: Optional[FunctionCall] = None


class Message(BaseModel):
    role: Optional[Role] = None
    reasoning_content: Optional[str] = None
    content: Optional[str] = None
    parts: Optional[List[ContentPart]] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


# ---------- 变量相关 ----------
class VariableType(str, Enum):
    STRING = "string"
    PLACEHOLDER = "placeholder"


class VariableDef(BaseModel):
    key: Optional[str] = None
    desc: Optional[str] = None
    type: Optional[VariableType] = None


class VariableVal(BaseModel):
    key: Optional[str] = None
    value: Any = None
    desc: Optional[str] = None
    type: Optional[VariableType] = None
    placeholder_messages: Optional[List[Message]] = None


class MockTool(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    mock_response: Optional[str] = None


# ---------- Token使用统计 ----------
class TokenUsage(BaseModel):
    input_tokens: Optional[str] = None
    output_tokens: Optional[str] = None


# ---------- 调试工具调用 ----------
class DebugToolCall(BaseModel):
    tool_call: Optional[ToolCall] = None
    mock_response: Optional[str] = None
    debug_trace_key: Optional[str] = None


# ---------- DebugCore ----------
class DebugMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: Optional[Role] = None
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    parts: Optional[List[ContentPart]] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[DebugToolCall]] = None
    debug_id: Optional[str] = None
    input_tokens: Optional[str] = None
    output_tokens: Optional[str] = None
    cost_ms: Optional[str] = None
    msg_time: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class DebugCore(BaseModel):
    mock_contexts: Optional[List[DebugMessage]]
    mock_variables: Optional[List[VariableVal]]
    mock_tools: Optional[List[MockTool]]


# ---------- Compare ----------
class CompareGroup(BaseModel):
    prompt_detail: Optional[Dict[str, Any]]
    debug_core: Optional[DebugCore]


class CompareConfig(BaseModel):
    groups: Optional[List[CompareGroup]] = []


# ---------- DebugContext ----------
class DebugContext(BaseModel):
    debug_core: Optional[DebugCore]
    debug_config: Optional[Dict[str, Any]]
    compare_config: Optional[CompareConfig] = Field(default_factory=CompareConfig)


class DebugContextResponse(BaseResponse):
    debug_context: Optional[DebugContext]


# ---------- DebugConfig ----------
class DebugConfig(BaseModel):
    single_step_debug: Optional[bool]


# ---------- DebugLog ----------
class DebugLog(BaseModel):
    id: Optional[str]
    prompt_id: Optional[str]
    workspace_id: Optional[str]
    prompt_key: Optional[str]
    version: Optional[str]
    input_tokens: Optional[str]
    output_tokens: Optional[str]
    cost_ms: Optional[str]
    status_code: Optional[int]
    debugged_by: Optional[str]
    debug_id: Optional[str]
    debug_step: Optional[int]
    started_at: Optional[str]
    ended_at: Optional[str]


# ---------- 请求/响应 ----------
class SaveDebugContextRequest(BaseModel):
    prompt_id: str = None
    workspace_id: Optional[str] = None
    debug_context: DebugContext


class SaveDebugContextResponse(BaseModel):
    saved: bool = True


class GetDebugContextRequest(BaseModel):
    prompt_id: str
    workspace_id: Optional[str] = None


class GetDebugContextResponse(BaseModel):
    debug_context: Optional[DebugContext]


class ListDebugHistoryRequest(BaseModel):
    prompt_id: str
    workspace_id: Optional[str] = None
    days_limit: Optional[int] = None
    page_size: Optional[int] = 20
    page_token: Optional[str] = None


class ListDebugHistoryResponse(BaseModel):
    debug_history: List[DebugLog] = Field(default_factory=list)
    has_more: bool = False
    next_page_token: Optional[str] = None


# ---------- SSE 流 ----------
class DebugStreamingRequest(BaseModel):
    prompt: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None
    variable_vals: Optional[List[Dict[str, Any]]] = None
    mock_tools: Optional[List[Dict[str, Any]]] = None
    single_step_debug: Optional[bool] = None
    debug_trace_key: Optional[str] = None
    workspace_id: Optional[int] = None

    @model_validator(mode="after")
    def check_draft_present(self) -> "DebugStreamingRequest":
        """ 校验 必要字段 是否存在 """
        if self.prompt is None:
            raise ValueError("prompt is required")
        if self.prompt.get("prompt_draft") is None:
            raise ValueError("prompt_draft is required")
        return self


class DebugStreamingResponse(BaseModel):
    delta: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    debug_id: Optional[str] = None
    debug_trace_key: Optional[str] = None
