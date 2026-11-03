# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""NativeRedisClient：SPI 核心协议（RedisClient）的 redis-py 委托实现。

装配形态（设计文档 §4.3 独立池约定）：
  - ``main``：业务命令池（settings.max_connections）；
  - ``subscriber``：订阅独立池（subscriber_pool_size；cluster 模式回退共享）；
  - ``blocking``：阻塞命令独立池（blocking_pool_size；cluster 模式回退共享）。

生命周期：
  - ``aclose()`` 幂等，关闭全部底层客户端（不重复关共享实例）；
  - ``ping()`` 供工厂装配后首检与业务健康检查。
"""

from __future__ import annotations

from typing import Any

from redis_native.capabilities import SUPPORTED_CAPABILITIES, capability_view
from redis_native.collection_commands import (
    HashCommandsMixin,
    ListCommandsMixin,
    SetCommandsMixin,
)
from redis_native.core_commands import (
    KeyCommandsMixin,
    ScanCommandsMixin,
    StringCommandsMixin,
)
from redis_native.error_mapping import REDIS_PY_ERRORS, spi_command, translate_error
from redis_native.pipeline import NativePipeline

from redis_spi.exceptions import CapabilityNotSupportedError


class NativeRedisClient(
    KeyCommandsMixin,
    StringCommandsMixin,
    ScanCommandsMixin,
    HashCommandsMixin,
    ListCommandsMixin,
    SetCommandsMixin,
):
    """核心面聚合实现（结构化满足 redis_spi.protocols.RedisClient）。"""

    def __init__(
        self,
        main: Any,
        *,
        subscriber: Any = None,
        blocking: Any = None,
        text_mode: bool = False,
        transaction_default: bool = True,
    ) -> None:
        self._redis = main
        # 独立池缺省回退主池（cluster 模式 / 测试替身场景）。
        self._subscriber = subscriber if subscriber is not None else main
        self._blocking = blocking if blocking is not None else main
        self._text_mode = text_mode
        self._transaction_default = transaction_default
        self._closed = False

    # ---- 生命周期与能力探测（RedisClient 协议）----

    @property
    def text_mode(self) -> bool:
        return self._text_mode

    @property
    def redis_client(self) -> Any:
        """主连接池的只读暴露（capability_view 构造能力视图用，包外只读）。"""
        return self._redis

    @property
    def subscriber_client(self) -> Any:
        """订阅通道连接池（缺省回退主池）的只读暴露。"""
        return self._subscriber

    @property
    def blocking_client(self) -> Any:
        """阻塞命令连接池（缺省回退主池）的只读暴露。"""
        return self._blocking

    @spi_command("ping")
    async def ping(self) -> bool:
        return await self._redis.ping()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        failures: list[BaseException] = []
        for underlying in self._underlying_clients():
            try:
                await underlying.aclose()
            except REDIS_PY_ERRORS as exc:
                failures.append(exc)
        if failures:
            # 全部尝试关闭后抛首个错误（不掩盖其余关闭失败的事实由 __cause__ 链承载）。
            raise translate_error(failures[0], operation="aclose") from failures[0]

    def supports(self, capability: type) -> bool:
        return capability in SUPPORTED_CAPABILITIES

    def as_capability(self, capability: type) -> Any:
        view = capability_view(self, capability)
        if view is None:
            raise CapabilityNotSupportedError(
                f"native provider does not implement capability "
                f"{getattr(capability, '__name__', capability)}",
                capability=capability,
            )
        return view

    def pipeline(self, *, transaction: bool | None = None) -> NativePipeline:
        resolved = self._transaction_default if transaction is None else transaction
        return NativePipeline(self._redis.pipeline(transaction=resolved))

    def native_client(self) -> Any:
        """过渡期兼容视图（Q3）：真实 redis-py 客户端。

        供 agent-core 注入与 common_utils.redis_manager 过渡委托使用；
        Phase 4 业务全量迁移后随 compat 层一并收口。
        """
        return self._redis

    # ---------------------------------------------------------------- internal

    def _underlying_clients(self) -> list[Any]:
        """待关闭的底层客户端（去重：独立池回退主池时不重复关）。"""
        unique: list[Any] = []
        for client in (self._redis, self._subscriber, self._blocking):
            if client not in unique:
                unique.append(client)
        return unique
