#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import json
import datetime
from typing import AsyncIterator, Optional
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException, status

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.agent import AgentGetVersion
from openjiuwen_studio.core.thirdparty_client import RuntimeAgentClient
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw, JiuwenBaseRepository
from openjiuwen_studio.models.runtime_info import RuntimeInfoDB


# 依赖注入（或直接使用单例）
def get_agent_client():
    return RuntimeAgentClient()  # 或全局单例


def _normalize_runtime_port(port: object, url: object = None) -> int | None:
    """
    runtime_info.port 为整型列；Runtime 可能返回 '' 或 null，需转为 int 或 None。
    若 port 无效，尝试从 url（如 http://localhost:8073/）解析端口。
    """
    p: int | None
    if port is None:
        p = None
    elif isinstance(port, int):
        p = port
    elif isinstance(port, str):
        s = port.strip()
        if s == "":
            p = None
        else:
            try:
                p = int(s)
            except ValueError:
                p = None
    else:
        try:
            p = int(port)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            p = None
    if p is None and isinstance(url, str) and url.strip():
        parsed = urlparse(url.strip())
        if parsed.port is not None:
            return parsed.port
    return p


async def get_agent_ir(
        agent_id: str,
        agent_version: str,
        space_id: str,
        current_user: dict
) -> dict:
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
    # 延迟导入，避免与 agent 模块循环依赖（agent 会引用本模块的 get_deploy_info 等）
    import openjiuwen_studio.core.manager.agent as mgr
    from openjiuwen_studio.schemas.agent import AgentExportRequest

    # 构建请求参数
    req = AgentExportRequest(
        agent_id=agent_id,
        space_id=space_id,
        agent_version=agent_version if agent_version else None
    )

    res = await mgr.agent_export(req, current_user)
    # 处理返回值：可能是 ResponseModel 或 (BytesIO, filename) 元组
    if isinstance(res, tuple) and len(res) == 2:
        # ZIP 文件情况：需要解压并解析 JSON
        import zipfile
        import io

        zip_buffer, _ = res
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            json_files = [f for f in zf.namelist() if f.endswith('.json')]
            if not json_files:
                raise ValueError("No JSON file found in export data")

            main_config_file = json_files[0]
            with zf.open(main_config_file) as f:
                export_data = json.loads(f.read().decode('utf-8'))

        return export_data
    else:
        # ResponseModel 情况：直接提取 data 字段
        return res.data


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
    deploy_url = deploy_result.get("url") or ""
    runtime_info_data = {
        "deployment_id": deploy_result.get("deployment_id", ""),
        "space_id": space_id,
        "source_id": agent_id,
        "version": agent_version,
        "type": deploy_result.get("type", ""),
        "name": deploy_result.get("name", ""),
        "status": deploy_result.get("status", ""),
        "url": deploy_url,
        "port": _normalize_runtime_port(deploy_result.get("port"), deploy_url),
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


async def save_part_deploy_info(
        agent_version: str,
        agent_id,
        space_id,
):
    runtime_info_data = {
        "space_id": space_id,
        "source_id": agent_id,
        "version": agent_version,
        "status": "pending",
        "is_delete": False,
    }
    # 存到新deployment表里
    with get_db_jw() as db:
        runtime_db = JiuwenBaseRepository(db, RuntimeInfoDB)

        # 构建查询条件（使用 deployment_id 作为唯一标识）
        find_id = {
            "space_id": space_id,
            "source_id": agent_id,
            "version": agent_version,
            "is_delete": False,
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
        logger.error(f"Failed to create deploy runtime info: {save_result.message}")


async def update_deploy_info(
        deploy_result_str: str,
        agent_version: str,
        agent_id,
        space_id,
) -> str:
    deploy_result = json.loads(deploy_result_str)
    deploy_url = deploy_result.get("url") or ""

    # 存到新deployment表里
    with get_db_jw() as db:
        runtime_db = JiuwenBaseRepository(db, RuntimeInfoDB)

        # 构建查询条件（使用 deployment_id 作为唯一标识）
        find_id = {
            "space_id": space_id,
            "source_id": agent_id,
            "version": agent_version,
            "is_delete": False,
        }

        # 先查询是否存在
        deploy_info = runtime_db.get_dl_in_sql(find_id=find_id, return_first_item=True)

        if deploy_info.code != status.HTTP_200_OK or not deploy_info.data:
            logger.warning(f"Deployment info not found for source_id={agent_id}")
            return status.HTTP_404_NOT_FOUND

        now_beijing = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        update_data = {
            "deployment_id": deploy_result.get("deployment_id", ""),
            "type": deploy_result.get("type", ""),
            "name": deploy_result.get("name", ""),
            "status": deploy_result.get("status", ""),
            "url": deploy_url,
            "port": _normalize_runtime_port(deploy_result.get("port"), deploy_url),
            "update_at": now_beijing
        }

        # 注册到数据库
        save_result = runtime_db.update_dl_in_sql(
            find_id=find_id,
            update_dl=update_data
        )
    if save_result.code != status.HTTP_200_OK:
        logger.error(f"Failed to update deploy runtime info: {save_result.message}")
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
        deploy_info = runtime_db.get_dl_in_sql(find_id=find_id, order_cols_asc=["create_at"])

        if deploy_info.code != status.HTTP_200_OK or not deploy_info.data:
            logger.warning(f"Deployment not found for agent_id={agent_id}")
            return []

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
) -> dict:
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
        return {"deploy_details": []}


async def stream_deployed_agent_query(
        target_url: str,
        space_id: str,
        body: dict,
) -> AsyncIterator[bytes]:
    """
    服务端转发聊天请求到已部署的 Runtime /query，避免浏览器直连 Runtime 触发 CORS。
    """
    target = (target_url or "").strip()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment URL is empty",
        )

    forward = {k: v for k, v in body.items() if k not in {"agent_id", "target_url"}}
    forward.setdefault("space_id", space_id)

    timeout = httpx.Timeout(600.0, connect=30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            async with http.stream(
                "POST",
                target,
                json=forward,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            ) as resp:
                if resp.status_code >= 400:
                    err = await resp.aread()
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=(
                            f"Runtime returned {resp.status_code}: "
                            f"{err.decode('utf-8', errors='replace')[:2000]}"
                        ),
                    )
                async for chunk in resp.aiter_bytes():
                    yield chunk
    except httpx.HTTPStatusError as e:
        err = await e.response.aread() if e.response else b""
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=err.decode("utf-8", errors="replace")[:2000],
        ) from e
    except httpx.RequestError as e:
        logger.error(f"stream_deployed_agent_query: failed to reach {target}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach runtime: {e}",
        ) from e


async def reset_deployed_agent_conversation(
        target_url: str,
        space_id: str,
        body: dict,
) -> dict:
    """
    服务端转发重置会话请求到已部署 Runtime /reset_conversation，避免浏览器直连 Runtime 触发 CORS。
    """
    target = (target_url or "").strip()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment URL is empty",
        )

    forward = {k: v for k, v in body.items() if k not in {"agent_id", "target_url"}}
    forward.setdefault("space_id", space_id)
    if not forward.get("conversation_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation_id is required",
        )

    timeout = httpx.Timeout(120.0, connect=30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            resp = await http.post(
                target,
                json=forward,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        f"Runtime returned {resp.status_code}: "
                        f"{resp.text[:2000]}"
                    ),
                )
            try:
                return resp.json()
            except ValueError:
                return {"status": "ok", "message": resp.text}
    except httpx.RequestError as e:
        logger.error(f"reset_deployed_agent_conversation: failed to reach {target}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach runtime: {e}",
        ) from e


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
