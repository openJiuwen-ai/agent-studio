#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from minio import Minio
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common.exceptions import JiuWenComponentException
from openjiuwen_studio.core.manager.internal.workflow import WorkflowResponsePublish
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.routers.common import handle_response, validate_request
import openjiuwen_studio.core.manager.workflow as mgr
from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.database import get_minio_client
from openjiuwen_studio.schemas.workflow import (
    WorkflowBaseResponse,
    WorkflowUpdate,
    WorkflowCreate,
    WorkflowSave,
    WorkflowResponseSave,
    WorkflowList,
    WorkflowResponseList,
    WorkflowPublish,
    WorkflowId,
    WorkflowSearchRequest,
    WorkflowSearchResponse,
    WorkflowVersionListRequest,
    WorkflowVersionListResponse,
)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.execution_log import (
    ExecutionLogsCreateList,
    ApiExecutionLogGet,
    ApiExecutionLogsDebugEnter,
    WfExecutionLogsFilter,
    WfExecutionLogIndex,
)
import openjiuwen_studio.core.manager.execution_log as exe_mgr

workflows_router = APIRouter()


@workflows_router.post("/create", response_model=ResponseModel[WorkflowBaseResponse])
async def workflow_create(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    创建工作流

    Args:
        request: 工作流创建请求数据
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowBaseResponse]: 创建结果
    """
    try:
        user_id = current_user.get("user_id", "unknown")
        logger.info(f"Workflow create request - User: {user_id}")
        req = validate_request(request, WorkflowCreate)
        res = mgr.workflow_create(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = current_user.get("user_id", "unknown")
        logger.error(
            f"Workflow create validation failed - User: {user_id}, Errors: {e.errors()}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post("/canvas", response_model=ResponseModel[WorkflowBaseResponse])
async def workflow_canvas(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    获取工作流画布

    Args:
        request: 包含工作流ID的请求数据
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowBaseResponse]: 工作流画布数据
    """
    try:
        logger.info(f"workflow canvas get start")
        req = validate_request(request, WorkflowId)
        res = mgr.workflow_canvas(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.get("/{workflow_id}", response_model=ResponseModel[dsl.Workflow])
async def workflow_get(
    workflow_id: str,
    space_id: Optional[str] = None,
    version: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    获取转换后工作流，供executor调用

    Args:
        workflow_id: 工作流ID
        space_id: 工作空间ID（可选）
        version: 工作流版本（可选）
        current_user: 当前用户信息

    Returns:
        ResponseModel[dsl.Workflow]: 转换后的工作流数据
    """
    try:
        req = {"workflow_id": workflow_id, "space_id": space_id, "version": version}
        res = mgr.workflow_convert(WorkflowId(**req), current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e
    except JiuWenComponentException as e:
        logger.info(f"JiuWenComponentException: {repr(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "component_id": e.component_id,
                "component_type": e.component_type,
                "error_stage": e.error_stage
            }
        ) from e


@workflows_router.post("/list", response_model=ResponseModel[WorkflowResponseList])
async def workflow_list(request: Dict, current_user: dict = Depends(get_current_user)):
    """
    获取指定工作空间的工作流列表

    Args:
        request: 工作流列表请求参数
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowResponseList]: 工作流列表结果
    """
    try:
        logger.info(f"workflow list start")
        req = validate_request(request, WorkflowList)
        res = mgr.workflow_list(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post("/save", response_model=ResponseModel[WorkflowResponseSave])
async def workflow_save(request: Dict, current_user: dict = Depends(get_current_user)):
    """
    保存工作流

    Args:
        request: 工作流保存请求参数
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowResponseSave]: 保存结果
    """
    try:
        user_id = current_user.get("user_id", "unknown")
        logger.info(f"Workflow save request - User: {user_id}")
        req = validate_request(request, WorkflowSave)
        logger.info(f"Saving workflow {req.workflow_id} for user {user_id}")
        res = mgr.workflow_canvas_save(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = current_user.get("user_id", "unknown")
        logger.error(
            f"Workflow save validation failed - User: {user_id}, Errors: {e.errors()}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post("/update", response_model=ResponseModel[dict])
async def workflow_update(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    更新工作流

    Args:
        request: 工作流更新请求参数
        current_user: 当前用户信息

    Returns:
        ResponseModel[dict]: 更新结果
    """
    try:
        logger.info(f"workflow update start")
        req = validate_request(request, WorkflowUpdate)
        res = mgr.workflow_meta_update(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post("/delete", response_model=ResponseModel[Dict])
async def workflow_delete(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    删除draft+publish的工作流

    Args:
        request: 包含工作流ID的请求数据
        current_user: 当前用户信息

    Returns:
        ResponseModel[Dict]: 删除结果
    """
    try:
        logger.info(f"workflow delete start")
        req = validate_request(request, WorkflowId)
        res = mgr.workflow_delete(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post("/delete_publish", response_model=ResponseModel[Dict])
async def workflow_publish_delete(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    删除某个publish版本的工作流

    Args:
        request: 包含工作流ID的请求数据
        current_user: 当前用户信息

    Returns:
        ResponseModel[Dict]: 删除结果
    """
    try:
        logger.info(f"workflow publish delete start")
        req = validate_request(request, WorkflowId)
        res = mgr.workflow_publish_delete(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post(
    "/publish", response_model=ResponseModel[WorkflowResponsePublish]
)
async def workflow_publish(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    发布工作流

    Args:
        request: 工作流发布请求参数
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowResponsePublish]: 发布结果
    """
    try:
        user_id = current_user.get("user_id", "unknown")
        logger.info(f"Workflow publish request - User: {user_id}")
        req = validate_request(request, WorkflowPublish)
        logger.info(
            f"Publishing workflow {req.workflow_id} version {req.workflow_version} for user {user_id}"
        )
        res = mgr.workflow_publish(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = current_user.get("user_id", "unknown")
        logger.error(
            f"Workflow publish validation failed - User: {user_id}, Errors: {e.errors()}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post("/copy", response_model=ResponseModel[WorkflowBaseResponse])
async def workflow_copy(request: Dict, current_user: dict = Depends(get_current_user)):
    """
    复制工作流

    Args:
        request: 工作流复制请求参数
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowBaseResponse]: 复制结果
    """
    try:
        logger.info(f"workflow copy start")
        req = validate_request(request, WorkflowId)
        res = mgr.workflow_copy(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"workflow copy failed, err: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="workflow copy failed"
        ) from e


@workflows_router.post("/search", response_model=ResponseModel[WorkflowSearchResponse])
async def workflow_search(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    搜索工作流

    Args:
        request: 搜索请求参数，包含：
            - space_id: 工作空间ID
            - search_term: 搜索关键词（支持名称、描述、标签）
            - tags: 标签过滤列表
            - status_filter: 状态过滤
            - sort_by: 排序字段
            - sort_order: 排序方向
            - page: 页码
            - page_size: 每页大小
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowSearchResponse]: 搜索结果
    """
    try:
        logger.info(f"workflow search start")
        req = validate_request(request, WorkflowSearchRequest)
        res = mgr.workflow_search(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error("workflow search failed, err")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post(
    "/version_list", response_model=ResponseModel[WorkflowVersionListResponse]
)
async def workflow_version_list(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    查询工作流的发布版本列表

    Args:
        request: 版本列表请求参数，包含：
            - workflow_id: 工作流ID
            - space_id: 工作空间ID
        current_user: 当前用户信息

    Returns:
        ResponseModel[WorkflowVersionListResponse]: 版本列表结果
    """
    try:
        logger.info(f"workflow version list start")
        req = validate_request(request, WorkflowVersionListRequest)
        res = mgr.workflow_version_list(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"workflow version list failed, err: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post(
    "/get_execution_logs_create_list",
    response_model=ResponseModel[ExecutionLogsCreateList],
)
async def get_workflow_execution_logs_create_list(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    获取工作流的所有执行日志创建信息列表

    Args:
        request: 工作流信息及过滤条件
        current_user: 当前用户信息

    Returns:
        ResponseModel[ExecutionLogsCreateList]: 执行日志创建信息列表
    """
    try:
        logger.info(f"Get workflow execution logs create list start.")
        req = validate_request(request, WfExecutionLogsFilter)
        res = exe_mgr.get_workflow_execution_logs_create_list(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(
            f"Get workflow execution logs create list failed, err: {e.errors()}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post(
    "/get_execution_log", response_model=ResponseModel[ApiExecutionLogGet]
)
async def get_workflow_execution_log(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    获取工作流的某次执行日志

    Args:
        request: 工作流及某次执行的ID信息
        current_user: 当前用户信息

    Returns:
        ResponseModel[ApiExecutionLogGet]: 创建信息list
    """
    try:
        logger.info(f"Get workflow execution log start.")
        req = validate_request(request, WfExecutionLogIndex)
        res = exe_mgr.get_workflow_execution_log(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"Get workflow execution log failed, err: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.post(
    "/enter_execution_logs_debug",
    response_model=ResponseModel[ApiExecutionLogsDebugEnter],
)
async def enter_workflow_execution_logs_debug(
    request: Dict, current_user: dict = Depends(get_current_user)
):
    """
    进入调试模式，获取工作流的所有执行日志创建列表及最新运行日志

    Args:
        request: 工作流ID信息
        current_user: 当前用户信息

    Returns:
        ResponseModel[ApiExecutionLogsDebugEnter]: 所有运行log的create list及最新运行日志
    """
    try:
        logger.info(f"Enter workflow execution logs debug start.")
        req = validate_request(request, WorkflowId)
        res = exe_mgr.enter_workflow_execution_logs_debug(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        logger.error(f"Enter workflow execution logs debug, err: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e


@workflows_router.get("/get_upload_url/{object_key}", response_model=ResponseModel[dict])
async def get_upload_url(
        space_id: str,
        object_key: str,
        current_user: dict = Depends(get_current_user)
):
    """
    获取文件上传自签名URL

    Args:
        workflow_id: 工作流ID
        space_id: 工作空间ID
        object_key：文件唯一标识
        current_user: 当前用户信息

    Returns:
        ResponseModel[dict]: 上传文件URL
    """
    try:
        minio_client = get_minio_client()
        logger.info(f"Get workflow execution logs create list start.")
        req = {"space_id": space_id, "object_key": object_key}
        res = mgr.get_upload_url(req, current_user, minio_client)
        return handle_response(res)
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate upload URL"
        ) from e


@workflows_router.get("/get_download_url/{object_key}", response_model=ResponseModel[dict])
async def get_download_url(
        space_id: str,
        object_key: Optional[str] = None,
        current_user: dict = Depends(get_current_user)
):
    """
    获取文件下载自签名URL

    Args:
        workflow_id: 工作流ID
        space_id: 工作空间ID
        object_key：文件唯一标识
        current_user: 当前用户信息

    Returns:
        ResponseModel[dict]: 下载文件URL
    """
    try:
        minio_client = get_minio_client()
        logger.info(f"Get workflow execution logs create list start.")
        req = {"space_id": space_id, "object_key": object_key}
        res = mgr.get_download_url(req, current_user, minio_client)
        return handle_response(res)
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to generate download URL"
        ) from e
