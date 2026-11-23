# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis_native：redis_spi 的内置原生实现（redis-py 委托）。

产物边界（设计文档 §3.2/§十三）：
  - 本包与 redis_spi 进运行时镜像与 requirements；
  - runtime 树内**唯一允许 import redis 的包**（CI grep 白名单，设计文档 §六）；
  - `RedisProviderFactory` 内置 native 短路（REDIS_PROVIDER=native / 缺省）。

模块布局：
  - provider：NativeRedisProvider（生命周期 + 能力声明 + native 兼容视图）；
  - connection：single/cluster/sentinel 三模式客户端构建（自 common_utils 迁入）；
  - error_mapping：redis-py 异常 → redis_spi 异常翻译 + @spi_command 装饰器；
  - client / core_commands / collection_commands：核心面实现；
  - pipeline：NativePipeline；pubsub_handle：订阅独立池句柄；
  - capabilities/：八个可选能力组实现；
  - compat：过渡期 native handle 透出（Phase 4 收口后移除）。
"""

from redis_native.client import NativeRedisClient
from redis_native.compat import as_native_client
from redis_native.pipeline import NativePipeline
from redis_native.provider import NativeRedisProvider
from redis_native.pubsub_handle import NativePubSubHandle

__version__ = "0.1.0"

__all__ = [
    "NativeRedisProvider",
    "NativeRedisClient",
    "NativePipeline",
    "NativePubSubHandle",
    "as_native_client",
    "__version__",
]
