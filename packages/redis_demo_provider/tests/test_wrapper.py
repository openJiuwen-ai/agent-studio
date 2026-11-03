# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""形态二（WrapperDemoProvider）单测：鉴权重试 + 逐命令注入（延迟/失败/限流）。

注入默认全关（透明模式）——契约套件对形态二的跑批即在此模式下进行；
本文件验证各注入开关本身的行为。
"""

import asyncio
import time

import pytest

from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import RedisAuthFailureError, RedisConnectionError
from redis_spi.factory import RedisProviderFactory

_TARGET = "redis_demo_provider.wrapper:WrapperDemoProvider"


def _settings(config: dict) -> RedisProviderSettings:
    import json

    # fakeredis: true 使被包装的 native 客户端离线可跑（README 口径）
    config = {"fakeredis": True, **config}
    return RedisProviderSettings(
        _env_file=None,
        REDIS_PROVIDER=_TARGET,
        REDIS_MODE="single",
        REDIS_PROVIDER_CONFIG=json.dumps(config),
    )


def test_auth_requires_app_id_and_passport():
    async def scenario():
        with pytest.raises(RedisAuthFailureError):
            await RedisProviderFactory.create(_settings({"maxAttempts": 1}))

    asyncio.run(scenario())


def test_auth_retries_then_succeeds():
    async def scenario():
        # 前 2 次鉴权失败（模拟抖动），第 3 次成功（maxAttempts=3）
        client = await RedisProviderFactory.create(
            _settings({"appId": "a", "passport": "p", "authFailures": 2, "maxAttempts": 3})
        )
        try:
            assert await client.ping() is True
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_auth_exhausts_attempts():
    async def scenario():
        with pytest.raises(RedisAuthFailureError):
            await RedisProviderFactory.create(
                _settings({"appId": "a", "passport": "p", "authFailures": 3, "maxAttempts": 3})
            )

    asyncio.run(scenario())


def test_transparent_mode_passes_and_logs():
    async def scenario():
        client = await RedisProviderFactory.create(
            _settings({"appId": "a", "passport": "p"})
        )
        try:
            assert await client.set("w:t", b"v") == b"OK"
            assert await client.get("w:t") == b"v"
            commands = [entry["command"] for entry in client.command_log]
            assert "set" in commands and "get" in commands
            assert all(entry["error"] is None for entry in client.command_log)
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_delay_injection():
    async def scenario():
        client = await RedisProviderFactory.create(
            _settings({"appId": "a", "passport": "p", "delayMs": 60})
        )
        try:
            started = time.perf_counter()
            await client.get("w:any")
            elapsed = time.perf_counter() - started
            assert elapsed >= 0.055, f"延迟注入未生效：{elapsed * 1000:.1f}ms"
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_failure_injection():
    async def scenario():
        client = await RedisProviderFactory.create(
            _settings({"appId": "a", "passport": "p", "failureRate": 1.0})
        )
        try:
            with pytest.raises(RedisConnectionError):
                await client.get("w:any")
            assert client.command_log[-1]["error"] is not None
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_rate_limit_injection():
    async def scenario():
        client = await RedisProviderFactory.create(
            _settings({"appId": "a", "passport": "p", "rateLimitPerSec": 2})
        )
        try:
            await client.get("w:a")  # 1/2
            await client.get("w:b")  # 2/2
            with pytest.raises(RedisConnectionError):
                await client.get("w:c")  # 超限
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_lifecycle_methods_not_instrumented():
    async def scenario():
        client = await RedisProviderFactory.create(
            _settings({"appId": "a", "passport": "p", "failureRate": 1.0})
        )
        try:
            # ping/aclose 不在注入面：failureRate=1.0 下健康检查仍可用
            assert await client.ping() is True
            await client.aclose()
        finally:
            pass

    asyncio.run(scenario())
