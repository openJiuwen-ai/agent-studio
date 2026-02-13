#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
from openjiuwen_studio.ops.common.handle_exceptions_util import handle_exceptions
from openjiuwen_studio.ops.modules.llm.llm_config_service import LLMConfigService
from openjiuwen_studio.ops.modules.prompt.application.debug_service import PromptDebugService
from openjiuwen_studio.ops.modules.prompt.domain.debug_entity import DebugStreamingRequest, \
    SaveDebugContextRequest, DebugContextResponse, ListDebugHistoryResponse

from openjiuwen_studio.ops.modules.prompt.infra.database import get_async_session_ops
from openjiuwen_studio.ops.modules.prompt.infra.repositories.debug_repo import SQLDebugContextRepository, SQLDebugLogRepository
from openjiuwen_studio.ops.modules.prompt.domain.entities import BaseResponse
from openjiuwen_studio.routers.prompt_llm_router import get_llm_config_service
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.login_manager.user import get_current_user

# 创建子路由
router = APIRouter(prefix="/api/v1/prompts", tags=["prompt-debug"])


def get_debug_service(session: AsyncSession = Depends(get_async_session_ops)) -> PromptDebugService:
    """ 依赖注入，获取调试服务实例"""
    return PromptDebugService(
        debug_ctx_repo=SQLDebugContextRepository(session),
        debug_log_repo=SQLDebugLogRepository(session),
    )


@router.post("/{prompt_id}/debug_streaming")
@handle_exceptions()
async def debug_streaming(
    body: DebugStreamingRequest = ...,
    service: PromptDebugService = Depends(get_debug_service),
    llm_config_service: LLMConfigService = Depends(get_llm_config_service),
    current_user: dict = Depends(get_current_user)
):
    """组装 Prompt → 调用大模型 → 逐条 SSE 返回 → 完成后保存 debug_context"""
    _ = check_user_space(str(body.workspace_id), current_user)
    prompt_detail = body.prompt.get("prompt_draft", {}).get("detail", {})
    model_cfg = prompt_detail.get("prompt_model_config", {})
    model_id = model_cfg.get("models_id")
    model_from = model_cfg.get("model_from")
    if not model_id:
        raise ValueError(f"debug_streaming input model_id not found")

    llm_config = llm_config_service.get_llm_model_info(model_id, model_from)

    if not llm_config:
        raise ValueError(f"debug_streaming llm_config not found from db")
    return StreamingResponse(
        service.stream_and_save(body, llm_config),
        media_type="text/event-stream",
    )


@router.post("/{prompt_id}/debug_context/save")
@handle_exceptions(response_model=BaseResponse)
async def save_debug_context(
    prompt_id: int = Path(...),
    body: SaveDebugContextRequest = ...,
    service: PromptDebugService = Depends(get_debug_service),
    current_user: dict = Depends(get_current_user)
):
    """ 保存调试上下文 """
    _ = check_user_space(str(body.workspace_id), current_user)
    body.prompt_id = prompt_id
    user_id = current_user.get("data")["user_id_str"]
    await service.save_debug_context(user_id=user_id, req=body)
    return BaseResponse()


@router.get("/{prompt_id}/debug_context/get")
@handle_exceptions(response_model=DebugContextResponse)
async def get_debug_context(
    prompt_id: int = Path(...),
    workspace_id: int = Query(...),
    service: PromptDebugService = Depends(get_debug_service),
    current_user: dict = Depends(get_current_user)
):
    """ 获取指定 prompt 的最新调试上下文 """
    _ = check_user_space(str(workspace_id), current_user)
    user_id = current_user.get("data")["user_id_str"]
    return DebugContextResponse(debug_context=await service.get_debug_context(prompt_id, user_id))


@router.get("/{prompt_id}/debug_history/list")
@handle_exceptions(response_model=ListDebugHistoryResponse)
async def list_debug_history(
    prompt_id: int = Path(...),
    workspace_id: str = Query("0"),
    days_limit: int = Query(None, ge=1, le=365),
    page_size: int = Query(20, ge=1, le=100),
    page_token: int = Query(0, ge=0),
    service: PromptDebugService = Depends(get_debug_service),
    current_user: dict = Depends(get_current_user)
):
    """ 分页查询调试历史记录 """
    _ = check_user_space(str(workspace_id), current_user)
    return await service.list_debug_history(
        prompt_id, workspace_id, days_limit, page_size, str(page_token)
    )
