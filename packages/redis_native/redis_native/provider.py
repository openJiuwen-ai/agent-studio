# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""NativeRedisProvider：builtin 保留实现 ``native``（redis-py 直连）。

装配（设计文档 §4.3 独立池约定）：
  - single/sentinel：业务主池 + 订阅独立池 + 阻塞独立池（三个客户端实例）；
  - cluster：共享主池（redis-py cluster 自带节点级连接管理，另建实例的代价
    是重复拓扑发现）——Phase 4 复评；
  - 阻塞池客户端 ``socket_timeout=None``：socket_timeout（默认 5s）不得
    先于 BLPOP 自身超时截断阻塞读。

惰性建连：start 仅构建客户端对象（redis-py 首命令才实际建连）——与
``common_utils.redis_manager.init()`` 行为对齐（启动期不强制 Redis 可达，
由工厂装配后的 ping 首检兜底）。
"""

from __future__ import annotations

from typing import Any

from redis_native.capabilities import SUPPORTED_CAPABILITIES
from redis_native.client import NativeRedisClient
from redis_native.connection import build_async_client, should_use_independent_pool
from redis_native.error_mapping import REDIS_PY_ERRORS, translate_error

from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import RedisConfigError
from redis_spi.factory import RedisProvider
from redis_spi.protocols import RedisClient


class NativeRedisProvider(RedisProvider):
    """redis-py 直连 Provider（REDIS_PROVIDER=native / 缺省时启用）。"""

    def __init__(self) -> None:
        self._client: NativeRedisClient | None = None
        self._underlying: list[Any] = []

    async def start(self, settings: RedisProviderSettings) -> RedisClient:
        # 二次调用守卫：静默覆盖会泄漏旧连接池（旧 client/underlying 被
        # 引用替换后无人关闭）——幂等返回既有客户端，语义与 stop 后重启一致
        if self._client is not None and self._underlying:
            return self._client
        main = build_async_client(settings)
        underlying = [main]
        subscriber = blocking = None
        if should_use_independent_pool(settings):
            subscriber = build_async_client(
                settings, max_connections=settings.subscriber_pool_size
            )
            blocking = build_async_client(
                settings,
                max_connections=settings.blocking_pool_size,
                socket_timeout=None,
            )
            underlying.extend((subscriber, blocking))
        self._client = NativeRedisClient(
            main,
            subscriber=subscriber,
            blocking=blocking,
            text_mode=settings.text_mode,
            transaction_default=settings.redis_transaction_enabled,
        )
        self._underlying = underlying
        return self._client

    async def stop(self) -> None:
        underlying, self._underlying = self._underlying, []
        self._client = None
        failures: list[BaseException] = []
        for client in underlying:
            try:
                await client.aclose()
            except REDIS_PY_ERRORS as exc:
                failures.append(exc)
        if failures:
            # 全部尝试关闭后抛首个（与 NativeRedisClient.aclose 口径一致）。
            raise translate_error(failures[0], operation="stop") from failures[0]

    def capabilities(self) -> list[type]:
        return list(SUPPORTED_CAPABILITIES)

    def native_client(self) -> Any:
        """过渡期兼容视图（Q3）：真实 redis-py 客户端（主池）。"""
        if self._client is None:
            raise RedisConfigError(
                "native provider 尚未启动（native_client 须在 start 之后调用）"
            )
        return self._client.native_client()
