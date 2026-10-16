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
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Depends, Header, Path, Query, Request
from fastapi.responses import JSONResponse
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.serve.apis.app_run import (
    _execute_workflow_run,
    _execute_agent_run,
    WorkflowAppRunRequest,
    WorkflowRunContext,
    AgentAppRunRequest,
    AgentRunContext,
    _STREAMING_RESPONSES_200,
)
from agent_runtime.serve.apis.app_release import AppRelease

web_run_app = APIRouter(tags=["web_run"])

_release_service = AppRelease()


@dataclass
class WorkflowWebRunPathParams:
    """网页工作流执行接口 path 参数封装."""

    short_code: str
    conversation_id: str

    @classmethod
    async def as_dependency(
        cls,
        short_code: str = Path(..., description="发布短码"),
        conversation_id: str = Path(..., description="会话ID"),
    ) -> "WorkflowWebRunPathParams":
        return cls(short_code=short_code, conversation_id=conversation_id)


@dataclass
class WorkflowWebRunQueryParams:
    """网页工作流执行接口 query 参数封装."""

    workspace_id: str = ""
    environment_id: Optional[str] = None

    @classmethod
    async def as_dependency(
        cls,
        workspace_id: str = Query(default="", description="工作空间ID"),
        environment_id: Optional[str] = Query(default=None, description="环境ID（manager 回填）"),
    ) -> "WorkflowWebRunQueryParams":
        return cls(
            workspace_id=workspace_id,
            environment_id=environment_id,
        )


@dataclass
class WorkflowWebRunParams:
    """网页工作流执行接口路由参数（path + query + header）封装."""

    short_code: str
    conversation_id: str
    workspace_id: str = ""
    environment_id: Optional[str] = None
    language: str = "zh-cn"
    stream: str = "true"

    @classmethod
    async def as_dependency(
        cls,
        path: WorkflowWebRunPathParams = Depends(WorkflowWebRunPathParams.as_dependency),
        query: WorkflowWebRunQueryParams = Depends(WorkflowWebRunQueryParams.as_dependency),
        language: str = Header(default="zh-cn", alias="x-language", description="语言"),
        stream: str = Header(default="true", description="是否流式响应"),
    ) -> "WorkflowWebRunParams":
        return cls(
            short_code=path.short_code,
            conversation_id=path.conversation_id,
            workspace_id=query.workspace_id,
            environment_id=query.environment_id,
            language=language,
            stream=stream,
        )


@dataclass
class AgentWebRunPathParams:
    """网页智能体执行接口 path 参数封装."""

    short_code: str

    @classmethod
    async def as_dependency(
        cls,
        short_code: str = Path(..., description="发布短码"),
    ) -> "AgentWebRunPathParams":
        return cls(short_code=short_code)


@dataclass
class AgentWebRunQueryParams:
    """网页智能体执行接口 query 参数封装."""

    workspace_id: str = ""
    conversation_id: str = ""
    environment_id: Optional[str] = None

    @classmethod
    async def as_dependency(
        cls,
        workspace_id: str = Query(default="", description="工作空间ID"),
        conversation_id: str = Query(default="", description="会话ID"),
        environment_id: Optional[str] = Query(default=None, description="环境ID（manager 回填）"),
    ) -> "AgentWebRunQueryParams":
        return cls(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            environment_id=environment_id,
        )


@dataclass
class AgentWebRunParams:
    """网页智能体执行接口路由参数（path + query + header）封装."""

    short_code: str
    workspace_id: str = ""
    conversation_id: str = ""
    environment_id: Optional[str] = None
    language: str = "zh-cn"
    stream: str = "true"

    @classmethod
    async def as_dependency(
        cls,
        path: AgentWebRunPathParams = Depends(AgentWebRunPathParams.as_dependency),
        query: AgentWebRunQueryParams = Depends(AgentWebRunQueryParams.as_dependency),
        language: str = Header(default="zh-cn", alias="x-language", description="语言"),
        stream: str = Header(default="true", description="是否流式响应"),
    ) -> "AgentWebRunParams":
        return cls(
            short_code=path.short_code,
            workspace_id=query.workspace_id,
            conversation_id=query.conversation_id,
            environment_id=query.environment_id,
            language=language,
            stream=stream,
        )


@web_run_app.post(
    "/v1/workflows/chat/{short_code}/conversations/{conversation_id}",
    summary="网页工作流对话",
    description="通过 short_code 查询发布信息后复用工作流执行链。"
                "先从 Redis 查询 release_web_rel_{short_code} 获取 ReleaseInfo，"
                "再用其中的 appId/versionId/projectId 构造执行上下文。",
    responses=_STREAMING_RESPONSES_200,
)
async def run_web_workflow(
    body: WorkflowAppRunRequest,
    request: Request,
    params: WorkflowWebRunParams = Depends(WorkflowWebRunParams.as_dependency),
):
    """网页工作流执行接口 — 通过 short_code 查询发布信息后复用试运行执行链。

    1. 从 Redis 查询 release_web_rel_{short_code} 获取 ReleaseInfo
    2. 用 ReleaseInfo 的 appId/versionId/projectId 构造 WorkflowRunContext
    3. 复用 _execute_workflow_run（IR 路径→校验→会话→ir_execute→EventHandler 封装）

    environment_id 由 manager 侧回填（按 short_code 所属发布通道解析的项目默认
    环境），用于解析插件/MCP URL 与模型 apiUrl 中的 ${_env.plugin_url_params.VAR}
    占位符；回填默认环境时 manager 同步以发布通道 workspace 覆盖 workspace_id
    （入口无鉴权，请求 workspace 不可信，环境变量按 (environment_id, workspace_id)
    维度存储），保证加载发布方预期的变量值。
    """
    workflow_logger.info(
        "Web workflow run request: short_code=%s, conversation=%s, workspace=%s, environment=%s",
        params.short_code,
        params.conversation_id,
        params.workspace_id,
        params.environment_id,
    )

    # 1. 查询 ReleaseInfo（含 workflow_id=app_id, version=version_id, project_id）
    release_info = await _release_service.get_release_info(params.short_code, params.language)
    if isinstance(release_info, JSONResponse):
        return release_info

    # 2. 构造 WorkflowRunContext（复用 app_run.py 的 context dataclass）
    ctx = WorkflowRunContext(
        project_id=release_info.project_id,
        workflow_id=release_info.app_id,
        conversation_id=params.conversation_id,
        version=str(release_info.version_id) if release_info.version_id else None,
        environment_id=params.environment_id,
        workspace_id=params.workspace_id,
    )

    # 3. 复用试运行核心执行逻辑（resolve_env=False：environment_id 由 manager 决定，
    #    不在此按请求 workspace 回填默认环境，避免无鉴权入口跨空间变量外流）
    return await _execute_workflow_run(ctx, body, request, params.stream, resolve_env=False)


@web_run_app.post(
    "/v1/agents/chat/{short_code}",
    summary="网页智能体对话",
    description="通过 short_code 查询发布信息后复用智能体执行链。"
                "conversation_id 为空时自动生成 UUID。"
                "handler_type 由 IR 的 mode 决定（ReAct/Controller/PlanExecute）。",
    responses=_STREAMING_RESPONSES_200,
)
async def run_web_agent(
    body: AgentAppRunRequest,
    request: Request,
    params: AgentWebRunParams = Depends(AgentWebRunParams.as_dependency),
):
    """网页智能体执行接口 — 通过 short_code 查询发布信息后复用试运行执行链。

    1. 从 Redis 查询 release_web_rel_{short_code} 获取 ReleaseInfo
    2. conversation_id 为空时生成 UUID
    3. 用 ReleaseInfo 的 appId/versionId/projectId 构造 AgentRunContext
    4. 复用 _execute_agent_run（IR 路径→校验→会话→ir_execute→EventHandler 封装）
       handler_type 由 IR 的 mode 决定（ReAct/Controller/PlanExecute）

    environment_id 由 manager 侧回填（按 short_code 所属发布通道解析的项目默认
    环境），用于解析模型 apiUrl 中的 ${_env.plugin_url_params.VAR} 占位符；
    回填默认环境时 manager 同步以发布通道 workspace 覆盖 workspace_id（入口
    无鉴权，请求 workspace 不可信，环境变量按 (environment_id, workspace_id)
    维度存储），保证加载发布方预期的变量值。
    """
    conversation_id = params.conversation_id
    # conversation_id 为空时生成 UUID
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    workflow_logger.info(
        "Web agent run request: short_code=%s, conversation=%s, workspace=%s, environment=%s",
        params.short_code,
        conversation_id,
        params.workspace_id,
        params.environment_id,
    )

    # 1. 查询 ReleaseInfo（含 agent_id=app_id, version=version_id, project_id）
    release_info = await _release_service.get_release_info(params.short_code, params.language)
    if isinstance(release_info, JSONResponse):
        return release_info

    # 2. 构造 AgentRunContext（复用 app_run.py 的 context dataclass）
    ctx = AgentRunContext(
        project_id=release_info.project_id,
        agent_id=release_info.app_id,
        conversation_id=conversation_id,
        version=str(release_info.version_id) if release_info.version_id else None,
        environment_id=params.environment_id,
        workspace_id=params.workspace_id,
    )

    # 3. 复用试运行核心执行逻辑（resolve_env=False：environment_id 由 manager 决定，
    #    不在此按请求 workspace 回填默认环境，避免无鉴权入口跨空间变量外流）
    return await _execute_agent_run(ctx, body, request, params.stream, resolve_env=False)
