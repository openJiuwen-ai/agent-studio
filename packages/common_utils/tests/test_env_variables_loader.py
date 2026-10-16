# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.env_variables_loader."""

import asyncio
import json

import pytest

from common_utils.env_variables_loader import (
    _parse_env_variables,
    load_default_environment_id,
    load_environment_variables,
)


class TestParseEnvVariables:
    @staticmethod
    def test_empty_items():
        assert _parse_env_variables("[]") == {
            "plugin_url_params": {},
            "_secretEnvKeys": [],
        }

    @staticmethod
    def test_single_string_var():
        raw = json.dumps([
            {"name": "KEY", "value": {"content": "val", "type": "string", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"KEY": "val"}
        assert result["_secretEnvKeys"] == []

    @staticmethod
    def test_number_var_converted_to_int():
        raw = json.dumps([
            {"name": "N", "value": {"content": "42", "type": "number", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"N": 42}
        assert isinstance(result["plugin_url_params"]["N"], int)

    @staticmethod
    def test_number_var_float():
        raw = json.dumps([
            {"name": "F", "value": {"content": "3.14", "type": "number", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"F": 3.14}

    @staticmethod
    def test_number_var_invalid_keeps_string():
        raw = json.dumps([
            {"name": "X", "value": {"content": "not-a-number", "type": "number", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"X": "not-a-number"}

    @staticmethod
    def test_secret_var_recorded():
        raw = json.dumps([
            {"name": "SEC", "value": {"content": "enc:xxx", "type": "string", "secret": True}},
        ])
        result = _parse_env_variables(raw)
        assert result["_secretEnvKeys"] == ["SEC"]

    @staticmethod
    def test_secret_var_decrypted_plain():
        # PlainCrypt 透传，secret content 解密后仍为原值。
        raw = json.dumps([
            {"name": "SEC", "value": {"content": "my-secret", "type": "string", "secret": True}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["SEC"] == "my-secret"

    @staticmethod
    def test_item_without_name_skipped():
        raw = json.dumps([
            {"name": "", "value": {"content": "x", "type": "string"}},
            {"name": "OK", "value": {"content": "y", "type": "string"}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"OK": "y"}

    @staticmethod
    def test_item_without_value_skipped():
        raw = json.dumps([{"name": "NO_VALUE"}])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {}

    @staticmethod
    def test_item_with_none_content_skipped():
        raw = json.dumps([
            {"name": "K", "value": {"content": None, "type": "string"}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {}

    @staticmethod
    def test_double_encoded_json():
        inner = json.dumps([
            {"name": "K", "value": {"content": "v", "type": "string", "secret": False}},
        ])
        raw = json.dumps(inner)
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"K": "v"}

    @staticmethod
    def test_invalid_json_returns_empty():
        result = _parse_env_variables("not-json")
        assert result == {}

    @staticmethod
    def test_non_list_returns_empty():
        result = _parse_env_variables(json.dumps({"not": "a list"}))
        assert result == {}

    @staticmethod
    def test_missing_type_defaults_to_string():
        raw = json.dumps([
            {"name": "K", "value": {"content": "v", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"K": "v"}


class TestLoadDefaultEnvironmentId:
    @staticmethod
    def test_empty_project_id_returns_none(monkeypatch):
        async def _run():
            assert await load_default_environment_id(None) is None
            assert await load_default_environment_id("") is None
        asyncio.run(_run())

    @staticmethod
    def test_redis_unavailable_returns_none(monkeypatch):
        from common_utils import env_variables_loader as mod

        def _boom():
            raise RuntimeError("redis down")

        monkeypatch.setattr(mod, "get_redis_client", _boom)

        async def _run():
            assert await load_default_environment_id("p1") is None
        asyncio.run(_run())

    @staticmethod
    def test_key_missing_returns_none(monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            @staticmethod
            async def get(key):
                return None

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") is None
        asyncio.run(_run())

    @staticmethod
    def test_bytes_value_returns_string(monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            @staticmethod
            async def get(key):
                return b"env-123"

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") == "env-123"
        asyncio.run(_run())

    @staticmethod
    def test_json_quoted_value_parsed(monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            @staticmethod
            async def get(key):
                return b'"env-123"'

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") == "env-123"
        asyncio.run(_run())

    @staticmethod
    def test_blank_bytes_returns_none(monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            @staticmethod
            async def get(key):
                return b"   "

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") is None
        asyncio.run(_run())


class TestLoadEnvironmentVariables:
    @staticmethod
    def test_empty_environment_id_returns_empty(monkeypatch):
        async def _run():
            assert await load_environment_variables(None, "ws") == {}
            assert await load_environment_variables("", "ws") == {}
        asyncio.run(_run())

    @staticmethod
    def test_redis_unavailable_returns_empty(monkeypatch):
        from common_utils import env_variables_loader as mod

        def _boom():
            raise RuntimeError("redis down")

        monkeypatch.setattr(mod, "get_redis_client", _boom)

        async def _run():
            assert await load_environment_variables("env1", "ws1") == {}
        asyncio.run(_run())

    @staticmethod
    def test_key_missing_returns_empty(monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            @staticmethod
            async def get(key):
                return None

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_environment_variables("env1", "ws1") == {}
        asyncio.run(_run())

    @staticmethod
    def test_parses_valid_data(monkeypatch):
        from common_utils import env_variables_loader as mod

        raw = json.dumps([
            {"name": "API_HOST", "value": {"content": "http://x", "type": "string", "secret": False}},
        ])

        class _Client:
            @staticmethod
            async def get(key):
                return raw.encode("utf-8")

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            result = await load_environment_variables("env1", "ws1")
            assert result["plugin_url_params"] == {"API_HOST": "http://x"}
        asyncio.run(_run())
