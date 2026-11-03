# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis_spi：Redis 适配层 SPI（能力协议 + 契约类型 + 异常体系 + Provider 工厂）。

零 redis-py 依赖——企业仅凭本包即可开发自研 Provider：

    from redis_spi import RedisProvider, RedisProviderSettings

    class MyProvider(RedisProvider):
        async def start(self, settings): ...
        async def stop(self): ...

接入方式见 config.RedisProviderSettings 与 factory.RedisProviderFactory。
"""

from redis_spi.accessor import (
    aclose,
    await_provider_ready,
    get_redis,
    get_redis_or_none,
    initialize,
    is_initialized,
    reset,
)
from redis_spi.capabilities import (
    BitmapCapability,
    BlockingCommands,
    CounterCapability,
    GeoCapability,
    HyperLogLogCapability,
    PubSubCapability,
    PubSubHandle,
    ScriptingCapability,
    SortedSetCapability,
)
from redis_spi.config import RedisMode, RedisProviderSettings
from redis_spi.exceptions import (
    REDIS_ERROR_CODE_BASE,
    CapabilityNotSupportedError,
    RedisAuthFailureError,
    RedisClusterError,
    RedisCommandError,
    RedisConfigError,
    RedisConnectionError,
    RedisError,
    RedisScriptError,
    RedisTimeoutError,
    RedisWrongTypeError,
)
from redis_spi.factory import RedisProvider, RedisProviderFactory
from redis_spi.protocols import (
    HashCommands,
    KeyCommands,
    ListCommands,
    Pipeline,
    PipelineCommands,
    RedisClient,
    ScanCommands,
    SetCommands,
    StringCommands,
)
from redis_spi.registry import (
    ENTRY_POINT_GROUP,
    available_names,
    register_provider,
    unregister_provider,
)
from redis_spi.types import (
    SCAN_START,
    Duration,
    GeoMember,
    GeoUnit,
    Key,
    PubSubMessage,
    ScanBatch,
    ScanCursor,
    ScoreBoundary,
    ScoreMember,
    SetCondition,
    Value,
)

__version__ = "0.1.0"

__all__ = [
    # 类型与值对象
    "Duration", "GeoMember", "GeoUnit", "Key", "PubSubMessage", "SCAN_START",
    "ScanBatch", "ScanCursor", "ScoreBoundary", "ScoreMember", "SetCondition", "Value",
    # 异常体系
    "REDIS_ERROR_CODE_BASE", "CapabilityNotSupportedError", "RedisAuthFailureError",
    "RedisClusterError", "RedisCommandError", "RedisConfigError",
    "RedisConnectionError", "RedisError", "RedisScriptError", "RedisTimeoutError",
    "RedisWrongTypeError",
    # 核心协议
    "HashCommands", "KeyCommands", "ListCommands", "Pipeline", "PipelineCommands",
    "RedisClient", "ScanCommands", "SetCommands", "StringCommands",
    # 可选能力组
    "BitmapCapability", "BlockingCommands", "CounterCapability", "GeoCapability",
    "HyperLogLogCapability", "PubSubCapability", "PubSubHandle", "ScriptingCapability",
    "SortedSetCapability",
    # 配置 / 工厂 / 注册表 / 访问器
    "RedisMode", "RedisProviderSettings",
    "RedisProvider", "RedisProviderFactory",
    "ENTRY_POINT_GROUP", "available_names", "register_provider", "unregister_provider",
    "aclose", "await_provider_ready", "get_redis", "get_redis_or_none",
    "initialize", "is_initialized", "reset",
]
