# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for app_release.py — ReleaseInfo model and AppRelease service."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from agent_runtime.serve.apis.app_release import (
    ReleaseInfo,
    AppRelease,
    _RELEASE_WEB_REL_KEY,
    _build_error_response,
)


class TestReleaseWebRelKey:
    """Redis key 常量测试."""

    @staticmethod
    def test_key_format():
        assert _RELEASE_WEB_REL_KEY == "release_web_rel_%s"

    @staticmethod
    def test_key_interpolation():
        key = _RELEASE_WEB_REL_KEY % "abc123"
        assert key == "release_web_rel_abc123"


class TestReleaseInfo:
    """ReleaseInfo Pydantic model 测试."""

    @staticmethod
    def test_defaults():
        info = ReleaseInfo()
        assert info.app_id == ""
        assert info.app_type == ""
        assert info.version_id == ""
        assert info.project_id == ""
        assert info.workspace_id == ""
        assert info.domain_id == ""
        assert info.channel_type is None
        assert info.short_code is None
        assert info.visibility_scope is None
        assert info.call_count is None
        assert info.already_been_called is None
        assert info.update_time is None

    @staticmethod
    def test_from_snake_case_json():
        data = {
            "app_id": "wf-001",
            "app_type": "workflow",
            "version_id": "v1",
            "short_code": "abc123",
            "project_id": "proj-1",
            "workspace_id": "ws-1",
            "domain_id": "dom-1",
            "channel_type": "WEB_PAGE",
            "visibility_scope": "TENANT",
            "call_count": 100,
            "already_been_called": 5,
            "update_time": 1700000000000,
        }
        info = ReleaseInfo.model_validate(data)
        assert info.app_id == "wf-001"
        assert info.app_type == "workflow"
        assert info.version_id == "v1"
        assert info.short_code == "abc123"
        assert info.project_id == "proj-1"
        assert info.visibility_scope == "TENANT"
        assert info.call_count == 100

    @staticmethod
    def test_extra_fields_ignored():
        data = {"app_id": "wf-001", "unknown_field": "ignored"}
        info = ReleaseInfo.model_validate(data)
        assert info.app_id == "wf-001"

    @staticmethod
    def test_model_dump_json_with_alias():
        info = ReleaseInfo(app_id="wf-001", version_id="v1", project_id="proj-1")
        dumped = json.loads(info.model_dump_json(by_alias=True, exclude_none=True))
        assert dumped["app_id"] == "wf-001"
        assert dumped["version_id"] == "v1"
        assert dumped["project_id"] == "proj-1"
        assert "channel_type" not in dumped


class TestAppReleaseGetReleaseInfo:
    """AppRelease.get_release_info 测试."""

    @pytest.mark.asyncio
    async def test_success(self):
        """正常查询返回 ReleaseInfo."""
        release_data = {
            "app_id": "wf-001",
            "app_type": "workflow",
            "version_id": "v1",
            "project_id": "proj-1",
        }
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(release_data).encode("utf-8")

        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            service = AppRelease()
            result = await service.get_release_info("abc123")

        assert isinstance(result, ReleaseInfo)
        assert result.app_id == "wf-001"
        mock_redis.get.assert_awaited_once_with("release_web_rel_abc123")

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self):
        """Redis key 不存在返回 404 JSONResponse."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            service = AppRelease()
            result = await service.get_release_info("nonexistent")

        from fastapi.responses import JSONResponse
        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_redis_error_returns_500(self):
        """Redis 异常返回 500 JSONResponse."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")

        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            service = AppRelease()
            result = await service.get_release_info("abc123")

        from fastapi.responses import JSONResponse
        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_invalid_json_returns_500(self):
        """Redis 数据格式异常返回 500."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"not-valid-json"

        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            service = AppRelease()
            result = await service.get_release_info("abc123")

        from fastapi.responses import JSONResponse
        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_empty_app_id_returns_404(self):
        """app_id 为空返回 404."""
        release_data = {"app_id": "", "version_id": "v1"}
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(release_data).encode("utf-8")

        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            service = AppRelease()
            result = await service.get_release_info("abc123")

        from fastapi.responses import JSONResponse
        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_bytes_response_decoded(self):
        """Redis 返回 bytes 时正确解码."""
        release_data = {"app_id": "wf-002", "version_id": "v2"}
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(release_data).encode("utf-8")

        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            service = AppRelease()
            result = await service.get_release_info("code1")

        assert isinstance(result, ReleaseInfo)
        assert result.app_id == "wf-002"
