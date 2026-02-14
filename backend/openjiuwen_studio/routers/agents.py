#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Optional
from urllib.parse import quote
from starlette.responses import StreamingResponse
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, Body, Request
from pydantic import ValidationError

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common.language_thread_context import get_language
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.manager.model_manager.managers import ModelConfigManager
from openjiuwen_studio.core.utils.compatible_field import mask_sensitive_fields
from openjiuwen_studio.routers.common import handle_response, validate_request
import openjiuwen_studio.core.manager.agent as mgr
from openjiuwen_studio.routers.models import get_model_config_manager
from openjiuwen_studio.schemas.agent import AgentCreate, AgentGet, AgentDisplayInfo, AgentList, AgentPublish, \
    AgentGetVersion, AgentUpdate, AgentCopy, AgentId, AgentSearchRequest, AgentVersionListRequest, \
    AgentVersionListResponse, AgentExportRequest, AgentImportRequest
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.execution_log import ExecutionLogsCreateList, ApiExecutionLogGet, \
    ApiExecutionLogsDebugEnter, AgExecutionLogsFilter, AgExecutionLogIndex
import openjiuwen_studio.core.manager.execution_log as exe_mgr


def _normalize_language(language: Optional[str]) -> str:
    if not language:
        return "zh"
    language = language.strip().lower()
    if language in {"cn", "zh", "zh-cn", "zh-hans", "zh-hans-cn"} or language.startswith("zh"):
        return "zh"
    return "en"


def _resolve_language(current_user: Optional[dict]) -> str:
    """
    解析当前语言。
    策略：倾向于英文 (Sticky English)。
    1. 如果 HTTP Header 指定了英文，返回英文。
    2. 如果用户配置 (Profile) 指定了英文，返回英文。
    3. 否则返回中文。
    
    这样可以解决：
    - 用户切换到英文，立即生效 (Header 优先)。
    - 用户配置了英文，但在默认中文的浏览器中访问，依然显示英文 (Profile 覆盖浏览器默认中文)。
    """
    # 1. 检查 Header
    language = get_language()
    header_lang = None
    if language and language.strip().lower() not in {"cn"}:
        header_lang = _normalize_language(language)
        if header_lang == "en":
            return "en"

    # 2. 检查用户配置
    if current_user:
        locale = (current_user.get("data") or {}).get("locale")
        if locale:
            user_lang = _normalize_language(locale)
            if user_lang == "en":
                return "en"

    # 3. 如果 Header 是中文 (或默认)，且用户配置不是英文 (或无配置)，则返回中文
    # (如果 Header 明确是中文，也会走到这里返回中文，除非用户配置是英文)
    return "zh"


# 常见字段名翻译映射
FIELD_TRANSLATIONS = {
    "model": {"zh": "模型配置", "en": "Model Configuration"},
    "name": {"zh": "名称", "en": "Name"},
    "description": {"zh": "描述", "en": "Description"},
    "agent_id": {"zh": "智能体ID", "en": "Agent ID"},
    "space_id": {"zh": "工作空间ID", "en": "Space ID"},
    "type": {"zh": "类型", "en": "Type"},
    "version": {"zh": "版本", "en": "Version"},
    "input_variables": {"zh": "输入变量", "en": "Input Variables"},
    "knowledge": {"zh": "知识库", "en": "Knowledge Base"},
    "prompt": {"zh": "提示词", "en": "Prompt"},
    "tools": {"zh": "工具", "en": "Tools"},
}


def _translate_field_name(field: str, language: str) -> str:
    """翻译字段名"""
    # 如果字段名在映射表中，返回对应语言的翻译
    if field in FIELD_TRANSLATIONS:
        translations = FIELD_TRANSLATIONS[field]
        return translations.get(language, field)
    
    # 尝试处理嵌套字段，例如 "model.name" -> "模型配置.名称"
    if '.' in field:
        parts = field.split('.')
        translated_parts = []
        for part in parts:
            if part in FIELD_TRANSLATIONS:
                translated_parts.append(FIELD_TRANSLATIONS[part].get(language, part))
            else:
                translated_parts.append(part)
        return '.'.join(translated_parts)
        
    return field


def _translate_validation_message(err: dict, operation: str, language: str) -> str:
    ctx = err.get("ctx") or {}
    if (operation == "AGENT_SAVE"
            and ctx.get("class_name") == "AgentModel"
            and err.get("msg") == "Input should be a valid dictionary or instance of AgentModel"):
        if language == "zh":
            return "智能体模型配置为空，请先配置模型"
        return "Agent model configuration is empty, please configure the model for the agent"

    err_type = err.get("type")
    err_msg = err.get("msg") or "Validation error"

    if err_type == "missing" or err_msg == "Field required":
        return "必填字段" if language == "zh" else "Field required"

    return err_msg


def handle_validation_error(
        e: ValidationError,
        operation: str,
        current_user: Optional[dict] = None,
        user_id: str = "unknown"
) -> HTTPException:
    """处理ValidationError，生成友好的错误信息"""
    language = _resolve_language(current_user)
    logger.error(f"[{operation}] Validation failed - User: {user_id}, Errors: {e.errors()}")
    # 构造友好的错误信息
    error_details = []
    for err in e.errors():
        # 提取字段路径和错误信息
        raw_field = '.'.join(map(str, err['loc'])) if isinstance(err['loc'], tuple) else str(err['loc'])
        # 翻译字段名
        field = _translate_field_name(raw_field, language)
        
        msg = _translate_validation_message(err, operation, language)
        error_details.append(f"{field}: {msg}")

    # 拼接最终的错误信息
    error_msg = ", ".join(error_details)
    prefix = "参数校验失败" if language == "zh" else "Validation failed"
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"{prefix}: {error_msg}"
    )


agents_router = APIRouter()


@agents_router.post("/create", response_model=ResponseModel[dict])
async def agent_create(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    创建新的智能体实例。

    Args:
        request (dict): 包含创建需求的请求体数据，需符合AgentCreate模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了创建成功的智能体详情及元数据。
        如果创建失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentCreate)
        res = mgr.agent_react_create(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[AGENT_CREATE] Agent created - ID: {res.data.get('id')}, User: {current_user.get('user_id', 'unknown')}")
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_CREATE", current_user=current_user, user_id=user_id) from e


@agents_router.post("/delete", response_model=ResponseModel[dict])
async def agent_delete(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    删除指定id智能体的draft+publish所有版本数据。

    Args:
        request (dict): 包含创建需求的请求体数据，需符合AgentGet模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了删除成功的智能体详情及元数据。
        如果删除失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentGet)
        res = mgr.agent_delete(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[AGENT_DELETE] Agent deleted - ID: {req.agent_id}, User: {current_user.get('user_id', 'unknown')}")
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_DELETE", current_user=current_user, user_id=user_id) from e


@agents_router.post("/delete_publish", response_model=ResponseModel[dict])
async def agent_publish_delete(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    删除指定id及publish版本的智能体。

    Args:
        request (dict): 包含删除需求的请求体数据，需符合AgentId模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了删除成功的智能体详情及元数据。
        如果删除失败，则包含相应的错误码与提示信息。
    """
    try:
        logger.info(f"agent publish delete start")
        req = validate_request(request, AgentId)
        logger.debug(f"received request {req}")
        res = mgr.agent_publish_delete(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_PUBLISH_DELETE", current_user=current_user, user_id=user_id) from e


@agents_router.post("/get_agent_info", response_model=ResponseModel[dict])
async def agent_get_info(
        request: dict,
        current_user: dict = Depends(get_current_user),
        manager: ModelConfigManager = Depends(get_model_config_manager)
):
    """
    获取智能体信息。

    Args:
        request (dict): 包含创建需求的请求体数据，需符合AgentGet模型定义。
        current_user (dict): 执行此操作的用户上下文信息。
        manager (ModelConfigManager): 模型配置管理实例。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了获取成功的智能体详情及元数据。
        如果获取失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentGetVersion)
        res = mgr.get_single_agent_info(req, current_user, manager)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_GET_INFO", current_user=current_user, user_id=user_id) from e


@agents_router.post("/save", response_model=ResponseModel[dict])
async def agent_save(
        request: dict,
        current_user: dict = Depends(get_current_user),
        manager: ModelConfigManager = Depends(get_model_config_manager)
):
    """
    保存智能体信息。

    Args:
        request (dict): 包含保存agent的请求体数据，需符合AgentDisplayInfo模型定义。
        current_user (dict): 执行此操作的用户上下文信息。
        manager (ModelConfigManager): 模型配置管理实例。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了保存成功的智能体详情及元数据。
        如果保存智能体失败，则包含相应的错误码与提示信息。
    """
    data = current_user.get('data', {})
    user_id = data.get('user_id_str', 'unknown')

    # 打印完整的请求数据，用于调试
    logger.info(f"[AGENT_SAVE] Raw request data: {mask_sensitive_fields(request)}")

    try:
        req = validate_request(request, AgentDisplayInfo)
        logger.info(f"[AGENT_SAVE] Validated request - ID: {req.agent_id}, User: {user_id}")
        logger.info(f"[AGENT_SAVE] Validated request data: {mask_sensitive_fields(req).model_dump()}")

        # 验证知识库的 embedding 模型一致性（如果有多个知识库）
        if req.knowledge and len(req.knowledge) > 1:
            from openjiuwen_studio.core.database import SessionLocal
            from openjiuwen_studio.core.manager.knowledge_base import _CURR_INDEX_TYPE
            from openjiuwen_studio.core.manager.repositories.knowledge_base_repository import knowledge_base_repository
            from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository
            from openjiuwen_studio.schemas.knowledge_base import KnowledgeBaseGet

            db = SessionLocal()
            try:
                embed_repo = EmbeddingModelConfigRepository(db)
                model_ids = []

                for kb_id in req.knowledge:
                    kb_result = knowledge_base_repository.knowledge_base_get(
                        KnowledgeBaseGet(
                            space_id=req.space_id,
                            kb_id=kb_id,
                            index_manager_type=_CURR_INDEX_TYPE,
                        )
                    )
                    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
                        continue

                    embed_config_id = kb_result.data.get('embedding_model_config_id')
                    if not embed_config_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"知识库 '{kb_result.data.get('name', kb_id)}' 未配置 embedding 模型"
                        )

                    embed_config = embed_repo.get_by_id(embed_config_id)
                    if not embed_config:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Embedding 模型配置不存在: {embed_config_id}"
                        )

                    model_ids.append(embed_config.model_id)

                # 验证所有 model_id 是否相同
                if len(set(model_ids)) > 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="所选知识库使用了不同的 embedding 模型（model_id），无法同时检索。请确保所有知识库使用相同的 embedding 模型。"
                    )
            finally:
                db.close()

        res = mgr.agent_save(req, current_user, manager)
        if res.code == status.HTTP_200_OK:
            logger.info(f"[AGENT_SAVE] Agent saved - ID: {req.agent_id}, User: {user_id}")
        return handle_response(res)
    except ValidationError as e:
        raise handle_validation_error(e, "AGENT_SAVE", current_user=current_user, user_id=user_id) from e


@agents_router.post("/update", response_model=ResponseModel[dict])
async def agent_update(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    更新智能体实例meta信息。

    Args:
        request (dict): 包含更新agent的请求体数据，需符合AgentUpdate模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了更新成功的agent详情及元数据。
        如果更新失败，则包含相应的错误码与提示信息。
    """
    data = current_user.get('data', {})
    user_id = data.get('user_id_str', 'unknown')
    try:
        req = validate_request(request, AgentUpdate)
        res = mgr.agent_meta_update(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(f"[AGENT_UPDATE] Agent updated - ID: {req.agent_id}, User: {user_id}")
        return handle_response(res)
    except ValidationError as e:
        raise handle_validation_error(e, "AGENT_UPDATE", current_user=current_user, user_id=user_id) from e


@agents_router.post("/list", response_model=ResponseModel[dict])
async def agent_list(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    获取智能体列表信息。

    Args:
        request (dict): 包含列表查询条件的请求体数据，需符合AgentList模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了获取成功的智能体列表详情及元数据。
        如果获取智能体列表失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentList)
        res = mgr.agent_get_list(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_LIST", current_user=current_user, user_id=user_id) from e


@agents_router.post("/publish", response_model=ResponseModel[dict])
async def agent_publish(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    发布智能体。

    Args:
        request (dict): 包含发布需求的请求体数据，需符合AgentPublish模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了发布成功的智能体详情及元数据。
        如果发布失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentPublish)
        res = mgr.agent_publish(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[AGENT_PUBLISH] Agent published - ID: {req.agent_id}, Version: {req.agent_version}, User: {current_user.get('user_id', 'unknown')}")
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_PUBLISH", current_user=current_user, user_id=user_id) from e


@agents_router.post("/version_list", response_model=ResponseModel[AgentVersionListResponse])
async def agent_version_list(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    查询智能体的发布版本列表

    Args:
        request (dict): 包含智能体ID和工作空间ID的请求体数据，需符合AgentVersionListRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[AgentVersionListResponse]: 标准化响应对象，其中封装了智能体版本列表。
        如果查询失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentVersionListRequest)
        res = mgr.agent_version_list(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_VERSION_LIST", current_user=current_user, user_id=user_id) from e


@agents_router.get("/{agent_id}", response_model=ResponseModel[dict])
async def agent_get(
        agent_id: str,
        space_id: str,
        version: Optional[str] = None,
        current_user: dict = Depends(get_current_user)
):
    """
    获取转换后agent，供executor调用

    Args:
        agent_id (str): 智能体id。
        space_id (str): 工作空间id。
        version (str): 智能体版本信息。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了转换成功的agent dsl信息详情。
        如果获取失败，则包含相应的错误码与提示信息。
    """
    try:
        req = {"agent_id": agent_id, "space_id": space_id, "agent_version": version}
        res = mgr.agent_convert(AgentGetVersion(**req), current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_GET", current_user=current_user, user_id=user_id) from e


@agents_router.post("/copy", response_model=ResponseModel[dict])
async def agent_copy(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    复制智能体实例。

    Args:
        request (dict): 包含复制需求的请求体数据，需符合AgentCopy模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了创建成功的智能体详情及元数据。
        如果创建失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentCopy)
        res = mgr.agent_react_copy(req, current_user)
        if res.code == status.HTTP_200_OK:
            logger.info(
                f"[AGENT_COPY] Agent copied - SourceID: {req.agent_id}, NewID: {res.data.get('id')}, User: {current_user.get('user_id', 'unknown')}")
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_COPY", current_user=current_user, user_id=user_id) from e


@agents_router.post("/search", response_model=ResponseModel[dict])
async def agent_search(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    搜索智能体

    Args:
        request (dict): 包含搜索需求的请求体数据，需符合AgentSearchRequest模型定义。
        current_user (dict): 执行此操作的用户上下文信息。

    Returns:
        ResponseModel[dict]: 标准化响应对象，其中封装了搜索成功的智能体列表及元数据。
        如果搜索失败，则包含相应的错误码与提示信息。
    """
    try:
        req = validate_request(request, AgentSearchRequest)
        res = mgr.agent_search(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_SEARCH", current_user=current_user, user_id=user_id) from e


@agents_router.post("/get_execution_logs_create_list", response_model=ResponseModel[ExecutionLogsCreateList])
async def get_agent_execution_logs_create_list(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    获取agent的所有执行日志的创建信息list

    Args:
        request: agent信息及过滤条件, AgExecutionLogsFilter类型
    Returns:
        ResponseModel[ExecutionLogsCreateList]: 创建信息list
    """
    try:
        req = validate_request(request, AgExecutionLogsFilter)
        res = exe_mgr.get_agent_execution_logs_create_list(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_EXECUTION_LOGS_LIST", current_user=current_user, user_id=user_id) from e


@agents_router.post("/get_execution_log", response_model=ResponseModel[ApiExecutionLogGet])
async def get_agent_execution_log(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    获取agent的某次执行日志

    Args:
        request: agent及某次执行的id信息, AgExecutionLogIndex类型
    Returns:
        ResponseModel[ApiExecutionLogGet]: 创建信息list
    """
    try:
        req = validate_request(request, AgExecutionLogIndex)
        res = exe_mgr.get_agent_execution_log(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_EXECUTION_LOG_GET", current_user=current_user, user_id=user_id) from e


@agents_router.post("/enter_execution_logs_debug", response_model=ResponseModel[ApiExecutionLogsDebugEnter])
async def enter_agent_execution_logs_debug(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    点击调试按钮，获取agent的所有运行log的create list及最新运行日志

    Args:
        request: agent的id信息, AgentId类型
    Returns:
        ResponseModel[ApiExecutionLogsDebugEnter]: 所有运行log的create list及最新运行日志
    """
    try:
        req = validate_request(request, AgentId)
        res = exe_mgr.enter_agent_execution_logs_debug(req, current_user)
        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_EXECUTION_DEBUG", current_user=current_user, user_id=user_id) from e


@agents_router.post("/export")
async def agent_export(
        request: dict,
        current_user: dict = Depends(get_current_user)
):
    """
    导出智能体及其依赖项。
    """
    try:
        req = validate_request(request, AgentExportRequest)
        res = mgr.agent_export(req, current_user)

        if isinstance(res, tuple) and len(res) == 2:
            zip_buffer, filename = res
            filename_encoded = quote(filename)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
                }
            )

        return handle_response(res)
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_EXPORT", current_user=current_user, user_id=user_id) from e


@agents_router.post("/import", response_model=ResponseModel[dict])
async def agent_import(
        raw_request: Request,
        file: Optional[UploadFile] = File(None),
        request: Optional[dict] = Body(None),
        space_id: str = Form(None),
        overwrite: bool = Form(False),
        current_user: dict = Depends(get_current_user)
):
    """
    导入智能体及其依赖项。
    支持 JSON 请求体（旧方式）或文件上传（ZIP/JSON）。
    对于文件上传，必须提供 space_id 参数。
    """
    try:
        # 尝试手动解析 JSON Body，解决 Body 与 File 混用导致 JSON 请求无法解析的问题
        if not file and not request:
            content_type = raw_request.headers.get("content-type", "")
            if content_type and "application/json" in content_type:
                try:
                    request = await raw_request.json()
                    logger.info("[AGENT_IMPORT] Manually parsed JSON body from request")
                except Exception as e:
                    logger.warning(f"[AGENT_IMPORT] Failed to parse JSON body: {e}")

        # 1. 如果是文件上传（优先处理）
        if file:
            if not space_id:
                # 尝试从用户数据获取默认空间，但这通常不安全，最好强制前端传参
                data = current_user.get('data', {})
                space_id = data.get('space_id') or "default"
            
            # 读取文件内容
            file_content = await file.read()
            
            # 构建请求对象
            # 注意：agent_import_from_file 是异步的
            res = await mgr.agent_import_from_file(
                file_content=file_content, 
                space_id=space_id, 
                overwrite=overwrite, 
                current_user=current_user
            )
            return handle_response(res)
            
        # 2. 如果是 JSON 请求体（兼容旧方式）
        elif request:
            req = validate_request(request, AgentImportRequest)
            res = await mgr.agent_import(req, current_user)
            return handle_response(res)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No import data provided"
            )
            
    except ValidationError as e:
        user_id = (current_user.get("data") or {}).get("user_id_str", "unknown")
        raise handle_validation_error(e, "AGENT_IMPORT", current_user=current_user, user_id=user_id) from e
    except Exception as e:
        logger.error(f"[AGENT_IMPORT] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        ) from e
