#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Literal, List, Optional, Any, Dict
from pydantic import BaseModel, Field, model_validator

MAX_TEMPLATE_CONTENT_LENGTH = 5 * 1000 * 1000
MAX_TEMPLATE_DESC_LENGTH = 2000
MAX_TEMPLATE_FILE_NAME_LENGTH = 255
MAX_TEMPLATE_NAME_LENGTH = 255
WebSearchProviderName = Literal[
    "xunfei",
    "petal",
    "tavily",
    "google",
    "jina",
    "serper",
    "bocha",
    "perplexity",
    "custom",
]


class WebSearchConfig(BaseModel):
    web_search_config_id: int = Field(description="Web搜索引擎ID")
    max_web_search_results: int = Field(default=5, ge=1, le=10, description="一次网页搜索的最大返回结果数量")


class LocalSearchConfig(BaseModel):
    local_search_config_ids: List[str] = Field(default=[], description="本地知识库ID列表")
    max_local_search_results: int = Field(default=5, ge=1, le=10, description="最大本地搜索结果数量")
    recall_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="知识库检索阈值")


class DeepSearchRequest(BaseModel):
    space_id: str = Field(..., description="用户空间ID")
    conversation_id: str = Field(..., description="请求对话ID")
    message: str = Field(..., description="用户请求查询或者人机交互时的反馈")
    workflow_human_in_the_loop: bool = Field(default=True, description="是否启用人机交互")
    outliner_max_section_num: int = Field(default=5, ge=1, le=10, description="最大规划章节数量，取值范围:[1,10]")
    source_tracer_research_trace_source_switch: bool = Field(default=True, description="溯源功能开关")
    source_tracer_source_tracer_infer_switch: bool = Field(default=True, description="溯源推理功能开关")
    info_collector_search_method: Literal["web", "local", "all"] = Field(
        default="web",
        description=(
            "搜索方式："
            "web: 联网搜索；"
            "local: 本地搜索工具搜索；"
            "all: 联网+本地融合搜索"
        ),
    )
    general_model_config_id: int = Field(..., description="通用模型配置ID")
    web_search_config: WebSearchConfig = Field(
        default=None, description="Web搜索引擎配置，和本地知识库配置至少选择一个"
    )
    local_search_config: Optional[LocalSearchConfig] = Field(
        default=None, description="本地知识库配置，和Web搜索引擎配置至少选择一个"
    )
    template_id: int = Field(default=-1, description="报告模板ID（可选）")
    interrupt_feedback: Literal["", "accepted", "cancel", "revise_comment", "revise_outline"] = Field(
        default="", description="中断反馈标识（可选）"
    )
    search_mode: Literal["research", "search"] = Field(default="research", description="生成研究报告还是生成答案")
    outline_interaction_enabled: bool = Field(default=False, description="大纲交互开关")
    outline_interaction_max_rounds: Optional[int] = Field(default=None, ge=1, description="大纲交互最大轮数")
    web_search_max_qps: float = Field(default=0, ge=0, description="联网搜索最大 QPS，0 表示不限流，支持浮点数如 0.5 表示每 2 秒 1 个请求")
    # 高级配置模型 ID（可选）
    plan_understanding_model_id: Optional[int] = Field(default=None, description="计划理解模型ID（可选）")
    info_collecting_model_id: Optional[int] = Field(default=None, description="信息收集模型ID（可选）")
    writing_checking_model_id: Optional[int] = Field(default=None, description="写作检查模型ID（可选）")
    vlm_model_config_id: Optional[int] = Field(default=None, description="VLM图表生成模型ID（可选）")
    vlm_chart_generator_enable: bool = Field(default=False, description="是否启用VLM图表生成")
    vlm_chart_generator_max_iterations: int = Field(
        default=1,
        description="VLM图表生成最大迭代次数，0表示不进行VLM迭代",
    )
    execution_method: Literal["parallel", "dependency_driving"] = Field(default="parallel",
                                                                         description="执行方法："
                                                                                     "parallel: 并行工作流执行"
                                                                                     "dependency_driving: 依赖驱动工作流执行")
    # 报告局部改写配置
    user_feedback_processor_enable: Optional[bool] = Field(default=None, description="是否启用报告后局部优化")
    user_feedback_processor_max_interactions: Optional[int] = Field(default=None, description="最大交互轮次")


class DeepSearchSearchRunLLMConfig(BaseModel):
    model_name: str = Field(..., min_length=1, description="Search mode LLM model name")
    model_type: str = Field(default="openai", min_length=1, description="Search mode LLM provider type")
    base_url: str = Field(..., min_length=1, description="Search mode LLM base URL")
    api_key: str = Field(..., min_length=1, description="Search mode LLM API key")


class DeepSearchSearchRunMilvusConfig(BaseModel):
    embedder_api_key: str = Field(..., min_length=1, description="Milvus embedder API key")
    embedder_base_url: str = Field(..., min_length=1, description="Milvus embedder base URL")
    embedder_model_name: Optional[str] = Field(default=None, description="Milvus embedder model name")
    milvus_host: Optional[str] = Field(default=None, description="Milvus host")
    milvus_port: Optional[int] = Field(default=None, description="Milvus port")
    database_name: Optional[str] = Field(default=None, description="Milvus database name")
    collection_name: Optional[str] = Field(default=None, description="Milvus collection name")
    embedder_timeout: Optional[int] = Field(default=None, description="Embedder timeout in seconds")
    host: Optional[str] = Field(default=None, description="Legacy Milvus host")
    port: Optional[int] = Field(default=None, description="Legacy Milvus port")

    @model_validator(mode="after")
    def normalize_legacy_host_fields(self):
        if self.milvus_host is None and self.host is not None:
            self.milvus_host = self.host
        if self.milvus_port is None and self.port is not None:
            self.milvus_port = self.port
        self.host = None
        self.port = None
        return self


class DeepSearchSearchRunWebSearchEngineConfig(BaseModel):
    """Telemetry web-search provider configuration for search-mode runs."""

    search_engine_name: str = Field(..., min_length=1, max_length=255, description="Search provider name")
    search_api_key: str = Field(..., min_length=1, max_length=255, description="Search provider API key")
    search_url: Optional[str] = Field(default=None, max_length=2048, description="Optional search endpoint")
    max_web_search_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum results returned per web search",
    )
    extension: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific search options")


class DeepSearchSearchRunWebFetchProviderConfig(BaseModel):
    """Telemetry web-fetch provider configuration for search-mode runs."""

    provider_name: Literal["jina"] = Field(..., description="Fetch provider name")
    api_key: str = Field(..., min_length=1, max_length=255, description="Fetch provider API key")
    base_url: Optional[str] = Field(default=None, max_length=2048, description="Optional fetch endpoint")
    extension: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific fetch options")


class DeepSearchSearchWorkflowPerQuestionParams(BaseModel):
    time_limit: Optional[int] = Field(default=None, description="Workflow time limit in seconds")
    actions_explored_limit: Optional[int] = Field(default=None, description="Maximum actions explored per question")


class DeepSearchSearchRunRequest(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")
    search_mode: Literal["search"] = Field(default="search", description="必须为 search")
    enable_question_router: bool = Field(default=True, description="是否启用问题路由到 ReAct")
    run_id: Optional[str] = Field(default=None, description="可选的外部 run 标识")
    query: str = Field(..., min_length=1, description="Search-mode query")
    llm: DeepSearchSearchRunLLMConfig = Field(..., description="Search-mode LLM config")
    tool_map: Literal["search_fetch", "retrieve"] = Field(..., description="Search tool strategy")
    web_search_engine_config: Optional[DeepSearchSearchRunWebSearchEngineConfig] = Field(
        default=None,
        description="Web search provider config (required with web_fetch_provider_config for search_fetch)",
    )
    web_fetch_provider_config: Optional[DeepSearchSearchRunWebFetchProviderConfig] = Field(
        default=None,
        description="Web fetch provider config (required with web_search_engine_config for search_fetch)",
    )
    milvus: Optional[DeepSearchSearchRunMilvusConfig] = Field(
        default=None,
        description="Milvus config（retrieve 必填）",
    )
    search_workflow_per_question_params: Optional[DeepSearchSearchWorkflowPerQuestionParams] = Field(
        default=None,
        description="Workflow runtime limits for search-mode runs",
    )


class DeepSearchSearchRunResponse(BaseModel):
    run_id: str = Field(..., description="Run ID")
    status: str = Field(..., description="Run status")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")


class DeepSearchTelemetryResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Telemetry envelopes")


class TemplateImportRequest(BaseModel):
    """Request for importing a template"""
    space_id: str = Field(..., description="Space ID")
    file_name: str = Field(
        ..., min_length=1, max_length=MAX_TEMPLATE_FILE_NAME_LENGTH,
        description="File name with extension"
    )
    file_stream: str = Field(
        ..., min_length=1, max_length=MAX_TEMPLATE_CONTENT_LENGTH,
        description="Base64 encoded file content"
    )
    is_template: bool = Field(..., description="Whether it's a template or sample report")
    template_name: str = Field(
        ..., min_length=1, max_length=MAX_TEMPLATE_NAME_LENGTH,
        description="Template name"
    )
    template_desc: str = Field(
        ..., max_length=MAX_TEMPLATE_DESC_LENGTH,
        description="Template description"
    )
    model_config_id: int = Field(..., description="Model configuration ID")


class TemplateUpdateRequest(BaseModel):
    """Request for updating a specific template"""
    space_id: str = Field(..., description="Space ID")
    template_id: int = Field(..., description="Template ID")
    template_content: str = Field(
        ..., min_length=1, max_length=MAX_TEMPLATE_CONTENT_LENGTH,
        description="Base64 encoded template content"
    )
    template_name: str = Field(
        ..., min_length=1, max_length=MAX_TEMPLATE_NAME_LENGTH,
        description="Template name"
    )
    template_desc: str = Field(
        ..., max_length=MAX_TEMPLATE_DESC_LENGTH,
        description="Template description"
    )


# Response Models
class TemplateBaseResponse(BaseModel):
    """Base response model"""
    code: int = Field(0, description="Error code (0: success, 1: failure)")
    msg: str = Field("success", description="Result message")


class TemplateImportResponse(TemplateBaseResponse):
    """Response for importing a template"""
    template_id: Optional[int] = Field(None, description="Template ID")


class TemplateUpdateResponse(TemplateBaseResponse):
    """Response for updating a specific template"""
    template_id: Optional[int] = Field(None, description="Template ID")


class TemplateDeleteResponse(TemplateBaseResponse):
    """Response for deleting a specific template"""
    pass


class TemplateGetResponse(TemplateBaseResponse):
    """Response for getting a specific template"""
    template_content: str = Field("", description="Base64 encoded template content")


class TemplateListItem(BaseModel):
    """Template list item"""
    template_name: str = Field(..., description="Template name")
    template_desc: str = Field(..., description="Template description")
    template_id: int = Field(..., description="Template ID")
    create_time: str = Field(..., description="Creation time")


class TemplateListResponse(TemplateBaseResponse):
    """Response for listing templates"""
    data: List[TemplateListItem] = Field(..., description="List of templates")


class WebSearchEngineBasicRequestDTO(BaseModel):
    '''web搜索引擎基类对象'''
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")


class WebSearchEngineCreateRequestDTO(WebSearchEngineBasicRequestDTO):
    '''web搜索引擎请求对象'''
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")
    search_engine_name: str = Field(..., min_length=1, max_length=255, description="搜索引擎名称")
    search_api_key: str = Field(..., min_length=1, max_length=255, description="搜索引擎访问api_key")
    search_url: str = Field(..., min_length=1, max_length=255, description="搜索引擎url")
    extension: dict = Field(default_factory=dict, description="搜索引擎扩展配置")
    is_active: bool = Field(default=True, description="搜索引擎是否禁用")


class WebSearchEngineGetRequestDTO(WebSearchEngineBasicRequestDTO):
    '''获取指定web搜索引擎请求对象'''
    web_search_engine_id: int = Field(..., description="搜索引擎id")


class WebSearchEngineListRequestDTO(WebSearchEngineBasicRequestDTO):
    '''获取搜索引擎列表请求对象'''
    pass


class WebSearchEngineDeleteRequestDTO(WebSearchEngineBasicRequestDTO):
    '''删除指定web搜索引擎请求对象'''
    web_search_engine_id: int = Field(..., description="搜索引擎id")


class WebSearchEngineUpdateRequestDTO(WebSearchEngineBasicRequestDTO):
    '''更新指定web搜索引擎对象'''
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")
    web_search_engine_id: int = Field(..., description="搜素引擎id")
    search_engine_name: Optional[str] = Field(None, min_length=1, max_length=255, description="搜索引擎名称")
    search_api_key: Optional[str] = Field(None, min_length=1, max_length=255, description="搜索引擎访问api_key")
    search_url: Optional[str] = Field(None, min_length=1, max_length=255, description="搜索引擎url")
    extension: Optional[dict] = Field(default_factory=dict, description="搜索引擎扩展配置")
    is_active: Optional[bool] = Field(default=True, description="搜索引擎是否禁用")


class BasicResponseDTO(BaseModel):
    '''web搜索引擎返回对象基类'''
    code: int = Field(default=200, description="是否成功")
    msg: str = Field(default='success', min_length=1, max_length=255, description="结果信息")


class WebSearchEngineCreateRes(BasicResponseDTO):
    '''创建web搜索引擎返回对象'''
    web_search_engine_id: int = Field(..., description="web搜索引擎id")


class WebSearchEngineGetRes(BasicResponseDTO):
    '''获取指定搜索引擎'''
    search_engine_name: str = Field(..., min_length=1, max_length=255, description="搜索引擎名称")
    search_url: str = Field(..., min_length=1, max_length=255, description="搜索引擎url")
    extension: Optional[dict[str, Any]] = Field(default_factory=dict, description="搜索引擎扩展配置")
    is_active: Optional[bool] = Field(default=True, description="搜索引擎是否禁用")


class WebSearchEngineDetail(BasicResponseDTO):
    '''获取指定搜索引擎详细信息'''
    search_engine_name: str = Field(..., min_length=1, max_length=255, description="搜索引擎名称")
    search_url: str = Field(..., min_length=1, max_length=255, description="搜索引擎url")
    search_api_key: str = Field(..., min_length=1, max_length=255, description="搜索引擎访问api_key")


class WebSearchEngineItem(BaseModel):
    '''web搜索引擎条目'''
    search_engine_name: str = Field(..., min_length=1, max_length=255, description="搜索引擎名称")
    search_url: str = Field(..., min_length=1, max_length=255, description="搜索引擎url")
    web_search_engine_id: int = Field(..., description="搜索引擎id")
    create_time: str = Field(..., min_length=1, max_length=255, description="模板创建时间")
    extension: Optional[dict[str, Any]] = Field(default_factory=dict, description="搜索引擎扩展配置")
    is_active: Optional[bool] = Field(default=True, description="搜索引擎是否禁用")


class WebSearchEngineListRes(BasicResponseDTO):
    '''获取搜索引擎列表'''
    data: List[WebSearchEngineItem] = Field(default=[], description="搜索引擎列表")


class WebSearchEngineDeleteRes(BasicResponseDTO):
    '''删除指定搜索引擎返回对象'''
    pass


class WebSearchEngineUpdateRes(BasicResponseDTO):
    '''修改指定搜索引擎'''
    web_search_engine_id: int = Field(default=0, description="搜索引擎id")


class WebSearchEngineAccessRequestDTO(BaseModel):
    '''web搜索引擎基类对象'''
    query: str = Field(..., description="用户query")


class WebSearchEngineAccessRes(BasicResponseDTO):
    '''测试指定搜索引擎'''
    search_engine_name: str = Field(..., min_length=1, max_length=255, description="搜索引擎名称")
    datas: List[dict[str, Any]] = Field(default=[], description="搜索引擎返回结果，key不固定")


class TaskSpaceWebSearchProviderAccessRequestDTO(BaseModel):
    """Request-only test of a browser-local web-search provider configuration."""
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")
    search_engine_name: WebSearchProviderName = Field(..., description="待测试的搜索服务商")
    search_api_key: str = Field(..., min_length=1, max_length=255, description="搜索服务商 API Key")
    search_url: Optional[str] = Field(default=None, max_length=2048, description="可选搜索服务地址")
    extension: Dict[str, Any] = Field(default_factory=dict, description="服务商扩展配置")
    query: str = Field(default="Latest AI developments", min_length=1, max_length=500, description="测试查询")


class TaskSpaceWebFetchProviderAccessRequestDTO(BaseModel):
    """Request-only test of a browser-local web-fetch provider configuration."""
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")
    provider_name: Literal["jina"] = Field(..., description="待测试的抓取服务商")
    api_key: str = Field(..., min_length=1, max_length=255, description="抓取服务商 API Key")
    base_url: Optional[str] = Field(default=None, max_length=2048, description="可选抓取服务地址")
    extension: Dict[str, Any] = Field(default_factory=dict, description="服务商扩展配置")
    test_url: str = Field(default="https://example.com", min_length=1, max_length=2048, description="测试抓取 URL")


class TaskSpaceProviderAccessRes(BasicResponseDTO):
    """Result of a non-persistent task-space provider connection test."""
    provider_name: str = Field(..., min_length=1, max_length=255, description="已测试的服务商")
    datas: List[dict[str, Any]] = Field(default=[], description="服务商返回结果")


class ReportConvertFinalResult(BaseModel):
    response_content: str = Field(..., description='报告内容（Markdown格式）')
    citation_messages: Optional[Any] = Field(default=None, description='引用数据')
    infer_messages: Optional[List[Any]] = Field(default_factory=list, description='推理图谱列表')
    chart_messages: Optional[List[Any]] = Field(default_factory=list, description='VLM图表结果')


class ReportConvertReq(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")
    final_result: ReportConvertFinalResult = Field(..., description='报告最终结果')
    convert_type: str = Field(..., description='转换类型，可选docx或html')


class ReportConvertRes(BaseModel):
    code: int = Field(..., description='错误码')
    msg: str = Field(..., description='结果信息')
    convert_content: str = Field(..., description='base64编码过的转换格式后报告内容')
