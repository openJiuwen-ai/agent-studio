# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
Release API — 应用发布信息管理接口（仅网页发布渠道）

提供发布信息的创建和删除端点，将 ReleaseInfo 写入/删除 Redis。

Redis key 格式：release_web_rel_{short_code}
"""

import time
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.serve.apis.app_release import ReleaseInfo, _RELEASE_WEB_REL_KEY

release_api_router = APIRouter(tags=["release"])


@release_api_router.post("/v1/{project_id}/releases")
async def create_release_info(
    project_id: str,
    body: ReleaseInfo,
    request: Request,
    workspace_id: Optional[str] = None,
):
    """创建应用发布信息 — 将 ReleaseInfo 写入 Redis。

    1. 根据 short_code 构建 Redis key
    2. 补充 projectId / workspaceId / domainId / alreadyBeenCalled / updateTime
    3. 写入 Redis
    """
    workflow_logger.info(
        "Create release info: project_id=%s, short_code=%s, app_id=%s, version_id=%s",
        project_id,
        body.short_code,
        body.app_id,
        body.version_id,
    )

    if not body.short_code:
        workflow_logger.error("Missing short_code in release info")
        return JSONResponse(
            status_code=400,
            content={"error": "Missing short_code in release info"},
        )

    # 1. 构建 Redis key
    release_key = _RELEASE_WEB_REL_KEY % body.short_code

    # 2. 补充字段
    body.project_id = project_id
    body.workspace_id = workspace_id or ""
    # domainId: 从 X-Auth-Token 解析的 project_id 作为 domainId
    from agent_runtime.context.request_context import _request_ctx

    ctx = _request_ctx.get()
    body.domain_id = ctx.project_id or ""
    body.already_been_called = 0
    body.update_time = int(time.time() * 1000)

    # 3. 写入 Redis
    try:
        from agent_runtime.common.redis_manager import get_redis_client

        redis_client = get_redis_client()
        release_data = body.model_dump_json(by_alias=True, exclude_none=True)
        await redis_client.set(release_key, release_data)
        workflow_logger.info("Release info created: key=%s", release_key)
    except Exception as e:
        workflow_logger.error("Failed to write release info to Redis: key=%s, error=%s", release_key, e)
        return JSONResponse(status_code=500, content={"error": f"Failed to write release info: {e}"})

    return JSONResponse(status_code=200, content={"message": "Release info created successfully"})


@release_api_router.delete("/v1/{project_id}/releases/{release_id}")
async def delete_release_info(
    project_id: str,
    release_id: str,
):
    """删除应用发布信息 — 从 Redis 删除 ReleaseInfo。

    1. 根据 short_code 构建 Redis key
    2. 从 Redis 删除
    """
    workflow_logger.info(
        "Delete release info: project_id=%s, release_id(short_code)=%s",
        project_id,
        release_id,
    )

    # 1. 构建 Redis key
    release_key = _RELEASE_WEB_REL_KEY % release_id

    # 2. 从 Redis 删除
    try:
        from agent_runtime.common.redis_manager import get_redis_client

        redis_client = get_redis_client()
        await redis_client.delete(release_key)
        workflow_logger.info("Release info deleted: key=%s", release_key)
    except Exception as e:
        workflow_logger.error("Failed to delete release info from Redis: key=%s, error=%s", release_key, e)
        return JSONResponse(status_code=500, content={"error": f"Failed to delete release info: {e}"})

    return JSONResponse(status_code=200, content={"message": "Release info deleted successfully"})
