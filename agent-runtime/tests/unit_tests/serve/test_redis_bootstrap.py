#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis_bootstrap 单测：Settings 映射 + 装配委托 + 错误口径对齐（行为零变化）。"""

import asyncio

import pytest

from agent_runtime.serve.redis_bootstrap import (
    build_provider_settings,
    init_redis_provider,
)
from common_utils.common_config import RedisMode as LegacyRedisMode
from common_utils.common_config import RedisSettings
from redis_spi import RedisMode, RedisProviderSettings, accessor
from redis_spi.exceptions import (
    RedisConfigError,
    RedisConnectionError,
    RedisTimeoutError,
)

#: 断言默认值时须清掉的 Provider 装配字段环境变量（连接字段走显式入参不受影响）。
_ASSEMBLY_ENV_VARS = (
    "REDIS_PROVIDER",
    "REDIS_PROVIDER_CLASS",
    "REDIS_TEXT_MODE",
    "REDIS_SUBSCRIBER_POOL_SIZE",
    "REDIS_BLOCKING_POOL_SIZE",
)

#: 断言默认值时同样须清掉的连接字段环境变量（真实 env 优先级高于 _env_file=None，
#: 终端若残留契约跑批的 REDIS_PASSWORD 等会污染默认值断言）。
_CONNECTION_ENV_VARS = (
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_DATABASE",
    "REDIS_PASSWORD",
    "REDIS_MODE",
    "REDIS_CLUSTER_NODES",
    "REDIS_SENTINEL_NODES",
    "REDIS_SENTINEL_MASTER",
    "REDIS_TRANSACTION_ENABLED",
    "REDIS_MAX_CONNECTIONS",
    "REDIS_SOCKET_TIMEOUT",
    "REDIS_SOCKET_CONNECT_TIMEOUT",
    "REDIS_SSL_ENABLED",
    "REDIS_SSL_CA_CERT",
    "REDIS_SSL_CERT_FILE",
    "REDIS_SSL_KEY_FILE",
    "REDIS_TTL",
)


def make_legacy(**aliases) -> RedisSettings:
    """构造不受环境/.env 干扰的 RedisSettings（显式别名覆盖）。"""
    return RedisSettings(_env_file=None, **aliases)


class _FakeSpiClient:
    """SPI 客户端替身：native_client() 返回预置原生视图。"""

    def __init__(self, native):
        self._native = native

    def native_client(self):
        return self._native


class TestBuildProviderSettings:
    @staticmethod
    def test_connection_fields_carried(monkeypatch):
        for name in _ASSEMBLY_ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        legacy = make_legacy(
            REDIS_HOST="h1",
            REDIS_PORT=6380,
            REDIS_DATABASE=3,
            REDIS_PASSWORD="secret",
            REDIS_TRANSACTION_ENABLED="false",
            REDIS_SENTINEL_MASTER="m1",
            REDIS_SENTINEL_NODES="s1:26380",
            REDIS_MAX_CONNECTIONS=7,
            REDIS_SOCKET_TIMEOUT=9,
            REDIS_SOCKET_CONNECT_TIMEOUT=4,
            REDIS_SSL_ENABLED="true",
            REDIS_SSL_CA_CERT="/ca",
            REDIS_SSL_CERT_FILE="/c",
            REDIS_SSL_KEY_FILE="/k",
            REDIS_TTL=3600,
        )
        settings = build_provider_settings(legacy)
        assert isinstance(settings, RedisProviderSettings)
        assert settings.host == "h1"
        assert settings.port == 6380
        assert settings.db == 3
        # password 在 RedisSettings 层已解密，本层只搬运
        assert settings.password == "secret"
        assert settings.redis_transaction_enabled is False
        assert settings.sentinel_master == "m1"
        assert settings.sentinel_nodes == "s1:26380"
        assert settings.max_connections == 7
        assert settings.socket_timeout == 9.0  # int→float 宽化，数值不变
        assert settings.socket_connect_timeout == 4.0
        assert settings.ssl_enabled is True
        assert settings.ssl_ca_cert == "/ca"
        assert settings.ssl_cert_file == "/c"
        assert settings.ssl_key_file == "/k"
        assert settings.datasource_ttl_seconds == 3600
        # 装配字段不搬运：env 未配置 → 缺省 native
        assert settings.provider == "native"
        assert settings.text_mode is False

    @staticmethod
    def test_mode_mapped_by_value():
        legacy = make_legacy(REDIS_MODE="sentinel", REDIS_SENTINEL_NODES="s1")
        settings = build_provider_settings(legacy)
        assert legacy.mode is LegacyRedisMode.SENTINEL  # 输入是 common_utils 枚举
        assert settings.mode is RedisMode.SENTINEL  # 输出是 redis_spi 枚举

    @staticmethod
    def test_provider_assembly_fields_read_own_env(monkeypatch):
        monkeypatch.setenv("REDIS_PROVIDER", "mycorp")
        monkeypatch.setenv("REDIS_PROVIDER_CLASS", "MyProvider")
        settings = build_provider_settings(make_legacy(REDIS_HOST="h"))
        assert settings.provider == "mycorp"
        assert settings.provider_class == "MyProvider"

    @staticmethod
    def test_defaults_align(monkeypatch):
        for name in _ASSEMBLY_ENV_VARS + _CONNECTION_ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        legacy = make_legacy()
        settings = build_provider_settings(legacy)
        assert settings.host == legacy.host == "127.0.0.1"
        assert settings.port == legacy.port == 6379
        assert settings.password is None
        assert settings.max_connections == 50
        assert settings.socket_timeout == 5.0
        assert settings.mode is RedisMode.SINGLE


class TestInitRedisProvider:
    @staticmethod
    def test_not_configured_returns_none():
        # 与旧 init() 同判据：host 与 cluster_nodes 全空 → 跳过装配
        legacy = make_legacy(REDIS_HOST="", REDIS_CLUSTER_NODES="")
        assert asyncio.run(init_redis_provider(legacy)) is None

    @staticmethod
    def test_success_returns_native_view_and_passes_settings(monkeypatch):
        calls = {}
        native = object()

        async def fake_initialize(settings):
            calls["settings"] = settings
            return _FakeSpiClient(native)

        monkeypatch.setattr(accessor, "initialize", fake_initialize)
        legacy = make_legacy(REDIS_HOST="h1", REDIS_PORT=6380, REDIS_PASSWORD="pw")
        assert asyncio.run(init_redis_provider(legacy)) is native

        passed = calls["settings"]
        assert isinstance(passed, RedisProviderSettings)
        assert passed.host == "h1"
        assert passed.port == 6380
        assert passed.password == "pw"
        assert passed.provider == "native"

    @staticmethod
    def test_connection_error_wrapped_to_runtime_error(monkeypatch):
        async def fake_initialize(settings):
            raise RedisConnectionError("refused")

        monkeypatch.setattr(accessor, "initialize", fake_initialize)
        with pytest.raises(RuntimeError, match="Redis connection check failed"):
            asyncio.run(init_redis_provider(make_legacy(REDIS_HOST="h")))

    @staticmethod
    def test_timeout_error_wrapped_to_runtime_error(monkeypatch):
        async def fake_initialize(settings):
            raise RedisTimeoutError("t/o")

        monkeypatch.setattr(accessor, "initialize", fake_initialize)
        with pytest.raises(RuntimeError, match="Redis connection check failed"):
            asyncio.run(init_redis_provider(make_legacy(REDIS_HOST="h")))

    @staticmethod
    def test_config_error_passthrough(monkeypatch):
        # 配置类错误原样上抛（对齐旧 init() 透传），不套连接失败文案
        async def fake_initialize(settings):
            raise RedisConfigError("bad provider spec")

        monkeypatch.setattr(accessor, "initialize", fake_initialize)
        with pytest.raises(RedisConfigError):
            asyncio.run(init_redis_provider(make_legacy(REDIS_HOST="h")))

    @staticmethod
    def test_non_native_view_raises_config_error(monkeypatch):
        class _NoNativeViewClient:
            pass

        async def fake_initialize(settings):
            return _NoNativeViewClient()

        monkeypatch.setattr(accessor, "initialize", fake_initialize)
        with pytest.raises(RedisConfigError, match="原生视图"):
            asyncio.run(init_redis_provider(make_legacy(REDIS_HOST="h")))
