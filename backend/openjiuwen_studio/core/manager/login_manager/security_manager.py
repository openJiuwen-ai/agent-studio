import random
import string

from openjiuwen_studio.core.manager.redis_manager.redis_client import redis_manager_str as redis_manager


class SecurityManager:
    """安全管理器：处理验证码、登录失败锁定"""
    _REG_CODE_KEY = "auth:reg:code:{email}"
    _REG_LIMIT_KEY = "auth:reg:limit:{email}"
    _RESET_CODE_KEY = "auth:reset:code:{email}"
    _RESET_LIMIT_KEY = "auth:reset:limit:{email}"
    _FAIL_COUNT_KEY = "auth:fail:count:{email}"

    MAX_LOGIN_ATTEMPTS = 5
    LOCK_TIME = 1800  # 30分钟锁定
    CODE_EXPIRE = 600 # 10分钟验证码有效
    LIMIT_EXPIRE = 60 # 60秒发送频率限制

    # 邮箱验证码相关操作
    @classmethod
    def generate_and_save_code(cls, email: str, action_type: str = "reg") -> str:
        """生成验证码并存入 Redis"""
        code = ''.join(random.choices(string.digits, k=6))
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
        key = template.format(email=email)
        saved_code = redis_manager.get(key)
        
        if saved_code and saved_code == input_code:
            redis_manager.delete(key) # 验证通过立即销毁
            return True
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
