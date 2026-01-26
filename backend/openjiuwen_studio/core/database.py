import time
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import ENABLED, Filter
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.config import settings


def get_database_url() -> str:
    """根据数据库类型生成数据库连接URL"""
    if settings.db_type.lower() == "mysql":
        return (f"mysql+pymysql://{settings.db_user}:{settings.db_password}@"
                   f"{settings.db_host}:{settings.db_port}/{settings.agent_db_name}?charset=utf8mb4")

    elif settings.db_type.lower() == "sqlite":
        # 确保数据库目录存在
        db_path = Path(settings.sqlite_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}/{settings.agent_sqlite_db}"

    else:
        raise ValueError(f"Unsupported database type: {settings.db_type.lower()}")

database_url = get_database_url()

# Create database engine
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_milliseconds() -> int:
    """返回当前时间戳的毫秒整数部分."""
    return int(time.time() * 1000)


milliseconds = get_milliseconds


class LazyMinioClient:
    """
    实现 MinIO 客户端的懒加载和错误处理。
    只在首次需要时尝试初始化，如果初始化失败则记录错误并保持未初始化状态，
    后续每次操作都尝试重新初始化，失败则抛出异常。
    """
    _instance = None
    _client = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LazyMinioClient, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def ensure_minio_lifecycle(minio_client: Minio, bucket_name: str, days: int = 99):
        """
        确保 MinIO bucket 设置了自动过期规则（days 天后删除）
        使URL永久有效（在文件存在期间），但文件会自动过期删除
        只需调用一次，幂等安全。
        """
        try:
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                logger.info(f"Bucket '{bucket_name}' created.")
            # 构造生命周期规则
            config = LifecycleConfig(
                [
                    Rule(
                        ENABLED,
                        rule_filter=Filter(prefix=""),
                        expiration=Expiration(days=days)
                    )
                ]
            )
            minio_client.set_bucket_lifecycle(bucket_name, config)
            # 设置桶策略为公开读（URL永久有效直到文件被删除）
            import json
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                    }
                ]
            }
            minio_client.set_bucket_policy(bucket_name, json.dumps(policy))
            logger.info(f"Bucket '{bucket_name}' configured: lifecycle {days} days, public read enabled.")
        except Exception as e:
            logger.exception(f"Failed to set lifecycle rule for bucket '{bucket_name}': {e}")

    def get_client(self) -> Minio:
        """获取 MinIO 客户端实例，如果尚未初始化或上次初始化失败，则尝试初始化。"""
        if not self._initialized:
            self._initialize_client()
        if not self._client:
            raise RuntimeError("MinIO client is not available due to "
                               "previous initialization failure or missing configuration.")
        return self._client

    def _initialize_client(self):
        """初始化 MinIO 客户端"""
        try:
            logger.debug("Attempting to initialize MinIO client...")
            # 尝试从 settings 中获取配置
            if not all([settings.minio_host, settings.minio_port,
                        settings.minio_access_key, settings.minio_secret_key]):
                raise ValueError("One or more required MinIO configuration settings are missing.")

            client = Minio(
                endpoint=f"{settings.minio_host}:{settings.minio_port}",
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure
            )

            # 进行一个简单的操作验证连接
            buckets = client.list_buckets()

            self._client = client
            self.ensure_minio_lifecycle(client, settings.minio_bucket)
            self._initialized = True
            logger.info("MinIO client initialized successfully.")
        except (ValueError, S3Error) as e:
            self._client = None
            self._initialized = False # 确保标记为未初始化
            logger.error(f"Failed to initialize MinIO client: {e}. Service will continue without MinIO.")
        except Exception as e:
            self._client = None
            self._initialized = False
            logger.exception(f"Unexpected error during MinIO client initialization: {e}. "
                                   f"Service will continue without MinIO.")


# 提供一个便捷函数给外部使用
def get_minio_client() -> Minio:
    """便捷函数，获取懒加载的 MinIO 客户端实例。"""
    lazy_client = LazyMinioClient()
    return lazy_client.get_client()
