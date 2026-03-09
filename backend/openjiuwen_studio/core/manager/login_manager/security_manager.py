import secrets
import string

from threading import Lock
from openjiuwen_studio.core.manager.redis_manager.redis_client import redis_manager_str as redis_manager
from fastapi import HTTPException
from cachetools import TTLCache


class TTLCacheRateLimiter:
    LOGIN_NAME = "login"
    REGISTER_NAME = "register"
    LOGIN_TIME_RANGE = 60
    REGISTER_TIME_RANGE = 3600
    MAX_SIZE = 10000

    def __init__(self):
        # 创建两个缓存：登录/注册
        self.caches = {
            TTLCacheRateLimiter.LOGIN_NAME:
                TTLCache(maxsize=TTLCacheRateLimiter.MAX_SIZE, ttl=TTLCacheRateLimiter.LOGIN_TIME_RANGE),
            TTLCacheRateLimiter.REGISTER_NAME:
                TTLCache(maxsize=TTLCacheRateLimiter.MAX_SIZE, ttl=TTLCacheRateLimiter.REGISTER_TIME_RANGE)
        }
        self.locks = {name: Lock() for name in self.caches}

    def allow_request(self, cache_name: str, key: str, max_requests: int) -> bool:
        cache = self.caches[cache_name]
        lock = self.locks[cache_name]
        with lock:
            # 获取当前计数，若 key 不存在则默认为0
            current = cache.get(key, 0)
            if current < max_requests:
                cache[key] = current + 1
                return True
            else:
                return False


class SecurityManager:
    """安全管理器：处理验证码、登录失败锁定"""
    _REG_CODE_KEY = "auth:reg:code:{email}"
    _REG_LIMIT_KEY = "auth:reg:limit:{email}"
    _RESET_CODE_KEY = "auth:reset:code:{email}"
    _RESET_LIMIT_KEY = "auth:reset:limit:{email}"
    _FAIL_COUNT_KEY = "auth:fail:count:{email}"
    _VERIFY_ATTEMPT_KEY = "auth:verify:attempt:{email}:{action_type}"
    _LOGIN_RATE_LIMIT_KEY = "rate_limit:login:{client_ip}"
    _REGISTER_RATE_LIMIT_KEY = "rate_limit:register:{client_ip}"
    MAX_VERIFY_ATTEMPTS = 5

    MAX_LOGIN_ATTEMPTS = 5
    LOCK_TIME = 1800  # 30分钟锁定
    CODE_EXPIRE = 600 # 10分钟验证码有效
    LIMIT_EXPIRE = 60 # 60秒发送频率限制
    LIMITER = TTLCacheRateLimiter()

    # 邮箱验证码相关操作
    @classmethod
    def generate_and_save_code(cls, email: str, action_type: str = "reg") -> str:
        """生成验证码并存入 Redis"""
        code = ''.join(secrets.choice(string.digits) for _ in range(6))
        template = cls._REG_CODE_KEY if action_type == "reg" else cls._RESET_CODE_KEY
        limit_template = cls._REG_LIMIT_KEY if action_type == "reg" else cls._RESET_LIMIT_KEY
        # 存储验证码和频率限制
        redis_manager.set_ex(template.format(email=email), code, cls.CODE_EXPIRE)
        redis_manager.set_ex(limit_template.format(email=email), "1", cls.LIMIT_EXPIRE)
        return code

    @classmethod
    def verify_code(cls, email: str, input_code: str, action_type: str = "reg") -> bool:
        """校验验证码，通过后立即销毁"""
        template = cls._REG_CODE_KEY if action_type == "reg" else cls._RESET_CODE_KEY
        attempt_key = cls._VERIFY_ATTEMPT_KEY.format(email=email, action_type=action_type)
        attempt_count = redis_manager.get(attempt_key)
        key = template.format(email=email)
        if attempt_count and int(attempt_count) >= cls.MAX_VERIFY_ATTEMPTS:
            redis_manager.delete(key) # 超过重试上限后销毁验证码
            redis_manager.delete(attempt_key) # 清除重试次数
            return False
        saved_code = redis_manager.get(key)
        
        if saved_code and saved_code == input_code:
            redis_manager.delete(key) # 验证通过立即销毁
            redis_manager.delete(attempt_key) # 清除重试次数
            return True
        # 失败次数累计
        redis_manager.incr(attempt_key, cls.CODE_EXPIRE)
        return False

    @classmethod
    def rate_limit(cls, email: str, action_type: str = "reg") -> bool:
        """检查邮件发送是否处于受限状态（频率过快）"""
        template = cls._REG_LIMIT_KEY if action_type == "reg" else cls._RESET_LIMIT_KEY
        return redis_manager.exists(template.format(email=email))

    # 锁定计数相关逻辑
    @classmethod
    def get_lock_info(cls, email: str) -> dict:
        """获取账号锁定状态信息"""
        count = redis_manager.get(cls._FAIL_COUNT_KEY.format(email=email))
        count = int(count) if count else 0
        return {
            "is_locked": count >= cls.MAX_LOGIN_ATTEMPTS,
            "remaining_attempts": max(0, cls.MAX_LOGIN_ATTEMPTS - count),
            "current_fail_count": count
        }

    @classmethod
    def record_login_failure(cls, email: str):
        """记录登录失败，第一次失败时设置过期时间，后续不重置时间"""
        key = cls._FAIL_COUNT_KEY.format(email=email)
        if not redis_manager.exists(key):
            # 第一次失败，设置过期时间
            redis_manager.incr(key, expire=cls.LOCK_TIME)
        else:
            # 后续失败只自增，不重置过期时间
            redis_manager.incr(key)

    @classmethod
    def clear_auth_status(cls, email: str):
        """清理安全限制状态(重置密码或登录成功后)"""
        redis_manager.delete(cls._FAIL_COUNT_KEY.format(email=email))

    @classmethod
    def login_rate_limit(cls, client_ip: str, max_requests: int = 10):
        """
        检查是否超过登录限流
        """
        if not cls.LIMITER.allow_request(TTLCacheRateLimiter.LOGIN_NAME,
                                        cls._LOGIN_RATE_LIMIT_KEY.format(client_ip=client_ip), max_requests):
            raise HTTPException(status_code=429, detail=f"登录过于频繁，请 {TTLCacheRateLimiter.LOGIN_TIME_RANGE} 秒后再试")
        
    @classmethod
    def register_rate_limit(cls, client_ip: str, max_requests: int = 5):
        """
        检查是否超过注册限流
        """
        if not cls.LIMITER.allow_request(TTLCacheRateLimiter.REGISTER_NAME,
                                         cls._REGISTER_RATE_LIMIT_KEY.format(client_ip=client_ip), max_requests):
            raise HTTPException(status_code=429, detail=f"注册过于频繁，请 {TTLCacheRateLimiter.REGISTER_TIME_RANGE} 秒后再试")
