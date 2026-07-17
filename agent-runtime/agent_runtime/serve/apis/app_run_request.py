# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Pydantic schemas for app run endpoints"""

from dataclasses import dataclass
from typing import Optional, Union, List, Dict, Any

from jiuwen.serve.schemas.orchestration_mgr import ConversationHistoryMessage
from pydantic import BaseModel, Field

from agent_runtime.schemas.orchestration_mgr import PluginConfig


@dataclass
class WorkflowRunContext:
    """工作流试运行上下文 — 封装路径参数."""
    project_id: str
    workflow_id: str
    conversation_id: str
    version: Optional[str]


@dataclass
class AgentRunContext:
    """智能体试运行上下文 — 封装路径参数."""
    project_id: str
    agent_id: str
    conversation_id: str
    version: Optional[str]


@dataclass
class ExecutionContext:
    """执行上下文 — 封装 build_req_json 所需的运行时参数."""
    conversation_id: str
    ir_path: str
    conversation_history: list
    dialogue_count: int
    user_id: str


class WorkflowAppRunRequest(BaseModel):
    """工作流试运行请求"""

    inputs: dict = Field(default_factory=dict)
    memory_inputs: Optional[dict] = Field(alias="memory_inputs", default=None)
    globals: dict = Field(default_factory=dict)
    environment: dict = Field(default_factory=dict)
    messages: list[ConversationHistoryMessage] = Field(default_factory=list)
    long_term_memory: Optional[dict] = Field(alias="long_term_memory", default=None)
    plugin_configs: Optional[list[PluginConfig]] = Field(
        alias="plugin_configs", default=None
    )
    version: Optional[Union[str, int]] = None
    user_id: Optional[str] = Field(alias="userId", default=None)
    enable_history: bool = Field(alias="enable_history", default=True)


class AgentAppRunRequest(BaseModel):
    """智能体试运行请求"""

    query: Optional[str] = Field(default=None)
    inputs: dict = Field(default_factory=dict)
    long_term_memory: Optional[dict] = Field(alias="long_term_memory", default=None)
    tool_switch_dict: dict = Field(alias="tool_switch_dict", default_factory=dict)
    model_deployment_id: Optional[str] = Field(
        alias="model_deployment_id", default=None
    )
    enable_history: bool = Field(alias="enable_history", default=True)
    histories: list[ConversationHistoryMessage] = Field(default_factory=list)
    files: list[dict] = Field(default_factory=list)
    agent_type: str = Field(alias="agent_type", default="auto")
    version: Optional[Union[str, int]] = None
    user_id: Optional[str] = Field(alias="userId", default=None)
