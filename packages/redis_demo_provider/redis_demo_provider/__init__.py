# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis_demo_provider：企业自研 Redis Provider 的可运行参照（设计文档 §八）。

两种形态（README 有选型说明）：
  1. **fakeredis 形态（默认，REDIS_PROVIDER=acme_demo）**：独立实现
     RedisProvider + 核心客户端（不依赖 redis-native），全内存离线可跑——
     CI / 离线演示 / 验收第 3 条的执行入口；
  2. **Wrapper 形态（REDIS_PROVIDER=acme_wrapper）**：包装 NativeRedisClient，
     逐命令结构化日志 + 延迟/失败/限流注入 + appId/passport 鉴权演示
     （REDIS_PROVIDER_CONFIG 专属参数）。

快速开始::

    pip install -e packages/redis_demo_provider
    REDIS_PROVIDER=acme_demo python -c "import asyncio; from redis_spi import accessor; \\
        print(asyncio.run(accessor.initialize()).ping())"

用契约套件自证（企业接入验收的标准动作）::

    REDIS_CONTRACT_TARGET=acme_demo python -m pytest --pyargs redis_contract_tests -v

产物边界：demo 包不进 studio-runtime 生产镜像（requirements/Dockerfile 均不含）。
"""

from redis_demo_provider.client import AcmeDemoClient
from redis_demo_provider.provider import AcmeDemoProvider
from redis_demo_provider.wrapper import InstrumentedClient, WrapperDemoProvider

__all__ = [
    "AcmeDemoClient",
    "AcmeDemoProvider",
    "InstrumentedClient",
    "WrapperDemoProvider",
]
