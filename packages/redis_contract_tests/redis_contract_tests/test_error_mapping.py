# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""错误映射契约（设计文档 §七）：底层故障/类型错误/用法错误 → redis_spi 异常体系。

分层口径：
  - 客户端侧用法校验（空参/互斥参数）：RedisCommandError，任何后端一致；
  - 服务端类型错误（WRONGTYPE）：RedisWrongTypeError；
  - 连接类故障（坏端口）：RedisConnectionError——仅对真实网络后端可测，
    离线后端（fakeredis/替身）自动 skip（自分类：坏端口装配成功即离线后端）。
"""

import os

import pytest

from redis_spi.capabilities import CounterCapability
from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import (
    CapabilityNotSupportedError,
    RedisCommandError,
    RedisConnectionError,
    RedisError,
    RedisTimeoutError,
    RedisWrongTypeError,
)
from redis_spi.factory import RedisProviderFactory

from redis_contract_tests.conftest import TARGET_ENV
from redis_contract_tests.test_core_contract import run


class TestWrongTypeMapping:
    @staticmethod
    def test_hash_command_on_string_key(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}wt-h"
            await provider_client.set(key, b"v")
            with pytest.raises(RedisWrongTypeError):
                await provider_client.hgetall(key)

        run(loop, scenario())

    @staticmethod
    def test_string_command_on_hash_key(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}wt-s"
            await provider_client.hset(key, field=b"f", value=b"v")
            with pytest.raises(RedisWrongTypeError):
                await provider_client.get(key)

        run(loop, scenario())

    @staticmethod
    def test_list_command_on_set_key(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}wt-l"
            await provider_client.sadd(key, b"m")
            with pytest.raises(RedisWrongTypeError):
                await provider_client.rpush(key, b"x")

        run(loop, scenario())


class TestClientSideValidation:
    """客户端侧 fail-fast 校验（不依赖服务端，任何后端一致）。"""

    @staticmethod
    def test_exists_requires_keys(provider_client, loop):
        async def scenario():
            with pytest.raises(RedisCommandError):
                await provider_client.exists()

        run(loop, scenario())

    @staticmethod
    def test_push_and_sadd_require_members(provider_client, key_prefix, loop):
        async def scenario():
            with pytest.raises(RedisCommandError):
                await provider_client.rpush(f"{key_prefix}x")
            with pytest.raises(RedisCommandError):
                await provider_client.lpush(f"{key_prefix}x")
            with pytest.raises(RedisCommandError):
                await provider_client.sadd(f"{key_prefix}x")

        run(loop, scenario())

    @staticmethod
    def test_hset_forms_mutually_exclusive(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}hset-v"
            with pytest.raises(RedisCommandError):
                await provider_client.hset(
                    key, {b"f": b"v"}, field=b"f", value=b"v"
                )
            with pytest.raises(RedisCommandError):
                await provider_client.hset(key)

        run(loop, scenario())

    @staticmethod
    def test_set_duration_keep_ttl_mutex(provider_client, key_prefix, loop):
        async def scenario():
            from redis_spi.types import Duration

            with pytest.raises(RedisCommandError):
                await provider_client.set(
                    f"{key_prefix}set-v",
                    b"v",
                    duration=Duration.seconds(10),
                    keep_ttl=True,
                )

        run(loop, scenario())


class TestServerSideCommandErrors:
    @staticmethod
    def test_lset_missing_key_and_out_of_range(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}lset"
            with pytest.raises(RedisCommandError):
                await provider_client.lset(key, 0, b"v")
            await provider_client.rpush(key, b"a")
            with pytest.raises(RedisCommandError):
                await provider_client.lset(key, 5, b"v")

        run(loop, scenario())

    @staticmethod
    def test_hincrby_non_integer_value(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}hincr"
            await provider_client.hset(key, field=b"n", value=b"not-a-number")
            with pytest.raises(RedisCommandError):
                await provider_client.hincr_by(key, b"n", 1)

        run(loop, scenario())


class TestErrorContext:
    @staticmethod
    def test_wrongtype_carries_operation_and_code(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}ctx"
            await provider_client.set(key, b"v")
            try:
                await provider_client.hgetall(key)
            except RedisWrongTypeError as exc:
                assert isinstance(exc, RedisError)
                assert exc.operation, "错误上下文须携带 operation"
                assert exc.code == RedisWrongTypeError.code
            else:
                raise AssertionError("expected RedisWrongTypeError")

        run(loop, scenario())


class TestConnectionErrorMapping:
    @staticmethod
    def test_bad_port_yields_connection_error(loop):
        """坏端口装配 → 连接族 SPI 异常（真实网络后端）；离线后端自动 skip。

        分类学：连接被拒 → RedisConnectionError；连接超时（Windows 防火墙对
        未开放端口常为静默 DROP）→ RedisTimeoutError——两者都是"基础设施错误
        正确翻译"的期望路径。自分类：离线后端（fakeredis/内存替身）不建连，
        坏端口也能装配成功——skip 而非放行。
        """
        target = os.environ.get(TARGET_ENV, "")
        if not target:
            # 无契约目标：默认解析为 native 并真实连接 127.0.0.1:1——对齐
            # conftest "未设置目标时全部 skip" 的承诺，不产生真实建连
            pytest.skip(f"{TARGET_ENV} not set; connection-error mapping needs a real backend")
        settings = RedisProviderSettings(
            REDIS_PROVIDER=target,
            REDIS_MODE="single",
            REDIS_HOST="127.0.0.1",
            REDIS_PORT=1,
            REDIS_CLUSTER_NODES="",
            REDIS_SENTINEL_NODES="",
            REDIS_SOCKET_TIMEOUT=1,
            REDIS_SOCKET_CONNECT_TIMEOUT=1,
        )
        try:
            client = loop.run_until_complete(RedisProviderFactory.create(settings))
        except (RedisConnectionError, RedisTimeoutError):
            return  # 期望路径：连接族/超时类异常，均已翻译为 redis_spi 体系
        except RedisError as exc:
            pytest.fail(
                f"expected RedisConnectionError/RedisTimeoutError, "
                f"got {type(exc).__name__}: {exc}"
            )
        else:
            loop.run_until_complete(client.aclose())
            pytest.skip("target is offline/in-memory (bad-port assembly succeeded)")


class TestCapabilityGuard:
    @staticmethod
    def test_as_capability_unsupported_raises(provider_client):
        """未声明能力组：supports()=False 且 as_capability() 抛 CapabilityNotSupportedError。"""
        probe = CounterCapability  # 任意能力组：各目标声明面不同，按 supports 分支断言
        if provider_client.supports(probe):
            view = provider_client.as_capability(probe)
            assert view is not None
        else:
            with pytest.raises(CapabilityNotSupportedError):
                provider_client.as_capability(probe)

    @staticmethod
    def test_as_capability_unknown_class_raises(provider_client):
        """完全未知的"能力组"（非协议类）：一律 CapabilityNotSupportedError。"""
        with pytest.raises(CapabilityNotSupportedError):
            provider_client.as_capability(dict)
