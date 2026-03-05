from redis.asyncio import Redis as AsyncRedis
from redis import Redis as SyncRedis
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils


class RedisManager:
    """通用 Redis 管理器"""
    def __init__(self, decode_responses: bool = False, sync_client: bool = False):
        rds_password = SecurityUtils.get_decrypted_secret("REDIS_PASSWORD", settings.redis_password)
        if sync_client:
            self.client = SyncRedis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=rds_password,
                decode_responses=decode_responses
            )
        else:
            self.client = AsyncRedis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=rds_password,
                decode_responses=decode_responses
            )

    def set_ex(self, key: str, value: str, seconds: int):
        """设置带过期时间的缓存"""
        self.client.setex(key, seconds, value)

    def get(self, key: str):
        """获取缓存"""
        return self.client.get(key)

    def delete(self, key: str):
        """删除缓存"""
        self.client.delete(key)

    def exists(self, key: str) -> bool:
        """检查 Key 是否存在"""
        return self.client.exists(key)

    def incr(self, key: str, expire: int = None):
        """原子自增，可选设置过期时间"""
        count = self.client.incr(key)
        if count == 1 and expire:
            self.client.expire(key, expire)
        return count

redis_manager_bytes = RedisManager(decode_responses=False, sync_client=False)  # 异步客户端，返回 bytes
redis_manager_str = RedisManager(decode_responses=True, sync_client=True)      # 同步客户端，返回 str
