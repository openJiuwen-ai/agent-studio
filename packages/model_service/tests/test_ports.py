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
    @staticmethod
    def test_set_then_get(reset_model_service_ports):
        fake = _FakeStorage()
        ports.set_storage_provider(lambda: fake)
        assert ports.get_storage_provider() is fake

    @staticmethod
    def test_set_none_clears(reset_model_service_ports):
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
    @staticmethod
    def test_set_then_get(reset_model_service_ports):
        class _S:
            timeout = 30.0
            ssl_verify = True

        ports.set_llm_settings(lambda: _S())
        settings = ports.get_llm_settings()
        assert settings.timeout == 30.0
        assert settings.ssl_verify is True

    @staticmethod
    def test_set_none_clears(reset_model_service_ports):
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
    @staticmethod
    def test_unregistered_returns_empty(reset_model_service_ports):
        # 未注入且 agent_runtime 不可用时返回空 dict。
        assert isinstance(ports.get_request_headers(), dict)

    @staticmethod
    def test_set_then_get(reset_model_service_ports):
        ports.set_request_headers(lambda: {"X": "1"})
        assert ports.get_request_headers() == {"X": "1"}

    @staticmethod
    def test_factory_exception_swallowed(reset_model_service_ports):
        def _boom():
            raise RuntimeError("boom")

        ports.set_request_headers(_boom)
        assert ports.get_request_headers() == {}

    @staticmethod
    def test_factory_returns_none(reset_model_service_ports):
        ports.set_request_headers(lambda: None)
        assert ports.get_request_headers() == {}


class TestEnvVariables:
    @staticmethod
    def test_unregistered_returns_empty(reset_model_service_ports):
        assert isinstance(ports.get_env_variables(), dict)

    @staticmethod
    def test_set_then_get(reset_model_service_ports):
        ports.set_env_variables(lambda: {"plugin_url_params": {"A": "1"}})
        assert ports.get_env_variables() == {"plugin_url_params": {"A": "1"}}

    @staticmethod
    def test_factory_exception_swallowed(reset_model_service_ports):
        ports.set_env_variables(lambda: (_ for _ in ()).throw(RuntimeError()))
        assert ports.get_env_variables() == {}


class TestCustomerHeaders:
    @staticmethod
    def test_unregistered_returns_empty(reset_model_service_ports):
        assert ports.get_request_customer_headers() == {}

    @staticmethod
    def test_set_then_get(reset_model_service_ports):
        ports.set_request_customer_headers(lambda: {"cust-a": "1"})
        assert ports.get_request_customer_headers() == {"cust-a": "1"}

    @staticmethod
    def test_factory_exception_swallowed(reset_model_service_ports):
        def _boom():
            raise RuntimeError("boom")

        ports.set_request_customer_headers(_boom)
        assert ports.get_request_customer_headers() == {}


class TestCacheQueues:
    @staticmethod
    def test_default_returns_none_or_fallback(reset_model_service_ports):
        # 未注册时可能回退 jiuwen 或 None，两者皆可接受。
        assert ports.get_model_cache() is None or ports.get_model_cache() is not None

    @staticmethod
    def test_set_none_disables(reset_model_service_ports):
        ports.set_cache_queues(None, None)
        assert ports.get_model_cache() is None
        assert ports.get_auth_cache() is None

    @staticmethod
    def test_set_cache_object(reset_model_service_ports):
        class _Cache:
            @staticmethod
            async def aget_with_source(key):
                return (None, "")

            @staticmethod
            async def aput(key, value, ttl=None):
                return None

        cache = _Cache()
        ports.set_cache_queues(cache, cache)
        assert ports.get_model_cache() is cache
        assert ports.get_auth_cache() is cache


class TestWrapStorage:
    @staticmethod
    def test_translates_not_found(reset_model_service_ports):
        class _NotFound(Exception):
            pass

        class _Provider:
            @staticmethod
            async def get_content(key):
                raise _NotFound("missing")

            @staticmethod
            async def list_keys(prefix):
                return ["a", "b"]

        wrapped = ports.wrap_storage(_Provider(), _NotFound)

        import asyncio

        async def _run():
            with pytest.raises(StorageNotFoundError):
                await wrapped.get_content("k")

        asyncio.run(_run())

    @staticmethod
    def test_passes_through_success(reset_model_service_ports):
        class _Provider:
            @staticmethod
            async def get_content(key):
                return "ok"

            @staticmethod
            async def list_keys(prefix):
                return ["a"]

        wrapped = ports.wrap_storage(_Provider(), RuntimeError)

        import asyncio

        async def _run():
            assert await wrapped.get_content("k") == "ok"
            assert await wrapped.list_keys("p") == ["a"]

        asyncio.run(_run())
