# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for publish_version_cache.py — 发布版本缓存."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.serve.apis.publish_version_cache import (
    AgentMetadata,
    PublishVersionCache,
    LATEST_PUBLISH_VERSION,
    resolve_published_version,
)


class TestAgentMetadata:
    """AgentMetadata model tests."""

    @staticmethod
    def test_parse_from_alias():
        data = {
            "agentId": "wf-123",
            "versionId": "v1",
            "projectId": "proj-1",
            "domainId": "dom-1",
            "workspaceId": "ws-1",
            "updatedAt": 1234567890,
            "isContentReviewEnable": True,
            "safetyBarrier": False,
            "appType": "chat",
        }
        meta = AgentMetadata.model_validate(data)
        assert meta.agent_id == "wf-123"
        assert meta.version_id == "v1"
        assert meta.project_id == "proj-1"
        assert meta.updated_at == 1234567890
        assert meta.is_content_review_enable is True
        assert meta.safety_barrier is False
        assert meta.app_type == "chat"

    @staticmethod
    def test_extra_fields_ignored():
        data = {"agentId": "wf-123", "unknownField": "value"}
        meta = AgentMetadata.model_validate(data)
        assert meta.agent_id == "wf-123"

    @staticmethod
    def test_defaults():
        meta = AgentMetadata()
        assert meta.agent_id == ""
        assert meta.version_id == ""
        assert meta.updated_at == 0

    @staticmethod
    def test_model_dump_by_alias():
        meta = AgentMetadata(agent_id="wf-123", version_id="v1")
        dumped = meta.model_dump(by_alias=True)
        assert "agentId" in dumped
        assert "versionId" in dumped


class TestPublishVersionCacheGetMetadata:
    """get_publish_metadata tests — 通过公共API验证Redis/OBS读写逻辑."""

    @pytest.mark.asyncio
    async def test_redis_hit(self):
        meta_data = {"agentId": "wf-123", "versionId": "v1"}
        raw = json.dumps(meta_data).encode("utf-8")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=raw)
        mock_manager = MagicMock()
        mock_manager.is_initialized = True

        with patch(
            "agent_runtime.common.redis_manager.RedisClientManager.get_instance",
            return_value=mock_manager,
        ), patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_client,
        ):
            result = await PublishVersionCache.get_publish_metadata("wf-123")
            assert result is not None
            assert result.version_id == "v1"

    @pytest.mark.asyncio
    async def test_redis_not_initialized_falls_to_obs(self):
        meta_data = {"agentId": "wf-123", "versionId": "v2"}
        content = json.dumps(meta_data)

        mock_manager = MagicMock()
        mock_manager.is_initialized = False

        with patch(
            "agent_runtime.common.redis_manager.RedisClientManager.get_instance",
            return_value=mock_manager,
        ), patch(
            "jiuwen.common.store.async_obs.AsyncOBSUtil.get_content",
            new_callable=AsyncMock,
            return_value=content,
        ):
            result = await PublishVersionCache.get_publish_metadata("wf-123")
            assert result is not None
            assert result.version_id == "v2"

    @pytest.mark.asyncio
    async def test_redis_empty_obs_fallback_bytes(self):
        meta_data = {"agentId": "wf-123", "versionId": "v3"}
        content = json.dumps(meta_data).encode("utf-8")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_manager = MagicMock()
        mock_manager.is_initialized = True

        with patch(
            "agent_runtime.common.redis_manager.RedisClientManager.get_instance",
            return_value=mock_manager,
        ), patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "jiuwen.common.store.async_obs.AsyncOBSUtil.get_content",
            new_callable=AsyncMock,
            return_value=content,
        ):
            result = await PublishVersionCache.get_publish_metadata("wf-123")
            assert result is not None
            assert result.version_id == "v3"

    @pytest.mark.asyncio
    async def test_obs_success_writes_back_to_redis(self):
        meta_data = {"agentId": "wf-123", "versionId": "v2"}
        content = json.dumps(meta_data)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock()
        mock_manager = MagicMock()
        mock_manager.is_initialized = True

        with patch(
            "agent_runtime.common.redis_manager.RedisClientManager.get_instance",
            return_value=mock_manager,
        ), patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "jiuwen.common.store.async_obs.AsyncOBSUtil.get_content",
            new_callable=AsyncMock,
            return_value=content,
        ):
            result = await PublishVersionCache.get_publish_metadata("wf-123")
            assert result.version_id == "v2"
            # 验证 OBS 成功后回写 Redis
            mock_client.set.assert_awaited_once()
            set_args = mock_client.set.call_args[0]
            assert "agent-builder:agent:metadata:wf-123:latest" in set_args[0]

    @pytest.mark.asyncio
    async def test_both_miss(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_manager = MagicMock()
        mock_manager.is_initialized = True

        with patch(
            "agent_runtime.common.redis_manager.RedisClientManager.get_instance",
            return_value=mock_manager,
        ), patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_client,
        ), patch(
            "jiuwen.common.store.async_obs.AsyncOBSUtil.get_content",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await PublishVersionCache.get_publish_metadata("wf-123")
            assert result is None


class TestResolvePublishedVersion:
    """resolve_published_version tests."""

    @pytest.mark.asyncio
    async def test_non_latest_passthrough(self):
        result = await resolve_published_version("wf-123", "v1")
        assert result == "v1"

    @pytest.mark.asyncio
    async def test_none_passthrough(self):
        result = await resolve_published_version("wf-123", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_latest_resolved(self):
        meta = AgentMetadata(agent_id="wf-123", version_id="resolved-v1")

        with patch.object(
            PublishVersionCache, "get_publish_metadata", new_callable=AsyncMock,
            return_value=meta,
        ):
            result = await resolve_published_version("wf-123", LATEST_PUBLISH_VERSION)
            assert result == "resolved-v1"

    @pytest.mark.asyncio
    async def test_latest_resolve_failed(self):
        with patch.object(
            PublishVersionCache, "get_publish_metadata", new_callable=AsyncMock,
            return_value=None,
        ):
            result = await resolve_published_version("wf-123", LATEST_PUBLISH_VERSION)
            assert result is None
