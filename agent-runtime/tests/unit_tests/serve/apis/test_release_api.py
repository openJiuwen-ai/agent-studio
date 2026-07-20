# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for release_api.py — create/delete release info endpoints."""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Stub agent_builder modules to avoid import errors (same pattern as test_app_run.py)
if "agent_builder.app" not in sys.modules:
    from flask import Flask

    stub_mod = MagicMock()
    stub_mod.app = Flask(__name__)
    sys.modules["agent_builder.app"] = stub_mod

if "agent_builder.nl_to_agent.nl2" not in sys.modules:
    stub_nl2 = MagicMock()
    sys.modules["agent_builder.nl_to_agent.nl2"] = stub_nl2
    stub_nl_to_agent = MagicMock()
    stub_nl_to_agent.nl2 = stub_nl2
    sys.modules["agent_builder.nl_to_agent"] = stub_nl_to_agent

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from agent_runtime.serve.apis.app_release import ReleaseInfo, _RELEASE_WEB_REL_KEY
from agent_runtime.serve.apis.release_api import (
    create_release_info,
    delete_release_info,
)


def _make_request() -> MagicMock:
    """Build a minimal FastAPI Request mock."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.path_params = {}
    return request


def _patch_request_ctx(project_id: str):
    """Patch _request_ctx.get() to return a context with given project_id.

    release_api.py imports _request_ctx late from agent_runtime.context.request_context,
    so patch the source module's attribute.
    """
    ctx = MagicMock()
    ctx.project_id = project_id
    cv = MagicMock()
    cv.get.return_value = ctx
    return patch("agent_runtime.context.request_context._request_ctx", cv)


class TestCreateReleaseInfo:
    """POST /v1/{project_id}/releases — create_release_info tests."""

    @pytest.mark.asyncio
    async def test_success(self):
        """正常写入 Redis 返回 200."""
        body = ReleaseInfo(
            app_id="wf-001",
            app_type="workflow",
            version_id="v1",
            short_code="abc123",
        )
        mock_redis = AsyncMock()

        with (
            _patch_request_ctx("domain-1"),
            patch(
                "agent_runtime.common.redis_manager.get_redis_client",
                return_value=mock_redis,
            ),
        ):
            result = await create_release_info(
                project_id="proj-1",
                body=body,
                request=_make_request(),
                workspace_id="ws-1",
            )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200
        mock_redis.set.assert_awaited_once()
        # Verify Redis key format
        call_args = mock_redis.set.await_args
        assert call_args.args[0] == "release_web_rel_abc123"
        # Verify payload contains supplemented fields
        payload = json.loads(call_args.args[1])
        assert payload["app_id"] == "wf-001"
        assert payload["project_id"] == "proj-1"
        assert payload["workspace_id"] == "ws-1"
        assert payload["domain_id"] == "domain-1"
        assert payload["already_been_called"] == 0
        assert "update_time" in payload

    @pytest.mark.asyncio
    async def test_missing_short_code_returns_400(self):
        """short_code 为 None 返回 400."""
        body = ReleaseInfo(app_id="wf-001", version_id="v1", short_code=None)
        result = await create_release_info(
            project_id="proj-1",
            body=body,
            request=_make_request(),
        )
        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_short_code_returns_400(self):
        """short_code 空字符串返回 400."""
        body = ReleaseInfo(app_id="wf-001", version_id="v1", short_code="")
        result = await create_release_info(
            project_id="proj-1",
            body=body,
            request=_make_request(),
        )
        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_redis_error_returns_500(self):
        """Redis 写入异常返回 500."""
        body = ReleaseInfo(
            app_id="wf-001",
            version_id="v1",
            short_code="abc123",
        )
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = ConnectionError("Redis down")

        with (
            _patch_request_ctx("domain-1"),
            patch(
                "agent_runtime.common.redis_manager.get_redis_client",
                return_value=mock_redis,
            ),
        ):
            result = await create_release_info(
                project_id="proj-1",
                body=body,
                request=_make_request(),
            )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_workspace_id_defaults_to_empty(self):
        """workspace_id 未传时默认为空字符串."""
        body = ReleaseInfo(
            app_id="wf-001",
            version_id="v1",
            short_code="abc123",
        )
        mock_redis = AsyncMock()

        with (
            _patch_request_ctx("domain-1"),
            patch(
                "agent_runtime.common.redis_manager.get_redis_client",
                return_value=mock_redis,
            ),
        ):
            result = await create_release_info(
                project_id="proj-1",
                body=body,
                request=_make_request(),
                workspace_id=None,
            )

        assert result.status_code == 200
        payload = json.loads(mock_redis.set.await_args.args[1])
        assert payload["workspace_id"] == ""

    @pytest.mark.asyncio
    async def test_domain_id_from_request_context(self):
        """domain_id 来源于 RequestContext.project_id."""
        body = ReleaseInfo(
            app_id="wf-001",
            version_id="v1",
            short_code="abc123",
        )
        mock_redis = AsyncMock()

        with (
            _patch_request_ctx("auth-domain-xyz"),
            patch(
                "agent_runtime.common.redis_manager.get_redis_client",
                return_value=mock_redis,
            ),
        ):
            await create_release_info(
                project_id="proj-1",
                body=body,
                request=_make_request(),
            )

        payload = json.loads(mock_redis.set.await_args.args[1])
        assert payload["domain_id"] == "auth-domain-xyz"

    @pytest.mark.asyncio
    async def test_domain_id_empty_when_ctx_project_id_none(self):
        """RequestContext.project_id 为 None 时 domain_id 为空字符串."""
        body = ReleaseInfo(
            app_id="wf-001",
            version_id="v1",
            short_code="abc123",
        )
        mock_redis = AsyncMock()

        with (
            _patch_request_ctx(None),
            patch(
                "agent_runtime.common.redis_manager.get_redis_client",
                return_value=mock_redis,
            ),
        ):
            await create_release_info(
                project_id="proj-1",
                body=body,
                request=_make_request(),
            )

        payload = json.loads(mock_redis.set.await_args.args[1])
        assert payload["domain_id"] == ""


class TestDeleteReleaseInfo:
    """DELETE /v1/{project_id}/releases/{release_id} — delete_release_info tests."""

    @pytest.mark.asyncio
    async def test_success(self):
        """正常删除 Redis key 返回 200."""
        mock_redis = AsyncMock()
        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            result = await delete_release_info(
                project_id="proj-1",
                release_id="abc123",
            )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200
        mock_redis.delete.assert_awaited_once_with("release_web_rel_abc123")

    @pytest.mark.asyncio
    async def test_redis_error_returns_500(self):
        """Redis 删除异常返回 500."""
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = ConnectionError("Redis down")
        with patch(
            "agent_runtime.common.redis_manager.get_redis_client",
            return_value=mock_redis,
        ):
            result = await delete_release_info(
                project_id="proj-1",
                release_id="abc123",
            )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

    @staticmethod
    def test_release_key_format():
        """release_id 直接作为 short_code 构建 Redis key."""
        key = _RELEASE_WEB_REL_KEY % "release-xyz"
        assert key == "release_web_rel_release-xyz"
