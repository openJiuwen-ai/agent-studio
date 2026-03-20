#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import json
import datetime
from typing import Optional
from fastapi import HTTPException, status

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.agent import AgentGetVersion
from openjiuwen_studio.core.thirdparty_client import RuntimeAgentClient
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw, JiuwenBaseRepository
import openjiuwen_studio.core.manager.agent as mgr
from openjiuwen_studio.models.runtime_info import RuntimeInfoDB


# 依赖注入（或直接使用单例）
def get_agent_client():
    return RuntimeAgentClient()  # 或全局单例


async def get_agent_ir(
        agent_id: str,
        agent_version: str,
        space_id: str,
        current_user: dict
) -> str:
    """
    导出 Agent 的 IR(Intermediate Representation) 中间表示

    Args:
        agent_id: Agent ID
        agent_version: Agent 版本号
        space_id: 空间 ID
        current_user: 当前用户信息

    Returns:
        ResponseModel: 包含 agent_ir 数据的响应
    """
    # 构建请求参数
    req = {"agent_id": agent_id, "space_id": space_id, "agent_version": agent_version}
    res = mgr.agent_convert(AgentGetVersion(**req), current_user)
    return json.dumps(res.data)


async def deploy_to_runtime(
        payload: dict,
        user_id,
        space_id,
        client: RuntimeAgentClient = None,
) -> str:
    # 构造部署请求 payload
    deploy_payload = {
        "name": payload.get('name'),
        "file": payload.get('file'),
        "deployer_type": payload.get('deployer_type', ""),
        "port": payload.get('port', ""),
    }

    # 调用 runtime 接口进行部署
    if client is None:
        client = get_agent_client()
    deploy_result = await client.deploy_agent(deploy_payload, user_id, space_id)
    deployment_id = deploy_result.get("deployment_id", "")

    if not deployment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Runtime service did not return deployment_id"
        )
    return json.dumps(deploy_result)


async def save_deploy_info(
        deploy_result_str: str,
        agent_version: str,
        agent_id,
        space_id,
) -> str:
    deploy_result = json.loads(deploy_result_str)
    runtime_info_data = {
        "deployment_id": deploy_result.get("deployment_id", ""),
        "space_id": space_id,
        "source_id": agent_id,
        "version": agent_version,
        "type": deploy_result.get("type", ""),
        "name": deploy_result.get("name", ""),
        "status": deploy_result.get("status", ""),
        "url": deploy_result.get("url", ""),
        "port": deploy_result.get("port", ""),
        "is_delete": False,
    }
    # 存到新deployment表里
    with get_db_jw() as db:
        runtime_db = JiuwenBaseRepository(db, RuntimeInfoDB)

        # 构建查询条件（使用 deployment_id 作为唯一标识）
        find_id = {
            "deployment_id": runtime_info_data["deployment_id"],
        }

        # 设置默认时间
        now_beijing = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        if "create_at" not in runtime_info_data or runtime_info_data["create_at"] is None:
            runtime_info_data["create_at"] = now_beijing
        if "update_at" not in runtime_info_data or runtime_info_data["update_at"] is None:
            runtime_info_data["update_at"] = now_beijing

        # 注册到数据库
        save_result = runtime_db.register_dl_in_sql(
            find_id=find_id,
            dl=runtime_info_data
        )
    if save_result.code != status.HTTP_200_OK:
        logger.error(f"Failed to save runtime info: {save_result.message}")
    return json.dumps(deploy_result)


async def get_deploy_info(
        agent_id,
        space_id,
) -> list:
    with get_db_jw() as db:
        runtime_db = JiuwenBaseRepository(db, RuntimeInfoDB)

        # 构建查询条件（使用 agent_id 和 space_id）
        find_id = {
            "source_id": agent_id,
            "space_id": space_id,
            "is_delete": False
        }

        # 查询部署信息
        deploy_info = runtime_db.get_dl_in_sql(find_id=find_id)

        if deploy_info.code != status.HTTP_200_OK or not deploy_info.data:
            logger.warning(f"Deployment not found for agent_id={agent_id}")
            return ""

        # 处理 datetime 对象的序列化问题
        result = []
        for item in deploy_info.data:
            deploy_data = item.copy()
            if isinstance(deploy_data.get("create_at"), datetime.datetime):
                deploy_data["create_at"] = deploy_data["create_at"].isoformat()
            if isinstance(deploy_data.get("update_at"), datetime.datetime):
                deploy_data["update_at"] = deploy_data["update_at"].isoformat()
            result.append(deploy_data)
    return result


async def delete_deploy_agent(
        deployment_id,
        user_id,
        space_id,
        client: RuntimeAgentClient = None,
) -> dict:
    # 调用runtime接口执行删除
    if client is None:
        client = get_agent_client()
    delete_result = await client.delete_deploy_agent(deployment_id, user_id, space_id)
    if delete_result.status_code == 202:
        _ = await unregister_deploy_info(deployment_id, space_id)
        logger.info(f"Delete deploy detail for runtime server not found: deployment_id={deployment_id}")
    elif delete_result.status_code != status.HTTP_200_OK:
        logger.error(f"Failed to delete runtime info: {delete_result.content}")
    logger.info(f"Agent removed from runtime successfully: deployment_id={deployment_id}")
    return delete_result


async def unregister_deploy_info(
        deployment_id,
        space_id
) -> int:
    # 更新到deployment表里
    with get_db_jw() as db:
        runtime_db = JiuwenBaseRepository(db, RuntimeInfoDB)

        # 使用 deployment_id 删除记录
        delete_find_id = {
            "deployment_id": deployment_id,
            "space_id": space_id
        }

        # 先查询是否存在
        deploy_info = runtime_db.get_dl_in_sql(find_id=delete_find_id, return_first_item=True)

        if deploy_info.code != status.HTTP_200_OK or not deploy_info.data:
            logger.warning(f"Deployment info not found for deployment_id={deployment_id}")
            return status.HTTP_404_NOT_FOUND

        # 执行逻辑删除：更新 is_delete 字段为 True
        now_beijing = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        update_data = {
            "is_delete": True,
            "update_at": now_beijing
        }

        update_result = runtime_db.update_dl_in_sql(
            find_id=delete_find_id,
            update_dl=update_data
        )

        if update_result.code != status.HTTP_200_OK:
            logger.warning(f"Failed to delete deployment info from database: {update_result.message}")
        else:
            logger.info(f"Deployment info deleted from database: deployment_id={deployment_id}")
    return update_result.code


async def get_deploy_list(
        deploy_status,
        user_id: Optional[str] = None,
        space_id: Optional[str] = None,
        client: RuntimeAgentClient = None,
) -> dict:
    if client is None:
        client = get_agent_client()
    deploy_list = await client.get_deploy_list(deploy_status, user_id, space_id)
    if deploy_list:
        logger.info(f"Get deploy list successfully: status={deploy_status}")

    return deploy_list


async def get_deploy_details(
        agent_id,
        deploy_status: Optional[str] = None,
        user_id: Optional[str] = None,
        space_id: Optional[str] = None,
        client: RuntimeAgentClient = None,
) -> list:
    # 接前端入参，取出deployment_id
    if client is None:
        client = get_agent_client()
    result = await get_deploy_info(agent_id, space_id)
    deploy_details = []
    if result:
        for deploy_info in result:
            deployment_id = deploy_info.get("deployment_id", "")
            deploy_detail = await client.get_deploy_detail(deployment_id, user_id, space_id)
            if isinstance(deploy_detail, dict) and deploy_detail:
                logger.info(f"Get deploy detail successfully: deployment_id={deployment_id}")
                if deploy_status and deploy_detail.get("status") == deploy_status:
                    deploy_details.append(deploy_detail)
                elif not deploy_status:
                    deploy_details.append(deploy_detail)
            elif deploy_detail.status_code == 202:
                _ = await unregister_deploy_info(deployment_id, space_id)
                logger.info(f"Delete deploy detail for runtime server not found: deployment_id={deployment_id}")
        return {"deploy_details": deploy_details}
    else:
        return []


async def get_agent_deploy_detail(
        deployment_id,
        user_id,
        space_id,
        client: RuntimeAgentClient = None,
) -> dict:
    # 接前端入参，取出deployment_id
    if client is None:
        client = get_agent_client()

        deploy_detail = await client.get_deploy_detail(deployment_id, user_id, space_id)
        if isinstance(deploy_detail, dict) and deploy_detail:
            logger.info(f"Get deploy detail successfully: deployment_id={deployment_id}")
            return deploy_detail
        elif deploy_detail.status_code == 202:
            _ = await unregister_deploy_info(deployment_id, space_id)
            logger.info(f"Delete deploy detail for runtime server not found: deployment_id={deployment_id}")
    else:
        return {}
