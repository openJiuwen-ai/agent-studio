import logging
import os

from redis_spi import accessor
from redis_spi.types import Duration

from jiuwen.context.memory_engine.store.base_kv_store import BaseKVStore


class KVStoreRedisImpl(BaseKVStore):
    """记忆引擎 KV 存储的 Redis 实现（redis_spi accessor 装配）。

    迁移自 jiuwen 老 store（Phase 4 第五批）：连接由 runtime lifespan 装配的
    Provider 单例提供，消除 DATASOURCE_REDIS_* 独立配置面。
    """

    def __init__(self):
        self.client = accessor.get_redis()
        expired_days = int(os.getenv("MEMORY_REDIS_TTL", 180))
        self.default_ttl = expired_days * 24 * 60 * 60

    async def set(self, key: str, value: str):
        # 当前kv_store的redis实现是用来做记忆存储的，需要有个默认的数据过期时间，避免数据一直存在
        await self.client.set(key, value, duration=Duration.seconds(self.default_ttl))

    async def exclusive_set(
        self, key: str, value: str, expiry: int | None = None
    ) -> bool:
        # 行为对齐旧实现（老 store 的 set 非 NX 语义，方法名与行为的历史差异原样保留）
        result = await self.client.set(
            key, value, duration=Duration.seconds(expiry) if expiry else None
        )
        return result is not None

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def delete(self, key: str):
        await self.client.delete(key)

    async def get_by_prefix(self, prefix: str) -> dict[str, str]:
        result: dict[str, str] = {}
        pattern = f"{prefix}*"
        async for key in self.client.scan_iter(match=pattern):
            value = await self.client.get(key)
            if value is not None:
                key_str = key.decode() if isinstance(key, bytes) else key
                value_str = value.decode() if isinstance(value, bytes) else value
                result[key_str] = value_str
        return result

    async def delete_by_prefix(self, prefix: str):
        # 旧实现对老 wrapper 的 delete_by_prefix 调用并不存在（一调即
        # AttributeError）；此处按 get_by_prefix 同款 SCAN 语义补齐实现
        pattern = f"{prefix}*"
        keys = [key async for key in self.client.scan_iter(match=pattern)]
        if keys:
            await self.client.delete(*keys)
        logging.info(f"delete keys of prefix '{prefix}', delete {len(keys)} keys")

    async def delete_by_pattern(self, pattern: str):
        """
        Remove all key-value pairs whose keys contain pattern string.

        Args:
            pattern (str): The pattern str to match against existing key.
        """
        logging.warning("Redis does not support deleting keys by pattern directly.")
        pass

    async def mget(self, keys: list[str], default: any = None) -> list[str]:
        return await self.client.mget(keys)
