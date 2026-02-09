#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Dict

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import ValidationError
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.routers.common import handle_response, validate_request
import openjiuwen_studio.core.manager.memory_base as mb_mgr
from openjiuwen_studio.schemas.memory_base import (
    MemoryBaseCreate, MemoryBaseGet, MemoryBaseUpdateRequest, MemoryBaseListRequest,
    MemoryBaseSearchRequest, MemoryBaseInfo
)
from openjiuwen_studio.schemas.common import ResponseModel

memory_base_router = APIRouter()


@memory_base_router.post("/repo/create", response_model=ResponseModel[Dict])
async def memory_base_create(
        request: Dict,
        current_user: Dict = Depends(get_current_user)
):
    """
    创建新的记忆库

    Args:
        request (dict): 包含创建需求的请求体数据，需符合MemoryBaseCreate模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了创建成功的记忆库详情及元数据。
        如果创建失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, MemoryBaseCreate)
        res = await mb_mgr.memory_base_create(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[MB_CREATE] Memory base created - ID: {res.data.get('id')}, "
                f"Name: {req.name}, User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[MB_CREATE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="memory base create failed") from e


@memory_base_router.post("/repo/get", response_model=ResponseModel[Dict])
async def memory_base_get(
        request: Dict,
        current_user: Dict = Depends(get_current_user)
):
    """
    获取指定记忆库信息

    Args:
        request (dict): 包含查询需求的请求体数据，需符合MemoryBaseGet模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了查询到的记忆库详情及元数据。
        如果查询失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, MemoryBaseGet)
        res = mb_mgr.memory_base_get(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[MB_GET] Memory base retrieved - ID: {req.mdb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[MB_GET] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="memory base get failed") from e


@memory_base_router.post("/repo/delete", response_model=ResponseModel[None])
async def memory_base_delete(
        request: Dict,
        current_user: Dict = Depends(get_current_user)
):
    """
    删除指定记忆库

    Args:
        request (dict): 包含删除需求的请求体数据，需符合MemoryBaseGet模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了删除成功的消息。
        如果删除失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, MemoryBaseGet)
        res = await mb_mgr.memory_base_delete(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[MB_DELETE] Memory base deleted - ID: {req.mdb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[MB_DELETE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="memory base delete failed") from e


@memory_base_router.post("/repo/update", response_model=ResponseModel[None])
async def memory_base_update(
        request: Dict,
        current_user: Dict = Depends(get_current_user)
):
    """
    更新记忆库信息

    Args:
        request (dict): 包含更新需求的请求体数据，需符合MemoryBaseUpdateRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了更新成功的消息。
        如果更新失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, MemoryBaseUpdateRequest)
        res = await mb_mgr.memory_base_update(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[MB_UPDATE] Memory base updated - ID: {req.mdb_id}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[MB_UPDATE] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="memory base update failed") from e


@memory_base_router.post("/repo/list", response_model=ResponseModel[Dict])
async def memory_base_list(
        request: Dict,
        current_user: Dict = Depends(get_current_user)
):
    """
    获取记忆库列表（支持分页）

    Args:
        request (dict): 包含查询需求的请求体数据，需符合MemoryBaseListRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了记忆库列表及分页信息。
        如果查询失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, MemoryBaseListRequest)
        res = mb_mgr.memory_base_list(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[MB_LIST] Memory base list retrieved - Space: {req.space_id}, "
                f"Page: {req.page}, Size: {req.page_size}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[MB_LIST] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="memory base list failed") from e


@memory_base_router.post("/repo/search", response_model=ResponseModel[Dict])
async def memory_base_search(
        request: Dict,
        current_user: Dict = Depends(get_current_user)
):
    """
    搜索记忆库（支持关键词查询和分页）

    Args:
        request (dict): 包含查询需求的请求体数据，需符合MemoryBaseSearchRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了匹配的记忆库列表及分页信息。
        如果搜索失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, MemoryBaseSearchRequest)
        res = mb_mgr.memory_base_search(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[MB_SEARCH] Memory base search completed - Space: {req.space_id}, "
                f"Query: {req.query}, Page: {req.page}, Page Size: {req.page_size}, "
                f"User: {current_user.get('user_id', 'unknown')}"
            )
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"[MB_SEARCH] Validation failed - User: {current_user.get('user_id', 'unknown')}, "
            f"Errors: {e.errors()}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="memory base search failed") from e