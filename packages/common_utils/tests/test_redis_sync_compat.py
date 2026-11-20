# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SyncCompatClient（专用循环 + 独立客户端的自包含同步桥）测试。

关键回归用例：事件循环线程内同步调用（builder Controller 在 Executor.__init__
里同步调 load_session 的形态）必须成功——桥循环与调用线程所属循环无关。
"""

import asyncio
import threading

import pytest

from common_utils.redis_manager import RedisClientManager
from common_utils.redis_sync_compat import SyncCompatClient


class StubAsyncClient:
    """SPI 协议面最小替身（内存实现，bytes 语义）。"""

    def __init__(self):
        self.strings = {}
        self.lists = {}

    async def get(self, key):
        return self.strings.get(key)

    async def set(self, key, value, *, condition=None, duration=None, keep_ttl=False):
        self.strings[key] = value if isinstance(value, bytes) else str(value).encode()
        return b"OK"

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self.strings:
                self.strings.pop(key)
                removed += 1
            if key in self.lists:
                self.lists.pop(key)
                removed += 1
        return removed

    async def expire(self, key, duration):
        return key in self.strings or key in self.lists

    async def exists(self, *keys):
        return sum(1 for key in keys if key in self.strings or key in self.lists)

    async def rpush(self, key, *values):
        bucket = self.lists.setdefault(key, [])
        bucket.extend(v if isinstance(v, bytes) else str(v).encode() for v in values)
        return len(bucket)

    async def lrange(self, key, start, stop):
        values = self.lists.get(key, [])
        if stop < 0:
            stop = len(values) + stop
        return values[start:stop + 1]

    async def llen(self, key):
        return len(self.lists.get(key, []))

    async def ping(self):
        return True

    async def aclose(self):
        self.strings.clear()
        self.lists.clear()


@pytest.fixture
def bridge():
    """已初始化的桥（注入 stub 工厂）。"""
    stub = StubAsyncClient()
    client = SyncCompatClient(lambda: _return(stub))
    client.initialize()
    yield client, stub
    client.close()


async def _return(value):
    return value


@pytest.fixture(autouse=True)
def _reset_manager():
    RedisClientManager.reset()
    yield
    RedisClientManager.reset()


class TestSyncCompatClient:
    @staticmethod
    def test_string_get_set_ex_roundtrip(bridge):
        client, _ = bridge
        assert client.set("k1", "v1", ex=60) == b"OK"
        assert client.get("k1") == b"v1"
        assert client.get("missing") is None

    @staticmethod
    def test_list_rpush_lrange_llen(bridge):
        client, _ = bridge
        assert client.rpush("hist", "a", "b", "c") == 3
        assert client.lrange("hist", 0, -1) == [b"a", b"b", b"c"]
        assert client.lrange("hist", 1, 1) == [b"b"]
        assert client.llen("hist") == 3
        assert client.llen("missing") == 0

    @staticmethod
    def test_key_delete_expire_exists_ping(bridge):
        client, _ = bridge
        client.set("k", "v")
        assert client.exists("k") == 1
        assert client.expire("k", 30) is True
        assert client.ping() is True
        assert client.delete("k") == 1
        assert client.exists("k") == 0
        assert client.delete("k") == 0
        assert client.expire("k", 30) is False

    @staticmethod
    def test_call_from_event_loop_thread_succeeds(bridge):
        """回归用例：事件循环线程内同步调用（n2l Controller 形态）不得死锁/抛错。

        旧版桥（复用装配循环 + 循环线程内 fail-fast）在此形态抛 RuntimeError
        导致 n2l 请求 13100004；自包含桥（专用循环）下该形态必须成功。
        """
        client, _ = bridge
        result = {}
        done = threading.Event()

        async def _scenario():
            # 在事件循环线程内直接同步调用桥
            result["set"] = client.set("loop-thread", "v", ex=60)
            result["get"] = client.get("loop-thread")
            done.set()

        async def _runner():
            await _scenario()

        loop = asyncio.new_event_loop()
        t = threading.Thread(target=loop.run_until_complete, args=(_runner(),))
        t.start()
        t.join(timeout=10)
        loop.close()
        assert done.is_set(), "event-loop-thread sync call did not finish"
        assert result["get"] == b"v"

    @staticmethod
    def test_call_before_initialize_raises():
        client = SyncCompatClient(lambda: _return(StubAsyncClient()))
        with pytest.raises(RuntimeError, match="before initialize"):
            client.get("k")

    @staticmethod
    def test_initialize_idempotent():
        stub = StubAsyncClient()
        client = SyncCompatClient(lambda: _return(stub))
        client.initialize()
        client.initialize()  # 幂等
        assert client.get("k2") is None
        client.close()
        client.close()  # 幂等

    @staticmethod
    def test_close_releases_client():
        stub = StubAsyncClient()
        client = SyncCompatClient(lambda: _return(stub))
        client.initialize()
        client.set("gone", "x", ex=10)
        client.close()
        assert stub.strings == {}, "aclose 应清空客户端状态"
        with pytest.raises(RuntimeError):
            client.get("gone")


class TestManagerSyncCompatWiring:
    @staticmethod
    def test_get_sync_client_prefers_registered_compat(bridge):
        client, _ = bridge
        RedisClientManager.set_sync_compat(client)
        assert RedisClientManager.get_instance().get_sync_client() is client

    @staticmethod
    def test_reset_clears_registered_compat(bridge):
        client, _ = bridge
        RedisClientManager.set_sync_compat(client)
        RedisClientManager.reset()
        assert getattr(RedisClientManager, "_sync_compat") is None
