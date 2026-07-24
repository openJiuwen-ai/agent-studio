# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Checkpointer 配置构建工具。"""

from typing import Any, Dict, Optional

from common_utils.redis_manager import get_redis_client
from openjiuwen.core.session.checkpointer.checkpointer import CheckpointerConfig


def build_redis_checkpointer_config(
    *,
    default_ttl: int = 10,
    agent_ttl: Optional[int] = None,
    agent_team_ttl: Optional[int] = None,
    workflow_ttl: Optional[int] = None,
) -> CheckpointerConfig:
    """构建 Redis Checkpointer 配置。

    从 RedisClientManager 获取预构建的异步 Redis 客户端并注入到配置中。

    Args:
        default_ttl: 默认 TTL（分钟）
        agent_ttl: Agent 状态 TTL（分钟）
        agent_team_ttl: Agent Team 状态 TTL（分钟）
        workflow_ttl: Workflow 状态 TTL（分钟）

    Returns:
        CheckpointerConfig 配置对象，可直接传给 CheckpointerFactory.create()
    """
    ttl_dict: Dict[str, Any] = {"default_ttl": default_ttl}
    if agent_ttl is not None:
        ttl_dict["agent_ttl"] = agent_ttl
    if agent_team_ttl is not None:
        ttl_dict["agent_team_ttl"] = agent_team_ttl
    if workflow_ttl is not None:
        ttl_dict["workflow_ttl"] = workflow_ttl

    redis_client = get_redis_client()

    connection_dict: Dict[str, Any] = {
        "redis_client": redis_client,
        "url": None,
        "cluster_mode": None,
        "connection_args": {},
    }

    return CheckpointerConfig(
        type="redis",
        conf={
            "connection": connection_dict,
            "ttl": ttl_dict,
        },
    )
