# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""accessor.py 生命周期契约测试。"""

import asyncio

import pytest

import redis_spi.accessor as accessor
from redis_spi import registry
from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import RedisConfigError, RedisTimeoutError

from redis_spi_test_fakes import FakeRedisClient, FakeRedisProvider

FAKE_SETTINGS = dict(REDIS_PROVIDER="accessor-fake")


def _register_fake():
    registry.register_provider("accessor-fake", FakeRedisProvider)


class TestLifecycle:
    @staticmethod
    def test_initialize_then_get_redis():
        _register_fake()
        client = asyncio.run(accessor.initialize(RedisProviderSettings(**FAKE_SETTINGS)))
        assert isinstance(client, FakeRedisClient)
        assert accessor.get_redis() is client
        assert accessor.is_initialized() is True

    @staticmethod
    def test_initialize_idempotent_returns_same_client():
        _register_fake()
        first = asyncio.run(accessor.initialize(RedisProviderSettings(**FAKE_SETTINGS)))
        second = asyncio.run(accessor.initialize(RedisProviderSettings(**FAKE_SETTINGS)))
        assert first is second

    @staticmethod
    def test_get_redis_uninitialized_fail_fast():
        with pytest.raises(RedisConfigError) as excinfo:
            accessor.get_redis()
        # 报错自描述：指明初始化入口
        assert "initialize" in str(excinfo.value)

    @staticmethod
    def test_get_redis_or_none():
        assert accessor.get_redis_or_none() is None
        _register_fake()
        asyncio.run(accessor.initialize(RedisProviderSettings(**FAKE_SETTINGS)))
        assert isinstance(accessor.get_redis_or_none(), FakeRedisClient)


class TestClose:
    @staticmethod
    def test_aclose_closes_client_and_clears():
        _register_fake()
        client = asyncio.run(accessor.initialize(RedisProviderSettings(**FAKE_SETTINGS)))
        asyncio.run(accessor.aclose())
        assert client.closed is True
        assert accessor.is_initialized() is False

    @staticmethod
    def test_aclose_idempotent():
        asyncio.run(accessor.aclose())
        asyncio.run(accessor.aclose())

    @staticmethod
    def test_reset_clears_without_closing():
        _register_fake()
        client = asyncio.run(accessor.initialize(RedisProviderSettings(**FAKE_SETTINGS)))
        accessor.reset()
        assert accessor.is_initialized() is False
        assert client.closed is False  # reset 不关连接（测试隔离语义）


class TestAwaitProviderReady:
    @staticmethod
    def test_immediate_when_initialized():
        _register_fake()
        client = asyncio.run(accessor.initialize(RedisProviderSettings(**FAKE_SETTINGS)))
        ready = asyncio.run(accessor.await_provider_ready())
        assert ready is client

    @staticmethod
    def test_timeout_when_not_initialized():
        with pytest.raises(RedisTimeoutError):
            asyncio.run(accessor.await_provider_ready(timeout=0.1))

    @staticmethod
    def test_invalid_timeout_rejected():
        with pytest.raises(ValueError):
            asyncio.run(accessor.await_provider_ready(timeout=0))


class TestConcurrentInitialize:
    def test_first_wins_loser_client_closed(self):
        # 慢启动制造并发窗口：两个 initialize 并发 → 同一实例，败者客户端被回收
        created: list[FakeRedisClient] = []

        class SlowStartProvider(FakeRedisProvider):
            async def start(self, settings):
                await asyncio.sleep(0.02)
                self.start_calls += 1
                client = FakeRedisClient()
                created.append(client)
                self.client = client
                return client

        registry.register_provider("accessor-slow", SlowStartProvider)

        async def run():
            settings = RedisProviderSettings(REDIS_PROVIDER="accessor-slow")
            return await asyncio.gather(
                accessor.initialize(settings), accessor.initialize(settings)
            )

        first, second = asyncio.run(run())
        # 胜者复用：两个调用方拿到同一实例
        assert first is second
        assert accessor.get_redis() is first
        # 恰好两个客户端被创建，且只有败者被回收（无连接泄漏）
        assert len(created) == 2
        assert sum(1 for client in created if client.closed) == 1
        assert first.closed is False
