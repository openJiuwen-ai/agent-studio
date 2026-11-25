# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

import os
import threading
from abc import ABC, abstractmethod

from common_utils.redis_manager import get_redis_client
from jiuwen.common.configs.env_constants import EXECUTION_STATE_TTL_SECONDS_KEY
from jiuwen.common.store.redis import get_redis_instance

# Agent 状态 Redis key 默认过期时间（秒），默认 24h。
# 正常结束会 delete_state 删除；此处 TTL 兜底异常/中断残留的 key，
# 压测等场景可调短（EXECUTION_STATE_TTL_SECONDS）以控制 Redis 内存。
_STATE_TTL_SECONDS = int(os.getenv(EXECUTION_STATE_TTL_SECONDS_KEY, 86400))


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
        self.redis_client.set(key=k, value=v, ex=_STATE_TTL_SECONDS)


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
        await self.redis_client.set(k, v, ex=_STATE_TTL_SECONDS)
