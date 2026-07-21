# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for env_variables_loader.py — 环境变量加载工具."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from agent_runtime.common.env_variables_loader import (
    _parse_env_variables,
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
            "agent_runtime.common.env_variables_loader.decrypt",
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
            "agent_runtime.common.env_variables_loader.decrypt",
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
            "agent_runtime.common.env_variables_loader.get_redis_client",
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
            "agent_runtime.common.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_environment_variables("env-123", "ws-456")
        assert result == {}

    @pytest.mark.asyncio
    async def test_redis_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("redis down"))

        with patch(
            "agent_runtime.common.env_variables_loader.get_redis_client",
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
            "agent_runtime.common.env_variables_loader.get_redis_client",
            return_value=mock_client,
        ):
            result = await load_environment_variables("env-123", None)
        assert result["plugin_url_params"]["host"] == "localhost"
        mock_client.get.assert_awaited_once_with("environment:env-123:workspaceId:")
