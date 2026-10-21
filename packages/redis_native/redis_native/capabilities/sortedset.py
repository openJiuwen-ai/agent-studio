# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SortedSetCapability 实现（ZSET 族）。"""

from __future__ import annotations

from typing import Any, Sequence

from redis_native.converters import condition_options
from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import (
    SCAN_START,
    Key,
    ScanCursor,
    ScoreBoundary,
    SetCondition,
    Value,
)

#: ZUNIONSTORE/ZINTERSTORE 合法聚合策略。
_AGGREGATES = frozenset({"SUM", "MIN", "MAX"})


class NativeSortedSetCapability:
    """有序集合能力组（redis-py 委托）。"""

    def __init__(self, redis) -> None:
        self._redis = redis

    @spi_command("zadd")
    async def zadd(
        self,
        key: Key,
        mapping: dict[Value, float],
        *,
        condition: SetCondition | None = None,
    ) -> int:
        return await self._redis.zadd(key, mapping, **condition_options(condition))

    @spi_command("zrem")
    async def zrem(self, key: Key, *members: Value) -> int:
        return await self._redis.zrem(key, *members)

    @spi_command("zscore")
    async def zscore(self, key: Key, member: Value) -> float | None:
        return await self._redis.zscore(key, member)

    @spi_command("zcard")
    async def zcard(self, key: Key) -> int:
        return await self._redis.zcard(key)

    @spi_command("zrank")
    async def zrank(self, key: Key, member: Value) -> int | None:
        return await self._redis.zrank(key, member)

    @spi_command("zrevrank")
    async def zrevrank(self, key: Key, member: Value) -> int | None:
        return await self._redis.zrevrank(key, member)

    @spi_command("zincrby")
    async def zincrby(self, key: Key, amount: float, member: Value) -> float:
        return await self._redis.zincrby(key, amount, member)

    @spi_command("zcount")
    async def zcount(self, key: Key, min_value, max_value) -> int:
        return await self._redis.zcount(key, min_value, max_value)

    @spi_command("zlexcount")
    async def zlexcount(self, key: Key, min_value, max_value) -> int:
        return await self._redis.zlexcount(key, min_value, max_value)

    @spi_command("zrange")
    async def zrange(
        self,
        key: Key,
        start: int,
        stop: int,
        *,
        withscores: bool = False,
        desc: bool = False,
    ) -> list[Value] | list[tuple[Value, float]]:
        return await self._redis.zrange(
            key, start, stop, desc=desc, withscores=withscores
        )

    @spi_command("zrangebyscore")
    async def zrangebyscore(
        self,
        key: Key,
        min_value,
        max_value,
        *,
        withscores: bool = False,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Value] | list[tuple[Value, float]]:
        # redis-py 要求 start/num 成对（单给 start 抛 DataError）：
        # 无分页时不传这对参数；offset 缺省 0，limit 单给 = 取前 limit 个。
        pagination = {} if limit is None else {"start": offset, "num": limit}
        return await self._redis.zrangebyscore(
            key,
            min_value,
            max_value,
            withscores=withscores,
            **pagination,
        )

    @spi_command("zrangebylex")
    async def zrangebylex(
        self,
        key: Key,
        min_value,
        max_value,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Value]:
        pagination = {} if limit is None else {"start": offset, "num": limit}
        return await self._redis.zrangebylex(key, min_value, max_value, **pagination)

    @spi_command("zremrangebyrank")
    async def zremrangebyrank(self, key: Key, start: int, stop: int) -> int:
        return await self._redis.zremrangebyrank(key, start, stop)

    @spi_command("zremrangebyscore")
    async def zremrangebyscore(
        self, key: Key, min_value, max_value
    ) -> int:
        return await self._redis.zremrangebyscore(key, min_value, max_value)

    @spi_command("zremrangebylex")
    async def zremrangebylex(
        self, key: Key, min_value, max_value
    ) -> int:
        return await self._redis.zremrangebylex(key, min_value, max_value)

    @spi_command("zunionstore")
    async def zunionstore(
        self,
        destination: Key,
        keys: Sequence[Key],
        *,
        aggregate: str | None = None,
    ) -> int:
        return await self._redis.zunionstore(
            destination, list(keys), aggregate=_normalize_aggregate(aggregate)
        )

    @spi_command("zinterstore")
    async def zinterstore(
        self,
        destination: Key,
        keys: Sequence[Key],
        *,
        aggregate: str | None = None,
    ) -> int:
        return await self._redis.zinterstore(
            destination, list(keys), aggregate=_normalize_aggregate(aggregate)
        )

    @spi_command("zscan")
    async def zscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, list[tuple[Value, float]]]:
        cursor, pairs = await self._redis.zscan(
            key, cursor=cursor, match=match, count=count
        )
        # ZScanPair 为 tuple | list 双形态（RESP 版本差异），统一为 (member, float)。
        return cursor, [(member, _to_score(score)) for member, score in pairs]


def _to_score(score: Any) -> float:
    """ZSCAN score 归一（float/str/bytes → float；不可解析收口为命令错误）。"""
    try:
        if isinstance(score, bytes):
            return float(score.decode("ascii"))
        return float(score)
    except (TypeError, ValueError) as exc:
        raise RedisCommandError(
            f"zscan 返回了无法解析的 score：{score!r}", command="zscan"
        ) from exc


def _normalize_aggregate(aggregate: str | None) -> str | None:
    """聚合策略归一（大小写不敏感；默认 SUM 由服务端处理）。"""
    if aggregate is None:
        return None
    normalized = aggregate.upper()
    if normalized not in _AGGREGATES:
        raise RedisCommandError(
            f"aggregate 必须为 {sorted(_AGGREGATES)} 之一，got '{aggregate}'",
            command="zunionstore",
        )
    return normalized
