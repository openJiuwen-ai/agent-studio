# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Redis Provider 启动装配（common_utils 共享版：agent-runtime 与 agent-builder 共用）。

自 agent_runtime.serve.redis_bootstrap 下沉（builder 纳入 Provider 时移动到共享包，
runtime 侧保留同名 re-export 薄壳，既有 import 路径不变）。

平台装配层职责（redis_spi.config 约定「平台装配层 = server lifespan」）：
  - 读取 common_utils.RedisSettings（password 已在其 field_validator 层解密）；
  - 映射为 redis_spi.RedisProviderSettings：连接字段同名搬运，Provider 装配字段
    （REDIS_PROVIDER / REDIS_PROVIDER_CLASS / 池尺寸等）由其自身 env 别名读取；
  - 经 redis_spi.accessor 完成进程级装配（RedisProviderFactory 内置 ping fail-fast）；
  - 装配成功后向 common_utils.redis_manager 注册同步兼容桥（sync-over-async），
    使既有同步调用方（builder 的 history 存储）零改动切换到 Provider。

依赖说明：本模块顶层导入 redis_spi，仅适用于已安装适配层包的环境（agent-runtime /
agent-builder 共享 venv）；未安装环境的调用方应 try/except ImportError 回退 legacy。

行为口径（Phase 2 验证 + Phase 4 修订）：
  - 未配置（REDIS_HOST / REDIS_CLUSTER_NODES 全空）：返回 None，由 lifespan 抛出
    与旧实现一致的 RuntimeError；
  - 连接/命令类装配失败：抛 RuntimeError("Redis connection check failed: ...")
    （对齐旧 lifespan 文案）；配置类错误（RedisConfigError）原样上抛；
  - 缺省 native（REDIS_PROVIDER 未配置）= redis-py 直连，连接参数与旧
    RedisClientManager 逐字段一致；
  - **builder 启动语义变化**：旧 _ping_redis 为 warn-and-continue，适配层
    装配期 ping fail-fast 直接终止进程（见 agent_builder server_fastapi
    lifespan docstring 的决策论证：半可用慢性故障显式失败更可运维）。
    Redis 为平台声明的必选依赖，无 Redis 环境须显式部署 Redis 或回退
    旧版本（升级注意事项见开发指南 Redis 章节）。
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from common_utils.common_config import RedisSettings
from common_utils.redis_manager import RedisClientManager
from common_utils.redis_sync_compat import SyncCompatClient
from redis_spi import RedisMode, RedisProviderSettings, accessor
from redis_spi.exceptions import RedisConfigError, RedisError
from redis_spi.factory import RedisProviderFactory

logger = logging.getLogger(__name__)

#: 本进程已注册的同步兼容桥（幂等判断：与 accessor 均就绪则重复调用早退）
_sync_bridge: SyncCompatClient | None = None

#: 两包 Settings 的同名连接字段（password 已在 RedisSettings 层解密后搬运）。
#: mode 不在此列：两包各有一套同名同值枚举，按 value 重导出（不做类身份耦合）。
_SHARED_CONNECTION_FIELDS = (
    "host",
    "port",
    "db",
    "password",
    "redis_transaction_enabled",
    "cluster_nodes",
    "sentinel_master",
    "sentinel_nodes",
    "max_connections",
    "socket_timeout",
    "socket_connect_timeout",
    "ssl_enabled",
    "ssl_ca_cert",
    "ssl_cert_file",
    "ssl_key_file",
    "datasource_ttl_seconds",
)


def build_provider_settings(
    legacy: RedisSettings | None = None,
) -> RedisProviderSettings:
    """common_utils.RedisSettings → redis_spi.RedisProviderSettings。

    - 连接字段同名搬运（socket_timeout int→float 由 pydantic 宽化，数值不变）；
    - Provider 装配字段不搬运：由 RedisProviderSettings 自身 env 别名读取，
      REDIS_PROVIDER 未配置时缺省 native（redis-py 直连）。
    """
    legacy = legacy if legacy is not None else RedisSettings()
    overrides: dict[str, Any] = {
        field: getattr(legacy, field) for field in _SHARED_CONNECTION_FIELDS
    }
    overrides["mode"] = RedisMode(legacy.mode.value)
    return RedisProviderSettings(_env_file=None, **overrides)


async def init_redis_provider(settings: RedisSettings | None = None) -> Any:
    """装配 Redis Provider，返回 redis-py 原生视图（过渡期注入面）。

    - settings 缺省时按环境构造（与旧 RedisClientManager.init() 同源同判据）；
    - 未配置返回 None（由 lifespan 转为旧口径 RuntimeError）；
    - 幂等：accessor 与同步桥均装配后，重复调用复用既有装配与视图
      （同步桥为自持循环+专属连接池，重复注册会泄漏，必须早退）；
    - 返回值（主池客户端）与 common_utils.get_redis_client() 过渡委托返回
      同一对象，保持旧「全局单客户端身份」不变量；
    - 原生视图在同步桥注册**之前**获取：非 native 且无兼容视图的 Provider
      在此处 fail-fast，不产生「桥已注册而视图不可用」的半注册态；
    - 装配成功后注册同步兼容桥，使 get_sync_client() 的既有同步调用方
      （builder history 存储）零改动切换 Provider。
    """
    global _sync_bridge
    legacy = settings if settings is not None else RedisSettings()
    if not legacy.host and not legacy.cluster_nodes:
        logger.warning("Redis not configured, provider not initialized.")
        return None

    # 幂等早退：主装配与同步桥均就绪时复用（视图对同一 client 稳定可重复取）
    if _sync_bridge is not None and accessor.is_initialized():
        return _as_native_view(accessor.get_redis())

    try:
        provider_settings = build_provider_settings(legacy)
    except ValidationError as exc:
        # pydantic 校验错误消息含 input_value= 原始配置（可能带企业凭证），
        # 重包装为只含错误位置的自描述配置错误
        locations = "; ".join(str(e.get("loc", "?")) for e in exc.errors()[:5])
        raise RedisConfigError(
            f"Redis Provider 配置校验失败（字段: {locations}），"
            "请检查 REDIS_PROVIDER_CONFIG 等 REDIS_* 环境变量"
        ) from exc

    try:
        client = await accessor.initialize(provider_settings)
    except RedisConfigError:
        # 配置类错误原样上抛（对齐旧 init() 对配置异常的透传行为）
        raise
    except RedisError as exc:
        # 连接/命令类失败对齐旧 lifespan 口径（RuntimeError 文案不变）
        raise RuntimeError(f"Redis connection check failed: {exc}") from exc

    # 先取原生视图：非 native 且无兼容视图在此 fail-fast（无半注册态）
    native = _as_native_view(client)

    # 注册同步兼容桥：自持专用后台循环 + 经 RedisProviderFactory.create 独立装配
    # 专属客户端（与主客户端互不共享连接池）。任意线程（含事件循环线程，如
    # builder Controller 在 Executor.__init__ 里同步调 load_session 的场景）的
    # 同步调用都调度到桥循环执行，无死锁。
    if _sync_bridge is not None:
        _sync_bridge.close()
    sync_bridge = SyncCompatClient(
        lambda: RedisProviderFactory.create(provider_settings)
    )
    try:
        sync_bridge.initialize()
    except Exception:
        # 同步面装配失败不拖垮主客户端装配（异步面已可用），warn 后不注册
        logger.warning("SyncCompatClient init failed, sync path stays legacy", exc_info=True)
    else:
        RedisClientManager.set_sync_compat(sync_bridge)
        _sync_bridge = sync_bridge

    logger.info(
        "Redis client initialized: provider=%s, mode=%s, host=%s:%s",
        provider_settings.provider,
        provider_settings.mode.value,
        provider_settings.host,
        provider_settings.port,
    )
    return native


def _as_native_view(client: Any) -> Any:
    """取 redis-py 原生视图（仅 native provider；函数内延迟导入兼容独立环境）。"""
    from redis_native.compat import as_native_client

    return as_native_client(client)
