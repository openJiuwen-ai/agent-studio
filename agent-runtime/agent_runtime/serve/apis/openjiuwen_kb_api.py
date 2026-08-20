# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
OpenJiuwen Knowledge Base API — 知识库管理接口

提供知识库的创建、文档上传、检索、删除等 REST API，
封装 openjiuwen SimpleKnowledgeBase 完整 RAG pipeline。
"""

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_kb_manager import (
    KBSearchOptions,
    OpenJiuwenKBManager,
)

logger = logging.getLogger(__name__)

openjiuwen_kb_router = APIRouter(tags=["openjiuwen_kb"])


class KBModelConfig(BaseModel):
    """Embedding 模型配置（通过模型中心解析）。"""

    model_service_id: str = Field(..., description="模型服务 ID（deploymentId）")
    workspace_id: str = Field(default="", description="工作空间 ID")
    project_id: str = Field(default="0", description="项目 ID")
    auth_id: str = Field(default="", description="认证 ID（为空时按 workspace 自动匹配）")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CreateKBRequest(BaseModel):
    """创建知识库请求。"""

    kb_id: str = Field(..., description="知识库 ID")
    kb_name: str = Field(default="", description="知识库名称")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="知识库元数据")
    model_config_field: KBModelConfig = Field(
        ..., validation_alias="model_config", description="Embedding 模型配置",
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class KBResponse(BaseModel):
    """通用知识库操作响应。"""

    success: bool = Field(default=True)
    message: str = Field(default="")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class UploadResponse(BaseModel):
    """上传文档响应。"""

    success: bool = Field(default=True)
    doc_count: int = Field(default=0)
    message: str = Field(default="")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SearchRequest(BaseModel):
    """检索知识库请求。"""

    kb_id: str = Field(..., description="知识库 ID")
    query: str = Field(..., description="检索查询文本")
    top_k: int = Field(default=5, description="返回结果数量")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="元数据过滤条件")
    index_type: str = Field(default="vector", description="检索模式: vector/bm25/hybrid")
    model_config_field: Optional[KBModelConfig] = Field(
        default=None, validation_alias="model_config", description="Embedding 模型配置（KB 未缓存时必传）",
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SearchResultItem(BaseModel):
    """单条检索结果。"""

    text: str = Field(default="")
    score: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SearchResponse(BaseModel):
    """检索响应。"""

    results: List[SearchResultItem] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DeleteKBRequest(BaseModel):
    """删除知识库请求。"""

    kb_id: str = Field(..., description="知识库 ID")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ListKBResponse(BaseModel):
    """知识库列表响应。"""

    kbs: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


@openjiuwen_kb_router.post("/internal/v1/kb/create", response_model=KBResponse)
async def create_kb(request: CreateKBRequest) -> KBResponse:
    """创建知识库。"""
    manager = OpenJiuwenKBManager()
    result = await manager.create_kb(
        kb_id=request.kb_id,
        kb_name=request.kb_name,
        metadata=request.metadata,
        model_config=request.model_config_field.model_dump(),
    )
    return KBResponse(success=result["success"], message=result["message"])


@openjiuwen_kb_router.post("/internal/v1/kb/upload", response_model=UploadResponse)
async def upload_documents(
    kb_id: str = Form(...),
    file: UploadFile = File(...),
    model_config_json: Optional[str] = Form(default=None),
) -> UploadResponse:
    """上传文档到知识库（multipart 文件流方式）。"""
    manager = OpenJiuwenKBManager()
    mc = json.loads(model_config_json) if model_config_json else None
    file_paths = []
    temp_files = []
    try:
        suffix = os.path.splitext(file.filename or "")[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        content = await file.read()
        tmp.write(content)
        tmp.close()
        file_paths.append(tmp.name)
        temp_files.append(tmp.name)
        result = await manager.upload_documents(
            kb_id=kb_id,
            file_paths=file_paths,
            model_config=mc,
        )
        return UploadResponse(
            success=result["success"],
            doc_count=result["doc_count"],
            message=result["message"],
        )
    finally:
        for path in temp_files:
            try:
                os.unlink(path)
            except OSError:
                logger.warning("Failed to clean up temp file: %s", path)


@openjiuwen_kb_router.post("/internal/v1/kb/search", response_model=SearchResponse)
async def search_kb(request: SearchRequest) -> SearchResponse:
    """检索知识库。"""
    manager = OpenJiuwenKBManager()
    results = await manager.search(
        kb_id=request.kb_id,
        query=request.query,
        options=KBSearchOptions(
            model_config=request.model_config_field.model_dump() if request.model_config_field else None,
            top_k=request.top_k,
            filters=request.filters,
            index_type=request.index_type,
        ),
    )
    return SearchResponse(
        results=[SearchResultItem(**r) for r in results],
    )


@openjiuwen_kb_router.delete("/internal/v1/kb/delete", response_model=KBResponse)
async def delete_kb(request: DeleteKBRequest) -> KBResponse:
    """删除知识库。"""
    manager = OpenJiuwenKBManager()
    result = await manager.delete_kb(request.kb_id)
    return KBResponse(success=result["success"], message=result["message"])


@openjiuwen_kb_router.get("/internal/v1/kb/list", response_model=ListKBResponse)
async def list_kbs(kb_ids: Optional[str] = None) -> ListKBResponse:
    """列出知识库存在状态。"""
    manager = OpenJiuwenKBManager()
    kb_id_list = kb_ids.split(",") if kb_ids else None
    kbs = await manager.list_kbs(kb_id_list)
    return ListKBResponse(kbs=kbs)
