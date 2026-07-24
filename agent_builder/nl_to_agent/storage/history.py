# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
# N2L临时九问补丁，若jiuwen已更新该代码，则删除
import json
from typing import List

from common_utils.common_config import RedisSettings
from common_utils.redis_manager import RedisClientManager, get_redis_client
from agent_builder.adapter.logger_rt_bridge import logger as rt_logger
from agent_builder.adapter.singleton import Singleton

from .base import BaseConversationMemory


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
            AsyncHistoryStorage._async_redis_client = get_redis_client()
        return AsyncHistoryStorage._async_redis_client

    async def add(self, key: str, value: dict) -> bool:
        redis_client = await self._get_async_redis_client()
        ttl = RedisSettings().datasource_ttl_seconds
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

    使用 RedisClientManager 管理的同步 Redis 客户端，支持单机/集群/哨兵三种模式。
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
            SessionStorage._sync_redis_client = (
                RedisClientManager.get_instance().get_sync_client()
            )
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
        ttl = RedisSettings().datasource_ttl_seconds
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
        ttl = RedisSettings().datasource_ttl_seconds
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
    使用 RedisClientManager 管理的同步 Redis 客户端，与 agent_runtime 其他接口保持一致
    """

    def __init__(self):
        self.redis_db = RedisClientManager.get_instance().get_sync_client()

    def add(self, key: object, value: object) -> bool:
        ttl = RedisSettings().datasource_ttl_seconds
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
