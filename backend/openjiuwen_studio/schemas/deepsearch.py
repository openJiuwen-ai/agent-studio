#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Literal, List, Optional, Any
from pydantic import BaseModel, Field


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
    # 高级配置模型 ID（可选）
    plan_understanding_model_id: Optional[int] = Field(default=None, description="计划理解模型ID（可选）")
    info_collecting_model_id: Optional[int] = Field(default=None, description="信息收集模型ID（可选）")
    writing_checking_model_id: Optional[int] = Field(default=None, description="写作检查模型ID（可选）")


class TemplateImportRequest(BaseModel):
    """Request for importing a template"""
    space_id: str = Field(..., description="Space ID")
    file_name: str = Field(..., description="File name with extension")
    file_stream: str = Field(..., description="Base64 encoded file content")
    is_template: bool = Field(..., description="Whether it's a template or sample report")
    template_name: str = Field(..., description="Template name")
    template_desc: str = Field(..., description="Template description")
    model_config_id: int = Field(..., description="Model configuration ID")


class TemplateUpdateRequest(BaseModel):
    """Request for updating a specific template"""
    space_id: str = Field(..., description="Space ID")
    template_id: int = Field(..., description="Template ID")
    template_content: str = Field(..., description="Base64 encoded template content")
    template_name: str = Field(..., description="Template name")
    template_desc: str = Field(..., description="Template description")


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


class ReportConvertReq(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=255, description="用户空间id")
    report_content: str = Field(..., min_length=1, max_length=1000 * 1000, description='base64编码过的原markdown报告内容')
    convert_type: str = Field(..., description='转换类型，可选docx或html')


class ReportConvertRes(BaseModel):
    code: int = Field(..., description='错误码')
    msg: str = Field(..., description='结果信息')
    convert_content: str = Field(..., description='base64编码过的转换格式后报告内容')
