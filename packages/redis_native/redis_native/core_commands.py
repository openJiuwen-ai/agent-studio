# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""核心命令实现（KeyCommands / StringCommands / ScanCommands 委托 mixin）。

翻译要点（与 redis-py 8.x 签名逐条核对）：
  - SET：redis-py 返回 True/None → SPI 契约返回 b"OK"/"OK"（text_mode）或 None；
  - TTL：Duration 走 px（毫秒精度）；EXPIRE 族按命令名走秒/毫秒（自研代理
    命令白名单场景保持命令保真）；
  - SCAN：SPI ``type`` 参数映射 redis-py ``_type``（避开关键字遮蔽）；
  - 空参校验（exists/rpush/lpush/sadd）在调用期抛 RedisCommandError，
    防止 redis-py DataError 泄漏。

Mixin 依赖宿主属性：``self._redis``（redis-py 客户端）、``self._text_mode``。
"""

from __future__ import annotations

from typing import AsyncIterator

from redis_native.converters import (
    duration_to_seconds,
    set_options,
    validate_set_ttl,
)
from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import (
    SCAN_START,
    Duration,
    Key,
    ScanBatch,
    ScanCursor,
    SetCondition,
    Value,
)

#: SET 成功返回值（bytes 模式；text_mode 为 "OK"）。
_OK_BYTES = b"OK"
_OK_TEXT = "OK"


class KeyCommandsMixin:
    """KeyCommands 协议实现。"""

    @spi_command("exists")
    async def exists(self, *keys: Key) -> int:
        if not keys:
            raise RedisCommandError("exists 需要至少一个 key", command="exists")
        return await self._redis.exists(*keys)  # type: ignore[attr-defined]

    @spi_command("delete")
    async def delete(self, *keys: Key) -> int:
        return await self._redis.delete(*keys)  # type: ignore[attr-defined]

    @spi_command("key_type")
    async def key_type(self, key: Key) -> Value:
        return await self._redis.type(key)  # type: ignore[attr-defined]

    @spi_command("expire")
    async def expire(self, key: Key, duration: Duration) -> bool:
        return await self._redis.expire(key, duration_to_seconds(duration))  # type: ignore[attr-defined]

    @spi_command("pexpire")
    async def pexpire(self, key: Key, duration: Duration) -> bool:
        return await self._redis.pexpire(key, duration.milliseconds)  # type: ignore[attr-defined]

    @spi_command("expire_at")
    async def expire_at(self, key: Key, unix_seconds: int) -> bool:
        return await self._redis.expireat(key, unix_seconds)  # type: ignore[attr-defined]

    @spi_command("pexpire_at")
    async def pexpire_at(self, key: Key, unix_milliseconds: int) -> bool:
        return await self._redis.pexpireat(key, unix_milliseconds)  # type: ignore[attr-defined]

    @spi_command("ttl")
    async def ttl(self, key: Key) -> int:
        return await self._redis.ttl(key)  # type: ignore[attr-defined]

    @spi_command("pttl")
    async def pttl(self, key: Key) -> int:
        return await self._redis.pttl(key)  # type: ignore[attr-defined]

    @spi_command("persist")
    async def persist(self, key: Key) -> bool:
        return await self._redis.persist(key)  # type: ignore[attr-defined]


class StringCommandsMixin:
    """StringCommands 协议实现。"""

    @spi_command("get")
    async def get(self, key: Key) -> Value | None:
        return await self._redis.get(key)  # type: ignore[attr-defined]

    @spi_command("set")
    async def set(
        self,
        key: Key,
        value: Value,
        *,
        condition: SetCondition | None = None,
        duration: Duration | None = None,
        keep_ttl: bool = False,
    ) -> Value | None:
        validate_set_ttl(duration, keep_ttl)
        result = await self._redis.set(  # type: ignore[attr-defined]
            key,
            value,
            **set_options(condition=condition, duration=duration, keep_ttl=keep_ttl),
        )
        if not result:
            # NX/XX 不满足时 redis-py 返回 None；契约：条件不满足 → None。
            return None
        return _OK_TEXT if self._text_mode else _OK_BYTES

    @spi_command("get_set")
    async def get_set(self, key: Key, value: Value) -> Value | None:
        return await self._redis.getset(key, value)  # type: ignore[attr-defined]

    @spi_command("mget")
    async def mget(self, keys: list[Key]) -> list[Value | None]:
        return await self._redis.mget(keys)  # type: ignore[attr-defined]

    @spi_command("mset")
    async def mset(self, mapping: dict[Key, Value]) -> None:
        await self._redis.mset(mapping)  # type: ignore[attr-defined]

    @spi_command("msetnx")
    async def msetnx(self, mapping: dict[Key, Value]) -> bool:
        return await self._redis.msetnx(mapping)  # type: ignore[attr-defined]

    @spi_command("append")
    async def append(self, key: Key, value: Value) -> int:
        return await self._redis.append(key, value)  # type: ignore[attr-defined]

    @spi_command("strlen")
    async def strlen(self, key: Key) -> int:
        return await self._redis.strlen(key)  # type: ignore[attr-defined]

    @spi_command("getrange")
    async def getrange(self, key: Key, start: int, end: int) -> Value:
        return await self._redis.getrange(key, start, end)  # type: ignore[attr-defined]

    @spi_command("setrange")
    async def setrange(self, key: Key, offset: int, value: Value) -> int:
        if offset < 0:
            raise RedisCommandError(
                f"setrange offset 必须 >= 0，got {offset}", command="setrange"
            )
        return await self._redis.setrange(key, offset, value)  # type: ignore[attr-defined]


class ScanCommandsMixin:
    """ScanCommands 协议实现。"""

    @spi_command("scan")
    async def scan(
        self,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
        type_name=None,
    ) -> ScanBatch:
        # SPI ``type`` → redis-py ``_type``（参数名遮蔽内建/关键字）。
        next_cursor, items = await self._redis.scan(  # type: ignore[attr-defined]
            cursor, match=match, count=count, _type=type_name
        )
        return ScanBatch(cursor=next_cursor, items=items)

    def scan_iter(
        self,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> AsyncIterator[Key]:
        """直接返回 redis-py 异步生成器（弱一致语义与去重责任在调用方）。"""
        return self._redis.scan_iter(match=match, count=count)  # type: ignore[attr-defined]
