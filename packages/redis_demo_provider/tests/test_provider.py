# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""形态一（AcmeDemoProvider）单测：工厂全链路 + 能力声明 + PubSub/Blocking 冒烟。"""

import asyncio

import pytest

from redis_spi import registry
from redis_spi.capabilities import BlockingCommands, CounterCapability, PubSubCapability
from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import CapabilityNotSupportedError
from redis_spi.factory import RedisProviderFactory
from redis_spi.types import Duration

from redis_demo_provider.provider import AcmeDemoProvider

_TARGET = "redis_demo_provider.provider:AcmeDemoProvider"


def _settings(**extra) -> RedisProviderSettings:
    return RedisProviderSettings(
        _env_file=None, REDIS_PROVIDER=_TARGET, REDIS_MODE="single", **extra
    )


def test_factory_create_ping_and_kv_roundtrip():
    async def scenario():
        client = await RedisProviderFactory.create(_settings())
        try:
            assert await client.ping() is True
            assert await client.set("demo:t", b"v") == b"OK"
            assert await client.get("demo:t") == b"v"
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_capability_declaration_is_testable():
    async def scenario():
        client = await RedisProviderFactory.create(_settings())
        try:
            # 声明面：核心 + PubSub + Blocking（框架完整依赖面），不含 Counter
            assert client.supports(PubSubCapability) is True
            assert client.supports(BlockingCommands) is True
            assert client.supports(CounterCapability) is False
            with pytest.raises(CapabilityNotSupportedError):
                client.as_capability(CounterCapability)
            # 一体实现：能力视图即客户端自身
            assert client.as_capability(PubSubCapability) is client
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_entry_point_registered():
    """安装后经 entry_points 组 openjiuwen.redis_providers 注册名为 acme_demo。"""
    assert registry.lookup("acme_demo") is not None


def test_stop_is_idempotent():
    async def scenario():
        provider = AcmeDemoProvider()
        client = await provider.start(_settings())
        await client.aclose()
        await provider.stop()
        await provider.stop()  # 幂等

    asyncio.run(scenario())


def test_pubsub_roundtrip_within_demo_client():
    async def scenario():
        client = await RedisProviderFactory.create(_settings())
        try:
            handle = client.pubsub()
            await handle.subscribe(b"demo:chan")

            received = []

            async def consume():
                async for message in handle.listen():
                    received.append(message)
                    if message.type == "message":
                        return

            task = asyncio.ensure_future(consume())
            await asyncio.sleep(0.05)  # 让消费者启动、订阅注册
            await client.publish(b"demo:chan", b"hello")
            await asyncio.wait_for(task, timeout=5)
            messages = [m for m in received if m.type == "message"]
            assert messages and messages[0].data == b"hello"
            assert messages[0].channel == b"demo:chan"
            await handle.aclose()
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_blpop_timeout_returns_none():
    async def scenario():
        client = await RedisProviderFactory.create(_settings())
        try:
            result = await asyncio.wait_for(
                client.as_capability(BlockingCommands).blpop(
                    [b"demo:empty-list"], Duration.milliseconds(150)
                ),
                timeout=5,
            )
            assert result is None
        finally:
            await client.aclose()

    asyncio.run(scenario())
