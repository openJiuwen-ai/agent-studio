# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
Web Run API — 网页执行接口

提供通过 short_code 调用已发布工作流/智能体的执行端点。
与试运行接口（app_run.py）的差异在于路径参数使用 short_code，
需先从 Redis 查询 ReleaseInfo 获取 appId/versionId/projectId，
再复用试运行的 _execute_workflow_run / _execute_agent_run 完整执行链。
"""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.serve.apis.app_run import (
    _execute_workflow_run,
    _execute_agent_run,
    WorkflowAppRunRequest,
    WorkflowRunContext,
    AgentAppRunRequest,
    AgentRunContext,
)
from agent_runtime.serve.apis.app_release import AppRelease

web_run_app = APIRouter(tags=["web_run"])

_release_service = AppRelease()


@web_run_app.post(
    "/v1/workflows/chat/{short_code}/conversations/{conversation_id}"
)
async def run_web_workflow(
    body: WorkflowAppRunRequest,
    request: Request,
):
    """网页工作流执行接口 — 通过 short_code 查询发布信息后复用试运行执行链。

    1. 从 Redis 查询 release_web_rel_{short_code} 获取 ReleaseInfo
    2. 用 ReleaseInfo 的 appId/versionId/projectId 构造 WorkflowRunContext
    3. 复用 _execute_workflow_run（IR 路径→校验→会话→ir_execute→EventHandler 封装）

    """
    path_params = request.path_params
    short_code = path_params["short_code"]
    conversation_id = path_params["conversation_id"]
    language = request.headers.get("x-language", "zh-cn")

    workflow_logger.info(
        "Web workflow run request: short_code=%s, conversation=%s",
        short_code,
        conversation_id,
    )

    # 1. 查询 ReleaseInfo（含 workflow_id=app_id, version=version_id, project_id）
    release_info = await _release_service.get_release_info(short_code, language)
    if isinstance(release_info, JSONResponse):
        return release_info

    # 2. 构造 WorkflowRunContext（复用 app_run.py 的 context dataclass）
    ctx = WorkflowRunContext(
        project_id=release_info.project_id,
        workflow_id=release_info.app_id,
        conversation_id=conversation_id,
        version=str(release_info.version_id) if release_info.version_id else None,
    )

    # 3. 复用试运行核心执行逻辑
    return await _execute_workflow_run(ctx, body, request)


@web_run_app.post("/v1/agents/chat/{short_code}")
async def run_web_agent(
    body: AgentAppRunRequest,
    request: Request,
    workspace_id: str = "",
    conversation_id: str = "",
):
    """网页智能体执行接口 — 通过 short_code 查询发布信息后复用试运行执行链。

    1. 从 Redis 查询 release_web_rel_{short_code} 获取 ReleaseInfo
    2. conversation_id 为空时生成 UUID
    3. 用 ReleaseInfo 的 appId/versionId/projectId 构造 AgentRunContext
    4. 复用 _execute_agent_run（IR 路径→校验→会话→ir_execute→EventHandler 封装）
       handler_type 由 IR 的 mode 决定（ReAct/Controller/PlanExecute）
    """
    short_code = request.path_params["short_code"]
    language = request.headers.get("x-language", "zh-cn")

    # conversation_id 为空时生成 UUID
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    workflow_logger.info(
        "Web agent run request: short_code=%s, conversation=%s, workspace=%s",
        short_code,
        conversation_id,
        workspace_id,
    )

    # 1. 查询 ReleaseInfo（含 agent_id=app_id, version=version_id, project_id）
    release_info = await _release_service.get_release_info(short_code, language)
    if isinstance(release_info, JSONResponse):
        return release_info

    # 2. 构造 AgentRunContext（复用 app_run.py 的 context dataclass）
    ctx = AgentRunContext(
        project_id=release_info.project_id,
        agent_id=release_info.app_id,
        conversation_id=conversation_id,
        version=str(release_info.version_id) if release_info.version_id else None,
    )

    # 3. 复用试运行核心执行逻辑（handler_type 由 IR mode 决定）
    return await _execute_agent_run(ctx, body, request)
