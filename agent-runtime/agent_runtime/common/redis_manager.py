# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""异步 Redis 客户端统一管理器，支持单机、集群、哨兵三种模式。"""

from __future__ import annotations

import ssl
from typing import Optional, Union

from agent_runtime.common.config import RedisMode, RedisSettings
from agent_runtime.common.logger import logger
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster, ClusterNode
from redis.asyncio.sentinel import Sentinel


class _NonTransactionRedis(Redis):
    """单机/哨兵模式 Redis 包装类：pipeline() 默认 transaction=False。
    """

    def pipeline(self, transaction: bool = False, shard_hint: Optional[str] = None):
        return super().pipeline(transaction=transaction, shard_hint=shard_hint)


class RedisClientManager:
    """异步 Redis 客户端管理器（进程单例）。"""

    _instance: Optional["RedisClientManager"] = None
    _client: Optional[Union[Redis, RedisCluster]] = None
    _settings: Optional[RedisSettings] = None

    def __init__(self) -> None:
        raise RuntimeError("Use get_instance() to get the singleton.")

    @classmethod
    def get_instance(cls) -> "RedisClientManager":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance._client = None
            cls._instance._settings = None
        return cls._instance

    def init(self, settings: Optional[RedisSettings] = None) -> None:
        """初始化 Redis 客户端（同步调用，实际创建在异步上下文中完成）。

        Args:
            settings: Redis 配置。如为 None，从全局 settings 读取。
        """
        if self._client is not None:
            logger.warning("Redis client already initialized, skipping.")
            return

        self._settings = settings
        if settings is None:
            from agent_runtime.common.config import settings as global_settings

            self._settings = global_settings.redis

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
        """根据配置创建 Redis 客户端。"""
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
            socket_connect_timeout=self._settings.socket_connect_timeout
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
        """关闭 Redis 客户端。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis client closed.")

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）。"""
        cls._instance = None
        cls._client = None
        cls._settings = None


def get_redis_client() -> Union[Redis, RedisCluster]:
    """获取异步 Redis 客户端的便捷函数。"""
    return RedisClientManager.get_instance().get_client()


class ExecutionIdStore:
    """execution_id 的 Redis 存储管理，用于工作流中断恢复时保持 execution_id 一致"""

    KEY_PREFIX = "agentBuilder:execution_id"
    DEFAULT_TTL = 86400  # 24小时

    @classmethod
    def _build_key(cls, workflow_id: str, session_id: str) -> str:
        """构建 Redis key: workflow_id + session_id"""
        return f"{cls.KEY_PREFIX}:{workflow_id}:{session_id}"

    @classmethod
    async def save(
        cls, workflow_id: str, session_id: str, exec_id: str, ttl: int = None
    ) -> bool:
        """保存 execution_id 到 Redis

        Args:
            workflow_id: 工作流 ID
            session_id: 会话 ID
            exec_id: execution_id
            ttl: 过期时间（秒），默认 24 小时

        Returns:
            bool: 是否保存成功
        """
        try:
            redis_client = get_redis_client()
            key = cls._build_key(workflow_id, session_id)
            expire = ttl if ttl is not None else cls.DEFAULT_TTL
            await redis_client.set(key, exec_id, ex=expire)
            logger.debug(f"Saved execution_id: key={key}, exec_id={exec_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save execution_id to Redis: {e}")
            return False

    @classmethod
    async def get(cls, workflow_id: str, session_id: str) -> str | None:
        """从 Redis 获取之前保存的 execution_id

        Args:
            workflow_id: 工作流 ID
            session_id: 会话 ID

        Returns:
            str | None: 保存的 execution_id，不存在或失败时返回 None
        """
        try:
            redis_client = get_redis_client()
            key = cls._build_key(workflow_id, session_id)
            result = await redis_client.get(key)
            if result is not None:
                exec_id = (
                    result.decode("utf-8") if isinstance(result, bytes) else str(result)
                )
                logger.debug(f"Retrieved execution_id: key={key}, exec_id={exec_id}")
                return exec_id
            return None
        except Exception as e:
            logger.warning(f"Failed to get execution_id from Redis: {e}")
            return None

    @classmethod
    async def delete(cls, workflow_id: str, session_id: str) -> bool:
        """删除 Redis 中保存的 execution_id

        Args:
            workflow_id: 工作流 ID
            session_id: 会话 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            redis_client = get_redis_client()
            key = cls._build_key(workflow_id, session_id)
            await redis_client.delete(key)
            logger.debug(f"Deleted execution_id: key={key}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete execution_id from Redis: {e}")
            return False


class QuestionerTraceStore:
    """Questioner 节点 trace 数据的 Redis 存储管理，用于工作流中断恢复时保持 on_invoke_data"""

    KEY_PREFIX = "agentBuilder:questioner:trace"
    DEFAULT_TTL = 86400  # 24小时

    @classmethod
    def _build_key(cls, session_id: str, component_id: str) -> str:
        """构建 Redis key: session_id + component_id"""
        return f"{cls.KEY_PREFIX}:{session_id}:{component_id}"

    @classmethod
    async def append(
        cls, session_id: str, component_id: str, trace_data: dict, ttl: int = None
    ) -> bool:
        """追加 trace 数据到 Redis 列表

        Args:
            session_id: 会话 ID
            component_id: 组件 ID
            trace_data: trace 数据字典
            ttl: 过期时间（秒），默认 24 小时

        Returns:
            bool: 是否保存成功
        """
        try:
            import json

            redis_client = get_redis_client()
            key = cls._build_key(session_id, component_id)
            trace_json = json.dumps(trace_data, ensure_ascii=False)
            expire = ttl if ttl is not None else cls.DEFAULT_TTL

            # 使用 RPUSH 追加到列表
            await redis_client.rpush(key, trace_json)
            # 设置过期时间
            await redis_client.expire(key, expire)

            logger.debug(f"Appended trace data: key={key}, data={trace_data}")
            return True
        except Exception as e:
            logger.warning(f"Failed to append trace data to Redis: {e}")
            return False

    @classmethod
    async def get_all(cls, session_id: str, component_id: str) -> list[dict]:
        """获取指定 session 和 component 的所有 trace 数据

        Args:
            session_id: 会话 ID
            component_id: 组件 ID

        Returns:
            list[dict]: trace 数据列表，失败时返回空列表
        """
        try:
            import json

            redis_client = get_redis_client()
            key = cls._build_key(session_id, component_id)
            result = await redis_client.lrange(key, 0, -1)

            trace_list = []
            for item in result:
                if isinstance(item, bytes):
                    item = item.decode("utf-8")
                trace_list.append(json.loads(item))

            logger.debug(f"Retrieved trace data: key={key}, count={len(trace_list)}")
            return trace_list
        except Exception as e:
            logger.warning(f"Failed to get trace data from Redis: {e}")
            return []

    @classmethod
    async def delete(cls, session_id: str, component_id: str) -> bool:
        """删除指定 session 和 component 的所有 trace 数据

        Args:
            session_id: 会话 ID
            component_id: 组件 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            redis_client = get_redis_client()
            key = cls._build_key(session_id, component_id)
            await redis_client.delete(key)
            logger.debug(f"Deleted trace data: key={key}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete trace data from Redis: {e}")
            return False

    @classmethod
    async def recover_to_session(
        cls, session_id: str, component_id: str, session
    ) -> bool:
        """将 Redis 中保存的 trace 数据恢复到 session 的 tracer

        Args:
            session_id: 会话 ID
            component_id: 组件 ID
            session: openjiuwen.core.session.node.Session 实例

        Returns:
            bool: 是否恢复成功
        """
        try:
            trace_list = await cls.get_all(session_id, component_id)
            if not trace_list:
                logger.debug(
                    f"No trace data to recover: session_id={session_id}, component_id={component_id}"
                )
                return True

            # 批量恢复：直接操作 span 的 on_invoke_data，不逐条触发事件
            tracer = session._inner.tracer()
            if tracer is None:
                return True

            from openjiuwen.core.session.tracer.handler import TracerHandlerName

            invoke_id = session._inner.executable_id()
            parent_id = session._inner.parent_id()
            handler_class_name = (
                TracerHandlerName.TRACER_WORKFLOW.value + "." + parent_id
                if parent_id != ""
                else TracerHandlerName.TRACER_WORKFLOW.value
            )
            handler = tracer._handlers.get(handler_class_name)
            if handler is None:
                handler = tracer._handlers.get(TracerHandlerName.TRACER_WORKFLOW.value)

            if handler:
                span = handler._span_manager.get_span(invoke_id)
                if span:
                    if not isinstance(span.on_invoke_data, list):
                        span.on_invoke_data = []
                    # 批量 extend 所有历史数据
                    span.on_invoke_data.extend(trace_list)
                    # 只发送一次事件
                    import asyncio

                    asyncio.create_task(handler._send_data(span))
            return True
        except Exception as e:
            logger.warning(f"Failed to recover trace data to session: {e}")
            return False
