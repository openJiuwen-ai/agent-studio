# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""委托层替身：redis-py 方法签名对齐的内存客户端（手写，非 fakeredis）。

用途（设计文档 §七 后端 4）：以本替身构造 ``NativeRedisClient``，跑同一套
核心契约——**零外部依赖**回归 redis_native 的"SPI 语义 → redis-py 调用"翻译
链路（CI 默认执行；fakeredis 后端另由 redis_demo_provider 提供）。

保真口径——替身模拟的是 **redis-py 客户端**（即 NativeRedisClient 实际对话的
对象），不是 Redis 服务端：
  - 返回值取 redis-py **响应回调之后**的形态（EXPIRE/PERSIST/MSETNX → bool；
    HSETNX/SISMEMBER 无回调 → int 0/1，与 redis-py 8.1 实测一致）；
  - 错误抛 redis-py 异常（``redis.exceptions.ResponseError`` 等，WRONGTYPE 以
    消息前缀区分），由 redis_native.error_mapping 翻译为 redis_spi 异常——
    这正是委托层替身要检验的链路；
  - 仅实现核心命令面（Key/String/Hash/List/Set/Scan/Pipeline）；能力组命令
    （PubSub/Blocking/Lua 等）不实现，由 stub_backend 声明核心面限定。

已声明的简化（不影响核心契约语义）：
  - pipeline 的 transaction=True/False 同为顺序重放（真实 MULTI/EXEC 的
    交错隔离不做模拟）；
  - SCAN 游标为"过滤后列表的下标"（真实服务端为不透明整数；契约只要求
    终点为 0、遍历完整，下标游标满足该不变量）；
  - 过期为惰性判定（访问时清理，无后台线程）。
"""

from __future__ import annotations

import fnmatch
import random
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple

import redis.exceptions as redis_exc

#: SCAN/SSCAN/HSCAN 未给 count 时的单批大小（刻意取小值强制多批返回，
#: 检验调用方"循环到游标 0"的契约行为）。
_SCAN_PAGE = 3


def _enc(value: Any) -> bytes:
    """str → UTF-8 bytes（redis-py 连接层编码语义；bytes 原样）。"""
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def _wrongtype() -> redis_exc.ResponseError:
    """WRONGTYPE 服务端错误（消息前缀与真实 Redis 一致，供翻译层识别）。"""
    return redis_exc.ResponseError(
        "WRONGTYPE Operation against a key holding the wrong kind of value"
    )


def _slice_inclusive(value: bytes, start: int, end: int) -> bytes:
    """闭区间字节切片（GETRANGE 语义：负索引、end 含端点）。"""
    n = len(value)
    if n == 0:
        return b""
    if start < 0:
        start = max(0, n + start)
    if end < 0:
        end = n + end
    end = min(end, n - 1)
    if start > end:
        return b""
    return value[start:end + 1]


def _slice_inclusive_list(container: List[bytes], start: int, stop: int) -> List[bytes]:
    """闭区间列表切片（LRANGE/LTRIM 语义）。"""
    n = len(container)
    if n == 0:
        return []
    if start < 0:
        start = max(0, n + start)
    if stop < 0:
        stop = n + stop
    stop = min(stop, n - 1)
    if start > stop:
        return []
    return container[start:stop + 1]


class StubPipeline:
    """redis-py pipeline 替身：命令同步入队（返回 self 支持链式），execute 重放。

    重放按入队顺序逐条调用宿主 stub 的异步命令方法；任一命令抛错即中止并
    上抛（对齐 redis-py execute() 抛首个错误的观察行为）。
    """

    def __init__(self, stub: "InMemoryRedisPyStub", *, transaction: bool = True) -> None:
        self._stub = stub
        self._ops: List[Tuple[str, tuple, dict]] = []
        self._transaction = transaction

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        def enqueue(*args: Any, **kwargs: Any) -> "StubPipeline":
            self._ops.append((name, args, kwargs))
            return self

        return enqueue

    async def execute(self) -> list:
        # redis-py 语义：整批执行后才抛首个错误（错误前已入队命令照常
        # 执行）——与 native/真实后端一致，首错即中止会掩盖后续命令回归
        results: list = []
        first_error: Optional[BaseException] = None
        for name, args, kwargs in self._ops:
            method = getattr(self._stub, name)
            try:
                results.append(await method(*args, **kwargs))
            except Exception as exc:  # noqa: BLE001
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error
        return results

    async def aclose(self) -> None:
        return None


class InMemoryRedisPyStub:
    """内存版 redis-py 异步客户端替身（核心命令面）。

    存储模型：四类容器字典 + 过期表（惰性清理）。str 入参一律按 UTF-8 编码；
    返回值默认 bytes 形态（decode_responses=False 口径）。
    """

    def __init__(self) -> None:
        self._strings: Dict[bytes, bytes] = {}
        self._hashes: Dict[bytes, Dict[bytes, bytes]] = {}
        self._lists: Dict[bytes, List[bytes]] = {}
        self._sets: Dict[bytes, Set[bytes]] = {}
        self._expiry: Dict[bytes, float] = {}  # key → 截止时刻（Unix 毫秒）
        self._closed = False

    # ---------------------------------------------------------------- 生命周期

    async def ping(self) -> bool:
        return True

    async def aclose(self, **kwargs: Any) -> None:
        self._closed = True

    def pipeline(self, transaction: bool = True, **kwargs: Any) -> StubPipeline:
        return StubPipeline(self, transaction=transaction)

    # ---------------------------------------------------------------- 内部守卫

    @staticmethod
    def _now_ms() -> float:
        return time.time() * 1000

    def _kind_of(self, key: bytes) -> Optional[str]:
        """容器类型：string/hash/list/set；不存在为 None（不做过期清理）。"""
        if key in self._strings:
            return "string"
        if key in self._hashes:
            return "hash"
        if key in self._lists:
            return "list"
        if key in self._sets:
            return "set"
        return None

    def _purge(self, key: bytes) -> bool:
        """惰性过期：到期即删。返回 key 是否仍存在（任意类型）。"""
        deadline = self._expiry.get(key)
        if deadline is not None and self._now_ms() >= deadline:
            self._delete_key(key)
            return False
        return self._kind_of(key) is not None

    def _delete_key(self, key: bytes) -> None:
        self._strings.pop(key, None)
        self._hashes.pop(key, None)
        self._lists.pop(key, None)
        self._sets.pop(key, None)
        self._expiry.pop(key, None)

    def _store_of(self, kind: str) -> Dict[bytes, Any]:
        return {
            "string": self._strings,
            "hash": self._hashes,
            "list": self._lists,
            "set": self._sets,
        }[kind]

    def _container(self, key: bytes, kind: str, *, create: bool = False) -> Any:
        """取 hash/list/set 容器；缺失按 create 决定新建或返回 None；类型不符抛 WRONGTYPE。"""
        alive = self._purge(key)
        actual = self._kind_of(key) if alive else None
        if actual is None:
            if not create:
                return None
            fresh: Any = {} if kind == "hash" else ([] if kind == "list" else set())
            self._store_of(kind)[key] = fresh
            return fresh
        if actual != kind:
            raise _wrongtype()
        return self._store_of(kind)[key]

    def _string_bytes(self, key: bytes) -> Optional[bytes]:
        """string 值；非 string 既有 key 抛 WRONGTYPE；缺失返回 None。"""
        if self._purge(key):
            kind = self._kind_of(key)
            if kind == "string":
                return self._strings[key]
            if kind is not None:
                raise _wrongtype()
        return None

    def _alive_keys(self) -> List[bytes]:
        """全部存活 key（先做一轮惰性过期清理；排序保证游标稳定）。"""
        for key in list(self._expiry):
            self._purge(key)
        keys: Set[bytes] = set()
        keys.update(self._strings)
        keys.update(self._hashes)
        keys.update(self._lists)
        keys.update(self._sets)
        return sorted(keys)

    @staticmethod
    def _match(pattern: Optional[Any], value: bytes) -> bool:
        """glob 匹配（match=None 全通过；Redis 通配与 fnmatch 语义一致）。"""
        if pattern is None:
            return True
        text = value.decode("utf-8", errors="replace")
        pat = _enc(pattern).decode("utf-8", errors="replace")
        return fnmatch.fnmatchcase(text, pat)

    # ---------------------------------------------------------------- Key 命令

    async def exists(self, *keys: Any) -> int:
        return sum(1 for key in keys if self._purge(_enc(key)))

    async def delete(self, *keys: Any) -> int:
        removed = 0
        for key in keys:
            key = _enc(key)
            if self._purge(key):
                self._delete_key(key)
                removed += 1
        return removed

    async def type(self, key: Any) -> bytes:
        key = _enc(key)
        if not self._purge(key):
            return b"none"
        return self._kind_of(key).encode("ascii")  # type: ignore[union-attr]

    async def expire(self, key: Any, seconds: Any) -> bool:
        return self._set_deadline(_enc(key), seconds * 1000)

    async def pexpire(self, key: Any, milliseconds: Any) -> bool:
        return self._set_deadline(_enc(key), milliseconds)

    async def expireat(self, key: Any, unix_seconds: Any) -> bool:
        return self._set_deadline(_enc(key), unix_seconds * 1000, absolute=True)

    async def pexpireat(self, key: Any, unix_milliseconds: Any) -> bool:
        return self._set_deadline(_enc(key), unix_milliseconds, absolute=True)

    async def ttl(self, key: Any) -> int:
        key = _enc(key)
        if not self._purge(key):
            return -2
        deadline = self._expiry.get(key)
        if deadline is None:
            return -1
        remaining_ms = deadline - self._now_ms()
        # 与服务端一致：剩余秒数向上取整（不足 1s 仍报 1）。
        return max(1, -(-int(remaining_ms) // 1000))

    async def pttl(self, key: Any) -> int:
        key = _enc(key)
        if not self._purge(key):
            return -2
        deadline = self._expiry.get(key)
        if deadline is None:
            return -1
        return max(0, int(deadline - self._now_ms()))

    async def persist(self, key: Any) -> bool:
        key = _enc(key)
        if not self._purge(key):
            return False
        return self._expiry.pop(key, None) is not None

    def _set_deadline(self, key: bytes, value: Any, *, absolute: bool = False) -> bool:
        if not self._purge(key):
            return False
        deadline = float(value) if absolute else self._now_ms() + float(value)
        self._expiry[key] = deadline
        return True

    # ---------------------------------------------------------------- String

    async def get(self, key: Any) -> Optional[bytes]:
        return self._string_bytes(_enc(key))

    async def set(
        self,
        key: Any,
        value: Any,
        nx: bool = False,
        xx: bool = False,
        **kwargs: Any,
    ) -> Optional[bool]:
        # redis-py 完整签名的 px / ex / keepttl 经 kwargs 承接（契约 stub
        # 需接纳调用方按上游任意参数形态传参）——显式参数收敛至门禁
        # 上限（G.FMT.03 计 5 含 self），语义不变。
        px = kwargs.get("px")
        ex = kwargs.get("ex")
        keepttl = bool(kwargs.get("keepttl", False))
        key, value = _enc(key), _enc(value)
        old_deadline = self._expiry.get(key)
        exists = self._purge(key)
        if nx and exists:
            return None
        if xx and not exists:
            return None
        # SET 覆盖任意旧类型（Redis 语义：SET 不做 WRONGTYPE 检查）。
        self._delete_key(key)
        self._strings[key] = value
        if px is not None:
            self._expiry[key] = self._now_ms() + int(px)
        elif ex is not None:
            self._expiry[key] = self._now_ms() + int(ex) * 1000
        elif keepttl and old_deadline is not None:
            # KEEPTTL：保留覆写前的既有 TTL。
            self._expiry[key] = old_deadline
        return True

    async def getset(self, key: Any, value: Any) -> Optional[bytes]:
        old = await self.get(key)
        await self.set(key, value)
        return old

    async def mget(self, keys: Any) -> List[Optional[bytes]]:
        result: List[Optional[bytes]] = []
        for key in keys:
            key = _enc(key)
            # MGET 对非 string 的既有 key 返回 nil（不报 WRONGTYPE，Redis 语义）。
            if self._purge(key) and self._kind_of(key) == "string":
                result.append(self._strings[key])
            else:
                result.append(None)
        return result

    async def mset(self, mapping: Any) -> bool:
        if not mapping:
            raise redis_exc.DataError("MSET requires at least one key/value pair")
        for key, value in mapping.items():
            await self.set(key, value)
        return True

    async def msetnx(self, mapping: Any) -> bool:
        if not mapping:
            raise redis_exc.DataError("MSETNX requires at least one key/value pair")
        if any(self._purge(_enc(key)) for key in mapping):
            return False
        for key, value in mapping.items():
            await self.set(key, value)
        return True

    async def append(self, key: Any, value: Any) -> int:
        key, chunk = _enc(key), _enc(value)
        if self._purge(key) and self._kind_of(key) != "string":
            raise _wrongtype()
        current = self._strings.get(key, b"")
        self._strings[key] = current + chunk
        return len(self._strings[key])

    async def strlen(self, key: Any) -> int:
        value = self._string_bytes(_enc(key))
        return len(value) if value is not None else 0

    async def getrange(self, key: Any, start: int, end: int) -> bytes:
        value = self._string_bytes(_enc(key))
        if not value:
            return b""
        return _slice_inclusive(value, start, end)

    async def setrange(self, key: Any, offset: int, value: Any) -> int:
        if offset < 0:
            raise redis_exc.ResponseError("offset is out of range")
        key, chunk = _enc(key), _enc(value)
        if self._purge(key) and self._kind_of(key) != "string":
            raise _wrongtype()
        current = self._strings.get(key, b"")
        if offset > len(current):
            current = current + b"\x00" * (offset - len(current))
        self._strings[key] = current[:offset] + chunk + current[offset + len(chunk):]
        return len(self._strings[key])

    # ---------------------------------------------------------------- Hash

    async def hset(
        self,
        name: Any,
        key: Optional[Any] = None,
        value: Optional[Any] = None,
        mapping: Optional[Any] = None,
    ) -> int:
        # redis-py 签名：hset(name, key=None, value=None, mapping=None)。
        # 两种合法形态互斥：键值对 或 mapping；同时给/都不给即入参错误。
        has_pair = key is not None and value is not None
        uses_mapping = bool(mapping)
        both_forms = uses_mapping and has_pair
        no_form = not uses_mapping and not has_pair
        if both_forms or no_form:
            raise redis_exc.DataError("hset requires 'key' and 'value', or 'mapping'")
        store_key = _enc(name)
        container = self._container(store_key, "hash", create=True)
        created = 0
        if mapping:
            for field, val in mapping.items():
                field_enc = _enc(field)
                if field_enc not in container:
                    created += 1
                container[field_enc] = _enc(val)
        else:
            field_enc = _enc(key)
            if field_enc not in container:
                created += 1
            container[field_enc] = _enc(value)
        return created

    async def hsetnx(self, key: Any, field: Any, value: Any) -> int:
        # redis-py 8.1 无 HSETNX bool 回调 → int 0/1（保真口径）。
        store_key, field, value = _enc(key), _enc(field), _enc(value)
        container = self._container(store_key, "hash", create=True)
        if field in container:
            return 0
        container[field] = value
        return 1

    async def hget(self, key: Any, field: Any) -> Optional[bytes]:
        container = self._container(_enc(key), "hash")
        if container is None:
            return None
        return container.get(_enc(field))

    async def hgetall(self, key: Any) -> Dict[bytes, bytes]:
        container = self._container(_enc(key), "hash")
        return dict(container) if container else {}

    async def hmget(self, key: Any, fields: Any) -> List[Optional[bytes]]:
        container = self._container(_enc(key), "hash")
        if container is None:
            return [None] * len(fields)
        return [container.get(_enc(field)) for field in fields]

    async def hdel(self, key: Any, *fields: Any) -> int:
        store_key = _enc(key)
        container = self._container(store_key, "hash")
        if container is None:
            return 0
        removed = 0
        for field in fields:
            if container.pop(_enc(field), None) is not None:
                removed += 1
        if not container:
            self._delete_key(store_key)
        return removed

    async def hexists(self, key: Any, field: Any) -> bool:
        container = self._container(_enc(key), "hash")
        return container is not None and _enc(field) in container

    async def hlen(self, key: Any) -> int:
        container = self._container(_enc(key), "hash")
        return len(container) if container else 0

    async def hkeys(self, key: Any) -> List[bytes]:
        container = self._container(_enc(key), "hash")
        return list(container) if container else []

    async def hvals(self, key: Any) -> List[bytes]:
        container = self._container(_enc(key), "hash")
        return list(container.values()) if container else []

    async def hincrby(self, key: Any, field: Any, amount: int) -> int:
        container = self._container(_enc(key), "hash", create=True)
        field = _enc(field)
        current = container.get(field)
        if current is not None:
            try:
                current_int = int(current)
            except (TypeError, ValueError) as exc:
                raise redis_exc.ResponseError("hash value is not an integer") from exc
        else:
            current_int = 0
        new_value = current_int + amount
        container[field] = str(new_value).encode("ascii")
        return new_value

    async def hincrbyfloat(self, key: Any, field: Any, amount: float) -> float:
        container = self._container(_enc(key), "hash", create=True)
        field = _enc(field)
        current = container.get(field)
        if current is not None:
            try:
                current_float = float(current)
            except (TypeError, ValueError) as exc:
                raise redis_exc.ResponseError("hash value is not a float") from exc
        else:
            current_float = 0.0
        new_value = current_float + amount
        container[field] = repr(new_value).encode("ascii")
        return new_value

    async def hscan(
        self,
        key: Any,
        cursor: int = 0,
        match: Optional[Any] = None,
        count: Optional[int] = None,
    ) -> Tuple[int, Dict[bytes, bytes]]:
        container = self._container(_enc(key), "hash")
        if not container:
            return 0, {}
        fields = sorted(field for field in container if self._match(match, field))
        page = count or _SCAN_PAGE
        batch = fields[cursor:cursor + page]
        next_cursor = cursor + page if cursor + page < len(fields) else 0
        return next_cursor, {field: container[field] for field in batch}

    # ---------------------------------------------------------------- List

    async def rpush(self, key: Any, *values: Any) -> int:
        container = self._container(_enc(key), "list", create=True)
        container.extend(_enc(value) for value in values)
        return len(container)

    async def lpush(self, key: Any, *values: Any) -> int:
        container = self._container(_enc(key), "list", create=True)
        for value in values:
            container.insert(0, _enc(value))
        return len(container)

    async def lpushx(self, key: Any, value: Any) -> int:
        container = self._container(_enc(key), "list")
        if container is None:
            return 0
        container.insert(0, _enc(value))
        return len(container)

    async def rpushx(self, key: Any, value: Any) -> int:
        container = self._container(_enc(key), "list")
        if container is None:
            return 0
        container.append(_enc(value))
        return len(container)

    async def lpop(self, key: Any, count: Optional[int] = None) -> Any:
        return self._pop(_enc(key), count, left=True)

    async def rpop(self, key: Any, count: Optional[int] = None) -> Any:
        return self._pop(_enc(key), count, left=False)

    def _pop(self, key: bytes, count: Optional[int], *, left: bool) -> Any:
        container = self._container(key, "list")
        if container is None:
            # 缺失 key：count 形态同样返回 nil（Redis 语义）。
            return None
        if count is None:
            if not container:
                return None
            return container.pop(0) if left else container.pop()
        if count >= 0:
            popped = container[:count] if left else container[-count:][::-1]
            if left:
                del container[:count]
            elif count > 0:
                del container[-count:]
            if not container:
                self._delete_key(key)
            return popped
        raise redis_exc.ResponseError("value is out of range, must be positive")

    async def lrange(self, key: Any, start: int, stop: int) -> List[bytes]:
        container = self._container(_enc(key), "list")
        if container is None:
            return []
        return _slice_inclusive_list(container, start, stop)

    async def ltrim(self, key: Any, start: int, stop: int) -> bool:
        store_key = _enc(key)
        container = self._container(store_key, "list")
        if container is None:
            return True
        keep = _slice_inclusive_list(container, start, stop)
        if keep:
            self._lists[store_key] = keep
        else:
            self._delete_key(store_key)
        return True

    async def llen(self, key: Any) -> int:
        container = self._container(_enc(key), "list")
        return len(container) if container else 0

    async def lindex(self, key: Any, index: int) -> Optional[bytes]:
        container = self._container(_enc(key), "list")
        if container is None:
            return None
        if index < 0:
            index += len(container)
        if 0 <= index < len(container):
            return container[index]
        return None

    async def lset(self, key: Any, index: int, value: Any) -> bool:
        container = self._container(_enc(key), "list")
        if container is None:
            raise redis_exc.ResponseError("no such key")
        if index < 0:
            index += len(container)
        if not 0 <= index < len(container):
            raise redis_exc.ResponseError("index out of range")
        container[index] = _enc(value)
        return True

    async def lrem(self, key: Any, count: int, value: Any) -> int:
        store_key = _enc(key)
        container = self._container(store_key, "list")
        if container is None:
            return 0
        target = _enc(value)
        removed = 0
        kept: List[bytes] = []
        if count >= 0:
            # count>0：从头开始删 limit 个；count=0：全删。
            limit = count if count > 0 else len(container)
            for item in container:
                if item == target and removed < limit:
                    removed += 1
                else:
                    kept.append(item)
        else:
            # count<0：从尾开始删 |count| 个。
            limit = -count
            for item in reversed(container):
                if item == target and removed < limit:
                    removed += 1
                else:
                    kept.append(item)
            kept.reverse()
        if kept:
            self._lists[store_key] = kept
        else:
            self._delete_key(store_key)
        return removed

    async def rpoplpush(self, source: Any, destination: Any) -> Optional[bytes]:
        src_key, dst_key = _enc(source), _enc(destination)
        src = self._container(src_key, "list")
        if not src:
            return None
        dst = self._container(dst_key, "list", create=True)
        value = src.pop()
        dst.insert(0, value)
        if not src:
            self._delete_key(src_key)
        return value

    # ---------------------------------------------------------------- Set

    async def sadd(self, key: Any, *members: Any) -> int:
        container = self._container(_enc(key), "set", create=True)
        added = 0
        for member in members:
            member_enc = _enc(member)
            if member_enc not in container:
                container.add(member_enc)
                added += 1
        return added

    async def srem(self, key: Any, *members: Any) -> int:
        store_key = _enc(key)
        container = self._container(store_key, "set")
        if container is None:
            return 0
        removed = 0
        for member in members:
            member_enc = _enc(member)
            if member_enc in container:
                container.remove(member_enc)
                removed += 1
        if not container:
            self._delete_key(store_key)
        return removed

    async def smembers(self, key: Any) -> Set[bytes]:
        container = self._container(_enc(key), "set")
        return set(container) if container else set()

    async def sismember(self, key: Any, member: Any) -> int:
        # redis-py 8.1 无 SISMEMBER bool 回调 → int 0/1（保真口径）。
        container = self._container(_enc(key), "set")
        if container is None:
            return 0
        return 1 if _enc(member) in container else 0

    async def scard(self, key: Any) -> int:
        container = self._container(_enc(key), "set")
        return len(container) if container else 0

    async def spop(self, key: Any, count: Optional[int] = None) -> Any:
        store_key = _enc(key)
        container = self._container(store_key, "set")
        if container is None:
            return None
        if count is None:
            if not container:
                return None
            return container.pop()
        # redis-py / fakeredis 语义：带 count 的 spop 返回 list（非 set）
        popped = random.sample(sorted(container), min(count, len(container)))
        container -= set(popped)
        if not container:
            self._delete_key(store_key)
        return popped

    async def srandmember(self, key: Any, count: Optional[int] = None) -> Any:
        container = self._container(_enc(key), "set")
        if container is None or not container:
            return None if count is None else []
        members = sorted(container)
        if count is None:
            return random.choice(members)
        if count >= 0:
            return random.sample(members, min(count, len(members)))
        # count<0：允许重复（Redis 语义）。
        return [random.choice(members) for _ in range(-count)]

    async def smove(self, source: Any, destination: Any, member: Any) -> bool:
        src = self._container(_enc(source), "set")
        if src is None or _enc(member) not in src:
            return False
        dst = self._container(_enc(destination), "set", create=True)
        src.remove(_enc(member))
        dst.add(_enc(member))
        return True

    async def sinter(self, *keys: Any) -> Set[bytes]:
        sets = [self._members_of(key) for key in keys]
        if not sets:
            raise redis_exc.DataError("at least one key required")
        return set.intersection(*sets)

    async def sunion(self, *keys: Any) -> Set[bytes]:
        sets = [self._members_of(key) for key in keys]
        return set().union(*sets) if sets else set()

    async def sdiff(self, *keys: Any) -> Set[bytes]:
        sets = [self._members_of(key) for key in keys]
        if not sets:
            raise redis_exc.DataError("at least one key required")
        return set.difference(*sets)

    async def sinterstore(self, destination: Any, *keys: Any) -> int:
        result = await self.sinter(*keys)
        return self._store_set(_enc(destination), result)

    async def sunionstore(self, destination: Any, *keys: Any) -> int:
        result = await self.sunion(*keys)
        return self._store_set(_enc(destination), result)

    async def sdiffstore(self, destination: Any, *keys: Any) -> int:
        result = await self.sdiff(*keys)
        return self._store_set(_enc(destination), result)

    def _members_of(self, key: Any) -> Set[bytes]:
        container = self._container(_enc(key), "set")
        return set(container) if container else set()

    def _store_set(self, key: bytes, members: Set[bytes]) -> int:
        self._delete_key(key)
        if not members:
            return 0
        self._sets[key] = set(members)
        return len(members)

    async def sscan(
        self,
        key: Any,
        cursor: int = 0,
        match: Optional[Any] = None,
        count: Optional[int] = None,
    ) -> Tuple[int, List[bytes]]:
        container = self._container(_enc(key), "set")
        if not container:
            return 0, []
        members = sorted(member for member in container if self._match(match, member))
        page = count or _SCAN_PAGE
        batch = members[cursor:cursor + page]
        next_cursor = cursor + page if cursor + page < len(members) else 0
        return next_cursor, batch

    # ---------------------------------------------------------------- Scan

    async def scan(
        self,
        cursor: int = 0,
        match: Optional[Any] = None,
        count: Optional[int] = None,
        _type: Optional[Any] = None,
        **kwargs: Any,
    ) -> Tuple[int, List[bytes]]:
        kind_filter = _enc(_type).decode("ascii") if _type is not None else None
        # 过滤条件拆为具名中间步骤（G.EXP.04：推导式仅承载简单逻辑）
        matched = [key for key in self._alive_keys() if self._match(match, key)]
        if kind_filter is not None:
            matched = [key for key in matched if self._kind_of(key) == kind_filter]
        keys = matched
        page = count or _SCAN_PAGE
        batch = keys[cursor:cursor + page]
        next_cursor = cursor + page if cursor + page < len(keys) else 0
        return next_cursor, batch

    def scan_iter(
        self,
        match: Optional[Any] = None,
        count: Optional[int] = None,
    ) -> AsyncIterator[bytes]:
        return self._scan_iter(match, count)

    async def _scan_iter(
        self, match: Optional[Any], count: Optional[int]
    ) -> AsyncIterator[bytes]:
        cursor = 0
        while True:
            cursor, batch = await self.scan(cursor, match=match, count=count)
            for key in batch:
                yield key
            if cursor == 0:
                return
