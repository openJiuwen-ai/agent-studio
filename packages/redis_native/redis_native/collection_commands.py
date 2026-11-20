# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""集合命令实现（HashCommands / ListCommands / SetCommands 委托 mixin）。

翻译要点：
  - HSET：mapping 与 field/value 二选一校验（入队期 fail-fast，防 DataError 泄漏）；
  - HSCAN：redis-py HScanPayload 为 dict | list（RESP2/RESP3 双形态），
    list 时自行配对为 dict；
  - SPOP：redis-py count 形态返回 set（8.x 实测），直接透传；
  - SRANDMEMBER：count<0 允许重复（Redis 语义），redis-py 原生支持；
  - 集合运算族（sinter/sunion/sdiff/store）：varargs 直传，同槽约束归服务端
    （CROSSSLOT → RedisClusterError）。

Mixin 依赖宿主属性：``self._redis``。
"""

from __future__ import annotations

from typing import Any

from redis_native.converters import validate_hset_args
from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import (
    SCAN_START,
    Key,
    ScanCursor,
    Value,
)


class HashCommandsMixin:
    """HashCommands 协议实现。"""

    @spi_command("hset")
    async def hset(
        self,
        key: Key,
        mapping: dict[Value, Value] | None = None,
        *,
        field: Value | None = None,
        value: Value | None = None,
    ) -> int:
        validate_hset_args(mapping, field, value)
        return await self._redis.hset(  # type: ignore[attr-defined]
            key, mapping=mapping, key=field, value=value
        )

    @spi_command("hsetnx")
    async def hsetnx(self, key: Key, field: Value, value: Value) -> bool:
        # redis-py 8.1 对 HSETNX 无 bool 响应回调（返回 int 0/1）——契约要求 bool，显式归一。
        return bool(await self._redis.hsetnx(key, field, value))  # type: ignore[attr-defined]

    @spi_command("hget")
    async def hget(self, key: Key, field: Value) -> Value | None:
        return await self._redis.hget(key, field)  # type: ignore[attr-defined]

    @spi_command("hgetall")
    async def hgetall(self, key: Key) -> dict[Value, Value]:
        return await self._redis.hgetall(key)  # type: ignore[attr-defined]

    @spi_command("hmget")
    async def hmget(self, key: Key, fields: list[Value]) -> list[Value | None]:
        return await self._redis.hmget(key, fields)  # type: ignore[attr-defined]

    @spi_command("hdel")
    async def hdel(self, key: Key, *fields: Value) -> int:
        return await self._redis.hdel(key, *fields)  # type: ignore[attr-defined]

    @spi_command("hexists")
    async def hexists(self, key: Key, field: Value) -> bool:
        return await self._redis.hexists(key, field)  # type: ignore[attr-defined]

    @spi_command("hlen")
    async def hlen(self, key: Key) -> int:
        return await self._redis.hlen(key)  # type: ignore[attr-defined]

    @spi_command("hkeys")
    async def hkeys(self, key: Key) -> list[Value]:
        return await self._redis.hkeys(key)  # type: ignore[attr-defined]

    @spi_command("hvals")
    async def hvals(self, key: Key) -> list[Value]:
        return await self._redis.hvals(key)  # type: ignore[attr-defined]

    @spi_command("hincr_by")
    async def hincr_by(self, key: Key, field: Value, amount: int) -> int:
        return await self._redis.hincrby(key, field, amount)  # type: ignore[attr-defined]

    @spi_command("hincr_by_float")
    async def hincr_by_float(self, key: Key, field: Value, amount: float) -> float:
        return await self._redis.hincrbyfloat(key, field, amount)  # type: ignore[attr-defined]

    @spi_command("hscan")
    async def hscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, dict[Value, Value]]:
        cursor, payload = await self._redis.hscan(  # type: ignore[attr-defined]
            key, cursor=cursor, match=match, count=count
        )
        return cursor, _pairs_to_dict(payload)


class ListCommandsMixin:
    """ListCommands 协议实现。"""

    @spi_command("rpush")
    async def rpush(self, key: Key, *values: Value) -> int:
        if not values:
            raise RedisCommandError("rpush 需要至少一个 value", command="rpush")
        return await self._redis.rpush(key, *values)  # type: ignore[attr-defined]

    @spi_command("lpush")
    async def lpush(self, key: Key, *values: Value) -> int:
        if not values:
            raise RedisCommandError("lpush 需要至少一个 value", command="lpush")
        return await self._redis.lpush(key, *values)  # type: ignore[attr-defined]

    @spi_command("lpushx")
    async def lpushx(self, key: Key, value: Value) -> int:
        return await self._redis.lpushx(key, value)  # type: ignore[attr-defined]

    @spi_command("rpushx")
    async def rpushx(self, key: Key, value: Value) -> int:
        return await self._redis.rpushx(key, value)  # type: ignore[attr-defined]

    @spi_command("lpop")
    async def lpop(self, key: Key, count: int | None = None) -> Value | list[Value] | None:
        return await self._redis.lpop(key, count)  # type: ignore[attr-defined]

    @spi_command("rpop")
    async def rpop(self, key: Key, count: int | None = None) -> Value | list[Value] | None:
        return await self._redis.rpop(key, count)  # type: ignore[attr-defined]

    @spi_command("lrange")
    async def lrange(self, key: Key, start: int, stop: int) -> list[Value]:
        return await self._redis.lrange(key, start, stop)  # type: ignore[attr-defined]

    @spi_command("ltrim")
    async def ltrim(self, key: Key, start: int, stop: int) -> None:
        await self._redis.ltrim(key, start, stop)  # type: ignore[attr-defined]

    @spi_command("llen")
    async def llen(self, key: Key) -> int:
        return await self._redis.llen(key)  # type: ignore[attr-defined]

    @spi_command("lindex")
    async def lindex(self, key: Key, index: int) -> Value | None:
        return await self._redis.lindex(key, index)  # type: ignore[attr-defined]

    @spi_command("lset")
    async def lset(self, key: Key, index: int, value: Value) -> None:
        # key 不存在/索引越界由服务端报错 → RedisCommandError
        await self._redis.lset(key, index, value)  # type: ignore[attr-defined]

    @spi_command("lrem")
    async def lrem(self, key: Key, count: int, value: Value) -> int:
        return await self._redis.lrem(key, count, value)  # type: ignore[attr-defined]

    @spi_command("rpoplpush")
    async def rpoplpush(self, source: Key, destination: Key) -> Value | None:
        return await self._redis.rpoplpush(source, destination)  # type: ignore[attr-defined]


class SetCommandsMixin:
    """SetCommands 协议实现。"""

    @spi_command("sadd")
    async def sadd(self, key: Key, *members: Value) -> int:
        if not members:
            raise RedisCommandError("sadd 需要至少一个 member", command="sadd")
        return await self._redis.sadd(key, *members)  # type: ignore[attr-defined]

    @spi_command("srem")
    async def srem(self, key: Key, *members: Value) -> int:
        return await self._redis.srem(key, *members)  # type: ignore[attr-defined]

    @spi_command("smembers")
    async def smembers(self, key: Key) -> set[Value]:
        return await self._redis.smembers(key)  # type: ignore[attr-defined]

    @spi_command("sismember")
    async def sismember(self, key: Key, member: Value) -> bool:
        # redis-py 8.1 对 SISMEMBER 无 bool 响应回调（返回 int 0/1）——契约要求 bool，显式归一。
        return bool(await self._redis.sismember(key, member))  # type: ignore[attr-defined]

    @spi_command("scard")
    async def scard(self, key: Key) -> int:
        return await self._redis.scard(key)  # type: ignore[attr-defined]

    @spi_command("spop")
    async def spop(self, key: Key, count: int | None = None) -> Value | set[Value] | None:
        return await self._redis.spop(key, count)  # type: ignore[attr-defined]

    @spi_command("srandmember")
    async def srandmember(
        self, key: Key, count: int | None = None
    ) -> Value | list[Value] | None:
        return await self._redis.srandmember(key, count)  # type: ignore[attr-defined]

    @spi_command("smove")
    async def smove(self, source: Key, destination: Key, member: Value) -> bool:
        return await self._redis.smove(source, destination, member)  # type: ignore[attr-defined]

    @spi_command("sinter")
    async def sinter(self, *keys: Key) -> set[Value]:
        if not keys:
            raise RedisCommandError("sinter 需要至少一个 key", command="sinter")
        return await self._redis.sinter(*keys)  # type: ignore[attr-defined]

    @spi_command("sunion")
    async def sunion(self, *keys: Key) -> set[Value]:
        if not keys:
            raise RedisCommandError("sunion 需要至少一个 key", command="sunion")
        return await self._redis.sunion(*keys)  # type: ignore[attr-defined]

    @spi_command("sdiff")
    async def sdiff(self, *keys: Key) -> set[Value]:
        if not keys:
            raise RedisCommandError("sdiff 需要至少一个 key", command="sdiff")
        return await self._redis.sdiff(*keys)  # type: ignore[attr-defined]

    @spi_command("sinterstore")
    async def sinterstore(self, destination: Key, *keys: Key) -> int:
        return await self._redis.sinterstore(destination, *keys)  # type: ignore[attr-defined]

    @spi_command("sunionstore")
    async def sunionstore(self, destination: Key, *keys: Key) -> int:
        return await self._redis.sunionstore(destination, *keys)  # type: ignore[attr-defined]

    @spi_command("sdiffstore")
    async def sdiffstore(self, destination: Key, *keys: Key) -> int:
        return await self._redis.sdiffstore(destination, *keys)  # type: ignore[attr-defined]

    @spi_command("sscan")
    async def sscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, list[Value]]:
        cursor, items = await self._redis.sscan(  # type: ignore[attr-defined]
            key, cursor=cursor, match=match, count=count
        )
        return cursor, list(items)


def _pairs_to_dict(payload: Any) -> dict:
    """HScanPayload 归一：RESP3 list 形态自行配对为 dict（RESP2 已是 dict）。"""
    if isinstance(payload, dict):
        return payload
    result: dict = {}
    it = iter(payload)
    for field, value in zip(it, it):
        result[field] = value
    return result
