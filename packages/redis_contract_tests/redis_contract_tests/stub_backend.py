# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""契约后端：委托层替身（设计文档 §七 后端 4，CI 默认离线后端）。

以手写内存替身（redis-py 签名对齐）构造 ``NativeRedisClient``，跑同一套
核心契约——零外部依赖即可回归 redis_native 的翻译链路。

用法::

    REDIS_CONTRACT_TARGET=redis_contract_tests.stub_backend:StubRedisProvider \\
        python -m pytest --pyargs redis_contract_tests

能力组口径：替身仅实现核心命令面，故 ``supports()`` 恒 False——能力组契约
用例对本后端自动 skip（设计如此：替身回归的是核心翻译链路；能力组语义由
fakeredis / 真实实例后端验证）。
"""

from __future__ import annotations

from typing import Any

from redis_contract_tests.stubs.redis_py_stub import InMemoryRedisPyStub

from redis_native.client import NativeRedisClient
from redis_spi.exceptions import CapabilityNotSupportedError
from redis_spi.factory import RedisProvider
from redis_spi.config import RedisProviderSettings
from redis_spi.protocols import RedisClient


class StubBackedClient(NativeRedisClient):
    """核心面限定视图：替身未实现能力组命令，能力探测一律不支持。

    继承 NativeRedisClient（核心翻译链路即被测对象），仅覆写能力面。
    """

    def supports(self, capability: type) -> bool:
        return False

    def as_capability(self, capability: type) -> Any:
        raise CapabilityNotSupportedError(
            f"stub backend 仅实现核心命令面，不提供能力组视图："
            f"{getattr(capability, '__name__', capability)}",
            capability=capability,
        )


class StubRedisProvider(RedisProvider):
    """委托层替身 Provider（无外部连接；每次 start 产出全新内存存储）。"""

    def __init__(self) -> None:
        self._client: StubBackedClient | None = None

    async def start(self, settings: RedisProviderSettings) -> RedisClient:
        stub = InMemoryRedisPyStub()
        self._client = StubBackedClient(
            stub,
            text_mode=settings.text_mode,
            transaction_default=settings.redis_transaction_enabled,
        )
        return self._client

    async def stop(self) -> None:
        if self._client is not None:
            client, self._client = self._client, None
            await client.aclose()

    def capabilities(self) -> list[type]:
        return []
