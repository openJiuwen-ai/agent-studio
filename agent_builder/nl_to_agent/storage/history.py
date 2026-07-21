# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
# N2L临时九问补丁，若jiuwen已更新该代码，则删除
import json
import ssl
from typing import List, Union

import redis
from redis.cluster import RedisCluster, ClusterNode

from agent_builder.adapter.config_bridge import RedisMode, settings as global_settings
from agent_builder.adapter.logger_rt_bridge import logger as rt_logger
from agent_builder.adapter.singleton import Singleton

from .base import BaseConversationMemory


def _create_ssl_context(redis_settings) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if redis_settings.ssl_ca_cert:
        ctx.load_verify_locations(redis_settings.ssl_ca_cert)
    if redis_settings.ssl_cert_file and redis_settings.ssl_key_file:
        ctx.load_cert_chain(
            redis_settings.ssl_cert_file,
            redis_settings.ssl_key_file,
        )
    return ctx


def _create_sync_single_client(redis_settings) -> redis.Redis:
    connection_kwargs = {
        "host": redis_settings.host,
        "port": redis_settings.port,
        "db": redis_settings.db,
        "decode_responses": False,
    }
    if redis_settings.password:
        connection_kwargs["password"] = redis_settings.password
    if redis_settings.ssl_enabled:
        connection_kwargs["ssl"] = _create_ssl_context(redis_settings)
    return redis.Redis(**connection_kwargs)


def _create_sync_cluster_client(redis_settings) -> RedisCluster:
    nodes = []
    for node_str in redis_settings.cluster_nodes.split(","):
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
        password=redis_settings.password,
        decode_responses=False,
    )


def _create_sync_sentinel_client(redis_settings) -> redis.Redis:
    from redis.sentinel import Sentinel

    sentinel_nodes = []
    for node_str in redis_settings.sentinel_nodes.split(","):
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
    sentinel = Sentinel(sentinel_nodes)
    return sentinel.master_for(
        redis_settings.sentinel_master,
        redis.Redis,
        password=redis_settings.password,
        decode_responses=False,
    )


def _create_sync_redis_client() -> Union[redis.Redis, RedisCluster]:
    """使用 agent_runtime 的 Redis 配置创建同步 Redis 客户端"""
    redis_settings = global_settings.redis
    if not redis_settings.host and not redis_settings.cluster_nodes:
        raise RuntimeError(
            "Redis not configured in agent_runtime settings, "
            "please check REDIS_HOST / REDIS_CLUSTER_NODES"
        )
    mode = redis_settings.mode
    if mode == RedisMode.CLUSTER:
        client = _create_sync_cluster_client(redis_settings)
        rt_logger.info(
            "creating sync Redis cluster client: nodes=%s",
            redis_settings.cluster_nodes,
        )
    elif mode == RedisMode.SENTINEL:
        client = _create_sync_sentinel_client(redis_settings)
        rt_logger.info(
            "creating sync Redis sentinel client: master=%s, nodes=%s",
            redis_settings.sentinel_master,
            redis_settings.sentinel_nodes,
        )
    else:
        client = _create_sync_single_client(redis_settings)
        rt_logger.info(
            "creating sync Redis client: host=%s:%s, db=%s",
            redis_settings.host,
            redis_settings.port,
            redis_settings.db,
        )
    return client


class HistoryStorage(metaclass=Singleton):
    """对话历史存储"""

    _initialized = False
    _storage_medium = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_storage()
            cls._initialized = True
        return instance

    def add(self, key: object, value: object) -> bool:
        """新增对话历史记录"""
        return self._storage_medium.add(key, value)

    def get_all(self, key: object) -> List[object]:
        """获取对话历史记录列表"""
        return self._storage_medium.get_all(key)

    def get_nearest_k(self, key: object, k: int) -> List[object]:
        """获取最近的k条对话历史记录"""
        return self._storage_medium.get_nearest_k(key, k)

    def delete(self, key: object) -> bool:
        """删除对话历史记录"""
        return self._storage_medium.delete(key)

    def _init_storage(self):
        """初始化存储中间件"""
        self._storage_medium = ImRedisConversation()


class AsyncHistoryStorage(metaclass=Singleton):
    """异步对话历史存储"""

    _initialized = False
    _async_redis_client = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            instance._init_async_storage()
            cls._initialized = True
        return instance

    async def _get_async_redis_client(self):
        if AsyncHistoryStorage._async_redis_client is None:
            from agent_builder.adapter.redis_bridge import get_redis_client
            AsyncHistoryStorage._async_redis_client = get_redis_client()
        return AsyncHistoryStorage._async_redis_client

    async def add(self, key: str, value: dict) -> bool:
        redis_client = await self._get_async_redis_client()
        ttl = global_settings.redis.datasource_ttl_seconds
        await redis_client.rpush(key, json.dumps(value, ensure_ascii=False))
        await redis_client.expire(key, ttl)
        return True

    async def get_all(self, key: str) -> List[str]:
        redis_client = await self._get_async_redis_client()
        result = await redis_client.lrange(key, 0, -1)
        return [
            item.decode("utf-8") if isinstance(item, bytes) else item
            for item in result
        ]

    async def delete(self, key: str) -> bool:
        redis_client = await self._get_async_redis_client()
        return await redis_client.delete(key) > 0

    def _init_async_storage(self):
        pass


class SessionStorage(metaclass=Singleton):
    """同步会话状态存储：封装 agent/resource/plugin_dict/workflow_dict 4 个键的 get/set/delete。

    使用 agent_runtime 的 Redis 配置，支持单机/集群/哨兵三种模式。
    """

    _initialized = False
    _sync_redis_client = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            cls._init_sync_session_storage()
            cls._initialized = True
        return instance

    @staticmethod
    def _init_sync_session_storage():
        pass

    @staticmethod
    def _get_sync_redis_client():
        if SessionStorage._sync_redis_client is None:
            SessionStorage._sync_redis_client = _create_sync_redis_client()
        return SessionStorage._sync_redis_client

    @staticmethod
    def _decode(value):
        if value is not None and isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    @staticmethod
    def load(task_id: str) -> dict:
        """加载会话状态。返回 dict 中各字段可能为 None。"""
        redis_client = SessionStorage._get_sync_redis_client()
        return {
            "state": SessionStorage._decode(
                redis_client.get(f"agent:{task_id}")
            ),
            "resource_config": SessionStorage._decode(
                redis_client.get(f"resource:{task_id}")
            ),
            "plugin_dict": SessionStorage._decode(
                redis_client.get(f"plugin_dict:{task_id}")
            ),
            "workflow_dict": SessionStorage._decode(
                redis_client.get(f"workflow_dict:{task_id}")
            ),
        }

    @staticmethod
    def save(
        task_id: str,
        state,
        resource_config,
        plugin_dict,
        workflow_dict,
    ) -> bool:
        """保存会话状态。"""
        redis_client = SessionStorage._get_sync_redis_client()
        ttl = global_settings.redis.datasource_ttl_seconds
        redis_client.set(f"agent:{task_id}", state, ex=ttl)
        redis_client.set(
            f"resource:{task_id}", json.dumps(resource_config), ex=ttl
        )
        redis_client.set(
            f"plugin_dict:{task_id}", json.dumps(plugin_dict), ex=ttl
        )
        redis_client.set(
            f"workflow_dict:{task_id}", json.dumps(workflow_dict), ex=ttl
        )
        return True

    @staticmethod
    def delete(task_id: str) -> bool:
        """删除会话状态。"""
        redis_client = SessionStorage._get_sync_redis_client()
        redis_client.delete(f"agent:{task_id}")
        redis_client.delete(f"resource:{task_id}")
        redis_client.delete(f"plugin_dict:{task_id}")
        redis_client.delete(f"workflow_dict:{task_id}")
        return True


class AsyncSessionStorage(metaclass=Singleton):
    """异步会话状态存储：封装 agent/resource/plugin_dict/workflow_dict 4 个键的 get/set/delete。

    使用 get_redis_client() 获取异步 Redis 客户端，支持单机/集群/哨兵三种模式，
    与 AsyncHistoryStorage 共用同一 Redis 连接（由 RedisClientManager 单例管理）。
    """

    _initialized = False
    _async_redis_client = None

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        if not cls._initialized:
            cls._init_async_session_storage()
            cls._initialized = True
        return instance

    @staticmethod
    def _init_async_session_storage():
        pass

    @staticmethod
    async def _get_async_redis_client():
        if AsyncSessionStorage._async_redis_client is None:
            from agent_builder.adapter.redis_bridge import get_redis_client
            AsyncSessionStorage._async_redis_client = get_redis_client()
        return AsyncSessionStorage._async_redis_client

    @staticmethod
    def _decode(value):
        if value is not None and isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    @staticmethod
    async def load(task_id: str) -> dict:
        """加载会话状态。返回 dict 中各字段可能为 None。"""
        redis_client = await AsyncSessionStorage._get_async_redis_client()
        return {
            "state": AsyncSessionStorage._decode(
                await redis_client.get(f"agent:{task_id}")
            ),
            "resource_config": AsyncSessionStorage._decode(
                await redis_client.get(f"resource:{task_id}")
            ),
            "plugin_dict": AsyncSessionStorage._decode(
                await redis_client.get(f"plugin_dict:{task_id}")
            ),
            "workflow_dict": AsyncSessionStorage._decode(
                await redis_client.get(f"workflow_dict:{task_id}")
            ),
        }

    @staticmethod
    async def save(
        task_id: str,
        state,
        resource_config,
        plugin_dict,
        workflow_dict,
    ) -> bool:
        """保存会话状态。"""
        redis_client = await AsyncSessionStorage._get_async_redis_client()
        ttl = global_settings.redis.datasource_ttl_seconds
        await redis_client.set(f"agent:{task_id}", state, ex=ttl)
        await redis_client.set(
            f"resource:{task_id}", json.dumps(resource_config), ex=ttl
        )
        await redis_client.set(
            f"plugin_dict:{task_id}", json.dumps(plugin_dict), ex=ttl
        )
        await redis_client.set(
            f"workflow_dict:{task_id}", json.dumps(workflow_dict), ex=ttl
        )
        return True

    @staticmethod
    async def delete(task_id: str) -> bool:
        """删除会话状态。"""
        redis_client = await AsyncSessionStorage._get_async_redis_client()
        await redis_client.delete(f"agent:{task_id}")
        await redis_client.delete(f"resource:{task_id}")
        await redis_client.delete(f"plugin_dict:{task_id}")
        await redis_client.delete(f"workflow_dict:{task_id}")
        return True


class ImRedisConversation(BaseConversationMemory):
    """
    history conversation memory in redis
    使用 agent_runtime 的 Redis 配置，与 agent_runtime 其他接口保持一致
    """

    def __init__(self):
        self.redis_db = _create_sync_redis_client()

    def add(self, key: object, value: object) -> bool:
        ttl = global_settings.redis.datasource_ttl_seconds
        self.redis_db.rpush(key, json.dumps(value, ensure_ascii=False))
        self.redis_db.expire(key, ttl)
        return True

    def get_nearest_k(self, key: object, k: int) -> List[object]:
        if k <= 0:
            return []
        length = self.redis_db.llen(key)
        if k > length:
            k = length
        start = length - k
        return self.redis_db.lrange(key, start, -1)

    def get_all(self, key: object) -> List[object]:
        return self.redis_db.lrange(key, 0, -1)

    def get(self, key: object) -> object:
        return self.redis_db.get(key)

    def contains(self, key: object) -> bool:
        return self.redis_db.exists(key) > 0

    def delete(self, key: object) -> bool:
        return self.redis_db.delete(key) > 0
