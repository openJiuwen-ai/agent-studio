# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Event handler models"""

from typing import Optional

from pydantic import BaseModel, Field


# SSE 输出模型

class EventField(BaseModel):
    """Final event returned to client (SSE response)."""
    event: Optional[str] = Field(default=None)
    conversation_id: Optional[str] = Field(default=None)
    data: Optional[dict] = Field(default=None)
    content: Optional[str] = Field(default=None)
    reasoning_content: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    created_time: Optional[int] = Field(alias="createdTime", default=None)
    execution_id: Optional[str] = Field(alias="executionId", default=None)
    index: Optional[int] = Field(default=None)


class WorkflowMessageDataField(BaseModel):
    """message event data (SSE response)."""
    text: Optional[str] = Field(default="")
    reasoning_content: Optional[str] = Field(default=None)
    index: Optional[int] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    origin: Optional[str] = Field(default=None)
    node_id: Optional[str] = Field(default=None)
    node_type: Optional[str] = Field(default=None)
    node_name: Optional[str] = Field(default=None)
    is_finished: Optional[bool] = Field(default=None)
    workflow_id: Optional[str] = Field(default=None)
    workflow_name: Optional[str] = Field(default=None)
    created_time: Optional[int] = Field(alias="createdTime", default=None)
    enable_history: Optional[bool] = Field(default=None)


class WorkflowEndDataField(BaseModel):
    """workflow_end event data (SSE response)."""
    status: Optional[dict] = Field(default=None)
    error_code: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    outputs: Optional[dict] = Field(default=None)
    metadata: Optional[dict] = Field(default=None)
    start_time: Optional[int] = Field(default=None)
    end_time: Optional[int] = Field(default=None)
    execution_id: Optional[str] = Field(default=None)


class ErrorEventDataField(BaseModel):
    """error event data (SSE response)."""
    node_id: Optional[str] = Field(default=None)
    node_type: Optional[str] = Field(default=None)
    node_name: Optional[str] = Field(default=None)
    code: Optional[int] = Field(default=None)
    message: Optional[str] = Field(default=None)
    workflow_id: Optional[str] = Field(default=None)
    workflow_name: Optional[str] = Field(default=None)
    error_msg: Optional[str] = Field(default=None)
    error_reason: Optional[str] = Field(default=None)
    error_suggestion: Optional[str] = Field(default=None)
    error_code: Optional[str] = Field(default=None)


class WorkflowNodeMessageDataField(BaseModel):
    """workflow_node_message event data (SSE response)."""
    agent_id: Optional[str] = Field(default=None)
    node_id: Optional[str] = Field(default=None)
    parent_node_id: Optional[str] = Field(default=None)
    node_status: Optional[str] = Field(default=None)
    parent_workflow_id: Optional[str] = Field(default="")
    status: Optional[dict] = Field(default=None)
    node_name: Optional[str] = Field(default=None)
    node_type: Optional[str] = Field(default=None)
    inputs: Optional[dict] = Field(default={})
    outputs: Optional[dict] = Field(default={})
    start_time: Optional[int] = Field(default=None)
    end_time: Optional[int] = Field(default=None)
    execution_id: Optional[str] = Field(default=None)
    messages: Optional[list] = Field(default=None)
    metadata: Optional[dict] = Field(default=None)


class PluginEventField(BaseModel):
    """function_call / plugin event (SSE response)."""
    event: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    content: Optional[dict] = Field(default=None)
    role: Optional[str] = Field(default=None)
    latency: Optional[dict] = Field(default=None)
    plugin: Optional[dict] = Field(default=None)
    created_time: Optional[int] = Field(alias="createdTime", default=None)


# 非流式响应

class NonStreamingResponse(BaseModel):
    """Non-streaming aggregated response."""
    conversation_id: Optional[str] = Field(default=None)
    error_code: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    outputs: Optional[dict] = Field(default=None)
    messages: Optional[list] = Field(default=None)
    metadata: Optional[dict] = Field(default=None)
    status: Optional[dict] = Field(default=None)
    start_time: Optional[int] = Field(default=None)
    end_time: Optional[int] = Field(default=None)
    events: Optional[list] = Field(default=None)
    node_info: Optional[list] = Field(default=None)
