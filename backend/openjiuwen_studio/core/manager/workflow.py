#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import uuid
import time
import random
from typing import Callable
from minio import Minio

from fastapi import status
from openjiuwen.core.common.logging import logger
from pydantic import ValidationError

from openjiuwen_studio.core.manager.internal.workflow import WorkflowResponseUpdate, WorkflowResponsePublish
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.utils.utils import Version, check_version
from openjiuwen_studio.core.utils.exception import log_exception
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.models.workflow import WorkflowBaseDBPd, WorkflowPublishDBPd
from openjiuwen_studio.models.agent import AgentBaseDB, AgentPublishDB
from openjiuwen_studio.schemas.workflow import WorkflowBase, WorkflowSave, WorkflowResponseSave, \
    WorkflowList, WorkflowResponse, WorkflowResponseList, WorkflowPublish, \
    WorkflowBaseResponse, WorkflowUpdate, WorkflowId, WorkflowSearchRequest, WorkflowCreate, \
    WorkflowSearchResponse, WorkflowVersionListRequest, WorkflowVersionInfo, WorkflowVersionListResponse
import openjiuwen_studio.core.manager.convertor.workflow as convert
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.manager.repositories.workflow_repository import workflow_repository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw, JiuwenBaseRepository
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.manager.workflow_tag import create_workflow_tags, get_workflow_tags, update_workflow_tags
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.schemas.space import SpaceAWPQuery
from openjiuwen_studio.core.manager.reference_extractor import extract_workflow_references, \
    check_referenced_dependencies
from openjiuwen_studio.core.manager.repositories.reference_repository import reference_repository
from openjiuwen_studio.core.manager.repositories.prompt_relation_repository import prompt_relation_repository
from openjiuwen_studio.core.common.exceptions import BaseError
from openjiuwen_studio.core.common.exceptions import JiuWenComponentException
from openjiuwen_studio.core.manager.model_manager.managers.model_config_manager import ModelConfigManager

# 生成随机字符串用于节点ID
random_id = ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_') for _ in range(5))

DEFAULT_WORKFLOW_TEXTS_ZH = {
    "start_title": "开始",
    "end_title": "结束",
    "query_default": "你好，请帮我分析一下这个问题。"
}

DEFAULT_WORKFLOW_TEXTS_EN = {
    "start_title": "Start",
    "end_title": "End",
    "query_default": "Hello, please help me analyze this question."
}


def get_default_workflow_schema():
    """获取默认工作流schema，根据当前语言返回对应文本"""
    from openjiuwen_studio.core.common.language_thread_context import get_language

    language = get_language()
    if language in ("zh-cn", "zh"):
        texts = DEFAULT_WORKFLOW_TEXTS_ZH
    else:
        texts = DEFAULT_WORKFLOW_TEXTS_EN

    return {
        "nodes": [
            {
                "id": f"start_{random_id}",
                "type": "1",
                "meta": {
                    "position": {
                        "x": 180,
                        "y": 36
                    }
                },
                "data": {
                    "title": texts["start_title"],
                    "outputs": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "default": texts["query_default"]
                            }
                        }
                    }
                }
            },
            {
                "id": f"end_{random_id}",
                "type": "2",
                "meta": {
                    "position": {
                        "x": 1100,
                        "y": 36
                    }
                },
                "data": {
                    "title": texts["end_title"],
                    "inputs": {
                        "inputParameters": {
                            "result": {}
                        }
                    },
                    "streaming": False
                }
            }
        ],
        "edges": []
    }


def with_exception_handling(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=str(e)
            )
        except BaseError as e:
            log_exception(e)
            if isinstance(e, JiuWenComponentException):
                type_name_map = {
                    ComponentType.COMPONENT_TYPE_START: "START",
                    ComponentType.COMPONENT_TYPE_LLM: "LLM",
                    ComponentType.COMPONENT_TYPE_END: "END",
                    ComponentType.COMPONENT_TYPE_IF: "IF",
                    ComponentType.COMPONENT_TYPE_LOOP: "LOOP",
                    ComponentType.COMPONENT_TYPE_INPUT: "INPUT",
                    ComponentType.COMPONENT_TYPE_OUTPUT: "OUTPUT",
                    ComponentType.COMPONENT_TYPE_QUESTION: "QUESTION",
                    ComponentType.COMPONENT_TYPE_CONTINUE: "CONTINUE",
                    ComponentType.COMPONENT_TYPE_BREAK: "BREAK",
                    ComponentType.COMPONENT_TYPE_TEXT_EDITOR: "TEXT_EDITOR",
                    ComponentType.COMPONENT_TYPE_INTENT: "INTENT",
                    ComponentType.COMPONENT_TYPE_SUB_WORKFLOW: "SUB_WORKFLOW",
                    ComponentType.COMPONENT_TYPE_EMPTY_START: "EMPTY_START",
                    ComponentType.COMPONENT_TYPE_EMPTY_END: "EMPTY_END",
                    ComponentType.COMPONENT_TYPE_CODE: "CODE",
                    ComponentType.COMPONENT_TYPE_VARIABLE_MERGE: "VARIABLE_MERGE",
                    ComponentType.COMPONENT_TYPE_SET_VARIABLE: "SET_VARIABLE",
                    ComponentType.COMPONENT_TYPE_PLUGIN: "PLUGIN",
                }
                type_name = type_name_map.get(getattr(e, "component_type", 0), str(getattr(e, "component_type", "")))
                formatted_message = f"{type_name} component [{getattr(e, 'component_id', '')}]: {e.message}"
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=formatted_message,
                    data={
                        "error_code": getattr(e, "code", -1),
                        "component_id": e.component_id,
                        "component_type": e.component_type,
                        "error_stage": e.error_stage,
                    }
                )
            else:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=e.message,
                    data={"error_code": getattr(e, "code", -1)}
                )
        except Exception as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=str(e)
            )

    return wrapper


def _process_workflow_data_list(data_list: list) -> list[WorkflowResponse]:
    """
    处理工作流数据列表的通用函数
    获取标签并构建 WorkflowResponse 对象

    Args:
        data_list: 从数据库获取的工作流数据列表

    Returns:
        处理后的 WorkflowResponse 对象列表
    """
    res_list: list[WorkflowResponse] = []

    for d in data_list:
        if not isinstance(d, dict):
            logger.warning(f"Invalid workflow data item: {d}, skipping")
            continue

        logger.debug(f"Processing workflow: {d.get('workflow_id')}")

        # 验证必要字段
        if not d.get("workflow_id") or not d.get("space_id"):
            logger.warning(f"Missing required fields in workflow data: {d}")
            continue

        # Get tags for this workflow - pass workflow_version for consistent tag retrieval
        workflow_version = d.get("workflow_version") or "draft"
        try:
            workflow_tags_result = get_workflow_tags(d.get("workflow_id"), d.get("space_id"), workflow_version)
            workflow_tags = workflow_tags_result if workflow_tags_result else []
        except Exception as e:
            logger.error(f"Error getting tags for workflow {d.get('workflow_id')}: {str(e)}")
            workflow_tags = []

        # 验证必要字段并设置默认值
        workflow_id = d.get("workflow_id")
        name = d.get("name", "Unnamed Workflow")
        desc = d.get("desc", "")
        space_id = d.get("space_id")
        create_time = d.get("create_time")
        update_time = d.get("update_time")
        input_parameters = d.get("input_parameters")
        output_parameters = d.get("output_parameters")

        # 创建工作流响应对象
        try:
            wf = WorkflowResponse(
                workflow_id=workflow_id,
                name=name,
                desc=desc,
                url=d.get("url"),
                icon_uri=d.get("icon_uri"),
                create_time=create_time,
                update_time=update_time,
                space_id=space_id,
                input_parameters=input_parameters,
                output_parameters=output_parameters,
                tags=workflow_tags
            )
            res_list.append(wf)
        except Exception as e:
            logger.error(f"Error creating WorkflowResponse for {workflow_id}: {str(e)}")
            continue

    return res_list


def _validate_and_normalize_pagination_data(data: dict, default_page: int = 1, default_page_size: int = 10) -> tuple:
    """
    验证和标准化分页数据的通用函数

    Args:
        data: 包含分页数据的字典
        default_page: 默认页码
        default_page_size: 默认页面大小

    Returns:
        (total, page, page_size, total_pages) 的元组
    """
    total = data.get("total", 0)
    page = data.get("page", default_page)
    page_size = data.get("page_size", default_page_size)
    total_pages = data.get("total_pages", 1)

    # 验证分页数据
    if not isinstance(total, int) or total < 0:
        total = 0
    if not isinstance(page, int) or page < 1:
        page = default_page
    if not isinstance(page_size, int) or page_size < 1:
        page_size = default_page_size
    if not isinstance(total_pages, int) or total_pages < 1:
        total_pages = max(1, (total + page_size - 1) // page_size)

    return total, page, page_size, total_pages


@with_exception_handling
def workflow_create(
        req: WorkflowCreate,
        current_user: dict
) -> ResponseModel:
    """创建新的工作流"""
    start_time = time.time()
    logger.info(f"Starting workflow creation request for user {current_user.get('user_id', 'unknown')}")

    _ = check_user_space(req.space_id, current_user)

    workflow_id = str(uuid.uuid4())
    current_time = milliseconds()

    workflow_schema = get_default_workflow_schema()
    inputs, outputs = convert.extract_inputs_and_outputs_from_canvas(workflow_schema)

    workflow = WorkflowBaseDBPd(
        workflow_id=workflow_id,
        name=req.name,
        desc=req.desc,
        url="test",
        icon_uri=req.icon_uri,
        space_id=req.space_id,
        create_time=current_time,
        update_time=current_time,
        schema=json.dumps(workflow_schema),
        input_parameters=inputs,
        output_parameters=outputs
    )

    logger.debug(f"create workflow info: {workflow}")
    logger.info(f"Creating workflow: {workflow.workflow_id} in space {workflow.space_id}")

    create_result = workflow_repository.workflow_create(workflow)
    logger.debug(f"create workflow info into db result: {create_result}")
    if create_result.code == status.HTTP_200_OK:
        logger.info(f"Workflow created successfully: {workflow.workflow_id}")
    if create_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=create_result.code,
            message=create_result.message,
        )

    # Process tags if provided
    processed_tags = []
    if hasattr(req, 'tags') and req.tags:
        processed_tags = create_workflow_tags(workflow_id, req.space_id, req.tags, current_user)
        logger.info(f"Processed tags for workflow {workflow_id}: {processed_tags}")

    # Add tags to workflow response
    workflow_dict = workflow.model_dump()
    workflow_dict['tags'] = processed_tags

    # Log performance metrics
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Workflow creation completed successfully in {execution_time:.3f}s - ID: {workflow.workflow_id}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create workflow success",
        data={"workflow": workflow_dict}
    )


def _sync_model_config_in_schema(schema: dict, space_id: str) -> bool:
    """
    Sync model configuration (name, type) in workflow schema with latest data from DB.
    Recursively traverses nodes and blocks.
    
    Returns:
        bool: True if any changes were made, False otherwise
    """
    has_changes = False
    
    def _traverse_and_update(nodes, model_mgr):
        nonlocal has_changes
        if not nodes:
            return
            
        for node in nodes:
            # Update model config in inputs.llmParam
            try:
                if "data" in node and "inputs" in node["data"]:
                    inputs = node["data"]["inputs"]
                    if "llmParam" in inputs:
                        llm_param = inputs["llmParam"]
                        if "model" in llm_param:
                            model_info = llm_param["model"]
                            model_id = model_info.get("id")
                            if model_id:
                                try:
                                    # Fetch latest config
                                    model_config = model_mgr.get_config_by_id(int(model_id), space_id)
                                    if model_config:
                                        # Update name and type
                                        # name in schema corresponds to model_config.name (user defined name)
                                        # type in schema corresponds to model_config.model_type (actual model type)
                                        if model_info.get("name") != model_config.name or \
                                           model_info.get("type") != model_config.model_type:
                                            model_info["name"] = model_config.name
                                            model_info["type"] = model_config.model_type
                                            has_changes = True
                                            logger.debug(f"Synced model {model_id} for node {node.get('id')}")
                                except Exception as e:
                                    # Log but don't fail the whole request if one model is missing or error
                                    logger.warning(
                                        "Failed to sync model config for node "
                                        f"{node.get('id')}, model_id {model_id}: {e}"
                                    )
            except Exception as e:
                logger.warning(f"Error processing node {node.get('id')}: {e}")

            # Recursive check for nested blocks (e.g. Loop)
            if "blocks" in node and isinstance(node["blocks"], list):
                _traverse_and_update(node["blocks"], model_mgr)

    try:
        with get_db_jw() as db:
            model_mgr = ModelConfigManager(db)
            if "nodes" in schema and isinstance(schema["nodes"], list):
                _traverse_and_update(schema["nodes"], model_mgr)
    except Exception as e:
        logger.error(f"Error in _sync_model_config_in_schema: {e}")
        
    return has_changes


@with_exception_handling
def workflow_canvas(
        req: WorkflowId,
        current_user: dict
) -> ResponseModel:
    """获取工作流画布数据"""
    _ = check_user_space(req.space_id, current_user)

    # 统一调用workflow_canvas方法，现在支持draft和publish版本
    canvas_result = workflow_repository.workflow_canvas(req)
    logger.debug(f"get workflow info from db result: {canvas_result}")
    logger.info(f"Retrieved workflow canvas: {req.workflow_id}, version: {req.workflow_version or 'draft'}")
    if canvas_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=canvas_result.code,
            message=canvas_result.message,
        )

    # 同步更新模型配置信息
    try:
        if canvas_result.data and "schema" in canvas_result.data:
            schema_str = canvas_result.data["schema"]
            if schema_str:
                schema = json.loads(schema_str)
                is_changed = _sync_model_config_in_schema(schema, req.space_id)
                
                if is_changed:
                    new_schema_str = json.dumps(schema)
                    canvas_result.data["schema"] = new_schema_str
                    
                    # 仅在草稿模式下自动保存变更
                    is_draft = not req.workflow_version or req.workflow_version == 'draft'
                    if is_draft:
                        logger.info(f"Auto-saving updated model config for workflow {req.workflow_id}")
                        update_data = {
                            "workflow_id": req.workflow_id,
                            "space_id": req.space_id,
                            "schema": new_schema_str
                        }
                        # 保存到数据库
                        workflow_repository.workflow_save(update_data)
                        
    except Exception as e:
        logger.error(f"Failed to sync model config in workflow canvas: {e}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="canvas workflow success",
        data=WorkflowBaseResponse(workflow=WorkflowBase(**canvas_result.data))
    )


@with_exception_handling
def workflow_convert(
        req: WorkflowId,
        current_user: dict,
        skip_validation: bool = False
) -> ResponseModel:
    """转换工作流数据格式"""
    _ = check_user_space(req.space_id, current_user)

    canvas_result = workflow_repository.workflow_canvas(req)
    logger.debug(f"get workflow info from db result: {canvas_result}")
    logger.info(f"Retrieved workflow canvas: {req.workflow_id}")
    if canvas_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=canvas_result.code,
            message=canvas_result.message,
        )

    workflow = convert.workflow_convert(WorkflowBase(**canvas_result.data), skip_validation=skip_validation)
    logger.debug(f"workflow info convert dl: {workflow}")
    logger.info(f"Converted workflow to data list format: {req.workflow_id}")
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="convert workflow success",
        data=workflow
    )


@with_exception_handling
def workflow_delete(
        req: WorkflowId,
        current_user: dict
) -> ResponseModel:
    """删除工作流"""
    logger.warning(
        f"Workflow deletion attempt by user {current_user.get('user_id', 'unknown')} - Workflow ID: {req.workflow_id}")
    _ = check_user_space(req.space_id, current_user)

    # 1. 检查依赖关系
    try:

        can_delete, message = check_referenced_dependencies(
            reference_repository, req.space_id, "WORKFLOW", req.workflow_id
        )

        if not can_delete:
            logger.warning(f"Workflow deletion blocked due to dependencies: {req.workflow_id} - {message}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=message,
            )
    except Exception as e:
        logger.error(f"Error checking dependencies for workflow {req.workflow_id}: {e}")
        # 依赖检查失败时，为安全起见阻止删除
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Error checking dependencies, deletion blocked for safety",
        )

    # 2. 执行删除操作
    delete_result = workflow_repository.workflow_draft_delete(req)
    logger.debug(f"delete workflow info in db result: {delete_result}")
    if delete_result.code == status.HTTP_200_OK:
        logger.info(f"Workflow deleted successfully: {req.workflow_id}")
    else:
        logger.error(f"Failed to delete workflow {req.workflow_id}: {delete_result.message}")
    if delete_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    # 3. 清理引用关系（删除成功后）
    try:
        cleanup_result = reference_repository.reference_delete_by_referer(
            req.space_id, "WORKFLOW", req.workflow_id
        )
        if cleanup_result["code"] != status.HTTP_200_OK:
            logger.warning(
                f"Failed to cleanup references for deleted workflow {req.workflow_id}: {cleanup_result['message']}")
    except Exception as e:
        logger.error(f"Error cleaning up references for workflow {req.workflow_id}: {e}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete workflow success",
    )


@with_exception_handling
def workflow_publish_delete(
        req: WorkflowId,
        current_user: dict
) -> ResponseModel:
    """删除publish工作流"""
    logger.warning(
        f"Workflow publish deletion attempt by user {current_user.get('user_id', 'unknown')} - Workflow ID: {req.workflow_id} v{req.workflow_version}")
    _ = check_user_space(req.space_id, current_user)

    # 1. 检查特定版本的依赖关系
    try:

        # 检查该特定版本是否被引用
        result = reference_repository.reference_list_by_referenced(
            req.space_id, "WORKFLOW", req.workflow_id
        )

        if result["code"] == status.HTTP_200_OK and result["data"]:
            # 检查是否有对该特定版本的引用
            version_refs = [ref for ref in result["data"] if ref.get('referenced_version') == req.workflow_version]
            if version_refs:
                referrers = []
                for ref in version_refs:
                    referrer_info = f"{ref['referer_type']}({ref['referer_id']}"
                    if ref.get('referer_version') and ref['referer_version'] != 'draft':
                        referrer_info += f":{ref['referer_version']}"
                    referrer_info += ")"
                    referrers.append(referrer_info)

                logger.warning(
                    f"Workflow publish version deletion blocked due to dependencies: {req.workflow_id}:{req.workflow_version} - referenced by {', '.join(referrers)}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Cannot delete version {req.workflow_version}: referenced by {', '.join(referrers)}",
                )
    except Exception as e:
        logger.error(f"Error checking dependencies for workflow {req.workflow_id}:{req.workflow_version}: {e}")
        # 依赖检查失败时，为安全起见阻止删除
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Error checking dependencies, deletion blocked for safety",
        )

    # 2. 执行删除操作
    delete_result = workflow_repository.workflow_publish_delete(req)
    logger.debug(f"delete workflow publish info in db result: {delete_result}")
    if delete_result.code == status.HTTP_200_OK:
        logger.info(f"Workflow publish deleted successfully: {req.workflow_id} v{req.workflow_version}")
    else:
        logger.error(f"Failed to delete workflow publish {req.workflow_id}: {delete_result.message}")
    if delete_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    # 3. 清理该版本的引用关系（删除成功后）
    try:
        cleanup_result = reference_repository.reference_delete_by_referer_with_version(
            req.space_id, "WORKFLOW", req.workflow_id, req.workflow_version
        )
        if cleanup_result["code"] != status.HTTP_200_OK:
            logger.warning(
                f"Failed to cleanup references for deleted workflow publish {req.workflow_id}:{req.workflow_version}: {cleanup_result['message']}")
    except Exception as e:
        logger.error(f"Error cleaning up references for workflow publish {req.workflow_id}:{req.workflow_version}: {e}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete workflow publish success",
    )


@with_exception_handling
def workflow_canvas_save(
        req: WorkflowSave,
        current_user: dict
) -> ResponseModel:
    start_time = time.time()
    logger.info(
        f"Starting workflow save request for user {current_user.get('user_id', 'unknown')} - Workflow ID: {req.workflow_id}")

    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    workflow_id = WorkflowId(
        workflow_id=req.workflow_id,
        space_id=req.space_id,
    )
    canvas_result = workflow_repository.workflow_canvas(workflow_id)
    logger.debug(f"get workflow info from db result: {canvas_result}")
    if canvas_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=canvas_result.code,
            message=canvas_result.message,
        )

    workflow = WorkflowBase(**canvas_result.data)

    # 2. 读取workflow.schema字段数据
    canvas_data = json.loads(req.schema)

    # Performance warning for large workflows
    schema_size = len(req.schema)
    if schema_size > 1024 * 1024:  # 1MB
        logger.warning(
            f"Large workflow data detected: {schema_size / 1024 / 1024:.2f}MB - Workflow ID: {req.workflow_id}")

    inputs, outputs = convert.extract_inputs_and_outputs_from_canvas(canvas_data)

    save_data = {
        "workflow_id": req.workflow_id,
        "space_id": req.space_id,
        "schema": req.schema,
        "input_parameters": inputs,
        "output_parameters": outputs
    }

    # 2. 读取workflow中的schema字段数据，开始调用DB的save接口进行数据保存
    save_result = workflow_repository.workflow_save(save_data)
    logger.debug(f"save workflow info into db result: {save_result}")
    if save_result and save_result.code == status.HTTP_200_OK:
        logger.info(f"Workflow saved successfully: {req.workflow_id}")
    else:
        logger.error(
            f"Failed to save workflow {req.workflow_id}: {save_result.message if save_result else 'Unknown error'}")
    if not save_result or save_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Workflow with id {req.workflow_id} save into db failed"
        )

    # 3. 管理引用关系
    try:

        # 3.1 删除旧的草稿引用关系
        delete_result = reference_repository.reference_delete_by_referer_with_version(
            req.space_id, "WORKFLOW", req.workflow_id, "draft"
        )
        if delete_result["code"] != status.HTTP_200_OK:
            logger.warning(
                f"Failed to delete old references for workflow {req.workflow_id}: {delete_result['message']}")

        # 3.2 提取并创建新的引用关系
        references = extract_workflow_references(req.schema, req.space_id, req.workflow_id, "draft")
        for ref in references:
            create_result = reference_repository.reference_create(ref)
            if create_result["code"] != status.HTTP_200_OK:
                logger.warning(f"Failed to create reference {ref}: {create_result['message']}")

        logger.info(
            f"Reference management completed for workflow {req.workflow_id}: {len(references)} references processed")
    except Exception as e:
        logger.error(f"Error managing references for workflow {req.workflow_id}: {e}")
        # 引用关系管理失败不影响主要保存功能

    res_data = WorkflowResponseSave(
        name=workflow.name,
        url=workflow.url,
        status=0,
        workflow_status=0
    )

    logger.debug(f"save workflow info response data: {res_data}")

    # Log performance metrics
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Workflow save completed successfully in {execution_time:.3f}s - ID: {req.workflow_id}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message=f"save workflow with id {req.workflow_id} into db success",
        data=res_data
    )


@with_exception_handling
def _update_workflow_name_in_agents(
        space_id: str,
        workflow_id: str,
        new_workflow_name: str,
        new_workflow_desc: str = None
) -> ResponseModel[dict]:
    """同步更新所有引用该工作流的agent配置中的工作流名称和描述"""
    with get_db_jw() as db:
        updated_count = 0
        failed_count = 0
        errors = []

        # 1. 查询并更新draft版本的agent
        agent_db = JiuwenBaseRepository(db, AgentBaseDB)
        
        # 获取所有draft版本的agent
        draft_agents = agent_db.get_dl_in_sql(
            find_id={"space_id": space_id},
            return_first_item=False
        )

        if draft_agents.code == status.HTTP_200_OK and draft_agents.data:
            for agent_data in draft_agents.data:
                try:
                    agent_id = agent_data.get("agent_id")
                    workflows = agent_data.get("workflows", [])

                    if not isinstance(workflows, list):
                        workflows = []

                    # 检查是否引用了该工作流
                    updated = False
                    for workflow in workflows:
                        if workflow.get("workflow_id") == workflow_id:
                            # 更新工作流名称和描述
                            if new_workflow_name:
                                workflow["workflow_name"] = new_workflow_name
                            if new_workflow_desc:
                                workflow["description"] = new_workflow_desc
                            updated = True

                    if updated:
                        # 更新draft版本
                        agent_data["workflows"] = workflows
                        agent_data["update_time"] = milliseconds()
                        
                        # 移除primary_id字段，避免更新时出错
                        if "primary_id" in agent_data:
                            del agent_data["primary_id"]

                        # 更新agent
                        update_result = agent_db.update_dl_in_sql(
                            find_id={
                                "agent_id": agent_id,
                                "agent_version": AgentBaseDB.__version_none__
                            },
                            update_dl=agent_data
                        )
                        
                        if update_result.code == status.HTTP_200_OK:
                            updated_count += 1
                            logger.info(
                                f"[WORKFLOW_UPDATE] Updated workflow name in agent {agent_id} (draft version)")
                        else:
                            failed_count += 1
                            errors.append(f"Failed to update agent {agent_id} (draft): {update_result.message}")

                except Exception as e:
                    failed_count += 1
                    agent_id_str = agent_data.get('agent_id', 'unknown')
                    error_msg = f"Error processing agent {agent_id_str} "
                    error_msg += f"(draft): {str(e)}"
                    errors.append(error_msg)
                    logger.error(
                        f"[WORKFLOW_UPDATE] Failed to update workflow name "
                        f"in agent {agent_id_str}: {e}")

        # 2. 查询并更新publish版本的agent
        agent_publish_db = JiuwenBaseRepository(db, AgentPublishDB)
        
        # 获取所有publish版本的agent
        publish_agents = agent_publish_db.get_dl_in_sql(
            find_id={"space_id": space_id},
            return_first_item=False
        )

        if publish_agents.code == status.HTTP_200_OK and publish_agents.data:
            for agent_data in publish_agents.data:
                try:
                    agent_id = agent_data.get("agent_id")
                    agent_version = agent_data.get("agent_version")
                    workflows = agent_data.get("workflows", [])

                    if not isinstance(workflows, list):
                        workflows = []

                    # 检查是否引用了该工作流
                    updated = False
                    for workflow in workflows:
                        if workflow.get("workflow_id") == workflow_id:
                            # 更新工作流名称和描述
                            if new_workflow_name:
                                workflow["workflow_name"] = new_workflow_name
                            if new_workflow_desc:
                                workflow["description"] = new_workflow_desc
                            updated = True

                    if updated:
                        # 更新publish版本
                        agent_data["workflows"] = workflows
                        agent_data["update_time"] = milliseconds()
                        
                        # 移除primary_id字段，避免更新时出错
                        if "primary_id" in agent_data:
                            del agent_data["primary_id"]

                        # 更新publish版本
                        update_result = agent_publish_db.update_dl_in_sql(
                            find_id={
                                "agent_id": agent_id,
                                "agent_version": agent_version
                            },
                            update_dl=agent_data
                        )
                        
                        if update_result.code == status.HTTP_200_OK:
                            updated_count += 1
                            logger.info(
                                f"[WORKFLOW_UPDATE] Updated workflow name in agent {agent_id} "
                                f"(publish v{agent_version})")
                        else:
                            failed_count += 1
                            error_msg = f"Failed to update agent {agent_id} v{agent_version} "
                            error_msg += f"(publish): {update_result.message}"
                            errors.append(error_msg)

                except Exception as e:
                    failed_count += 1
                    agent_id_str = agent_data.get('agent_id', 'unknown')
                    error_msg = f"Error processing agent {agent_id_str} "
                    error_msg += f"(publish): {str(e)}"
                    errors.append(error_msg)
                    logger.error(
                        f"[WORKFLOW_UPDATE] Failed to update workflow name "
                        f"in agent {agent_id_str} (publish): {e}")

        return ResponseModel(
            code=status.HTTP_200_OK,
            message=f"Updated workflow name in agents: {updated_count} updated, {failed_count} failed",
            data={
                "updated_count": updated_count,
                "failed_count": failed_count,
                "errors": errors if errors else None
            }
        )


@with_exception_handling
def workflow_meta_update(
        req: WorkflowUpdate,
        current_user: dict
) -> ResponseModel:
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 构建更新数据，只包含非空字段
    update_data = {
        "workflow_id": req.workflow_id,
        "space_id": req.space_id
    }

    # 只添加非空字段到更新数据中
    if req.name is not None:
        update_data["name"] = req.name
    if req.desc is not None:
        update_data["desc"] = req.desc
    if req.url is not None:
        update_data["url"] = req.url
    if req.icon_uri is not None:
        update_data["icon_uri"] = req.icon_uri

    # 3. 更新工作流基本信息
    update_result = workflow_repository.workflow_save(update_data)
    logger.debug(f"update workflow meta into db result: {update_result}")
    if update_result and update_result.code == status.HTTP_200_OK:
        logger.info(f"Workflow metadata updated successfully: {req.workflow_id}")
    else:
        logger.error(
            f"Failed to update workflow metadata {req.workflow_id}: {update_result.message if update_result else 'Unknown error'}")
    if not update_result or update_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Workflow with id {req.workflow_id} save into db failed"
        )

    # 4. 处理标签（如果提供了标签）- 使用增量更新来提升性能
    processed_tags = []
    if req.tags is not None:
        try:
            processed_tags = update_workflow_tags(req.workflow_id, req.space_id, req.tags, current_user)
            logger.info(f"Updated tags incrementally for workflow {req.workflow_id}: {processed_tags}")
        except ValueError as e:
            # 处理tag数量限制错误
            logger.warning(f"Tag update failed for workflow {req.workflow_id}: {str(e)}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=str(e)
            )

    # 5. 同步更新所有引用该工作流的agent配置中的工作流名称和描述
    if req.name is not None or req.desc is not None:
        sync_result = _update_workflow_name_in_agents(
            space_id=req.space_id,
            workflow_id=req.workflow_id,
            new_workflow_name=req.name,
            new_workflow_desc=req.desc
        )
        logger.info(
            f"Synced workflow name in agents: {sync_result.data['updated_count']} updated, "
            f"{sync_result.data['failed_count']} failed"
        )

    # 6. 同步更新 prompt_relation 表中该工作流关联记录的 name（id 格式为 workflow_id&node_id）
    if req.name is not None:
        pr_result = prompt_relation_repository.update_member_name_in_prompt_relation(
            space_id=req.space_id,
            member_type="WORKFLOW",
            member_id=req.workflow_id,
            new_name=req.name,
        )
        if pr_result.code == status.HTTP_200_OK:
            logger.info(f"Synced workflow name in prompt_relation: {pr_result.message}")
        else:
            logger.warning(f"Sync workflow name in prompt_relation failed: {pr_result.message}")

    res_data = WorkflowResponseUpdate(
        workflow_id=req.workflow_id,
        success=True
    )

    logger.debug(f"update workflow meta response data: {res_data}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message=f"save workflow with id {req.workflow_id} into db success",
        data=res_data.model_dump()
    )


@with_exception_handling
def workflow_list(
        req: WorkflowList,
        current_user: dict
) -> ResponseModel:
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 调用repository列表接口
    list_result = workflow_repository.workflow_list(SpaceAWPQuery.model_validate(req.model_dump()))
    logger.debug(f"get workflow list from db result: {list_result.code}")

    if list_result.code == status.HTTP_404_NOT_FOUND or list_result.code == status.HTTP_400_BAD_REQUEST:
        return ResponseModel(
            code=status.HTTP_200_OK,
            message=f"Get workflow list with space_id {req.space_id} failed, error: {list_result.message}",
        )
    elif list_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=list_result.code,
            message=f"Get workflow list with space_id {req.space_id} failed, error: {list_result.message}",
        )

    # 3. 处理工作流数据
    data_list = list_result.data.get("workflow_list", [])
    res_list = _process_workflow_data_list(data_list)

    # 4. 验证和标准化分页数据
    total, page, page_size, total_pages = _validate_and_normalize_pagination_data(
        list_result.data,
        default_page=req.page or 1,
        default_page_size=req.page_size or 10
    )

    # 5. 构建响应数据
    res_data = WorkflowResponseList(
        workflow_list=res_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    logger.info(
        f"get workflow list success: {len(res_data.workflow_list)} workflows, page {res_data.page}/{res_data.total_pages}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Get workflow list success",
        data=res_data
    )


@with_exception_handling
def workflow_search(
        req: WorkflowSearchRequest,
        current_user: dict
) -> ResponseModel:
    """搜索工作流"""
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 构建搜索参数
    search_params = {
        "space_id": req.space_id,
        "search_term": req.search_term or "",
        "tags": req.tags or [],
        "status_filter": req.status_filter or "all",
        "sort_by": req.sort_by.value if req.sort_by else "update_time",
        "sort_order": req.sort_order.value if req.sort_order else "desc",
        "page": req.page or 1,
        "page_size": req.page_size or 10
    }

    # 3. 调用repository搜索接口
    try:
        search_result = workflow_repository.workflow_search(search_params)
        logger.debug(f"search workflow from db result: {search_result.code}")

        if search_result.code != status.HTTP_200_OK:
            return ResponseModel(
                code=search_result.code,
                message=f"Search workflow with space_id {req.space_id} failed, error: {search_result.message}",
            )
    except Exception as e:
        logger.error(f"Search workflow exception: {str(e)}")
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Search workflow with space_id {req.space_id} failed, error: {str(e)}"
        )

    # 4. 验证搜索结果数据结构
    if not search_result.data or not isinstance(search_result.data, dict):
        logger.warning(f"Invalid search result data structure: {search_result.data}")
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Invalid search result data structure"
        )

    # 5. 处理工作流数据
    data_list = search_result.data.get("workflow_list", [])
    if not isinstance(data_list, list):
        logger.warning(f"Invalid workflow_list in search result: {data_list}")
        data_list = []

    res_list = _process_workflow_data_list(data_list)

    # 6. 验证和标准化分页数据
    total, page, page_size, total_pages = _validate_and_normalize_pagination_data(
        search_result.data,
        default_page=req.page or 1,
        default_page_size=req.page_size or 10
    )

    # 7. 构建搜索响应数据
    try:
        res_data = WorkflowSearchResponse(
            workflow_list=res_list,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            search_term=req.search_term,
            filters={
                "tags": req.tags or [],
                "status_filter": req.status_filter or "all",
                "sort_by": search_params["sort_by"],
                "sort_order": search_params["sort_order"]
            }
        )
        logger.info(
            f"search workflow success: {len(res_data.workflow_list)} results for term '{req.search_term}', page {res_data.page}/{res_data.total_pages}")
    except Exception as e:
        logger.error(f"Error creating WorkflowSearchResponse: {str(e)}")
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error creating search response: {str(e)}"
        )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Search workflow success",
        data=res_data
    )


def deal_db_error(result: ResponseModel) -> ResponseModel:
    if result is None:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="publish workflow failed, error: result can not be None",
            data=None
        )

    if result.code == status.HTTP_400_BAD_REQUEST or result.code == status.HTTP_404_NOT_FOUND:
        return ResponseModel(
            code=status.HTTP_200_OK,
            message=f"publish workflow failed, error: {result.message}",
            data=None
        )

    return ResponseModel(
        code=result.code,
        message=f"publish workflow failed, error: {result.message}",
        data=None
    )


@with_exception_handling
def workflow_publish(
        req: WorkflowPublish,
        current_user: dict
) -> ResponseModel:
    start_time = time.time()
    logger.warning(
        f"Workflow publish attempt by user {current_user.get('user_id', 'unknown')} - Workflow ID: {req.workflow_id}, Version: {req.workflow_version}")
    logger.info(
        f"Starting workflow publish request for user {current_user.get('user_id', 'unknown')} - Workflow ID: {req.workflow_id}, Version: {req.workflow_version}")

    try:
        # 1. 校验Space_id是否有权限
        _ = check_user_space(req.space_id, current_user)

        workflow_latest_version_query = WorkflowId(
            workflow_id=req.workflow_id,
            space_id=req.space_id,
            workflow_version="latest_publish_version"
        )
        # 2. 获取lasted version信息
        get_version_result = workflow_repository.workflow_publish_get(workflow_latest_version_query)
        logger.debug(f"get version workflow info: {get_version_result}")
        if get_version_result.code == status.HTTP_200_OK:
            logger.info(f"Retrieved latest version for workflow: {req.workflow_id}")
        is_latest_found = True
        if get_version_result.code == status.HTTP_404_NOT_FOUND:
            is_latest_found = False
        elif get_version_result.code != status.HTTP_200_OK:
            return ResponseModel(
                code=get_version_result.code,
                message=f"Get versioned workflow with id {req.workflow_id} failed, error: {get_version_result.message}",
                data=None
            )

        if is_latest_found:
            try:
                latest_version_data = WorkflowPublishDBPd(**get_version_result.data)
            except Exception as e:
                logger.error(f"Failed to parse latest version data: {str(e)}")
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Invalid latest version data format: {str(e)}",
                    data=None
                )
        else:
            latest_version_data = None

        # 3. 判断当前版本格式是否正确，且version是否为递增的
        try:
            if latest_version_data:
                check_res, check_err = check_version(latest_version_data.workflow_version, req.workflow_version)
                logger.info(f"get latest workflow info, check version {check_res}")
                if not check_res:
                    return ResponseModel(
                        code=status.HTTP_400_BAD_REQUEST,
                        message=f"check version failed, error: {check_err}",
                        data=None
                    )
            else:
                current_version, check_err = Version.string_to_object(req.workflow_version)
                logger.info(f"no latest workflow info, check version {check_err is None}")
                if check_err is not None:
                    return ResponseModel(
                        code=status.HTTP_400_BAD_REQUEST,
                        message=f"check version {req.workflow_version} failed, error: {check_err}",
                        data=None
                    )
        except Exception as e:
            logger.error(f"Version validation error: {str(e)}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"Version validation failed: {str(e)}",
                data=None
            )

        # 4. 获取draft数据库中workflow的信息
        workflow_draft_query = WorkflowId(
            workflow_id=req.workflow_id,
            space_id=req.space_id
        )
        canvas_result = workflow_repository.workflow_canvas(workflow_draft_query)
        logger.info(f"get draft workflow info: {canvas_result}")
        if canvas_result.code != status.HTTP_200_OK:
            return ResponseModel(
                code=canvas_result.code,
                message=f"Get workflow with id {req.workflow_id} failed, error: {canvas_result.message}",
                data=None
            )

        try:
            wf_data = WorkflowBaseDBPd(**canvas_result.data)
        except Exception as e:
            logger.error(f"Failed to parse workflow data: {str(e)}")
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Invalid workflow data format: {str(e)}",
                data=None
            )

        # 5. 使用flow_mgr进行工作流校验
        try:
            logger.info(f"validating workflow {req.workflow_id} before publish")
            from openjiuwen_studio.core.executor.workflow.workflow_runner import flow_mgr
            flow_mgr.validate(req.workflow_id, "draft", req.space_id, current_user)
            logger.info(f"workflow {req.workflow_id} validation passed")
        except Exception as e:
            logger.error(f"workflow validation failed for {req.workflow_id}: {str(e)}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"Workflow validation failed: {str(e)}",
                data=None
            )

        # 6. 构建publish需要的WorkflowDBVersion结构，并将其存入数据库中
        try:
            # 获取工作流基础数据，明确排除 workflow_version 字段以避免冲突
            workflow_data = wf_data.model_dump(exclude_none=True, exclude={"workflow_version"})

            # 更新时间戳为当前发布时间
            current_time = milliseconds()
            workflow_data["create_time"] = current_time
            workflow_data["update_time"] = current_time

            # 添加发布版本必需的字段
            workflow_data["workflow_version"] = req.workflow_version
            workflow_data["version_description"] = req.version_description

            logger.info(f"Creating version data with workflow_version: {req.workflow_version}")
            logger.debug(f"Version data keys: {list(workflow_data.keys())}")

            # 创建发布版本数据
            version_data = WorkflowPublishDBPd(**workflow_data)

        except Exception as e:
            logger.error(f"Failed to create version data: {str(e)}")

            try:
                test_data = wf_data.model_dump(exclude_none=True)
                logger.error(f"exclude_none data: {test_data}")
                for key, value in test_data.items():
                    logger.error(f"Field {key}: {value} (type: {type(value)})")
            except Exception as debug_e:
                logger.error(f"Debug error: {str(debug_e)}")

            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to prepare version data: {str(e)}",
                data=None
            )

        try:
            publish_result = workflow_repository.workflow_publish(version_data)
            logger.debug(f"publish workflow info result: {publish_result}")
            if publish_result.code == status.HTTP_200_OK:
                logger.info(f"Workflow published successfully: {req.workflow_id} version {req.workflow_version}")
            else:
                logger.error(f"Failed to publish workflow {req.workflow_id}: {publish_result.message}")
            if publish_result.code != status.HTTP_200_OK:
                return deal_db_error(publish_result)
        except Exception as e:
            logger.error(f"Failed to publish workflow to database: {str(e)}")
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Database publish operation failed: {str(e)}",
                data=None
            )

        # 4. 管理发布版本的引用关系
        try:

            # 4.1 提取并创建发布版本的引用关系
            references = extract_workflow_references(
                wf_data.schema, req.space_id, req.workflow_id, req.workflow_version)
            for ref in references:
                create_result = reference_repository.reference_create(ref)
                if create_result["code"] != status.HTTP_200_OK:
                    logger.warning(f"Failed to create publish reference {ref}: {create_result['message']}")

            logger.info(
                f"Publish reference management completed for workflow {req.workflow_id} v{req.workflow_version}: {len(references)} references processed")
        except Exception as e:
            logger.error(f"Error managing publish references for workflow {req.workflow_id}: {e}")
            # 引用关系管理失败不影响主要发布功能

        try:
            res_data = WorkflowResponsePublish(
                workflow_id=req.workflow_id,
                success=True
            )
        except Exception as e:
            logger.error(f"Failed to create response data: {str(e)}")
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to create response: {str(e)}",
                data=None
            )

        # Log performance metrics
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(
            f"Workflow publish completed successfully in {execution_time:.3f}s - ID: {req.workflow_id}, Version: {req.workflow_version}")

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="publish workflow success",
            data=res_data
        )

    except Exception as e:
        logger.error(f"Unexpected error in workflow_publish: {str(e)}")
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Unexpected error during workflow publish: {str(e)}",
            data=None
        )


@with_exception_handling
def workflow_copy(
        req: WorkflowId,
        current_user: dict
) -> ResponseModel:
    """创建新的工作流"""
    _ = check_user_space(req.space_id, current_user)

    # 重新创建一个id
    workflow_copy_id = str(uuid.uuid4())
    current_time = milliseconds()

    # draft版本
    if not req.workflow_version:
        get_result = workflow_repository.workflow_canvas(req)
    # 发布版本
    else:
        get_result = workflow_repository.workflow_publish_get(req)
    if get_result.code != status.HTTP_200_OK:
        logger.info(f"Copy workflow fail: {get_result}")
        return get_result

    # 获取原始工作流的标签信息
    original_workflow_id = get_result.data.get("workflow_id")
    if original_workflow_id:
        try:
            original_tags = get_workflow_tags(original_workflow_id, req.space_id, req.workflow_version or "draft")
            tag_names = [tag.get("tag_name") for tag in original_tags if tag.get("tag_name")]
            logger.info(f"Original workflow tags found: {tag_names}")
        except Exception as e:
            logger.error(f"Error getting original workflow tags: {e}")
            tag_names = []
    else:
        tag_names = []

    get_result.data.pop("workflow_version", None)  # 复制的workflow只能生成draft版本
    workflow_base_copy = WorkflowBaseDBPd(**get_result.data)
    workflow_base_copy.workflow_id = workflow_copy_id
    workflow_base_copy.create_time = current_time
    workflow_base_copy.update_time = current_time
    workflow_base_copy.name = workflow_base_copy.name + "_copy"

    logger.debug(f"copy workflow info: {workflow_base_copy}")
    logger.info(f"Copying workflow: {req.workflow_id} -> {workflow_copy_id}")

    copy_result = workflow_repository.workflow_create(workflow_base_copy)
    logger.debug(f"copy workflow info into db result: {copy_result}")
    if copy_result.code == status.HTTP_200_OK:
        logger.info(f"Workflow copied successfully: {req.workflow_id} -> {workflow_copy_id}")
    else:
        logger.error(f"Failed to copy workflow {req.workflow_id}: {copy_result.message}")
    if copy_result.code != status.HTTP_200_OK:
        return copy_result

    # 复制标签到新的工作流
    if tag_names:
        try:
            create_workflow_tags(workflow_copy_id, req.space_id, tag_names, current_user)
            logger.info(f"Successfully copied {len(tag_names)} tags to workflow {workflow_copy_id}")
        except Exception as e:
            logger.error(f"Error copying tags to new workflow: {e}")
            # 标签复制失败不影响工作流复制的主要功能
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="copy workflow success",
        data=WorkflowBaseResponse(workflow=WorkflowBase(**workflow_base_copy.model_dump()))
    )


def resolve_ref_types(output_parameters: list[dict], schema_str: str) -> list[dict]:
    """Resolve ref and constant types to actual types."""
    if not output_parameters or not schema_str:
        return output_parameters

    try:
        schema = json.loads(schema_str)
        nodes = {node["id"]: node for node in schema.get("nodes", [])}

        # Find end node
        end_node = next((node for node in nodes.values()
                         if node.get("type") == str(ComponentType.COMPONENT_TYPE_END)), None)
        if not end_node:
            return output_parameters

        input_params = end_node.get("data", {}).get("inputs", {}).get("inputParameters", {})

        # Resolve types in-place
        for param in output_parameters:
            param_def = input_params.get(param["name"])
            if not param_def:
                continue

            param_type = param["type"]

            if param_type == "ref":
                content = param_def.get("content", [])
                if len(content) >= 2:  # Need at least 2 elements: node_id and output_name
                    node_id, output_name = content[0], content[1]
                    node = nodes.get(node_id)
                    if node:
                        outputs = node.get("data", {}).get("outputs", {})
                        if outputs.get("type") == "object":
                            param["type"] = outputs.get("properties", {}).get(output_name, {}).get("type")
                        else:
                            param["type"] = outputs.get("type")

            elif param_type == "constant":
                schema_type = param_def.get("schema", {}).get("type")
                if schema_type:
                    param["type"] = schema_type

        return output_parameters
    except Exception as e:
        logger.error(f"Error resolving ref types: {type(e).__name__}")
        return output_parameters


@with_exception_handling
def workflow_version_list(
        req: WorkflowVersionListRequest,
        current_user: dict
) -> ResponseModel:
    """查询工作流的发布版本列表"""
    _ = check_user_space(req.space_id, current_user)

    # 调用repository查询版本列表
    version_result = workflow_repository.get_workflow_publish_list(WorkflowId.model_validate(req.model_dump()))
    logger.debug(f"get workflow version list result: {version_result}")
    if version_result.code == status.HTTP_200_OK:
        logger.info(f"Retrieved version list for workflow: {req.workflow_id}")
    else:
        logger.warning(f"Failed to retrieve version list for workflow {req.workflow_id}: {version_result.message}")

    # 处理404情况，返回200和空列表
    if version_result.code == status.HTTP_404_NOT_FOUND:
        logger.info(f"No published versions found for workflow {req.workflow_id}, returning empty list")
        response_data = WorkflowVersionListResponse(
            workflow_id=req.workflow_id,
            versions=[]
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="No workflow version was found",
            data=response_data
        )

    if version_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=version_result.code,
            message=version_result.message,
            data=None
        )

    # 构建返回数据
    version_data = version_result.data or []
    versions = []

    for version_info in version_data:
        versions.append(WorkflowVersionInfo(
            workflow_version=version_info.get("workflow_version", ""),
            version_description=version_info.get("version_description", ""),
            create_time=version_info.get("create_time", 0)
        ))

    response_data = WorkflowVersionListResponse(
        workflow_id=req.workflow_id,
        versions=versions
    )

    logger.info(f"get workflow version list success: {len(versions)} versions for workflow {req.workflow_id}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Get workflow version list success",
        data=response_data
    )


# @with_exception_handling
def get_upload_url(
        req: dict,
        current_user: dict,
        minio_client: Minio
) -> ResponseModel:
    """获取文件上传自签名URL"""
    space_id = req.get("space_id")
    object_key = req.get("object_key")

    if not all([space_id, object_key]):
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Missing required fields: object_key or space_id"
        )
    # 1. 校验用户是否有权限访问该space
    _ = check_user_space(space_id, current_user)

    # 2. 生成 MinIO 上传 URL
    bucket_name = settings.minio_bucket

    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        logger.info(f"桶 '{bucket_name}' 创建成功")
    else:
        logger.info(f"桶 '{bucket_name}' 已存在")

    from datetime import timedelta
    upload_url = minio_client.presigned_put_object(
        bucket_name=bucket_name,
        object_name=object_key,
        expires=timedelta(hours=1)
    )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Get upload_url success",
        data={"upload_url": upload_url}
    )


# @with_exception_handling
def get_download_url(
        req: dict,
        current_user: dict,
        minio_client: Minio
) -> ResponseModel:
    """获取文件上传自签名URL"""
    space_id = req.get("space_id")
    object_key = req.get("object_key")

    if not all([space_id, object_key]):
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Missing required fields: object_key or space_id"
        )
    # 1. 校验用户是否有权限访问该space
    _ = check_user_space(space_id, current_user)

    # 2. 生成 MinIO 下载 URL
    bucket_name = settings.minio_bucket

    try:
        # 检查对象是否存在
        minio_client.stat_object(bucket_name, object_key)
    except Exception as e:
        logger.error(f"Object not found in MinIO: {object_key}, error: {str(e)}")
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message=f"File {object_key} not found in storage"
        )

    # 生成永久公开访问URL
    protocol = "https" if settings.minio_secure else "http"
    download_url = f"{protocol}://{settings.minio_host}:{settings.minio_port}/{bucket_name}/{object_key}"

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Get download_url success",
        data={"download_url": download_url}
    )
