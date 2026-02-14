#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

TASK_NAME_LENGTH_MIN_LIMIT = 1
TASK_NAME_LENGTH_MAX_LIMIT = 32

TASK_DESC_LENGTH_MIN_LIMIT = 1
TASK_DESC_LENGTH_MAX_LIMIT = 256

TASK_CASES_LENGTH_MAX_LIMIT = 300
TASK_CASES_SIZE_MAX_LIMIT = 16 * 1024 * 1024

GET_JOBS_UPPER_BOUND = 50
GET_JOBS_MIN_LIMIT = 1
GET_JOBS_MAX_LIMIT = 50
GET_JOBS_LIMIT_DEFAULT = 10


class BaseResponse(BaseModel):
    code: int = Field(0, description="状态码")
    msg: str = Field("success", description="提示信息")


class PromptBase(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    created_by: str


class PromptSample(PromptBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    class Config:
        from_attributes = True  # 使用新的 from_attributes 代替 orm_mode


class PromptVersionBase(BaseModel):
    name: str
    content: str
    prompt_id: int
    version: int
    description: Optional[str] = None
    created_by: str


class PromptVersion(PromptVersionBase):
    id: int
    created_at: datetime
    is_current: bool = False

    class Config:
        from_attributes = True  # 使用新的 from_attributes 代替 orm_mode


class PromptWithVersions(PromptSample):
    versions: List[PromptVersion] = []

    class Config:
        from_attributes = True  # 使用新的 from_attributes 代替 orm_mode


# 枚举类型定义
class TemplateType(str, Enum):
    Normal = "normal"
    JinJa2 = "jinja2"


class ToolType(str, Enum):
    Function = "function"


class ToolChoiceType(str, Enum):
    None_ = "none"
    Auto = "auto"


class Role(str, Enum):
    System = "system"
    User = "user"
    Assistant = "assistant"
    Tool = "tool"
    Placeholder = "placeholder"


class ContentType(str, Enum):
    Text = "text"
    ImageURL = "image_url"


class VariableType(str, Enum):
    String = "string"
    Placeholder = "placeholder"
    Integer = "integer"
    Float = "float"
    Boolean = "boolean"
    Object = "object"


class Scenario(str, Enum):
    Default = "default"
    EvalTarget = "eval_target"


# 基础结构定义
class UserInfoDetail(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    nick_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None


class Function(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[str] = None  # JSON string
    parameters_mode: Optional[str] = "visual"


class Tool(BaseModel):
    type: Optional[ToolType] = None
    function: Optional[Function] = None


class ToolCallConfig(BaseModel):
    tool_choice: Optional[ToolChoiceType] = None


class ModelConfig(BaseModel):
    models_id: Optional[int] = None
    models_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    timeout: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    json_mode: Optional[bool] = None
    model_from: Optional[str] = None


class ImageURL(BaseModel):
    uri: Optional[str] = None
    url: Optional[str] = None


class ContentPart(BaseModel):
    type: Optional[ContentType] = None
    text: Optional[str] = None
    image_url: Optional[ImageURL] = None


class FunctionCall(BaseModel):
    name: Optional[str] = None
    arguments: Optional[str] = None


class ToolCall(BaseModel):
    index: Optional[int] = None
    id: Optional[str] = None
    type: Optional[ToolType] = None
    function_call: Optional[FunctionCall] = None


class VariableDef(BaseModel):
    key: Optional[str] = None
    desc: Optional[str] = None
    type: Optional[VariableType] = None


class Message(BaseModel):
    role: Optional[Role] = None
    reasoning_content: Optional[str] = None
    content: Optional[str] = None
    parts: Optional[List[ContentPart]] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    key: Optional[str] = None


class PromptTemplate(BaseModel):
    template_type: Optional[TemplateType] = None
    messages: Optional[List[Message]] = None
    variable_defs: Optional[List[VariableDef]] = None


# 核心结构定义
class PromptDetail(BaseModel):
    prompt_template: Optional[PromptTemplate] = None
    tools: Optional[List[Tool]] = None
    tool_call_config: Optional[ToolCallConfig] = None
    prompt_model_config: Optional[ModelConfig] = None


class AgentRelationObj(BaseModel):
    obj_id: Optional[str] = None
    obj_version: Optional[str] = None
    obj_name: Optional[str] = None
    obj_type_name: Optional[str] = None


class CommitInfo(BaseModel):
    version: Optional[str] = None
    base_version: Optional[str] = None
    description: Optional[str] = None
    committed_by: Optional[str] = None
    committed_by_name: Optional[str] = None
    committed_at: Optional[int] = None
    relation_obj: Optional[List[AgentRelationObj]] = None


class DraftInfo(BaseModel):
    user_id: Optional[str] = None
    space_id: Optional[str] = None
    base_version: Optional[str] = None
    is_draft_edited: Optional[bool] = None
    created_at: datetime = None
    updated_at: datetime = None


class PromptBasic(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    latest_version: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    latest_committed_at: Optional[datetime] = None


class PromptCommit(BaseModel):
    detail: Optional[PromptDetail] = None
    commit_info: Optional[CommitInfo] = None


class PromptDraft(BaseModel):
    detail: Optional[PromptDetail] = None
    draft_info: Optional[DraftInfo] = None


class TrafficEnv(BaseModel):
    open: bool = False
    env: str = ""


class Base(BaseModel):
    LogID: str = ""
    Caller: str = ""
    Addr: str = ""
    Client: str = ""
    TrafficEnv: Optional[TrafficEnv] = None
    Extra: Optional[Dict[str, str]] = None


class BaseResp(BaseModel):
    status_message: str = ""
    status_code: int = 0
    extra: Optional[Dict[str, str]] = None


# 顶级结构定义
class Prompt(BaseModel):
    id: Optional[int] = None
    workspace_id: Optional[int] = None
    prompt_key: Optional[str] = None
    prompt_basic: Optional[PromptBasic] = None
    prompt_draft: Optional[PromptDraft] = None
    prompt_commit: Optional[PromptCommit] = None
    relation_obj: Optional[List[AgentRelationObj]] = None


class CreatePromptRequest(BaseModel):
    updated_by: Optional[str] = None
    workspace_id: Optional[int] = None
    prompt_name: Optional[str] = None
    prompt_key: Optional[str] = None
    prompt_description: Optional[str] = None
    draft_detail: Optional[PromptDetail] = None
    Base: Optional[Base] = None
    prompt: Optional[Prompt] = None


class CreatePromptResponse(BaseModel):
    prompt_id: Optional[int] = None
    msg: str = ""
    code: int = 0


class ListPromptOrderBy(str, Enum):
    COMMITTED_AT = "committed_at"  # 按提交时间排序
    CREATED_AT = "created_at"  # 按创建时间排序
    NAME = "display_name"
    DESCRIPTION = "description"
    LATEST_VERSION = "latest_version"
    UPDATED_AT = "updated_at"
    CREATED_BY = "created_by_name"
    UPDATED_BY = "updated_by_name"
    LATEST_COMMITTED_TIME = "latest_committed_at"
    PROMPT_KEY = "prompt_key"


class PromptBasicMap(str, Enum):
    display_name = "name"
    description = "description"
    latest_version = "latest_version"
    created_by_name = "created_by"
    updated_by_name = "updated_by"
    created_at = "created_at"
    updated_at = "updated_at"
    latest_committed_at = "latest_commit_time"
    prompt_key = "prompt_key"


class ListPromptRequest(BaseModel):
    workspace_id: Optional[int] = None
    key_word: Optional[str] = None
    created_bys: Optional[List[str]] = None
    page_num: int = 1
    page_size: int = 20
    order_by: Optional[ListPromptOrderBy] = None
    asc: Optional[bool] = None
    Base: Optional[Base] = None  # 嵌套基础对象


class ListPromptResponse(BaseModel):
    prompts: Optional[List[Prompt]] = None
    users: Optional[List[UserInfoDetail]] = None
    total: Optional[int] = None
    msg: str = ""
    code: int = 0


class UpdatePromptRequest(BaseModel):
    prompt_id: Optional[int] = None
    workspace_id: Optional[int] = None
    prompt_name: Optional[str] = None
    prompt_description: Optional[str] = None
    Base: Optional[Base] = None


class UpdatePromptResponse(BaseModel):
    msg: str = ""
    code: int = 0


class GetPromptResponse(BaseModel):
    prompt: Optional[List[Prompt]] = None
    default_config: Optional[PromptDetail] = None
    msg: str = ""
    code: int = 0


class DeletePromptRequest(BaseModel):
    prompt_id: Optional[int] = None
    workspace_id: Optional[int] = None
    Base: Optional[Base] = None


class DeletePromptResponse(BaseModel):
    msg: str = ""
    code: int = 0


class ClonePromptRequest(BaseModel):
    user_id: str
    prompt_id: Optional[int] = None
    workspace_id: Optional[int] = None
    commit_version: Optional[str] = None
    cloned_prompt_name: Optional[str] = None
    cloned_prompt_key: Optional[str] = None
    cloned_prompt_description: Optional[str] = None
    Base: Optional[Base] = None


class ClonePromptResponse(BaseModel):
    cloned_prompt_id: Optional[int] = None
    msg: str = ""
    code: int = 0


class PromptDraftInput(BaseModel):
    prompt_draft: PromptDraft


class DraftInfoOutput(BaseModel):
    base_version: Optional[str] = None
    created_at: str
    is_draft_edited: bool
    updated_at: str
    user_id: str
    space_id: Optional[str] = None


class DraftPO(BaseModel):
    id: Optional[int] = None
    prompt_id: int
    user_id: str
    space_id: str
    template_type: str
    messages: str
    prompt_model_config: str
    variable_defs: str
    tools: str
    tool_call_config: str
    base_version: str
    is_draft_edited: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[int] = 0


class DraftSaveResponse(BaseResponse):
    draft_info: Optional[DraftInfoOutput] = None


class CommitRequest(BaseModel):
    commit_version: str
    commit_description: Optional[str] = None


class CommitResponse(BaseResponse):
    content: Optional[str] = None


class PromptSubmit(BaseModel):
    id: Optional[int] = None
    space_id: int = 0
    prompt_id: int
    prompt_key: str = ""
    template_type: str = "normal"
    messages: str
    prompt_model_config: str
    variable_defs: str
    tools: str
    tool_call_config: str
    version: str
    base_version: str = ""
    committed_by: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CommitListRequest(BaseModel):
    page_size: int = 10


class CommitListResponse(BaseResponse):
    prompt_commit_infos: Optional[List[CommitInfo]] = []


class RevertFromCommitRequest(BaseModel):
    commit_version_reverting_from: str


class RevertFromCommitResponse(BaseResponse):
    content: Optional[str] = None


class PromptQuery(BaseModel):
    prompt_id: int
    with_commit: bool = False
    commit_version: Optional[str] = None
    user_id: Optional[str] = None  # 用于查询草稿


class BatchGetPromptRequest(BaseModel):
    queries: List[PromptQuery]
    workspace_id: Optional[int] = None


class BatchPromptResponseItem(BaseModel):
    query: PromptQuery
    prompt: Optional[Prompt] = None
    error_code: Optional[int] = None
    error_msg: Optional[str] = None


class BatchGetPromptResponse(BaseResponse):
    items: List[BatchPromptResponseItem]


class LLMModelInfo(BaseModel):
    """LLM model config info"""
    id: int = Field(default=0)
    url: str = Field(default="", min_length=0, max_length=256)
    model: str = Field(default="", min_length=0, max_length=256)
    model_from: str = Field(default="", min_length=0, max_length=256)
    model_provider: str = Field(default="", min_length=0, max_length=256)
    type: str = Field(default="", min_length=0, max_length=256)
    headers: Optional[Dict[str, Any]] = Field(default={})
    model_source: str = Field(default="", min_length=0, max_length=256)
    api_key: str = Field(default="", min_length=0, max_length=256)


class JobInfo(BaseModel):

    created_at: Optional[str] = Field("", description="创建时间")
    desc: Optional[str] = Field("", description="任务描述")
    id: Optional[str] = Field("", description="任务ID")
    name: Optional[str] = Field("", description="任务名称")
    num_iter: Optional[int] = Field(0, description="迭代次数")
    job_type: str = Field(default="formal", description="任务类型：formal|draft")
    model_info: Optional[LLMModelInfo] = Field(default=None, alias="modelInfo")
    assistant_info: Optional[LLMModelInfo] = Field(default=None, alias="assistantInfo")


class JobDetailItem(BaseModel):
    error_msg: Optional[str] = Field("", description="错误信息")
    job_info: Optional[JobInfo] = Field(JobInfo(), description="任务信息")
    progress_rate: Optional[float] = Field(0.0, description="进度比率")
    status: Optional[str] = Field("", description="任务状态")
    time_cost: Optional[int] = Field(0, description="耗时（秒）")


class JobDetails(BaseModel):
    data: Optional[List[JobDetailItem]] = Field(JobDetailItem(), description="任务数据列表")
    failed_jobs: Optional[int] = Field(0, description="失败的任务数量")
    finished_jobs: Optional[int] = Field(0, description="完成的任务数量")
    running_jobs: Optional[int] = Field(0, description="运行中的任务数量")
    total_jobs: Optional[int] = Field(0, description="总任务数量")


class OptimizeTaskGetInfoResponse(BaseResponse):
    job_details: Optional[JobDetails] = Field(None, description="任务详细信息")


class OptimizeTaskCreationResponse(BaseResponse):
    jobInfo: Optional[JobInfo] = Field(None, description="任务信息")


class JobDraftCreateResponse(BaseResponse):
    draft_id: Optional[int] = Field(None, description="草稿id")

# 定义案例模型


class Case(BaseModel):
    inputs: Dict[str, Any] = Field(..., description="输入数据字典")
    label: Dict[str, Any] = Field(..., description="标签数据字典")

# 定义优化信息模型
class OptimizeInfo(BaseModel):
    num_iter: Optional[int] = Field(0, description="迭代次数")
    early_stop_score: Optional[float] = Field(None, description="早停分数")
    cases: Optional[List[Case]] = Field(default=[], description="案例列表")
    example_num: Optional[int] = Field(None, description="示例数量")
    placeholder: Optional[List[str]] = Field(None, description="占位符")
    llm_parallel: Optional[int] = Field(None, description="LLM并行数")
    user_compare_rules: Optional[str] = Field(None, description="用户比较规则")
    user_compare_options: Optional[str] = Field(None, description="用户比较选项")
    external_knowledge: Optional[str] = Field(None, description="外部知识")
    tools: Optional[List[Dict[str, Any]]] = Field([], description="代理工具")
    num_parallel: Optional[int] = Field(default=1, ge=1, le=10)
    num_examples: Optional[int] = Field(default=0, ge=0, le=10)
    num_cot_examples: Optional[int] = Field(default=0, ge=0, le=5)
    num_retires: Optional[int] = Field(default=5, ge=1, le=10)
    optimize_method: Optional[str] = Field(default="JOINT")
    evaluation_method: Optional[str] = Field(default="LLM")
    num_iterations: Optional[int] = Field(default=0)

    @field_validator('cases')
    @classmethod
    def validate_cases_length(cls, v):
        """校验cases数量不超过300条"""
        if v and len(v) > TASK_CASES_LENGTH_MAX_LIMIT:
            raise ValueError(f'cases数量不能超过300条，当前为{len(v)}条')
        return v

    @model_validator(mode='after')
    def validate_cases_size(self):
        """校验cases数据大小不超过16MB"""
        if self.cases:
            try:
                # 将cases转换为字典列表进行序列化
                cases_dicts = [case.dict() if hasattr(case, 'dict') else case for case in self.cases]
                cases_json = json.dumps(cases_dicts, ensure_ascii=False)
                cases_size = len(cases_json.encode('utf-8'))

                if cases_size > TASK_CASES_SIZE_MAX_LIMIT:
                    raise ValueError(f'cases数据大小不能超过16MB，当前为{cases_size / (1024 * 1024):.2f}MB')
            except (TypeError, ValueError, AttributeError) as e:
                raise ValueError(f'cases数据序列化错误: {str(e)}') from e
        return self


# 定义模型信息模型
class ModelInfo(BaseModel):
    model: str = Field(..., description="模型名称")
    model_source: str = Field(..., description="模型来源")
    headers: Optional[Dict[str, Any]] = Field(None, description="头部信息")


class OptimizeTaskCreationRequest(BaseModel):
    """Prompt optimization task creation request"""
    name: str = Field(min_length=TASK_NAME_LENGTH_MIN_LIMIT, max_length=TASK_NAME_LENGTH_MAX_LIMIT)
    desc: Optional[str] = Field(default="")
    raw_templates: Optional[str] = Field(default="", alias="rawTemplates")
    optimize_info: Optional[OptimizeInfo] = Field(default=None, alias="optimizeInfo")
    model_info: Optional[LLMModelInfo] = Field(default=None, alias="modelInfo")
    assistant_info: Optional[LLMModelInfo] = Field(default=None, alias="assistantInfo")
    agent_tools: Optional[List[Dict[str, Any]]] = Field(default=[], alias="agentTools")


class JobDraftResponse(BaseResponse):
    draft_id: Optional[int] = Field(None, description="草稿id")
    user_id: Optional[str] = Field("", description="用户id")
    space_id: Optional[str] = Field("", description="空间id")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    content: Optional[OptimizeTaskCreationRequest] = Field(None, description="job草稿内容")


# 定义优化任务创建请求模型
class OptimizeTaskDraft(OptimizeTaskCreationRequest):
    user_id: Optional[str] = None
    space_id: Optional[str] = None
    is_deleted: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# 定义HistoryItem模型
class HistoryItem(BaseModel):
    iteration_round: Optional[int] = Field(None, description="迭代轮次")
    optimized_prompt: Optional[str] = Field(None, description="优化后的提示")
    success_rate: Optional[float] = Field(None, description="成功率")
    evaluate_cases: Optional[List[Dict[str, Any]]] = Field(None, description="用例集运行情况")


# 定义Progress模型
class Progress(BaseModel):
    best_iteration: Optional[int] = Field(None, description="最佳迭代轮次")
    best_placeholder: Optional[Dict[str, Any]] = Field(None, description="最佳占位符")
    best_prompt: Optional[str] = Field(None, description="最佳提示")
    error_msg: Optional[str] = Field(None, description="错误信息")
    evaluation_method: Optional[str] = Field(None, description="评估方法")
    examples: Optional[List[str]] = Field(None, description="示例列表")
    filled_prompt: Optional[str] = Field(None, description="填充后的提示")
    job_info: Optional[JobInfo] = Field(None, description="任务信息")
    original_placeholder: Optional[Dict[str, Any]] = Field(None, description="原始占位符")
    original_prompt: Optional[str] = Field(None, description="原始提示")
    progress_rate: Optional[float] = Field(None, description="进度比率")
    status: Optional[str] = Field(None, description="状态")
    success_rate: Optional[float] = Field(None, description="成功率")
    time_cost: Optional[int] = Field(None, description="耗时")


# 定义响应模型
class OptimizeProgressResponse(BaseResponse):
    history: Optional[List[HistoryItem]] = Field(None, description="历史记录")
    progress: Optional[Progress] = Field(None, description="进度信息")
    optimizeInfo: Optional[OptimizeInfo] = Field(None, description="优化信息")
    message: Optional[str] = Field(None, description="提示信息")


class MetaTemplateTypeEnum(str, Enum):
    GENERAL_TEMPLATE = "GeneralTemplate-PanguUnify71B"
    PLAN_TEMPLATE = "PlanTemplate-PanguUnify71B"
    GENERAL_TEMPLATE_XIAOYI = "GeneralTemplate-Xiaoyi"
    PLAN_TEMPLATE_XIAOYI = "PlanTemplate-Xiaoyi"
    DEEPSEEKR1_PLANTEMPLATE_XIAOYI = "DeepSeekR1-PlanTemplate-XiaoYi"


class TemplateInfo(BaseModel):
    """TemplateInfo"""
    metaTemplateType: MetaTemplateTypeEnum = Field(default=MetaTemplateTypeEnum.DEEPSEEKR1_PLANTEMPLATE_XIAOYI)


class OptimizeTaskGetInfoRequest(BaseModel):
    """Definition of get jobs request rag."""
    id_list: List[str] = Field(default=[])


# prompt优化反馈信息
class OptFeedBackInfoRequest(BaseModel):
    modelInfo: LLMModelInfo = Field(default=LLMModelInfo(url="", token=""), description="大模型配置信息")
    prompt: str = Field(min_length=1, description="待优化prompt")
    feedback: str = Field(min_length=1, max_length=65535, description="反馈的要求")
    select_content_index: Optional[Tuple[int, int]] = Field(default=None, description="选中优化的初始和结束位置")
    insert_pos_index: Optional[int] = Field(default=None, description="选中优化插入的位置")
    stream: bool = Field(default=True, description="是否流式")
    templateInfo: TemplateInfo = Field(default=TemplateInfo(), description="元模版配置信息")


class OptBadCaseInfoRequest(BaseModel):
    modelInfo: LLMModelInfo = Field(default=LLMModelInfo(url="", token=""), description="大模型配置信息")
    prompt: str = Field(min_length=1, description="待优化prompt")
    badcases: Optional[List[dict]] = Field(default=True, description="优化要求")
    stream: bool = Field(default=True, description="是否流式")
    templateInfo: TemplateInfo = Field(default=TemplateInfo(), description="元模版配置信息")


class GetOptimizeResponse(BaseResponse):
    history: Optional[List[HistoryItem]] = Field(None, description="历史记录")
    msg: str = "Success"
    code: int = 0
