# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""PubSubCapability 实现（订阅走独立订阅池，发布走业务命令池）。"""

from __future__ import annotations

from redis_native.error_mapping import spi_command
from redis_native.pubsub_handle import NativePubSubHandle

from redis_spi.types import Value


class NativePubSubCapability:
    """PubSub 能力组。

    订阅句柄从**订阅池客户端**创建（subscriber_pool_size 独立池，默认 1——
    长期占用订阅连接不侵蚀业务命令池）；PUBLISH 是普通命令，走业务主池。
    """

    def __init__(self, main, subscriber) -> None:
        self._main = main
        self._subscriber = subscriber

    def pubsub(self) -> NativePubSubHandle:
        return NativePubSubHandle(self._subscriber.pubsub())

    @spi_command("publish")
    async def publish(self, channel: Value, message: Value) -> int:
        return await self._main.publish(channel, message)
