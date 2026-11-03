# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""测试替身：RedisClient / RedisProvider 的 fake 实现。

两个客户端替身：
  - FakeRedisClient：最小生命周期面（工厂/访问器行为测试用）；
  - FullSurfaceFakeClient：**完整核心方法面**（Phase 1 验收点——证明核心协议
    可被第三方 fake 实现：不继承任何平台实现类，仅按协议结构实现全部方法）。
"""

from __future__ import annotations

from typing import Any

from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import CapabilityNotSupportedError
from redis_spi.factory import RedisProvider
from redis_spi.protocols import RedisClient


class FakeRedisClient:
    """最小客户端：只实现生命周期与能力探测面（命令面按需补）。"""

    def __init__(self) -> None:
        self.closed = False
        self.ping_calls = 0
        self.ping_error: BaseException | None = None
        self.ping_result: bool = True

    @property
    def text_mode(self) -> bool:
        return False

    async def ping(self) -> bool:
        self.ping_calls += 1
        if self.ping_error is not None:
            raise self.ping_error
        return self.ping_result

    async def aclose(self) -> None:
        self.closed = True

    @staticmethod
    def supports(capability: type) -> bool:
        return False

    @staticmethod
    def as_capability(capability: type) -> Any:
        raise CapabilityNotSupportedError(
            f"fake client does not support "
            f"{getattr(capability, '__name__', capability)}"
        )


class FakeRedisProvider(RedisProvider):
    """最小 Provider：产出 FakeRedisClient，记录 stop 调用。"""

    def __init__(self) -> None:
        self.stopped = False
        self.start_calls = 0
        self.client: FakeRedisClient | None = None

    async def start(self, settings: RedisProviderSettings) -> RedisClient:
        self.start_calls += 1
        self.client = FakeRedisClient()
        return self.client

    async def stop(self) -> None:
        self.stopped = True


def _stub(*args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("full-surface fake stub")


class FullSurfaceFakeClient:
    """全核心方法面 fake（命令体一律 NotImplementedError——本替身只证明结构可实现）。

    与 FakeRedisClient 的区别：覆盖 RedisClient 协议**全部**核心命令方法，
    isinstance(client, RedisClient) 为 True（runtime_checkable 属性存在性检查通过）。
    语义级实现见 Phase 3 契约套件 / demo provider。
    """

    text_mode = False

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None

    @staticmethod
    def supports(capability: type) -> bool:
        return False

    @staticmethod
    def as_capability(capability: type) -> Any:
        raise CapabilityNotSupportedError(f"not supported: {capability}")

    # ---- KeyCommands ----

    async def exists(self, *keys):
        return _stub()

    async def delete(self, *keys):
        return _stub()

    async def key_type(self, key):
        return _stub()

    async def expire(self, key, duration):
        return _stub()

    async def pexpire(self, key, duration):
        return _stub()

    async def expire_at(self, key, unix_seconds):
        return _stub()

    async def pexpire_at(self, key, unix_milliseconds):
        return _stub()

    async def ttl(self, key):
        return _stub()

    async def pttl(self, key):
        return _stub()

    async def persist(self, key):
        return _stub()

    # ---- StringCommands ----

    async def get(self, key):
        return _stub()

    async def set(self, key, value, *, condition=None, duration=None, keep_ttl=False):
        return _stub()

    async def get_set(self, key, value):
        return _stub()

    async def mget(self, keys):
        return _stub()

    async def mset(self, mapping):
        return _stub()

    async def msetnx(self, mapping):
        return _stub()

    async def append(self, key, value):
        return _stub()

    async def strlen(self, key):
        return _stub()

    async def getrange(self, key, start, end):
        return _stub()

    async def setrange(self, key, offset, value):
        return _stub()

    # ---- HashCommands ----

    async def hset(self, key, mapping=None, *, field=None, value=None):
        return _stub()

    async def hsetnx(self, key, field, value):
        return _stub()

    async def hget(self, key, field):
        return _stub()

    async def hgetall(self, key):
        return _stub()

    async def hmget(self, key, fields):
        return _stub()

    async def hdel(self, key, *fields):
        return _stub()

    async def hexists(self, key, field):
        return _stub()

    async def hlen(self, key):
        return _stub()

    async def hkeys(self, key):
        return _stub()

    async def hvals(self, key):
        return _stub()

    async def hincr_by(self, key, field, amount):
        return _stub()

    async def hincr_by_float(self, key, field, amount):
        return _stub()

    async def hscan(self, key, cursor=0, *, match=None, count=None):
        return _stub()

    # ---- ListCommands ----

    async def rpush(self, key, *values):
        return _stub()

    async def lpush(self, key, *values):
        return _stub()

    async def lpushx(self, key, value):
        return _stub()

    async def rpushx(self, key, value):
        return _stub()

    async def lpop(self, key, count=None):
        return _stub()

    async def rpop(self, key, count=None):
        return _stub()

    async def lrange(self, key, start, stop):
        return _stub()

    async def ltrim(self, key, start, stop):
        return _stub()

    async def llen(self, key):
        return _stub()

    async def lindex(self, key, index):
        return _stub()

    async def lset(self, key, index, value):
        return _stub()

    async def lrem(self, key, count, value):
        return _stub()

    async def rpoplpush(self, source, destination):
        return _stub()

    # ---- SetCommands ----

    async def sadd(self, key, *members):
        return _stub()

    async def srem(self, key, *members):
        return _stub()

    async def smembers(self, key):
        return _stub()

    async def sismember(self, key, member):
        return _stub()

    async def scard(self, key):
        return _stub()

    async def spop(self, key, count=None):
        return _stub()

    async def srandmember(self, key, count=None):
        return _stub()

    async def smove(self, source, destination, member):
        return _stub()

    async def sinter(self, *keys):
        return _stub()

    async def sunion(self, *keys):
        return _stub()

    async def sdiff(self, *keys):
        return _stub()

    async def sinterstore(self, destination, *keys):
        return _stub()

    async def sunionstore(self, destination, *keys):
        return _stub()

    async def sdiffstore(self, destination, *keys):
        return _stub()

    async def sscan(self, key, cursor=0, *, match=None, count=None):
        return _stub()

    # ---- ScanCommands ----

    async def scan(self, cursor=0, *, match=None, count=None, type_name=None):
        return _stub()

    @staticmethod
    def scan_iter(*, match=None, count=None):
        return _stub()

    # ---- PipelineCommands ----

    @staticmethod
    def pipeline(*, transaction=None):
        return _stub()
