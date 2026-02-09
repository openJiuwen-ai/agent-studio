#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from openjiuwen.core.session.tracer.span import TraceWorkflowSpan, TraceAgentSpan
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from openjiuwen_studio.core.common.message import ExecuteResponse
from openjiuwen_studio.schemas.agent import AgentId
from openjiuwen_studio.schemas.workflow import WorkflowId


class ExecutionCallType(str, Enum):
    ''' 发起某次执行的调用者类型 '''
    workflow = "workflow"
    agent = "agent"
    llm = "LLM"
    plugin = "plugin"


class ComponentExecuteStatus(str, Enum):
    '''执行时，component的可选状态, TraceWorkflowSpan.status'''
    finish = "finish"
    start = "start"
    error = "error"


class ExecutionTraceChunkType(str, Enum):
    '''   某次执行trace中，各个chunk的类型 '''
    workflow_tracer = "tracer_workflow"
    workflow_final = "workflow_final"
    agent_tracer = "tracer_agent"
    agent_answer = "answer"


class WfExecutionLogsFilter(WorkflowId):
    ''' workflow的日志筛选条件 '''
    model_config = ConfigDict(populate_by_name=True)
    status: Optional[str] = Field(None, description='finish/start/error/running/interrupted/unknown')
    start_time: Optional[datetime] = Field(None, alias="startTime", description='None means unrestricted')
    end_time: Optional[datetime] = Field(None, alias="endTime", description='None means unrestricted')


class WfExecutionLogIndex(WorkflowId):
    ''' workflow的某次日志索引 '''
    model_config = ConfigDict(populate_by_name=True)
    trace_id: str = Field(alias="traceId")


class AgExecutionLogsFilter(AgentId):
    ''' agent的日志筛选条件 '''
    model_config = ConfigDict(populate_by_name=True)
    status: Optional[str] = Field(None, description='finish/start/error/running/interrupted/unknown')
    start_time: Optional[datetime] = Field(None, alias="startTime", description='None means unrestricted')
    end_time: Optional[datetime] = Field(None, alias="endTime", description='None means unrestricted')


class AgExecutionLogIndex(AgentId):
    ''' agent的某次日志索引 '''
    model_config = ConfigDict(populate_by_name=True)
    trace_id: str = Field(alias="traceId")


class TraceInvokeExecutionLogIndex(BaseModel):
    ''' 某次日志(agent/workflow)中某个invoke的索引, invoke的类型可能是worfklow/llm/..., 可用于去details表格中获取该invoke的详细数据 '''
    model_config = ConfigDict(populate_by_name=True)
    space_id: str = Field(alias="spaceId")
    trace_id: str = Field(alias="traceId")
    invoke_id: str = Field(alias="invokeId")


class ExecutionLogCreateInfo(BaseModel):
    '''某次执行的创建信息'''
    model_config = ConfigDict(populate_by_name=True)
    trace_id: str = Field(alias="traceId")
    create_time: datetime = Field(alias="createTime")


class InvokeExecuteInfo(BaseModel):
    ''' 某调用节点的某次运行信息，节点可以是agent/workflow/llm/plugin等任何类'''
    model_config = ConfigDict(populate_by_name=True)
    invoke_id: str = Field(
        alias="invokeId", description='the id of the user(agent/workflow/llm/plugin/any component) that runs this node')
    invoke_version: Optional[str] = Field(None, validation_alias=AliasChoices("invokeVersion", "version", "workflow_version", "agent_version"),
                                            serialization_alias="workflow_version")
    invoke_type: Optional[str] = Field(
        None, alias="invokeType", description='type of node: workflow/agent/llm/plugin...')
    invoke_name: Optional[str] = Field(None, validation_alias=AliasChoices(
        "invokeName", "workflowName", "agentName", "pluginName", "llmName"))
    status: Optional[str] = Field(None, description='success/fail/running/interrupted/finish/error/...')
    start_timestamp: Optional[int] = Field(None, alias="startTimestamp", 
                                           description='The start time of the current component is in milliseconds when the start time of the start component is 0ms.')
    duration: Optional[int] = Field(None, description='execution duration in millisecond')
    llm_maximum_reply_length: Optional[int] = Field(None, validation_alias=AliasChoices('maximumReplyLength', "llmMaximumReplyLength", "maximum_reply_length"), 
                                                    description='maximum reply length of llm')
    llm_model: Optional[str] = Field(None, alias="llmModel", description="Model of llm.")
    llm_temperature: Optional[float] = Field(None, validation_alias=AliasChoices(
        "llmTemperature", "temperature"), description='Temperature of llm.')
    llm_ttft: Optional[float] = Field(None, validation_alias=AliasChoices(
        "llmTtft", "TTFT", "ttft"), description='Time to first token of llm.')
    input_tokens: Optional[int] = Field(None, description="The input tokens of this node")
    output_tokens: Optional[int] = Field(None, description="The output tokens of this node")
    loop_node_id: Optional[str] = Field(None, alias="loopNodeId")
    loop_index: Optional[int] = Field(None, alias="loopIndex", description='loop index')
    inputs: Optional[dict] = Field(None)
    outputs: Optional[dict] = Field(None)
    child_invokes_execute_info: Optional[List[InvokeExecuteInfo]] = Field(
        None, alias="childInvokesExecuteInfo", description="child invokes' execute info")


class ExecutionLogSummary(BaseModel):
    ''' workflow/agent的某次日志总结 '''
    model_config = ConfigDict(populate_by_name=True)
    trace_id: str = Field(alias="traceId")
    create_time: datetime = Field(alias="createTime")
    duration: Optional[int] = Field(None)
    status: str = Field(..., description='finish/start/error/running/interrupted/unknown')
    inputs: Optional[dict] = Field(None)
    outputs: Optional[dict] = Field(None)
    input_tokens: Optional[int] = Field(None)
    output_tokens: Optional[int] = Field(None)
    execute_info_list: Optional[List[InvokeExecuteInfo]] = Field(
        None, description="execute info of workflows/plugins/agents/llms/...")


class ExecutionLogDebug(BaseModel):
    ''' agent/workflow的所有日志创建信息 以及 某次日志总结及详情 '''
    model_config = ConfigDict(populate_by_name=True)
    logs_create_list: Optional[list[ExecutionLogCreateInfo]] = Field(default=None, alias="logsCreateList")
    log_summary: Optional[ExecutionLogSummary] = Field(default=None, alias="logSummary")
    log_details: Optional[list[TraceWorkflowSpan | TraceAgentSpan]] = Field(default=None, alias="logDetails")
    workflow_metadata: Optional[dict] = Field(default=None, alias="workflowMetadata")


class ExecutionLogsCreateList(BaseModel):
    ''' 某个workflow/agent所有执行日志的创建信息 '''
    model_config = ConfigDict(populate_by_name=True)
    logs_create_list: list[ExecutionLogCreateInfo] = Field(alias="logsCreateList")


class ApiExecutionLogGet(BaseModel):
    ''' api调用返回：获取某次执行时的返回数据结构，适用包括workflow/agent等类型的执行 '''
    model_config = ConfigDict(populate_by_name=True)
    log_summary: ExecutionLogSummary = Field(alias="logSummary")
    log_details: Optional[list[ExecuteResponse | None]] = Field(default=None, alias="logDetails")


class ApiExecutionLogsDebugEnter(ApiExecutionLogGet):
    ''' api调用返回：前端进入调试页面时的返回数据结构，适用包括workflow/agent等类型的调试 '''
    logs_create_list: list[ExecutionLogCreateInfo] = Field(alias="logsCreateList")

