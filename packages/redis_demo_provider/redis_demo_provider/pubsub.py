# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Acme demo：PubSub 订阅句柄（fakeredis pubsub 委托）。"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from redis_demo_provider.errors import REDIS_PY_ERRORS, acme_command, acme_translate

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import PubSubMessage, Value

#: 未订阅时 listen 自旋等待间隔（秒）。
_WAIT_SUBSCRIBED_INTERVAL = 0.05


class AcmePubSubHandle:
    """PubSubHandle 协议实现（demo 形态一）。

    与 fakeredis（redis-py asyncio）行为对齐：未订阅时 listen 自旋等待
    首个订阅（支持"先迭代后订阅"）；订阅确认消息透传；pong 保活过滤。
    """

    def __init__(self, pubsub: Any) -> None:
        self._pubsub = pubsub
        self._closed = False

    @acme_command("subscribe")
    async def subscribe(self, *channels: Value) -> None:
        if not channels:
            raise RedisCommandError("subscribe 需要至少一个频道", command="subscribe")
        await self._pubsub.subscribe(*channels)

    @acme_command("psubscribe")
    async def psubscribe(self, *patterns: Value) -> None:
        if not patterns:
            raise RedisCommandError("psubscribe 需要至少一个模式", command="psubscribe")
        await self._pubsub.psubscribe(*patterns)

    def listen(self) -> AsyncIterator[PubSubMessage]:
        return self._listen()

    @acme_command("unsubscribe")
    async def unsubscribe(self, *channels: Value) -> None:
        # 空参 = 退订全部频道（redis-py 原生语义）。
        await self._pubsub.unsubscribe(*channels)

    @acme_command("punsubscribe")
    async def punsubscribe(self, *patterns: Value) -> None:
        await self._pubsub.punsubscribe(*patterns)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._pubsub.aclose()
        except REDIS_PY_ERRORS as exc:
            raise acme_translate(exc, operation="pubsub.aclose") from exc

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
                    return
                except REDIS_PY_ERRORS as exc:
                    raise acme_translate(exc, operation="listen") from exc
                message = _to_message(raw)
                if message is not None:
                    yield message
        finally:
            try:
                await iterator.aclose()
            except REDIS_PY_ERRORS:
                pass


def _to_message(raw: Any) -> PubSubMessage | None:
    """redis-py 消息 dict → PubSubMessage；pong 保活产物返回 None。"""
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
