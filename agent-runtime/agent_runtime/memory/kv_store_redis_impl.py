import logging
import os

from jiuwen.context.memory_engine.store.base_kv_store import BaseKVStore


class KVStoreRedisImpl(BaseKVStore):
    def __init__(self):
        from jiuwen.common.store.async_redis import get_async_redis_instance

        self.client = get_async_redis_instance()
        expired_days = int(os.getenv("MEMORY_REDIS_TTL", 180))
        self.default_ttl = expired_days * 24 * 60 * 60

    async def set(self, key: str, value: str):
        # 当前kv_store的redis实现是用来做记忆存储的，需要有个默认的数据过期时间，避免数据一直存在
        await self.client.set(key, value, ex=self.default_ttl)

    async def exclusive_set(
        self, key: str, value: str, expiry: int | None = None
    ) -> bool:
        return await self.client.set(key, value, expiry)

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def exists(self, key: str) -> bool:
        return await self.client.list_contain(key)

    async def delete(self, key: str):
        await self.client.delete(key)

    async def get_by_prefix(self, prefix: str) -> dict[str, str]:
        result = await self.client.get_by_prefix(prefix)
        return {k: str(v) if v is not None else None for k, v in result.items()}

    async def delete_by_prefix(self, prefix: str):
        deleted_count = await self.client.delete_by_prefix(prefix)
        logging.info(f"delete keys of prefix '{prefix}', delete {deleted_count} keys")

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
