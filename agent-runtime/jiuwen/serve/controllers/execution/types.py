# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""This module defines execution data types."""

from dataclasses import dataclass
from typing import Optional, Union, List, Any

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.orchestration.flow.workflow import Workflow
from jiuwen.serve.common.message import MessageCollector
from jiuwen.serve.controllers.execution.enum import (
    ConversationEvent,
    IRType,
    AsyncExecutionStatus,
)
from pydantic import BaseModel, Field, StrictStr, field_validator

typeList = ["ReAct", "RAG", "ToolUse", "Controller", "ToolUse", "PlanExecute"]


@dataclass
class WorkflowConfigs:
    """Container for workflow configurations"""

    normal: List
    start: Optional[object] = None
    end: Optional[object] = None
    default: Optional[object] = None
    global_workflows: List = None
    intent: List = None

    def __post_init__(self):
        if self.global_workflows is None:
            self.global_workflows = []
        if self.intent is None:
            self.intent = []


class ErrorResponse(BaseModel):
    """
    Common error response
    """

    code: int
    message: StrictStr


class AsyncChatResponse(BaseModel):
    """
    An async chat response.
    """

    data: dict
    created_time: int = Field(alias="createdTime")

    event: Optional[ConversationEvent] = Field(default=ConversationEvent.ASYNC_RESPONSE)
    execution_id: Optional[StrictStr] = Field(alias="executionId", default=None)


class AsyncExecutionResponse(BaseModel):
    """
    The async execution results of a workflow, which contains several messages of StreamData.
    """

    status: AsyncExecutionStatus
    time: int

    messages: Optional[list] = Field(default=None)


class CompletionChatResponse(BaseModel):
    """
    A complete chat response.
    """

    data: dict
    created_time: int = Field(alias="createdTime")

    execution_id: StrictStr = Field(alias="executionId")
    event: Optional[ConversationEvent] = Field(
        default=ConversationEvent.BLOCKING_RESPONSE
    )
    message_list: Optional[list] = Field(alias="messageList", default=[])
    card_list: Optional[list] = Field(alias="cardList", default=[])


class StreamingChatResponse(BaseModel):
    """
    A streaming chunk of chat response.
    """

    event: ConversationEvent
    data: dict
    created_time: int = Field(alias="createdTime")

    execution_id: Optional[StrictStr] = Field(alias="executionId", default=None)
    index: Optional[int] = Field(default=None)
    is_struct_message: bool = Field(alias="isStructMessage", default=False)


class CancelExecutionResponse(BaseModel):
    """
    The response of cancel_ir_execution_async interface.
    """

    code: int
    message: StrictStr


@dataclass
class ExecutionData:
    """
    Stores an executable instance of agent or workflow, along with its latest updated time.
    """

    instance: Union[Workflow, Any]
    instance_type: IRType
    updated_time: int
    collector: Optional[MessageCollector] = None


class ModelConfigValidator(BaseModel):
    modelName: str = Field(..., description="模型名字", max_length=1000)
    modelType: str = Field(..., description="模型类型", max_length=1000)
    hyperParameters: dict = Field(..., description="配置项列表")
    extension: dict = Field(default={}, description="配置项列表")

    # 使用 field_validator 校验 temperature 和 topP 范围
    @field_validator("hyperParameters", mode="before")
    @classmethod
    def check_hyper_parameters(cls, v):
        """validate hyper_parameters rule"""
        if not isinstance(v, dict):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="hyper_parameters should be dict"
                ),
            )
        temperature = v.get("temperature")
        if (
            not isinstance(temperature, (float, int))
            or temperature < 0
            or temperature > 1
        ):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="temperature must be between 0 and 1"
                ),
            )
        top_p = v.get("top_p")
        if not isinstance(top_p, (int, float)) or top_p < 0 or top_p > 1:
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="top_p must be between 0 and 1"
                ),
            )
        thinking = v.get("thinking")
        if thinking is not None and (
            not isinstance(thinking, dict)
            or thinking.get("type") not in ("enabled", "disabled")
        ):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="model thinking type is not valid"
                ),
            )
        return v


class AgentIrValidator(BaseModel):
    schemaVersion: str = Field(..., description="AgentIR版本号", max_length=1000)
    agentId: str = Field(..., description="Agent唯一标识id", max_length=1000)
    description: str = Field(..., description="Agent描述信息", max_length=1000)
    agentVersion: str = Field(..., description="agent版本号", max_length=1000)
    agentName: str = Field(..., description="Agent名称", max_length=1000)
    configs: dict = Field(..., description="配置项列表")

    # 使用 field_validator 校验 configs 字段的格式
    @field_validator("configs", mode="before")
    @classmethod
    def validate_configs(cls, v):
        """validate configs rule"""
        if not isinstance(v, dict):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="configs must be dictionaries"
                ),
            )
        sys_prompt = v.get("sysPromptTemplate")
        if not isinstance(sys_prompt, str) or len(sys_prompt) > 10000:
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="sysPromptTemplate must be a string or length more than 10000"
                ),
            )
        mode = v.get("mode")
        if mode not in typeList:
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg='mode must be "ReAct" or "Controller"'
                ),
            )
        max_iteration = v.get("maxIteration")
        if not (isinstance(max_iteration, int) and 0 <= max_iteration < 101):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="maxIteration must be an integer between 0 and 30"
                ),
            )
        model_config = v.get("modelConfig")
        if model_config is not None:
            ModelConfigValidator(**model_config)
        plugins = v.get("plugins")
        if not isinstance(plugins, list):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="plugins must be list"
                ),
            )
        for plugin in plugins:
            if not isinstance(plugin, dict):
                raise JiuWenBaseException(
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                        error_msg="plugin ir must be dict"
                    ),
                )
        mcps = v.get("mcps", [])
        if not isinstance(mcps, list):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="mcps must be list"
                ),
            )
        for mcp in mcps:
            if not isinstance(mcp, dict):
                raise JiuWenBaseException(
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                        error_msg="mcp ir must be dict"
                    ),
                )
        workflows = v.get("workflows")
        if workflows is None or not isinstance(workflows, list):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg="workflows must exist and type must be list"
                ),
            )
        for workflow in workflows:
            if not isinstance(workflow, dict):
                raise JiuWenBaseException(
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                        error_msg="workflow must be dict"
                    ),
                )
            workflow_path = workflow.get("ir_path")
            if not workflow_path or not isinstance(workflow_path, str):
                raise JiuWenBaseException(
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                        error_msg="workflow path must be str"
                    ),
                )

        return v


class AsyncExecutionState(BaseModel):
    """
    Async execution state.
    """

    status: AsyncExecutionStatus
    exec_id: StrictStr
