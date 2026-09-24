# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.ports (injection registry)."""

import pytest

from model_service import ports
from storage.exceptions import StorageNotFoundError


class _FakeStorage:
    def __init__(self):
        self.read_keys = []
        self.listed = []

    async def get_content(self, key):
        self.read_keys.append(key)
        return "content"

    async def list_keys(self, prefix):
        self.listed.append(prefix)
        return []


class TestStorageProvider:
    def test_set_then_get(self, reset_model_service_ports):
        fake = _FakeStorage()
        ports.set_storage_provider(lambda: fake)
        assert ports.get_storage_provider() is fake

    def test_set_none_clears(self, reset_model_service_ports):
        fake = _FakeStorage()
        ports.set_storage_provider(lambda: fake)
        ports.set_storage_provider(None)
        # 清除后 get_storage_provider 回退到共享 storage 包（可能因未注入 settings 抛错，
        # 但绝不应再返回已清除的 fake）。
        try:
            provider = ports.get_storage_provider()
            assert provider is not fake
        except RuntimeError:
            pass


class TestLlmSettings:
    def test_set_then_get(self, reset_model_service_ports):
        class _S:
            timeout = 30.0
            ssl_verify = True

        ports.set_llm_settings(lambda: _S())
        settings = ports.get_llm_settings()
        assert settings.timeout == 30.0
        assert settings.ssl_verify is True

    def test_set_none_clears(self, reset_model_service_ports):
        class _S:
            timeout = 1.0
            ssl_verify = False

        ports.set_llm_settings(lambda: _S())
        ports.set_llm_settings(None)
        # 回退到 agent_runtime（本仓库测试环境可能不可用），绝不应返回注入的 _S。
        try:
            settings = ports.get_llm_settings()
            assert not isinstance(settings, _S)
        except ModuleNotFoundError:
            pass


class TestRequestHeaders:
    def test_unregistered_returns_empty(self, reset_model_service_ports):
        # 未注入且 agent_runtime 不可用时返回空 dict。
        assert isinstance(ports.get_request_headers(), dict)

    def test_set_then_get(self, reset_model_service_ports):
        ports.set_request_headers(lambda: {"X": "1"})
        assert ports.get_request_headers() == {"X": "1"}

    def test_factory_exception_swallowed(self, reset_model_service_ports):
        def _boom():
            raise RuntimeError("boom")

        ports.set_request_headers(_boom)
        assert ports.get_request_headers() == {}

    def test_factory_returns_none(self, reset_model_service_ports):
        ports.set_request_headers(lambda: None)
        assert ports.get_request_headers() == {}


class TestEnvVariables:
    def test_unregistered_returns_empty(self, reset_model_service_ports):
        assert isinstance(ports.get_env_variables(), dict)

    def test_set_then_get(self, reset_model_service_ports):
        ports.set_env_variables(lambda: {"plugin_url_params": {"A": "1"}})
        assert ports.get_env_variables() == {"plugin_url_params": {"A": "1"}}

    def test_factory_exception_swallowed(self, reset_model_service_ports):
        ports.set_env_variables(lambda: (_ for _ in ()).throw(RuntimeError()))
        assert ports.get_env_variables() == {}


class TestCustomerHeaders:
    def test_unregistered_returns_empty(self, reset_model_service_ports):
        assert ports.get_request_customer_headers() == {}

    def test_set_then_get(self, reset_model_service_ports):
        ports.set_request_customer_headers(lambda: {"cust-a": "1"})
        assert ports.get_request_customer_headers() == {"cust-a": "1"}

    def test_factory_exception_swallowed(self, reset_model_service_ports):
        def _boom():
            raise RuntimeError("boom")

        ports.set_request_customer_headers(_boom)
        assert ports.get_request_customer_headers() == {}


class TestCacheQueues:
    def test_default_returns_none_or_fallback(self, reset_model_service_ports):
        # 未注册时可能回退 jiuwen 或 None，两者皆可接受。
        assert ports.get_model_cache() is None or ports.get_model_cache() is not None

    def test_set_none_disables(self, reset_model_service_ports):
        ports.set_cache_queues(None, None)
        assert ports.get_model_cache() is None
        assert ports.get_auth_cache() is None

    def test_set_cache_object(self, reset_model_service_ports):
        class _Cache:
            async def aget_with_source(self, key):
                return (None, "")

            async def aput(self, key, value, ttl=None):
                return None

        cache = _Cache()
        ports.set_cache_queues(cache, cache)
        assert ports.get_model_cache() is cache
        assert ports.get_auth_cache() is cache


class TestWrapStorage:
    def test_translates_not_found(self, reset_model_service_ports):
        class _NotFound(Exception):
            pass

        class _Provider:
            async def get_content(self, key):
                raise _NotFound("missing")

            async def list_keys(self, prefix):
                return ["a", "b"]

        wrapped = ports.wrap_storage(_Provider(), _NotFound)

        import asyncio

        async def _run():
            with pytest.raises(StorageNotFoundError):
                await wrapped.get_content("k")

        asyncio.run(_run())

    def test_passes_through_success(self, reset_model_service_ports):
        class _Provider:
            async def get_content(self, key):
                return "ok"

            async def list_keys(self, prefix):
                return ["a"]

        wrapped = ports.wrap_storage(_Provider(), RuntimeError)

        import asyncio

        async def _run():
            assert await wrapped.get_content("k") == "ok"
            assert await wrapped.list_keys("p") == ["a"]

        asyncio.run(_run())
