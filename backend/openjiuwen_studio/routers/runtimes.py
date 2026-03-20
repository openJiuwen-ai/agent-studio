#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.routers.common import handle_response, validate_request
import openjiuwen_studio.core.manager.runtime as rtm
from openjiuwen_studio.schemas.runtime import ResponseModel, DeployRequest

runtime_router = APIRouter()


@runtime_router.post("/deploy", response_model=ResponseModel[dict])
async def deploy(
    request: DeployRequest,
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
        deploy_result_str = await rtm.deploy_to_runtime(payload, user_id, space_id)
        logger.info(f"Agent deployed successfully: agent_id={agent_id}")

        # 解析 deploy_result 字符串为字典
        deploy_result = json.loads(deploy_result_str)

        # 更新deployment表里
        _ = await rtm.save_deploy_info(deploy_result_str, agent_version, agent_id, space_id)

        res = ResponseModel(
            code=status.HTTP_200_OK,
            message="Deployment successful",
            data=deploy_result,
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
            message="Deployment successful"
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
            message="Deployment successful",
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
            message="Deployment successful",
            data=deploy_detail
        )
        return handle_response(res)
    except Exception as e:
        logger.error(f"Failed to get deploy detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get deploy detail"
        ) from e

