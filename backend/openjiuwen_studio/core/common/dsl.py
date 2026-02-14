#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import Enum, IntEnum, StrEnum
from typing import Optional, Any, Dict, List, TypeVar, Union
from pydantic import BaseModel as PydanticBaseModel, Field

from openjiuwen.core.workflow.components.flow.loop.loop_comp import LoopType as BaseLoopType


class AgentType(str, Enum):
    ReAct = "react"
    Workflow = "workflow"
    Undefined = "undefined"


class AgentEditMode(StrEnum):
    Manual = "manual"
    Auto = "auto"
    Undefined = "undefined"


class ComponentType(IntEnum):
    COMPONENT_TYPE_EMPTY = 0,
    COMPONENT_TYPE_START = 1,
    COMPONENT_TYPE_END = 2,
    COMPONENT_TYPE_LLM = 3,
    COMPONENT_TYPE_IF = 4,
    COMPONENT_TYPE_LOOP = 5,
    COMPONENT_TYPE_INTENT = 6,
    COMPONENT_TYPE_QUESTION = 7,
    COMPONENT_TYPE_INPUT = 8,
    COMPONENT_TYPE_OUTPUT = 9,
    COMPONENT_TYPE_CODE = 10,
    COMPONENT_TYPE_TEXT_EDITOR = 11,
    COMPONENT_TYPE_CONTINUE = 12,
    COMPONENT_TYPE_BREAK = 13,
    COMPONENT_TYPE_SUB_WORKFLOW = 14,
    COMPONENT_TYPE_EMPTY_START = 15,
    COMPONENT_TYPE_EMPTY_END = 16,
    COMPONENT_TYPE_SET_VARIABLE = 17,
    COMPONENT_TYPE_VARIABLE_MERGE = 18,
    COMPONENT_TYPE_PLUGIN = 19,


class LLMResponseFormatType(StrEnum):
    Text = "text"
    Markdown = "markdown"
    Json = "json"


class TextEditorType(StrEnum):
    CONCATENATION = "StringConcatenation"
    SPLITTING = "StringSplitting"


class BaseModel(PydanticBaseModel):
    model_config = {
        "use_enum_values": True,  # 序列化时输出枚举值而非对象
        "json_encoders": {AgentType: lambda v: v.value,
                          LLMResponseFormatType: lambda v: v.value,
                          TextEditorType: lambda v: v.value,
                          ComponentType: lambda v: v.value}  # 明确指定枚举序列化方式
    }


class ModelClientConfig(BaseModel):
    client_provider: str = Field("")
    api_key: str = Field("")
    api_base: str = Field("")
    timeout: float = Field(0.1)


class ModelRequestConfig(BaseModel):
    model_name: str = Field("")
    temperature: float = Field(0.1)
    top_p: float = Field(0.1)
    stream: bool = Field(False)


class ModelConfig(BaseModel):
    model_id: str = Field("")
    model_client_config: Optional[ModelClientConfig] = Field(default=None)
    request_config: Optional[ModelRequestConfig] = Field(default=None)


class BaseInfo(BaseModel):
    id: str = Field("")
    version: Optional[str] = Field("")

    name: Optional[str] = Field("")
    description: Optional[str] = Field("")


class ToolSchema(BaseInfo):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    configs: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PluginSchema(ToolSchema):
    plugin_id: str = Field("")


class WorkflowSchema(ToolSchema):
    pass


class KnowledgeSchema(ToolSchema):
    pass


class KBRetrievalConfig(BaseModel):
    retrieval_type: Optional[int] = Field(1)
    use_graph: Optional[bool] = Field(False)
    source: Optional[int] = Field(1)
    topk: Optional[int] = Field(5)
    score_threshold: Optional[float] = Field(0.1)
    graph_expansion: Optional[bool] = Field(False)
    use_agent: Optional[bool] = Field(False)
    use_sync: Optional[bool] = Field(True)


class Agent(BaseInfo):
    agent_type: AgentType = Field(AgentType.ReAct)
    configs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    plugins: List[PluginSchema] = Field(default_factory=list)
    workflows: List[WorkflowSchema] = Field(default_factory=list)
    model: ModelConfig = Field(default_factory=ModelConfig)
    knowledges: List[KnowledgeSchema] = Field(default_factory=list)
    kb_retrieval: Optional[KBRetrievalConfig] = Field(default_factory=KBRetrievalConfig)


class ConstrainConfig(BaseModel):
    reserved_max_chat_rounds: int = Field(10)
    max_iteration: int = Field(5)


class ReactAgent(Agent):
    prompt_template_name: str = Field(default="react_system_prompt")
    prompt_template: List[Dict] = Field(default_factory=list)
    constrain: ConstrainConfig = Field(default_factory=ConstrainConfig)


class WorkflowAgent(Agent):
    default_response: str = Field(default="抱歉，我无法理解您的问题，请换一种方式表达")


class Branch(BaseModel):
    branch_id: str = Field("")
    bool_expression: Optional[str] = Field('True')


class LLMConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    template_content: List[Dict] = Field(default_factory=list)
    response_format_type: LLMResponseFormatType = Field(LLMResponseFormatType.Text)
    output_config: Dict[str, Any] = Field(default_factory=dict)
    enable_history: bool = Field(default=False)


class BaseMessage(BaseModel):
    role: str = Field("")
    content: Union[str, List[Union[str, Dict]]] = Field("")
    name: Optional[str] = Field("")


class Template(BaseModel):
    name: str = Field("")
    content: Union[List[Dict], List[BaseMessage], str] = Field(default_factory=list)
    filters: Optional[dict] = Field(default=None)


class IntentDetectionConfig(BaseModel):
    user_prompt: str = Field("")
    category_info: str = Field("")
    category_list: List[str] = Field(default_factory=list)
    intent_detection_template: Template = Field(default_factory=Template)
    category_name_list: List[str] = Field(default_factory=list)
    default_class: str = Field("")
    enable_history: bool = Field(False)
    enable_input: bool = Field(True)
    chat_history_max_turn: int = Field(3)
    example_content: List[str] = Field(default_factory=list)
    overrideable: bool = Field(False)
    enableKnowledges: bool = Field(False)
    enable_q2fewshot: bool = Field(True)
    enable_validation: bool = Field(True)
    recallThreshold: float = Field(0.9)
    levenshtein_ration: float = Field(0.8)
    q2label_few_shot_score: float = Field(0.5)
    model: ModelConfig = Field(default_factory=ModelConfig)


class FieldInfo(BaseModel):
    field_name: str = Field(default="")
    description: str = Field(default="")
    cn_field_name: str = Field(default="")
    required: bool = Field(default=False)
    default_value: Any = Field(default="")
    type: str = Field(default="string")


class QuestionerConfig(BaseModel):
    model: Optional[ModelConfig] = Field(default=None)
    response_type: str = Field(default="reply_directly")
    question_content: str = Field(default="")
    extract_fields_from_response: bool = Field(default=True)
    field_names: List[FieldInfo] = Field(default_factory=list)
    max_response: int = Field(default=3)
    with_chat_history: bool = Field(default=False)
    chat_history_max_rounds: int = Field(default=5)
    prompt_template: List[dict] = Field(default_factory=list)
    extra_prompt_for_fields_extraction: str = Field(default="")
    example_content: str = Field(default="")


class Component(BaseInfo):
    type: ComponentType = Field(ComponentType.COMPONENT_TYPE_EMPTY)
    type_version: Optional[str] = Field("")
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    branches: Optional[List[Branch]] = Field(default_factory=list)
    configs: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Connection(BaseModel):
    source: Union[str, List[str]] = Field("")
    branch_id: Optional[str] = Field("")
    target: str = Field("")


class BaseFlow(BaseModel):
    start_id: List[str] = Field(default_factory=list)
    end_id: List[str] = Field(default_factory=list)
    components: List[Component] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)


class Workflow(BaseFlow, BaseInfo):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    configs: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ExecSubWfConfig(BaseModel):
    sub_workflow_info: Optional[BaseInfo] = Field(default_factory=BaseInfo)


class LoopType(str, Enum):
    Array = BaseLoopType.Array.value
    Number = BaseLoopType.Number.value


class LoopInput(BaseModel):
    loop_type: Optional[str] = Field("")
    loop_number: Optional[Any] = Field(0)
    loop_array: Optional[Dict[str, Any]] = Field(default_factory=dict)
    bool_expression: Optional[Union[str, bool]] = Field("")
    intermediate_var: Dict[str, Union[str, Any]] = Field(default_factory=dict)


class LoopConfig(BaseModel):
    loop_body: BaseFlow = Field(default_factory=BaseFlow)


class SetVariableConfig(BaseModel):
    inter_variable: Dict[str, Any] = Field(default_factory=dict)


class TextEditorConfig(BaseModel):
    edit_type: Optional[TextEditorType] = Field(default=TextEditorType.CONCATENATION)
    delimiters: Optional[list[str]] = Field(default_factory=list)
    concatenate_format: Optional[str] = Field(default="")


class MergeGroupConfig(BaseModel):
    name: str = Field(default="")
    type: str = Field(default="")
    items: List[str] = Field(default_factory=list)


class VariMergeConfig(BaseModel):
    groups: List[MergeGroupConfig] = Field(default_factory=list)


class CodeLanguage(StrEnum):
    PYTHON3 = "python3"
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class ExceptHandlingMethod(StrEnum):
    BREAK = "break"
    RETURN_CONTENT = "return_content"
    EXECUTE_EXCEPT_STEP = "execute_exception_step"


class PluginType(StrEnum):
    CODE = "code"
    SERVICE = "service"


class ParamConfig(BaseModel):
    name: Optional[str] = Field(default="")
    type: Optional[str] = Field(default="")


class ExceptRouterConfig(BaseModel):
    default_router_id: str = Field(default="default")
    error_router_id: str = Field(default="branch_error")


class ExceptConfig(BaseModel):
    max_retries: Optional[int] = Field(default=0)
    timeout_seconds: Optional[int] = Field(default=300)
    except_handling_method: Optional[ExceptHandlingMethod] = Field(default=ExceptHandlingMethod.BREAK)
    return_content: Optional[dict] = Field(default_factory=dict)
    execute_exception_step: Optional[ExceptRouterConfig] = Field(default_factory=ExceptRouterConfig)


class CodeConfig(BaseModel):
    language: str = Field(default=CodeLanguage.PYTHON)
    execute_type: str = Field(default="remote")
    code: str = Field(default_factory=str)
    output_params: List[ParamConfig] = Field(default_factory=list)
    exception_config: ExceptConfig = Field(default_factory=ExceptConfig)


class Param(BaseModel):
    name: Optional[str] = Field("")
    description: Optional[str] = Field("")
    type: Optional[str] = Field("")
    required: Optional[bool] = Field(default=False)
    default_value: Optional[str] = Field(default=None)
    method: Optional[str] = Field(default="")
    runtime: Optional[bool] = Field(default=True)


class PluginCodeConfig(CodeConfig):
    tool_id: str = Field("")
    name: str = Field(default="")
    description: Optional[str] = Field("")
    input_params: List[Param] = Field(default_factory=list)


class ErrorBody(BaseModel):
    error_message: str = Field(default="")
    error_code: int = Field(default=0)


class RestfulApiSchema(BaseModel):
    tool_id: str = Field("")
    name: Optional[str] = Field("")
    description: Optional[str] = Field("")
    params: List[Param] = Field(default_factory=list)
    path: Optional[str] = Field("")
    headers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    method: Optional[str] = Field("")
    response: List[Param] = Field(default_factory=list)


class Plugin(BaseModel):
    plugin_id: str = Field(default="")
    plugin_name: str = Field("")
    plugin_description: str = Field("")
    plugin_type: str = Field("")
    tools: List[Dict[str, Any]] = Field(default_factory=dict)
    plugin_version: str = Field(default="")


class ToolCompConfig(BaseModel):
    type: Optional[str] = Field("")
    tool: Optional[Dict[str, Any]] = Field(default_factory=dict)
    exception_config: ExceptConfig = Field(default_factory=ExceptConfig)


def encode_to_json(m: BaseModel) -> str:
    return m.model_dump_json(by_alias=True)


T = TypeVar('T')


def decode_from_json(json_str: str, t: T):
    return t.model_validate_json(json_str)


class EndConfig(BaseModel):
    response_template: Optional[str] = Field(default_factory=str)
    stream_output: Optional[bool] = Field(False)


class UserInputElem(BaseModel):
    input_name: Optional[str] = Field("")
    description: Optional[str] = Field("")
    type: Optional[str] = Field("")
    required: Optional[bool] = Field(False)
    default: Optional[Any] = Field(None)


class UserInputsConfig(BaseModel):
    inputs: Optional[List[UserInputElem]] = Field(default_factory=list)


class UserOutputConfig(BaseModel):
    streaming: Optional[bool] = Field(False)
    output_message: Optional[str] = Field("")
