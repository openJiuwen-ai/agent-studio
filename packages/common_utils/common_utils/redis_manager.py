# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""异步 / 同步 Redis 客户端统一管理器，支持单机、集群、哨兵三种模式。

agent-runtime / agent-builder 共享：
  - RedisClientManager（单例，同时管理异步与同步客户端）
  - get_redis_client() / get_sync_redis_client()
"""

from __future__ import annotations

import logging
import ssl
from typing import Optional, Union

from redis import Redis as SyncRedis
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster, ClusterNode
from redis.cluster import RedisCluster as SyncRedisCluster
from redis.cluster import ClusterNode as SyncClusterNode
from redis.asyncio.sentinel import Sentinel
from redis.sentinel import Sentinel as SyncSentinel

from common_utils.common_config import RedisMode, RedisSettings

logger = logging.getLogger(__name__)


class _NonTransactionRedis(Redis):
    """异步单机/哨兵模式 Redis 包装类：pipeline() 默认 transaction=False。"""

    def pipeline(self, transaction: bool = False, shard_hint: Optional[str] = None):
        return super().pipeline(transaction=transaction, shard_hint=shard_hint)


class _NonTransactionSyncRedis(SyncRedis):
    """同步单机/哨兵模式 Redis 包装类：pipeline() 默认 transaction=False。"""

    def pipeline(self, transaction: bool = False, shard_hint: Optional[str] = None):
        return super().pipeline(transaction=transaction, shard_hint=shard_hint)


class RedisClientManager:
    """Redis 客户端管理器（进程单例）。

    同时管理异步客户端（_client）与同步客户端（_sync_client），
    两者共享同一份 RedisSettings 配置，按需惰性创建。
    """

    _instance: Optional["RedisClientManager"] = None
    _client: Optional[Union[Redis, RedisCluster]] = None
    _sync_client: Optional[Union[SyncRedis, SyncRedisCluster]] = None
    _settings: Optional[RedisSettings] = None

    def __init__(self) -> None:
        raise RuntimeError("Use get_instance() to get the singleton.")

    @classmethod
    def get_instance(cls) -> "RedisClientManager":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def init(self, settings: Optional[RedisSettings] = None) -> None:
        """初始化 Redis 客户端（同步调用，实际创建在异步上下文中完成）。

        Args:
            settings: Redis 配置。如为 None，直接实例化 RedisSettings() 读取环境变量。
        """
        if self._client is not None:
            logger.warning("Redis client already initialized, skipping.")
            return

        self._settings = settings if settings is not None else RedisSettings()

        if not self._settings.host and not self._settings.cluster_nodes:
            logger.warning("Redis not configured, client not initialized.")
            return

        try:
            self._client = self._create_client()
            logger.info(
                "Redis client initialized: mode=%s, host=%s:%s",
                self._settings.mode.value,
                self._settings.host,
                self._settings.port,
            )
        except Exception as e:
            logger.error("Failed to initialize Redis client: %s", e)
            raise

    def _create_client(self) -> Union[Redis, RedisCluster]:
        """根据配置创建异步 Redis 客户端。"""
        mode = self._settings.mode
        if mode == RedisMode.CLUSTER:
            return self._create_cluster_client()
        elif mode == RedisMode.SENTINEL:
            return self._create_sentinel_client()
        else:
            return self._create_single_client()

    def _create_single_client(self) -> Redis:
        """创建单机模式的异步 Redis 客户端。"""
        connection_kwargs: dict = {
            "host": self._settings.host,
            "port": self._settings.port,
            "db": self._settings.db,
            "max_connections": self._settings.max_connections,
            "socket_timeout": self._settings.socket_timeout,
            "socket_connect_timeout": self._settings.socket_connect_timeout,
            "decode_responses": False,
        }
        if self._settings.password:
            connection_kwargs["password"] = self._settings.password

        if self._settings.ssl_enabled:
            connection_kwargs["ssl"] = self._create_ssl_context()

        redis_cls = Redis if self._settings.redis_transaction_enabled else _NonTransactionRedis
        return redis_cls(**connection_kwargs)

    def _create_cluster_client(self) -> RedisCluster:
        """创建集群模式的异步 Redis 客户端。"""
        nodes = []
        for node_str in self._settings.cluster_nodes.split(","):
            node_str = node_str.strip()
            if not node_str:
                continue
            if ":" in node_str:
                host, port = node_str.split(":", 1)
                node = ClusterNode(host=host, port=int(port))
            else:
                node = ClusterNode(host=node_str, port=6379)
            nodes.append(node)

        if not nodes:
            raise ValueError("REDIS_CLUSTER_NODES not configured")

        return RedisCluster(
            startup_nodes=nodes,
            max_connections=self._settings.max_connections,
            password=self._settings.password,
            decode_responses=False,
            socket_timeout=self._settings.socket_timeout,
            socket_connect_timeout=self._settings.socket_connect_timeout,
        )

    def _create_sentinel_client(self) -> Redis:
        """创建哨兵模式的异步 Redis 客户端。"""
        sentinel_nodes = []
        for node_str in self._settings.sentinel_nodes.split(","):
            node_str = node_str.strip()
            if not node_str:
                continue
            if ":" in node_str:
                host, port = node_str.split(":", 1)
                sentinel_nodes.append((host, int(port)))
            else:
                sentinel_nodes.append((node_str, 26379))

        if not sentinel_nodes:
            raise ValueError("REDIS_SENTINEL_NODES not configured")

        sentinel = Sentinel(
            sentinel_nodes,
            socket_timeout=self._settings.socket_timeout,
            socket_connect_timeout=self._settings.socket_connect_timeout,
        )
        redis_cls = Redis if self._settings.redis_transaction_enabled else _NonTransactionRedis
        return sentinel.master_for(
            self._settings.sentinel_master,
            redis_cls,
            password=self._settings.password,
            max_connections=self._settings.max_connections,
            ssl=self._create_ssl_context() if self._settings.ssl_enabled else None,
            decode_responses=False,
        )

    # ------------------------------------------------------------------ #
    # 同步客户端
    # ------------------------------------------------------------------ #
    def get_sync_client(self) -> Union[SyncRedis, SyncRedisCluster]:
        """获取同步 Redis 客户端（惰性创建）。

        与异步客户端共用同一份 RedisSettings；若异步客户端尚未 init()，
        本方法会先尝试 init()（同样惰性读取环境变量）。
        """
        if self._sync_client is not None:
            return self._sync_client

        if self._settings is None:
            self.init()

        if self._settings is None or (
            not self._settings.host and not self._settings.cluster_nodes
        ):
            raise RuntimeError(
                "Redis not configured, please check REDIS_HOST / REDIS_CLUSTER_NODES"
            )

        self._sync_client = self._create_sync_client()
        logger.info(
            "Sync Redis client initialized: mode=%s, host=%s:%s",
            self._settings.mode.value,
            self._settings.host,
            self._settings.port,
        )
        return self._sync_client

    def _create_sync_client(self) -> Union[SyncRedis, SyncRedisCluster]:
        """根据配置创建同步 Redis 客户端。"""
        mode = self._settings.mode
        if mode == RedisMode.CLUSTER:
            return self._create_sync_cluster_client()
        elif mode == RedisMode.SENTINEL:
            return self._create_sync_sentinel_client()
        else:
            return self._create_sync_single_client()

    def _create_sync_single_client(self) -> SyncRedis:
        """创建单机模式的同步 Redis 客户端。"""
        connection_kwargs: dict = {
            "host": self._settings.host,
            "port": self._settings.port,
            "db": self._settings.db,
            "decode_responses": False,
        }
        if self._settings.password:
            connection_kwargs["password"] = self._settings.password

        if self._settings.ssl_enabled:
            connection_kwargs["ssl"] = self._create_ssl_context()

        redis_cls = (
            SyncRedis
            if self._settings.redis_transaction_enabled
            else _NonTransactionSyncRedis
        )
        return redis_cls(**connection_kwargs)

    def _create_sync_cluster_client(self) -> SyncRedisCluster:
        """创建集群模式的同步 Redis 客户端。"""
        nodes = []
        for node_str in self._settings.cluster_nodes.split(","):
            node_str = node_str.strip()
            if not node_str:
                continue
            if ":" in node_str:
                host, port = node_str.split(":", 1)
                node = SyncClusterNode(host=host, port=int(port))
            else:
                node = SyncClusterNode(host=node_str, port=6379)
            nodes.append(node)

        if not nodes:
            raise ValueError("REDIS_CLUSTER_NODES not configured")

        return SyncRedisCluster(
            startup_nodes=nodes,
            password=self._settings.password,
            decode_responses=False,
        )

    def _create_sync_sentinel_client(self) -> SyncRedis:
        """创建哨兵模式的同步 Redis 客户端。"""
        sentinel_nodes = []
        for node_str in self._settings.sentinel_nodes.split(","):
            node_str = node_str.strip()
            if not node_str:
                continue
            if ":" in node_str:
                host, port = node_str.split(":", 1)
                sentinel_nodes.append((host, int(port)))
            else:
                sentinel_nodes.append((node_str, 26379))

        if not sentinel_nodes:
            raise ValueError("REDIS_SENTINEL_NODES not configured")

        sentinel = SyncSentinel(sentinel_nodes)
        redis_cls = (
            SyncRedis
            if self._settings.redis_transaction_enabled
            else _NonTransactionSyncRedis
        )
        return sentinel.master_for(
            self._settings.sentinel_master,
            redis_cls,
            password=self._settings.password,
            decode_responses=False,
        )

    # ------------------------------------------------------------------ #
    # 通用
    # ------------------------------------------------------------------ #
    def _create_ssl_context(self) -> ssl.SSLContext:
        """创建 SSL 上下文。"""
        ctx = ssl.create_default_context()
        if self._settings.ssl_ca_cert:
            ctx.load_verify_locations(self._settings.ssl_ca_cert)
        if self._settings.ssl_cert_file and self._settings.ssl_key_file:
            ctx.load_cert_chain(
                self._settings.ssl_cert_file,
                self._settings.ssl_key_file,
            )
        return ctx

    def get_client(self) -> Union[Redis, RedisCluster]:
        """获取异步 Redis 客户端。"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call init() first.")
        return self._client

    @property
    def is_initialized(self) -> bool:
        return self._client is not None

    async def close(self) -> None:
        """关闭 Redis 客户端（异步 + 同步）。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis async client closed.")
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None
            logger.info("Redis sync client closed.")

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）。"""
        cls._instance = None
        cls._client = None
        cls._sync_client = None
        cls._settings = None


def get_redis_client() -> Union[Redis, RedisCluster]:
    """获取异步 Redis 客户端的便捷函数。"""
    return RedisClientManager.get_instance().get_client()


def get_sync_redis_client() -> Union[SyncRedis, SyncRedisCluster]:
    """获取同步 Redis 客户端的便捷函数。"""
    return RedisClientManager.get_instance().get_sync_client()
