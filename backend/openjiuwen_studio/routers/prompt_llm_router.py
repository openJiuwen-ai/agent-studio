#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.ops.modules.llm.llm_config_service import LLMConfigService
from openjiuwen_studio.ops.config import ModelConfigManager
from openjiuwen_studio.ops.modules.llm.llm_manager import init_llm_manager
from openjiuwen_studio.ops.modules.llm.schema import ListModelRequest, GetModelRequest
from openjiuwen_studio.ops.modules.prompt.infra.database import get_db_agent
from openjiuwen_studio.ops.modules.prompt.infra.repositories.agent_repo import SQLAgentRepository

router = APIRouter(
    prefix="/api/v1/llm",
    tags=["model"],
)

router_initialized = False          # 模块级标记，确保只 init 一次


def get_llm_config_service(agent_db: Session = Depends(get_db_agent)) -> LLMConfigService:
    """
    依赖注入：创建 LLMConfigService 实例
    """
    global router_initialized

    model_config_manager = ModelConfigManager()
    agent_repo = SQLAgentRepository(agent_db)
    svc = LLMConfigService(model_config_manager, agent_repo)

    # 只有第一次进来时才注入
    if not router_initialized:
        init_llm_manager(svc)
        router_initialized = True

    return svc


@router.post("/model/{model_id}")
async def get_model(
    model_id: str,
    request: GetModelRequest,
    llm_service: LLMConfigService = Depends(get_llm_config_service),
    current_user: dict = Depends(get_current_user)
):
    """
    获取单个模型信息
    """
    _ = check_user_space(str(request.workspace_id), current_user)
    try:
        return await llm_service.get_model(model_id, request.model_from)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/models/list")
async def list_models(
    request: ListModelRequest,
    llm_service: LLMConfigService = Depends(get_llm_config_service),
    current_user: dict = Depends(get_current_user)
):
    """
    获取所有可用模型列表
    """
    _ = check_user_space(str(request.workspace_id), current_user)
    try:
        return await llm_service.list_models(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
