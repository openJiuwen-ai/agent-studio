# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis-py 异步客户端构建（single / cluster / sentinel 三模式）。

自 ``common_utils.redis_manager.RedisClientManager`` 的连接构建逻辑迁入
（设计文档 §六 Phase 1 第 2 条：NativeRedisProvider 复用现有连接创建逻辑，
保证产出行与旧 client 一致——本模块与其保持参数级对齐）：

  - 同样的 connection_kwargs / ClusterNode 解析 / Sentinel.master_for 写法；
  - ``redis_transaction_enabled=False`` 时用 ``_NonTransactionRedis`` 包装类
    翻转 pipeline 默认（兼容既有调用点裸 ``.pipeline()`` 的默认行为）；
  - ``decode_responses`` 由 SPI ``text_mode`` 驱动（旧代码恒 False，行为不变）。

独立池（设计文档 §4.3）：订阅与阻塞命令各建独立客户端（独立连接池）。
集群模式的独立池暂不拆分（redis-py cluster 自带节点级连接管理，另建实例
代价是重复拓扑发现）——single/sentinel 拆、cluster 共享主池，Phase 4 复评。
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Union

from redis.asyncio import Redis
from redis.asyncio.cluster import ClusterNode, RedisCluster
from redis.asyncio.sentinel import Sentinel

from redis_spi.config import RedisMode, RedisProviderSettings
from redis_spi.exceptions import RedisConfigError

logger = logging.getLogger(__name__)

#: "未指定"哨兵——与显式 None（禁用超时，阻塞池场景）区分。
_UNSET: Any = object()

#: redis-py 异步客户端类型（single/sentinel 为 Redis，cluster 为 RedisCluster）。
NativeConnection = Union[Redis, RedisCluster]


class _NonTransactionRedis(Redis):
    """异步单机/哨兵模式包装类：pipeline() 默认 transaction=False。

    与 common_utils.redis_manager._NonTransactionRedis 保持一致（迁入副本）；
    仅影响裸 ``.pipeline()`` 的默认值——SPI 路径恒显式传 transaction。
    """

    def pipeline(self, transaction: bool = False, shard_hint: Optional[str] = None):
        return super().pipeline(transaction=transaction, shard_hint=shard_hint)


def build_async_client(
    settings: RedisProviderSettings,
    *,
    max_connections: Optional[int] = None,
    socket_timeout: Any = _UNSET,
) -> NativeConnection:
    """按配置构建 redis-py 异步客户端（惰性建连，实际连接发生在首命令）。

    Args:
        settings: SPI 配置（text_mode → decode_responses）。
        max_connections: 覆盖连接池上限（独立订阅/阻塞池用）；缺省取配置值。
        socket_timeout: 覆盖 socket 读超时；显式传 ``None`` = 不设超时
            （阻塞池——socket_timeout 不得先于 BLPOP 自身超时截断阻塞读），
            缺省取配置值。
    """
    mode = settings.mode
    if mode == RedisMode.CLUSTER:
        return _build_cluster(settings, max_connections, socket_timeout)
    if mode == RedisMode.SENTINEL:
        return _build_sentinel(settings, max_connections, socket_timeout)
    return _build_single(settings, max_connections, socket_timeout)


def should_use_independent_pool(settings: RedisProviderSettings) -> bool:
    """当前配置是否为订阅/阻塞命令拆独立客户端（single/sentinel）。

    集群模式共享主池（见模块 docstring）。
    """
    return settings.mode is not RedisMode.CLUSTER


def _build_single(
    settings: RedisProviderSettings,
    max_connections: Optional[int],
    socket_timeout: Any,
) -> Redis:
    """单机模式（参数与 RedisClientManager._create_single_client 对齐）。"""
    connection_kwargs: dict = {
        "host": settings.host,
        "port": settings.port,
        "db": settings.db,
        "max_connections": max_connections or settings.max_connections,
        "socket_timeout": (
            settings.socket_timeout if socket_timeout is _UNSET else socket_timeout
        ),
        "socket_connect_timeout": settings.socket_connect_timeout,
        "decode_responses": settings.text_mode,
    }
    if settings.password:
        connection_kwargs["password"] = settings.password
    if settings.ssl_enabled:
        connection_kwargs.update(_ssl_params(settings))

    redis_cls = Redis if settings.redis_transaction_enabled else _NonTransactionRedis
    return redis_cls(**connection_kwargs)


def _build_cluster(
    settings: RedisProviderSettings,
    max_connections: Optional[int],
    socket_timeout: Any,
) -> RedisCluster:
    """集群模式（参数与 RedisClientManager._create_cluster_client 对齐）。"""
    nodes = _parse_cluster_nodes(settings.cluster_nodes)
    return RedisCluster(
        startup_nodes=nodes,
        max_connections=max_connections or settings.max_connections,
        password=settings.password,
        decode_responses=settings.text_mode,
        socket_timeout=(
            settings.socket_timeout if socket_timeout is _UNSET else socket_timeout
        ),
        socket_connect_timeout=settings.socket_connect_timeout,
    )


def _build_sentinel(
    settings: RedisProviderSettings,
    max_connections: Optional[int],
    socket_timeout: Any,
) -> Redis:
    """哨兵模式（参数与 RedisClientManager._create_sentinel_client 对齐）。

    master_for 不传 socket_timeout（与旧实现一致）；显式覆盖（阻塞池传
    None）时才注入——保证缺省路径产物与旧客户端参数级相同。
    """
    sentinel_nodes = _parse_sentinel_nodes(settings.sentinel_nodes)
    sentinel_kwargs: dict = {
        "socket_timeout": settings.socket_timeout,
        "socket_connect_timeout": settings.socket_connect_timeout,
    }
    # 哨兵节点自身认证（与数据节点密码独立；哨兵集群 requirepass 场景）
    if settings.sentinel_password:
        sentinel_kwargs["sentinel_password"] = settings.sentinel_password
    sentinel = Sentinel(sentinel_nodes, **sentinel_kwargs)
    redis_cls = Redis if settings.redis_transaction_enabled else _NonTransactionRedis
    master_kwargs: dict = {
        "password": settings.password,
        "max_connections": max_connections or settings.max_connections,
        "decode_responses": settings.text_mode,
    }
    if socket_timeout is not _UNSET:
        master_kwargs["socket_timeout"] = socket_timeout
    if settings.ssl_enabled:
        master_kwargs.update(_ssl_params(settings))
    return sentinel.master_for(
        settings.sentinel_master,
        redis_cls,
        **master_kwargs,
    )


def _parse_cluster_nodes(cluster_nodes: str) -> list[ClusterNode]:
    """解析 "host:port,host:port" 形态的集群节点列表（非法形态归入配置错误族）。"""
    nodes: list[ClusterNode] = []
    try:
        for node_str in cluster_nodes.split(","):
            node_str = node_str.strip()
            if not node_str:
                continue
            if ":" in node_str:
                host, port = node_str.split(":", 1)
                node = ClusterNode(host=host, port=int(port))
            else:
                node = ClusterNode(host=node_str, port=6379)
            nodes.append(node)
    except ValueError as exc:
        raise RedisConfigError(f"REDIS_CLUSTER_NODES 非法（需 host:port 列表）: {exc}") from exc
    if not nodes:
        raise RedisConfigError("REDIS_CLUSTER_NODES not configured")
    return nodes


def _parse_sentinel_nodes(sentinel_nodes: str) -> list[tuple[str, int]]:
    """解析 "host:port,host:port" 形态的哨兵节点列表（缺省端口 26379）。"""
    parsed: list[tuple[str, int]] = []
    try:
        for node_str in sentinel_nodes.split(","):
            node_str = node_str.strip()
            if not node_str:
                continue
            if ":" in node_str:
                host, port = node_str.split(":", 1)
                parsed.append((host, int(port)))
            else:
                parsed.append((node_str, 26379))
    except ValueError as exc:
        raise RedisConfigError(f"REDIS_SENTINEL_NODES 非法（需 host:port 列表）: {exc}") from exc
    if not parsed:
        raise RedisConfigError("REDIS_SENTINEL_NODES not configured")
    return parsed


def _ssl_params(settings: RedisProviderSettings) -> dict:
    """SSL 参数组：redis-py 的 ssl 形参仅是开关（SSLContext 传入会被真值
    化丢弃，证书不生效）——私有 CA / mTLS 必须经专用形参传递。"""
    params: dict = {"ssl": True}
    if settings.ssl_ca_cert:
        params["ssl_ca_certs"] = settings.ssl_ca_cert
    if settings.ssl_cert_file:
        params["ssl_certfile"] = settings.ssl_cert_file
    if settings.ssl_key_file:
        params["ssl_keyfile"] = settings.ssl_key_file
    return params
