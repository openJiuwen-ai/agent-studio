# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""AcmeDemoProvider（demo 形态一）：fakeredis 后端的独立 Provider。

企业实现参考——一个 Provider 最少要写什么：
  1. ``start(settings)``：用你的 SDK 建客户端并固化为 SPI 客户端
     （text_mode 构造期固化；``settings.raw_provider_config()`` 取专属参数）；
  2. ``stop()``：幂等回收（与 start 对称）；
  3. ``capabilities()``：声明核心之外实现的能力组（未声明组调用即报错，
     契约套件按声明自动 skip——"实现多少声明多少"）。

形态一不依赖 redis-native / redis-py 进程连接：fakeredis 全内存，无需外部
Redis——用于 CI、离线演示与验收第 3 条（自研 Provider 不改框架接入）。
"""

from __future__ import annotations

import logging

from redis_demo_provider.client import AcmeDemoClient, SUPPORTED_CAPABILITIES

from redis_spi.config import RedisProviderSettings
from redis_spi.factory import RedisProvider
from redis_spi.protocols import RedisClient

logger = logging.getLogger(__name__)


class AcmeDemoProvider(RedisProvider):
    """fakeredis 形态（推荐默认）：REDIS_PROVIDER=acme_demo（entry_points）。"""

    def __init__(self) -> None:
        self._client: AcmeDemoClient | None = None

    async def start(self, settings: RedisProviderSettings) -> RedisClient:
        import fakeredis.aioredis  # 延迟导入：包安装即可用，导入失败即装配期报错

        raw_config = settings.raw_provider_config()
        if raw_config:
            # 专属参数透传演示：形态一不消费，仅记录（企业在此传给自研 SDK）。
            logger.info(
                "acme_demo 收到 %d 项专属配置（形态一不消费）：%s",
                len(raw_config),
                ",".join(sorted(raw_config)),
            )
        underlying = fakeredis.aioredis.FakeRedis(decode_responses=settings.text_mode)
        self._client = AcmeDemoClient(
            underlying,
            text_mode=settings.text_mode,
            transaction_default=settings.redis_transaction_enabled,
        )
        return self._client

    async def stop(self) -> None:
        if self._client is not None:
            client, self._client = self._client, None
            await client.aclose()

    def capabilities(self) -> list[type]:
        return list(SUPPORTED_CAPABILITIES)
