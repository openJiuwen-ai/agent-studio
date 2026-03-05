#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import datetime
import functools
import io
import json
import math
import os
import shutil
import time
import uuid
import zipfile
from pathlib import Path
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Type, Set, Any, Dict, Optional, Union, Tuple

from fastapi import status
from openjiuwen.core.common.logging import logger
from pydantic import BaseModel, ValidationError
from pymilvus import connections
import psutil
from openjiuwen_studio.core.common.agent_defaults import AgentDefaults

import openjiuwen_studio.core.manager.knowledge_base as kb_mgr
import openjiuwen_studio.core.manager.convertor.agent as convert
from openjiuwen_studio.core.common.dsl import AgentEditMode
from openjiuwen_studio.core.common.language_thread_context import get_language
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.internal.agent import (
    AgentItem,
    AgentListInfo,
    AgentListPagination,
    AgentModelListNode,
    AgentOptionInfo,
    AgentWorkflowListNode,
    SingleAgentData,
)
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.model_manager.managers import ModelConfigManager
from openjiuwen_studio.core.manager.reference_extractor import extract_agent_references
from openjiuwen_studio.core.manager.repositories.agent_repository import (
    agent_repository,
)
from openjiuwen_studio.core.manager.repositories.reference_repository import (
    reference_repository,
)
from openjiuwen_studio.core.manager.repositories.workflow_repository import (
    workflow_repository,
)
from openjiuwen_studio.core.manager.repositories.plugin_repository import (
    plugin_repository,
)
from openjiuwen_studio.core.manager.repositories.knowledge_base_repository import (
    knowledge_base_repository,
)
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.core.manager.repositories.tool_repository import tool_repository
from openjiuwen_studio.ops.dependencies import get_db_ops, get_db_agent
from openjiuwen_studio.core.manager.utils.utils import (
    Version,
    check_version,
    get_current_project_version,
)
from openjiuwen_studio.models.agent import AgentBaseDBPd, AgentModelConfig
from openjiuwen_studio.models.agent import AgentPublishDBPd
from openjiuwen_studio.models.embedding_model_config import EmbeddingModelConfig
from openjiuwen_studio.models.knowledge_base_document import KnowledgeBaseDocumentDB
from openjiuwen_studio.models.workflow import WorkflowBaseDBPd
from openjiuwen_studio.core.manager.repositories.prompt_relation_repository import (
    prompt_relation_repository,
)
from openjiuwen_studio.schemas import related_member
from sqlalchemy import and_
from openjiuwen_studio.ops.modules.prompt.infra.repositories.orm_repo import (
    PromptBasicModel,
    PromptCommitModel,
    PromptUserDraftModel,
)
from openjiuwen_studio.schemas.agent import (
    AGENT_NAME_MAX_SIZE,
    AgentConstraint,
    AgentCopy,
    AgentCreate,
    AgentDisplayInfo,
    AgentGet,
    AgentGetVersion,
    AgentId,
    AgentList,
    AgentModel,
    AgentPublish,
    AgentResponseCreate,
    AgentResponsePublish,
    AgentSearchRequest,
    AgentUpdate,
    AgentVersionInfo,
    AgentVersionListRequest,
    AgentVersionListResponse,
    AgentExportRequest,
    AgentImportRequest,
    AgentExportData,
    AgentDependencies,
    AgentExportMetadata,
    ModelReference,
)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.model_config import ModelParameters
from openjiuwen_studio.schemas.space import SpaceAWPQuery
from openjiuwen_studio.schemas.plugin import (
    PluginCreate,
    PluginApiInfo,
    PluginCodeInfo,
    PluginApiMethod,
    PluginType,
)
from openjiuwen_studio.schemas.knowledge_base import (
    KnowledgeBaseGet,
    ParsingStrategy,
    SegmentationStrategy,
    IndexingStrategy,
)
from openjiuwen_studio.core.manager.convertor.components.plugin import (
    param_type_mapping,
)

if TYPE_CHECKING:
    # 只为类型检查器服务，运行时不执行
    AgentBaseDBPd: Type[BaseModel]

# Current index manager type from environment
_CURR_INDEX_TYPE = os.getenv("INDEX_MANAGER_TYPE", "milvus")

DEFAULT_PAGE = 1


DEFAULT_PAGE_SIZE = 10


@contextmanager
def get_db_ops_session():
    """Helper to get ops database session as context manager"""
    gen = get_db_ops()
    try:
        db = next(gen)
        yield db
    finally:
        gen.close()


@contextmanager
def get_db_agent_session():
    """Helper to get agent database session as context manager"""
    gen = get_db_agent()
    try:
        db = next(gen)
        yield db
    finally:
        gen.close()


def with_exception_handling(func: Callable) -> Callable:
    """增强的异常处理装饰器，提供统一的错误处理、性能监控和日志记录"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__

        # 尝试从参数中提取用户信息
        user_id = "unknown"
        if len(args) >= 2:
            # 假设第二个参数是current_user字典
            current_user = args[1]
            if isinstance(current_user, dict):
                data = current_user.get("data", "unknown")
                user_id = data["user_id_str"]

        operation_tag = func_name.upper().replace("AGENT_", "[AGENT_")

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 记录成功执行的性能指标
            if hasattr(result, "code") and result.code == status.HTTP_200_OK:
                logger.debug(
                    f"{operation_tag}] Performance - User: {user_id}, Duration: {execution_time:.3f}s"
                )

            return result

        except ValidationError as e:
            execution_time = time.time() - start_time
            # 构造友好的错误信息
            error_msg = ", ".join(
                [
                    f"{'.'.join(map(str, err['loc'])) if isinstance(err['loc'], tuple) else str(err['loc'])}: "
                    f"{err['msg']}"
                    for err in e.errors()
                ]
            )
            logger.error(
                f"{operation_tag} Validation failed - User: {user_id}, "
                f"Duration: {execution_time:.3f}s, Errors: {e.errors()}"
            )

            return ResponseModel(
                code=StatusCode.AGENT_VALIDATION_ERROR.code,
                message=StatusCode.AGENT_VALIDATION_ERROR.errmsg.format(msg=error_msg),
            )

        except ValueError as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(
                f"{operation_tag}] Invalid value - User: {user_id}, Duration: {execution_time:.3f}s, Error: {error_msg}"
            )

            return ResponseModel(
                code=StatusCode.AGENT_INVALID_VALUE.code,
                message=StatusCode.AGENT_INVALID_VALUE.errmsg.format(msg=error_msg),
            )

        except KeyError as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(
                f"{operation_tag}] Missing required field - User: {user_id}, "
                f"Duration: {execution_time:.3f}s, Error: {error_msg}"
            )

            return ResponseModel(
                code=StatusCode.AGENT_MISSING_FIELD.code,
                message=StatusCode.AGENT_MISSING_FIELD.errmsg.format(msg=error_msg),
            )

        except TimeoutError as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(
                f"{operation_tag}] Operation timeout - User: {user_id}, "
                f"Duration: {execution_time:.3f}s, Error: {error_msg}"
            )

            return ResponseModel(
                code=StatusCode.AGENT_TIMEOUT.code,
                message=StatusCode.AGENT_TIMEOUT.errmsg.format(msg=error_msg),
            )

        except ConnectionError as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(
                f"{operation_tag}] Database connection error - User: {user_id}, "
                f"Duration: {execution_time:.3f}s, Error: {error_msg}"
            )

            return ResponseModel(
                code=StatusCode.AGENT_DB_CONNECTION_ERROR.code,
                message=StatusCode.AGENT_DB_CONNECTION_ERROR.errmsg.format(
                    msg=error_msg
                ),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_type = type(e).__name__
            error_msg = str(e)

            # 记录详细的错误信息包括堆栈跟踪
            logger.error(
                f"{operation_tag}] Unexpected error - User: {user_id}, Duration: {execution_time:.3f}s, "
                f"Type: {error_type}, Error: {error_msg}",
                exc_info=True,
            )

            # 根据错误类型返回不同的状态码
            if "database" in error_msg.lower() or "sql" in error_type.lower():
                status_code = StatusCode.AGENT_DATABASE_OPERATION_ERROR.code
                message = StatusCode.AGENT_DATABASE_OPERATION_ERROR.errmsg
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                status_code = StatusCode.AGENT_NETWORK_CONNECTION_ERROR.code
                message = StatusCode.AGENT_NETWORK_CONNECTION_ERROR.errmsg
            elif (
                "permission" in error_msg.lower() or "unauthorized" in error_msg.lower()
            ):
                status_code = StatusCode.AGENT_PERMISSION_ERROR.code
                message = StatusCode.AGENT_PERMISSION_ERROR.errmsg
            else:
                status_code = StatusCode.AGENT_INTERNAL_SERVER_ERROR.code
                message = StatusCode.AGENT_INTERNAL_SERVER_ERROR.errmsg.format(
                    msg=error_type
                )

            return ResponseModel(code=status_code, message=message)

    return wrapper


def create_agent_react_info(req: AgentCreate) -> AgentBaseDBPd:
    # 1 生成agent_id
    agent_id = str(uuid.uuid4())
    current_time = milliseconds()

    # 2 获取和agent绑定的workflow信息列表
    constraint = AgentConstraint()

    default_agent_info = AgentBaseDBPd(
        agent_id=agent_id,
        agent_name=req.agent_name,
        space_id=req.space_id,
        description=req.description,
        agent_type=req.agent_type,
        # configs=configs,  # 待configs功能完善后再获取
        icon=req.icon,
        edit_mode=AgentEditMode.Manual,
        # plugins=plugins,  # 待plugins功能完善后再获取
        # model=req.model,
        constraint=constraint.model_dump(),
        opening_remarks=AgentDefaults.OPENING_REMARKS.msg,
        create_time=current_time,
        update_time=current_time,
    )

    return default_agent_info


@with_exception_handling
def agent_react_create(req: AgentCreate, current_user: dict) -> ResponseModel:
    """创建新的智能体"""
    start_time = time.time()
    # 从current_user中正确获取user_id_str
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )

    logger.info(
        f"[AGENT_CREATE] Creating agent - User: {user_id}, Name: {req.agent_name}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 生成agent_info信息
    agent_info = create_agent_react_info(req)
    logger.debug(f"[AGENT_CREATE] Generated agent ID: {agent_info.agent_id}")

    # 3. 保存agent_info信息至DB中
    create_result = agent_repository.create_agent_db(agent_info)

    if create_result.code != status.HTTP_200_OK:
        logger.error(
            f"[AGENT_CREATE] Database save failed - ID: {agent_info.agent_id}, Error: {create_result.message}"
        )
        return ResponseModel(
            code=create_result.code,
            message=create_result.message,
        )

    # 4. 准备响应数据
    response_data = AgentResponseCreate(id=agent_info.agent_id)

    logger.info(
        f"[AGENT_CREATE] Agent created - ID: {agent_info.agent_id}, User: {user_id}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )

    # 5. 返回创建结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create agent success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
def agent_delete(req: AgentGet, current_user: dict) -> ResponseModel:
    """删除已有的智能体的draft+publish数据"""
    start_time = time.time()
    # 从current_user中正确获取user_id_str
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )

    logger.info(f"[AGENT_DELETE] Deleting agent - User: {user_id}, ID: {req.agent_id}")

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 构建删除查询参数
    agent_query = AgentId(
        space_id=req.space_id,
        agent_id=req.agent_id,
        agent_version=None
    )

    # 3. 从DB中删除agent及其所有版本
    delete_result = agent_repository.delete_agent_db(agent_query)

    if delete_result.code != status.HTTP_200_OK:
        logger.error(
            f"[AGENT_DELETE] Database deletion failed - ID: {req.agent_id}, Error: {delete_result.message}"
        )
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    # 4. 清理引用关系（删除成功后）
    try:
        cleanup_result = reference_repository.reference_delete_by_referer(
            req.space_id, "AGENT", req.agent_id
        )
        if cleanup_result["code"] != status.HTTP_200_OK:
            logger.warning(
                f"[AGENT_DELETE] Failed to cleanup references for deleted agent {req.agent_id}: "
                f"{cleanup_result['message']}"
            )
    except Exception as e:
        logger.error(
            f"[AGENT_DELETE] Error cleaning up references for agent {req.agent_id}: {e}"
        )

    logger.info(
        f"[AGENT_DELETE] Agent deleted - ID: {req.agent_id}, User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 5. 返回删除结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message=f"delete agent with id {req.agent_id} success",
    )


@with_exception_handling
def agent_publish_delete(
        req: AgentId,
        current_user: dict
) -> ResponseModel:
    """删除指定id及publish版本的智能体"""
    start_time = time.time()
    # 从current_user中正确获取user_id_str
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )

    logger.info(
        f"[AGENT_PUBLISH_DELETE] Deleting agent publish - User: {user_id}, ID: {req.agent_id}, "
        f"Version: {req.agent_version}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 从DB中删除agent的指定publish版本
    delete_result = agent_repository.delete_agent_publish_db(req)

    if delete_result.code != status.HTTP_200_OK:
        logger.error(
            f"[AGENT_PUBLISH_DELETE] Database deletion failed - ID: {req.agent_id}, "
            f"Version: {req.agent_version}, Error: {delete_result.message}"
        )
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

    # 3. 清理该版本的引用关系（删除成功后）
    try:
        cleanup_result = reference_repository.reference_delete_by_referer_with_version(
            req.space_id, "AGENT", req.agent_id, req.agent_version
        )
        if cleanup_result["code"] != status.HTTP_200_OK:
            logger.warning(
                f"[AGENT_PUBLISH_DELETE] Failed to cleanup references for deleted agent publish "
                f"{req.agent_id}:{req.agent_version}: {cleanup_result['message']}"
            )
    except Exception as e:
        logger.error(
            f"[AGENT_PUBLISH_DELETE] Error cleaning up references for agent publish "
            f"{req.agent_id}:{req.agent_version}: {e}"
        )

    logger.info(
        f"[AGENT_PUBLISH_DELETE] Agent publish deleted - ID: {req.agent_id}, User: {user_id}, "
        f"Version: {req.agent_version}, Duration: {time.time() - start_time:.3f}s"
    )

    # 4. 返回删除结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message=f"delete agent publish with id {req.agent_id} and version {req.agent_version} success",
    )


@with_exception_handling
def get_single_agent_info(
        req: AgentGetVersion,
        current_user: dict,
        manager: ModelConfigManager
) -> ResponseModel:
    """获取单个智能体信息"""
    _ = check_user_space(req.space_id, current_user)

    # 1. 从db中获取agent_info信息
    agent_query = AgentId(
        space_id=req.space_id,
        agent_id=req.agent_id,
        agent_version=req.agent_version,  # 使用指定的版本，None时获取draft版本
    )
    get_result = agent_repository.get_agent_db(agent_query)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )
    agent_info = AgentBaseDBPd(**get_result.data)

    # 2. 获取workflow list列表
    workflow_request = req.model_dump()
    workflow_request.update({"page": 1, "page_size": 10000})  # 获取所有工作流
    list_result = workflow_repository.workflow_list(
        SpaceAWPQuery.model_validate(workflow_request)
    )
    if list_result.code != status.HTTP_200_OK:
        wf_list: list[AgentWorkflowListNode] = []
    else:
        wf_list: list[AgentWorkflowListNode] = []
        for w in list_result.data.get("workflow_list", []):
            node = AgentWorkflowListNode(
                id=w.get("workflow_id"),
                version=w.get("workflow_version", "draft"),
                name=w.get("name"),
                desc=w.get("desc"),
            )
            wf_list.append(node)

    # 4. 获取model list列表
    filters = {"space_id": req.space_id}
    models, _ = manager.get_paginated_configs(
        page=DEFAULT_PAGE, size=DEFAULT_PAGE_SIZE, filters=filters
    )
    m_list: list[AgentModelListNode] = []
    for model in models:
        if not model.is_active:
            continue
        param = ModelParameters(**model.parameters)
        m_info = AgentModelListNode(
            **param.model_dump(),
            id=model.id,
            name=model.name,
            type=model.model_type,
            # 隐藏掉api_key和api_base数据
            api_key="",
            api_base="",
            model_provider=model.provider,
            streaming=model.enable_streaming,
            timeout=model.timeout,
        )

        m_list.append(m_info)

    options = AgentOptionInfo(
        workflow_list=wf_list,
        model_list=m_list
    )

    data_response = SingleAgentData(
        agent_info=agent_info,
        agent_option_info=options
    )

    resp_data = data_response.model_dump(by_alias=False)

    # 补充model信息
    if agent_info.model_id:
        models, _ = manager.get_paginated_configs(
            page=1, size=1, filters={"id": agent_info.model_id, "space_id": req.space_id}
        )
        if models:
            model_config = models[0]
            saved_config = agent_info.agent_model_config or {}

            model_info = {
                "model_id": model_config.id,
                "model_name": model_config.name,
                "model_type": model_config.model_type,
                "api_base": "",
                "api_key": "",
                "streaming": model_config.enable_streaming,
                "temperature": saved_config.get("temperature", 0.7),
                "top_p": saved_config.get("top_p", 0.9),
                "timeout": saved_config.get("timeout", 300),
            }

            resp_data["agent_info"]["model"] = {
                "model_provider": model_config.provider,
                "model_info": model_info
            }

    # 5. 返回创建结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create agent success",
        data=resp_data,
    )


@with_exception_handling
def agent_save(
        req: AgentDisplayInfo,
        current_user: dict,
        manager: ModelConfigManager
) -> ResponseModel:
    """更新并保存智能体"""
    start_time = time.time()
    data = current_user.get("data", "unknown")
    user_id = data["user_id_str"]

    logger.info(
        f"[AGENT_SAVE] Saving agent - User: {user_id}, ID: {req.agent_id}, Name: {req.agent_name}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 验证agent版本（保存时应该为空）
    if req.agent_version is not None and req.agent_version != "":
        logger.error(
            f"[AGENT_SAVE] Invalid version for save - ID: {req.agent_id}, Version: {req.agent_version}"
        )
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="agent version should be empty or None when agent save",
        )

    # 3. Get model configuration
    req_dict = req.model_dump()
    model_using = None

    # 尝试获取模型配置
    req_model = req.model
    model_id = getattr(req_model.model_info, "model_id", None)

    logger.info(f"[AGENT_SAVE] model id: {model_id}")
    # 首先尝试根据ID获取模型
    if model_id:
        models, _ = manager.get_paginated_configs(
            page=1, size=1, filters={"id": model_id, "space_id": req.space_id}
        )
        model_using = models[0] if models else None

    # 如果没有ID或未找到，尝试根据名称获取
    if not model_using:
        models, _ = manager.get_paginated_configs(
            page=1,
            size=1,
            filters={"name": req_model.model_info.model_name, "space_id": req.space_id},
        )
        model_using = models[0] if models else None

    req_dict.pop("model", None)
    if model_using:
        # 提取模型基础参数
        req_model_info = req_model.model_info.model_dump()

        req_dict["model_id"] = model_using.id

        # 使用定义的 Schema 来构建model_config配置
        model_config_data = AgentModelConfig(
            timeout=req_model_info.get("timeout") or 300,
            temperature=req_model_info.get("temperature") or 0.7,
            top_p=req_model_info.get("top_p") or 0.9,
        )
        req_dict["agent_model_config"] = model_config_data.model_dump(exclude_none=True)
    else:
        # 如果指定了model_info但找不到对应模型，则报错
        if req_model and req_model.model_info and req_model.model_info.model_name:
            logger.error(f"[AGENT_SAVE] {req_model.model_info.model_name} Model not found")
            return ResponseModel(
                code=StatusCode.AGENT_MODEL_NOT_FOUND.code,
                message=StatusCode.AGENT_MODEL_NOT_FOUND.errmsg.format(msg=req_model.model_info.model_name)
            )

    # 创建AgentBaseDBPd实例
    try:
        agent_info = AgentBaseDBPd(**req_dict, update_time=milliseconds())
    except ValidationError as e:
        raise e

    # 4. 更新agent_info信息至DB中
    save_result = agent_repository.save_agent_db(agent_info)

    if save_result.code != status.HTTP_200_OK:
        logger.error(
            f"[AGENT_SAVE] Database save failed - ID: {req.agent_id}, Error: {save_result.message}"
        )
        return ResponseModel(
            code=save_result.code,
            message=save_result.message,
        )

    # 5. 管理引用关系
    try:
        # 查询是否存在旧关系
        search_result = reference_repository.get_records_by_referer_with_version(
            req.space_id, "AGENT", req.agent_id, "draft"
        )
        if search_result["code"] == status.HTTP_200_OK and search_result["data"]:
            # 5.1 删除旧的草稿引用关系
            delete_result = reference_repository.reference_delete_by_referer_with_version(
                req.space_id, "AGENT", req.agent_id, "draft"
            )
            if delete_result["code"] != status.HTTP_200_OK:
                logger.warning(
                    f"[AGENT_SAVE] Failed to delete old references for agent {req.agent_id}: {delete_result['message']}"
                )
        else:
            logger.warning(
                f"[AGENT_SAVE] Search old references for agent {req.agent_id} failed: {search_result['message']}"
            )

        # 5.2 提取并创建新的引用关系
        references = extract_agent_references(req.model_dump(), req.space_id, "draft")
        for ref in references:
            create_result = reference_repository.reference_create(ref)
            if create_result["code"] != status.HTTP_200_OK:
                logger.warning(
                    f"[AGENT_SAVE] Failed to create reference {ref}: {create_result['message']}"
                )

        logger.info(
            f"[AGENT_SAVE] Reference management completed for agent {req.agent_id}: "
            f"{len(references)} references processed"
        )
    except Exception as e:
        logger.error(
            f"[AGENT_SAVE] Error managing references for agent {req.agent_id}: {e}"
        )
        # 引用关系管理失败不影响主要保存功能

    logger.info(
        f"[AGENT_SAVE] Agent saved - ID: {req.agent_id}, User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 6. 返回保存结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="save agent success",
    )


@with_exception_handling
def agent_meta_update(
        req: AgentUpdate,
        current_user: dict
) -> ResponseModel:
    """更新并保存智能体"""
    start_time = time.time()
    # 从current_user中正确获取user_id_str
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )

    logger.info(f"[AGENT_UPDATE] Updating agent metadata - User: {user_id}")

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 构建agent_info对象
    req_dict = req.model_dump()

    agent_info = AgentBaseDBPd(
        **req_dict,
        update_time=milliseconds()
    )

    # 3. 更新agent_info信息至DB中
    save_result = agent_repository.save_agent_db(agent_info)

    if save_result.code != status.HTTP_200_OK:
        logger.error(
            f"[AGENT_UPDATE] Database update failed, Error: {save_result.message}"
        )
        return ResponseModel(
            code=save_result.code,
            message=save_result.message,
        )

    # 4. 同步更新 prompt_relation 表中该智能体关联记录的 name（id 存的是智能体id）
    pr_result = prompt_relation_repository.update_member_name_in_prompt_relation(
        space_id=req.space_id,
        member_type="AGENT",
        member_id=req.agent_id,
        new_name=req.agent_name,
    )
    if pr_result.code == status.HTTP_200_OK:
        logger.info(f"[AGENT_UPDATE] Synced agent name in prompt_relation: {pr_result.message}")
    else:
        logger.warning(f"[AGENT_UPDATE] Sync agent name in prompt_relation failed: {pr_result.message}")

    logger.info(
        f"[AGENT_UPDATE] Agent metadata updated, User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 5. 返回更新结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="update agent success",
    )


@with_exception_handling
def agent_get_list(
        req: AgentList,
        current_user: dict
) -> ResponseModel:
    """获取智能体列表"""
    # 从current_user中正确获取user_id_str
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )

    logger.info(
        f"[AGENT_LIST] Getting agent list - User: {user_id}, Space: {req.space_id}, Page: {req.page}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 构建查询参数
    query_info = SpaceAWPQuery(**req.model_dump())

    # 3. 从数据库获取agent列表
    list_result = agent_repository.get_space_agent_list_db(query_info)

    if list_result.code != status.HTTP_200_OK:
        # 查询有异常错误，直接报出来
        return ResponseModel(
            code=list_result.code,
            message=list_result.message
        )

    # 批量获取模型信息
    model_ids = {item.get("model_id") for item in list_result.data["items"] if item.get("model_id")}
    model_name_map = {}
    if model_ids:
        try:
            with get_db_agent_session() as db:
                model_mgr = ModelConfigManager(db)
                models = model_mgr.get_configs_by_ids(list(model_ids))
                if models:
                    for m in models:
                        model_name_map[m.id] = m.name
        except Exception as e:
            logger.error(f"[AGENT_GET_LIST] Failed to fetch model names: {e}")

    items: list[AgentItem] = []
    for item_data in list_result.data["items"]:
        model_name = "no model"
        m_id = item_data.get("model_id")
        if m_id and m_id in model_name_map:
            model_name = model_name_map[m_id]
        elif item_data.get("model"): # 兼容旧数据
            try:
                # 简化模型数据处理
                model = AgentModel(**item_data.get("model"))
                model_name = model.model_info.model_name
            except Exception as e:
                logger.error(
                    f"[AGENT_GET_LIST] Failed to process model data: {item_data.get('model')}, error: {e}"
                )
        item = AgentItem(
            id=item_data.get("agent_id"),
            name=item_data.get("agent_name"),
            version=item_data.get("agent_version"),
            type=item_data.get("agent_type"),
            desc=item_data.get("description"),
            icon=item_data.get("icon") or "🤖",
            status=item_data.get("status", "test"),
            model_name=model_name,
            last_activate=item_data.get("last_activate", "test"),
            usage_count=item_data.get("usage_count", 0),
            tags=item_data.get("tags", []),
            create_time=item_data.get("create_time"),
            update_time=item_data.get("update_time"),
            api_endpoint=item_data.get("api_endpoint", "test"),
        )

        items.append(item)

    total_agent = int(list_result.data["total"])
    total_pages = math.ceil(total_agent / req.page_size)

    page_info = AgentListPagination(
        page=req.page,
        page_size=req.page_size,
        total=total_agent,
        total_pages=total_pages,
    )

    response_data = AgentListInfo(
        agent_items=items,
        pagination=page_info
    )

    # 4. 返回创建结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get agent list success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
def agent_publish(
        req: AgentPublish,
        current_user: dict
) -> ResponseModel:
    """发布智能体"""
    start_time = time.time()
    # 从current_user中正确获取user_id_str
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )
    logger.info(
        f"[AGENT_PUBLISH] Publishing agent - User: {user_id}, ID: {req.agent_id}, Version: {req.agent_version}"
    )

    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 获取最新版本信息进行版本校验
    latest_version_query = AgentId(
        agent_id=req.agent_id,
        space_id=req.space_id,
        agent_version="latest_publish_version",
    )

    # 获取最新的发布版本信息
    latest_publish_version = agent_repository.get_agent_latest_publish_version_db(
        latest_version_query
    )

    # 3. 判断当前版本格式是否正确，且version是否为递增的
    if latest_publish_version is None:
        current_version, check_err = Version.string_to_object(req.agent_version)
        logger.info(
            f"[AGENT_PUBLISH] First time publishing - ID: {req.agent_id}, Version: {req.agent_version}"
        )
        if check_err is not None:
            logger.error(
                f"[AGENT_PUBLISH] Invalid version format - ID: {req.agent_id}, "
                f"Version: {req.agent_version}, Error: {check_err}"
            )
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"check version {req.agent_version} failed, error: {check_err}",
                data=None,
            )
    else:
        check_res, check_err = check_version(latest_publish_version, req.agent_version)
        logger.debug(
            f"[AGENT_PUBLISH] Version validation - ID: {req.agent_id}, "
            f"Latest: {latest_publish_version}, Current: {req.agent_version}"
        )
        if not check_res:
            logger.error(
                f"[AGENT_PUBLISH] Version validation failed - ID: {req.agent_id}, Error: {check_err}"
            )
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"check version failed, error: {check_err}",
                data=None,
            )

    # 4. 获取draft数据库中agent的信息
    agent_draft_query = AgentId(
        space_id=req.space_id,
        agent_id=req.agent_id,
        agent_version=None,  # 获取draft版本
    )
    draft_result = agent_repository.get_agent_db(agent_draft_query)

    if draft_result.code != status.HTTP_200_OK:
        logger.error(
            f"[AGENT_PUBLISH] Failed to get draft agent - ID: {req.agent_id}, Error: {draft_result.message}"
        )
        return ResponseModel(
            code=draft_result.code,
            message=f"Get agent with id {req.agent_id} failed, error: {draft_result.message}",
            data=None,
        )

    agent_data = AgentBaseDBPd(**draft_result.data)

    # 5. 使用agent_convert进行智能体校验
    logger.debug(f"[AGENT_PUBLISH] Starting validation - ID: {req.agent_id}")
    # 临时获取模型信息用于校验
    model_details = None
    if agent_data.model_id:
        try:
            with get_db_agent_session() as db:
                model_mgr = ModelConfigManager(db)
                models, _ = model_mgr.get_paginated_configs(
                    page=1, size=1, filters={"id": agent_data.model_id}
                )
                if models:
                    m = models[0]
                    model_details = {
                        "id": m.id,
                        "name": m.name,
                        "model_type": m.model_type,
                        "provider": m.provider,
                        "api_key": m.api_key,
                        "base_url": m.base_url,
                        "enable_streaming": m.enable_streaming,
                        "timeout": m.timeout,
                        "parameters": m.parameters,
                    }

                    # Apply model_config overrides
                    if agent_data.agent_model_config:
                        if model_details.get("parameters") is None:
                            model_details["parameters"] = {}
                        if agent_data.agent_model_config.get("temperature") is not None:
                            model_details["parameters"]["temperature"] = (
                                agent_data.agent_model_config.get("temperature")
                            )
                        if agent_data.agent_model_config.get("top_p") is not None:
                            model_details["parameters"]["top_p"] = (
                                agent_data.agent_model_config.get("top_p")
                            )
                        if agent_data.agent_model_config.get("timeout") is not None:
                            model_details["timeout"] = (
                                agent_data.agent_model_config.get("timeout")
                            )

        except Exception as e:
            logger.warning(
                f"[AGENT_PUBLISH] Failed to fetch model info for validation: {e}"
            )

    _, err = convert.agent_convert(req.space_id, agent_data, model_details)
    if err is not None:
        logger.error(
            f"[AGENT_PUBLISH] Validation failed - ID: {req.agent_id}, Error: {err}"
        )
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"Agent validation failed: {err}",
            data=None,
        )
    logger.debug(f"[AGENT_PUBLISH] Validation passed - ID: {req.agent_id}")

    # 6. 构建publish需要的AgentPublishDB结构，并将其存入数据库中
    # 获取智能体基础数据，明确排除 agent_version 字段以避免冲突
    agent_publish_data = agent_data.model_dump(
        exclude_none=True, exclude={"agent_version"}
    )

    # 更新时间戳为当前发布时间
    current_time = milliseconds()
    agent_publish_data["create_time"] = current_time
    agent_publish_data["update_time"] = current_time

    # 添加发布版本必需的字段
    agent_publish_data["agent_version"] = req.agent_version
    agent_publish_data["version_description"] = req.version_description

    # 创建发布版本数据
    version_data = AgentPublishDBPd(**agent_publish_data)

    # 7. 将发布版本数据存储到数据库
    logger.debug(f"[AGENT_PUBLISH] Starting database publish - ID: {req.agent_id}")
    publish_result = agent_repository.publish_agent_db(version_data)

    if publish_result.code != status.HTTP_200_OK:
        logger.error(
            f"[AGENT_PUBLISH] Database publish failed - ID: {req.agent_id}, Error: {publish_result.message}"
        )
        return ResponseModel(
            code=publish_result.code,
            message=f"publish agent failed, error: {publish_result.message}",
            data=None,
        )

    # 8. 管理发布版本的引用关系
    try:
        # 8.1 提取并创建发布版本的引用关系
        references = extract_agent_references(
            agent_publish_data, req.space_id, req.agent_version
        )
        for ref in references:
            create_result = reference_repository.reference_create(ref)
            if create_result["code"] != status.HTTP_200_OK:
                logger.warning(
                    f"[AGENT_PUBLISH] Failed to create publish reference {ref}: {create_result['message']}"
                )

        logger.info(
            f"[AGENT_PUBLISH] Publish reference management completed for agent {req.agent_id} "
            f"v{req.agent_version}: {len(references)} references processed"
        )
    except Exception as e:
        logger.error(
            f"[AGENT_PUBLISH] Error managing publish references for agent {req.agent_id}: {e}"
        )
        # 引用关系管理失败不影响主要发布功能

    # 9. 构建响应数据
    res_data = AgentResponsePublish(
        agent_id=req.agent_id,
        success=True
    )

    # 记录完成指标
    execution_time = time.time() - start_time
    logger.info(
        f"[AGENT_PUBLISH] Published successfully - ID: {req.agent_id}, Version: {req.agent_version}, "
        f"User: {user_id}, Duration: {execution_time:.3f}s"
    )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="publish agent success",
        data=res_data.model_dump(),
    )


@with_exception_handling
def agent_convert(
        req: AgentGetVersion,
        current_user: dict
) -> ResponseModel:
    """转换agent数据格式"""
    _ = check_user_space(req.space_id, current_user)

    # 1. 从db中获取agent_info信息
    agent_query = AgentId(
        space_id=req.space_id,
        agent_id=req.agent_id,
        agent_version=req.agent_version
    )
    get_result = agent_repository.get_agent_db(agent_query)
    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    # 2. 获取模型详情 (if model_id exists)
    model_details = None
    model_id = get_result.data.get("model_id")
    model_config = get_result.data.get("agent_model_config")
    if model_id:
        try:
            with get_db_agent_session() as db:
                model_mgr = ModelConfigManager(db)
                models, _ = model_mgr.get_paginated_configs(
                    page=1, size=1, filters={"id": model_id, "space_id": req.space_id}
                )
                if models:
                    m = models[0]
                    model_details = {
                        "id": m.id,
                        "name": m.name,
                        "model_type": m.model_type,
                        "provider": m.provider,
                        "api_key": m.api_key,
                        "base_url": m.base_url,
                        "enable_streaming": m.enable_streaming,
                        "timeout": m.timeout,
                        "parameters": m.parameters
                    }
        except Exception as e:
            logger.error(f"[AGENT_CONVERT] Failed to fetch model config: {e}")

    if model_details and model_config:
        # 优先使用 agent 自身的配置覆盖模型的默认配置
        if model_config.get("timeout") is not None:
            model_details["timeout"] = model_config.get("timeout")
        # 确保 parameters 字典存在
        if "parameters" in model_details and model_details["parameters"] is not None:
            if model_config.get("max_tokens") is not None:
                model_details["parameters"]["max_tokens"] = model_config.get("max_tokens")
            if model_config.get("temperature") is not None:
                model_details["parameters"]["temperature"] = model_config.get("temperature")
            if model_config.get("top_p") is not None:
                model_details["parameters"]["top_p"] = model_config.get("top_p")

    # 3. 将展示面信息转换成执行面可用信息
    agent_dsl, err = convert.agent_convert(
        req.space_id, AgentBaseDBPd(**get_result.data), model_details
    )
    if err is not None:
        return ResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="convert agent dsl failed",
        )
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="convert agent success",
        data=agent_dsl
    )


@with_exception_handling
def agent_react_copy(
        req: AgentCopy,
        current_user: dict
) -> ResponseModel:
    """创建新的智能体"""
    _ = check_user_space(req.space_id, current_user)

    # 重新生成agent_id
    agent_copy_id = str(uuid.uuid4())
    current_time = milliseconds()

    # 获取要复制的agent
    get_result = agent_repository.get_agent_db(AgentId(**req.model_dump()))
    if get_result.code != status.HTTP_200_OK:
        return get_result

    # 准备复制数据
    agent_data = get_result.data.copy()
    agent_data.pop("agent_version", None)  # 复制的智能体只能生成draft版本
    agent_data.pop("latest_publish_version", None)
    agent_data.pop("latest_publish_time", None)

    # 创建复制的智能体
    agent_copy = AgentBaseDBPd(**agent_data)
    agent_copy.agent_id = agent_copy_id
    agent_copy.create_time = current_time
    agent_copy.update_time = current_time
    agent_copy.agent_name = f"{agent_copy.agent_name}_copy"
    if len(agent_copy.agent_name) > AGENT_NAME_MAX_SIZE:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"Agent name add '_copy' suffix exceeds the {AGENT_NAME_MAX_SIZE}-character length limit."
        )

    # 保存到数据库
    copy_result = agent_repository.create_agent_db(agent_copy)
    if copy_result.code != status.HTTP_200_OK:
        return copy_result

    # 构造响应数据
    response_data = AgentResponseCreate(id=agent_copy.agent_id)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="copy agent success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
def agent_search(
        req: AgentSearchRequest,
        current_user: dict
) -> ResponseModel:
    """搜索智能体"""
    # 1. 校验Space_id是否有权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 构建查询参数，使用SpaceAgentQuery模型
    query_params = SpaceAWPQuery(
        space_id=req.space_id,
        search_term=req.search_term or "",
        status_filter=req.status_filter or "all",
        sort_by=req.sort_by.value if req.sort_by else "update_time",
        sort_order=req.sort_order.value if req.sort_order else "desc",
        page=req.page or 1,
        page_size=req.page_size or 10,
    )

    # 3. 调用现有的get_space_agent_list_db接口（已支持搜索）
    list_result = agent_repository.get_space_agent_list_db(query_params)

    if list_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=list_result.code,
            message=f"Search agent with space_id {req.space_id} failed, error: {list_result.message}",
        )

    # 4. 处理智能体数据
    data_list = list_result.data.get("items", [])
    if not isinstance(data_list, list):
        data_list = []

    # 5. 构建搜索响应数据
    total = list_result.data.get("total", 0)
    page = query_params.page
    page_size = query_params.page_size
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    res_data = {
        "agent_items": data_list,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
        "search_term": req.search_term,
        "filters": {
            "status_filter": req.status_filter or "all",
            "sort_by": query_params.sort_by,
            "sort_order": query_params.sort_order,
        },
    }

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Search agent success",
        data=res_data
    )


@with_exception_handling
def agent_version_list(
        req: AgentVersionListRequest,
        current_user: dict
) -> ResponseModel:
    """获取智能体的发布版本列表"""
    _ = check_user_space(req.space_id, current_user)

    # 调用repository获取版本列表
    version_result = agent_repository.get_agent_publish_list(req.model_dump())

    if version_result.code == status.HTTP_404_NOT_FOUND:
        logger.info(f"No published versions found for agent {req.agent_id}, returning empty list")
        response_data = AgentVersionListResponse(
            agent_id=req.agent_id,
            versions=[]
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="No agent version was found",
            data=response_data
        )

    if version_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=version_result.code,
            message=version_result.message,
            data=None
        )

    # 构建响应数据
    versions_data = version_result.data or []
    versions = []

    for version_info in versions_data:
        versions.append(
            AgentVersionInfo(
                agent_version=version_info.get("agent_version", ""),
                version_description=version_info.get("version_description", ""),
                create_time=version_info.get("create_time", 0),
            )
        )

    response_data = {
        "agent_id": req.agent_id,
        "versions": versions
    }

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Get agent version list success",
        data=response_data,
    )


def _extract_dependencies_from_nodes(nodes: list) -> tuple[set, set]:
    """从节点列表中递归提取 workflow_ids 和 plugin_ids"""
    workflow_ids = set()
    plugin_ids = set()

    for node in nodes:
        node_data = node.get("data", {})
        configs = node_data.get("configs", {})
        inputs = node_data.get("inputs", {})

        # 1. Sub-Workflow
        sub_workflow = configs.get("subWorkflow")
        if sub_workflow and isinstance(sub_workflow, dict):
            wf_id = sub_workflow.get("workflowId")
            if wf_id:
                workflow_ids.add(wf_id)

        # 2. Plugin
        plugin_param = inputs.get("pluginParam")
        if plugin_param and isinstance(plugin_param, dict):
            p_id = plugin_param.get("pluginID")
            if p_id:
                plugin_ids.add(p_id)

        # 3. Loop Node (Recursive)
        blocks = node.get("blocks", [])
        if blocks:
            sub_wf_ids, sub_pl_ids = _extract_dependencies_from_nodes(blocks)
            workflow_ids.update(sub_wf_ids)
            plugin_ids.update(sub_pl_ids)

    return workflow_ids, plugin_ids


def _collect_workflow_dependencies(
    workflow_id: str,
    space_id: str,
    workflows: list,
    processed_workflow_ids: Set[str],
    plugins: list,
    processed_plugin_ids: Set[str],
):
    """递归收集Workflow依赖（包括子工作流和插件）"""
    if workflow_id in processed_workflow_ids:
        return

    from openjiuwen_studio.schemas.workflow import WorkflowId

    wf_query = WorkflowId(
        space_id=space_id, workflow_id=workflow_id, workflow_version=None
    )

    wf_result = workflow_repository.workflow_get(wf_query)

    if wf_result.code != status.HTTP_200_OK or not wf_result.data:
        return

    wf_data = wf_result.data
    processed_workflow_ids.add(workflow_id)
    workflows.append(wf_data)

    # 解析 schema 提取依赖
    schema_str = wf_data.get("schema")
    if not schema_str:
        return

    try:
        schema = json.loads(schema_str)
        nodes = schema.get("nodes", [])

        sub_wf_ids, sub_pl_ids = _extract_dependencies_from_nodes(nodes)

        # 递归收集子工作流
        for sub_id in sub_wf_ids:
            _collect_workflow_dependencies(
                sub_id,
                space_id,
                workflows,
                processed_workflow_ids,
                plugins,
                processed_plugin_ids,
            )

        # 收集插件
        for pl_id in sub_pl_ids:
            _collect_plugin_dependencies(pl_id, space_id, plugins, processed_plugin_ids)

    except Exception as e:
        logger.error(f"Failed to parse workflow schema for dependencies: {e}")


def _collect_plugin_dependencies(
    plugin_id: str, space_id: str, plugins: list, processed_plugin_ids: Set[str]
):
    """收集Plugin依赖"""
    if plugin_id in processed_plugin_ids:
        return

    query_body = {"plugin_id": plugin_id, "space_id": space_id}
    plugin_res, tool_list = plugin_repository.plugin_get(query_body)

    if plugin_res.get("code") != status.HTTP_200_OK:
        return

    plugin_data = plugin_res.get("data")
    if not plugin_data:
        return

    # 处理PluginBaseDB对象，转换为字典格式
    if hasattr(plugin_data, "to_dict"):
        plugin_dict = plugin_data.to_dict()
    elif hasattr(plugin_data, "model_dump"):
        plugin_dict = plugin_data.model_dump()
    elif hasattr(plugin_data, "__dict__"):
        plugin_dict = {
            k: v for k, v in plugin_data.__dict__.items() if not k.startswith("_")
        }
    else:
        # 如果是字典，直接使用
        plugin_dict = plugin_data

    if "plugin_id" not in plugin_dict:
        return

    # Merge tool_list into plugin_dict if not present or empty
    if tool_list:
        plugin_dict["tool_list"] = tool_list

    processed_plugin_ids.add(plugin_id)
    plugins.append(plugin_dict)


def _update_workflow_ids_in_json(data: Any, workflow_id_map: Dict[str, str]) -> Any:
    """递归更新JSON中的workflow_id"""
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # 检查值是否为旧ID
            if isinstance(v, str) and v in workflow_id_map:
                new_data[k] = workflow_id_map[v]
            else:
                new_data[k] = _update_workflow_ids_in_json(v, workflow_id_map)
        return new_data
    elif isinstance(data, list):
        return [_update_workflow_ids_in_json(item, workflow_id_map) for item in data]
    else:
        return data


def _update_plugin_ids_in_json(data: Any, plugin_id_map: Dict[str, str]) -> Any:
    """递归更新JSON中的plugin_id"""
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # 检查值是否为旧插件ID
            if k == "pluginID" or k == "plugin_id":
                if isinstance(v, str) and v in plugin_id_map:
                    new_data[k] = plugin_id_map[v]
                else:
                    new_data[k] = v
            else:
                new_data[k] = _update_plugin_ids_in_json(v, plugin_id_map)
        return new_data
    elif isinstance(data, list):
        return [_update_plugin_ids_in_json(item, plugin_id_map) for item in data]
    else:
        return data


def _update_tool_ids_in_json(data: Any, tool_id_map: Dict[str, str]) -> Any:
    """递归更新JSON中的tool_id"""
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # 检查值是否为旧工具ID
            if k == "toolID" or k == "tool_id":
                if isinstance(v, str) and v in tool_id_map:
                    new_data[k] = tool_id_map[v]
                else:
                    new_data[k] = v
            else:
                new_data[k] = _update_tool_ids_in_json(v, tool_id_map)
        return new_data
    elif isinstance(data, list):
        return [_update_tool_ids_in_json(item, tool_id_map) for item in data]
    else:
        return data


def _create_plugin_and_tools(
    space_id: str, plugin_tpl: dict, tool_id_map: Dict[str, str]
) -> tuple[str, list[str]]:
    """创建插件和工具，类似pre_installed.py中的同名函数"""
    created_tool_ids = []
    if not plugin_tpl:
        return None, created_tool_ids
    plugin_id = str(uuid.uuid4())
    current_time = milliseconds()

    # 使用PluginCreate模型创建插件
    plugin_create = PluginCreate(
        name=plugin_tpl.get("name"),
        desc=plugin_tpl.get("desc"),
        space_id=space_id,
        plugin_type=plugin_tpl.get("plugin_type", PluginType.PLUGIN_TYPE_CLOUD_API),
        url=plugin_tpl.get("url") or "",
        icon_uri=plugin_tpl.get("icon_uri") or "",
    )

    # 转换为字典并添加额外字段
    plugin_dict = plugin_create.model_dump(by_alias=True)
    plugin_dict.update(
        {
            "plugin_id": plugin_id,
            "create_time": current_time,
            "update_time": current_time,
        }
    )

    plugin_repository.plugin_create(plugin_dict)

    # 同时支持tools和tool_list字段，兼容不同的数据结构
    tools = plugin_tpl.get("tools") or plugin_tpl.get("tool_list") or []

    # 获取插件版本，兼容不同字段名，默认值为"draft"（与__version_none__保持一致）
    plugin_version = (
        plugin_tpl.get("plugin_version") or plugin_tpl.get("version") or "draft"
    )
    plugin_type = plugin_tpl.get("plugin_type", PluginType.PLUGIN_TYPE_CLOUD_API)

    for t in tools:
        # 获取旧的工具ID
        old_tool_id = t.get("tool_id")
        # 生成新的工具ID，避免冲突
        tool_id = old_tool_id or str(uuid.uuid4())

        # 使用相应的插件工具模型创建工具
        if plugin_type == PluginType.PLUGIN_TYPE_CLOUD_API:
            # API类型插件工具
            tool_info = PluginApiInfo(
                space_id=space_id,
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                plugin_type=plugin_type,
                tool_id=tool_id,
                name=t.get("name"),
                desc=t.get("description") or t.get("desc") or "",
                path=t.get("path"),
                method=t.get("method", PluginApiMethod.PLUGIN_API_METHOD_GET),
                request_params=t.get("request_params", []),
                response_params=t.get("response_params", []),
                headers=t.get("headers", []),
            )
        else:
            # 代码类型插件工具
            tool_info = PluginCodeInfo(
                space_id=space_id,
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                plugin_type=plugin_type,
                tool_id=tool_id,
                name=t.get("name"),
                desc=t.get("description") or t.get("desc") or "",
                language=t.get("language", "python"),
                code=t.get("code", ""),
                request_params=t.get("request_params", []),
                response_params=t.get("response_params", []),
            )

        # 转换为字典并添加额外字段
        tool_dict = tool_info.model_dump(by_alias=True)

        # 处理方法转换（字符串到枚举）
        if isinstance(tool_dict.get("method"), str):
            method_map = {
                "GET": PluginApiMethod.PLUGIN_API_METHOD_GET,
                "POST": PluginApiMethod.PLUGIN_API_METHOD_POST,
                "PUT": PluginApiMethod.PLUGIN_API_METHOD_PUT,
                "DELETE": PluginApiMethod.PLUGIN_API_METHOD_DELETE,
            }
            tool_dict["method"] = method_map.get(
                tool_dict["method"].upper(), PluginApiMethod.PLUGIN_API_METHOD_GET
            )

        # 处理参数类型转换
        for param_key in ["request_params", "response_params"]:
            params = tool_dict.get(param_key, [])
            if isinstance(params, list):
                for p in params:
                    if isinstance(p, dict) and isinstance(p.get("type"), str):
                        p["type"] = param_type_mapping.get(
                            p["type"].lower(), param_type_mapping["string"]
                        )
            elif isinstance(params, dict):
                # 如果是字典格式（如模板中可能出现），转换为列表
                new_params = []
                for k, v in params.items():
                    if not isinstance(v, dict):
                        continue
                    new_params.append(
                        {
                            "name": k,
                            "desc": v.get("description", ""),
                            "type": param_type_mapping.get(
                                v.get("type", "string").lower(),
                                param_type_mapping["string"],
                            ),
                            "is_required": bool(v.get("required", False)),
                        }
                    )
                tool_dict[param_key] = new_params

        # 添加_rest_字段（仅API类型）
        if plugin_type == PluginType.PLUGIN_TYPE_CLOUD_API:
            tool_dict["_rest_"] = {
                "path": tool_dict.get("path"),
                "method": tool_dict.get("method"),
                "headers": tool_dict.get("headers") or [],
            }

        # 记录工具创建日志
        logger.info(
            f"[AGENT_IMPORT] Creating tool {t.get('name')} for plugin {plugin_id}"
        )
        logger.debug(f"[AGENT_IMPORT] Tool data: {tool_dict}")

        # 创建工具并处理冲突
        create_res = tool_repository.tool_create(tool_dict)
        logger.debug(f"[AGENT_IMPORT] Tool create result: {create_res}")

        final_tool_id = tool_id
        if create_res.get("code") != status.HTTP_200_OK:
            # 检查是否是ID冲突
            if "This db already exists" in create_res.get(
                "message", ""
            ) or "Duplicate entry" in create_res.get("message", ""):
                # 生成新的工具ID并重试
                logger.warning(
                    f"[AGENT_IMPORT] Tool {tool_id} exists, generating new ID."
                )
                final_tool_id = str(uuid.uuid4())
                tool_dict["tool_id"] = final_tool_id
                create_res = tool_repository.tool_create(tool_dict)
                logger.debug(f"[AGENT_IMPORT] Tool create retry result: {create_res}")

                if create_res.get("code") == status.HTTP_200_OK:
                    logger.info(
                        f"[AGENT_IMPORT] Created tool {t.get('name')} with new ID {final_tool_id}"
                    )
                    created_tool_ids.append(final_tool_id)
                else:
                    logger.error(
                        f"[AGENT_IMPORT] Failed to create tool {t.get('name')} with new ID: {create_res.get('message')}"
                    )
                    continue
            else:
                logger.error(
                    f"[AGENT_IMPORT] Failed to create tool {t.get('name')}: {create_res.get('message')}"
                )
                continue
        else:
            logger.info(
                f"[AGENT_IMPORT] Created tool {t.get('name')} with ID {final_tool_id}"
            )
            created_tool_ids.append(final_tool_id)

        # 更新tool_id_map，记录旧的工具ID和新的工具ID的映射关系
        if old_tool_id:
            tool_id_map[old_tool_id] = final_tool_id
    return plugin_id, created_tool_ids


def _import_plugin_tools(
    plugin_data: dict,
    space_id: str,
    tool_id_map: Dict[str, str],
) -> list[str]:
    """导入插件工具，返回创建的工具ID列表"""
    # 同时支持tools和tool_list字段，兼容不同的数据结构
    tool_list = plugin_data.get("tool_list", []) or plugin_data.get("tools", [])
    created_tool_ids = []

    if not tool_list:
        logger.info(
            f"[AGENT_IMPORT] No tools found for plugin {plugin_data.get('plugin_id')}"
        )
        return created_tool_ids
    logger.info(
        f"[AGENT_IMPORT] Found {len(tool_list)} tools for plugin {plugin_data.get('plugin_id')}"
    )

    current_plugin_id = plugin_data.get("plugin_id")
    # 确保工具的 plugin_type 与插件一致
    plugin_type = plugin_data.get("plugin_type", PluginType.PLUGIN_TYPE_CLOUD_API)
    # 获取插件版本，默认值为"draft"（与__version_none__保持一致）
    plugin_version = (
        plugin_data.get("plugin_version") or plugin_data.get("version") or "draft"
    )

    for tool in tool_list:
        # 1. 基础字段补全
        tool["plugin_id"] = current_plugin_id
        tool["space_id"] = space_id
        tool["plugin_type"] = plugin_type
        tool["plugin_version"] = plugin_version

        # 2. 获取或生成工具ID
        old_tool_id = tool.get("tool_id")
        # 如果 tool_id 已经被映射（即在插件创建冲突处理时更新了），使用新ID
        if old_tool_id and old_tool_id in tool_id_map:
            tool["tool_id"] = tool_id_map[old_tool_id]
        elif not old_tool_id:
            tool["tool_id"] = str(uuid.uuid4())

        # 3. 使用相应的插件工具模型创建工具
        if plugin_type == PluginType.PLUGIN_TYPE_CLOUD_API:
            # API类型插件工具
            try:
                tool_info = PluginApiInfo(
                    space_id=space_id,
                    plugin_id=current_plugin_id,
                    plugin_version=plugin_version,
                    plugin_type=plugin_type,
                    tool_id=tool["tool_id"],
                    name=tool.get("name"),
                    desc=tool.get("description") or tool.get("desc") or "",
                    path=tool.get("path"),
                    method=tool.get("method", PluginApiMethod.PLUGIN_API_METHOD_GET),
                    request_params=tool.get("request_params", []),
                    response_params=tool.get("response_params", []),
                    headers=tool.get("headers", []),
                )
            except ValidationError as e:
                logger.error(f"[AGENT_IMPORT] Failed to create PluginApiInfo: {e}")
                continue
        else:
            # 代码类型插件工具
            try:
                tool_info = PluginCodeInfo(
                    space_id=space_id,
                    plugin_id=current_plugin_id,
                    plugin_version=plugin_version,
                    plugin_type=plugin_type,
                    tool_id=tool["tool_id"],
                    name=tool.get("name"),
                    desc=tool.get("description") or tool.get("desc") or "",
                    language=tool.get("language", "python"),
                    code=tool.get("code", ""),
                    request_params=tool.get("request_params", []),
                    response_params=tool.get("response_params", []),
                )
            except ValidationError as e:
                logger.error(f"[AGENT_IMPORT] Failed to create PluginCodeInfo: {e}")
                continue

        # 转换为字典并添加额外字段
        tool_dict = tool_info.model_dump(by_alias=True)

        # 处理方法转换（字符串到枚举）
        if isinstance(tool_dict.get("method"), str):
            method_map = {
                "GET": PluginApiMethod.PLUGIN_API_METHOD_GET,
                "POST": PluginApiMethod.PLUGIN_API_METHOD_POST,
                "PUT": PluginApiMethod.PLUGIN_API_METHOD_PUT,
                "DELETE": PluginApiMethod.PLUGIN_API_METHOD_DELETE,
            }
            tool_dict["method"] = method_map.get(
                tool_dict["method"].upper(), PluginApiMethod.PLUGIN_API_METHOD_GET
            )

        # 处理参数类型转换
        for param_key in ["request_params", "response_params"]:
            params = tool_dict.get(param_key, [])
            if isinstance(params, list):
                for p in params:
                    if isinstance(p, dict) and isinstance(p.get("type"), str):
                        p["type"] = param_type_mapping.get(
                            p["type"].lower(), param_type_mapping["string"]
                        )
            elif isinstance(params, dict):
                # 如果是字典格式（如模板中可能出现），转换为列表
                new_params = []
                for k, v in params.items():
                    if not isinstance(v, dict):
                        continue
                    new_params.append(
                        {
                            "name": k,
                            "desc": v.get("description", ""),
                            "type": param_type_mapping.get(
                                v.get("type", "string").lower(),
                                param_type_mapping["string"],
                            ),
                            "is_required": bool(v.get("required", False)),
                        }
                    )
                tool_dict[param_key] = new_params

        # 4. 构建或修复 _rest_ 字段（仅API类型）
        if plugin_type == PluginType.PLUGIN_TYPE_CLOUD_API:
            if "_rest_" not in tool_dict or not isinstance(tool_dict["_rest_"], dict):
                tool_dict["_rest_"] = {
                    "path": tool_dict.get("path"),
                    "method": tool_dict.get("method"),
                    "headers": tool_dict.get("headers") or [],
                }
            else:
                # 确保 _rest_ 里的 method 也是正确的类型
                rest_method = tool_dict["_rest_"].get("method")
                if isinstance(rest_method, str):
                    method_map = {
                        "GET": PluginApiMethod.PLUGIN_API_METHOD_GET,
                        "POST": PluginApiMethod.PLUGIN_API_METHOD_POST,
                        "PUT": PluginApiMethod.PLUGIN_API_METHOD_PUT,
                        "DELETE": PluginApiMethod.PLUGIN_API_METHOD_DELETE,
                    }
                    tool_dict["_rest_"]["method"] = method_map.get(
                        rest_method.upper(), PluginApiMethod.PLUGIN_API_METHOD_GET
                    )
                elif rest_method is None:
                    tool_dict["_rest_"]["method"] = tool_dict.get(
                        "method", PluginApiMethod.PLUGIN_API_METHOD_GET
                    )

                if "path" not in tool_dict["_rest_"]:
                    tool_dict["_rest_"]["path"] = tool_dict.get("path", "")

        # 5. 检查工具是否存在 - 使用正确的查询参数（包括plugin_version）
        check_query = {
            "tool_id": tool_dict.get("tool_id"),
            "plugin_version": plugin_version,
        }
        existing_tool_res, _ = tool_repository.tool_get(check_query)

        if existing_tool_res.get("code") == status.HTTP_200_OK:
            # 更新
            tool_repository.tool_save(tool_dict)
        else:
            # 创建
            # 清除时间戳让其自动生成
            tool_dict.pop("create_time", None)
            tool_dict.pop("update_time", None)
            create_res = tool_repository.tool_create(tool_dict)

            if create_res.get("code") != status.HTTP_200_OK:
                message = create_res.get("message", "")
                if "Duplicate entry" in str(message) or "IntegrityError" in str(
                    message
                ):
                    # 工具ID冲突，生成新ID
                    logger.warning(
                        f"[AGENT_IMPORT] Tool {tool_dict.get('tool_id')} exists, generating new ID."
                    )
                    new_tool_id = str(uuid.uuid4())
                    if old_tool_id:
                        tool_id_map[old_tool_id] = new_tool_id
                    tool_dict["tool_id"] = new_tool_id
                    create_res_retry = tool_repository.tool_create(tool_dict)
                    if create_res_retry.get("code") == status.HTTP_200_OK:
                        created_tool_ids.append(new_tool_id)
                else:
                    logger.error(
                        f"[AGENT_IMPORT] Failed to create tool {tool_dict.get('name')}: {message}"
                    )
            else:
                # 记录创建成功的ID
                created_tool_ids.append(tool_dict.get("tool_id"))

    return created_tool_ids


def _collect_knowledge_dependencies(
    knowledge_ids: list[str],
    space_id: str,
    knowledge_bases: list[Dict[str, Any]],
    processed_kb_ids: Set[str],
    index_manager_type: str | None = None,
):
    """收集 Knowledge Base 依赖"""
    if not knowledge_ids:
        return

    for kb_id in knowledge_ids:
        if kb_id in processed_kb_ids:
            continue

        # Get KB Data
        kb_query = KnowledgeBaseGet(
            space_id=space_id, kb_id=kb_id, index_manager_type=index_manager_type
        )
        kb_res = knowledge_base_repository.knowledge_base_get(kb_query)

        if kb_res.code != status.HTTP_200_OK or not kb_res.data:
            logger.warning(f"Failed to export knowledge base {kb_id}: {kb_res.message}")
            continue

        kb_data = kb_res.data

        # Get Embedding Model Info
        embedding_model_info = {}
        emb_config_id = kb_data.get("embedding_model_config_id")
        if emb_config_id:
            with get_db_jw() as db:
                emb_config = (
                    db.query(EmbeddingModelConfig)
                    .filter(EmbeddingModelConfig.id == emb_config_id)
                    .first()
                )
                if emb_config:
                    embedding_model_info = {
                        "model_name": emb_config.model_name,
                        "protocol": emb_config.protocol,
                        "model_id": emb_config.model_id,
                    }

        kb_data["embedding_model_info"] = embedding_model_info

        # Export Documents
        documents_list = []
        with get_db_jw() as db:
            docs = (
                db.query(KnowledgeBaseDocumentDB)
                .filter(
                    KnowledgeBaseDocumentDB.space_id == space_id,
                    KnowledgeBaseDocumentDB.kb_id == kb_id,
                )
                .all()
            )
            for doc in docs:
                # Serialize document
                doc_dict = {
                    "doc_id": doc.doc_id,
                    "name": doc.name,
                    "file_path": doc.file_path,
                    "obs_name": doc.obs_name,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                    "mime_type": doc.mime_type,
                    "status": doc.status,
                    "index_manager_type": doc.index_manager_type,
                    "index_id": doc.index_id,
                    "index_name": doc.index_name,
                    "chunk_count": doc.chunk_count,
                    "process_info": doc.process_info,
                    "doc_metadata": doc.doc_metadata,
                }
                documents_list.append(doc_dict)

        kb_data["documents"] = documents_list

        knowledge_bases.append(kb_data)
        processed_kb_ids.add(kb_id)


def _resolve_embedding_model_id(
    space_id: str, model_info: Dict[str, Any]
) -> Optional[int]:
    """Resolve embedding model ID based on exported info"""
    if not model_info:
        return None

    target_name = model_info.get("model_name")
    target_protocol = model_info.get("protocol")
    target_model_id = model_info.get("model_id")

    with get_db_jw() as db:
        # 1. Try match by protocol and model_id (Most reliable)
        if target_protocol and target_model_id:
            config = (
                db.query(EmbeddingModelConfig)
                .filter(
                    EmbeddingModelConfig.space_id == space_id,
                    EmbeddingModelConfig.protocol == target_protocol,
                    EmbeddingModelConfig.model_id == target_model_id,
                    EmbeddingModelConfig.is_active,
                )
                .first()
            )
            if config:
                return config.id

        # 2. Try match by name and space
        if target_name:
            config = (
                db.query(EmbeddingModelConfig)
                .filter(
                    EmbeddingModelConfig.space_id == space_id,
                    EmbeddingModelConfig.model_name == target_name,
                    EmbeddingModelConfig.is_active,
                )
                .first()
            )
            if config:
                return config.id

    return None


async def _import_knowledge_bases(
    knowledge_bases_data: list[Dict[str, Any]],
    space_id: str,
    kb_id_map: Dict[str, str],
    current_user: dict,
    overwrite: bool = False,
    documents_source_dir: Path = None,
) -> tuple[list[Dict[str, Any]], list[str]]:
    """导入知识库，返回 (创建/更新的资源列表用于回滚, 警告列表)"""
    created_resources = []
    warnings = []

    # 清理 space_id，防止路径穿越
    if space_id:
        safe_space_id = Path(space_id).name.lstrip(".").replace("..", "_")
    else:
        safe_space_id = None

    if not safe_space_id:
        warnings.append(f"空间ID无效，跳过知识库导入: {space_id}\n")
        return created_resources, warnings

    async def import_documents(
        target_kb_id: str, source_kb_id: str, documents: list[Dict[str, Any]]
    ):
        """导入文档记录并处理文件"""
        if not documents:
            return

        # 准备文档ID列表，用于后续处理
        # doc_ids_to_process = []  # No longer used
        # 收集需要处理的文档信息 (doc_id, file_path)
        docs_to_process = []

        # 清理 source_kb_id，防止路径穿越
        if source_kb_id:
            safe_source_kb_id = Path(source_kb_id).name.lstrip(".").replace("..", "_")
        else:
            safe_source_kb_id = None

        if not safe_source_kb_id:
            warnings.append(f"知识库ID无效，跳过文档导入: {source_kb_id}\n")
            return

        # 清理 target_kb_id，防止路径穿越
        if target_kb_id:
            safe_target_kb_id = Path(target_kb_id).name.lstrip(".").replace("..", "_")
        else:
            safe_target_kb_id = None

        if not safe_target_kb_id:
            warnings.append(f"目标知识库ID无效，跳过文档导入: {target_kb_id}\n")
            return

        with get_db_jw() as db:
            for doc_data in documents:
                # 检查是否存在
                existing_doc = (
                    db.query(KnowledgeBaseDocumentDB)
                    .filter(
                        KnowledgeBaseDocumentDB.space_id == space_id,
                        KnowledgeBaseDocumentDB.kb_id == target_kb_id,
                        KnowledgeBaseDocumentDB.doc_id == doc_data["doc_id"],
                    )
                    .first()
                )

                if existing_doc:
                    # 如果文档存在，可能不需要做任何事
                    # 这里简化处理：如果存在，跳过
                    continue
                else:
                    # 创建新文档
                    if overwrite:
                        # 验证用户提供的 doc_id，防止路径穿越
                        raw_doc_id = doc_data.get("doc_id", "")
                        if raw_doc_id:
                            new_doc_id = Path(str(raw_doc_id)).name.lstrip(".").replace("..", "_")
                        else:
                            new_doc_id = None

                        if not new_doc_id:
                            logger.warning(f"[KB_IMPORT] 无效的 doc_id，生成新的 UUID: {raw_doc_id}")
                            new_doc_id = str(uuid.uuid4())
                    else:
                        new_doc_id = str(uuid.uuid4())

                    # 尝试从 ZIP 中恢复文件
                    file_restored = False
                    new_file_path = doc_data.get("file_path")
                    if not new_file_path:
                        name_or_id = doc_data.get("name") or doc_data.get("doc_id") or "unknown"
                        warnings.append(f"文档 \"{name_or_id}\" 的 file_path 缺失，已跳过（不应缺失，请检查导出数据）。\n")
                        continue

                    if documents_source_dir:
                        # 在 ZIP 中查找文件: documents/{source_kb_id}/{filename}
                        # 优先尝试 doc name，因为新版 export 使用 doc name
                        filename = doc_data.get("name")

                        # 防止路径穿越攻击：清理文件名，移除路径分隔符和父目录引用
                        if filename:
                            # 获取纯文件名，移除任何路径组件
                            safe_filename = Path(filename).name
                            # 进一步清理，移除潜在的隐藏文件前缀和危险字符
                            safe_filename = safe_filename.lstrip(".").replace("..", "_")
                        else:
                            safe_filename = None

                        if not safe_filename:
                            warnings.append(f"文档文件名无效，跳过: {filename}\n")
                            continue

                        source_file = documents_source_dir / "documents" / safe_source_kb_id / safe_filename

                        # 安全检查：确保解析后的路径仍在预期的基础目录内
                        expected_base = (documents_source_dir / "documents" / safe_source_kb_id).resolve()
                        try:
                            resolved_source_file = source_file.resolve()
                            if not str(resolved_source_file).startswith(str(expected_base)):
                                logger.warning(f"[KB_IMPORT] 路径穿越攻击尝试被阻止: {filename}")
                                warnings.append(f"文档文件名包含非法路径: {filename}\n")
                                continue
                        except (OSError, ValueError) as path_err:
                            logger.warning(f"[KB_IMPORT] 路径解析失败: {filename}, 错误: {path_err}")
                            warnings.append(f"文档文件名无效: {filename}\n")
                            continue

                        if source_file.exists():
                            # 安全检查：确保是常规文件，不是符号链接或目录
                            try:
                                file_stat = source_file.stat()
                                if not source_file.is_file():
                                    logger.warning(f"[KB_IMPORT] 跳过非文件项: {safe_filename}")
                                    warnings.append(f"文档文件不是常规文件: {safe_filename}\n")
                                    continue
                            except (OSError, IOError) as stat_err:
                                logger.warning(f"[KB_IMPORT] 无法获取文件状态: {safe_filename}, 错误: {stat_err}")
                                warnings.append(f"文档文件状态获取失败: {safe_filename}\n")
                                continue

                            # 复制到系统的知识库存储目录
                            # 路径规则参考 knowledge_base._get_storage_path
                            # backend/data/knowledge_base/{space_id}/{kb_id}/{doc_id}{ext}

                            # 获取后端数据目录 (假设在当前工作区根目录的 backend/data)
                            # 这里需要一种可靠的方式获取数据目录，通常配置在 settings 中
                            # 暂时使用相对路径推断
                            try:
                                # 模拟 kb_mgr._get_storage_path 的逻辑
                                # xxx/agent-studio/backend/openjiuwen_studio/core/manager/agent.py
                                # -> backend/data
                                backend_dir = Path(__file__).resolve().parent.parent.parent.parent
                                storage_path = (
                                    backend_dir
                                    / "data"
                                    / "knowledge_base"
                                    / safe_space_id
                                    / safe_target_kb_id
                                )
                                storage_path.mkdir(parents=True, exist_ok=True)

                                # 生成新文件名
                                target_filename = f"{new_doc_id}{Path(safe_filename).suffix}"
                                target_path = storage_path / target_filename

                                # 验证文件大小，防止元数据欺骗
                                actual_file_size = source_file.stat().st_size
                                declared_file_size = doc_data.get("file_size", 0)
                                if actual_file_size != declared_file_size:
                                    logger.warning(
                                        f"[KB_IMPORT] 文件大小不匹配: {safe_filename} "
                                        f"(实际: {actual_file_size}, 声明: {declared_file_size})"
                                    )
                                    # 可以选择跳过或继续，这里选择继续但记录警告

                                # 可选：文件大小上限检查，防止磁盘耗尽攻击
                                max_file_size = 100 * 1024 * 1024  # 100MB
                                if actual_file_size > max_file_size:
                                    logger.warning(
                                        f"[KB_IMPORT] 文件超过大小限制 ({max_file_size} bytes): {safe_filename}"
                                    )
                                    warnings.append(f"文档文件超过大小限制: {safe_filename}\n")
                                    continue

                                shutil.copy2(source_file, target_path)
                                new_file_path = str(target_path)
                                file_restored = True
                                logger.info(
                                    f"[KB_IMPORT] Restored document file: {safe_filename} -> {target_path}"
                                )
                            except Exception as e:
                                logger.error(f"[KB_IMPORT] Failed to restore file {safe_filename}: {e}")
                                warnings.append(f"文档文件 {safe_filename} 恢复失败: {e}\n")
                        else:
                            doc_name = doc_data.get("name") or doc_data.get("doc_id") or safe_filename or "unknown"
                            warnings.append(f"文档 \"{doc_name}\" 在导入包中未找到文件，已标记为失败。\n")

                    # file_path already validated above (skip if missing); should not be empty here
                    if not new_file_path:
                        warnings.append(
                            f"文档 \"{doc_data.get('name', '')}\" (doc_id: {doc_data.get('doc_id', '')}) "
                            f"在 ZIP 中未找到对应文件且无 file_path，已跳过。\n"
                        )
                        continue

                    new_doc = KnowledgeBaseDocumentDB(
                        space_id=space_id,
                        kb_id=target_kb_id,
                        doc_id=new_doc_id,
                        name=doc_data["name"],
                        file_path=new_file_path,
                        obs_name=doc_data.get("obs_name", ""),
                        file_size=doc_data["file_size"],
                        file_type=doc_data["file_type"],
                        mime_type=doc_data["mime_type"],
                        # 如果文件恢复成功，设置为 UPLOADED 以便触发处理
                        # 否则设置为 FAILED
                        status="uploaded" if file_restored else "failed",
                        index_id=None,  # 清空索引关联
                        index_name=None,
                        index_manager_type=_CURR_INDEX_TYPE,
                        chunk_count=0,
                        process_info={
                            "message": (
                                "Imported from agent export."
                                if file_restored
                                else "Imported but file missing."
                            ),
                            "original_process_info": doc_data.get("process_info"),
                        },
                        doc_metadata=doc_data.get("doc_metadata"),
                        _rest_=doc_data.get("_rest_"),
                        create_time=milliseconds(),
                        update_time=milliseconds(),
                    )
                    db.add(new_doc)

                    if file_restored:
                        docs_to_process.append(
                            {
                                "doc_id": new_doc_id,
                                "file_path": new_file_path,
                                "process_info": doc_data.get("process_info", {}),
                            }
                        )

            db.commit()

        # 触发文档处理（同步/内联 await，不使用 background task 以避免连接上下文丢失问题）
        if docs_to_process:
            try:
                # 显式建立 Milvus 连接 (处理 ConnectionNotExistException)
                try:
                    milvus_host = os.getenv("MILVUS_HOST", "localhost")
                    milvus_port = os.getenv("MILVUS_PORT", "19530")
                    # 尝试连接 default alias，这通常是 pymilvus 的默认连接
                    connections.connect(alias="default", host=milvus_host, port=milvus_port)
                    logger.info("[KB_IMPORT] Explicitly established Milvus connection for import.")
                except Exception as conn_err:
                    logger.warning(
                        f"[KB_IMPORT] Failed to explicitly connect to Milvus: {conn_err}"
                    )

                # 构造策略对象 (使用第一个文档的信息作为模板)
                ref_info = docs_to_process[0].get("process_info", {})

                # ParsingStrategy
                parsing_dict = ref_info.get("parsing_strategy", {})
                if not parsing_dict.get("strategy_type"):
                    parsing_dict["strategy_type"] = "1"
                parsing_strategy = ParsingStrategy(**parsing_dict)

                # SegmentationStrategy
                seg_dict = ref_info.get("segmentation_strategy", {})
                if not seg_dict.get("strategy_type"):
                    seg_dict["strategy_type"] = "1"
                if not seg_dict.get("strategy_config"):
                    seg_dict["strategy_config"] = {"max_tokens": 512, "chunk_overlap_percent": 10}
                segmentation_strategy = SegmentationStrategy(**seg_dict)

                # IndexingStrategy
                idx_dict = ref_info.get("indexing_strategy", {})
                if idx_dict.get("llm_model_id") is None:
                    idx_dict["llm_model_id"] = 0
                indexing_strategy = IndexingStrategy(**idx_dict)

                # 构造基础 process_info
                current_time = milliseconds()
                task_id = str(uuid.uuid4())
                process_info_base = {
                    "task_id": task_id,
                    "parsing_strategy": parsing_strategy.model_dump(),
                    "segmentation_strategy": segmentation_strategy.model_dump(),
                    "indexing_strategy": indexing_strategy.model_dump(),
                    "start_time": current_time,
                    "import_task": True,  # 标记为导入任务
                }

                # 串行处理每个文档
                for idx, doc_item in enumerate(docs_to_process):
                    doc_id = doc_item["doc_id"]
                    file_path = doc_item["file_path"]

                    logger.info(
                        f"[KB_IMPORT] Processing document {idx+1}/{len(docs_to_process)}: {doc_id}"
                    )

                    process_info = {
                        **process_info_base,
                        "current_index": idx + 1,
                        "total_count": len(docs_to_process),
                    }

                    # 直接调用 manager 的内部处理函数 (await)
                    # 这样可以保证在当前上下文（及连接）中执行
                    try:
                        await kb_mgr.process_single_document(
                            space_id=space_id,
                            kb_id=target_kb_id,
                            doc_id=doc_id,
                            file_path=file_path,
                            parsing_strategy=parsing_strategy,
                            segmentation_strategy=segmentation_strategy,
                            indexing_strategy=indexing_strategy,
                            process_info=process_info,
                        )
                    except Exception as inner_e:
                        logger.error(f"[KB_IMPORT] Failed to process document {doc_id}: {inner_e}")
                        # 不中断整个导入，继续下一个
                        continue

                logger.info(
                    f"[KB_IMPORT] Completed document processing for {len(docs_to_process)} documents."
                )

            except Exception as e:
                logger.error(
                    f"[KB_IMPORT] Failed to trigger document processing: {e}", exc_info=True
                )

    for kb_data in knowledge_bases_data:
        old_kb_id = kb_data.get("kb_id")
        if not old_kb_id:
            continue

        target_kb_id = None

        # Check existence - use current environment's index_manager_type
        kb_query = KnowledgeBaseGet(
            space_id=space_id, kb_id=old_kb_id, index_manager_type=_CURR_INDEX_TYPE
        )
        existing_res = knowledge_base_repository.knowledge_base_get(kb_query)

        if existing_res.code == status.HTTP_200_OK and existing_res.data:
            if overwrite:
                # Update logic (only name/desc usually)
                knowledge_base_repository.knowledge_base_update(
                    space_id, old_kb_id, kb_data.get("name"), kb_data.get("description")
                )
                kb_id_map[old_kb_id] = old_kb_id
                target_kb_id = old_kb_id
            else:
                # Reuse existing KB but create copy if overwrite is False (Force Copy)
                logger.info(
                    f"Creating copy of Knowledge Base '{kb_data.get('name')}' because overwrite=False"
                )

                # 1. Generate new ID
                new_kb_id = uuid.uuid4().hex
                kb_id_map[old_kb_id] = new_kb_id

                # 2. Check embedding model
                emb_id = _resolve_embedding_model_id(space_id, kb_data.get("embedding_model_info"))
                if not emb_id:
                    model_id = kb_data.get("embedding_model_info", {}).get("model_id") or "unknown"
                    warning_msg = f"Embedding模型 '{model_id}' 未找到。请手动添加模型信息后再重新配置知识库！\n"
                    logger.warning(warning_msg)
                    warnings.append(warning_msg)
                    # Even if model missing, we mapped ID, but can't create KB effectively without model
                    # skips creation if model missing
                    continue

                # 3. Prepare data for new KB
                new_kb_data = {
                    "space_id": space_id,
                    "kb_id": new_kb_id,
                    "name": f"{kb_data.get('name')}_copy",
                    "description": kb_data.get("description"),
                    "embedding_model_config_id": emb_id,
                    "config": kb_data.get("config"),
                    "index_manager_type": _CURR_INDEX_TYPE,
                    "create_time": milliseconds(),
                    "update_time": milliseconds(),
                }

                # 4. Create KB
                res = knowledge_base_repository.knowledge_base_create(new_kb_data)
                if res.code == status.HTTP_200_OK:
                    created_resources.append({"type": "knowledge_base", "id": new_kb_id})
                    target_kb_id = new_kb_id
                else:
                    logger.error(f"Failed to create copy of KB: {res.message}")
                    warnings.append(f"知识库副本 {new_kb_data['name']} 创建失败！\n")
        else:
            # Create new with original ID
            emb_id = _resolve_embedding_model_id(space_id, kb_data.get("embedding_model_info"))
            if not emb_id:
                model_id = kb_data.get("embedding_model_info", {}).get("model_id") or "unknown"
                warning_msg = (
                    f"Embedding模型 '{model_id}' 未找到。请手动添加模型信息后再重新配置知识库！\n"
                )
                logger.warning(warning_msg)
                warnings.append(warning_msg)
                # Map kb_id to kb_name so the agent config shows the name instead of a broken ID
                kb_id_map[old_kb_id] = kb_data.get("name")
                continue

            # Ensure KB ID is hex (Milvus compatibility)
            target_kb_id_val = uuid.uuid4().hex

            new_kb_data = {
                "space_id": space_id,
                "kb_id": target_kb_id_val,
                "name": kb_data.get("name"),
                "description": kb_data.get("description"),
                "embedding_model_config_id": emb_id,
                "config": kb_data.get("config"),
                "index_manager_type": _CURR_INDEX_TYPE,
                "create_time": milliseconds(),
                "update_time": milliseconds(),
            }

            res = knowledge_base_repository.knowledge_base_create(new_kb_data)
            if res.code == status.HTTP_200_OK:
                created_resources.append({"type": "knowledge_base", "id": target_kb_id_val})
                kb_id_map[old_kb_id] = target_kb_id_val
                target_kb_id = target_kb_id_val
            else:
                # If conflict (globally unique ID used in another space)
                # generate new ID again, and change name
                if (
                    "Duplicate entry" in str(res.message)
                    or "IntegrityError" in str(res.message)
                    or "This db already exists" in str(res.message)
                ):
                    new_kb_id = uuid.uuid4().hex
                    kb_id_map[old_kb_id] = new_kb_id
                    new_kb_data["kb_id"] = new_kb_id
                    new_kb_data["name"] = f"{new_kb_data['name']}_copy"

                    retry_res = knowledge_base_repository.knowledge_base_create(new_kb_data)
                    if retry_res.code == status.HTTP_200_OK:
                        created_resources.append({"type": "knowledge_base", "id": new_kb_id})
                        target_kb_id = new_kb_id
                    else:
                        logger.error(f"Failed to create KB with new ID: {retry_res.message}")
                else:
                    logger.error(f"Failed to create KB: {res.message}")

        # Import documents if KB was created or updated
        if target_kb_id and "documents" in kb_data:
            # 如果是新 KB，或者覆盖模式，都尝试导入文档
            # 传递原始 KB ID 以便在 ZIP 中查找文件
            await import_documents(target_kb_id, old_kb_id, kb_data["documents"])

    return created_resources, warnings


@with_exception_handling
async def agent_export(
    req: AgentExportRequest, current_user: dict
) -> Union[ResponseModel, Tuple[io.BytesIO, str]]:
    """导出智能体及其依赖项"""
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )
    username = data.get("username", "unknown") if isinstance(data, dict) else "unknown"

    logger.info(f"[AGENT_EXPORT] Exporting agent - User: {user_id}, ID: {req.agent_id}")

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 获取Agent基础配置
    agent_query = AgentId(
        space_id=req.space_id, agent_id=req.agent_id, agent_version=req.agent_version
    )
    # 优先获取发布版本，如果没有指定版本，获取draft
    if req.agent_version:
        get_result = agent_repository.get_agent_publish_db(agent_query)
    else:
        get_result = agent_repository.get_agent_db(agent_query)

    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(code=get_result.code, message=get_result.message)

    if not get_result.data:
        return ResponseModel(
            code=StatusCode.AGENT_EXPORT_AGENT_NOT_FOUND.code,
            message=StatusCode.AGENT_EXPORT_AGENT_NOT_FOUND.errmsg,
        )

    agent_data = get_result.data

    # 3. 递归获取依赖项
    workflows = []
    plugins = []
    knowledge_bases = []
    prompt_templates = []

    try:
        # 收集已处理的依赖项ID，防止重复
        processed_workflow_ids: Set[str] = set()
        processed_plugin_ids: Set[str] = set()
        processed_kb_ids: Set[str] = set()
        processed_prompt_ids: Set[str] = set()

        # 3.1 处理直接依赖的Workflows
        agent_workflows = agent_data.get("workflows", []) or []
        for wf in agent_workflows:
            # 兼容处理：尝试获取 "id" 或 "workflow_id"
            wf_id = wf.get("id") or wf.get("workflow_id")
            if wf_id and wf_id not in processed_workflow_ids:
                _collect_workflow_dependencies(
                    wf_id,
                    req.space_id,
                    workflows,
                    processed_workflow_ids,
                    plugins,
                    processed_plugin_ids,
                )

        # 3.2 处理直接依赖的Plugins
        agent_plugins = agent_data.get("plugins", []) or []
        for pl in agent_plugins:
            pl_id = pl.get("plugin_id")
            if pl_id and pl_id not in processed_plugin_ids:
                _collect_plugin_dependencies(
                    pl_id, req.space_id, plugins, processed_plugin_ids
                )
    
        # 3. 处理知识库依赖
        if "knowledge" in agent_data and agent_data["knowledge"]:
            _collect_knowledge_dependencies(
                agent_data["knowledge"],
                req.space_id,
                knowledge_bases,
                processed_kb_ids,
                index_manager_type=_CURR_INDEX_TYPE,
            )

        # 3.4 处理提示词模板依赖
        # 获取Agent关联的prompt模板
        agent_related_info = related_member.RelatedMemberInfo(
            id=req.agent_id,
            version=req.agent_version or "draft",
            type=related_member.MemberType.AGENT,
            name=agent_data.get("agent_name", ""),
        )

        prompt_relations_res = prompt_relation_repository.get_prompt_relate_tbl(
            space_id=req.space_id,
            find_member_info=agent_related_info,
            only_active=True
        )

        if prompt_relations_res.code == status.HTTP_200_OK and prompt_relations_res.data:
            prompt_relations = prompt_relations_res.data

            # 使用直接数据库查询获取完整的prompt模板信息
            with get_db_ops_session() as db:
                # 动态导入prompt相关模型
                for relation in prompt_relations:
                    prompt_id = relation.get("prompt_id")
                    prompt_version = relation.get("prompt_version")

                    # 只要有prompt_id就尝试导出，增加容错性
                    if prompt_id and prompt_id not in processed_prompt_ids:
                        processed_prompt_ids.add(prompt_id)

                        try:
                            # 查询prompt基本信息
                            prompt_basic = db.query(PromptBasicModel).filter(
                                and_(
                                    PromptBasicModel.id == int(prompt_id),
                                    PromptBasicModel.deleted_at.is_(None)
                                )
                            ).first()
                            
                            # 查询prompt提交信息
                            prompt_commit = None

                            # 1. 尝试根据关联的版本号查找
                            if prompt_version and prompt_version != "draft":
                                prompt_commit = (
                                    db.query(PromptCommitModel)
                                    .filter(
                                        and_(
                                            PromptCommitModel.prompt_id == int(prompt_id),
                                            PromptCommitModel.version == prompt_version,
                                        )
                                    )
                                ).first()
                            
                            # 2. 如果没找到，或者版本是draft，或者关联版本查找失败，尝试查找最新提交
                            if not prompt_commit and prompt_basic and prompt_basic.latest_version:
                                prompt_commit = (
                                    db.query(PromptCommitModel)
                                    .filter(
                                        and_(
                                            PromptCommitModel.prompt_id == int(prompt_id),
                                            PromptCommitModel.version
                                            == prompt_basic.latest_version,
                                        )
                                    )
                                ).first()
                                
                            # 3. 如果还是没找到，尝试查找用户草稿
                            prompt_draft = None
                            if not prompt_commit:
                                prompt_draft = (
                                    db.query(PromptUserDraftModel)
                                    .filter(
                                        and_(
                                            PromptUserDraftModel.prompt_id == int(prompt_id),
                                            PromptUserDraftModel.user_id == user_id,
                                            PromptUserDraftModel.deleted_at == 0,
                                        )
                                    )
                                    .first()
                                )

                            # 构建prompt_commit_dict
                            prompt_commit_dict = {}
                            if prompt_commit:
                                prompt_commit_dict = {
                                    "id": prompt_commit.id,
                                    "space_id": prompt_commit.space_id,
                                    "prompt_id": prompt_commit.prompt_id,
                                    "prompt_key": prompt_commit.prompt_key,
                                    "template_type": prompt_commit.template_type,
                                    "messages": prompt_commit.messages,
                                    "prompt_model_config": prompt_commit.prompt_model_config,
                                    "variable_defs": prompt_commit.variable_defs,
                                    "tools": prompt_commit.tools,
                                    "tool_call_config": prompt_commit.tool_call_config,
                                    "version": prompt_commit.version,
                                    "base_version": prompt_commit.base_version,
                                    "committed_by": prompt_commit.committed_by,
                                    "description": prompt_commit.description,
                                }
                            elif prompt_draft:
                                # 使用草稿模拟commit数据
                                prompt_commit_dict = {
                                    "id": None,  # 草稿没有commit id
                                    "space_id": prompt_draft.space_id,
                                    "prompt_id": prompt_draft.prompt_id,
                                    "prompt_key": prompt_basic.prompt_key if prompt_basic else "",
                                    "template_type": prompt_draft.template_type,
                                    "messages": prompt_draft.messages,
                                    "prompt_model_config": prompt_draft.prompt_model_config,
                                    "variable_defs": prompt_draft.variable_defs,
                                    "tools": prompt_draft.tools,
                                    "tool_call_config": prompt_draft.tool_call_config,
                                    "version": (
                                        prompt_version
                                        if prompt_version and prompt_version != "draft"
                                        else "draft"
                                    ),
                                    "base_version": prompt_draft.base_version,
                                    "committed_by": prompt_draft.user_id,
                                    "description": "Exported from draft",
                                }

                            # 构建完整的prompt模板数据
                            prompt_template = {
                                "prompt_id": prompt_id,
                                "prompt_version": prompt_version,
                                "prompt_name": relation.get("prompt_name", ""),
                                "prompt_basic": (
                                    {
                                        "id": prompt_basic.id if prompt_basic else None,
                                        "space_id": prompt_basic.space_id if prompt_basic else None,
                                        "prompt_key": (
                                            prompt_basic.prompt_key if prompt_basic else ""
                                        ),
                                        "name": prompt_basic.name if prompt_basic else "",
                                        "description": (
                                            prompt_basic.description if prompt_basic else ""
                                        ),
                                        "latest_version": (
                                            prompt_basic.latest_version if prompt_basic else ""
                                        ),
                                    }
                                    if prompt_basic
                                    else {}
                                ),
                                "prompt_commit": prompt_commit_dict,
                            }
                            prompt_templates.append(prompt_template)
                        except Exception as e:
                            logger.error(
                                f"[AGENT_EXPORT] Failed to get prompt detail for {prompt_id}: {e}"
                            )
                            # 如果获取失败，使用基本信息
                            prompt_template = {
                                "prompt_id": prompt_id,
                                "prompt_version": prompt_version,
                                "prompt_name": relation.get("prompt_name", ""),
                            }
                            prompt_templates.append(prompt_template)
    except Exception as e:
        logger.error(f"[AGENT_EXPORT] Dependency collection failed: {e}", exc_info=True)
        return ResponseModel(
            code=StatusCode.AGENT_EXPORT_DEPENDENCY_ERROR.code,
            message=StatusCode.AGENT_EXPORT_DEPENDENCY_ERROR.errmsg.format(msg=str(e)),
        )

    # 4. 清理敏感信息 (如 API Key)
    # model字段已弃用，不再处理
    # agent_model_config 中不包含敏感信息，model_id 直接导出供参考

    # 5. 收集模型引用信息（用于跨环境迁移）
    # 使用 provider + model_type 作为key，确保相同模型只导出一次
    model_references = {}
    processed_model_ids = set()  # 避免重复处理相同的模型
    
    def _get_model_ref_key(provider: str, model_type: str) -> str:
        """生成模型引用key，用于去重"""
        return f"{provider}/{model_type}"
    
    def _build_model_reference(model_config) -> ModelReference:
        """构建模型引用对象"""
        return ModelReference(
            provider=model_config.provider,
            model_type=model_config.model_type,
            name=model_config.name,
            base_url=model_config.base_url,
            api_key=None,  # 运行时注入，导出时为null
            timeout=model_config.timeout or 300,
            parameters=model_config.parameters or {"temperature": 0.7, "top_p": 0.9}
        )
    
    def _collect_model_from_config(model_config):
        """收集模型配置，自动去重"""
        if not model_config:
            return
        
        model_id = getattr(model_config, 'id', None)
        if model_id and model_id in processed_model_ids:
            return
        
        ref_key = _get_model_ref_key(model_config.provider, model_config.model_type)
        if ref_key not in model_references:
            model_references[ref_key] = _build_model_reference(model_config)
            logger.info(f"[AGENT_EXPORT] Collected model ref: {ref_key} -> {model_config.name}")
        
        if model_id:
            processed_model_ids.add(model_id)
    
    def _collect_model_from_node(node: dict, wf_id: str, parent_path: str = ""):
        """
        从节点中收集模型引用（递归处理嵌套节点）
        
        Args:
            node: 节点数据
            wf_id: 工作流ID
            parent_path: 父节点路径（用于生成唯一引用key）
        """
        node_id = node.get("id", "unknown")
        node_type = str(node.get("type", ""))  # 确保是字符串
        current_path = f"{parent_path}/{node_id}" if parent_path else node_id
        
        # 处理使用模型的节点类型
        # 节点类型: "3"=LLM大模型, "6"=Intent意图识别, "7"=Questioner提问器
        if node_type in ["3", "6", "7"]:
            try:
                inputs = node.get("data", {}).get("inputs", {})
                llm_param = inputs.get("llmParam", {})
                model_info = llm_param.get("model", {})
                model_id = model_info.get("id")
                
                if model_id:
                    model_id_int = int(model_id)
                    if model_id_int in processed_model_ids:
                        return
                    
                    with get_db_agent_session() as db:
                        model_mgr = ModelConfigManager(db)
                        model_config = model_mgr.get_config_by_id(model_id_int, req.space_id)
                        _collect_model_from_config(model_config)
            except Exception as e:
                logger.warning(f"[AGENT_EXPORT] Failed to get model reference for node {node_id}: {e}")
        
        # 递归处理循环组件内的子节点 (type="8" 表示循环组件)
        if node_type == "8":
            try:
                inputs = node.get("data", {}).get("inputs", {})
                loop_children = inputs.get("loopChildren", [])
                logger.debug(f"[AGENT_EXPORT] Processing loop node {node_id} with {len(loop_children)} children")
                for child_node in loop_children:
                    _collect_model_from_node(child_node, wf_id, current_path)
            except Exception as e:
                logger.warning(f"[AGENT_EXPORT] Failed to process loop node {node_id}: {e}")
        
        # 递归处理子工作流 (type="10" 表示子工作流)
        if node_type == "10":
            try:
                inputs = node.get("data", {}).get("inputs", {})
                sub_wf_schema = inputs.get("subWorkflow", {})
                sub_wf_nodes = sub_wf_schema.get("nodes", [])
                logger.debug(f"[AGENT_EXPORT] Processing sub-workflow node {node_id} with {len(sub_wf_nodes)} nodes")
                for sub_node in sub_wf_nodes:
                    _collect_model_from_node(sub_node, wf_id, current_path)
            except Exception as e:
                logger.warning(f"[AGENT_EXPORT] Failed to process sub-workflow node {node_id}: {e}")
    
    # 5.1 收集Agent主模型引用
    if agent_data.get("model_id"):
        try:
            with get_db_agent_session() as db:
                model_mgr = ModelConfigManager(db)
                model_config = model_mgr.get_config_by_id(agent_data["model_id"], req.space_id)
                _collect_model_from_config(model_config)
        except Exception as e:
            logger.warning(f"[AGENT_EXPORT] Failed to get model reference for agent: {e}")
    
    # 5.2 收集所有Workflow节点模型引用（包括嵌套节点）
    for wf in workflows:
        try:
            wf_id = wf.get("workflow_id") or wf.get("id", "unknown")
            schema = json.loads(wf.get("schema", "{}"))
            nodes = schema.get("nodes", [])
            
            for node in nodes:
                _collect_model_from_node(node, wf_id)
                
        except Exception as e:
            logger.warning(f"[AGENT_EXPORT] Failed to process workflow schema: {e}")

    # 6. 构建导出数据
    version = get_current_project_version()
    export_data = AgentExportData(
        version=version,  # 暂定和代码发布版本相同
        agent=agent_data,
        dependencies=AgentDependencies(
            workflows=workflows,
            plugins=plugins,
            knowledge_bases=knowledge_bases,
            prompt_templates=prompt_templates,
        ),
        metadata=AgentExportMetadata(
            export_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            export_by=username,
            agent_studio_version=version,
        ),
        model_references=model_references if model_references else None,
        env_config=None,  # 后续运行时根据 config_template 自行处理环境变量
    )

    # 检查是否有知识库文档需要导出
    has_documents = any(
        kb.get("documents") for kb in knowledge_bases
    )

    # 统一文件名格式
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    base_filename = f"{agent_data.get('agent_name', 'agent')}-export-{timestamp}"

    if has_documents:
        doc_entries = []
        obs_manager = None
        for kb in knowledge_bases:
            documents = kb.get("documents", [])
            kb_id = kb.get("kb_id", "")
            for doc in documents:
                file_path = doc.get("file_path")
                obs_name = doc.get("obs_name", "")  # NOT NULL; old export JSON may lack this key
                file_name = doc.get("name") or (os.path.basename(file_path) if file_path else None)
                if not file_name:
                    continue
                if not file_path:
                    name_or_id = doc.get("name", "unknown") or doc.get("doc_id", "unknown")
                    raise ValueError(
                        f"文档 \"{name_or_id}\" 的 file_path 缺失，无法导出（不应缺失，请检查数据）。"
                    )
                zip_path = f"documents/{kb_id}/{file_name}"
                if os.path.exists(file_path):
                    doc_entries.append((file_path, zip_path))
                elif obs_name and os.getenv("OBS_BUCKET"):
                    # OBS download only when bucket is configured.
                    if obs_manager is None:
                        obs_manager = kb_mgr.OBSDocumentManager()
                    try:
                        await obs_manager.download_document(object_name=obs_name, file_path=file_path)
                        doc_entries.append((file_path, zip_path))
                    except Exception as e:
                        logger.warning("[AGENT_EXPORT] OBS download skipped for %s: %s", file_name, e)
                else:
                    logger.warning(
                        "[AGENT_EXPORT] Document skipped (local file missing, no OBS): path=%s, name=%s",
                        file_path,
                        file_name,
                    )
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                f"{base_filename}.json",
                json.dumps(export_data.model_dump(), ensure_ascii=False, indent=2),
            )
            for src_path, zpath in doc_entries:
                zip_file.write(src_path, zpath)
        zip_buffer.seek(0)
        filename = f"{base_filename}.zip"
        return zip_buffer, filename

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="export agent success",
        data=export_data.model_dump(),
    )


@with_exception_handling
async def agent_import_from_file(
    file_content: bytes, space_id: str, overwrite: bool, current_user: dict
) -> ResponseModel:
    """处理文件导入（支持 ZIP 和 JSON）"""
    # 安全限制常量
    MAX_EXTRACT_SIZE = 100 * 1024 * 1024  # 文件大小检查，限定100MB
    MAX_FILE_COUNT = 50  # 最多50个文件

    # 临时目录用于解压
    temp_dir = Path(f"/tmp/agent_import_{uuid.uuid4()}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        import_data_dict = None
        is_zip = False

        # 1. 识别文件类型并处理
        file_io = io.BytesIO(file_content)

        if zipfile.is_zipfile(file_io):
            # 处理 ZIP 文件
            try:
                with zipfile.ZipFile(file_io) as zip_file:
                    # 安全检查：防止路径遍历攻击和恶意文件
                    file_list = zip_file.infolist()

                    # 检查点1：检查文件个数，文件个数大于预期值时上报异常退出
                    file_count = len(file_list)
                    if file_count > MAX_FILE_COUNT:
                        return ResponseModel(
                            code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                            message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                                msg=f"ZIP contains {file_count} files, exceeds limit of {MAX_FILE_COUNT}"
                            ),
                        )

                    # 检查点2：检查第一层解压文件总大小，总大小超过设定的上限值
                    total_size = sum(info.file_size for info in file_list)
                    if total_size > MAX_EXTRACT_SIZE:
                        return ResponseModel(
                            code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                            message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                                msg=f"ZIP size exceeds limit ({MAX_EXTRACT_SIZE//(1024*1024)}MB)"
                            ),
                        )

                    # 检查点3：检查磁盘剩余空间是否足够（如果psutil可用）
                    try:
                        disk_usage = psutil.disk_usage(temp_dir)
                        if total_size > disk_usage.free:
                            return ResponseModel(
                                code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                                message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                                    msg=f"ZIP {total_size//(1024*1024)}MB exceeds free disk space"
                                ),
                            )
                    except ImportError:
                        # psutil不可用，跳过磁盘空间检查
                        logger.warning("psutil not available, skipping disk space check")
                    except Exception as e:
                        logger.warning(f"Failed to check disk space: {e}")

                    # 检查点4：检查Zip内文件名是否存在路径穿越风险
                    resolved_temp_dir = temp_dir.resolve()

                    for member in file_list:
                        # 解析目标文件的绝对路径
                        try:
                            # 拼接路径并解析，以处理 '..' 和符号链接
                            # 注意：如果文件不存在，pathlib.resolve() 在不同版本行为不同，
                            # 但此处我们要检查的是路径字符串是否逃逸
                            member_path = temp_dir / member.filename
                            resolved_member_path = member_path.resolve()
                        except Exception:
                            # 尝试使用 os.path.abspath 作为备选，处理 resolve 可能的异常
                            # 但通常 resolve 是最准确的
                            try:
                                resolved_member_path = Path(os.path.abspath(temp_dir / member.filename))
                            except Exception as e:
                                logger.warning(f"Failed to resolve path for {member.filename}: {e}")
                                return ResponseModel(
                                    code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                                    message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                                        msg=f"Invalid file path in ZIP: {member.filename}"
                                    ),
                                )

                        if not str(resolved_member_path).startswith(str(resolved_temp_dir)):
                            logger.warning(
                                f"Zip path traversal attempt detected: {member.filename} -> {resolved_member_path}"
                            )
                            return ResponseModel(
                                code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                                message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                                    msg=f"Security error: Zip contains file with illegal path ({member.filename})"
                                ),
                            )

                    # 所有检查通过之后，解压文件
                    zip_file.extractall(temp_dir)
                    is_zip = True

                    # 查找 agent JSON 配置文件
                    json_files = list(temp_dir.glob("*.json"))
                    if not json_files:
                        return ResponseModel(
                            code=StatusCode.AGENT_IMPORT_CONFIG_MISSING.code,
                            message=StatusCode.AGENT_IMPORT_CONFIG_MISSING.errmsg,
                        )

                    # 假设只有一个 JSON 文件，或者找名字匹配模式的
                    # 优先找包含 '-export-' 的，否则取第一个
                    config_file = next(
                        (f for f in json_files if "-export-" in f.name), json_files[0]
                    )

                    with open(config_file, "r", encoding="utf-8") as f:
                        import_data_dict = json.load(f)

            except zipfile.BadZipFile:
                return ResponseModel(
                    code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                    message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                        msg="Invalid ZIP file format"
                    ),
                )
            except (IOError, OSError) as e:
                return ResponseModel(
                    code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                    message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                        msg=f"File operation error: {e}"
                    ),
                )
            except json.JSONDecodeError as e:
                return ResponseModel(
                    code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                    message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                        msg=f"Invalid JSON in config file: {e}"
                    ),
                )
            except Exception as e:
                logger.warning(f"Unexpected error during ZIP processing: {e}", exc_info=True)
                return ResponseModel(
                    code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                    message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                        msg=f"Error processing ZIP file: {e}"
                    ),
                )

        else:
            # 不是 ZIP，作为 JSON 处理
            try:
                import_data_dict = json.loads(file_content.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return ResponseModel(
                    code=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.code,
                    message=StatusCode.AGENT_IMPORT_FILE_FORMAT_ERROR.errmsg.format(
                        msg="Unsupported format. Use valid ZIP or JSON"
                    ),
                )

        # 2. 构造 AgentImportRequest 对象
        try:
            # import_data_dict 应该符合 AgentExportData 结构
            import_data = AgentExportData(**import_data_dict)

            # 构造请求对象
            req = AgentImportRequest(
                space_id=space_id,
                import_data=import_data,
                overwrite=overwrite
            )

            # 3. 调用核心导入逻辑（复用现有逻辑）
            res = await _agent_import_core(
                req, current_user, documents_source_dir=temp_dir if is_zip else None
            )
            return res

        except ValidationError as e:
            return ResponseModel(
                code=StatusCode.AGENT_IMPORT_DATA_VALIDATION_ERROR.code,
                message=StatusCode.AGENT_IMPORT_DATA_VALIDATION_ERROR.errmsg.format(msg=str(e)),
            )

    except Exception as e:
        logger.error(f"[AGENT_IMPORT_FILE] Error: {e}", exc_info=True)
        return ResponseModel(
            code=StatusCode.AGENT_IMPORT_FAILED.code,
            message=StatusCode.AGENT_IMPORT_FAILED.errmsg.format(msg=str(e)),
        )
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@with_exception_handling
async def agent_import(req: AgentImportRequest, current_user: dict) -> ResponseModel:
    """导入智能体及其依赖项（旧接口，用于JSON请求体）"""
    return await _agent_import_core(req, current_user)


async def _agent_import_core(
    req: AgentImportRequest, 
    current_user: dict, 
    documents_source_dir: Path = None
) -> ResponseModel:
    """导入智能体及其依赖项（核心逻辑）"""
    data = current_user.get("data", {})
    user_id = (
        data.get("user_id_str", "unknown") if isinstance(data, dict) else "unknown"
    )
    space_id = req.space_id

    logger.info(f"[AGENT_IMPORT] Importing agent - User: {user_id}, Space: {space_id}")

    # 1. 验证用户空间权限
    _ = check_user_space(space_id, current_user)

    import_data = req.import_data
    agent_data = import_data.agent
    dependencies = import_data.dependencies
    old_agent_id = agent_data.get("agent_id")

    # Track created resources for rollback
    created_resources = []

    def rollback_resources(resources):
        logger.info(
            f"[AGENT_IMPORT] Rolling back {len(resources)} resources due to error"
        )
        for item in reversed(resources):
            try:
                if item["type"] == "workflow":
                    from openjiuwen_studio.schemas.workflow import WorkflowId

                    wf_id = WorkflowId(
                        workflow_id=item["id"], space_id=space_id, workflow_version=None
                    )
                    workflow_repository.workflow_draft_delete(wf_id)
                elif item["type"] == "tool":
                    tool_repository.tool_delete(
                        {"tool_id": item["id"], "space_id": space_id}
                    )
                elif item["type"] == "plugin":
                    plugin_repository.plugin_delete(
                        {"plugin_id": item["id"], "space_id": space_id}
                    )
                elif item["type"] == "knowledge_base":
                    kb_del_req = KnowledgeBaseGet(space_id=space_id, kb_id=item["id"])
                    knowledge_base_repository.knowledge_base_delete(kb_del_req)
            except Exception as e:
                logger.error(f"[AGENT_IMPORT] Rollback failed for {item}: {e}")

    try:
        # 2. 导入 Plugins
        plugin_id_map = {}
        tool_id_map = {}

        logger.info("[AGENT_IMPORT] Installing plugins from import data")
        for plugin_data in dependencies.plugins:
            old_plugin_id = plugin_data.get("plugin_id")
            if not old_plugin_id:
                continue

            # 检查是否存在
            check_query = {"plugin_id": old_plugin_id, "space_id": space_id}
            existing_plugin_res, _ = plugin_repository.plugin_get(check_query)

            if existing_plugin_res.get("code") == status.HTTP_200_OK and existing_plugin_res.get(
                "data"
            ):
                if req.overwrite:
                    # 覆盖：使用原有ID更新
                    plugin_data["space_id"] = space_id
                    plugin_repository.plugin_save(plugin_data)
                    # 同时也更新工具
                    created_tools = _import_plugin_tools(
                        plugin_data, space_id, tool_id_map
                    )
                    # Note: We don't rollback overwritten plugins/tools usually as it's destructive,
                    # but newly created tools inside existing plugin should probably be tracked.
                    # For simplicity, we only track completely new resources.
                    for tid in created_tools:
                        created_resources.append({"type": "tool", "id": tid})

                    # 记录ID映射
                    plugin_id_map[old_plugin_id] = old_plugin_id
                else:
                    # 如果选择创建副本
                    # 1. 生成新 Plugin ID
                    new_plugin_id = str(uuid.uuid4())
                    plugin_id_map[old_plugin_id] = new_plugin_id

                    # 2. 更新 Plugin 数据
                    plugin_data["plugin_id"] = new_plugin_id
                    plugin_data["name"] = f"{plugin_data.get('name')}_copy"
                    plugin_data["create_time"] = None
                    plugin_data["update_time"] = None

                    # 3. 更新 Tool IDs
                    if "tool_list" in plugin_data and isinstance(plugin_data["tool_list"], list):
                        for tool in plugin_data["tool_list"]:
                            old_tool_id = tool.get("tool_id")
                            if old_tool_id:
                                new_tool_id = str(uuid.uuid4())
                                tool_id_map[old_tool_id] = new_tool_id
                                tool["tool_id"] = new_tool_id

                    # 4. 创建新插件副本
                    logger.info(f"[AGENT_IMPORT] Creating plugin copy {plugin_data.get('name')}")

                    created_pid, created_tools = _create_plugin_and_tools(
                        space_id, plugin_data, tool_id_map
                    )

                    if created_pid:
                        created_resources.append({"type": "plugin", "id": created_pid})
                        for tid in created_tools:
                            created_resources.append({"type": "tool", "id": tid})

                        # 更新 map 为实际创建的 ID
                        plugin_id_map[old_plugin_id] = created_pid
                        logger.info(
                            f"[AGENT_IMPORT] Created plugin copy {plugin_data.get('name')} with ID {created_pid}"
                        )
                    else:
                        logger.error(
                            f"[AGENT_IMPORT] Failed to create plugin copy for {old_plugin_id}"
                        )
            else:
                # 使用_create_plugin_and_tools创建插件和工具
                logger.info(f"[AGENT_IMPORT] Creating plugin {plugin_data.get('name')}")
                plugin_id, created_tools = _create_plugin_and_tools(
                    space_id, plugin_data, tool_id_map
                )

                if plugin_id:
                    created_resources.append({"type": "plugin", "id": plugin_id})
                    for tid in created_tools:
                        created_resources.append({"type": "tool", "id": tid})

                    plugin_id_map[old_plugin_id] = plugin_id
                    logger.info(
                        f"[AGENT_IMPORT] Created plugin {plugin_data.get('name')} with ID {plugin_id}"
                    )
                else:
                    # 创建失败，尝试使用原有逻辑
                    plugin_data["space_id"] = space_id
                    create_res = plugin_repository.plugin_create(plugin_data)

                    # plugin_create 返回的是 dict，不是 ResponseModel
                    if create_res.get("code") != status.HTTP_200_OK:
                        message = create_res.get("message", "")
                        # 捕获 IntegrityError (全局ID冲突)
                        if "Duplicate entry" in str(message) or "IntegrityError" in str(
                            message
                        ):
                            logger.warning(
                                f"[AGENT_IMPORT] Plugin {old_plugin_id} exists in another space, generating new ID."
                            )
                            new_plugin_id = str(uuid.uuid4())
                            plugin_id_map[old_plugin_id] = new_plugin_id
                            plugin_data["plugin_id"] = new_plugin_id
                            plugin_data["plugin_name"] = (
                                f"{plugin_data.get('plugin_name')}_copy"
                            )
                            plugin_data["create_time"] = None
                            plugin_data["update_time"] = None

                            # 同时也需要更新 tool_id，防止 tool_id 冲突
                            if "tool_list" in plugin_data and isinstance(
                                plugin_data["tool_list"], list
                            ):
                                for tool in plugin_data["tool_list"]:
                                    old_tool_id = tool.get("tool_id")
                                    if old_tool_id:
                                        new_tool_id = str(uuid.uuid4())
                                        tool_id_map[old_tool_id] = new_tool_id
                                        tool["tool_id"] = new_tool_id

                            retry_res = plugin_repository.plugin_create(plugin_data)
                            if retry_res.get("code") != status.HTTP_200_OK:
                                logger.error(
                                    f"[AGENT_IMPORT] Failed to create plugin with new ID: {retry_res.get('message')}"
                                )
                            else:
                                created_resources.append(
                                    {"type": "plugin", "id": new_plugin_id}
                                )
                                # 插件创建成功，创建工具
                                created_tools = _import_plugin_tools(
                                    plugin_data, space_id, tool_id_map
                                )
                                for tid in created_tools:
                                    created_resources.append(
                                        {"type": "tool", "id": tid}
                                    )
                        else:
                            logger.error(
                                f"[AGENT_IMPORT] Failed to create plugin {old_plugin_id}: {message}"
                            )
                    else:
                        created_resources.append(
                            {"type": "plugin", "id": plugin_data.get("plugin_id")}
                        )
                        # 插件创建成功，创建工具
                        created_tools = _import_plugin_tools(
                            plugin_data, space_id, tool_id_map
                        )
                        for tid in created_tools:
                            created_resources.append({"type": "tool", "id": tid})

        # 2.5 导入 Knowledge Bases
        kb_id_map = {}
        import_warnings = []
        if dependencies.knowledge_bases:
            logger.info("[AGENT_IMPORT] Installing knowledge bases from import data")
            if documents_source_dir:
                created_kbs, warnings = await _import_knowledge_bases(
                    dependencies.knowledge_bases,
                    space_id,
                    kb_id_map,
                    current_user,
                    req.overwrite,
                    documents_source_dir=documents_source_dir,
                )
            else:
                created_kbs, warnings = await _import_knowledge_bases(
                    dependencies.knowledge_bases, space_id, kb_id_map, current_user, req.overwrite
                )
            created_resources.extend(created_kbs)
            import_warnings.extend(warnings)

        # 2.6 导入 Prompt Templates
        prompt_id_map = {}
        prompt_templates_data = []  # 保存导入的prompt模板数据，用于后续建立关联
        if dependencies.prompt_templates:
            logger.info("[AGENT_IMPORT] Installing prompt templates from import data")

            # 使用直接数据库操作导入prompt模板
            with get_db_ops_session() as db:
                for prompt_data in dependencies.prompt_templates:
                    old_prompt_id = prompt_data.get("prompt_id")
                    if not old_prompt_id:
                        continue

                    raw_version = prompt_data.get("prompt_version")
                    # 如果版本为空，默认设为0.0.1，以确保能生成有效的Commit记录
                    if not raw_version:
                        prompt_version = "0.0.1"
                    else:
                        prompt_version = raw_version

                    prompt_name = prompt_data.get(
                        "prompt_name", f"导入的提示词_{old_prompt_id}"
                    )  # 默认名称

                    # 确保prompt_basic_data和prompt_commit_data不为空
                    prompt_basic_data = prompt_data.get("prompt_basic", {})
                    prompt_commit_data = prompt_data.get("prompt_commit", {})

                    # 容错处理：如果 prompt_commit 为空，尝试从 agent config 中恢复 system prompt
                    if not prompt_commit_data or not prompt_commit_data.get("messages"):
                        logger.warning(
                            f"[AGENT_IMPORT] Prompt commit data is empty for {prompt_name}, "
                            f"trying to recover from agent config"
                        )

                        # 尝试从 agent.configs.system_prompt 恢复
                        system_prompt = agent_data.get("configs", {}).get("system_prompt")
                        if system_prompt:
                            # 构造 messages 结构
                            recovered_messages = json.dumps([
                                {
                                    "role": "system",
                                    "content": system_prompt
                                }
                            ], ensure_ascii=False)
                            
                            if not prompt_commit_data:
                                prompt_commit_data = {}

                            prompt_commit_data["messages"] = recovered_messages
                            prompt_commit_data["template_type"] = "normal"  # 默认为普通模板
                            prompt_commit_data["version"] = prompt_version
                            prompt_commit_data["description"] = "Recovered from agent config"

                            # 尝试恢复 prompt_model_config
                            if not prompt_commit_data.get("prompt_model_config"):
                                agent_model = agent_data.get("model", {}).get("model_info", {})
                                if agent_model:
                                    prompt_commit_data["prompt_model_config"] = json.dumps(
                                        {
                                            "parameters": {
                                                "temperature": agent_model.get("temperature", 0.7),
                                                "max_tokens": agent_model.get("max_tokens", 4096),
                                                "top_p": agent_model.get("top_p", 0.9),
                                            }
                                        }
                                    )

                            logger.info(
                                f"[AGENT_IMPORT] Recovered prompt messages from agent config for {prompt_name}"
                            )

                    try:
                        # 2.1 检查是否存在 (根据 prompt_key 和 version)
                        original_key = (
                            prompt_basic_data.get("prompt_key") or f"prompt_{old_prompt_id}"
                        )
                        target_version = prompt_commit_data.get("version") or prompt_version

                        existing_basic = (
                            db.query(PromptBasicModel)
                            .filter(
                                and_(
                                    PromptBasicModel.space_id == space_id,
                                    PromptBasicModel.prompt_key == original_key,
                                    PromptBasicModel.deleted_at.is_(None),
                                )
                            )
                            .first()
                        )

                        current_prompt_id = None

                        if existing_basic:
                            # 检查版本是否匹配
                            existing_commit = (
                                db.query(PromptCommitModel)
                                .filter(
                                    and_(
                                        PromptCommitModel.prompt_id == existing_basic.id,
                                        PromptCommitModel.version == target_version,
                                    )
                                )
                                .first()
                            )

                            if existing_commit:
                                # 存在且版本匹配，直接复用
                                current_prompt_id = existing_basic.id

                        if not current_prompt_id:
                            # 2.2 不存在或版本不匹配，创建新的
                            # 确定新的prompt_key
                            if existing_basic:
                                # Key已存在但版本不匹配，需要使用新Key避免冲突
                                unique_suffix = str(uuid.uuid4())[:8]
                                new_prompt_key = f"{original_key}_{unique_suffix}"
                                logger.info(
                                    f"[AGENT_IMPORT] Prompt key {original_key} exists but version mismatch. "
                                    f"Creating new with key: {new_prompt_key}"
                                )
                            else:
                                # Key不存在，尝试使用原始Key
                                new_prompt_key = original_key
                                logger.info(
                                    f"[AGENT_IMPORT] Creating new prompt template with key: {new_prompt_key}"
                                )

                            # 创建 PromptBasicModel
                            new_prompt_basic = PromptBasicModel(
                                space_id=space_id,
                                prompt_key=new_prompt_key,
                                name=prompt_basic_data.get("name", prompt_name),
                                description=prompt_basic_data.get(
                                    "description", "导入的提示词模板"
                                ),
                                created_by=data.get("user_id_str", "unknown"),
                                updated_by=data.get("user_id_str", "unknown"),
                                latest_version=target_version,  # 使用当前导入的版本作为最新版本，确保一致性
                                latest_commit_time=datetime.datetime.now(
                                    datetime.timezone.utc
                                ).replace(tzinfo=None),
                            )
                            db.add(new_prompt_basic)
                            db.flush()  # 获取数据库生成的自增ID

                            current_prompt_id = new_prompt_basic.id

                            # 创建 PromptCommitModel
                            new_prompt_commit = PromptCommitModel(
                                space_id=space_id,
                                prompt_id=current_prompt_id,
                                prompt_key=new_prompt_key,
                                template_type=prompt_commit_data.get("template_type", "normal"),
                                messages=prompt_commit_data.get("messages", ""),
                                prompt_model_config=prompt_commit_data.get(
                                    "prompt_model_config", ""
                                ),
                                variable_defs=prompt_commit_data.get("variable_defs", ""),
                                tools=prompt_commit_data.get("tools", ""),
                                tool_call_config=prompt_commit_data.get("tool_call_config", ""),
                                version=prompt_commit_data.get("version", prompt_version),
                                base_version=prompt_commit_data.get("base_version", ""),
                                committed_by=prompt_commit_data.get(
                                    "committed_by", data.get("username", "unknown")
                                ),
                                description=prompt_commit_data.get(
                                    "description", "导入的提示词版本"
                                ),
                            )
                            db.add(new_prompt_commit)

                            logger.info(
                                f"[AGENT_IMPORT] Created new prompt {current_prompt_id} "
                                f"(version: {new_prompt_commit.version})"
                            )

                        # 记录ID映射
                        prompt_id_map[old_prompt_id] = str(current_prompt_id)

                        # 无论prompt模板是否已存在，都要为目标用户创建prompt草稿
                        # 这样用户才能在前端提示词管理中看到导入的模板
                        user_id = data.get("user_id_str", "unknown")

                        # 检查草稿是否已存在
                        existing_draft = (
                            db.query(PromptUserDraftModel)
                            .filter(
                                PromptUserDraftModel.prompt_id == int(current_prompt_id),
                                PromptUserDraftModel.user_id == user_id,
                                PromptUserDraftModel.deleted_at == 0,
                            )
                            .first()
                        )

                        if not existing_draft:
                            # 获取提交数据（如果存在的话）
                            # 由于总是创建新的提交记录，所以直接使用prompt_commit_data
                            commit_data = prompt_commit_data or {}

                            # 创建新草稿
                            new_draft = PromptUserDraftModel(
                                space_id=int(space_id),
                                prompt_id=int(current_prompt_id),
                                user_id=user_id,
                                template_type=commit_data.get("template_type", "normal"),
                                messages=commit_data.get("messages", ""),
                                prompt_model_config=commit_data.get("prompt_model_config", ""),
                                variable_defs=commit_data.get("variable_defs", ""),
                                tools=commit_data.get("tools", ""),
                                tool_call_config=commit_data.get("tool_call_config", ""),
                                base_version=target_version,
                                is_draft_edited=False,
                                deleted_at=0,
                            )
                            db.add(new_draft)

                        logger.info(
                            f"[AGENT_IMPORT] Processed prompt template: {prompt_name} "
                            f"(ID: {prompt_id_map[old_prompt_id]})"
                        )
                        # 保存prompt模板数据，用于后续建立关联
                        prompt_templates_data.append(
                            {
                                "old_prompt_id": old_prompt_id,
                                "prompt_version": prompt_version,
                                "prompt_name": prompt_name,
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"[AGENT_IMPORT] Failed to import prompt template {old_prompt_id}: {e}"
                        )
                        # 记录原始ID映射，以便后续处理
                        prompt_id_map[old_prompt_id] = old_prompt_id

                # 提交所有更改
                db.commit()

        # 3. 导入 Workflows
        workflow_id_map = {}
        workflow_name_map = {}

        # 使用反向迭代，先处理子工作流，再处理父工作流
        reversed_workflows = list(reversed(dependencies.workflows))

        for wf_data in reversed_workflows:
            old_wf_id = wf_data.get("workflow_id")
            if not old_wf_id:
                continue

            # 0. 先尝试更新 schema 中的依赖引用 (使用已有的 map)
            if "schema" in wf_data and wf_data["schema"]:
                try:
                    schema_obj = json.loads(wf_data["schema"])
                    updated_schema = schema_obj

                    # 更新工作流ID引用
                    if workflow_id_map:
                        updated_schema = _update_workflow_ids_in_json(
                            updated_schema, workflow_id_map
                        )

                    # 更新插件ID引用
                    if plugin_id_map:
                        updated_schema = _update_plugin_ids_in_json(updated_schema, plugin_id_map)

                    # 更新工具ID引用
                    if tool_id_map:
                        updated_schema = _update_tool_ids_in_json(updated_schema, tool_id_map)

                    # 如果 schema 发生变化，更新 wf_data
                    if updated_schema != schema_obj:
                        wf_data["schema"] = json.dumps(updated_schema, ensure_ascii=False)
                        logger.info(
                            f"[AGENT_IMPORT] Updated schema for workflow {old_wf_id} with new dependencies"
                        )
                except Exception as e:
                    logger.warning(
                        f"[AGENT_IMPORT] Failed to update schema for workflow {old_wf_id}: {e}"
                    )

            # 检查是否存在
            from openjiuwen_studio.schemas.workflow import WorkflowId

            wf_query = WorkflowId(
                space_id=space_id, workflow_id=old_wf_id, workflow_version=None
            )
            existing_wf = workflow_repository.workflow_get(wf_query)

            # 根据用户需求：如果当前用户空间下不存在同样workflow_id的工作流，就直接生成新ID
            # 这是为了避免id冲突错误，因为workflow_id在数据库中是全局唯一的，可能在其他空间已存在
            if existing_wf.code == status.HTTP_200_OK and existing_wf.data:
                if req.overwrite:
                    # 覆盖现有工作流
                    wf_data["space_id"] = space_id
                    workflow_repository.workflow_save(wf_data)
                else:
                    # 当前空间存在且不允许覆盖，生成新ID
                    new_wf_id = str(uuid.uuid4())
                    workflow_id_map[old_wf_id] = new_wf_id
                    wf_data["workflow_id"] = new_wf_id
                    wf_data["name"] = f"{wf_data.get('name')}_copy"
                    workflow_name_map[old_wf_id] = wf_data["name"]

                    # 创建新工作流
                    wf_data["space_id"] = space_id
                    wf_data["create_time"] = None
                    wf_data["update_time"] = None

                    try:
                        wf_obj = WorkflowBaseDBPd(**wf_data)
                        wf_obj.create_time = None
                        wf_obj.update_time = None

                        create_res = workflow_repository.workflow_create(wf_obj)
                        if create_res.code == status.HTTP_200_OK:
                            created_resources.append({"type": "workflow", "id": new_wf_id})
                            logger.info(
                                f"[AGENT_IMPORT] Created copy workflow: {new_wf_id} (original: {old_wf_id})"
                            )
                        else:
                            logger.error(
                                f"[AGENT_IMPORT] Failed to create copy workflow {old_wf_id}: "
                                f"{create_res.message}"
                            )
                    except Exception as e:
                        logger.error(
                            f"[AGENT_IMPORT] Failed to create copy workflow {old_wf_id}: {e}"
                        )
            else:
                # 当前用户空间下不存在该workflow_id，直接生成新的workflow_id来写入，避免id冲突
                new_wf_id = str(uuid.uuid4())
                workflow_id_map[old_wf_id] = new_wf_id
                wf_data["workflow_id"] = new_wf_id

                # 创建新工作流
                wf_data["space_id"] = space_id
                wf_data["create_time"] = None
                wf_data["update_time"] = None

                try:
                    wf_obj = WorkflowBaseDBPd(**wf_data)
                    wf_obj.create_time = None
                    wf_obj.update_time = None

                    create_res = workflow_repository.workflow_create(wf_obj)
                    if create_res.code == status.HTTP_200_OK:
                        created_resources.append({"type": "workflow", "id": new_wf_id})
                        logger.info(
                            f"[AGENT_IMPORT] Created workflow with new ID: {new_wf_id} (original: {old_wf_id})"
                        )
                    else:
                        logger.error(
                            f"[AGENT_IMPORT] Failed to create workflow {old_wf_id}: {create_res.message}"
                        )
                except Exception as e:
                    logger.error(f"[AGENT_IMPORT] Failed to create workflow {old_wf_id}: {e}")

        # 4. 导入 Agent

        # 4.0 处理模型引用映射（用于跨环境迁移）
        model_id_map = {}
        if import_data.model_references:
            logger.info(f"[AGENT_IMPORT] Resolving model references: {import_data.model_references}")
            
            for ref_key, reference in import_data.model_references.items():
                try:
                    # 匹配本地模型
                    matched_model = _match_model_reference(reference, space_id)
                    if matched_model:
                        model_id_map[ref_key] = matched_model.id
                        logger.info(
                            f"[AGENT_IMPORT] Matched model {ref_key}: {reference.name} -> "
                            f"{matched_model.name} (ID: {matched_model.id})"
                        )
                    else:
                        logger.warning(
                            f"[AGENT_IMPORT] No matching model found for {ref_key}: "
                            f"{reference.provider}/{reference.model_type}"
                        )
                except Exception as e:
                    logger.warning(f"[AGENT_IMPORT] Failed to match model {ref_key}: {e}")

        # 更新Agent主模型ID
        if "agent_model" in model_id_map:
            old_model_id = agent_data.get("model_id")
            agent_data["model_id"] = model_id_map["agent_model"]
            logger.info(f"[AGENT_IMPORT] Mapped agent model: {old_model_id} -> {agent_data['model_id']}")

        # 更新Workflow节点中的模型ID
        if "workflows" in agent_data and agent_data["workflows"]:
            for wf in agent_data["workflows"]:
                wf_id = wf.get("workflow_id") or wf.get("id")
                if wf_id and wf_id in workflow_id_map:
                    # 这个workflow被导入了，需要更新其中的模型ID
                    schema = wf.get("schema", "{}")
                    if isinstance(schema, str):
                        try:
                            schema_obj = json.loads(schema)
                        except json.JSONDecodeError:
                            schema_obj = {}
                    else:
                        schema_obj = schema
                    
                    for node in schema_obj.get("nodes", []):
                        node_type = str(node.get("type", ""))
                        # 节点类型: "3"=LLM, "6"=Intent, "7"=Questioner, "8"=Loop, "10"=SubWorkflow
                        if node_type in ["3", "6", "7", "8", "10"]:
                            _update_node_model_recursive(node, model_id_map, wf_id)
                    
                    # 更新schema
                    wf["schema"] = json.dumps(schema_obj, ensure_ascii=False)

        # 更新引用了plugin_id/tool_id的字段
        if "plugins" in agent_data and agent_data["plugins"]:
            logger.info(
                f"[AGENT_IMPORT] Updating plugin references in agent config. "
                f"Maps: Plugins={plugin_id_map}, Tools={tool_id_map}"
            )
            new_plugins_list = []
            for p in agent_data["plugins"]:
                # 1. 更新 ID
                p_id = p.get("plugin_id")
                if p_id and p_id in plugin_id_map:
                    p["plugin_id"] = plugin_id_map[p_id]

                t_id = p.get("tool_id")
                if t_id and t_id in tool_id_map:
                    p["tool_id"] = tool_id_map[t_id]

                # 2. 从数据库获取最新信息以更新名称等字段 (确保与安装的一致)
                current_plugin_id = p.get("plugin_id")
                current_tool_id = p.get("tool_id")

                if current_plugin_id and current_tool_id:
                    # 获取插件信息
                    plugin_res, _ = plugin_repository.plugin_get(
                        {"plugin_id": current_plugin_id, "space_id": space_id}
                    )
                    # 获取工具信息
                    tool_res, _ = tool_repository.tool_get(
                        {"tool_id": current_tool_id, "space_id": space_id}
                    )

                    if plugin_res.get("code") == status.HTTP_200_OK and plugin_res.get(
                        "data"
                    ):
                        plugin_info = plugin_res["data"]
                        # 处理PluginBaseDB对象或字典
                        if hasattr(plugin_info, "name"):
                            p["plugin_name"] = plugin_info.name
                        elif isinstance(plugin_info, dict):
                            p["plugin_name"] = plugin_info.get("name")
                        else:
                            # 尝试转换为字典
                            try:
                                p["plugin_name"] = getattr(plugin_info, "name", None)
                            except Exception:
                                p["plugin_name"] = None

                    if tool_res.get("code") == status.HTTP_200_OK and tool_res.get(
                        "data"
                    ):
                        tool_info = tool_res["data"]
                        # 处理ToolBaseDB对象或字典
                        if hasattr(tool_info, "name"):
                            p["tool_name"] = tool_info.name
                        elif isinstance(tool_info, dict):
                            p["tool_name"] = tool_info.get("name")
                        else:
                            # 尝试转换为字典
                            try:
                                p["tool_name"] = getattr(tool_info, "name", None)
                            except Exception:
                                p["tool_name"] = None

                new_plugins_list.append(p)
            agent_data["plugins"] = new_plugins_list

        # 更新引用了workflow_id的字段
        if workflow_id_map:
            logger.info(
                f"[AGENT_IMPORT] Updating workflow IDs in agent config: {workflow_id_map}"
            )
            # Update workflows list
            if "workflows" in agent_data and agent_data["workflows"]:
                for wf in agent_data["workflows"]:
                    # Update ID inside the workflow reference list
                    old_ref_id = wf.get("id") or wf.get("workflow_id")
                    if old_ref_id and old_ref_id in workflow_id_map:
                        new_id = workflow_id_map[old_ref_id]
                        if "id" in wf:
                            wf["id"] = new_id
                        if "workflow_id" in wf:
                            wf["workflow_id"] = new_id

                        # Update name if it was changed (copy created)
                        if old_ref_id in workflow_name_map:
                            new_name = workflow_name_map[old_ref_id]
                            if "name" in wf:
                                wf["name"] = new_name
                            if "workflow_name" in wf:
                                wf["workflow_name"] = new_name

            # Update configs
            if "configs" in agent_data and agent_data["configs"]:
                agent_data["configs"] = _update_workflow_ids_in_json(
                    agent_data["configs"], workflow_id_map
                )

            # Update constraint if needed
            if "constraint" in agent_data and agent_data["constraint"]:
                agent_data["constraint"] = _update_workflow_ids_in_json(
                    agent_data["constraint"], workflow_id_map
                )

        # Update knowledge list
        if "knowledge" in agent_data and agent_data["knowledge"]:
            logger.info(
                f"[AGENT_IMPORT] Updating knowledge references in agent config: {kb_id_map}"
            )
            new_knowledge_list = []
            for k_id in agent_data["knowledge"]:
                if k_id in kb_id_map:
                    new_knowledge_list.append(kb_id_map[k_id])
                else:
                    new_knowledge_list.append(k_id)
            agent_data["knowledge"] = new_knowledge_list

        # Update prompt template references
        if "prompt_template" in agent_data and agent_data["prompt_template"]:
            logger.info(
                f"[AGENT_IMPORT] Updating prompt template references in agent config: {prompt_id_map}"
            )
            # 这里需要根据实际的prompt_template结构进行更新
            # 假设prompt_template中包含prompt_id字段
            if isinstance(agent_data["prompt_template"], dict):
                old_prompt_id = agent_data["prompt_template"].get("prompt_id")
                if old_prompt_id and old_prompt_id in prompt_id_map:
                    agent_data["prompt_template"]["prompt_id"] = prompt_id_map[old_prompt_id]

        old_agent_id = agent_data.get("agent_id")

        # 检查 Agent 是否存在于当前空间
        agent_query = AgentId(
            space_id=space_id, agent_id=old_agent_id, agent_version=None
        )
        existing_agent = agent_repository.get_agent_db(agent_query)

        final_agent_id = old_agent_id

        # 如果当前空间下已存在该ID
        if existing_agent.code == status.HTTP_200_OK:
            if req.overwrite:
                # 覆盖：更新
                agent_data["space_id"] = space_id
                agent_data["update_time"] = milliseconds()

                # model_id 在不同环境可能不同，导入时作为参考，保留原值
                # agent_model_config 不包含敏感信息，直接导入

                # 创建AgentBaseDBPd实例 (不再处理model字段)
                agent_obj = AgentBaseDBPd(**agent_data)
                save_res = agent_repository.save_agent_db(agent_obj)
                if save_res.code != status.HTTP_200_OK:
                    logger.error(
                        f"[AGENT_IMPORT] Failed to update agent {old_agent_id}: {save_res.message}"
                    )
                    rollback_resources(created_resources)
                    return ResponseModel(
                        code=StatusCode.AGENT_IMPORT_AGENT_CREATE_ERROR.code,
                        message=StatusCode.AGENT_IMPORT_AGENT_CREATE_ERROR.errmsg.format(
                            msg=save_res.message
                        ),
                    )
            else:
                # 不覆盖，创建副本：生成新的agent_id
                new_agent_id = str(uuid.uuid4())
                agent_data["agent_id"] = new_agent_id
                # 更新agent_name，添加_copy后缀
                agent_data["agent_name"] = f"{agent_data.get('agent_name', 'agent')}_copy"
                agent_data["space_id"] = space_id
                agent_data["create_time"] = milliseconds()
                agent_data["update_time"] = milliseconds()
                # 确保没有 agent_version (Draft)
                agent_data.pop("agent_version", None)
                agent_data.pop("latest_publish_version", None)
                agent_data.pop("latest_publish_time", None)

                # 创建AgentBaseDBPd实例 (不再处理model字段)
                logger.info(
                    f"[AGENT_IMPORT] Creating agent copy with new ID {new_agent_id} (original: {old_agent_id})"
                )
                agent_obj = AgentBaseDBPd(**agent_data)
                create_res = agent_repository.create_agent_db(agent_obj)

                if create_res.code != status.HTTP_200_OK:
                    # 捕获 IntegrityError: ID已存在但不在当前space下
                    logger.error(
                        f"[AGENT_IMPORT] Failed to create agent copy: {create_res.message}"
                    )
                    rollback_resources(created_resources)
                    return ResponseModel(
                        code=StatusCode.AGENT_IMPORT_AGENT_CREATE_ERROR.code,
                        message=StatusCode.AGENT_IMPORT_AGENT_CREATE_ERROR.errmsg.format(
                            msg=create_res.message
                        ),
                    )

                final_agent_id = new_agent_id
        else:
            # 直接生成新的agent_id，避免全局冲突
            new_agent_id = str(uuid.uuid4())
            agent_data["agent_id"] = new_agent_id
            agent_data["space_id"] = space_id
            agent_data["create_time"] = milliseconds()
            agent_data["update_time"] = milliseconds()
            # 确保没有 agent_version (Draft)
            agent_data.pop("agent_version", None)
            agent_data.pop("latest_publish_version", None)
            agent_data.pop("latest_publish_time", None)

            logger.info(f"[AGENT_IMPORT] Creating agent with new ID {new_agent_id}")
            agent_obj = AgentBaseDBPd(**agent_data)
            create_res = agent_repository.create_agent_db(agent_obj)

            if create_res.code != status.HTTP_200_OK:
                # 捕获 IntegrityError: ID已存在但不在当前space下
                logger.error(
                    f"[AGENT_IMPORT] Failed to create agent: {create_res.message}"
                )
                rollback_resources(created_resources)
                return ResponseModel(
                    code=StatusCode.AGENT_IMPORT_AGENT_CREATE_ERROR.code,
                    message=StatusCode.AGENT_IMPORT_AGENT_CREATE_ERROR.errmsg.format(
                        msg=create_res.message
                    ),
                )

            final_agent_id = new_agent_id

        # 建立prompt与agent的关联关系
        if prompt_templates_data:
            for prompt_data in prompt_templates_data:
                old_prompt_id = prompt_data.get("old_prompt_id")
                prompt_version = prompt_data.get("prompt_version")
                prompt_name = prompt_data.get("prompt_name", "")

                # 获取实际的prompt_id（可能是原始ID或新生成的ID）
                actual_prompt_id = prompt_id_map.get(old_prompt_id, old_prompt_id)

                try:
                    # 构建prompt信息
                    prompt_info = related_member.RelatedMemberInfo(
                        id=actual_prompt_id,
                        version=prompt_version,
                        type=related_member.MemberType.PROMPT,
                        name=prompt_name,
                    )

                    # 构建agent信息
                    agent_info = related_member.RelatedMemberInfo(
                        id=final_agent_id,  # 这是导入后的agent_id
                        version="draft",  # 导入的agent默认是draft版本
                        type=related_member.MemberType.AGENT,
                        name=agent_data.get("agent_name", ""),
                    )

                    # 创建或更新关联关系
                    prompt_relation_repository.create_prompt_relate_tbl(
                        space_id=space_id,
                        prompt_info=prompt_info,
                        relate_member_info=agent_info
                    )
                except Exception as e:
                    logger.error(
                        f"[AGENT_IMPORT] Failed to create relation between prompt {actual_prompt_id} "
                        f"and agent {final_agent_id}: {e}"
                    )

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="import agent success",
            data={"agent_id": final_agent_id, "warnings": import_warnings},
        )

    except Exception as e:
        logger.error(f"[AGENT_IMPORT] Exception during import: {e}", exc_info=True)
        rollback_resources(created_resources)
        return ResponseModel(
            code=StatusCode.AGENT_IMPORT_FAILED.code,
            message=StatusCode.AGENT_IMPORT_FAILED.errmsg.format(msg=str(e)),
        )


def _match_model_reference(reference: ModelReference, space_id: str):
    """
    匹配模型引用到本地模型
    
    匹配策略：
    1. 精确匹配：provider + model_type
    2. 模糊匹配：provider + name similarity
    
    Returns:
        匹配到的模型配置对象，或 None
    """
    try:
        with get_db_agent_session() as db:
            model_mgr = ModelConfigManager(db)
            # 获取空间下的所有模型
            models, _ = model_mgr.get_paginated_configs(
                page=1, size=1000, filters={"space_id": space_id}
            )
            
            if not models:
                return None
            
            # 1. 精确匹配：provider + model_type
            for model in models:
                if (model.provider == reference.provider and 
                    model.model_type == reference.model_type):
                    return model
            
            # 2. 模糊匹配：provider + name similarity
            # 简单实现：相同 provider 且名称包含关系
            for model in models:
                if model.provider == reference.provider:
                    ref_name = reference.name.lower()
                    model_name = model.name.lower()
                    # 名称互相包含视为匹配
                    if ref_name in model_name or model_name in ref_name:
                        return model
            
            return None
    except Exception as e:
        logger.error(f"[AGENT_IMPORT] Error matching model reference: {e}")
        return None


def _update_node_model_id(node: dict, new_model_id: int):
    """
    更新节点中的模型ID
    
    与 node schema 对齐：
    - LLM/Intent/Questioner 节点：node.data.inputs.llmParam.model.id
    """
    try:
        data = node.get("data", {})
        inputs = data.get("inputs", {})
        llm_param = inputs.get("llmParam", {})
        model_info = llm_param.get("model", {})
        
        old_id = model_info.get("id")
        model_info["id"] = str(new_model_id)
        
        logger.debug(f"[AGENT_IMPORT] Updated node {node.get('id')} model: {old_id} -> {new_model_id}")
    except Exception as e:
        logger.warning(f"[AGENT_IMPORT] Failed to update node model ID: {e}")


def _update_node_model_recursive(node: dict, model_id_map: dict, wf_id: str):
    """
    递归更新节点中的模型ID（支持嵌套节点）
    
    Args:
        node: 节点数据
        model_id_map: 模型ID映射表
        wf_id: 工作流ID
    """
    node_id = node.get("id", "unknown")
    node_type = str(node.get("type", ""))
    ref_key = f"node_{node_id}"
    
    # 更新当前节点的模型ID（如果是使用模型的节点）
    if node_type in ["3", "6", "7"] and ref_key in model_id_map:
        _update_node_model_id(node, model_id_map[ref_key])
    
    # 递归处理循环组件内的子节点 (type="8")
    if node_type == "8":
        try:
            inputs = node.get("data", {}).get("inputs", {})
            loop_children = inputs.get("loopChildren", [])
            for child_node in loop_children:
                _update_node_model_recursive(child_node, model_id_map, wf_id)
        except Exception as e:
            logger.warning(f"[AGENT_IMPORT] Failed to update loop node {node_id}: {e}")
    
    # 递归处理子工作流内的节点 (type="10")
    if node_type == "10":
        try:
            inputs = node.get("data", {}).get("inputs", {})
            sub_wf_schema = inputs.get("subWorkflow", {})
            sub_wf_nodes = sub_wf_schema.get("nodes", [])
            for sub_node in sub_wf_nodes:
                _update_node_model_recursive(sub_node, model_id_map, wf_id)
        except Exception as e:
            logger.warning(f"[AGENT_IMPORT] Failed to update sub-workflow node {node_id}: {e}")
