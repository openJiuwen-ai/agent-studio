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
    environment_id: Optional[str] = None
    workspace_id: Optional[str] = None


@dataclass
class AgentRunContext:
    """智能体试运行上下文 — 封装路径参数."""
    project_id: str
    agent_id: str
    conversation_id: str
    version: Optional[str]
    environment_id: Optional[str] = None
    workspace_id: Optional[str] = None


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

    inputs: dict = Field(
        default_factory=dict,
        description="输入参数，必须包含 query 字段作为用户消息",
        examples=[{"query": "帮我创建一个工作流"}],
    )
    memory_inputs: Optional[dict] = Field(
        alias="memory_inputs", default=None,
        description="记忆输入参数",
        examples=[{"last_topic": "天气"}],
    )
    globals: dict = Field(
        default_factory=dict,
        description="全局变量",
        examples=[{"var1": "value1"}],
    )
    environment: dict = Field(
        default_factory=dict,
        description="环境变量（优先使用 environment_id 从 Redis 加载）",
        examples=[{"API_KEY": "sk-xxx"}],
    )
    messages: list[ConversationHistoryMessage] = Field(
        default_factory=list,
        description="会话历史消息（携带时跳过 Redis 加载）",
    )
    long_term_memory: Optional[dict] = Field(
        alias="long_term_memory", default=None,
        description="长期记忆配置",
    )
    plugin_configs: Optional[list[PluginConfig]] = Field(
        alias="plugin_configs", default=None,
        description="插件配置列表",
    )
    version: Optional[Union[str, int]] = Field(
        default=None,
        description="发布版本号，latest 表示使用最新发布版本",
        examples=["latest", 1],
    )
    user_id: Optional[str] = Field(
        alias="userId", default=None,
        description="用户ID",
    )
    enable_history: bool = Field(
        alias="enable_history", default=True,
        description="是否启用会话历史",
    )


class AgentAppRunRequest(BaseModel):
    """智能体试运行请求"""

    query: Optional[str] = Field(
        default=None,
        description="用户输入消息",
        examples=["你好，请帮我分析数据"],
    )
    resume_input: Optional[str] = Field(
        alias="resumeInput", default=None,
        description="恢复执行的输入（用于中断恢复场景）",
    )
    inputs: dict = Field(
        default_factory=dict,
        description="输入参数（含 query、intent、workflowSequence、activeWorkflows 等）",
        examples=[{"query": "你好", "intent": "chat"}],
    )
    long_term_memory: Optional[dict] = Field(
        alias="long_term_memory", default=None,
        description="长期记忆配置",
    )
    tool_switch_dict: dict = Field(
        alias="tool_switch_dict", default_factory=dict,
        description="工具开关配置，key 为工具ID，value 为是否启用",
        examples=[{"tool_001": True}],
    )
    model_deployment_id: Optional[str] = Field(
        alias="model_deployment_id", default=None,
        description="模型部署ID",
    )
    enable_history: bool = Field(
        alias="enable_history", default=True,
        description="是否启用会话历史",
    )
    histories: list[ConversationHistoryMessage] = Field(
        default_factory=list,
        description="会话历史消息（携带时跳过 Redis 加载）",
    )
    files: list[str] = Field(
        default_factory=list,
        description="文件 URL 列表（支持图片/视频，自动识别扩展名）",
        examples=[["https://example.com/image.png"]],
    )
    agent_type: str = Field(
        alias="agent_type", default="auto",
        description="智能体类型：auto-自动推断、deepresearch-深度研究（不支持）",
        examples=["auto"],
    )
    version: Optional[Union[str, int]] = Field(
        default=None,
        description="发布版本号，latest 表示使用最新发布版本",
        examples=["latest", 1],
    )
    user_id: Optional[str] = Field(
        alias="userId", default=None,
        description="用户ID",
    )


@dataclass
class NodeRunContext:
    """工作流单节点执行上下文 — 封装路径参数."""
    project_id: str
    workflow_id: str
    conversation_id: str
    node_id: str


class NodeExecuteRequest(BaseModel):
    """工作流单节点执行请求"""

    inputs: dict = Field(
        default_factory=dict,
        description="节点输入参数",
        examples=[{"query": "测试数据"}],
    )
    plugin_configs: Optional[list[PluginConfig]] = Field(
        alias="plugin_configs", default=None,
        description="插件配置列表",
    )
    version: Optional[Union[str, int]] = Field(
        default=None,
        description="发布版本号",
    )
    user_id: Optional[str] = Field(
        alias="userId", default=None,
        description="用户ID",
    )
