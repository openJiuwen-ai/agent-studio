# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis-py 替身：记录调用并回放预置结果/异常（redis_native 单测专用）。"""

from __future__ import annotations

from typing import Any


class FakeRedisClient:
    """redis-py 异步客户端替身。

    - 异步命令：实例字典未命中的属性访问 → 记录 ``(name, args, kwargs)`` 的
      异步方法；``results[name]`` 为 callable 时按调用求值，否则原样返回，
      未预置返回 None；``exceptions[name]`` 存在则抛出；
    - 同步面：``pipeline()`` / ``pubsub()`` 返回预置对象
      （``pipeline_obj`` / ``pubsub_obj``；pipeline 用
      :class:`FakePipeline`——命令须同步记录）；``scan_iter`` 返回预置
      key 的异步生成器（真客户端此方法是同步函数返回异步迭代器）；
    - ``calls`` 保留全部调用记录（含 pipeline/pubsub/aclose/scan_iter）。
    """

    def __init__(
        self,
        results: dict[str, Any] | None = None,
        exceptions: dict[str, BaseException] | None = None,
    ) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self._results = results or {}
        self._exceptions = exceptions or {}
        self.pipeline_obj: Any = None
        self.pubsub_obj: Any = None

    def pipeline(self, transaction: bool = True, **kwargs: Any):
        self.calls.append(("pipeline", (), {"transaction": transaction, **kwargs}))
        return self.pipeline_obj

    def pubsub(self, **kwargs: Any):
        self.calls.append(("pubsub", (), dict(kwargs)))
        return self.pubsub_obj

    def scan_iter(self, *, match: Any = None, count: int | None = None):
        self.calls.append(("scan_iter", (), {"match": match, "count": count}))

        async def iterator():
            for item in self._results.get("scan_iter_items", []):
                yield item

        return iterator()

    async def aclose(self, close_connection_pool: Any = None) -> None:
        self.calls.append(
            ("aclose", (), {"close_connection_pool": close_connection_pool})
        )
        if "aclose" in self._exceptions:
            raise self._exceptions["aclose"]

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        async def command(*args: Any, **kwargs: Any):
            self.calls.append((name, args, kwargs))
            if name in self._exceptions:
                raise self._exceptions[name]
            result = self._results.get(name)
            if callable(result):
                return result(*args, **kwargs)
            return result

        return command


class FakePipeline:
    """redis-py pipeline 替身：命令方法**同步**记录（入队语义，不返回协程），
    ``execute``/``aclose`` 异步。

    真实 redis-py pipeline 的命令方法是同步入队调用；FakeRedisClient 的
    动态异步命令只适合当客户端替身，作 pipeline 替身会产生 never-awaited
    协程警告且不记录调用。
    """

    def __init__(
        self,
        results: dict[str, Any] | None = None,
        exceptions: dict[str, BaseException] | None = None,
    ) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self._results = results or {}
        self._exceptions = exceptions or {}

    async def execute(self) -> Any:
        self.calls.append(("execute", (), {}))
        if "execute" in self._exceptions:
            raise self._exceptions["execute"]
        result = self._results.get("execute")
        if callable(result):
            return result()
        return result

    async def aclose(self) -> None:
        self.calls.append(("aclose", (), {}))

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        def command(*args: Any, **kwargs: Any):
            self.calls.append((name, args, kwargs))

        return command


class FakePubSub:
    """redis-py PubSub 替身：subscribed 状态机 + 预置消息序列回放。

    - ``listen()`` 返回异步生成器：逐条产出 ``messages`` 后（可选）抛出
      ``listen_error``；
    - ``subscribe``/``psubscribe`` 置 ``subscribed=True``；空参
      ``unsubscribe`` 置回 False（对齐 redis-py 语义）。
    """

    def __init__(
        self,
        messages: list[Any] | None = None,
        listen_error: BaseException | None = None,
        aclose_error: BaseException | None = None,
    ) -> None:
        self.subscribed = False
        self._messages = list(messages or [])
        self._listen_error = listen_error
        self._aclose_error = aclose_error
        self.operations: list[tuple[str, tuple]] = []
        self.closed = False

    async def subscribe(self, *channels: Any) -> None:
        self.operations.append(("subscribe", channels))
        self.subscribed = True

    async def psubscribe(self, *patterns: Any) -> None:
        self.operations.append(("psubscribe", patterns))
        self.subscribed = True

    async def unsubscribe(self, *channels: Any) -> None:
        self.operations.append(("unsubscribe", channels))
        if not channels:
            self.subscribed = False

    async def punsubscribe(self, *patterns: Any) -> None:
        self.operations.append(("punsubscribe", patterns))

    async def aclose(self) -> None:
        self.operations.append(("aclose", ()))
        self.closed = True
        if self._aclose_error is not None:
            raise self._aclose_error

    def listen(self):
        messages = self._messages
        error = self._listen_error

        async def iterator():
            for message in messages:
                yield message
            if error is not None:
                raise error

        return iterator()
