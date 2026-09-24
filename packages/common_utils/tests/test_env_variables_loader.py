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
    def test_empty_items(self):
        assert _parse_env_variables("[]") == {
            "plugin_url_params": {},
            "_secretEnvKeys": [],
        }

    def test_single_string_var(self):
        raw = json.dumps([
            {"name": "KEY", "value": {"content": "val", "type": "string", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"KEY": "val"}
        assert result["_secretEnvKeys"] == []

    def test_number_var_converted_to_int(self):
        raw = json.dumps([
            {"name": "N", "value": {"content": "42", "type": "number", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"N": 42}
        assert isinstance(result["plugin_url_params"]["N"], int)

    def test_number_var_float(self):
        raw = json.dumps([
            {"name": "F", "value": {"content": "3.14", "type": "number", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"F": 3.14}

    def test_number_var_invalid_keeps_string(self):
        raw = json.dumps([
            {"name": "X", "value": {"content": "not-a-number", "type": "number", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"X": "not-a-number"}

    def test_secret_var_recorded(self):
        raw = json.dumps([
            {"name": "SEC", "value": {"content": "enc:xxx", "type": "string", "secret": True}},
        ])
        result = _parse_env_variables(raw)
        assert result["_secretEnvKeys"] == ["SEC"]

    def test_secret_var_decrypted_plain(self):
        # PlainCrypt 透传，secret content 解密后仍为原值。
        raw = json.dumps([
            {"name": "SEC", "value": {"content": "my-secret", "type": "string", "secret": True}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"]["SEC"] == "my-secret"

    def test_item_without_name_skipped(self):
        raw = json.dumps([
            {"name": "", "value": {"content": "x", "type": "string"}},
            {"name": "OK", "value": {"content": "y", "type": "string"}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"OK": "y"}

    def test_item_without_value_skipped(self):
        raw = json.dumps([{"name": "NO_VALUE"}])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {}

    def test_item_with_none_content_skipped(self):
        raw = json.dumps([
            {"name": "K", "value": {"content": None, "type": "string"}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {}

    def test_double_encoded_json(self):
        inner = json.dumps([
            {"name": "K", "value": {"content": "v", "type": "string", "secret": False}},
        ])
        raw = json.dumps(inner)
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"K": "v"}

    def test_invalid_json_returns_empty(self):
        result = _parse_env_variables("not-json")
        assert result == {}

    def test_non_list_returns_empty(self):
        result = _parse_env_variables(json.dumps({"not": "a list"}))
        assert result == {}

    def test_missing_type_defaults_to_string(self):
        raw = json.dumps([
            {"name": "K", "value": {"content": "v", "secret": False}},
        ])
        result = _parse_env_variables(raw)
        assert result["plugin_url_params"] == {"K": "v"}


class TestLoadDefaultEnvironmentId:
    def test_empty_project_id_returns_none(self, monkeypatch):
        async def _run():
            assert await load_default_environment_id(None) is None
            assert await load_default_environment_id("") is None
        asyncio.run(_run())

    def test_redis_unavailable_returns_none(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        def _boom():
            raise RuntimeError("redis down")

        monkeypatch.setattr(mod, "get_redis_client", _boom)

        async def _run():
            assert await load_default_environment_id("p1") is None
        asyncio.run(_run())

    def test_key_missing_returns_none(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            async def get(self, key):
                return None

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") is None
        asyncio.run(_run())

    def test_bytes_value_returns_string(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            async def get(self, key):
                return b"env-123"

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") == "env-123"
        asyncio.run(_run())

    def test_json_quoted_value_parsed(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            async def get(self, key):
                return b'"env-123"'

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") == "env-123"
        asyncio.run(_run())

    def test_blank_bytes_returns_none(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            async def get(self, key):
                return b"   "

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_default_environment_id("p1") is None
        asyncio.run(_run())


class TestLoadEnvironmentVariables:
    def test_empty_environment_id_returns_empty(self, monkeypatch):
        async def _run():
            assert await load_environment_variables(None, "ws") == {}
            assert await load_environment_variables("", "ws") == {}
        asyncio.run(_run())

    def test_redis_unavailable_returns_empty(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        def _boom():
            raise RuntimeError("redis down")

        monkeypatch.setattr(mod, "get_redis_client", _boom)

        async def _run():
            assert await load_environment_variables("env1", "ws1") == {}
        asyncio.run(_run())

    def test_key_missing_returns_empty(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        class _Client:
            async def get(self, key):
                return None

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            assert await load_environment_variables("env1", "ws1") == {}
        asyncio.run(_run())

    def test_parses_valid_data(self, monkeypatch):
        from common_utils import env_variables_loader as mod

        raw = json.dumps([
            {"name": "API_HOST", "value": {"content": "http://x", "type": "string", "secret": False}},
        ])

        class _Client:
            async def get(self, key):
                return raw.encode("utf-8")

        monkeypatch.setattr(mod, "get_redis_client", lambda: _Client())

        async def _run():
            result = await load_environment_variables("env1", "ws1")
            assert result["plugin_url_params"] == {"API_HOST": "http://x"}
        asyncio.run(_run())
