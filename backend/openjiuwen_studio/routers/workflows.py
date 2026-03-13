#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import ValidationError
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


@workflows_router.get("/export_py/{workflow_id}", response_model=ResponseModel[dict])
async def workflow_export_py(
    workflow_id: str,
    space_id: Optional[str] = None,
    version: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Export a workflow as a runnable Python script.

    Retrieves the workflow from the database, converts it through the full
    canvas → DSL pipeline, then generates a standalone Python file that
    uses the openjiuwen SDK to rebuild and run the same workflow.

    Args:
        workflow_id: The workflow ID.
        space_id: The space ID (optional).
        version: The workflow version (optional).
        current_user: The current authenticated user.

    Returns:
        ResponseModel[dict]: A dict with keys:
            - workflow_id: str
            - python_code: str  (the full .py file content)
    """
    try:
        req = {"workflow_id": workflow_id, "space_id": space_id, "version": version}
        res = mgr.workflow_export_py(WorkflowId(**req), current_user)
        return handle_response(res)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Request validation failed"
        ) from e
    except JiuWenComponentException as e:
        logger.info(f"JiuWenComponentException during export_py: {repr(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "component_id": e.component_id,
                "component_type": e.component_type,
                "error_stage": e.error_stage,
            },
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


@workflows_router.post("/import", response_model=ResponseModel[Dict])
async def workflow_import(
    file: UploadFile = File(...),
    space_id: str = Form(...),
    validate_strict: bool = Form(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Import workflow from JSON file.

    Supported formats:
    - OpenJiuwen native export
    - n8n workflow JSON

    The imported workflow will receive:
    - A NEW workflow_id (GUID) - different from the exported workflow
    - A NEW auto-incrementing id field
    - Name with " (imported)" suffix (e.g., "My Workflow (imported)")
    - Regenerated canvas node IDs to avoid conflicts
    - Current timestamps (create_time, update_time)
    - No version history (starts as draft)

    Args:
        file: JSON file containing workflow
        space_id: Target workspace ID
        validate_strict: If True, compile workflow to validate (slower but more thorough)
        current_user: Current user information

    Returns:
        ResponseModel[Dict]: Import result with workflow_id, name, warnings, and metadata
        Example response:
        {
            "code": 200,
            "message": "Workflow imported successfully",
            "data": {
                "workflow_id": "new-guid-12345",
                "workflow_name": "My Workflow (imported)",
                "warnings": ["Referenced resource may not exist: plugin_123"],
                "metadata": {
                    "original_workflow_id": "old-guid-67890",
                    "original_name": "My Workflow",
                    "source_format": "openjiuwen_native",
                    "regenerated_nodes": 5,
                    "saved_to_db": true,
                    "published": false
                }
            }
        }

    Example OpenJiuwen workflow JSON (complete, validated, ready for import):
        {
            "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "workflow_version": "draft",
            "latest_publish_time": null,
            "latest_publish_version": null,
            "name": "Customer Support Workflow",
            "desc": "Automated customer support with AI-powered responses",
            "space_id": "18630429",
            "url": "test",
            "icon_uri": "",
            "schema": "{\"nodes\":[{\"id\":\"start_abc\",\"type\":\"1\",\"position\":{\"x\":100,\"y\":100},\"data\":
                        {\"title\":\"START\",\"inputs\":{\"inputParameters\":{\"message\":{\"type\":\"value\",
                        \"content\":\"Hello\"}}}}},{\"id\":\"llm_def\",\"type\":\"3\",\"position\":{\"x\":300,
                        \"y\":100},\"data\":{\"title\":\"LLM\",\"inputs\":{\"inputParameters\":{\"prompt\":
                        {\"type\":\"ref\",\"content\":[\"start_abc\",\"message\"]}},\"llmParam\":{\"model\":
                        {\"id\":\"gpt-4\"}}}}},{\"id\":\"end_ghi\",\"type\":\"2\",\"position\":{\"x\":500,\"y\":100},
                        \"data\":{\"title\":\"END\"}}],\"edges\":[{\"id\":\"e1\",\"source\":\"start_abc\",
                        \"target\":\"llm_def\"},{\"id\":\"e2\",\"source\":\"llm_def\",\"target\":\"end_ghi\"}]}",
            "input_parameters": [
                {
                    "name": "customer_query",
                    "description": "The customer's question or issue",
                    "type": "string",
                    "required": true
                }
            ],
            "output_parameters": [
                {
                    "name": "ai_response",
                    "description": "AI-generated response",
                    "type": "string"
                }
            ],
            "create_time": 1770709211479,
            "update_time": 1770718317014
        }

        Validation (3 layers - all will PASS with above example):

        Layer 1 - WorkflowBase Schema:
        ✓ Required fields present: workflow_id, name, space_id, schema, create_time, update_time
        ✓ Field types correct: strings are strings, ints are ints
        ✓ Field constraints met: name (1-255 chars), desc (max 500 chars), url (max 500 chars)

        Layer 2 - Canvas Structure:
        ✓ Schema is valid JSON string with nodes and edges
        ✓ Has START node (type="1") - required
        ✓ Has END node (type="2") - required
        ✓ All nodes are connected via edges

        Layer 3 - Strict Validation (optional, if validate_strict=true):
        ✓ Canvas converts to DSL successfully
        ✓ Components are valid
        ✓ Workflow can be compiled and executed

        Flexible Format Support:
        The importer automatically handles different export formats:
        - Schema as JSON string (standard) OR as object (auto-converted)
        - Edges with "source"/"target" OR "sourceNodeID"/"targetNodeID" (auto-normalized)

        So you can import workflows exported from different systems without manual editing!

    Example cURL:
        curl -X POST "http://localhost:8000/workflows/import" \\
             -H "Authorization: Bearer {token}" \\
             -F "file=@workflow.json" \\
             -F "space_id=abc123" \\
             -F "validate_strict=false"
    """
    try:
        import json
        from openjiuwen_studio.core.dsl_converter.converter.importer import WorkflowImporter, ImportOptions

        logger.info(f"Workflow import request - User: {current_user.get('user_id', 'unknown')}, "
                   f"Space: {space_id}")

        # Read and parse JSON file
        try:
            content = await file.read()
            json_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file: {e}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Workflow import failed",
                data={
                    "errors": [f"Invalid JSON file: {e}"],
                    "warnings": []
                }
            )
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Workflow import failed",
                data={
                    "errors": [f"Failed to read file: {e}"],
                    "warnings": []
                }
            )

        # Build import options
        options = ImportOptions(
            validate_strict=validate_strict
        )

        # Perform import
        importer = WorkflowImporter()
        result = await importer.import_workflow(
            json_data=json_data,
            space_id=space_id,
            current_user=current_user,
            options=options
        )

        # Return result
        if result.success:
            logger.info(f"Workflow import successful: {result.workflow_id}")
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Workflow imported successfully",
                data={
                    "workflow_id": result.workflow_id,
                    "workflow_name": result.workflow_name,
                    "warnings": result.warnings,
                    "metadata": result.metadata
                }
            )
        else:
            logger.error(f"Workflow import failed: {result.errors}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Workflow import failed",
                data={
                    "errors": result.errors,
                    "warnings": result.warnings
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during workflow import: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during import: {str(e)}"
        ) from e
