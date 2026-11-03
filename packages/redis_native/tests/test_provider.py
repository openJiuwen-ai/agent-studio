# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""NativeRedisProvider 单测：三池装配 / cluster 共享 / 生命周期 / 兼容视图。

build_async_client 被 monkeypatch（provider 模块级引用）——本文件验证的是
**装配决策**（何时建几个客户端、传什么池参数），客户端构建参数本身由
test_connection.py 覆盖。
"""

from __future__ import annotations

import asyncio

import pytest
import redis.exceptions as redis_exc

import redis_native.provider as provider_module
from redis_native.capabilities import SUPPORTED_CAPABILITIES
from redis_native.client import NativeRedisClient
from redis_native.provider import NativeRedisProvider

from redis_spi.capabilities import CounterCapability, PubSubCapability
from redis_spi.config import RedisMode, RedisProviderSettings
from redis_spi.exceptions import RedisConfigError, RedisConnectionError

from redis_native_test_fakes import FakeRedisClient


def make_settings(**overrides) -> RedisProviderSettings:
    return RedisProviderSettings(_env_file=None, **overrides)


@pytest.fixture
def created(monkeypatch):
    """捕获 build_async_client 的每次调用（客户端, 覆盖参数）。"""
    calls: list[tuple[FakeRedisClient, dict]] = []

    def fake_build(settings, **kwargs):
        client = FakeRedisClient(results={"ping": True})
        calls.append((client, kwargs))
        return client

    monkeypatch.setattr(provider_module, "build_async_client", fake_build)
    return calls


class TestStartAssembly:
    @staticmethod
    def test_single_builds_three_pools(created):
        provider = NativeRedisProvider()
        client = asyncio.run(provider.start(make_settings()))

        assert isinstance(client, NativeRedisClient)
        assert len(created) == 3
        main, subscriber, blocking = (c for c, _ in created)
        # 主池无覆盖；订阅/阻塞池独立（§4.3）；阻塞池关 socket_timeout
        assert created[0][1] == {}
        assert created[1][1] == {"max_connections": 1}
        assert created[2][1] == {"max_connections": 2, "socket_timeout": None}
        # 视图绑定：发布走主池，订阅句柄来自订阅池
        assert client.native_client() is main
        assert getattr(client, "_subscriber") is subscriber  # noqa: SLF001
        assert getattr(client, "_blocking") is blocking  # noqa: SLF001

    @staticmethod
    def test_pool_sizes_from_settings(created):
        asyncio.run(
            NativeRedisProvider().start(
                make_settings(subscriber_pool_size=5, blocking_pool_size=7)
            )
        )
        assert created[1][1] == {"max_connections": 5}
        assert created[2][1] == {"max_connections": 7, "socket_timeout": None}

    @staticmethod
    def test_sentinel_builds_three_pools(created):
        asyncio.run(
            NativeRedisProvider().start(
                make_settings(
                    mode=RedisMode.SENTINEL, sentinel_nodes="s1:26379"
                )
            )
        )
        assert len(created) == 3

    @staticmethod
    def test_cluster_shares_main_pool(created):
        provider = NativeRedisProvider()
        client = asyncio.run(
            provider.start(
                make_settings(mode=RedisMode.CLUSTER, cluster_nodes="h1:7000")
            )
        )
        assert len(created) == 1  # 仅主池（redis-py cluster 自管节点连接）
        assert created[0][1] == {}
        # 共享主池：订阅/阻塞视图回退主池（client 侧回退逻辑）
        client.as_capability(PubSubCapability)
        asyncio.run(client.as_capability(CounterCapability).incr("c"))
        assert [c[0] for c in created[0][0].calls][-1] == "incr"

    @staticmethod
    def test_text_mode_and_transaction_default_carried(created):
        provider = NativeRedisProvider()
        client = asyncio.run(
            provider.start(
                make_settings(text_mode=True, redis_transaction_enabled=False)
            )
        )
        assert client.text_mode is True
        client.pipeline()
        assert created[0][0].calls[0][2]["transaction"] is False

    @staticmethod
    def test_ping_and_capability_surface(created):
        client = asyncio.run(NativeRedisProvider().start(make_settings()))
        assert asyncio.run(client.ping()) is True
        assert client.supports(CounterCapability) is True


class TestStop:
    @staticmethod
    def test_stop_closes_all_once_and_idempotent(created):
        provider = NativeRedisProvider()
        asyncio.run(provider.start(make_settings()))
        asyncio.run(provider.stop())
        for fake, _ in created:
            assert [c[0] for c in fake.calls] == ["aclose"]
        asyncio.run(provider.stop())  # 幂等：无新调用
        for fake, _ in created:
            assert [c[0] for c in fake.calls] == ["aclose"]

    @staticmethod
    def test_stop_attempts_all_then_raises_first_translated(created):
        provider = NativeRedisProvider()
        client = asyncio.run(provider.start(make_settings()))
        main = client.native_client()
        getattr(main, "_exceptions")["aclose"] = redis_exc.ConnectionError("main down")  # noqa: SLF001
        getattr(created[1][0], "_exceptions")["aclose"] = redis_exc.TimeoutError("t")  # noqa: SLF001

        with pytest.raises(RedisConnectionError) as excinfo:
            asyncio.run(provider.stop())
        # 首个失败（主池连接错误）决定异常类型；其余池仍被尝试关闭
        assert isinstance(excinfo.value.__cause__, redis_exc.ConnectionError)
        for fake, _ in created:
            assert any(c[0] == "aclose" for c in fake.calls)

    @staticmethod
    def test_stop_before_start_is_noop():
        asyncio.run(NativeRedisProvider().stop())  # 不抛


class TestCapabilitiesAndNativeView:
    @staticmethod
    def test_capabilities_matches_supported_set():
        assert set(NativeRedisProvider().capabilities()) == set(SUPPORTED_CAPABILITIES)

    @staticmethod
    def test_native_client_before_start_rejected():
        with pytest.raises(RedisConfigError, match="尚未启动"):
            NativeRedisProvider().native_client()

    @staticmethod
    def test_native_client_after_start_returns_main(created):
        provider = NativeRedisProvider()
        asyncio.run(provider.start(make_settings()))
        assert provider.native_client() is created[0][0]
