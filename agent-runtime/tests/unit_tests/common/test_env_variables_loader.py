# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for env_variables_loader.py — 环境变量加载工具."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from common_utils.env_variables_loader import (
    _parse_env_variables,
    load_default_environment_id,
    load_environment_variables,
)


class TestParseEnvVariables:
    """JSON 解析测试."""

    @staticmethod
    def test_normal_string_variable():
        raw = json.dumps([
            {"name": "host", "value": {"content": "localhost", "type": "string", "secret": False}}
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["host"] == "localhost"
        assert result["_secretEnvKeys"] == []

    @staticmethod
    def test_number_variable():
        raw = json.dumps([
            {"name": "port", "value": {"content": "8080", "type": "number", "secret": False}}
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["port"] == 8080

    @staticmethod
    def test_number_float():
        raw = json.dumps([
            {"name": "ratio", "value": {"content": "3.14", "type": "number", "secret": False}}
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["ratio"] == 3.14

    @staticmethod
    def test_secret_variable():
        raw = json.dumps([
            {"name": "api_key", "value": {"content": "plaintext", "type": "string", "secret": True}}
        ])
        with patch(
            "common_utils.env_variables_loader.decrypt",
            return_value="decrypted_val",
        ):
            result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["api_key"] == "decrypted_val"
        assert "api_key" in result["_secretEnvKeys"]

    @staticmethod
    def test_mixed_variables():
        raw = json.dumps([
            {"name": "host", "value": {"content": "localhost", "type": "string", "secret": False}},
            {"name": "key", "value": {"content": "secret_val", "type": "string", "secret": True}},
        ])
        with patch(
            "common_utils.env_variables_loader.decrypt",
            return_value="decrypted",
        ):
            result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["host"] == "localhost"
        assert result["plugin_url_params"]["key"] == "decrypted"
        assert result["_secretEnvKeys"] == ["key"]

    @staticmethod
    def test_empty_content():
        raw = json.dumps([
            {"name": "empty", "value": {"content": "", "type": "string", "secret": False}}
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["empty"] == ""

    @staticmethod
    def test_skip_invalid_items():
        raw = json.dumps([
            {"name": "", "value": {"content": "val", "type": "string", "secret": False}},
            {"name": "no_value", "value": None},
            {"name": "no_content", "value": {"content": None, "type": "string", "secret": False}},
            {"name": "valid", "value": {"content": "ok", "type": "string", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert "valid" in result["plugin_url_params"]
        assert len(result["plugin_url_params"]) == 1

    @staticmethod
    def test_invalid_json():
        result = _parse_env_variables("not json")
        assert result == {}

    @staticmethod
    def test_non_list_json():
        result = _parse_env_variables('{"key": "value"}')
        assert result == {}

    @staticmethod
    def test_empty_list():
        result = _parse_env_variables("[]")
        assert result == {"plugin_url_params": {}, "_secretEnvKeys": []}


class TestLoadEnvironmentVariables:
    """Redis 加载测试."""

    @pytest.mark.asyncio
    async def test_empty_environment_id(self):
        result = await load_environment_variables(None, "ws-123")
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_string_environment_id(self):
        result = await load_environment_variables("", "ws-123")
        assert result == {}

    @pytest.mark.asyncio
    async def test_redis_returns_data(self):
        raw_data = json.dumps([
            {"name": "host", "value": {"content": "localhost", "type": "string", "secret": False}}
        ]).encode("utf-8")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=raw_data)

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_environment_variables("env-123", "ws-456")
        assert result["plugin_url_params"]["host"] == "localhost"
        mock_client.get.assert_awaited_once_with("environment:env-123:workspaceId:ws-456")

    @pytest.mark.asyncio
    async def test_redis_returns_none(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_environment_variables("env-123", "ws-456")
        assert result == {}

    @pytest.mark.asyncio
    async def test_redis_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("redis down"))

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_environment_variables("env-123", "ws-456")
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_workspace_id(self):
        raw_data = json.dumps([
            {"name": "host", "value": {"content": "localhost", "type": "string", "secret": False}}
        ]).encode("utf-8")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=raw_data)

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_environment_variables("env-123", None)
        assert result["plugin_url_params"]["host"] == "localhost"
        mock_client.get.assert_awaited_once_with("environment:env-123:workspaceId:")


class TestLoadDefaultEnvironmentId:
    """项目默认环境 id 加载测试（runtime 直连时按 project_id 兜底读默认环境）."""

    @pytest.mark.asyncio
    async def test_empty_project_id(self):
        """project_id 为空 -> 不访问 Redis，直接返回 None."""
        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            side_effect=AssertionError("redis should not be touched"),
        ):
            result = await load_default_environment_id(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_string_project_id(self):
        """project_id 为空白串 -> 直接返回 None."""
        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            side_effect=AssertionError("redis should not be touched"),
        ):
            result = await load_default_environment_id("")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_key_missing_returns_none(self):
        """Redis key 不存在（老项目从未写默认环境）-> 返回 None 由调用方降级."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_default_environment_id("proj-1")
        assert result is None
        mock_client.get.assert_awaited_once_with("project:proj-1:default_environment")

    @pytest.mark.asyncio
    async def test_redisson_quoted_value_json_loads(self):
        """Redisson 默认 codec 存带引号值 b'\"9abd-...\"' -> json.loads 还原为纯 id."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=b'"9abd-1234-5678"')

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_default_environment_id("proj-1")
        assert result == "9abd-1234-5678"

    @pytest.mark.asyncio
    async def test_plain_string_returns_as_is(self):
        """Redis 存纯字符串（手动写入/其他写入方）-> 原样返回."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=b"env-plain-id")

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_default_environment_id("proj-1")
        assert result == "env-plain-id"

    @pytest.mark.asyncio
    async def test_redis_exception_returns_none(self):
        """Redis 访问异常 -> 记录日志并返回 None，不向上抛."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("redis down"))

        with patch(
            "common_utils.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_default_environment_id("proj-1")
        assert result is None
