#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from pydantic import ValidationError
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.routers.common import handle_response, validate_request
import openjiuwen_studio.core.manager.knowledge_base as kb_mgr
from openjiuwen_studio.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseGet,
    KnowledgeBaseUpdateRequest,
    KnowledgeBaseSearchRequest,
    KnowledgeBaseListRequest,
    DocumentStatusRequest,
    DocumentProcessRequest,
    DocumentListRequest,
    DocumentUpdateRequest,
    DocumentDeleteRequest,
    TaskProgressRequest,
    WeblinkAddRequest,
    WeblinkListRequest,
    WeblinkStatusRequest,
    WeblinkProcessRequest,
    WeblinkUpdateRequest,
    WeblinkDeleteRequest,
    SyncUploadRequest,
    SyncProcessRequest,
)
from openjiuwen_studio.schemas.common import ResponseModel

knowledge_base_router = APIRouter()


@knowledge_base_router.post("/create", response_model=ResponseModel[dict])
async def knowledge_base_create(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    创建新的知识库

    Args:
        request (dict): 包含创建需求的请求体数据，需符合KnowledgeBaseCreate模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了创建成功的知识库详情及元数据。
        如果创建失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, KnowledgeBaseCreate)
        res = kb_mgr.knowledge_base_create(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[KB_CREATE] Knowledge base created - ID: {res.data.get('id')}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[KB_CREATE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="knowledge base create failed") from e


@knowledge_base_router.post("/get-referencing-agents", response_model=ResponseModel[dict])
async def knowledge_base_get_referencing_agents(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    获取引用指定知识库的智能体列表
    
    Args:
        request (dict): 包含知识库查询条件的请求体，需符合KnowledgeBaseGet模型定义
        current_user (dict): 执行此操作的用户上下文信息
    
    Returns:
        ResponseModel[dict]: 包含智能体名称列表和数量的响应
    """
    try:
        req = validate_request(request, KnowledgeBaseGet)
        res = kb_mgr.knowledge_base_get_referencing_agents(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[KB_GET_REF_AGENTS] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e.errors()}"
        ) from e
    except Exception as e:
        logger.error(
            f"[KB_GET_REF_AGENTS] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@knowledge_base_router.post("/delete", response_model=ResponseModel[dict])
async def knowledge_base_delete(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    删除指定知识库

    Args:
        request (dict): 包含删除需求的请求体数据，需符合KnowledgeBaseGet模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了删除成功的知识库详情及元数据。
        如果删除失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, KnowledgeBaseGet)
        res = await kb_mgr.knowledge_base_delete(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[KB_DELETE] Knowledge base deleted - ID: {req.kb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[KB_DELETE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="knowledge base delete failed") from e


@knowledge_base_router.post("/update", response_model=ResponseModel[dict])
async def knowledge_base_update(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    更新知识库

    Args:
        request (dict): 包含更新需求的请求体数据，需符合KnowledgeBaseUpdateRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了更新成功的消息。
        如果更新失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, KnowledgeBaseUpdateRequest)
        res = kb_mgr.knowledge_base_update(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[KB_UPDATE] Knowledge base updated - ID: {req.kb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except HTTPException:
        # 重新抛出 HTTPException，不要转换为 500
        raise
    except ValidationError as e:
        logger.error(
            f"[KB_UPDATE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="knowledge base update failed") from e
    except Exception as e:
        logger.error(
            f"[KB_UPDATE] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@knowledge_base_router.post("/upload", response_model=ResponseModel[dict])
async def knowledge_base_upload_documents(
        files: List[UploadFile] = File(..., description="要上传的文件列表（支持多文件）"),
        space_id: str = Form(..., description="空间ID"),
        kb_id: str = Form(..., description="知识库ID"),
        metadata: Optional[str] = Form(None, description="文档元数据（JSON字符串，可选）"),
        current_user: dict = Depends(get_current_user)
):
    """
    上传文档到知识库（支持多文件上传）

    Args:
        files (List[UploadFile]): 要上传的文件列表，支持同时上传多个文件
        space_id (str): 空间ID
        kb_id (str): 知识库ID
        metadata (Optional[str]): 文档元数据，JSON字符串格式（可选）
        current_user (dict): 执行此操作的用户上下文信息

    Returns:
        ResponseModel[dict]: 标准化响应对象，包含上传结果：
        - success_count: 成功上传的文件数量
        - failed_count: 上传失败的文件数量
        - documents: 上传成功的文档列表（包含 doc_id, name, file_size, status）
    """
    try:
        # 验证文件列表不为空
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )

        # 允许的文件类型
        allowed_file_extensions = {'.pdf', '.doc', '.docx', '.txt', '.md'}

        # 验证文件类型
        invalid_files = []
        for file in files:
            if not file.filename:
                invalid_files.append("未命名文件")
                continue

            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_file_extensions:
                invalid_files.append(file.filename)

        if invalid_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {', '.join(invalid_files)}。仅支持: {', '.join(sorted(allowed_file_extensions))}"
            )
        
        # 注意：文件大小限制在 Manager 层检查，因为需要读取文件内容后才能获取实际大小

        # 解析元数据（如果提供）
        doc_metadata = None
        if metadata:
            try:
                doc_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(
                    f"[KB_UPLOAD] Invalid metadata JSON - User: {current_user.get('user_id', 'unknown')}"
                )
                # 如果元数据格式错误，继续处理，但不使用元数据

        # 调用 Manager 层处理文件上传（异步）
        res = await kb_mgr.document_upload(
            space_id=space_id,
            kb_id=kb_id,
            files=files,
            metadata=doc_metadata,
            current_user=current_user
        )

        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[KB_UPLOAD] Documents uploaded - KB ID: {kb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}, "
                f"Success: {res.data.get('success_count', 0)}, "
                f"Failed: {res.data.get('failed_count', 0)}"
            )
        else:
            logger.error(
                f"[KB_UPLOAD] Upload failed - KB ID: {kb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}, "
                f"Error: {res.message}"
            )

        return handle_response(res)

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(
            f"[KB_UPLOAD] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document upload validation failed") from e
    except Exception as e:
        logger.error(
            f"[KB_UPLOAD] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@knowledge_base_router.post("/search", response_model=ResponseModel[dict])
async def knowledge_base_search(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    查询知识库（支持分页）

    Args:
        request (dict): 包含查询需求的请求体数据，需符合KnowledgeBaseSearchRequest模型定义。
            - space_id: 空间ID
            - query: 查询词（查询词完整出现在知识库名称或描述中，大小写不敏感）
            - page: 页码，从1开始（可选，默认1）
            - page_size: 每页大小（可选，默认10，最大100）
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，包含查询结果：
        - knowledge_bases: 匹配的知识库列表
        - total: 总记录数
        - page: 当前页码
        - page_size: 每页大小
        - total_pages: 总页数
    """
    try:
        req = validate_request(request, KnowledgeBaseSearchRequest)
        res = kb_mgr.knowledge_base_search(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[KB_SEARCH] Knowledge bases searched - "
                f"User: {current_user.get('user_id', 'unknown')}, "
                f"Query: '{req.query}', Found: {len(res.data.get('knowledge_bases', [])) if res.data else 0}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[KB_SEARCH] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="knowledge base search failed") from e
    except Exception as e:
        logger.error(
            f"[KB_SEARCH] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@knowledge_base_router.post("/list", response_model=ResponseModel[dict])
async def knowledge_base_list(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    获取知识库列表（支持分页）

    Args:
        request (dict): 包含查询需求的请求体数据，需符合KnowledgeBaseListRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，包含知识库列表：
        - items: 知识库列表数组，每个元素包含：
          - name: 知识库名称
          - desc: 知识库描述
          - id: 知识库ID
          - type: 知识库类型（固定为"text"）
          - created_at: 创建时间（格式：YYYY-MM-DD）
          - updated_at: 更新时间（格式：YYYY-MM-DD）
        - total: 总记录数
        - page: 当前页码
        - size: 每页大小
    """
    try:
        req = validate_request(request, KnowledgeBaseListRequest)
    except ValidationError:
        # 验证失败时，使用默认值调用 manager 层（manager 层会返回空列表）
        req = KnowledgeBaseListRequest(
            space_id=request.get("space_id", "") if isinstance(request, dict) else "",
            page=request.get("page", 1) if isinstance(request, dict) else 1,
            size=request.get("size", 10) if isinstance(request, dict) else 10
        )

    res = kb_mgr.knowledge_base_list(req, current_user)
    if res.code == status.HTTP_200_OK:
        logger.info(
            f"[KB_LIST] Knowledge base list retrieved - Space ID: {req.space_id}, "
            f"Count: {len(res.data.get('items', []))}, User: {current_user.get('user_id', 'unknown')}"
        )
    # 直接返回结果，manager 层已经确保总是返回 200 和正常数据结构
    return res


@knowledge_base_router.post("/sync/upload", response_model=ResponseModel[dict])
async def knowledge_base_sync_upload(
    request: dict,
    current_user: dict = Depends(get_current_user),
):
    """文件同步到 DeepSearch 知识库：创建/复用 DS 知识库并上传文档"""
    try:
        req = validate_request(request, SyncUploadRequest)
        res = await kb_mgr.knowledge_base_sync_upload(
            space_id=req.space_id,
            kb_id=req.kb_id,
            current_user=current_user,
            deepsearch_embedding_model_config_id=req.deepsearch_embedding_model_config_id,
        )
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[KB_SYNC_UPLOAD] Validation failed - Errors: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sync upload request validation failed",
        ) from e


@knowledge_base_router.post("/sync/process", response_model=ResponseModel[dict])
async def knowledge_base_sync_process(
    request: dict,
    current_user: dict = Depends(get_current_user),
):
    """同步到 DeepSearch 知识库：文档参数设置/建索引"""
    try:
        req = validate_request(request, SyncProcessRequest)
        payload = req.model_dump(exclude_none=True)
        res = await kb_mgr.knowledge_base_sync_process(
            payload=payload, current_user=current_user
        )
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[KB_SYNC_PROCESS] Validation failed - Errors: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sync process request validation failed",
        ) from e


@knowledge_base_router.post("/documents/status", response_model=ResponseModel[dict])
async def document_get_status(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    批量查询文档状态

    Args:
        request (dict): 包含查询需求的请求体数据，需符合DocumentStatusRequest模型定义。
            - space_id: 空间ID
            - kb_id: 知识库ID
            - doc_id_list: 文档ID列表（支持批量查询）
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，包含文档状态列表：
        - items: 文档状态列表，每个元素包含：
          - id: 文档ID
          - status: 文档状态（uploading, uploaded, processing, indexing, indexed, failed, deleted）
          - name: 文档名称（可选）
    """
    try:
        req = validate_request(request, DocumentStatusRequest)
        res = await kb_mgr.document_get_status_batch(req, current_user)
        if res.code == status.HTTP_200_OK:
            items_count = len(res.data.get('items', [])) if res.data else 0
            logger.info(
                f"[DOC_STATUS] Document status retrieved - "
                f"Space ID: {req.space_id}, KB ID: {req.kb_id}, "
                f"Requested: {len(req.doc_id_list)}, Found: {items_count}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[DOC_STATUS] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document status query failed") from e
    except Exception as e:
        logger.error(
            f"[DOC_STATUS] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@knowledge_base_router.post("/process", response_model=ResponseModel[dict])
async def knowledge_base_process_documents(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    启动文档处理流程

    Args:
        request (dict): 包含处理需求的请求体数据，需符合DocumentProcessRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，包含处理结果：
        - task_id: 处理任务ID
        - processed_count: 已启动处理的文档数量
        - failed_count: 启动失败的文档数量
        - failed_files: 启动失败的文件ID列表
    """
    try:
        req = validate_request(request, DocumentProcessRequest)
        res = await kb_mgr.document_process(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[KB_PROCESS] Document processing started - Task ID: {res.data.get('task_id')}, "
                f"KB ID: {req.kb_id}, Processed: {res.data.get('processed_count', 0)}, "
                f"Failed: {res.data.get('failed_count', 0)}, User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[KB_PROCESS] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="knowledge base process failed") from e


@knowledge_base_router.post("/task/progress", response_model=ResponseModel[dict])
async def task_progress(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    查询文档处理任务进度

    Args:
        request (dict): 包含查询需求的请求体数据，需符合TaskProgressRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，包含任务进度
    """
    try:
        req = validate_request(request, TaskProgressRequest)
        res = kb_mgr.task_progress(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[TASK_PROGRESS] Task progress retrieved - Task ID: {req.task_id}, "
                f"KB ID: {req.kb_id}, User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[TASK_PROGRESS] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="task progress query failed") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[TASK_PROGRESS] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@knowledge_base_router.post("/documents/list", response_model=ResponseModel[dict])
async def document_list(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    获取知识库文档列表（支持分页）

    Args:
        request (dict): 包含查询需求的请求体数据，需符合DocumentListRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，包含文档列表：
        - items: 文档列表数组，每个元素包含：
          - name: 文档名称
          - id: 文档ID
          - created_at: 创建时间（格式：YYYY-MM-DD）
          - updated_at: 更新时间（格式：YYYY-MM-DD）
        - total: 总记录数
        - page: 当前页码
        - size: 每页大小
    """
    try:
        req = validate_request(request, DocumentListRequest)
        res = await kb_mgr.document_list(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[DOC_LIST] Document list retrieved - Space ID: {req.space_id}, "
                f"KB ID: {req.kb_id}, Count: {len(res.data.get('items', []))}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[DOC_LIST] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document list failed")


@knowledge_base_router.post("/documents/update", response_model=ResponseModel[dict])
async def document_update(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    更新文档信息（当前只支持更新文档名称）

    Args:
        request (dict): 包含更新需求的请求体数据，需符合DocumentUpdateRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了更新成功的消息。
        如果更新失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, DocumentUpdateRequest)
        res = kb_mgr.document_update(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[DOC_UPDATE] Document updated - Doc ID: {req.document_id}, KB ID: {req.kb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except HTTPException:
        # 重新抛出 HTTPException，不要转换为 500
        raise
    except ValidationError as e:
        logger.error(
            f"[DOC_UPDATE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document update failed") from e
    except Exception as e:
        logger.error(
            f"[DOC_UPDATE] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@knowledge_base_router.post("/documents/delete", response_model=ResponseModel[dict])
async def document_delete(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    删除文档（支持批量删除）

    Args:
        request (dict): 包含删除需求的请求体数据，需符合DocumentDeleteRequest模型定义。
            - space_id: 空间ID
            - kb_id: 知识库ID
            - document_ids: 文档ID列表（数组）
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了删除成功的消息。
        如果删除失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, DocumentDeleteRequest)
        res = await kb_mgr.document_delete(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[DOC_DELETE] Documents deleted - Doc IDs: {req.document_ids}, KB ID: {req.kb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except HTTPException:
        # 重新抛出 HTTPException，不要转换为 500
        raise
    except ValidationError as e:
        logger.error(
            f"[DOC_DELETE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="document delete failed") from e
    except Exception as e:
        logger.error(
            f"[DOC_DELETE] Unexpected error - User: {current_user.get('user_id', 'unknown')}, "
            f"Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


# ==================== Weblink routes ====================


@knowledge_base_router.post("/weblinks/add", response_model=ResponseModel[dict])
async def weblink_add_route(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """添加链接到知识库"""
    try:
        req = validate_request(request, WeblinkAddRequest)
        res = await kb_mgr.weblink_add(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[WEBLINK_ADD] Validation failed - Errors: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weblink add failed") from e


@knowledge_base_router.post("/weblinks/list", response_model=ResponseModel[dict])
async def weblink_list_route(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """获取链接列表"""
    try:
        req = validate_request(request, WeblinkListRequest)
        res = await kb_mgr.weblink_list(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[WEBLINK_LIST] Validation failed - Errors: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weblink list failed") from e


@knowledge_base_router.post("/weblinks/status", response_model=ResponseModel[dict])
async def weblink_status_route(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """批量查询链接状态"""
    try:
        req = validate_request(request, WeblinkStatusRequest)
        res = await kb_mgr.weblink_get_status_batch(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[WEBLINK_STATUS] Validation failed - Errors: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weblink status failed") from e


@knowledge_base_router.post("/weblinks/process", response_model=ResponseModel[dict])
async def weblink_process_route(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """处理链接（解析并索引）"""
    try:
        req = validate_request(request, WeblinkProcessRequest)
        res = await kb_mgr.weblink_process(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[WEBLINK_PROCESS] Validation failed - Errors: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weblink process failed") from e


@knowledge_base_router.post("/weblinks/update", response_model=ResponseModel[dict])
async def weblink_update_route(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """更新链接名称"""
    try:
        req = validate_request(request, WeblinkUpdateRequest)
        res = kb_mgr.weblink_update(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[WEBLINK_UPDATE] Validation failed - Errors: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weblink update failed") from e


@knowledge_base_router.post("/weblinks/delete", response_model=ResponseModel[dict])
async def weblink_delete_route(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """批量删除链接"""
    try:
        req = validate_request(request, WeblinkDeleteRequest)
        res = await kb_mgr.weblink_delete(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"[WEBLINK_DELETE] Validation failed - Errors: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weblink delete failed") from e
