"""Pydantic schemas for orchestration execute endpoint."""

import time
from enum import Enum
from typing import Optional, Union, Dict, List, Any

from jiuwen.serve.controllers.execution.constants import (
    MIN_MESSAGE_ROLE_LENGTH,
    MIN_CONVERSATION_ID_LENGTH,
)
from jiuwen.serve.schemas.orchestration_mgr import (
    ToolCallSchema,
    ConversationHistoryMessage,
)
from pydantic import BaseModel, Field, StrictStr


class ResponseMode(str, Enum):
    STREAMING = "streaming"
    BLOCKING = "blocking"


class PluginConfig(BaseModel):
    """Defines the structure of one plugin config."""

    plugin_id: StrictStr = Field(min_length=1, alias="pluginId")

    config: Optional[dict] = Field(default={})

    @classmethod
    def validate_config(cls, v):
        """validate config"""
        if not isinstance(v, dict):
            raise ValueError("Input should be a valid dict")
        return v


class ExecutionParams(BaseModel):
    """Defines the structure of execution params."""

    conversation_key: Optional[StrictStr] = Field(alias="conversationKey", default="")
    conversation_history: Optional[list[ConversationHistoryMessage]] = Field(
        alias="conversationHistory", default_factory=list
    )
    plugin_configs: Optional[Union[list[PluginConfig], dict]] = Field(
        alias="pluginConfigs", default_factory=list
    )
    global_variables: Optional[dict] = Field(
        alias="globalVariables", default_factory=dict
    )
    tool_switch_dict: Optional[dict] = Field(
        alias="toolSwitchDict", default_factory=dict
    )
    workflow_sequence: Optional[list[str]] = Field(
        alias="workflowSequence", default_factory=list
    )
    active_workflows: Optional[list[str]] = Field(
        alias="activeWorkflows", default_factory=list
    )
    intent: Optional[str] = Field(alias="intent", default="")
    enable_history: Optional[bool] = Field(alias="enableHistory", default=True)
    environment_variables: Optional[dict] = Field(
        alias="environmentVariables", default_factory=dict
    )
    files: Optional[List[Dict[str, Any]]] = Field(alias="files", default_factory=list)
    deepresearch_agent_config: Optional[dict] = Field(
        alias="DeepResearchAgentConfig", default_factory=dict
    )
    # DeepResearch report generation variables
    message: Optional[str] = Field(alias="message", default="")
    report_template: Optional[str] = Field(alias="reportTemplate", default="")
    interrupt_feedback: Optional[str] = Field(alias="interruptFeedback", default="")
    # DeepResearch template generation variables
    file_name: Optional[str] = Field(alias="fileName", default="")
    file_stream: Optional[str] = Field(alias="fileStream", default="")
    is_template: Optional[bool] = Field(alias="isTemplate", default=False)
    file_url: Optional[str] = Field(alias="fileUrl", default="")
    repo_id: Optional[str] = Field(alias="repoId", default="")
    enable_memory_retrieve: Optional[bool] = Field(
        alias="enableMemoryRetrieve", default=False
    )
    enable_memory_extract: Optional[bool] = Field(
        alias="enableMemoryExtract", default=False
    )
    sys_operation_card: Optional[dict] = Field(alias="sysOperationCard", default=None)
    # Internal: cached IR data to avoid redundant storage reads (excluded from JSON serialization)
    ir_cache: Optional[dict] = None
    is_debug: bool = Field(
        default=False, alias="isDebug", description="是否启用调试模式"
    )


class ConversationHistoryMessage(BaseModel):
    """Defines the structure of one conversation history message."""

    role: StrictStr = Field(min_length=MIN_MESSAGE_ROLE_LENGTH)
    content: Optional[StrictStr] = Field(default="")
    files: Optional[List[Dict[str, Any]]] = Field(default=None)
    name: Optional[StrictStr] = Field(default=None)
    intent: Optional[list[StrictStr]] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCallSchema]] = Field(default=None)
    function_call: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        default=None
    )
    enable_history: Optional[bool] = Field(default=True)
    agent_id: Optional[str] = Field(default=None)


class ExecutionRequest(BaseModel):
    conversation_id: str = Field(min_length=1, alias="conversationId")
    user_id: str = Field(default="anonymous", alias="userId")
    # 平台 userId 独立保留（Memory 用，不被 cust-userid 覆盖）
    platform_user_id: str = Field(default="", alias="platformUserId")
    ir_path: str = Field(default="__mvp_mock__", alias="irPath")
    params: ExecutionParams = Field(default_factory=ExecutionParams)
    headers: Optional[dict] = Field(default={})
    query: str = ""
    response_mode: ResponseMode = Field(
        default=ResponseMode.STREAMING, alias="responseMode"
    )
    agent_type: str = Field(
        default="auto",
        alias="agentType",
        description="Agent类型: auto=自动检测, workflow=WorkflowRunner, react=ReActAgent, controller=ControllerRunner",
    )
    resume_input: Optional[str] = Field(
        default=None,
        alias="resumeInput",
        description="恢复中断时的用户输入（后端自动检测会话状态决定是否使用）",
    )


class StreamingChatResponse(BaseModel):
    event: str
    data: Optional[dict] = None
    createdTime: int = Field(default_factory=lambda: int(time.time() * 1000))
    executionId: Optional[str] = None
    index: Optional[int] = None
    isStructMessage: Optional[bool] = None

    class Config:
        populate_by_name = True


class ConversationEvent(str, Enum):
    START = "start"
    DONE = "done"
    MESSAGE = "message"
    ERROR = "error"
    EXCEPTION = "exception"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    WORKFLOW_NODE_MESSAGE = "workflow_node_message"
    # Controller mode events
    TASK_START = "task_start"
    TASK_END = "task_end"
    WAITING_USER_INPUT = "waiting_user_input"
    INTERMEDIATE_MESSAGE = "intermediate_message"
    AGENT_HANDOFF = "agent_handoff"
    AGENT_INTERRUPTED = "agent_interrupted"
    TASK_TERMINATED = "task_terminated"


class ComponentDebugRequest(BaseModel):
    conversation_id: str = Field(min_length=1, alias="conversationId")
    user_id: str = Field(default="anonymous", alias="userId")
    ir_path: str = Field(min_length=1, alias="irPath")
    inputs: dict = Field(
        default_factory=dict, description="Debug inputs for the component"
    )
    params: ExecutionParams = Field(default_factory=ExecutionParams)
    headers: Optional[dict] = Field(default={})


class DeleteExecutionInstanceRequest(BaseModel):
    """
    执行管理器用户删除执行请求模型。

    功能描述：
    此类用于表示执行管理器的删除执行请求，包含请求的必要信息。
    """

    conversation_id: StrictStr = Field(
        min_length=MIN_CONVERSATION_ID_LENGTH, alias="conversationId"
    )
    """对话ID，最小长度为`MIN_CONVERSATION_ID_LENGTH`。"""

    ir_path: Optional[StrictStr] = Field(alias="irPath", default="")
    """IR路径，默认为空字符串。"""
