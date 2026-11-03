# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Provider 配置（RedisProviderSettings，设计文档 5.3）。

与 common_utils.RedisSettings 的关系：
  - 本模块**自包含**——redis_spi 不依赖 common_utils（企业仅凭 redis-spi 即可开发
    自研 Provider），连接字段与 env 别名同 common_utils.RedisSettings 保持同名；
  - 平台装配层（Phase 2 的 server lifespan）负责把**解密后**的连接值注入本 Settings
    ——password 在本模块不做解密（平台解密发生在 common_utils.crypto_tool 装配层；
    独立使用 / 测试时直接传明文）。

REDIS_PROVIDER 取值形态（设计文档 5.1，工厂按此解析）：
  - ``native``：内置 redis-py 实现（默认；等价不配置）；
  - ``module:Class``：已安装模块内的 Provider 类；
  - ``/path/file.py`` / ``/path/file.py:Class``：插件文件路径（缺 .py 后缀自动补）；
  - 注册名：entry_points（组 ``openjiuwen.redis_providers``）注册的插件名。
REDIS_PROVIDER_CLASS：当 REDIS_PROVIDER 为文件路径 / 模块名时的类名（与 OBS
命名对齐：MODULE + CLASS 分置两个 env 的形态同样支持）。
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from redis_spi.exceptions import RedisConfigError


class RedisMode(str, Enum):
    """Redis 连接模式。"""

    SINGLE = "single"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


class RedisProviderSettings(BaseSettings):
    """Redis Provider 装配与连接配置。

    env 前缀统一 REDIS_；extra="ignore"（.env 中其他服务变量不干扰）。
    构造可用别名 kwarg：``RedisProviderSettings(REDIS_PROVIDER="native")``；
    也接受字段名 kwarg（populate_by_name，如 ``RedisProviderSettings(provider="x")``），
    两者同给时以别名为准时须自查——建议只用一种形态。
    """

    # —— Provider 装配（设计文档 5.3）——
    provider: str = Field(default="native", validation_alias="REDIS_PROVIDER")
    provider_class: str = Field(default="", validation_alias="REDIS_PROVIDER_CLASS")
    text_mode: bool = Field(default=False, validation_alias="REDIS_TEXT_MODE")
    subscriber_pool_size: int = Field(
        default=1, ge=1, validation_alias="REDIS_SUBSCRIBER_POOL_SIZE"
    )
    blocking_pool_size: int = Field(
        default=2, ge=1, validation_alias="REDIS_BLOCKING_POOL_SIZE"
    )
    provider_config: dict[str, Any] = Field(
        default_factory=dict, validation_alias="REDIS_PROVIDER_CONFIG"
    )
    provider_config_file: str = Field(
        default="", validation_alias="REDIS_PROVIDER_CONFIG_FILE"
    )

    # —— 通用连接项（别名与 common_utils.RedisSettings 同名；native 实现与过渡层共用）——
    mode: RedisMode = Field(default=RedisMode.SINGLE, validation_alias="REDIS_MODE")
    host: str = Field(default="127.0.0.1", validation_alias="REDIS_HOST")
    port: int = Field(default=6379, ge=1, le=65535, validation_alias="REDIS_PORT")
    db: int = Field(default=0, ge=0, validation_alias="REDIS_DATABASE")
    password: str | None = Field(default=None, validation_alias="REDIS_PASSWORD")
    # 是否启用 pipeline 事务（pipeline(transaction=None) 时取此默认）
    redis_transaction_enabled: bool = Field(
        default=True, validation_alias="REDIS_TRANSACTION_ENABLED"
    )

    # 集群模式（"host:port,host:port" 逗号分隔；为空时按 host/port 单点）
    cluster_nodes: str = Field(default="", validation_alias="REDIS_CLUSTER_NODES")

    # 哨兵模式（"host:port,host:port" 逗号分隔）
    sentinel_master: str = Field(
        default="mymaster", validation_alias="REDIS_SENTINEL_MASTER"
    )
    sentinel_nodes: str = Field(default="", validation_alias="REDIS_SENTINEL_NODES")
    # 哨兵节点自身的认证密码（与数据节点 password 独立——哨兵集群启用
    # requirepass 时必填；沿用旧 DATASOURCE_REDIS 体系同名环境变量）
    sentinel_password: str | None = Field(
        default=None, validation_alias="REDIS_SENTINEL_PASSWORD"
    )

    # 连接池
    max_connections: int = Field(default=50, ge=1, validation_alias="REDIS_MAX_CONNECTIONS")
    socket_timeout: float = Field(default=5.0, gt=0, validation_alias="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: float = Field(
        default=5.0, gt=0, validation_alias="REDIS_SOCKET_CONNECT_TIMEOUT"
    )

    # SSL
    ssl_enabled: bool = Field(default=False, validation_alias="REDIS_SSL_ENABLED")
    ssl_ca_cert: str = Field(default="", validation_alias="REDIS_SSL_CA_CERT")
    ssl_cert_file: str = Field(default="", validation_alias="REDIS_SSL_CERT_FILE")
    ssl_key_file: str = Field(default="", validation_alias="REDIS_SSL_KEY_FILE")

    # 业务写入 TTL 兜底（秒；与 agent-builder 侧 REDIS_TTL 跨进程约定同名）
    datasource_ttl_seconds: int = Field(
        default=3 * 24 * 60 * 60, gt=0, validation_alias="REDIS_TTL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("provider_config", mode="before")
    @classmethod
    def _parse_provider_config(cls, value: Any) -> dict[str, Any]:
        """REDIS_PROVIDER_CONFIG 支持 JSON 字符串或 dict。"""
        if value is None or value == "":
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"REDIS_PROVIDER_CONFIG must be valid JSON: {exc}"
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError("REDIS_PROVIDER_CONFIG must decode to a JSON object")
            return parsed
        raise ValueError(
            f"REDIS_PROVIDER_CONFIG must be a JSON object string or dict, "
            f"got {type(value).__name__}"
        )

    def raw_provider_config(self) -> dict[str, Any]:
        """合并后的 Provider 专属透传配置：文件内容 + 内联 provider_config（内联优先）。

        - provider_config_file：JSON 文件路径（卷挂载场景）；
        - 读取/解析失败抛 RedisConfigError（fail-fast，不静默忽略）；
        - 返回新建 dict（不暴露内部可变引用）。
        """
        merged: dict[str, Any] = {}
        if self.provider_config_file:
            try:
                with open(self.provider_config_file, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
            except OSError as exc:
                raise RedisConfigError(
                    f"cannot read REDIS_PROVIDER_CONFIG_FILE "
                    f"'{self.provider_config_file}': {exc}"
                ) from exc
            except ValueError as exc:
                # JSONDecodeError（非法 JSON）与 UnicodeDecodeError（非 UTF-8 编码，
                # 中文 Windows 环境真实发生的运维错误）统一收口为配置错误。
                raise RedisConfigError(
                    f"REDIS_PROVIDER_CONFIG_FILE "
                    f"'{self.provider_config_file}' is not valid UTF-8 JSON: {exc}"
                ) from exc
            if not isinstance(loaded, dict):
                raise RedisConfigError(
                    f"REDIS_PROVIDER_CONFIG_FILE "
                    f"'{self.provider_config_file}' must contain a JSON object"
                )
            merged.update(loaded)
        merged.update(self.provider_config)
        return merged
