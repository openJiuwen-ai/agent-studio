# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""BlockingCommands 实现（独立阻塞连接池）。

阻塞池客户端构建时 socket_timeout=None（见 provider）——socket_timeout
（默认 5s）不得先于 BLPOP/BRPOP 自身超时截断阻塞读。
"""

from __future__ import annotations

from typing import Sequence

from redis_native.converters import blocking_timeout
from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import Duration, Key, Value


class NativeBlockingCapability:
    """阻塞命令能力组（redis-py 委托；持独立阻塞池客户端）。"""

    def __init__(self, redis) -> None:
        self._redis = redis

    @spi_command("blpop")
    async def blpop(
        self, keys: Sequence[Key], timeout: Duration | None = None
    ) -> tuple[Key, Value] | None:
        # 裸 str/bytes 是"单键"惯例（redis-py 原生支持）——直接 list() 会把
        # 字符串拆成单字符键列表，消费方将永远阻塞在错误键上
        if isinstance(keys, (str, bytes)):
            keys = [keys]
        if not keys:
            raise RedisCommandError("blpop 需要至少一个 key", command="blpop")
        return await self._redis.blpop(list(keys), blocking_timeout(timeout))

    @spi_command("brpop")
    async def brpop(
        self, keys: Sequence[Key], timeout: Duration | None = None
    ) -> tuple[Key, Value] | None:
        if isinstance(keys, (str, bytes)):
            keys = [keys]
        if not keys:
            raise RedisCommandError("brpop 需要至少一个 key", command="brpop")
        return await self._redis.brpop(list(keys), blocking_timeout(timeout))

    @spi_command("brpoplpush")
    async def brpoplpush(
        self, source: Key, destination: Key, timeout: Duration | None = None
    ) -> Value | None:
        return await self._redis.brpoplpush(
            source, destination, blocking_timeout(timeout)
        )
