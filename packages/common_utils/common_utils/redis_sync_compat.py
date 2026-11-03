# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SPI 异步客户端的 redis-py 同步兼容面（sync-over-async 专用循环桥）。

背景：Redis Provider 适配层（redis_spi）只有异步协议面；builder 的同步存储类
（nl_to_agent/storage/history.py 的 ImRedisConversation / SessionStorage）以
redis-py 同步调用形态工作（get / set(ex=) / delete / expire / exists / rpush /
lrange / llen），且其上层接口（BaseConversationMemory）约束同步签名，无法改异步；
Controller 甚至在事件循环线程内同步调用（Executor.__init__ → load_session）。

方案：本桥自持**专用后台事件循环**，并在该循环上经 RedisProviderFactory.create
独立装配专属客户端（与 accessor 主客户端互不共享连接池）。任意线程（含装配
循环/事件循环线程）的同步调用经 run_coroutine_threadsafe 调度到桥循环执行、
调用线程阻塞等待——目标循环与调用线程所属循环无关，无死锁场景。

语义约定：
  - 返回值透传 SPI 语义（native 实现默认 bytes，与 legacy decode_responses=False
    一致，调用方零感知）；
  - 生产路径 client_factory=RedisProviderFactory.create(settings)（含 ping
    fail-fast）；测试可注入替身工厂；
  - close 为幂等：先在桥循环上关闭客户端，再停循环。
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any, Awaitable, Callable

from redis_spi.types import Duration

logger = logging.getLogger(__name__)


class SyncCompatClient:
    """redis-py 同步调用形态的自包含桥（专用循环 + 独立 Provider 客户端）。"""

    def __init__(
        self,
        client_factory: Callable[..., Awaitable[Any]],
        *,
        call_timeout: float = 60.0,
    ):
        self._client_factory = client_factory
        self._call_timeout = call_timeout
        self._client: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._closed = False
        # 生命周期互斥锁：防并发 initialize 双建循环线程（泄漏）与对已停循环二次 stop
        self._lifecycle_lock = threading.Lock()

    # ---------------------------------------------------------------- lifecycle

    def initialize(self) -> None:
        """启动桥循环并独立装配客户端（含 ping fail-fast）。

        幂等：已初始化直接返回；装配失败停循环后上抛。
        """
        with self._lifecycle_lock:
            if self._client is not None:
                return
            if self._closed:
                raise RuntimeError("SyncCompatClient already closed")

            self._loop = asyncio.new_event_loop()
            self._loop_thread = threading.Thread(
                target=self._loop.run_forever, name="redis-sync-compat", daemon=True
            )
            self._loop_thread.start()
            try:
                self._client = self._call(self._client_factory, "initialize")
            except BaseException:
                self._stop_loop()
                raise
        logger.info("SyncCompatClient initialized (dedicated loop + own client)")

    def close(self) -> None:
        """幂等关闭：先关客户端，再停桥循环。"""
        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            if self._client is not None and self._loop is not None:
                aclose = getattr(self._client, "aclose", None)
                if callable(aclose):
                    try:
                        self._run(aclose(), "aclose")
                    except Exception as exc:  # noqa: BLE001 - 关闭尽力而为
                        logger.warning("SyncCompatClient aclose failed: %s", exc)
            self._client = None
            self._stop_loop()

    @property
    def closed(self) -> bool:
        """是否已关闭（bootstrap 幂等判断用）。"""
        return self._closed

    def _stop_loop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=5)
        if self._loop is not None:
            self._loop.close()
        self._loop = None
        self._loop_thread = None

    # ---------------------------------------------------------------- internal

    def _run(self, coro: Any, method: str) -> Any:
        """把协程调度到桥循环执行，调用线程阻塞等待结果（守卫由 _call 负责）。"""
        # 快照循环引用：close() 并发置 None 时不以裸 AttributeError 暴露
        loop = self._loop
        loop_thread = self._loop_thread
        if loop is None:
            raise RuntimeError(
                f"SyncCompatClient.{method} called on a closed/uninitialized client"
            )
        if threading.current_thread() is loop_thread:
            # 防御：桥循环线程只跑桥协程，正常不会出现；真出现即逻辑错误
            raise RuntimeError(
                f"SyncCompatClient.{method} called from its own loop thread"
            )
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=self._call_timeout)
        except FutureTimeoutError as exc:
            future.cancel()
            raise RuntimeError(
                f"Redis sync compat call '{method}' timed out "
                f"after {self._call_timeout}s"
            ) from exc

    def _call(self, coro_factory: Callable[[], Any], method: str) -> Any:
        """守卫通过后才求值协程工厂（工厂可能访问 self._client）。"""
        self._ensure_ready(method)
        return self._run(coro_factory(), method)

    def _ensure_ready(self, method: str) -> None:
        if self._closed:
            raise RuntimeError(
                f"SyncCompatClient.{method} called after close()"
            )
        if self._loop is None:
            raise RuntimeError(
                f"SyncCompatClient.{method} called before initialize()"
            )
        if self._client is None and method != "initialize":
            raise RuntimeError(
                f"SyncCompatClient.{method} called before initialize()"
            )

    # ---------------------------------------------------------------- String

    def get(self, key: str) -> bytes | None:
        """GET。"""
        return self._call(lambda: self._client.get(key), "get")

    def set(self, key: str, value: str | bytes, ex: int | None = None) -> Any:
        """SET（redis-py 兼容签名：ex 秒 → SPI duration）。"""
        duration = Duration.seconds(ex) if ex is not None else None

        async def _do() -> Any:
            return await self._client.set(key, value, duration=duration)

        return self._call(_do, "set")

    # ---------------------------------------------------------------- Key

    def delete(self, *keys: str) -> int:
        """DEL，返回删除数量。"""
        return self._call(lambda: self._client.delete(*keys), "delete")

    def expire(self, key: str, ttl_seconds: int) -> bool:
        """EXPIRE（秒）。"""
        duration = Duration.seconds(ttl_seconds)

        async def _do() -> bool:
            return await self._client.expire(key, duration)

        return self._call(_do, "expire")

    def exists(self, *keys: str) -> int:
        """EXISTS，返回存在的 key 数量。"""
        return self._call(lambda: self._client.exists(*keys), "exists")

    # ---------------------------------------------------------------- List

    def rpush(self, key: str, *values: str | bytes) -> int:
        """RPUSH，返回列表长度。"""
        return self._call(lambda: self._client.rpush(key, *values), "rpush")

    def lrange(self, key: str, start: int, stop: int) -> list[bytes]:
        """LRANGE（stop=-1 表示到末尾）。"""
        return self._call(lambda: self._client.lrange(key, start, stop), "lrange")

    def llen(self, key: str) -> int:
        """LLEN。"""
        return self._call(lambda: self._client.llen(key), "llen")

    # ---------------------------------------------------------------- misc

    def ping(self) -> bool:
        """PING（redis-py 兼容探活）。"""
        return self._call(lambda: self._client.ping(), "ping")

    def keys(self, pattern: str) -> list[bytes]:
        """KEYS（经 SCAN 迭代实现，仅小键空间场景）。"""

        async def _do() -> list[bytes]:
            return [key async for key in self._client.scan_iter(match=pattern)]

        return self._call(_do, "keys")
