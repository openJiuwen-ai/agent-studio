# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""公共配置类：agent-runtime / agent-builder 共享的配置定义。

当前包含 Redis 相关配置（RedisMode / RedisSettings）。
后续如有其他跨服务共享的配置项，可继续在此模块中扩展。
"""

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from common_utils.crypto_tool import decrypt


def _decrypt(v):
    """通用解密验证器：尝试解密，失败则返回原文（明文兼容）。"""
    return decrypt(v)


class RedisMode(Enum):
    """Redis 连接模式。"""

    SINGLE = "single"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


class RedisSettings(BaseSettings):
    """Redis 配置。环境变量前缀统一为 REDIS_。

    合并 agent-runtime 与 agent-builder 两侧的 Redis 配置字段：
      - redis_transaction_enabled（来自 agent-runtime）：是否启用 redis 事务
      - datasource_ttl_seconds（来自 agent-builder）：业务写入 TTL 兜底
    """

    # 模式配置
    mode: RedisMode = Field(default=RedisMode.SINGLE, validation_alias="REDIS_MODE")

    # 单机/哨兵模式配置
    host: str = Field(default="127.0.0.1", validation_alias="REDIS_HOST")
    port: int = Field(default=6379, validation_alias="REDIS_PORT")
    db: int = Field(default=0, validation_alias="REDIS_DATABASE")
    password: Optional[str] = Field(default=None, validation_alias="REDIS_PASSWORD")
    # 是否启用 redis 事务（pipeline 默认 transaction=True/False）
    redis_transaction_enabled: bool = Field(
        default=True, validation_alias="REDIS_TRANSACTION_ENABLED"
    )

    # 集群模式配置
    cluster_nodes: str = Field(default="", validation_alias="REDIS_CLUSTER_NODES")

    # 哨兵模式配置
    sentinel_master: str = Field(
        default="mymaster", validation_alias="REDIS_SENTINEL_MASTER"
    )
    sentinel_nodes: str = Field(default="", validation_alias="REDIS_SENTINEL_NODES")

    # 连接池配置
    max_connections: int = Field(default=50, validation_alias="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(default=5, validation_alias="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(
        default=5, validation_alias="REDIS_SOCKET_CONNECT_TIMEOUT"
    )

    # SSL 配置（建议直接使用默认值就可以）
    ssl_enabled: bool = Field(default=False, validation_alias="REDIS_SSL_ENABLED")
    ssl_ca_cert: str = Field(default="", validation_alias="REDIS_SSL_CA_CERT")
    ssl_cert_file: str = Field(default="", validation_alias="REDIS_SSL_CERT_FILE")
    ssl_key_file: str = Field(default="", validation_alias="REDIS_SSL_KEY_FILE")

    # Redis 写入 TTL（秒）：用于会话状态、对话历史等业务的过期兜底，防止 key 永久驻留。
    # 与 agent_runtime 侧 jiuwen RedisUtils.set 的 REDIS_TTL 跨进程约定保持同名。
    datasource_ttl_seconds: int = Field(
        default=3 * 24 * 60 * 60, validation_alias="REDIS_TTL"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("password", mode="after")
    @classmethod
    def _decrypt_password(cls, v):
        return _decrypt(v)
