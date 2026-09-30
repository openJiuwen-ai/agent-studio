# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""演示用企业自研 Redis Provider（模拟通过插件文件接入，不修改框架源码）。

通过 REDIS_PROVIDER_MODULE 指向本文件 + REDIS_PROVIDER_CLASS=DemoCustomRedisProvider 启用，
验证适配层的可替换性（与 Java 侧 demo RedisClientProvider 对应）。
"""

from typing import Optional

from common_utils.common_config import RedisSettings
from common_utils.redis_provider import (
    BaseAsyncRedisClient,
    BaseSyncRedisClient,
    InMemoryAsyncRedisClient,
    InMemoryRedisProvider,
    RedisProvider,
)


class DemoCustomSyncRedisClient(BaseSyncRedisClient):
    """自研客户端：在内存实现之上叠加读写操作统计（模拟自研代理的审计/计量能力）。"""

    def __init__(self, delegate: InMemoryAsyncRedisClient):
        self._delegate = delegate
        self.read_ops = 0
        self.write_ops = 0

    def get(self, key):
        self.read_ops += 1
        return self._delegate.get(key)

    def set(self, key, value, ex=None):
        self.write_ops += 1
        return self._delegate.set(key, value, ex)

    def delete(self, *keys):
        self.write_ops += 1
        return self._delegate.delete(*keys)

    def exists(self, *keys):
        self.read_ops += 1
        return self._delegate.exists(*keys)

    def expire(self, key, seconds):
        self.write_ops += 1
        return self._delegate.expire(key, seconds)

    def ttl(self, key):
        self.read_ops += 1
        return self._delegate.ttl(key)

    def mget(self, keys):
        self.read_ops += 1
        return self._delegate.mget(keys)

    def mset(self, mapping):
        self.write_ops += 1
        return self._delegate.mset(mapping)

    def hset(self, name, key=None, value=None, mapping=None, ex=None):
        self.write_ops += 1
        return self._delegate.hset(name, key, value, mapping, ex)

    def hget(self, name, key):
        self.read_ops += 1
        return self._delegate.hget(name, key)

    def hgetall(self, name):
        self.read_ops += 1
        return self._delegate.hgetall(name)

    def sadd(self, name, *members):
        self.write_ops += 1
        return self._delegate.sadd(name, *members)

    def srem(self, name, *members):
        self.write_ops += 1
        return self._delegate.srem(name, *members)

    def smembers(self, name):
        self.read_ops += 1
        return self._delegate.smembers(name)

    def rpush(self, name, *values, ex=None):
        self.write_ops += 1
        return self._delegate.rpush(name, *values, ex=ex)

    def lrange(self, name, start, end):
        self.read_ops += 1
        return self._delegate.lrange(name, start, end)

    def llen(self, name):
        self.read_ops += 1
        return self._delegate.llen(name)

    def scan_iter(self, match):
        return self._delegate.scan_iter(match)

    def get_lock(self, name, timeout=10.0):
        return self._delegate.get_lock(name, timeout)


class DemoCustomRedisProvider(RedisProvider):
    """演示 Provider：name 为 demo-custom，create_* 返回带统计的自研客户端。"""

    NAME = "demo-custom"

    def __init__(self):
        self._memory = InMemoryRedisProvider()

    def name(self) -> str:
        return self.NAME

    def create_sync_client(self, settings: Optional[RedisSettings]) -> BaseSyncRedisClient:
        return DemoCustomSyncRedisClient(self._memory.create_sync_client(settings))

    def create_async_client(self, settings: Optional[RedisSettings]) -> BaseAsyncRedisClient:
        return self._memory.create_async_client(settings)
