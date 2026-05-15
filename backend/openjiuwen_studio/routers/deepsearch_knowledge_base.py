#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.routers.common import handle_response, validate_request
import openjiuwen_studio.core.manager.knowledge_base as kb_mgr
from openjiuwen_studio.schemas.knowledge_base import KnowledgeBaseListRequest
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.database import get_db
from openjiuwen_studio.models.knowledge_base import KnowledgeBaseDB
from openjiuwen_studio.core.manager.repositories.embedding_model_config_repository import EmbeddingModelConfigRepository
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from pydantic import ValidationError

deepsearch_knowledge_base_router = APIRouter()


def _default_ds_collection_name(kb_id: str) -> str:
    normalized_kb_id = str(kb_id).strip()
    if normalized_kb_id.startswith("ds_kb_"):
        return f"{normalized_kb_id}_chunks"
    return f"ds_kb_{normalized_kb_id}_chunks"


@deepsearch_knowledge_base_router.post("/knowledge-base/list", response_model=ResponseModel[dict])
async def deepsearch_knowledge_base_list(
    request: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    查询 DeepSearch 知识库列表，返回含索引状态，配置弹框中仅可选已建好索引的知识库。仅返回已同步到 DeepSearch 的项，不包含 Studio 原始知识库。
    """
    try:
        req = validate_request(request, KnowledgeBaseListRequest)
    except ValidationError:
        req = KnowledgeBaseListRequest(
            space_id=request.get("space_id", "") if isinstance(request, dict) else "",
            page=request.get("page", 1) if isinstance(request, dict) else 1,
            size=request.get("size", 10) if isinstance(request, dict) else 10,
        )
    res = await kb_mgr.knowledge_base_ds_list(
        space_id=req.space_id,
        page=req.page,
        size=req.size,
        current_user=current_user,
    )
    return handle_response(res)


@deepsearch_knowledge_base_router.post("/knowledge-base/runtime-config", response_model=ResponseModel[dict])
async def deepsearch_knowledge_base_runtime_config(
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Resolve Deep Search local-KB runtime retrieve_config from a selected DeepSearch KB ID.
    This keeps Milvus / embedder details on backend side and avoids exposing them in config UI.
    """
    space_id = request.get("space_id") if isinstance(request, dict) else None
    kb_id = request.get("kb_id") if isinstance(request, dict) else None
    if not space_id or not kb_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="space_id and kb_id are required",
        )

    _ = check_user_space(space_id, current_user)

    # Defaults from backend environment
    retrieve_config = {
        "milvus_host": os.getenv("MILVUS_HOST", "localhost"),
        "milvus_port": int(os.getenv("MILVUS_PORT", "19530")),
        "database_name": os.getenv("MILVUS_DATABASE_NAME", "default"),
        # Fallback to DS KB-derived naming if DS list does not provide an explicit collection.
        "collection_name": _default_ds_collection_name(str(kb_id)),
        "embedder_timeout": int(os.getenv("DEEPSEARCH_EMBEDDER_TIMEOUT", "100")),
    }

    # Try to enrich from DS KB list payload first (if config/collection is present there)
    try:
        ds_list = await kb_mgr.knowledge_base_ds_list(
            space_id=space_id,
            page=1,
            size=200,
            current_user=current_user,
        )
        items = (((ds_list.data or {}) if hasattr(ds_list, "data") else {}) or {}).get("items", [])
        selected = next((item for item in items if str(item.get("id")) == str(kb_id)), None)
        if selected:
            # Common field candidates from DS payload
            cfg = selected.get("retrieve_config") or (selected.get("config") or {}).get("retrieve_config") or {}
            selected_name = selected.get("name")
            selected_name_as_collection = (
                selected_name.strip()
                if isinstance(selected_name, str) and selected_name.strip().endswith("_chunks")
                else None
            )
            retrieve_config["collection_name"] = (
                cfg.get("collection_name")
                or selected.get("collection_name")
                or selected.get("chunk_index")
                or selected.get("index_name")
                or selected_name_as_collection
                or retrieve_config["collection_name"]
            )
            retrieve_config["database_name"] = (
                cfg.get("database_name")
                or selected.get("database_name")
                or retrieve_config["database_name"]
            )
    except Exception as exc:
        logger.warning(
            "[DeepSearch KB Runtime] DS list lookup failed, using fallback retrieve_config. "
            f"space_id={space_id}, kb_id={kb_id}, error={exc}",
        )

    # Use Studio KB mapping + embedding model to fill embedder config where possible
    kb_row = db.query(KnowledgeBaseDB).filter(
        KnowledgeBaseDB.space_id == space_id,
        KnowledgeBaseDB.ds_kb_id == kb_id,
    ).first()

    if kb_row and kb_row.embedding_model_config_id:
        embed_repo = EmbeddingModelConfigRepository(db)
        embed_model = embed_repo.get_by_id(kb_row.embedding_model_config_id)
        if embed_model:
            security_utils = SecurityUtils()
            embed_api_key = None
            if embed_model.api_key:
                try:
                    embed_api_key = security_utils.decrypt_api_key(embed_model.api_key)
                except Exception:
                    embed_api_key = None

            retrieve_config["embedder_model_name"] = embed_model.model_id
            retrieve_config["embedder_base_url"] = embed_model.api_base
            retrieve_config["embedder_api_key"] = embed_api_key

    return ResponseModel(
        code=200,
        message="DeepSearch runtime retrieve_config resolved successfully",
        data={"retrieve_config": retrieve_config},
    )
