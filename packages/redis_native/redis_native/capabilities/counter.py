# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""CounterCapability 实现（INCR/DECR 族）。

计数命令为非幂等写：超时后**结果未知**——``timeout_result_known=False``
使 RedisTimeoutError(result_known=False)，禁止调用方盲重试（nos 契约）。
"""

from __future__ import annotations

from redis_native.error_mapping import spi_command

from redis_spi.types import Key


class NativeCounterCapability:
    """计数器能力组（redis-py 委托；与客户端共享业务命令池与生命周期）。"""

    def __init__(self, redis) -> None:
        self._redis = redis

    @spi_command("incr", timeout_result_known=False)
    async def incr(self, key: Key, amount: int = 1) -> int:
        return await self._redis.incr(key, amount)

    @spi_command("incr_by_float", timeout_result_known=False)
    async def incr_by_float(self, key: Key, amount: float) -> float:
        return await self._redis.incrbyfloat(key, amount)

    @spi_command("decr", timeout_result_known=False)
    async def decr(self, key: Key, amount: int = 1) -> int:
        return await self._redis.decr(key, amount)
