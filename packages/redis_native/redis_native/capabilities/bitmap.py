# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""BitmapCapability 实现（位图族）。

前置校验（offset/value/bit/操作名/NOT 单 key）统一在调用期抛
RedisCommandError——保证确定性报错（不依赖服务端）且不泄漏原生异常。
"""

from __future__ import annotations

from redis_native.converters import validate_range_paired
from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import Key

#: BITOP 合法操作名。
_BIT_OPS = frozenset({"AND", "OR", "XOR", "NOT"})


class NativeBitmapCapability:
    """位图能力组（redis-py 委托；共享业务命令池与生命周期）。"""

    def __init__(self, redis) -> None:
        self._redis = redis

    @spi_command("setbit")
    async def setbit(self, key: Key, offset: int, value: int) -> int:
        if offset < 0:
            raise RedisCommandError(
                f"setbit offset 必须 >= 0，got {offset}", command="setbit"
            )
        if value not in (0, 1):
            raise RedisCommandError(
                f"setbit value 只能为 0/1，got {value!r}", command="setbit"
            )
        return await self._redis.setbit(key, offset, value)

    @spi_command("getbit")
    async def getbit(self, key: Key, offset: int) -> int:
        return await self._redis.getbit(key, offset)

    @spi_command("bitcount")
    async def bitcount(
        self, key: Key, start: int | None = None, end: int | None = None
    ) -> int:
        # start/end 均 None = 全 key 统计（redis-py 同语义直传）。
        validate_range_paired("bitcount", start, end)
        return await self._redis.bitcount(key, start, end)

    @spi_command("bitpos")
    async def bitpos(
        self, key: Key, bit: int, start: int | None = None, end: int | None = None
    ) -> int:
        if bit not in (0, 1):
            raise RedisCommandError(
                f"bitpos bit 只能为 0/1，got {bit!r}", command="bitpos"
            )
        validate_range_paired("bitpos", start, end)
        return await self._redis.bitpos(key, bit, start, end)

    @spi_command("bitop")
    async def bitop(self, operation: str, destination: Key, *keys: Key) -> int:
        normalized = operation.upper()
        if normalized not in _BIT_OPS:
            raise RedisCommandError(
                f"bitop operation 必须为 {sorted(_BIT_OPS)} 之一，got '{operation}'",
                command="bitop",
            )
        if not keys:
            raise RedisCommandError("bitop 需要至少一个 source key", command="bitop")
        if normalized == "NOT" and len(keys) != 1:
            raise RedisCommandError(
                f"BITOP NOT 仅允许 1 个 source key，got {len(keys)}", command="bitop"
            )
        return await self._redis.bitop(normalized, destination, *keys)
