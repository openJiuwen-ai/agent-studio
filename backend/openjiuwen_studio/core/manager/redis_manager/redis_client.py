import redis
from openjiuwen_studio.core.config import settings


class RedisManager:
    """通用 Redis 管理器"""
    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
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

redis_manager = RedisManager()
