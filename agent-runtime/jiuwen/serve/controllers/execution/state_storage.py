# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

import threading
from abc import ABC, abstractmethod

from common_utils.redis_manager import get_redis_client
from jiuwen.common.store.redis import get_redis_instance


class StateStorage(ABC):
    """Agent状态存储基类"""

    @abstractmethod
    def set_state(self, k, v):
        """设置状态"""
        pass

    @abstractmethod
    def delete_state(self, k):
        """删除状态"""
        pass

    @abstractmethod
    def get_state(self, k):
        """获取状态"""
        pass


class AsyncStateStorage(ABC):
    """Agent状态异步存储基类"""

    @abstractmethod
    async def set_state(self, k, v):
        """设置状态"""
        pass

    @abstractmethod
    async def delete_state(self, k):
        """删除状态"""
        pass

    @abstractmethod
    async def get_state(self, k):
        """获取状态"""
        pass


class MemoryStateStorage(StateStorage):
    """Agent状态内存存储"""

    def __init__(self):
        self._state_dict = {}
        self._lock = threading.Lock()

    def get_state(self, k):
        """从内存中获取状态"""
        with self._lock:
            return self._state_dict.get(k)

    def delete_state(self, k):
        """从内存中删除某个状态"""
        with self._lock:
            if k in self._state_dict:
                del self._state_dict[k]

    def set_state(self, k, v):
        """往内存中设置状态"""
        with self._lock:
            self._state_dict[k] = v


class RedisStateStorage(StateStorage):
    """Agent状态Redis存储"""

    def __init__(self):
        self.redis_client = get_redis_instance()

    def delete_state(self, k):
        """从Redis中删除某个状态"""
        self.redis_client.delete(key=k)

    def get_state(self, k):
        """从Redis中获取状态"""
        return self.redis_client.get(key=k)

    def set_state(self, k, v):
        """往Redis中设置状态"""
        self.redis_client.set(key=k, value=v)


class AsyncMemoryStateStorage(AsyncStateStorage):
    """Agent状态内存存储异步封装"""

    def __init__(self):
        super().__init__()
        self._storage = MemoryStateStorage()

    async def init(self):
        """init"""
        pass

    async def get_state(self, k):
        """从内存中获取状态"""
        return self._storage.get_state(k)

    async def delete_state(self, k):
        """从内存中删除某个状态"""
        return self._storage.delete_state(k)

    async def set_state(self, k, v):
        """往内存中设置状态"""
        return self._storage.set_state(k, v)


class AsyncRedisStateStorage(AsyncStateStorage):
    """Agent状态异步Redis存储"""

    def __init__(self):
        self.redis_client = get_redis_client()

    async def init(self):
        """No-op: get_redis_client() 返回已初始化的 redis.asyncio.Redis 实例，无需再 init"""
        pass

    async def delete_state(self, k):
        """从Redis中删除某个状态"""
        await self.redis_client.delete(k)

    async def get_state(self, k):
        """从Redis中获取状态"""
        return await self.redis_client.get(k)

    async def set_state(self, k, v):
        """往Redis中设置状态"""
        await self.redis_client.set(k, v)
