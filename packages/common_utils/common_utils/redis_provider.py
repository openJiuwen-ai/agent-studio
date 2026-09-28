# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Redis 适配层：能力抽象 + 原生默认实现 + Provider 插件化（同步/异步双栈）。

与 Java 侧 studio-common RedisClientProvider SPI 概念对齐，与 Python 侧
password_provider 的自定义加载方式一致（REDIS_PROVIDER_MODULE + _CLASS）：

  - BaseSyncRedisClient / BaseAsyncRedisClient: 能力抽象基类（契约见各方法 docstring）
  - RedisPySyncClient / RedisPyAsyncClient: 原生默认实现（包装 RedisClientManager 的 redis-py 客户端）
  - InMemorySyncRedisClient / InMemoryAsyncRedisClient: 内存实现（测试与 TCK 参考）
  - RedisProvider: Provider SPI；DefaultRedisProvider（"redis"）/ InMemoryRedisProvider（"memory"）
  - get_redis_provider(): Provider 工厂，按 RedisSettings 切换实现

统一契约（同步/异步一致）：
  - key 一律 str；value 一律 bytes（对齐 redis-py decode_responses=False 现状，调用方自行解码）
  - 前置条件：key/name 非 None；TTL 秒数必须为正整数
  - 错误分类：底层客户端异常原样透传（redis.exceptions.RedisError 及其子类），由调用方降级；
    内存实现无网络异常，行为按 Redis 命令语义模拟
"""

from __future__ import annotations

import asyncio
import fnmatch
import importlib
import importlib.util
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Set, Tuple, Union

from common_utils.common_config import RedisSettings
from common_utils.redis_manager import RedisClientManager

try:  # pragma: no cover - 类型提示用途，redis 为必装依赖
    from redis import Redis as SyncRedisPy
    from redis.asyncio import Redis as AsyncRedisPy
    from redis.cluster import RedisCluster as SyncRedisClusterPy
    from redis.asyncio.cluster import RedisCluster as AsyncRedisClusterPy
except ImportError:  # pragma: no cover
    SyncRedisPy = AsyncRedisPy = SyncRedisClusterPy = AsyncRedisClusterPy = object

__all__ = [
    "BaseSyncRedisClient",
    "BaseAsyncRedisClient",
    "RedisPySyncClient",
    "RedisPyAsyncClient",
    "InMemorySyncRedisClient",
    "InMemoryAsyncRedisClient",
    "RedisProvider",
    "DefaultRedisProvider",
    "InMemoryRedisProvider",
    "get_redis_provider",
    "get_provider_sync_client",
    "get_provider_async_client",
]

Value = Union[bytes, str, int, float]


def _to_bytes(value: Value) -> bytes:
    """值统一编码为 bytes（对齐 redis-py decode_responses=False 语义）。"""
    if isinstance(value, bytes):
        return value
    if value is None:
        raise ValueError("value must not be None")
    if isinstance(value, (int, float)):
        return str(value).encode("utf-8")
    return str(value).encode("utf-8")


# --------------------------------------------------------------------------- #
# 能力抽象基类（契约面：以平台实际使用的命令与语义为限）
# --------------------------------------------------------------------------- #
class BaseSyncRedisClient(ABC):
    """同步 Redis 客户端能力抽象（契约见各方法 docstring）。"""

    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """GET：key 不存在返回 None，存在返回 bytes 值。"""

    @abstractmethod
    def set(self, key: str, value: Value, ex: Optional[int] = None) -> bool:
        """SET：value 编码为 bytes 写入；ex 为生存时间秒数（None 表示永不过期）。
        重复 set 覆盖旧值并重置 TTL。"""

    @abstractmethod
    def delete(self, *keys: str) -> int:
        """DEL：返回实际删除的 key 数量，不存在的 key 被忽略。"""

    @abstractmethod
    def exists(self, *keys: str) -> int:
        """EXISTS：返回存在的 key 数量。"""

    @abstractmethod
    def expire(self, key: str, seconds: int) -> bool:
        """EXPIRE：key 不存在返回 False，存在返回 True 并设置生存时间。"""

    @abstractmethod
    def ttl(self, key: str) -> int:
        """TTL：返回剩余生存秒数；key 不存在返回 -2，永不过期返回 -1。"""

    @abstractmethod
    def mget(self, keys: List[str]) -> List[Optional[bytes]]:
        """MGET：按入参顺序返回值列表，不存在的 key 对应 None。"""

    @abstractmethod
    def mset(self, mapping: Mapping[str, Value]) -> bool:
        """MSET：批量写入，全部成功返回 True。"""

    @abstractmethod
    def hset(
        self,
        name: str,
        key: Optional[str] = None,
        value: Optional[Value] = None,
        mapping: Optional[Mapping[str, Value]] = None,
        ex: Optional[int] = None,
    ) -> int:
        """HSET：支持 key/value 或 mapping 两种形式（互斥）；ex 为整个 hash 的生存秒数。
        返回新增 field 数量（redis-py 语义）。"""

    @abstractmethod
    def hget(self, name: str, key: str) -> Optional[bytes]:
        """HGET：field 不存在返回 None。"""

    @abstractmethod
    def hgetall(self, name: str) -> Dict[bytes, bytes]:
        """HGETALL：hash 不存在返回空 dict。"""

    @abstractmethod
    def sadd(self, name: str, *members: Value) -> int:
        """SADD：返回实际新增成员数。"""

    @abstractmethod
    def srem(self, name: str, *members: Value) -> int:
        """SREM：返回实际移除成员数。"""

    @abstractmethod
    def smembers(self, name: str) -> Set[bytes]:
        """SMEMBERS：set 不存在返回空集合。"""

    @abstractmethod
    def rpush(self, name: str, *values: Value, ex: Optional[int] = None) -> int:
        """RPUSH：向列表尾部追加元素，返回追加后列表长度；ex 为列表生存秒数。"""

    @abstractmethod
    def lrange(self, name: str, start: int, end: int) -> List[bytes]:
        """LRANGE：end=-1 表示取到末尾；列表不存在返回空列表。"""

    @abstractmethod
    def llen(self, name: str) -> int:
        """LLEN：列表不存在返回 0。"""

    @abstractmethod
    def scan_iter(self, match: str) -> Iterator[bytes]:
        """SCAN 渐进式遍历（glob 模式匹配），返回匹配 key 的迭代器。"""

    @abstractmethod
    def get_lock(self, name: str, timeout: float = 10.0):
        """获取分布式锁（上下文管理器）：同 name 互斥，timeout 为持锁超时秒数。"""


class BaseAsyncRedisClient(ABC):
    """异步 Redis 客户端能力抽象（契约与同步版一致）。"""

    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """GET：见同步版契约。"""

    @abstractmethod
    async def set(self, key: str, value: Value, ex: Optional[int] = None) -> bool:
        """SET：见同步版契约。"""

    @abstractmethod
    async def delete(self, *keys: str) -> int:
        """DEL：见同步版契约。"""

    @abstractmethod
    async def exists(self, *keys: str) -> int:
        """EXISTS：见同步版契约。"""

    @abstractmethod
    async def expire(self, key: str, seconds: int) -> bool:
        """EXPIRE：见同步版契约。"""

    @abstractmethod
    async def ttl(self, key: str) -> int:
        """TTL：见同步版契约。"""

    @abstractmethod
    async def mget(self, keys: List[str]) -> List[Optional[bytes]]:
        """MGET：见同步版契约。"""

    @abstractmethod
    async def mset(self, mapping: Mapping[str, Value]) -> bool:
        """MSET：见同步版契约。"""

    @abstractmethod
    async def hset(
        self,
        name: str,
        key: Optional[str] = None,
        value: Optional[Value] = None,
        mapping: Optional[Mapping[str, Value]] = None,
        ex: Optional[int] = None,
    ) -> int:
        """HSET：见同步版契约。"""

    @abstractmethod
    async def hget(self, name: str, key: str) -> Optional[bytes]:
        """HGET：见同步版契约。"""

    @abstractmethod
    async def hgetall(self, name: str) -> Dict[bytes, bytes]:
        """HGETALL：见同步版契约。"""

    @abstractmethod
    async def sadd(self, name: str, *members: Value) -> int:
        """SADD：见同步版契约。"""

    @abstractmethod
    async def srem(self, name: str, *members: Value) -> int:
        """SREM：见同步版契约。"""

    @abstractmethod
    async def smembers(self, name: str) -> Set[bytes]:
        """SMEMBERS：见同步版契约。"""

    @abstractmethod
    async def rpush(self, name: str, *values: Value, ex: Optional[int] = None) -> int:
        """RPUSH：见同步版契约。"""

    @abstractmethod
    async def lrange(self, name: str, start: int, end: int) -> List[bytes]:
        """LRANGE：见同步版契约。"""

    @abstractmethod
    async def llen(self, name: str) -> int:
        """LLEN：见同步版契约。"""

    @abstractmethod
    def scan_iter(self, match: str):
        """SCAN：异步迭代器（async for），契约见同步版。"""

    @abstractmethod
    def get_lock(self, name: str, timeout: float = 10.0):
        """获取分布式锁（异步上下文管理器）：契约见同步版。"""


# --------------------------------------------------------------------------- #
# 内存实现（测试与 TCK 参考，Redis 命令语义模拟）
# --------------------------------------------------------------------------- #
class _InMemoryEngine:
    """内存存储引擎：KV（带 TTL）/ hash / set / list，线程安全。"""

    _NEVER = float("inf")

    def __init__(self) -> None:
        self._kv: Dict[str, Tuple[bytes, float]] = {}
        self._hash: Dict[str, Dict[bytes, bytes]] = {}
        self._set: Dict[str, Set[bytes]] = {}
        self._list: Dict[str, List[bytes]] = {}
        # hash / set / list 等结构的过期时刻（KV 结构的过期内嵌在 _kv 中）
        self._struct_expire: Dict[str, float] = {}
        self._lock = threading.RLock()

    # ---- 过期辅助 ----
    def _purge_if_expired(self, key: str) -> None:
        item = self._kv.get(key)
        if item is not None and item[1] <= time.monotonic():
            del self._kv[key]

    def _purge_struct_if_expired(self, name: str) -> None:
        expire_at = self._struct_expire.get(name)
        if expire_at is not None and expire_at <= time.monotonic():
            self._hash.pop(name, None)
            self._set.pop(name, None)
            self._list.pop(name, None)
            del self._struct_expire[name]

    # ---- KV ----
    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            self._purge_if_expired(key)
            item = self._kv.get(key)
            return item[0] if item else None

    def set(self, key: str, value: Value, ex: Optional[int] = None) -> bool:
        expire_at = time.monotonic() + ex if ex else self._NEVER
        with self._lock:
            self._kv[key] = (_to_bytes(value), expire_at)
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        with self._lock:
            for key in keys:
                self._purge_if_expired(key)
                self._purge_struct_if_expired(key)
                removed = False
                if key in self._kv:
                    del self._kv[key]
                    removed = True
                if key in self._hash:
                    del self._hash[key]
                    removed = True
                if key in self._set:
                    del self._set[key]
                    removed = True
                if key in self._list:
                    del self._list[key]
                    removed = True
                if removed:
                    self._struct_expire.pop(key, None)
                    count += 1
        return count

    def exists(self, *keys: str) -> int:
        count = 0
        with self._lock:
            for key in keys:
                self._purge_if_expired(key)
                self._purge_struct_if_expired(key)
                if key in self._kv or key in self._hash or key in self._set or key in self._list:
                    count += 1
        return count

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            self._purge_if_expired(key)
            self._purge_struct_if_expired(key)
            item = self._kv.get(key)
            if item is not None:
                self._kv[key] = (item[0], time.monotonic() + seconds)
                return True
            if key in self._hash or key in self._set or key in self._list:
                self._struct_expire[key] = time.monotonic() + seconds
                return True
            return False

    def ttl(self, key: str) -> int:
        with self._lock:
            self._purge_if_expired(key)
            item = self._kv.get(key)
            if item is None:
                return -2
            if item[1] == self._NEVER:
                return -1
            return max(0, int(item[1] - time.monotonic()))

    def mget(self, keys: List[str]) -> List[Optional[bytes]]:
        return [self.get(key) for key in keys]

    def mset(self, mapping: Mapping[str, Value]) -> bool:
        for key, value in mapping.items():
            self.set(key, value)
        return True

    # ---- hash ----
    def hset(self, name, key=None, value=None, mapping=None, ex=None) -> int:
        if (key is None) == (mapping is None):
            raise ValueError("hset requires either key/value or mapping, not both")
        with self._lock:
            self._purge_struct_if_expired(name)
            fields = self._hash.setdefault(name, {})
            added = 0
            if mapping:
                for field, val in mapping.items():
                    if _to_bytes(field) not in fields:
                        added += 1
                    fields[_to_bytes(field)] = _to_bytes(val)
            else:
                if _to_bytes(key) not in fields:
                    added += 1
                fields[_to_bytes(key)] = _to_bytes(value)
            if ex:
                self._struct_expire[name] = time.monotonic() + ex
        return added

    def hget(self, name: str, key: str) -> Optional[bytes]:
        with self._lock:
            self._purge_struct_if_expired(name)
            return self._hash.get(name, {}).get(_to_bytes(key))

    def hgetall(self, name: str) -> Dict[bytes, bytes]:
        with self._lock:
            self._purge_struct_if_expired(name)
            return dict(self._hash.get(name, {}))

    # ---- set ----
    def sadd(self, name: str, *members: Value) -> int:
        added = 0
        with self._lock:
            self._purge_struct_if_expired(name)
            bucket = self._set.setdefault(name, set())
            for member in members:
                encoded = _to_bytes(member)
                if encoded not in bucket:
                    bucket.add(encoded)
                    added += 1
        return added

    def srem(self, name: str, *members: Value) -> int:
        removed = 0
        with self._lock:
            bucket = self._set.get(name, set())
            for member in members:
                encoded = _to_bytes(member)
                if encoded in bucket:
                    bucket.discard(encoded)
                    removed += 1
        return removed

    def smembers(self, name: str) -> Set[bytes]:
        with self._lock:
            self._purge_struct_if_expired(name)
            return set(self._set.get(name, set()))

    # ---- list ----
    def rpush(self, name: str, *values: Value, ex: Optional[int] = None) -> int:
        with self._lock:
            self._purge_struct_if_expired(name)
            bucket = self._list.setdefault(name, [])
            bucket.extend(_to_bytes(value) for value in values)
            if ex:
                self._struct_expire[name] = time.monotonic() + ex
            return len(bucket)

    def lrange(self, name: str, start: int, end: int) -> List[bytes]:
        with self._lock:
            self._purge_struct_if_expired(name)
            bucket = self._list.get(name, [])
            if not bucket:
                return []
            stop = None if end == -1 else end + 1
            return list(bucket[start:stop])

    def llen(self, name: str) -> int:
        with self._lock:
            self._purge_struct_if_expired(name)
            return len(self._list.get(name, []))

    # ---- scan ----
    def scan_iter(self, match: str) -> Iterator[bytes]:
        with self._lock:
            keys = list(self._kv.keys()) + list(self._hash.keys()) \
                + list(self._set.keys()) + list(self._list.keys())
        for key in keys:
            if fnmatch.fnmatchcase(key, match):
                yield key.encode("utf-8")


class InMemorySyncRedisClient(BaseSyncRedisClient):
    """内存同步客户端（仅用于测试/TCK；与契约语义对齐）。"""

    def __init__(self, engine: Optional[_InMemoryEngine] = None):
        self._engine = engine or _InMemoryEngine()
        self._locks: Dict[str, threading.RLock] = {}

    def get(self, key):  # noqa: D102
        return self._engine.get(key)

    def set(self, key, value, ex=None):  # noqa: D102
        return self._engine.set(key, value, ex)

    def delete(self, *keys):  # noqa: D102
        return self._engine.delete(*keys)

    def exists(self, *keys):  # noqa: D102
        return self._engine.exists(*keys)

    def expire(self, key, seconds):  # noqa: D102
        return self._engine.expire(key, seconds)

    def ttl(self, key):  # noqa: D102
        return self._engine.ttl(key)

    def mget(self, keys):  # noqa: D102
        return self._engine.mget(keys)

    def mset(self, mapping):  # noqa: D102
        return self._engine.mset(mapping)

    def hset(self, name, key=None, value=None, mapping=None, ex=None):  # noqa: D102
        return self._engine.hset(name, key, value, mapping, ex)

    def hget(self, name, key):  # noqa: D102
        return self._engine.hget(name, key)

    def hgetall(self, name):  # noqa: D102
        return self._engine.hgetall(name)

    def sadd(self, name, *members):  # noqa: D102
        return self._engine.sadd(name, *members)

    def srem(self, name, *members):  # noqa: D102
        return self._engine.srem(name, *members)

    def smembers(self, name):  # noqa: D102
        return self._engine.smembers(name)

    def rpush(self, name, *values, ex=None):  # noqa: D102
        return self._engine.rpush(name, *values, ex=ex)

    def lrange(self, name, start, end):  # noqa: D102
        return self._engine.lrange(name, start, end)

    def llen(self, name):  # noqa: D102
        return self._engine.llen(name)

    def scan_iter(self, match):  # noqa: D102
        return self._engine.scan_iter(match)

    def get_lock(self, name, timeout=10.0):  # noqa: D102
        lock = self._locks.setdefault(name, threading.RLock())

        @contextmanager
        def _ctx():
            acquired = lock.acquire(timeout=timeout)
            try:
                if not acquired:
                    raise TimeoutError(f"acquire redis lock '{name}' timeout")
                yield
            finally:
                if acquired:
                    lock.release()

        return _ctx()


class InMemoryAsyncRedisClient(BaseAsyncRedisClient):
    """内存异步客户端（仅用于测试/TCK；与契约语义对齐，异步方法为同步内存引擎的直接包装）。"""

    def __init__(self, engine: Optional[_InMemoryEngine] = None):
        self._sync = InMemorySyncRedisClient(engine)
        self._locks: Dict[str, asyncio.Lock] = {}

    async def get(self, key):  # noqa: D102
        return self._sync.get(key)

    async def set(self, key, value, ex=None):  # noqa: D102
        return self._sync.set(key, value, ex)

    async def delete(self, *keys):  # noqa: D102
        return self._sync.delete(*keys)

    async def exists(self, *keys):  # noqa: D102
        return self._sync.exists(*keys)

    async def expire(self, key, seconds):  # noqa: D102
        return self._sync.expire(key, seconds)

    async def ttl(self, key):  # noqa: D102
        return self._sync.ttl(key)

    async def mget(self, keys):  # noqa: D102
        return self._sync.mget(keys)

    async def mset(self, mapping):  # noqa: D102
        return self._sync.mset(mapping)

    async def hset(self, name, key=None, value=None, mapping=None, ex=None):  # noqa: D102
        return self._sync.hset(name, key, value, mapping, ex)

    async def hget(self, name, key):  # noqa: D102
        return self._sync.hget(name, key)

    async def hgetall(self, name):  # noqa: D102
        return self._sync.hgetall(name)

    async def sadd(self, name, *members):  # noqa: D102
        return self._sync.sadd(name, *members)

    async def srem(self, name, *members):  # noqa: D102
        return self._sync.srem(name, *members)

    async def smembers(self, name):  # noqa: D102
        return self._sync.smembers(name)

    async def rpush(self, name, *values, ex=None):  # noqa: D102
        return self._sync.rpush(name, *values, ex=ex)

    async def lrange(self, name, start, end):  # noqa: D102
        return self._sync.lrange(name, start, end)

    async def llen(self, name):  # noqa: D102
        return self._sync.llen(name)

    def scan_iter(self, match):  # noqa: D102
        return self._async_scan_iter(match)

    async def _async_scan_iter(self, match: str):
        for key in self._sync.scan_iter(match):
            yield key

    def get_lock(self, name, timeout=10.0):  # noqa: D102
        lock = self._locks.setdefault(name, asyncio.Lock())

        class _AsyncLockCtx:
            def __init__(self, lock_, timeout_):
                self._lock = lock_
                self._timeout = timeout_
                self._acquired = False

            async def __aenter__(self):
                try:
                    self._acquired = await asyncio.wait_for(self._lock.acquire(), self._timeout)
                except asyncio.TimeoutError as exc:
                    raise TimeoutError(f"acquire redis lock '{name}' timeout") from exc
                return self

            async def __aexit__(self, exc_type, exc, tb):
                if self._acquired:
                    self._lock.release()
                return False

        return _AsyncLockCtx(lock, timeout)


# --------------------------------------------------------------------------- #
# 原生默认实现（包装 RedisClientManager 的 redis-py 客户端，零行为变更）
# --------------------------------------------------------------------------- #
class RedisPySyncClient(BaseSyncRedisClient):
    """默认同步实现：委托 RedisClientManager 管理的 redis-py 同步客户端。"""

    def __init__(self, client):
        self._client = client

    def get(self, key):  # noqa: D102
        return self._client.get(key)

    def set(self, key, value, ex=None):  # noqa: D102
        return self._client.set(key, value, ex=ex)

    def delete(self, *keys):  # noqa: D102
        return self._client.delete(*keys)

    def exists(self, *keys):  # noqa: D102
        return self._client.exists(*keys)

    def expire(self, key, seconds):  # noqa: D102
        return self._client.expire(key, seconds)

    def ttl(self, key):  # noqa: D102
        return self._client.ttl(key)

    def mget(self, keys):  # noqa: D102
        return self._client.mget(keys)

    def mset(self, mapping):  # noqa: D102
        return self._client.mset(mapping)

    def hset(self, name, key=None, value=None, mapping=None, ex=None):  # noqa: D102
        if key is None and mapping is None:
            raise ValueError("hset requires either key/value or mapping")
        result = self._client.hset(name, key=key, value=value, mapping=mapping)
        if ex is not None:
            self._client.expire(name, ex)
        return result

    def hget(self, name, key):  # noqa: D102
        return self._client.hget(name, key)

    def hgetall(self, name):  # noqa: D102
        return self._client.hgetall(name)

    def sadd(self, name, *members):  # noqa: D102
        return self._client.sadd(name, *members)

    def srem(self, name, *members):  # noqa: D102
        return self._client.srem(name, *members)

    def smembers(self, name):  # noqa: D102
        return self._client.smembers(name)

    def rpush(self, name, *values, ex=None):  # noqa: D102
        result = self._client.rpush(name, *values)
        if ex is not None:
            self._client.expire(name, ex)
        return result

    def lrange(self, name, start, end):  # noqa: D102
        return self._client.lrange(name, start, end)

    def llen(self, name):  # noqa: D102
        return self._client.llen(name)

    def scan_iter(self, match):  # noqa: D102
        return self._client.scan_iter(match=match)

    def get_lock(self, name, timeout=10.0):  # noqa: D102
        return self._client.lock(name, timeout=timeout)


class RedisPyAsyncClient(BaseAsyncRedisClient):
    """默认异步实现：委托 RedisClientManager 管理的 redis-py 异步客户端。"""

    def __init__(self, client):
        self._client = client

    async def get(self, key):  # noqa: D102
        return await self._client.get(key)

    async def set(self, key, value, ex=None):  # noqa: D102
        return await self._client.set(key, value, ex=ex)

    async def delete(self, *keys):  # noqa: D102
        return await self._client.delete(*keys)

    async def exists(self, *keys):  # noqa: D102
        return await self._client.exists(*keys)

    async def expire(self, key, seconds):  # noqa: D102
        return await self._client.expire(key, seconds)

    async def ttl(self, key):  # noqa: D102
        return await self._client.ttl(key)

    async def mget(self, keys):  # noqa: D102
        return await self._client.mget(keys)

    async def mset(self, mapping):  # noqa: D102
        return await self._client.mset(mapping)

    async def hset(self, name, key=None, value=None, mapping=None, ex=None):  # noqa: D102
        if key is None and mapping is None:
            raise ValueError("hset requires either key/value or mapping")
        result = await self._client.hset(name, key=key, value=value, mapping=mapping)
        if ex is not None:
            await self._client.expire(name, ex)
        return result

    async def hget(self, name, key):  # noqa: D102
        return await self._client.hget(name, key)

    async def hgetall(self, name):  # noqa: D102
        return await self._client.hgetall(name)

    async def sadd(self, name, *members):  # noqa: D102
        return await self._client.sadd(name, *members)

    async def srem(self, name, *members):  # noqa: D102
        return await self._client.srem(name, *members)

    async def smembers(self, name):  # noqa: D102
        return await self._client.smembers(name)

    async def rpush(self, name, *values, ex=None):  # noqa: D102
        result = await self._client.rpush(name, *values)
        if ex is not None:
            await self._client.expire(name, ex)
        return result

    async def lrange(self, name, start, end):  # noqa: D102
        return await self._client.lrange(name, start, end)

    async def llen(self, name):  # noqa: D102
        return await self._client.llen(name)

    def scan_iter(self, match):  # noqa: D102
        return self._client.scan_iter(match=match)

    def get_lock(self, name, timeout=10.0):  # noqa: D102
        return self._client.lock(name, timeout=timeout)


# --------------------------------------------------------------------------- #
# Provider SPI
# --------------------------------------------------------------------------- #
class RedisProvider(ABC):
    """Redis Provider 插件接口（Redis 适配层 SPI）。

    企业自研 Redis 通过实现本接口接入平台，无需修改框架源码。
    实现要求：
      - name() 返回全局唯一标识（内置 "redis" / "memory" 不可复用）
      - create_sync_client / create_async_client 返回的客户端必须满足
        BaseSyncRedisClient / BaseAsyncRedisClient 的完整契约，
        并通过 common_utils 测试中的一致性测试套件（TCK）自验证
      - 实现必须线程安全；客户端生命周期由实现方管理（建议惰性连接）
      - 底层异常原样透传，由调用方降级
    """

    @abstractmethod
    def name(self) -> str:
        """Provider 全局唯一标识（用于 REDIS_PROVIDER_TYPE 配置匹配）。"""

    @abstractmethod
    def create_sync_client(self, settings: RedisSettings) -> BaseSyncRedisClient:
        """创建同步客户端。"""

    @abstractmethod
    def create_async_client(self, settings: RedisSettings) -> BaseAsyncRedisClient:
        """创建异步客户端。"""


class DefaultRedisProvider(RedisProvider):
    """默认 Provider：包装 RedisClientManager（redis-py，单机/集群/哨兵）。"""

    NAME = "redis"

    def name(self) -> str:  # noqa: D102
        return self.NAME

    def _ensure_manager(self, settings: Optional[RedisSettings]) -> RedisClientManager:
        manager = RedisClientManager.get_instance()
        if not manager.is_initialized:
            manager.init(settings)
        return manager

    def create_sync_client(self, settings: RedisSettings) -> BaseSyncRedisClient:  # noqa: D102
        manager = self._ensure_manager(settings)
        return RedisPySyncClient(manager.get_sync_client())

    def create_async_client(self, settings: RedisSettings) -> BaseAsyncRedisClient:  # noqa: D102
        manager = self._ensure_manager(settings)
        return RedisPyAsyncClient(manager.get_client())


class InMemoryRedisProvider(RedisProvider):
    """内存 Provider（仅用于测试/TCK）。"""

    NAME = "memory"

    def __init__(self):
        self._engine = _InMemoryEngine()

    def name(self) -> str:  # noqa: D102
        return self.NAME

    def create_sync_client(self, settings: RedisSettings) -> BaseSyncRedisClient:  # noqa: D102
        return InMemorySyncRedisClient(self._engine)

    def create_async_client(self, settings: RedisSettings) -> BaseAsyncRedisClient:  # noqa: D102
        return InMemoryAsyncRedisClient(self._engine)


_BUILTIN_PROVIDERS = {
    DefaultRedisProvider.NAME: DefaultRedisProvider,
    InMemoryRedisProvider.NAME: InMemoryRedisProvider,
}


def _load_custom_provider(module_path: str, class_name: str) -> RedisProvider:
    """通过 importlib 动态加载自定义 Redis Provider（与 password_provider 加载约定一致）。

    Args:
        module_path: Python 模块路径或 .py 文件路径
            - 文件路径：/opt/plugins/custom_redis_provider（自动加 .py 后缀）
            - 模块名：my_package.custom_provider（需已安装到 site-packages）
        class_name: 实现类名（必须继承 RedisProvider）

    Returns:
        RedisProvider 实例
    """
    p = Path(module_path)
    try:
        py_path = p if p.suffix == ".py" else p.with_suffix(".py")
        if py_path.exists() and py_path.is_file():
            spec = importlib.util.spec_from_file_location(py_path.stem, str(py_path))
            if spec is None:
                raise ImportError(f"Cannot load module spec from: {py_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            module = importlib.import_module(module_path)
    except Exception as e:
        raise ImportError(
            f"Failed to load custom redis provider module '{module_path}': {e}"
        ) from e

    cls = getattr(module, class_name, None)
    if cls is None:
        raise AttributeError(f"Class '{class_name}' not found in module '{module_path}'")

    if not (isinstance(cls, type) and issubclass(cls, RedisProvider)):
        raise TypeError(f"Class '{class_name}' does not inherit from RedisProvider")

    try:
        return cls()
    except Exception as e:
        raise RuntimeError(
            f"Failed to instantiate custom redis provider '{class_name}': {e}"
        ) from e


def get_redis_provider(settings: Optional[RedisSettings] = None) -> RedisProvider:
    """按配置解析 Redis Provider。

    解析优先级：
      1. REDIS_PROVIDER_MODULE + REDIS_PROVIDER_CLASS（自定义插件，显式指定时优先）
      2. REDIS_PROVIDER_TYPE（内置注册表按名匹配："redis" / "memory"）
      3. 默认 "redis"（redis-py 原生实现）

    Raises:
        ImportError / AttributeError / TypeError / RuntimeError: 自定义 Provider 加载失败（报错含原因）
        ValueError: REDIS_PROVIDER_TYPE 未注册
    """
    if settings is None:
        settings = RedisSettings()

    if settings.provider_module or settings.provider_class:
        if not settings.provider_module:
            raise ValueError(
                "REDIS_PROVIDER_MODULE is required when REDIS_PROVIDER_CLASS is specified"
            )
        if not settings.provider_class:
            raise ValueError(
                "REDIS_PROVIDER_CLASS is required when REDIS_PROVIDER_MODULE is specified"
            )
        return _load_custom_provider(settings.provider_module, settings.provider_class)

    provider_type = (settings.provider_type or DefaultRedisProvider.NAME).strip().lower()
    if provider_type in _BUILTIN_PROVIDERS:
        return _BUILTIN_PROVIDERS[provider_type]()

    raise ValueError(
        f"Unknown redis provider type: '{provider_type}', "
        f"available: {sorted(_BUILTIN_PROVIDERS)}. "
        "Check REDIS_PROVIDER_TYPE or set REDIS_PROVIDER_MODULE/_CLASS for custom providers."
    )


def get_provider_sync_client(settings: Optional[RedisSettings] = None) -> BaseSyncRedisClient:
    """获取当前 Provider 的同步客户端（便捷入口）。"""
    provider = get_redis_provider(settings)
    return provider.create_sync_client(settings or RedisSettings())


def get_provider_async_client(settings: Optional[RedisSettings] = None) -> BaseAsyncRedisClient:
    """获取当前 Provider 的异步客户端（便捷入口）。"""
    provider = get_redis_provider(settings)
    return provider.create_async_client(settings or RedisSettings())
