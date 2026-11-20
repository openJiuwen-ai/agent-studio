# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""AcmeDemoClient：SPI 核心协议 + PubSub + Blocking 的一体实现（demo 形态一）。

企业实现参考（这就是"用你的 SDK 实现一个 Provider 客户端"的完整样板）：
  - 底层 SDK：fakeredis（redis-py 兼容）——企业替换为自研中间件 SDK；
  - 全部方法按 redis_spi.protocols 契约实现：参数校验 fail-fast、异常在
    边界翻译（errors.py）、返回值按哨兵语义归一（bool/None/-1/-2）；
  - 能力声明：核心 + PubSub + Blocking（框架业务路径的完整依赖面）——
    未声明的能力组调用即 CapabilityNotSupportedError，契约套件按声明自动
    skip（"实现多少声明多少"的可测试口径）。
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Sequence

from redis_demo_provider.converters import (
    blocking_timeout,
    duration_to_seconds,
    set_options,
    validate_hset_args,
    validate_set_ttl,
)
from redis_demo_provider.errors import acme_command
from redis_demo_provider.pipeline import AcmeDemoPipeline
from redis_demo_provider.pubsub import AcmePubSubHandle

from redis_spi.capabilities import BlockingCommands, PubSubCapability
from redis_spi.exceptions import CapabilityNotSupportedError, RedisCommandError
from redis_spi.types import (
    SCAN_START,
    Duration,
    Key,
    ScanBatch,
    ScanCursor,
    SetCondition,
    Value,
)

#: 本实现声明的能力组（核心面之外）。
SUPPORTED_CAPABILITIES = frozenset({PubSubCapability, BlockingCommands})

_OK_BYTES = b"OK"
_OK_TEXT = "OK"


class AcmeDemoClient:
    """核心面聚合实现（结构化满足 redis_spi.protocols.RedisClient）。"""

    def __init__(
        self,
        redis_client: Any,
        *,
        text_mode: bool = False,
        transaction_default: bool = True,
    ) -> None:
        self._redis = redis_client
        self._text_mode = text_mode
        self._transaction_default = transaction_default
        self._closed = False

    # --------------------------------- 生命周期与能力探测（RedisClient 协议）

    @property
    def text_mode(self) -> bool:
        return self._text_mode

    @staticmethod
    def supports(capability: type) -> bool:
        return capability in SUPPORTED_CAPABILITIES

    def as_capability(self, capability: type) -> Any:
        if capability in SUPPORTED_CAPABILITIES:
            # 一体实现：客户端自身即能力视图（共享连接池与生命周期）。
            return self
        raise CapabilityNotSupportedError(
            f"acme demo provider 未实现能力组 "
            f"{getattr(capability, '__name__', capability)}（核心 + PubSub + Blocking 之外）",
            capability=capability,
        )

    @acme_command("ping")
    async def ping(self) -> bool:
        return await self._redis.ping()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._redis.aclose()

    # ---------------------------------------------------------------- Key 命令

    @acme_command("exists")
    async def exists(self, *keys: Key) -> int:
        if not keys:
            raise RedisCommandError("exists 需要至少一个 key", command="exists")
        return await self._redis.exists(*keys)

    @acme_command("delete")
    async def delete(self, *keys: Key) -> int:
        return await self._redis.delete(*keys)

    @acme_command("key_type")
    async def key_type(self, key: Key) -> Value:
        return await self._redis.type(key)

    @acme_command("expire")
    async def expire(self, key: Key, duration: Duration) -> bool:
        return await self._redis.expire(key, duration_to_seconds(duration))

    @acme_command("pexpire")
    async def pexpire(self, key: Key, duration: Duration) -> bool:
        return await self._redis.pexpire(key, duration.milliseconds)

    @acme_command("expire_at")
    async def expire_at(self, key: Key, unix_seconds: int) -> bool:
        return await self._redis.expireat(key, unix_seconds)

    @acme_command("pexpire_at")
    async def pexpire_at(self, key: Key, unix_milliseconds: int) -> bool:
        return await self._redis.pexpireat(key, unix_milliseconds)

    @acme_command("ttl")
    async def ttl(self, key: Key) -> int:
        return await self._redis.ttl(key)

    @acme_command("pttl")
    async def pttl(self, key: Key) -> int:
        return await self._redis.pttl(key)

    @acme_command("persist")
    async def persist(self, key: Key) -> bool:
        return await self._redis.persist(key)

    # ---------------------------------------------------------------- String

    @acme_command("get")
    async def get(self, key: Key) -> Value | None:
        return await self._redis.get(key)

    @acme_command("set")
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
        result = await self._redis.set(
            key,
            value,
            **set_options(condition=condition, duration=duration, keep_ttl=keep_ttl),
        )
        if not result:
            return None  # NX/XX 不满足
        return _OK_TEXT if self._text_mode else _OK_BYTES

    @acme_command("get_set")
    async def get_set(self, key: Key, value: Value) -> Value | None:
        return await self._redis.getset(key, value)

    @acme_command("mget")
    async def mget(self, keys: list[Key]) -> list[Value | None]:
        return await self._redis.mget(keys)

    @acme_command("mset")
    async def mset(self, mapping: dict[Key, Value]) -> None:
        await self._redis.mset(mapping)

    @acme_command("msetnx")
    async def msetnx(self, mapping: dict[Key, Value]) -> bool:
        return await self._redis.msetnx(mapping)

    @acme_command("append")
    async def append(self, key: Key, value: Value) -> int:
        return await self._redis.append(key, value)

    @acme_command("strlen")
    async def strlen(self, key: Key) -> int:
        return await self._redis.strlen(key)

    @acme_command("getrange")
    async def getrange(self, key: Key, start: int, end: int) -> Value:
        return await self._redis.getrange(key, start, end)

    @acme_command("setrange")
    async def setrange(self, key: Key, offset: int, value: Value) -> int:
        if offset < 0:
            raise RedisCommandError(
                f"setrange offset 必须 >= 0，got {offset}", command="setrange"
            )
        return await self._redis.setrange(key, offset, value)

    # ---------------------------------------------------------------- Hash

    @acme_command("hset")
    async def hset(
        self,
        key: Key,
        mapping: dict[Value, Value] | None = None,
        *,
        field: Value | None = None,
        value: Value | None = None,
    ) -> int:
        validate_hset_args(mapping, field, value)
        return await self._redis.hset(key, mapping=mapping, key=field, value=value)

    @acme_command("hsetnx")
    async def hsetnx(self, key: Key, field: Value, value: Value) -> bool:
        # redis-py 无 HSETNX bool 回调（int 0/1）——契约要求 bool，显式归一。
        return bool(await self._redis.hsetnx(key, field, value))

    @acme_command("hget")
    async def hget(self, key: Key, field: Value) -> Value | None:
        return await self._redis.hget(key, field)

    @acme_command("hgetall")
    async def hgetall(self, key: Key) -> dict[Value, Value]:
        return await self._redis.hgetall(key)

    @acme_command("hmget")
    async def hmget(self, key: Key, fields: list[Value]) -> list[Value | None]:
        return await self._redis.hmget(key, fields)

    @acme_command("hdel")
    async def hdel(self, key: Key, *fields: Value) -> int:
        return await self._redis.hdel(key, *fields)

    @acme_command("hexists")
    async def hexists(self, key: Key, field: Value) -> bool:
        return await self._redis.hexists(key, field)

    @acme_command("hlen")
    async def hlen(self, key: Key) -> int:
        return await self._redis.hlen(key)

    @acme_command("hkeys")
    async def hkeys(self, key: Key) -> list[Value]:
        return await self._redis.hkeys(key)

    @acme_command("hvals")
    async def hvals(self, key: Key) -> list[Value]:
        return await self._redis.hvals(key)

    @acme_command("hincr_by")
    async def hincr_by(self, key: Key, field: Value, amount: int) -> int:
        return await self._redis.hincrby(key, field, amount)

    @acme_command("hincr_by_float")
    async def hincr_by_float(self, key: Key, field: Value, amount: float) -> float:
        return await self._redis.hincrbyfloat(key, field, amount)

    @acme_command("hscan")
    async def hscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, dict[Value, Value]]:
        cursor, payload = await self._redis.hscan(
            key, cursor=cursor, match=match, count=count
        )
        return cursor, _pairs_to_dict(payload)

    # ---------------------------------------------------------------- List

    @acme_command("rpush")
    async def rpush(self, key: Key, *values: Value) -> int:
        if not values:
            raise RedisCommandError("rpush 需要至少一个 value", command="rpush")
        return await self._redis.rpush(key, *values)

    @acme_command("lpush")
    async def lpush(self, key: Key, *values: Value) -> int:
        if not values:
            raise RedisCommandError("lpush 需要至少一个 value", command="lpush")
        return await self._redis.lpush(key, *values)

    @acme_command("lpushx")
    async def lpushx(self, key: Key, value: Value) -> int:
        return await self._redis.lpushx(key, value)

    @acme_command("rpushx")
    async def rpushx(self, key: Key, value: Value) -> int:
        return await self._redis.rpushx(key, value)

    @acme_command("lpop")
    async def lpop(self, key: Key, count: int | None = None) -> Value | list[Value] | None:
        return await self._redis.lpop(key, count)

    @acme_command("rpop")
    async def rpop(self, key: Key, count: int | None = None) -> Value | list[Value] | None:
        return await self._redis.rpop(key, count)

    @acme_command("lrange")
    async def lrange(self, key: Key, start: int, stop: int) -> list[Value]:
        return await self._redis.lrange(key, start, stop)

    @acme_command("ltrim")
    async def ltrim(self, key: Key, start: int, stop: int) -> None:
        await self._redis.ltrim(key, start, stop)

    @acme_command("llen")
    async def llen(self, key: Key) -> int:
        return await self._redis.llen(key)

    @acme_command("lindex")
    async def lindex(self, key: Key, index: int) -> Value | None:
        return await self._redis.lindex(key, index)

    @acme_command("lset")
    async def lset(self, key: Key, index: int, value: Value) -> None:
        await self._redis.lset(key, index, value)

    @acme_command("lrem")
    async def lrem(self, key: Key, count: int, value: Value) -> int:
        return await self._redis.lrem(key, count, value)

    @acme_command("rpoplpush")
    async def rpoplpush(self, source: Key, destination: Key) -> Value | None:
        return await self._redis.rpoplpush(source, destination)

    # ---------------------------------------------------------------- Set

    @acme_command("sadd")
    async def sadd(self, key: Key, *members: Value) -> int:
        if not members:
            raise RedisCommandError("sadd 需要至少一个 member", command="sadd")
        return await self._redis.sadd(key, *members)

    @acme_command("srem")
    async def srem(self, key: Key, *members: Value) -> int:
        return await self._redis.srem(key, *members)

    @acme_command("smembers")
    async def smembers(self, key: Key) -> set[Value]:
        return await self._redis.smembers(key)

    @acme_command("sismember")
    async def sismember(self, key: Key, member: Value) -> bool:
        # redis-py 无 SISMEMBER bool 回调（int 0/1）——契约要求 bool，显式归一。
        return bool(await self._redis.sismember(key, member))

    @acme_command("scard")
    async def scard(self, key: Key) -> int:
        return await self._redis.scard(key)

    @acme_command("spop")
    async def spop(self, key: Key, count: int | None = None) -> Value | set[Value] | None:
        return await self._redis.spop(key, count)

    @acme_command("srandmember")
    async def srandmember(
        self, key: Key, count: int | None = None
    ) -> Value | list[Value] | None:
        return await self._redis.srandmember(key, count)

    @acme_command("smove")
    async def smove(self, source: Key, destination: Key, member: Value) -> bool:
        return await self._redis.smove(source, destination, member)

    @acme_command("sinter")
    async def sinter(self, *keys: Key) -> set[Value]:
        if not keys:
            raise RedisCommandError("sinter 需要至少一个 key", command="sinter")
        return await self._redis.sinter(*keys)

    @acme_command("sunion")
    async def sunion(self, *keys: Key) -> set[Value]:
        if not keys:
            raise RedisCommandError("sunion 需要至少一个 key", command="sunion")
        return await self._redis.sunion(*keys)

    @acme_command("sdiff")
    async def sdiff(self, *keys: Key) -> set[Value]:
        if not keys:
            raise RedisCommandError("sdiff 需要至少一个 key", command="sdiff")
        return await self._redis.sdiff(*keys)

    @acme_command("sinterstore")
    async def sinterstore(self, destination: Key, *keys: Key) -> int:
        return await self._redis.sinterstore(destination, *keys)

    @acme_command("sunionstore")
    async def sunionstore(self, destination: Key, *keys: Key) -> int:
        return await self._redis.sunionstore(destination, *keys)

    @acme_command("sdiffstore")
    async def sdiffstore(self, destination: Key, *keys: Key) -> int:
        return await self._redis.sdiffstore(destination, *keys)

    @acme_command("sscan")
    async def sscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, list[Value]]:
        cursor, items = await self._redis.sscan(
            key, cursor=cursor, match=match, count=count
        )
        return cursor, list(items)

    # ---------------------------------------------------------------- Scan

    @acme_command("scan")
    async def scan(
        self,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
        type_name=None,
    ) -> ScanBatch:
        next_cursor, items = await self._redis.scan(
            cursor, match=match, count=count, _type=type_name
        )
        return ScanBatch(cursor=next_cursor, items=items)

    def scan_iter(
        self,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> AsyncIterator[Key]:
        return self._redis.scan_iter(match=match, count=count)

    # ---------------------------------------------------------------- Pipeline

    def pipeline(self, *, transaction: bool | None = None) -> AcmeDemoPipeline:
        resolved = self._transaction_default if transaction is None else transaction
        return AcmeDemoPipeline(self._redis.pipeline(transaction=resolved))

    # --------------------------------- 能力组：PubSub（订阅/publish）

    def pubsub(self) -> AcmePubSubHandle:
        """订阅句柄（demo 单 SDK 实例内共享；企业按自研 SDK 的独立连接要求拆分）。"""
        return AcmePubSubHandle(self._redis.pubsub())

    @acme_command("publish")
    async def publish(self, channel: Value, message: Value) -> int:
        return await self._redis.publish(channel, message)

    # --------------------------------- 能力组：Blocking（BLPOP 族）

    @acme_command("blpop")
    async def blpop(
        self, keys: Sequence[Key], timeout: Duration | None = None
    ) -> tuple[Key, Value] | None:
        if not keys:
            raise RedisCommandError("blpop 需要至少一个 key", command="blpop")
        return await self._redis.blpop(list(keys), blocking_timeout(timeout))

    @acme_command("brpop")
    async def brpop(
        self, keys: Sequence[Key], timeout: Duration | None = None
    ) -> tuple[Key, Value] | None:
        if not keys:
            raise RedisCommandError("brpop 需要至少一个 key", command="brpop")
        return await self._redis.brpop(list(keys), blocking_timeout(timeout))

    @acme_command("brpoplpush")
    async def brpoplpush(
        self,
        source: Key,
        destination: Key,
        timeout: Duration | None = None,
    ) -> Value | None:
        return await self._redis.brpoplpush(
            source, destination, blocking_timeout(timeout)
        )


def _pairs_to_dict(payload: Any) -> dict:
    """HScanPayload 归一：RESP3 list 形态自行配对为 dict。"""
    if isinstance(payload, dict):
        return payload
    result: dict = {}
    it = iter(payload)
    for field, value in zip(it, it):
        result[field] = value
    return result
