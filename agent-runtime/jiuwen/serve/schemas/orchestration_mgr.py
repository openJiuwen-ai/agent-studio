#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Restful parameters for IrManager and InvokableManager of orchestration."""

__all__ = (
    "ManagerContent",
    "InvokableManagerIds",
    "IrManagerIds",
    "IrManageParams",
    "IrManagerUserInput",
    "IrManagerNotifySession",
    "ExecutionRequest",
    "ExecutionParams",
    "ComponentExecutionRequest",
    "ComponentParams",
    "IrManagerCleanSession",
    "AgentRegisterParams",
    "WorkflowRegisterParams",
    "IrManagerStopInvocation",
    "DeleteExecutionInstanceRequest",
)

from typing import Union, Optional, Any, List, Dict

from jiuwen.orchestration.ir.ir_types import AgentId
from jiuwen.serve.controllers.execution.constants import (
    MIN_IR_PATH_LENGTH,
    MIN_PLUGIN_ID_LENGTH,
    MIN_MESSAGE_ROLE_LENGTH,
    MIN_QUERY_LENGTH,
    MIN_CONVERSATION_ID_LENGTH,
)
from jiuwen.serve.controllers.execution.enum import ResponseMode, ExecutionMode
from pydantic import BaseModel, Field, StrictStr, field_validator, ConfigDict
from starlette.datastructures import Headers


class ManagerContent(BaseModel):
    """manger content model"""

    mgr_name: str = Field(alias="mgrName")
    content_json: str = Field(alias="contentJson")


class InvokableManagerIds(BaseModel):
    """invokable manager model"""

    mgr_name: str = Field(alias="mgrName")
    ids: list[str] = Field(alias="typeIds")


class WorkflowRegisterParams(BaseModel):
    """Validation class for Restful interface of workflow register and update"""

    mgr_name: str = Field(alias="mgrName")
    workflow_ir: str = Field(alias="workflowIr")
    component_type_irs: Optional[list[str]] = Field(
        alias="componentTypeIrs", default=None
    )
    sub_workflow_irs: Optional[list[str]] = Field(alias="subWorkflowIrs", default=None)


class AgentRegisterParams(BaseModel):
    """Validation class for Restful interface of Agent register and update"""

    mgr_name: str = Field(alias="mgrName")
    agent_ir: str = Field(alias="agentIr")
    component_type_irs: Optional[list[str]] = Field(
        alias="componentTypeIrs", default=None
    )
    workflow_irs: Optional[list[str]] = Field(alias="workflowIrs", default=None)


class IrManagerIds(BaseModel):
    """ir manager model"""

    mgr_name: str = Field(alias="mgrName")
    agents: list[AgentId]


class IrManageParams(BaseModel):
    """Validation class for Restful interface of IrMgrBase.register(...) and update(...)"""

    mgr_name: str = Field(alias="mgrName")
    ir: str
    invokable: list[str]


class IrManagerUserInput(BaseModel):
    """ir manager user input model"""

    mgr_name: str = Field(alias="mgrName")
    session_id: str = Field(alias="sessionId")
    data: str
    session: Union[dict[str, Any], None] = Field(None, alias="session")


class IrManagerNotifySession(BaseModel):
    """Validation class for Restful interface of IrMgrBase.notify_session(...)"""

    mgr_name: StrictStr = Field(alias="mgrName")
    session_id: StrictStr = Field(alias="sessionId")
    message: StrictStr
    session: Union[dict[str, Any], None] = Field(None, alias="session")


class IrManagerCleanSession(BaseModel):
    """Validation class for Restful interface of IrMgrBase.clean_session(...)"""

    mgr_name: StrictStr = Field(alias="mgrName")
    session_id: StrictStr = Field(alias="sessionId")
    session: Union[dict[str, Any], None] = Field(None, alias="session")


class IrManagerStopInvocation(BaseModel):
    """Validation class for Restful interface of IrMgrBase.cancel_task(...)"""

    mgr_name: StrictStr = Field(alias="mgrName")
    task_id: StrictStr = Field(alias="taskId")
    session: Union[dict[str, Any], None] = Field(None, alias="session")


class ToolCallSchema(BaseModel):
    """schema of tool calls for role is assistant"""

    type: Optional[str] = Field(default="")
    id: Optional[str] = Field(default="")
    function: Optional[Dict[str, Any]] = Field(default_factory=dict)


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


class PluginConfig(BaseModel):
    """Defines the structure of one plugin config."""

    plugin_id: StrictStr = Field(min_length=MIN_PLUGIN_ID_LENGTH, alias="pluginId")

    config: Optional[dict] = Field(default={})

    @field_validator("config", mode="before")  # noqa: pydantic.field_validator accepts a classmethod
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
    # 默认 None=未提供（Controller 使用全部业务工作流）；
    # 显式空列表 [] 表示明确的权限收窄（无业务工作流候选），二者必须可区分
    workflow_sequence: Optional[list[str]] = Field(
        alias="workflowSequence", default=None
    )
    active_workflows: Optional[list[str]] = Field(
        alias="activeWorkflows", default=None
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
    app_id: Optional[str] = Field(alias="appId", default="")
    enable_memory_retrieve: Optional[bool] = Field(
        alias="enableMemoryRetrieve", default=False
    )
    enable_memory_extract: Optional[bool] = Field(
        alias="enableMemoryExtract", default=False
    )
    sys_operation_card: Optional[dict] = Field(alias="sysOperationCard", default=None)

    @field_validator("global_variables", mode="before")  # noqa: pydantic.field_validator accepts a classmethod
    @classmethod
    def validate_global_variables(cls, v):
        """validate global_variables"""
        if not isinstance(v, dict):
            raise ValueError("Input should be a valid dict")
        return v

    @field_validator("tool_switch_dict", mode="before")  # noqa: pydantic.field_validator accepts a classmethod
    @classmethod
    def validate_tool_switch_dict(cls, v):
        """validate tool_switch_dict"""
        if not isinstance(v, dict):
            raise ValueError("Input should be a valid dict")
        for tool_name, switch_value in v.items():
            if not isinstance(switch_value, bool):
                raise ValueError(f"the value of {tool_name} should be of boolean type")
        return v


class ExecutionRequest(BaseModel):
    """
    执行管理器用户请求模型。

    功能描述：
    此类用于表示执行管理器的用户请求，包含请求的必要信息。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    """允许使用任意类型字段的配置。"""

    conversation_id: StrictStr = Field(
        min_length=MIN_CONVERSATION_ID_LENGTH, alias="conversationId"
    )
    """对话ID，最小长度为`MIN_CONVERSATION_ID_LENGTH`。"""

    query: StrictStr = Field(min_length=MIN_QUERY_LENGTH)
    """查询字符串，最小长度为`MIN_QUERY_LENGTH`。"""

    ir_path: StrictStr = Field(min_length=MIN_IR_PATH_LENGTH, alias="irPath")
    """IR路径，最小长度为`MIN_IR_PATH_LENGTH`。"""

    params: Optional[ExecutionParams] = Field(default_factory=ExecutionParams)
    """执行参数，默认为`ExecutionParams`实例。"""

    headers: Optional[Union[Headers, dict]] = Field(default={})
    """请求头，默认为空字典。"""

    response_mode: Optional[ResponseMode] = Field(
        default=ResponseMode.STREAMING, alias="responseMode"
    )
    """响应模式，默认为流式响应。"""

    execution_mode: Optional[ExecutionMode] = Field(
        default=ExecutionMode.SYNC, alias="executionMode"
    )
    """执行模式，默认为同步执行。"""

    user_id: StrictStr = Field(alias="userId", default=None)
    """用户ID，默认为None。"""

    @field_validator("query", mode="before")  # noqa: pydantic.field_validator accepts a classmethod
    @classmethod
    def validate_query(cls, v):
        """
        验证查询字符串。

        Args:
            v (str): 查询字符串。

        Raises:
            ValueError: 如果查询字符串为空或仅包含空白字符，抛出此异常。

        Returns:
            str: 验证通过的查询字符串。
        """
        if not v.strip():
            raise ValueError("query cannot be empty or whitespace only")
        return v


class ComponentParams(BaseModel):
    """Defines the structure of component execution params."""

    conversation_history: Optional[list[ConversationHistoryMessage]] = Field(
        alias="conversationHistory", default=[]
    )
    plugin_configs: Optional[list[PluginConfig]] = Field(
        alias="pluginConfigs", default=[]
    )
    global_variables: Optional[dict] = Field(
        alias="globalVariables", default_factory=dict
    )
    app_id: Optional[str] = Field(alias="appId", default="")
    enable_memory_retrieve: Optional[bool] = Field(
        alias="enableMemoryRetrieve", default=False
    )


class ComponentExecutionRequest(BaseModel):
    """
    组件执行管理器用户请求模型。

    功能描述：
    此类用于表示组件执行管理器的用户请求，包含请求的必要信息。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    """允许使用任意类型字段的配置。"""

    conversation_id: StrictStr = Field(
        min_length=MIN_CONVERSATION_ID_LENGTH, alias="conversationId"
    )
    """对话ID，最小长度为`MIN_CONVERSATION_ID_LENGTH`。序列化别名为`conversationId`"""

    ir_path: StrictStr = Field(min_length=MIN_IR_PATH_LENGTH, alias="irPath")
    """IR路径，最小长度为`MIN_IR_PATH_LENGTH`。序列化别名为`irPath`"""

    inputs: dict
    """输入字典。"""

    params: Optional[ComponentParams] = Field(default_factory=ComponentParams)
    """组件参数，默认为`ComponentParams`实例。"""

    headers: Optional[Union[Headers, dict]] = Field(default={})
    """请求头，默认为空字典。"""

    user_id: StrictStr = Field(alias="userId", default=None)
    """用户ID，默认为None。序列化别名为`userId`"""

    agent_id: Optional[str] = Field(alias="agentId", default=None)


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
