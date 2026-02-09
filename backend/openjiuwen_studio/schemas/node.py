#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from openjiuwen_studio.core.common import dsl


class NodePosition(BaseModel):
    x: float = Field(0, alias="x")
    y: float = Field(0, alias="y")


class Meta(BaseModel):
    position: NodePosition = Field(..., alias="position")


class Extra(BaseModel):
    index: int = Field(..., alias="index")


class BaseType(BaseModel):
    type: Optional[str] = Field("", alias="type")


class BaseValue(BaseType):
    default: Optional[Any] = Field(None, alias="default")
    description: Optional[str] = Field("", alias="description")
    content: Optional[Any] = Field(None, alias="content")
    extra: Optional[Extra] = Field(None, alias="extra")
    schema: Optional[BaseType] = Field(None, alias="schema")
    items: Optional[Dict] = Field(None, alias="items")


class Outputs(BaseType):
    properties: Optional[Dict[str, Dict]] = Field(None, alias="properties")
    required: Optional[List[Any]] = Field([], alias="required")


class PromptValue(BaseValue):
    content: str = Field(..., alias="content")


class ModelInfo(BaseType):
    id: str = Field(..., alias="id")
    name: str = Field(..., alias="name")


class LLMParam(BaseModel):
    model: ModelInfo = Field(..., alias="model")
    prompt: PromptValue = Field(..., alias="prompt")
    system_prompt: PromptValue = Field(..., alias="systemPrompt")


class BranchCondition(BaseModel):
    operator: Any = Field(..., alias="operator")
    left: BaseValue = Field(..., alias="left")
    right: Optional[BaseValue] = Field(None, alias="right")


class BranchInfo(BaseModel):
    branch_id: str = Field(..., alias="branchId")
    logic: Optional[int] = Field(0, alias="logic")
    conditions: Optional[List[BranchCondition]] = Field(None, alias="conditions")

    class Config:
        populate_by_name = True


class SubWorkflowConfig(BaseModel):
    workflow_id: str = Field(..., alias="workflowId")
    workflow_name: Optional[str] = Field(None, alias="workflowName")
    workflow_version: Optional[str] = Field(None, alias="workflowVersion")
    workflow_description: Optional[str] = Field(None, alias="workflowDescription")


class NodeConfigs(BaseModel):
    sub_workflow: Optional[SubWorkflowConfig] = Field(None, alias="subWorkflow")


class LoopParam(BaseType):
    loop_num: Optional[BaseValue] = Field(0, alias="loopNum")
    loop_array: Optional[Dict[str, BaseValue]] = Field(None, alias="loopArray")
    intermediate_var: Optional[Dict[str, BaseValue]] = Field(None, alias="intermediateVar")


class Content(BaseType):
    content: Optional[str] = Field("", alias="content")
    streaming: Optional[bool] = Field(False, alias="streaming")


class TextConcatenateFormat(BaseModel):
    type: str = Field(..., alias="type")
    content: str = Field(..., alias="content")


class TextEditorParam(BaseModel):
    edit_type: Optional[str] = Field(None, alias="editType")
    delimiters: Optional[list[str]] = Field(None, alias="delimiters")  # 分隔符; 如果是值为CUSTOM_DELIMITER_VAL，则代表自定义
    concatenate_format: Optional[TextConcatenateFormat] = Field(None, alias="concatenateFormat")
    custom_delimiters: Optional[list[str]] = Field(None, alias="customDelimiters")  # 如果是自定义，同时使用此值作为分隔符

    class Config:
        populate_by_name = True


class Intent(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    id: str = Field("")


class VariableMerge(BaseModel):
    name: str = Field(..., alias="name")
    type: str = Field(..., alias="type")
    items: list[str] = Field(..., alias="items")


class PluginParam(BaseModel):
    plugin_id: str = Field(..., alias="pluginID")
    tool_id: str = Field(..., alias="toolID")
    plugin_name: Optional[str] = Field("", alias="pluginName")
    tool_name: Optional[str] = Field("", alias="toolName")
    plugin_version: Optional[str] = Field("draft", alias="pluginVersion")


class Inputs(BaseModel):
    input_parameters: Optional[Dict[str, BaseValue]] = Field(None, alias="inputParameters")
    llm_param: Optional[LLMParam] = Field(None, alias="llmParam")
    loop_param: Optional[LoopParam] = Field(None, alias="loopParam")
    intents: Optional[list[Intent]] = Field(None)
    default_intent: Optional[str] = Field("0")
    content: Optional[Content] = Field(None, alias="content")
    text_editor_param: Optional[TextEditorParam] = Field(None, alias="textEditorParam")
    language: Optional[str] = Field("", alias="language")
    code: Optional[str] = Field("", alias="code")
    variable_merge: Optional[list[VariableMerge]] = Field(None, alias="variableMerge")
    plugin_param: Optional[PluginParam] = Field(None, alias="pluginParam")
    streaming: Optional[bool] = Field(False)
    max_response: Optional[int] = Field(3, alias="max_response")
    enable_history: Optional[bool] = Field(False, alias="historyEnable")


    class Config:
        populate_by_name = True

    @model_validator(mode='after')
    def check_text_editor_inputs(self) -> 'Inputs':
        from openjiuwen_studio.core.common.dsl import TextEditorType

        # 只有当 text_editor_param 存在且 edit_type 为 StringSplitting 才继续
        if (
                self.text_editor_param is not None
                and self.text_editor_param.edit_type == TextEditorType.SPLITTING.value
        ):
            if self.input_parameters is not None and len(self.input_parameters) > 1:
                raise ValueError(
                    f"When textEditorParam.editType is '{TextEditorType.SPLITTING.value}', "
                    "it is required that the length of inputParamters must <= 1."
                )
        return self

    @model_validator(mode='after')
    def check_variable_merge_inputs(self) -> 'Inputs':
        # 只有当 variable_merge 存在才验证
        if self.variable_merge is not None:
            for group in self.variable_merge:
                for var in group.items:
                    # Group中的输入在input_parameters中存在
                    if var not in self.input_parameters:
                        raise ValueError(f"variable_merge: {group.name}/{var} not in the input_parameters")
                    # Group中的输入格式相同
                    if self.input_parameters[var].type == 'constant' and group.type != self.input_parameters[
                        var].schema.type:
                        raise ValueError(f"variable_merge: {group.name}'s type({group.type}) is different \
                                         from {var}'s type({self.input_parameters[var].type}).")
        return self


class ExceptionStep(BaseModel):
    default_step: str = Field("default", alias="defaultStep")
    error_step: str = Field("branch_error", alias="errorStep")


class ExceptionConfig(BaseModel):
    retry_times: int = Field(0, alias="retryTimes")
    timeout_seconds: int = Field(60, alias="timeoutSeconds")
    process_type: dsl.ExceptHandlingMethod = Field(dsl.ExceptHandlingMethod.BREAK, alias="processType")
    return_content: Optional[Dict] = Field(None, alias="returnContent")
    execute_step: Optional[ExceptionStep] = Field(None, alias="executeStep")


class VariableAssign(BaseModel):
    operator: str = Field(..., alias="operator")
    left: BaseValue = Field(..., alias="left")
    right: BaseValue = Field(..., alias="right")


class NodeData(BaseModel):
    title: str = Field("", alias="title")
    inputs: Optional[Inputs] = Field(None, alias="inputs")
    outputs: Optional[Outputs] = Field(None, alias="outputs")
    output_format: dsl.LLMResponseFormatType = Field(dsl.LLMResponseFormatType.Text, alias="output_format")
    branches: Optional[List[BranchInfo]] = Field([], alias="branches")
    configs: Optional[NodeConfigs] = Field(None, alias="configs")
    exception_config: Optional[ExceptionConfig] = Field(None, alias="exceptionConfig")
    assign: Optional[List[VariableAssign]] = Field([], alias="assign")


class Edge(BaseModel):
    source_node_id: str = Field(..., alias="sourceNodeID")
    target_node_id: str = Field(..., alias="targetNodeID")
    source_port_id: Optional[str] = Field("", alias="sourcePortID")


class Node(BaseType):
    id: str = Field(..., alias="id")
    meta: Meta = Field(..., alias="meta")
    data: NodeData = Field(..., alias="data")
    blocks: Optional[List[Dict]] = Field([], alias="blocks")
    edges: Optional[List[Edge]] = Field([], alias="edges")
