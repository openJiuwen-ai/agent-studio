#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.routers.common import handle_response, validate_request
import openjiuwen_studio.core.manager.runtime as rtm
from openjiuwen_studio.schemas.runtime import ResponseModel, DeployRequest

runtime_router = APIRouter()


async def _background_deploy_and_save(
    agent_id: str,
    agent_version: str,
    payload: dict,
    space_id: str,
    user_id: str,
):
    """后台执行完整的部署流程（包括 runtime 调用和数据库保存）"""
    try:
        deploy_result_str = await rtm.deploy_to_runtime(payload, user_id, space_id)
        logger.info(f"Agent deployed successfully: agent_id={agent_id}")
        await rtm.update_deploy_info(deploy_result_str, agent_version, agent_id, space_id)
        logger.info(f"Deployment completed in background: agent_id={agent_id}")
    except Exception as e:
        logger.error(f"Background deployment failed: agent_id={agent_id}, error={e}")


@runtime_router.post("/deploy", response_model=ResponseModel[dict])
async def deploy(
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    try:
        agent_id = request.agent_id
        agent_name = request.agent_name
        agent_version = request.agent_version
        deployer_type = request.deployer_type
        port = request.port
        space_id = request.space_id

        _ = check_user_space(space_id, current_user)
        # 接前端入参，导出agent ir
        agent_ir = await rtm.get_agent_ir(agent_id, agent_version, space_id, current_user)

        # 调用runtime接口，把ir传给runtime,接收从runtime返回的status和id
        data = current_user.get("data", {})
        user_id = data.get("user_id_str", "")
        payload = {"file": agent_ir, "name": agent_name, "deployer_type": deployer_type, "port": port}
        # 将整个部署流程放到后台执行
        background_tasks.add_task(
            _background_deploy_and_save,
            agent_id,
            agent_version,
            payload,
            space_id,
            user_id
        )
        await rtm.save_part_deploy_info(agent_version, agent_id, space_id)
        res = ResponseModel(
            code=status.HTTP_200_OK,
            message="Deployment successful",
            data={
                "status": "pending",
                "message": "Deployment initiated in background",
                "agent_id": agent_id,
                "agent_name": agent_name,
                "note": "Poll /api/v1/agents/list to check status"
            },
        )
        return handle_response(res)
    except Exception as e:
        logger.error(f"Failed to deploy agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to deploy agent"
        ) from e


@runtime_router.delete("/remove", response_model=ResponseModel[dict])
async def remove(
        agent_id: str,
        space_id: str,
        current_user: dict = Depends(get_current_user),
):
    try:
        _ = check_user_space(space_id, current_user)
        # 接前端入参，取出deployment_id
        deploy_infos = await rtm.get_deploy_info(agent_id, space_id)

        # 调用runtime接口执行删除
        for deploy_info in deploy_infos:
            data = current_user.get("data", {})
            user_id = data.get("user_id_str", "")
            _ = await rtm.delete_deploy_agent(deploy_info.get("deployment_id", ""), user_id, space_id)

            # 更新到deployment表里
            _ = await rtm.unregister_deploy_info(deploy_info.get("deployment_id", ""), space_id)

        res = ResponseModel(
            code=status.HTTP_200_OK,
            message="Delete deployment successful"
        )
        return handle_response(res)
    except Exception as e:
        logger.error(f"Failed to delete deploy agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete deploy agent"
        ) from e


@runtime_router.post("/list", response_model=ResponseModel[dict])
async def get_deploy_list(
        deploy_status: Optional[str] = None,
        space_id: Optional[str] = None,
        current_user: dict = Depends(get_current_user),
):
    try:
        _ = check_user_space(space_id, current_user)

        data = current_user.get("data", {})
        user_id = data.get("user_id_str", "")
        deploy_list = await rtm.get_deploy_list(deploy_status, user_id, space_id)

        res = ResponseModel(
            code=status.HTTP_200_OK,
            message="Get deployment list successful",
            data=deploy_list
        )
        return handle_response(res)
    except Exception as e:
        logger.error(f"Failed to get deploy list: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get deploy list"
        ) from e


@runtime_router.post("/detail", response_model=ResponseModel[dict])
async def get_deploy_detail(
        agent_id: str,
        deploy_status: Optional[str] = None,
        space_id: Optional[str] = None,
        current_user: dict = Depends(get_current_user),
):
    try:
        _ = check_user_space(space_id, current_user)

        data = current_user.get("data", {})
        user_id = data.get("user_id_str", "")
        deploy_detail = await rtm.get_deploy_details(agent_id, deploy_status, user_id, space_id)

        res = ResponseModel(
            code=status.HTTP_200_OK,
            message="Get deployment detail successful",
            data=deploy_detail
        )
        return handle_response(res)
    except Exception as e:
        logger.error(f"Failed to get deploy detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get deploy detail"
        ) from e


@runtime_router.post("/query")
async def proxy_deployed_agent_query(
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    将发布页聊天请求转发到已部署 Runtime 的 /query（SSE），避免浏览器直连 Runtime 触发 CORS。
    请求体须包含 target_url、space_id，以及 Runtime 所需的 messages、conversation_id、user_id、stream 等字段。
    """
    try:
        body = await http_request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from e
    target_url = body.get("target_url")
    space_id = body.get("space_id")
    if not target_url or not space_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_url and space_id are required",
        )
    _ = check_user_space(space_id, current_user)

    async def byte_stream():
        async for chunk in rtm.stream_deployed_agent_query(str(target_url), space_id, body):
            yield chunk

    return StreamingResponse(
        byte_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@runtime_router.post("/reset_conversation", response_model=ResponseModel[dict])
async def proxy_deployed_agent_reset_conversation(
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    将发布页新对话请求转发到已部署 Runtime 的 /reset_conversation，避免浏览器直连 Runtime 触发 CORS。
    请求体须包含 target_url、space_id、conversation_id。
    """
    try:
        body = await http_request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        ) from e

    target_url = body.get("target_url")
    space_id = body.get("space_id")
    conversation_id = body.get("conversation_id")
    if not target_url or not space_id or not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_url, space_id and conversation_id are required",
        )

    _ = check_user_space(space_id, current_user)
    result = await rtm.reset_deployed_agent_conversation(str(target_url), space_id, body)
    res = ResponseModel(
        code=status.HTTP_200_OK,
        message="Reset conversation successful",
        data=result,
    )
    return handle_response(res)

