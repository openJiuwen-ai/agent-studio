# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Redis 客户端一致性测试套件（TCK）。

覆盖 BaseSyncRedisClient / BaseAsyncRedisClient 契约的全部方法语义与边界，
所有 Provider 实现（内置或企业自研）均应继承本套件对应 Mixin 跑批通过后接入平台：
  - TestInMemorySyncClientContract: 内存实现跑批（TCK 参考实现）
  - TestRedisPySyncClientContract: 默认实现（redis-py 委托）以替身客户端跑批，验证委托正确性
  - TestDemoCustomProviderContract: 演示自研 Provider 跑批（验证可替换性）
  - TestInMemoryAsyncClientContract: 异步内存实现跑批
"""

import asyncio
import threading
import time
from contextlib import contextmanager

from common_utils.redis_provider import (
    BaseSyncRedisClient,
    InMemorySyncRedisClient,
    RedisPySyncClient,
    _InMemoryEngine,
)

from demo_custom_provider import DemoCustomRedisProvider

TTL_WAIT = 0.7
SHORT_TTL = 0.3


class SyncClientContractMixin:
    """同步客户端契约测试（子类实现 make_client，每条用例独立客户端）。"""

    def make_client(self) -> BaseSyncRedisClient:
        raise NotImplementedError

    # ---------------- KV ----------------
    def test_get_missing_key_returns_none(self):
        client = self.make_client()
        assert client.get("tck:missing") is None

    def test_set_then_get_round_trip_bytes(self):
        client = self.make_client()
        client.set("tck:kv", "value")
        assert client.get("tck:kv") == b"value"
        client.set("tck:kv", b"bytes-value")
        assert client.get("tck:kv") == b"bytes-value"

    def test_set_overwrites_value(self):
        client = self.make_client()
        client.set("tck:overwrite", "v1")
        client.set("tck:overwrite", "v2")
        assert client.get("tck:overwrite") == b"v2"

    def test_set_with_ttl_expires(self):
        client = self.make_client()
        client.set("tck:kv:ttl", "value", ex=SHORT_TTL)
        assert client.get("tck:kv:ttl") == b"value"
        time.sleep(TTL_WAIT)
        assert client.get("tck:kv:ttl") is None

    def test_delete_returns_removed_count(self):
        client = self.make_client()
        client.set("tck:del:1", "v")
        client.set("tck:del:2", "v")
        assert client.delete("tck:del:1", "tck:del:2", "tck:del:missing") == 2
        assert client.get("tck:del:1") is None

    def test_exists_counts_existing_keys(self):
        client = self.make_client()
        client.set("tck:exists:1", "v")
        assert client.exists("tck:exists:1", "tck:exists:missing") == 1

    def test_expire_missing_key_returns_false(self):
        client = self.make_client()
        assert client.expire("tck:expire:missing", 60) is False

    def test_expire_then_ttl_semantics(self):
        client = self.make_client()
        client.set("tck:expire", "v")
        assert client.ttl("tck:expire") == -1
        assert client.expire("tck:expire", 100) is True
        assert 0 < client.ttl("tck:expire") <= 100
        assert client.ttl("tck:expire:missing") == -2

    def test_mget_preserves_order_with_none(self):
        client = self.make_client()
        client.set("tck:mget:1", "v1")
        client.set("tck:mget:3", "v3")
        assert client.mget(["tck:mget:1", "tck:mget:2", "tck:mget:3"]) == [b"v1", None, b"v3"]

    def test_mset_batch_write(self):
        client = self.make_client()
        client.mset({"tck:mset:1": "v1", "tck:mset:2": "v2"})
        assert client.get("tck:mset:1") == b"v1"
        assert client.get("tck:mset:2") == b"v2"

    # ---------------- Hash ----------------
    def test_hset_key_value_and_mapping(self):
        client = self.make_client()
        assert client.hset("tck:hash", key="f1", value="v1") == 1
        assert client.hset("tck:hash", mapping={"f2": "v2", "f3": "v3"}) == 2
        assert client.hget("tck:hash", "f1") == b"v1"
        assert client.hgetall("tck:hash") == {b"f1": b"v1", b"f2": b"v2", b"f3": b"v3"}

    def test_hget_missing_returns_none_and_hgetall_missing_empty(self):
        client = self.make_client()
        assert client.hget("tck:hash:missing", "f") is None
        assert client.hgetall("tck:hash:missing") == {}

    def test_hset_with_ex_expires(self):
        client = self.make_client()
        client.hset("tck:hash:ttl", mapping={"f": "v"}, ex=SHORT_TTL)
        assert client.hget("tck:hash:ttl", "f") == b"v"
        time.sleep(TTL_WAIT)
        assert client.hgetall("tck:hash:ttl") == {}

    # ---------------- Set ----------------
    def test_sadd_srem_smembers(self):
        client = self.make_client()
        assert client.sadd("tck:set", "m1", "m2") == 2
        assert client.sadd("tck:set", "m2", "m3") == 1  # m2 已存在
        assert client.smembers("tck:set") == {b"m1", b"m2", b"m3"}
        assert client.srem("tck:set", "m1", "missing") == 1
        assert client.smembers("tck:set") == {b"m2", b"m3"}

    def test_smembers_missing_returns_empty(self):
        client = self.make_client()
        assert client.smembers("tck:set:missing") == set()

    # ---------------- List ----------------
    def test_rpush_lrange_llen(self):
        client = self.make_client()
        assert client.rpush("tck:list", "a", "b") == 2
        assert client.rpush("tck:list", "c") == 3
        assert client.lrange("tck:list", 0, -1) == [b"a", b"b", b"c"]
        assert client.lrange("tck:list", 1, -1) == [b"b", b"c"]
        assert client.llen("tck:list") == 3

    def test_lrange_missing_returns_empty(self):
        client = self.make_client()
        assert client.lrange("tck:list:missing", 0, -1) == []
        assert client.llen("tck:list:missing") == 0

    def test_rpush_with_ex_expires(self):
        client = self.make_client()
        client.rpush("tck:list:ttl", "a", ex=SHORT_TTL)
        assert client.llen("tck:list:ttl") == 1
        time.sleep(TTL_WAIT)
        assert client.llen("tck:list:ttl") == 0
        assert client.lrange("tck:list:ttl", 0, -1) == []

    # ---------------- scan ----------------
    def test_scan_iter_glob_match(self):
        client = self.make_client()
        client.set("tck:scan:1", "v")
        client.set("tck:scan:2", "v")
        client.set("tck:other", "v")
        keys = set(client.scan_iter("tck:scan:*"))
        assert keys == {b"tck:scan:1", b"tck:scan:2"}

    # ---------------- lock ----------------
    def test_lock_acquire_and_release(self):
        client = self.make_client()
        with client.get_lock("tck:lock"):
            pass
        with client.get_lock("tck:lock"):
            pass

    def test_lock_same_key_mutually_exclusive_across_threads(self):
        client = self.make_client()
        acquired = []

        with client.get_lock("tck:lock:mutex"):
            def _try_acquire():
                try:
                    with client.get_lock("tck:lock:mutex", timeout=0.2):
                        acquired.append(True)
                except TimeoutError:
                    acquired.append(False)

            thread = threading.Thread(target=_try_acquire)
            thread.start()
            thread.join()

        assert acquired == [False]

        with client.get_lock("tck:lock:mutex", timeout=1.0):
            pass  # 释放后可重新获取


class _FakeRedisPyClient:
    """redis-py 同步客户端测试替身：bytes 语义，方法签名对齐 redis-py（供委托实现跑 TCK）。"""

    def __init__(self):
        self._engine = _InMemoryEngine()
        self._locks = {}

    def get(self, key):
        return self._engine.get(key)

    def set(self, key, value, ex=None):
        return self._engine.set(key, value, ex)

    def delete(self, *keys):
        return self._engine.delete(*keys)

    def exists(self, *keys):
        return self._engine.exists(*keys)

    def expire(self, key, seconds):
        return self._engine.expire(key, seconds)

    def ttl(self, key):
        return self._engine.ttl(key)

    def mget(self, keys):
        return self._engine.mget(keys)

    def mset(self, mapping):
        return self._engine.mset(mapping)

    def hset(self, name, key=None, value=None, mapping=None):
        if key is None and mapping is None:
            raise ValueError("hset requires key/value or mapping")
        return self._engine.hset(name, key, value, mapping)

    def hget(self, name, key):
        return self._engine.hget(name, key)

    def hgetall(self, name):
        return self._engine.hgetall(name)

    def sadd(self, name, *members):
        return self._engine.sadd(name, *members)

    def srem(self, name, *members):
        return self._engine.srem(name, *members)

    def smembers(self, name):
        return self._engine.smembers(name)

    def rpush(self, name, *values):
        return self._engine.rpush(name, *values)

    def lrange(self, name, start, end):
        return self._engine.lrange(name, start, end)

    def llen(self, name):
        return self._engine.llen(name)

    def scan_iter(self, match=None):
        return self._engine.scan_iter(match or "*")

    def lock(self, name, timeout=10.0):
        import threading as _threading

        lock = self._locks.setdefault(name, _threading.Lock())

        @contextmanager
        def _ctx():
            acquired = lock.acquire(timeout=timeout)
            try:
                if not acquired:
                    raise TimeoutError(f"acquire lock '{name}' timeout")
                yield
            finally:
                if acquired:
                    lock.release()

        return _ctx()


class TestInMemorySyncClientContract(SyncClientContractMixin):
    """内置内存实现跑批一致性测试套件。"""

    def make_client(self):
        return InMemorySyncRedisClient()


class TestRedisPySyncClientContract(SyncClientContractMixin):
    """默认实现（redis-py 委托）跑批：以替身客户端验证委托与契约对齐。"""

    def make_client(self):
        return RedisPySyncClient(_FakeRedisPyClient())


class TestDemoCustomProviderContract(SyncClientContractMixin):
    """演示自研 Provider 跑批（验收标准：demo Provider 通过 TCK）。"""

    def make_client(self):
        return DemoCustomRedisProvider().create_sync_client(None)


class TestInMemoryAsyncClientContract:
    """异步内存实现契约测试（asyncio.run 驱动，不依赖 pytest-asyncio）。"""

    def _client(self):
        from common_utils.redis_provider import InMemoryAsyncRedisClient

        return InMemoryAsyncRedisClient()

    def test_kv_round_trip(self):
        async def run():
            client = self._client()
            assert await client.get("tck:a:missing") is None
            await client.set("tck:a:kv", "value")
            assert await client.get("tck:a:kv") == b"value"
            await client.set("tck:a:kv", "v2", ex=SHORT_TTL)
            assert await client.get("tck:a:kv") == b"v2"
            await asyncio.sleep(TTL_WAIT)
            assert await client.get("tck:a:kv") is None

        asyncio.run(run())

    def test_delete_exists_expire_ttl(self):
        async def run():
            client = self._client()
            await client.set("tck:a:del", "v")
            assert await client.delete("tck:a:del", "tck:a:none") == 1
            assert await client.exists("tck:a:del") == 0
            assert await client.expire("tck:a:none", 10) is False
            await client.set("tck:a:exp", "v")
            assert await client.expire("tck:a:exp", 100) is True
            assert 0 < await client.ttl("tck:a:exp") <= 100

        asyncio.run(run())

    def test_mget_mset(self):
        async def run():
            client = self._client()
            await client.mset({"tck:a:mset:1": "v1"})
            assert await client.mget(["tck:a:mset:1", "tck:a:mset:none"]) == [b"v1", None]

        asyncio.run(run())

    def test_hash_set_list(self):
        async def run():
            client = self._client()
            assert await client.hset("tck:a:hash", key="f", value="v") == 1
            assert await client.hget("tck:a:hash", "f") == b"v"
            assert await client.hset("tck:a:hash", mapping={"g": "w"}) == 1
            assert await client.hgetall("tck:a:hash") == {b"f": b"v", b"g": b"w"}

            assert await client.sadd("tck:a:set", "m1", "m1", "m2") == 2
            assert await client.smembers("tck:a:set") == {b"m1", b"m2"}
            assert await client.srem("tck:a:set", "m1") == 1

            assert await client.rpush("tck:a:list", "a", "b", ex=SHORT_TTL) == 2
            assert await client.lrange("tck:a:list", 0, -1) == [b"a", b"b"]
            assert await client.llen("tck:a:list") == 2
            await asyncio.sleep(TTL_WAIT)
            assert await client.llen("tck:a:list") == 0

        asyncio.run(run())

    def test_scan_iter(self):
        async def run():
            client = self._client()
            await client.set("tck:a:scan:1", "v")
            keys = [key async for key in client.scan_iter("tck:a:scan:*")]
            assert keys == [b"tck:a:scan:1"]

        asyncio.run(run())

    def test_async_lock(self):
        async def run():
            client = self._client()
            async with client.get_lock("tck:a:lock"):
                pass
            async with client.get_lock("tck:a:lock"):
                pass

        asyncio.run(run())
