# -*- coding: utf-8 -*-
"""公共工具层共享包（runtime / agent-builder 共用）。

集中存放跨服务的通用工具类，避免重复实现漂移。
当前包含：
  - 加解密工具（crypto_tool）
  - 公共配置（common_config：RedisMode / RedisSettings）
  - Redis 客户端管理（redis_manager：RedisClientManager 等）
"""

from .crypto_tool import (
    BaseCrypt,
    CryptUtils,
    CryptTool,
    PlainCrypt,
    encrypt,
    decrypt,
)
from .common_config import RedisMode, RedisSettings
from .redis_manager import (
    RedisClientManager,
    get_redis_client,
    get_sync_redis_client,
)

__all__ = [
    # crypto
    "BaseCrypt",
    "CryptUtils",
    "CryptTool",
    "PlainCrypt",
    "encrypt",
    "decrypt",
    # common_config
    "RedisMode",
    "RedisSettings",
    # redis_manager
    "RedisClientManager",
    "get_redis_client",
    "get_sync_redis_client",
]
