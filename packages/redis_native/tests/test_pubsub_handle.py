# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""NativePubSubHandle 单测：订阅语义 / 消息映射 / 自旋保活 / 生命周期。

自旋语义（契约允许"自旋保活或阻塞等订阅"）：redis-py listen() 为
``while subscribed:``——未订阅立即退出；实现先自旋等待首个订阅或句柄关闭，
支持"先迭代后订阅"形态（真实时序验证，非仅 mock 调用序列）。
"""

from __future__ import annotations

import asyncio

import pytest
import redis.exceptions as redis_exc

from redis_native.pubsub_handle import NativePubSubHandle

from redis_spi.exceptions import (
    RedisCommandError,
    RedisConnectionError,
    RedisTimeoutError,
)
from redis_spi.types import PubSubMessage

from redis_native_test_fakes import FakePubSub


def make_handle(
    messages: list | None = None,
    listen_error: BaseException | None = None,
    aclose_error: BaseException | None = None,
) -> tuple[NativePubSubHandle, FakePubSub]:
    fake = FakePubSub(
        messages=messages, listen_error=listen_error, aclose_error=aclose_error
    )
    return NativePubSubHandle(fake), fake


class TestSubscription:
    @staticmethod
    def test_subscribe_empty_rejected():
        handle, fake = make_handle()
        with pytest.raises(RedisCommandError, match="至少一个频道"):
            asyncio.run(handle.subscribe())
        assert fake.operations == []

    @staticmethod
    def test_psubscribe_empty_rejected():
        handle, fake = make_handle()
        with pytest.raises(RedisCommandError, match="至少一个模式"):
            asyncio.run(handle.psubscribe())
        assert fake.operations == []

    @staticmethod
    def test_subscribe_delegates():
        handle, fake = make_handle()
        asyncio.run(handle.subscribe("ch1", "ch2"))
        assert fake.operations == [("subscribe", ("ch1", "ch2"))]
        assert fake.subscribed is True

    @staticmethod
    def test_psubscribe_delegates():
        handle, fake = make_handle()
        asyncio.run(handle.psubscribe("ch.*"))
        assert fake.operations == [("psubscribe", ("ch.*",))]
        assert fake.subscribed is True

    @staticmethod
    def test_unsubscribe_empty_means_all():
        handle, fake = make_handle()
        asyncio.run(handle.subscribe("ch"))
        asyncio.run(handle.unsubscribe())
        assert fake.subscribed is False
        assert fake.operations[-1] == ("unsubscribe", ())

    @staticmethod
    def test_unsubscribe_specific_passthrough():
        handle, fake = make_handle()
        asyncio.run(handle.unsubscribe("ch1"))
        assert fake.operations == [("unsubscribe", ("ch1",))]

    @staticmethod
    def test_punsubscribe_passthrough():
        handle, fake = make_handle()
        asyncio.run(handle.punsubscribe("ch.*"))
        assert fake.operations == [("punsubscribe", ("ch.*",))]


class TestListenMessageMapping:
    @staticmethod
    def collect(handle: NativePubSubHandle) -> list[PubSubMessage]:
        async def run():
            return [message async for message in handle.listen()]

        return asyncio.run(asyncio.wait_for(run(), timeout=2))

    def test_message_mapping(self):
        handle, fake = make_handle(
            messages=[
                {"type": "message", "channel": b"ch", "data": b"hello", "pattern": None},
                {"type": "subscribe", "channel": b"ch", "data": 1, "pattern": None},
                {"type": "pmessage", "pattern": b"ch.*", "channel": b"ch1", "data": b"x"},
            ]
        )
        fake.subscribed = True  # 已订阅形态，直接进入内层迭代
        messages = self.collect(handle)
        assert messages == [
            PubSubMessage(type="message", channel=b"ch", data=b"hello", pattern=None),
            PubSubMessage(type="subscribe", channel=b"ch", data=1, pattern=None),
            PubSubMessage(type="pmessage", channel=b"ch1", data=b"x", pattern=b"ch.*"),
        ]

    def test_pong_and_non_dict_filtered(self):
        handle, fake = make_handle(
            messages=[
                {"type": "pong", "channel": None, "data": 1, "pattern": None},
                "not-a-dict",
                {"type": "message", "channel": b"ch", "data": b"v", "pattern": None},
            ]
        )
        fake.subscribed = True
        messages = self.collect(handle)
        assert len(messages) == 1
        assert messages[0].data == b"v"

    def test_listen_error_translated(self):
        handle, fake = make_handle(
            messages=[{"type": "message", "channel": b"ch", "data": b"v", "pattern": None}],
            listen_error=redis_exc.ConnectionError("broker gone"),
        )
        fake.subscribed = True
        with pytest.raises(RedisConnectionError) as excinfo:
            self.collect(handle)
        assert excinfo.value.operation == "listen"
        assert isinstance(excinfo.value.__cause__, redis_exc.ConnectionError)


class TestSpinWait:
    def test_listen_waits_for_late_subscription(self):
        # 先迭代后订阅：listen 自旋 > 2 个周期后才出现订阅，消息不丢
        handle, fake = make_handle(
            messages=[
                {"type": "message", "channel": b"ch", "data": b"late", "pattern": None}
            ]
        )

        async def run():
            task = asyncio.ensure_future(self._consume(handle))
            await asyncio.sleep(0.12)  # > 2 × 0.05 自旋间隔
            assert not task.done(), "未订阅时 listen 不应提前结束"
            await handle.subscribe("ch")
            return await asyncio.wait_for(task, timeout=2)

        assert asyncio.run(run()) == [
            PubSubMessage(type="message", channel=b"ch", data=b"late", pattern=None)
        ]

    def test_aclose_stops_spin_wait(self):
        # 句柄关闭打断自旋等待：迭代器安静结束（不抛错、不产出）
        handle, fake = make_handle()

        async def run():
            task = asyncio.ensure_future(self._consume(handle))
            await asyncio.sleep(0.08)
            await handle.aclose()
            return await asyncio.wait_for(task, timeout=2)

        assert asyncio.run(run()) == []

    @staticmethod
    async def _consume(handle: NativePubSubHandle) -> list[PubSubMessage]:
        return [message async for message in handle.listen()]


class TestLifecycle:
    @staticmethod
    def test_aclose_idempotent():
        handle, fake = make_handle()
        asyncio.run(handle.aclose())
        asyncio.run(handle.aclose())
        assert fake.closed is True
        assert fake.operations.count(("aclose", ())) == 1

    @staticmethod
    def test_aclose_error_translated():
        handle, fake = make_handle(aclose_error=redis_exc.TimeoutError("t/o"))
        with pytest.raises(RedisTimeoutError):
            asyncio.run(handle.aclose())
        # 底层已标记关闭（尽力而为口径），失败已上抛
        assert fake.closed is True
