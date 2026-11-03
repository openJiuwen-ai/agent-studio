# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""PubSub 订阅句柄（redis-py asyncio PubSub 委托）。

redis-py 行为差异（已核对 8.1 源码）：
  - ``PubSub.listen()`` 为 ``while self.subscribed:``——未订阅时迭代器**立即
    结束**。SPI 契约允许"自旋保活或阻塞等订阅"，本实现先自旋等待出现首个
    订阅（或句柄关闭），支持"先迭代后订阅"的使用形态；
  - 消息为 dict ``{type, pattern, channel, data}``；pong 为 redis-py 内部
    保活产物（契约外），过滤不产出；
  - 订阅确认消息（subscribe/psubscribe 等）的 data 为订阅计数 int——契约
    明示"含 subscribe 确认消息"，透传（消费方应忽略未知/确认类 type）。

生命周期声明（契约要求二选一）：**级联关闭**——句柄自身 aclose() 可独立
调用；主客户端 aclose() 关闭订阅池时句柄随之失效（socket 级关闭）。
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from redis_native.error_mapping import (
    REDIS_PY_ERRORS,
    spi_command,
    translate_error,
)

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import PubSubMessage, Value

#: 未订阅时 listen 自旋等待间隔（秒）。
_WAIT_SUBSCRIBED_INTERVAL = 0.05


class NativePubSubHandle:
    """PubSubHandle 协议实现（订阅连接来自独立订阅池）。"""

    def __init__(self, pubsub: Any) -> None:
        self._pubsub = pubsub
        self._closed = False

    @spi_command("subscribe")
    async def subscribe(self, *channels: Value) -> None:
        if not channels:
            raise RedisCommandError(
                "subscribe 需要至少一个频道", command="subscribe"
            )
        await self._pubsub.subscribe(*channels)

    @spi_command("psubscribe")
    async def psubscribe(self, *patterns: Value) -> None:
        if not patterns:
            raise RedisCommandError(
                "psubscribe 需要至少一个模式", command="psubscribe"
            )
        await self._pubsub.psubscribe(*patterns)

    def listen(self) -> AsyncIterator[PubSubMessage]:
        """消息迭代器（含订阅确认消息；pong 保活产物被过滤）。"""
        return self._listen()

    @spi_command("unsubscribe")
    async def unsubscribe(self, *channels: Value) -> None:
        # 空参 = 退订全部频道（redis-py 原生语义，直接透传）。
        await self._pubsub.unsubscribe(*channels)

    @spi_command("punsubscribe")
    async def punsubscribe(self, *patterns: Value) -> None:
        # 空参 = 退订全部模式。
        await self._pubsub.punsubscribe(*patterns)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._pubsub.aclose()
        except REDIS_PY_ERRORS as exc:
            raise translate_error(exc, operation="pubsub.aclose") from exc

    # ---------------------------------------------------------------- internal

    async def _listen(self) -> AsyncIterator[PubSubMessage]:
        while not self._pubsub.subscribed and not self._closed:
            await asyncio.sleep(_WAIT_SUBSCRIBED_INTERVAL)
        if self._closed:
            return
        iterator = self._pubsub.listen()
        try:
            while True:
                try:
                    raw = await iterator.__anext__()
                except StopAsyncIteration:
                    # 全部退订后 redis-py listen 循环自然结束。
                    return
                except REDIS_PY_ERRORS as exc:
                    raise translate_error(exc, operation="listen") from exc
                message = _to_message(raw)
                if message is not None:
                    yield message
        finally:
            # 消费方提前退出时收尾内层迭代器（清理路径，错误不外抛）。
            try:
                await iterator.aclose()
            except REDIS_PY_ERRORS:
                pass


def _to_message(raw: Any) -> PubSubMessage | None:
    """redis-py 消息 dict → PubSubMessage；pong 保活产物返回 None（契约外）。"""
    if not isinstance(raw, dict):
        return None
    if raw.get("type") == "pong":
        return None
    return PubSubMessage(
        type=raw.get("type", ""),
        channel=raw.get("channel"),
        data=raw.get("data"),
        pattern=raw.get("pattern"),
    )
