# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
PublishVersionCache — 发布版本缓存

从 Redis / OBS 查询 latest 发布版本的 AgentMetadata，
供 version=latest 时解析为实际版本号使用。

对齐 PublishUtils 逻辑：
- Redis key: agent-builder:agent:metadata:{agentId}:latest
- OBS key: metadata/{agentId}/{agentId}_latest.json
- TTL: 10天
"""

import json
from typing import Optional

from openjiuwen.core.common.logging import workflow_logger
from pydantic import BaseModel, Field, ConfigDict


# Redis key 格式
_REDIS_KEY_TEMPLATE = "agent-builder:agent:metadata:%s:%s"

# OBS key 格式: metadata/{agentId}/{agentId}_latest.json
_OBS_KEY_TEMPLATE = "metadata/%s/%s_latest.json"

# Redis 缓存 TTL（秒），PUBLISH_METADATA_EXPIRE_DAYS=10
_PUBLISH_CACHE_TTL = 10 * 24 * 3600


class AgentMetadata(BaseModel):
    """发布版本元数据"""

    agent_id: str = Field(alias="agentId", default="")
    domain_id: str = Field(alias="domainId", default="")
    project_id: str = Field(alias="projectId", default="")
    workspace_id: str = Field(alias="workspaceId", default="")
    version_id: str = Field(alias="versionId", default="")
    updated_at: int = Field(alias="updatedAt", default=0)
    is_content_review_enable: bool = Field(
        alias="isContentReviewEnable", default=False
    )
    safety_barrier: bool = Field(alias="safetyBarrier", default=False)
    app_type: str = Field(alias="appType", default="")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class PublishVersionCache:
    """发布版本缓存 — 从 Redis/OBS 获取 latest 版本元数据。"""

    @staticmethod
    def _build_redis_key(agent_id: str) -> str:
        return _REDIS_KEY_TEMPLATE % (agent_id, "latest")

    @staticmethod
    def _build_obs_key(agent_id: str) -> str:
        return _OBS_KEY_TEMPLATE % (agent_id, agent_id)

    @classmethod
    async def get_publish_metadata(cls, agent_id: str) -> Optional[AgentMetadata]:
        """查询 latest 发布版本元数据，优先 Redis，回退 OBS。

        Args:
            agent_id: 工作流/智能体 ID

        Returns:
            AgentMetadata 实例；查询失败时返回 None
        """
        metadata = await cls._read_from_redis(agent_id)
        if metadata is not None:
            return metadata

        metadata = await cls._read_from_obs(agent_id)
        if metadata is not None:
            # OBS 读取成功，回写 Redis 缓存
            await cls._write_to_redis(agent_id, metadata)
            return metadata

        workflow_logger.error(
            "Publish metadata not found: agent_id=%s", agent_id
        )
        return None

    @classmethod
    async def _read_from_redis(cls, agent_id: str) -> Optional[AgentMetadata]:
        """从 Redis 读取发布版本元数据。"""
        try:
            from agent_runtime.common.redis_manager import (
                get_redis_client,
                RedisClientManager,
            )

            if not RedisClientManager.get_instance().is_initialized:
                workflow_logger.debug("Redis not initialized, skip Redis read")
                return None

            redis_client = get_redis_client()
            key = cls._build_redis_key(agent_id)
            raw = await redis_client.get(key)

            if not raw:
                return None

            data = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            metadata = AgentMetadata.model_validate(json.loads(data))
            workflow_logger.debug(
                "Publish metadata loaded from Redis: agent_id=%s, version_id=%s",
                agent_id,
                metadata.version_id,
            )
            return metadata
        except Exception as e:
            workflow_logger.warning(
                "Failed to read publish metadata from Redis: agent_id=%s, error=%s",
                agent_id,
                e,
            )
            return None

    @classmethod
    async def _read_from_obs(cls, agent_id: str) -> Optional[AgentMetadata]:
        """从 OBS 读取发布版本元数据。"""
        try:
            from jiuwen.common.store.async_obs import AsyncOBSUtil

            obs_key = cls._build_obs_key(agent_id)
            content = await AsyncOBSUtil.get_content(obs_key)

            if not content:
                return None

            if isinstance(content, bytes):
                content = content.decode("utf-8")

            metadata = AgentMetadata.model_validate(json.loads(content))
            workflow_logger.debug(
                "Publish metadata loaded from OBS: agent_id=%s, version_id=%s",
                agent_id,
                metadata.version_id,
            )
            return metadata
        except Exception as e:
            workflow_logger.warning(
                "Failed to read publish metadata from OBS: agent_id=%s, error=%s",
                agent_id,
                e,
            )
            return None

    @classmethod
    async def _write_to_redis(
        cls,
        agent_id: str,
        metadata: AgentMetadata,
    ) -> None:
        """将发布版本元数据写入 Redis 缓存。"""
        try:
            from agent_runtime.common.redis_manager import (
                get_redis_client,
                RedisClientManager,
            )

            if not RedisClientManager.get_instance().is_initialized:
                return

            redis_client = get_redis_client()
            key = cls._build_redis_key(agent_id)
            value = json.dumps(
                metadata.model_dump(by_alias=True), ensure_ascii=False
            )
            await redis_client.set(key, value, ex=_PUBLISH_CACHE_TTL)
            workflow_logger.debug(
                "Publish metadata cached to Redis: agent_id=%s", agent_id
            )
        except Exception as e:
            workflow_logger.warning(
                "Failed to cache publish metadata to Redis: agent_id=%s, error=%s",
                agent_id,
                e,
            )


LATEST_PUBLISH_VERSION = "latest"


async def resolve_published_version(
    agent_id: str, version: Optional[str]
) -> Optional[str]:
    """解析发布版本号 — 当 version=latest 时从缓存获取实际版本号。

    Args:
        agent_id: 工作流/智能体 ID
        version: 请求中的 version 参数

    Returns:
        解析后的实际版本号；非 latest 时原样返回；解析失败时返回 None
    """
    if version != LATEST_PUBLISH_VERSION:
        return version

    metadata = await PublishVersionCache.get_publish_metadata(agent_id)
    if metadata is None:
        return None

    workflow_logger.info(
        "Resolved latest publish version: agent_id=%s, version_id=%s",
        agent_id,
        metadata.version_id,
    )
    return metadata.version_id
