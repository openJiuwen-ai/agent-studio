#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import re
from enum import IntEnum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


# 知识库名称中不允许的特殊字符正则表达式
INVALID_KB_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_kb_name(name: str) -> str:
    """验证知识库名称，不允许包含特殊字符"""
    if not name or not name.strip():
        raise ValueError("知识库名称不能为空")

    trimmed_name = name.strip()

    if trimmed_name != name:
        raise ValueError("知识库名称不能以空格开头或结尾")

    if INVALID_KB_NAME_CHARS.search(trimmed_name):
        raise ValueError('知识库名称不能包含以下字符: < > : " / \\ | ? * 以及控制字符')

    return name


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=2000, description="知识库描述")
    embedding_model_config_id: int = Field(
        ..., description="Embedding 模型配置ID（必填，知识库创建时选择，后续不可更改）"
    )
    config: Optional[Dict[str, Any]] = Field(None, description="知识库配置信息")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证知识库名称"""
        return validate_kb_name(v)


class KnowledgeBaseResponseCreate(BaseModel):
    """创建知识库响应"""

    kb_id: str = Field(..., alias="id", description="知识库ID")

    class Config:
        populate_by_name = True


class KnowledgeBaseGet(BaseModel):
    """获取/删除知识库请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    index_manager_type: str | None = Field(
        default=None, description="Whether Chroma or Milvus is used for indexing"
    )


class KnowledgeBaseUpdateRequest(BaseModel):
    """更新知识库请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    name: str = Field(..., min_length=1, max_length=100, description="新的名字")
    desc: str = Field(..., description="新的描述")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证知识库名称"""
        return validate_kb_name(v)


class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""

    kb_id: str = Field(..., alias="id")
    space_id: str = Field(..., description="空间ID")
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    embedding_model_config_id: Optional[int] = Field(None, description="Embedding 模型配置ID")
    config: Optional[Dict[str, Any]] = Field(None, description="知识库配置")
    create_time: Optional[int] = Field(None, description="创建时间")
    update_time: Optional[int] = Field(None, description="更新时间")
    has_graph_enhancement: Optional[bool] = Field(None, description="是否有图增强构建的文档")

    class Config:
        populate_by_name = True


class DocumentUploadRequest(BaseModel):
    """文档上传请求（表单字段）"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文档元数据（可选）")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""

    doc_id: str = Field(..., alias="id", description="文档ID")
    name: str = Field(..., description="文档名称")
    file_size: int = Field(..., description="文件大小（字节）")
    status: str = Field(..., description="文档状态")

    class Config:
        populate_by_name = True


class DocumentUploadBatchResponse(BaseModel):
    """批量文档上传响应"""

    success_count: int = Field(..., description="成功上传的文档数量")
    failed_count: int = Field(..., description="上传失败的文档数量")
    documents: list[DocumentUploadResponse] = Field(..., description="上传结果列表")


class KnowledgeBaseSearchRequest(BaseModel):
    """知识库查询请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="查询词（查询词完整出现在知识库名称或描述中，大小写不敏感）",
    )
    page: Optional[int] = Field(1, ge=1, description="页码，从1开始")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="每页大小，最大100")


class KnowledgeBaseSearchResponse(BaseModel):
    """知识库查询响应"""

    knowledge_bases: list[KnowledgeBaseInfo] = Field(..., description="匹配的知识库列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


class KnowledgeBaseListRequest(BaseModel):
    """知识库列表请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    page: int = Field(1, ge=1, description="页码，默认1")
    size: int = Field(10, ge=1, le=100, description="每页大小，默认10")


class KnowledgeBaseListItem(BaseModel):
    """知识库列表项"""

    name: str = Field(..., description="知识库名称")
    desc: str | None = Field(None, description="知识库描述")
    id: str = Field(..., description="知识库ID")
    type: str = Field("text", description="知识库类型，固定为text")
    embedding_model_config_id: int | None = Field(None, description="Embedding 模型配置ID")
    created_at: str = Field(..., description="创建时间，格式：YYYY-MM-DD")
    updated_at: str = Field(..., description="更新时间，格式：YYYY-MM-DD")
    has_graph_enhancement: Optional[bool] = Field(None, description="是否有图增强构建的文档")


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""

    items: list[KnowledgeBaseListItem] = Field(..., description="知识库列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


class DocumentGetRequest(BaseModel):
    """获取文档状态请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    doc_id: str = Field(..., min_length=1, max_length=100, description="文档ID")


class DocumentStatusRequest(BaseModel):
    """批量查询文档状态请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    doc_id_list: list[str] = Field(..., min_items=1, description="文档ID列表")


class DocumentStatusResponse(BaseModel):
    """文档状态响应"""

    doc_id: str = Field(..., alias="id", description="文档ID")
    status: str = Field(..., description="文档状态")
    name: Optional[str] = Field(None, description="文档名称")
    error_msg: Optional[str] = Field(None, description="错误信息（如果有）")
    enable_graph_enhancement: Optional[bool] = Field(None, description="是否启用图增强")

    class Config:
        populate_by_name = True


class DocumentStatusListResponse(BaseModel):
    """批量文档状态响应"""

    items: list[DocumentStatusResponse] = Field(..., description="文档状态列表")


class ParsingStrategy(BaseModel):
    """解析策略"""

    strategy_type: str = Field(..., description="策略类型：1=快速解析")
    strategy_config: Dict[str, Any] = Field(default_factory=dict, description="策略配置")


class SegmentationStrategy(BaseModel):
    """分段策略"""

    strategy_type: str = Field(..., description="策略类型：1=自动分段与清洗，2=自定义")
    strategy_config: Dict[str, Any] = Field(..., description="策略配置")


class IndexingStrategy(BaseModel):
    """索引策略"""

    enable_graph_enhancement: bool = Field(False, description="是否启用图增强")
    llm_model_id: Optional[int] = Field(None, description="LLM模型ID，启用图增强时使用")


class DocumentProcessRequest(BaseModel):
    """文档处理请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    doc_id_list: list[str] = Field(..., min_items=1, description="文档ID列表（UUID列表）")
    parsing_strategy: ParsingStrategy = Field(..., description="解析策略")
    segmentation_strategy: SegmentationStrategy = Field(..., description="分段策略")
    indexing_strategy: IndexingStrategy = Field(..., description="索引策略")


class DocumentProcessResponse(BaseModel):
    """文档处理响应"""

    task_id: str = Field(..., description="处理任务ID")
    processed_count: int = Field(..., description="已启动处理的文档数量")
    failed_count: int = Field(..., description="启动失败的文档数量")
    failed_docs: list[str] = Field(default_factory=list, description="启动失败的文档ID列表")


class DocumentListRequest(BaseModel):
    """文档列表请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    page: int = Field(1, ge=1, description="页码，默认1")
    size: int = Field(10, ge=1, le=100, description="每页大小，默认10")


class DocumentListItem(BaseModel):
    """文档列表项"""

    name: str = Field(..., description="文档名称")
    id: str = Field(..., description="文档ID")
    created_at: str = Field(..., description="创建时间，格式：YYYY-MM-DD")
    updated_at: str = Field(..., description="更新时间，格式：YYYY-MM-DD")


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    items: list[DocumentListItem] = Field(..., description="文档列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")


class DocumentUpdateRequest(BaseModel):
    """更新文档请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    document_id: str = Field(..., min_length=1, max_length=100, description="文档ID")
    document_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="新的名字（文件名部分最多100字符，加上扩展名最多150字符）",
    )

    @field_validator("document_name")
    @classmethod
    def validate_document_name_length(cls, v: str) -> str:
        """验证文档名称长度（不含扩展名）"""
        if not v:
            raise ValueError("文档名称不能为空")

        # 分离文件名和扩展名
        last_dot_index = v.rfind(".")
        if last_dot_index == -1 or last_dot_index == len(v) - 1:
            # 没有扩展名或点号在最后
            name_without_ext = v
        else:
            name_without_ext = v[:last_dot_index]

        # 检查文件名部分（不含扩展名）的长度
        MAX_NAME_LENGTH = 100
        if len(name_without_ext) > MAX_NAME_LENGTH:
            raise ValueError(
                f"文档名称不能超过 {MAX_NAME_LENGTH} 个字符，当前为 {len(name_without_ext)} 个字符"
            )

        return v


class DocumentDeleteRequest(BaseModel):
    """删除文档请求（支持批量删除）"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    document_ids: list[str] = Field(..., min_items=1, description="文档ID列表")


class TaskProgressRequest(BaseModel):
    """任务进度查询请求"""

    space_id: str = Field(..., min_length=1, max_length=100, description="空间ID")
    kb_id: str = Field(..., min_length=1, max_length=100, description="知识库ID")
    task_id: str = Field(..., min_length=1, description="任务ID")


class TaskProgressItem(BaseModel):
    """任务进度项"""

    doc_id: str = Field(..., description="文档ID")
    doc_name: str = Field(..., description="文档名称")
    status: str = Field(..., description="文档状态")
    error: str | None = Field(None, description="错误信息（如果有）")


class TaskProgressResponse(BaseModel):
    """任务进度响应"""

    task_id: str = Field(..., description="任务ID")
    total_count: int = Field(..., description="总文档数")
    processed_count: int = Field(..., description="已处理文档数")
    success_count: int = Field(..., description="成功处理文档数")
    failed_count: int = Field(..., description="失败文档数")
    items: list[TaskProgressItem] = Field(..., description="文档处理进度列表")


class RetrievalType(IntEnum):
    RETRIEVAL_HYBRID = (1,)
    RETRIEVAL_VECTOR = (2,)
    RETRIEVAL_BM25 = (3,)


class RetrievalGraphMode(IntEnum):
    NOT_USE_GRAPH = (1,)
    USE_NORMAL_GRAPH = (2,)
    USE_AGENTIC_GRAPH = (3,)


class RetrievalSourceType(IntEnum):
    RETRIEVAL_SOURCE_HYBRID = (1,)
    RETRIEVAL_SOURCE_CHUNKS = (2,)
    RETRIEVAL_SOURCE_TRIPLES = (3,)
