import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Jiuwen Agent Studio"
    app_version: str = "1.0.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM info for deepsearch
    llm_basic_base_url: str = ""
    llm_basic_model: str = ""
    llm_basic_api_key: str = ""
    llm_basic_api_type: str = ""

    # config path for deepsearch
    service_config_path: str = ""

    # 数据库类型配置 (mysql/sqlite)
    db_type: str = "mysql"

    # mysql配置
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    agent_db_name: str = ""

     # sqlite配置
    sqlite_db_path: str = "data/databases"
    agent_sqlite_db: str = "agent.db"

    # OBS配置(MinIO)
    minio_host: str = ""
    minio_port: int = 9000
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_bucket: str = ""

    # deepsearch配置
    deepsearch_agent_host: str = ""
    deepsearch_agent_port: int = 6000

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    # 单机版默认用户：设置很长的过期时间，避免用户被踢出
    # access_token: 10年，refresh_token: 10年
    access_token_expire_minutes: int = 5256000  # 10年 = 365 * 10 * 24 * 60
    refresh_token_expire_days: int = 3650  # 10年
    # 非单机部署使用较短的过期时间
    new_access_token_expire_minutes: int = 15 # 15分钟
    new_refresh_token_expire_days: int = 7 # 7天

    # CORS
    allowed_origins: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    
    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # 云邮件推送
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_alias: str = "openJiuwen"
    
    # 用户认证类型开关,只用在后端
    enable_new_auth: bool = Field(False, alias="VITE_ENABLE_NEW_AUTH")

    # External APIs
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    class Config:
        env_file = "../.env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file


# Create settings instance
settings = Settings()
