#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

AGENT_NAME_MAX_SIZE = 255


class AgentId(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    space_id: str = Field(alias="spaceId", min_length=1, max_length=100)
    agent_id: str = Field(alias="agentId", min_length=1, max_length=100)
    agent_version: Optional[str] = Field("", validation_alias=AliasChoices("agentVersion", "version"),
                                            serialization_alias="agent_version")


class AgentCreate(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=100)
    agent_name: str = Field(..., min_length=1, max_length=AGENT_NAME_MAX_SIZE, title="agent name", alias="name")
    description: str = Field(..., min_length=1, max_length=500, title="agent description", alias="desc")
    icon: str = Field(..., max_length=2000)
    model_config = ConfigDict(populate_by_name=True)
    agent_type: str = Field(..., min_length=1, max_length=30, alias="type")


class AgentResponseCreate(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=100, alias="id")
    model_config = ConfigDict(populate_by_name=True)


class AgentUpdate(AgentCreate):
    agent_id: str = Field(..., min_length=1, max_length=100, alias="id")
    model_config = ConfigDict(populate_by_name=True)


class AgentGet(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=100)
    agent_id: str = Field(..., min_length=1, max_length=100)


class AgentPlugin(BaseModel):
    plugin_id: str = Field(..., min_length=1, max_length=100)
    tool_id: str = Field(..., min_length=1, max_length=100)
    plugin_name: Optional[str] = Field(None, max_length=100)
    tool_name: Optional[str] = Field(None, max_length=100)
    plugin_version: Optional[str] = Field("draft", max_length=100)


class AgentWorkflow(BaseModel):
    workflow_id: str = Field(..., min_length=1, max_length=100, alias="id")
    workflow_version: str = Field(..., min_length=1, max_length=100, alias="version")
    workflow_name: str = Field(..., min_length=1, max_length=100, alias="name")
    description: str = Field(..., min_length=1, max_length=500)
    model_config = ConfigDict(populate_by_name=True)


class AgentModelInfo(BaseModel):
    api_key: Optional[str] = Field(None)
    api_base: Optional[str] = Field(None, max_length=500)
    model_id: Optional[int] = Field(None)
    model_name: str = Field(..., min_length=1, max_length=100)
    model_type: str = Field(..., min_length=1, max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    streaming: bool = Field(default=False)
    max_tokens: int = Field(default=4096, ge=1)
    timeout: float = Field(default=4096, ge=1)


class AgentModel(BaseModel):
    model_provider: Optional[str] = Field("", min_length=0, max_length=100)
    model_info: AgentModelInfo


class AgentPromptTemplate(BaseModel):
    role: str = Field(..., min_length=1, max_length=100)
    content: Optional[str] = Field("", min_length=0, max_length=5000)


class AgentConstraint(BaseModel):
    reserved_max_chat_rounds: int = Field(10, ge=1, le=50, description="最大的对话保留轮次")
    max_iteration: int = Field(5, ge=1, le=50, description="最大迭代次数")


class MemoryVariableConfig(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    enabled: Optional[bool] = True


class MemoryBaseConfig(BaseModel):
    mdb_id: str
    name: str
    embedding_model_config_id: int
    llm_model_config_id: int
    description: Optional[str] = None


class AgentMemoryConfig(BaseModel):
    max_tokens: int = Field(default=1000, ge=1, le=5000)
    variable_config: Optional[List[MemoryVariableConfig]] | None = None
    longterm_memory_config: bool | None = False
    user_profile_config: bool | None = False
    semantic_memory_config: bool | None = False
    episodic_memory_config: bool | None = False
    summary_memory_config: bool | None = False
    memory_base: Optional[MemoryBaseConfig] | None = None


class AgentDisplayInfo(AgentCreate):
    agent_id: str = Field(..., min_length=1, max_length=100, alias="id")
    agent_version: Optional[str] = Field(None, max_length=100, alias="version")
    configs: Dict[str, Any] = Field(default_factory=dict)
    edit_mode: str = Field(..., max_length=100, alias="mode")
    plugins: list[AgentPlugin] = Field(default_factory=list)
    workflows: list[AgentWorkflow] = Field(default_factory=list)
    model: AgentModel
    prompt_template_name: str = Field("", max_length=100)
    prompt_template: list[AgentPromptTemplate] = Field(default_factory=list)
    constraint: AgentConstraint
    auto_generated_prompt: str = Field("", max_length=2000)
    prompt_tuning: dict[str, Any] = Field(default_factory=dict)
    triggers: list[str] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)
    memory: AgentMemoryConfig
    opening_remarks: str = Field("", max_length=2000)
    default_response: Optional[str] = Field("", max_length=2000, description="Agent默认响应，当无法理解用户输入时使用")
    model_config = ConfigDict(populate_by_name=True)


# 基础分页请求模型
class AgentBaseRequest(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=100)
    sort_by: Optional[str] = Field("update_time", description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序方向")
    page: Optional[int] = Field(1, ge=1, le=1000, description="页码")
    page_size: Optional[int] = Field(10, ge=1, le=1000, description="每页大小")


class AgentList(AgentBaseRequest):
    pass


class AgentPublish(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=100)
    agent_id: str = Field(..., min_length=1, max_length=100, alias="id")
    agent_version: str = Field(..., min_length=1, max_length=100, alias="version")
    version_description: str = Field(..., min_length=1, max_length=500, alias="description")
    model_config = ConfigDict(populate_by_name=True)


class AgentGetVersion(AgentGet):
    agent_version: Optional[str] = Field(None, max_length=100, alias="version")
    model_config = ConfigDict(populate_by_name=True)


class AgentSearchSortBy(str, Enum):
    """智能体搜索排序字段枚举"""
    name = "agent_name"
    create_time = "create_time"
    update_time = "update_time"


class AgentSearchSortOrder(str, Enum):
    """智能体搜索排序方向枚举"""
    asc = "asc"
    desc = "desc"


class AgentSearchRequest(BaseModel):
    """智能体搜索请求模型"""
    space_id: str = Field(..., min_length=1, max_length=100)
    search_term: Optional[str] = Field("", description="搜索关键词（支持名称、描述）")
    status_filter: Optional[str] = Field("all", description="状态过滤")
    sort_by: Optional[AgentSearchSortBy] = Field(AgentSearchSortBy.update_time, description="排序字段")
    sort_order: Optional[AgentSearchSortOrder] = Field(AgentSearchSortOrder.desc, description="排序方向")
    page: Optional[int] = Field(1, ge=1, description="页码")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="每页大小")


class AgentSearchResponse(BaseModel):
    """智能体搜索响应模型"""
    agent_items: List[Dict[str, Any]] = Field(..., description="智能体列表")
    pagination: Dict[str, Any] = Field(..., description="分页信息")
    search_term: Optional[str] = Field(None, description="搜索关键词")
    filters: Dict[str, Any] = Field(default_factory=dict, description="应用的过滤器")


class AgentCopy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    space_id: str = Field(..., min_length=1, max_length=100)
    agent_id: str = Field(..., alias="id", min_length=1, max_length=100)
    agent_version: Optional[str] = Field(None, alias="version", max_length=100)


class AgentVersionListRequest(BaseModel):
    """智能体版本列表请求模型"""
    space_id: str = Field(..., min_length=1, max_length=100)
    agent_id: str = Field(..., min_length=1, max_length=100)


class AgentVersionInfo(BaseModel):
    """智能体版本信息模型"""
    agent_version: str = Field(..., description="版本号")
    version_description: str = Field(..., description="版本描述")
    create_time: int = Field(..., description="创建时间")


class AgentVersionListResponse(BaseModel):
    """智能体版本列表响应模型"""
    agent_id: str = Field(..., description="智能体ID")
    versions: List[AgentVersionInfo] = Field(..., description="版本列表")


class AgentResponsePublish(BaseModel):
    """智能体发布响应模型"""
    agent_id: str = Field(..., description="智能体ID")
    success: bool = Field(..., description="发布是否成功")


class AgentUpdateMemory(AgentUpdate):  # 假设你有 AgentUpdate 基类
    memory_config: AgentMemoryConfig
    model_config = ConfigDict(populate_by_name=True)


class AgentExportRequest(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=100)
    agent_id: str = Field(..., min_length=1, max_length=100)
    agent_version: Optional[str] = Field(None, max_length=100)


class AgentDependencies(BaseModel):
    workflows: List[Dict[str, Any]] = Field(default_factory=list)
    plugins: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_bases: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_templates: List[Dict[str, Any]] = Field(default_factory=list)


class AgentExportMetadata(BaseModel):
    export_time: str
    export_by: str
    agent_studio_version: Optional[str] = None


class ModelReference(BaseModel):
    """
    模型配置模板，用于跨环境迁移和运行时加载
    
    包含完整的模型配置信息，支持后续运行时进行环境变量注入。
    字段值可以是字符串、数字，或环境变量占位符如 "${ENV_NAME}" "${ENV_NAME:-default}"
    """
    provider: str
    model_type: str
    name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # 运行时注入，导出时为 null
    timeout: int = 300
    parameters: Optional[Dict[str, Any]] = None


class AgentExportData(BaseModel):
    version: str = ""
    agent: Dict[str, Any]
    dependencies: AgentDependencies
    metadata: AgentExportMetadata
    model_references: Optional[Dict[str, ModelReference]] = None


class AgentImportRequest(BaseModel):
    space_id: str = Field(..., min_length=1, max_length=100)
    import_data: AgentExportData
    overwrite: bool = Field(False)
