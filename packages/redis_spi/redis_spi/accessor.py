# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""进程级客户端访问器（设计文档 5.4）。

生命周期约定：
  - 启动期（server lifespan / 装配层）调用一次 initialize() 完成装配；
  - 业务代码统一经 get_redis() 取客户端（未初始化 = 装配缺陷，fail-fast 报错，
    不静默回退默认实现）；
  - 全生命周期单例，不支持热切换（重启进程换 Provider）。

线程/协程模型：initialize/await_provider_ready 在**同一事件循环内**可并发
调用（首个装配胜出，其余等待复用同一实例）；跨线程并发 initialize 仍可能
各自建连（后到者被关闭，短暂双池）——跨线程场景由调用方自行串行化，或
装配线程完成后其它线程改用 await_provider_ready；get_redis_or_none/
is_initialized 纯读。
"""

from __future__ import annotations

import asyncio

from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import RedisConfigError, RedisTimeoutError
from redis_spi.factory import RedisProviderFactory
from redis_spi.protocols import RedisClient

#: 轮询间隔（await_provider_ready；仅启动次序等待，不做长阻塞）。
_POLL_INTERVAL_SECONDS = 0.05

_client: RedisClient | None = None


async def initialize(settings: RedisProviderSettings | None = None) -> RedisClient:
    """装配并缓存进程级客户端（幂等：已初始化直接返回既有实例）。

    并发调用时首个装配胜出，其余调用方复用（不重复建连）。
    """
    global _client  # noqa: PLW0603 - 进程级单例
    if _client is not None:
        return _client
    client = await RedisProviderFactory.create(settings)
    if _client is None:
        _client = client
        return _client
    # 并发装配竞争：丢弃后到者，避免泄漏连接。
    await _aclose_quietly(client)
    return _client


def is_initialized() -> bool:
    """是否已装配。"""
    return _client is not None


def get_redis_or_none() -> RedisClient | None:
    """取客户端；未初始化返回 None（可空场景用）。"""
    return _client


def get_redis() -> RedisClient:
    """取客户端；未初始化抛 RedisConfigError（fail-fast，自描述报错）。"""
    if _client is None:
        raise RedisConfigError(
            "Redis 客户端尚未初始化：请在服务启动期调用 "
            "redis_spi.accessor.initialize(settings) 完成装配后再使用"
        )
    return _client


async def await_provider_ready(
    timeout: float | None = None,
    poll_interval: float = _POLL_INTERVAL_SECONDS,
) -> RedisClient:
    """等待装配完成（后台任务先于 lifespan 完成的次序场景）。

    - 已初始化立即返回；
    - timeout 秒内未就绪抛 RedisTimeoutError；timeout=None 无限等待（慎用）。
    """
    if timeout is not None and timeout <= 0:
        raise ValueError(f"timeout must be positive or None, got {timeout}")
    loop = asyncio.get_running_loop()
    deadline = None if timeout is None else loop.time() + timeout
    while _client is None:
        if deadline is not None and loop.time() >= deadline:
            raise RedisTimeoutError(
                f"redis provider not ready within {timeout}s "
                f"(initialize() not called or failed)"
            )
        await asyncio.sleep(poll_interval)
    return _client


async def aclose() -> None:
    """关闭并清空客户端（服务停机 / 测试 teardown）。幂等；关闭异常原样上抛。"""
    global _client  # noqa: PLW0603
    client, _client = _client, None
    if client is not None:
        await client.aclose()


def reset() -> None:
    """仅清空引用不关连接（测试隔离用；生产停机用 aclose）。"""
    global _client  # noqa: PLW0603
    _client = None


async def _aclose_quietly(client: RedisClient) -> None:
    """并发竞争败者的连接回收（异常吞掉：不掩盖胜者路径）。"""
    try:
        await client.aclose()
    except Exception:  # noqa: BLE001
        pass
