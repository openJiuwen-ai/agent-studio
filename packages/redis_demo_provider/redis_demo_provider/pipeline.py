# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Acme demo：Pipeline 句柄（fakeredis pipeline 委托）。"""

from __future__ import annotations

from typing import Any

from redis_demo_provider.converters import (
    duration_to_seconds,
    set_options,
    validate_hset_args,
    validate_set_ttl,
)
from redis_demo_provider.errors import REDIS_PY_ERRORS, acme_translate

from redis_spi.types import Duration, Key, ScanCursor, SetCondition, Value


class AcmeDemoPipeline:
    """SPI Pipeline 协议实现：命令入队（返回 self 链式），execute 一次提交。

    参数校验在**入队期** fail-fast；execute 异常统一翻译为 redis_spi 体系。
    句柄非协程安全：单协程使用。
    """

    def __init__(self, pipe: Any) -> None:
        self._pipe = pipe

    def get(self, key: Key) -> "AcmeDemoPipeline":
        self._pipe.get(key)
        return self

    def set(
        self,
        key: Key,
        value: Value,
        *,
        condition: SetCondition | None = None,
        duration: Duration | None = None,
        keep_ttl: bool = False,
    ) -> "AcmeDemoPipeline":
        validate_set_ttl(duration, keep_ttl)
        self._pipe.set(
            key, value, **set_options(condition=condition, duration=duration, keep_ttl=keep_ttl)
        )
        return self

    def delete(self, *keys: Key) -> "AcmeDemoPipeline":
        self._pipe.delete(*keys)
        return self

    def exists(self, *keys: Key) -> "AcmeDemoPipeline":
        self._pipe.exists(*keys)
        return self

    def expire(self, key: Key, duration: Duration) -> "AcmeDemoPipeline":
        self._pipe.expire(key, duration_to_seconds(duration))
        return self

    def hset(
        self,
        key: Key,
        mapping: dict[Value, Value] | None = None,
        *,
        field: Value | None = None,
        value: Value | None = None,
    ) -> "AcmeDemoPipeline":
        validate_hset_args(mapping, field, value)
        self._pipe.hset(key, mapping=mapping, key=field, value=value)
        return self

    def hget(self, key: Key, field: Value) -> "AcmeDemoPipeline":
        self._pipe.hget(key, field)
        return self

    def hgetall(self, key: Key) -> "AcmeDemoPipeline":
        self._pipe.hgetall(key)
        return self

    def hdel(self, key: Key, *fields: Value) -> "AcmeDemoPipeline":
        self._pipe.hdel(key, *fields)
        return self

    def rpush(self, key: Key, *values: Value) -> "AcmeDemoPipeline":
        self._pipe.rpush(key, *values)
        return self

    def lrange(self, key: Key, start: int, stop: int) -> "AcmeDemoPipeline":
        self._pipe.lrange(key, start, stop)
        return self

    def sadd(self, key: Key, *members: Value) -> "AcmeDemoPipeline":
        self._pipe.sadd(key, *members)
        return self

    def scan(
        self,
        cursor: ScanCursor = 0,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> "AcmeDemoPipeline":
        self._pipe.scan(cursor, match=match, count=count)
        return self

    async def execute(self) -> list:
        try:
            return await self._pipe.execute()
        except REDIS_PY_ERRORS as exc:
            raise acme_translate(exc, operation="pipeline.execute") from exc

    async def aclose(self) -> None:
        await self._pipe.aclose()
