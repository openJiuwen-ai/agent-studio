# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""HyperLogLogCapability 实现（PF 族）。"""

from __future__ import annotations

from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import Key, Value


class NativeHyperLogLogCapability:
    """HyperLogLog 能力组（redis-py 委托）。"""

    def __init__(self, redis) -> None:
        self._redis = redis

    @spi_command("pfadd")
    async def pfadd(self, key: Key, *elements: Value) -> int:
        if not elements:
            raise RedisCommandError("pfadd 需要至少一个 element", command="pfadd")
        return await self._redis.pfadd(key, *elements)

    @spi_command("pfcount")
    async def pfcount(self, *keys: Key) -> int:
        if not keys:
            raise RedisCommandError("pfcount 需要至少一个 key", command="pfcount")
        return await self._redis.pfcount(*keys)

    @spi_command("pfmerge")
    async def pfmerge(self, destination: Key, *source_keys: Key) -> bool:
        # 空 source 由服务端报错（wrong number of arguments）→ RedisCommandError。
        # 返回值归一 bool：redis-py 对 PFMERGE 的回调形态按版本差异（True/b"OK"）。
        return bool(await self._redis.pfmerge(destination, *source_keys))
