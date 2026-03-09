#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from openjiuwen.core.common.logging import logger
from openjiuwen_studio.ops.config import settings
from openjiuwen_studio.ops.common.date_time_util import get_china_datetime
from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils


def get_database_url(db_name: str = None) -> str:
    """根据数据库类型生成数据库连接URL"""
    if settings.DB_TYPE.lower() == "mysql":
        db_password = SecurityUtils.get_decrypted_secret("DB_PASSWORD", settings.DB_PASSWORD)
        if db_name == "ops":
            return (f"mysql+pymysql://{settings.DB_USER}:{db_password}@"
                   f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.OPS_DB_NAME}?charset=utf8mb4")
        elif db_name == "agent":
            return (f"mysql+pymysql://{settings.DB_USER}:{db_password}@"
                   f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.AGENT_DB_NAME}?charset=utf8mb4")
        else:
            raise ValueError(f"Unknown database name: {db_name}")
    elif settings.DB_TYPE.lower() == "sqlite":
        # 确保数据库目录存在
        db_path = Path(settings.SQLITE_DB_PATH)
        db_path.mkdir(parents=True, exist_ok=True)

        if db_name == "ops":
            return f"sqlite:///{db_path}/{settings.OPS_SQLITE_DB}"
        elif db_name == "agent":
            return f"sqlite:///{db_path}/{settings.AGENT_SQLITE_DB}"
        else:
            raise ValueError(f"Unknown database name: {db_name}")
    else:
        raise ValueError(f"Unsupported database type: {settings.DB_TYPE}")


def get_async_database_url(db_url: str) -> str:
    """将同步数据库URL转换为异步URL"""
    if "mysql+pymysql" in db_url:
        return db_url.replace("pymysql", "aiomysql")
    elif "sqlite" in db_url:
        return db_url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        raise ValueError(f"Unsupported database URL for async: {db_url}")


def _check_async_drivers():
    """检查异步数据库驱动是否可用"""
    if settings.DB_TYPE.lower() == "sqlite":
        try:
            import aiosqlite
            return True
        except ImportError:
            pass
    elif settings.DB_TYPE.lower() == "mysql":
        try:
            import aiomysql
            return True
        except ImportError:
            pass

    return False

# 延迟初始化的数据库引擎和会话工厂
engine = None
engine_agent = None
SessionLocalOps = None
SessionLocalAgent = None
async_engine_ops = None
async_engine_agent = None
AsyncSessionLocalOps = None
AsyncSessionLocalAgent = None


def _get_engine_kwargs():
    """获取数据库引擎参数"""
    if settings.DB_TYPE.lower() == "mysql":
        return {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "echo": settings.DEBUG
        }
    elif settings.DB_TYPE.lower() == "sqlite":
        return {
            "connect_args": {"check_same_thread": False},
            "echo": settings.DEBUG
        }
    else:
        raise ValueError(f"Unsupported database type: {settings.DB_TYPE}")


def _init_engines():
    """初始化数据库引擎"""
    global engine, engine_agent, SessionLocalOps, SessionLocalAgent
    global async_engine_ops, async_engine_agent, AsyncSessionLocalOps, AsyncSessionLocalAgent

    if engine and engine_agent:
        return  # 已经初始化过了

    try:
        # 获取数据库连接URL
        DATABASE_URL_OPS = get_database_url("ops")
        DATABASE_URL_AGENT = get_database_url("agent")

        # 获取引擎参数
        engine_kwargs = _get_engine_kwargs()

        # 同步引擎
        engine = create_engine(DATABASE_URL_OPS, **engine_kwargs)
        engine_agent = create_engine(DATABASE_URL_AGENT, **engine_kwargs)

        # 同步会话工厂
        SessionLocalOps = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        SessionLocalAgent = sessionmaker(autocommit=False, autoflush=False, bind=engine_agent)

        # 异步引擎配置（仅在驱动可用时初始化）
        if _check_async_drivers():
            async_engine_kwargs = engine_kwargs.copy()
            if settings.DB_TYPE.lower() == "sqlite":
                async_engine_kwargs.pop("connect_args", None)

            # 异步数据库URL
            ASYNC_DATABASE_URL_OPS = get_async_database_url(DATABASE_URL_OPS)
            ASYNC_DATABASE_URL_AGENT = get_async_database_url(DATABASE_URL_AGENT)

            global async_engine_ops, async_engine_agent
            global AsyncSessionLocalOps, AsyncSessionLocalAgent
            async_engine_ops = create_async_engine(ASYNC_DATABASE_URL_OPS, **async_engine_kwargs)
            async_engine_agent = create_async_engine(ASYNC_DATABASE_URL_AGENT, **async_engine_kwargs)

            # 异步会话工厂
            AsyncSessionLocalOps = sessionmaker(bind=async_engine_ops, class_=AsyncSession, expire_on_commit=False)
            AsyncSessionLocalAgent = sessionmaker(bind=async_engine_agent, class_=AsyncSession, expire_on_commit=False)
        else:
            logger.warning("警告: 异步数据库驱动不可用，只使用同步数据库功能")
            # 设置异步引擎为None，后续使用时需要检查
            async_engine_ops = None
            async_engine_agent = None
            AsyncSessionLocalOps = None
            AsyncSessionLocalAgent = None

    except ImportError as e:
        # 处理缺少驱动的情况
        if settings.DB_TYPE.lower() == "mysql" and "pymysql" in str(e):
            logger.warning(f"警告: MySQL驱动不可用，请安装 pymysql: pip install pymysql")
            logger.warning("继续运行，但数据库功能将不可用")
        elif settings.DB_TYPE.lower() == "sqlite" and "sqlite3" in str(e):
            logger.warning(f"警告: SQLite驱动不可用: {e}")
        else:
            logger.warning(f"数据库初始化警告: {e}")
            raise e
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise e


def get_database_url_cached(db_name: str = None) -> str:
    """获取缓存的数据库URL"""
    return get_database_url(db_name)


Base = declarative_base()
BaseAgent = declarative_base()


def get_db_ops():
    """提供ops数据库会话的依赖"""
    _init_engines()  # 确保引擎已初始化
    db = SessionLocalOps()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception as e:
            logger.warning(f"Error closing database session: {e}")


def get_db_agent():
    """提供agent数据库会话的依赖"""
    _init_engines()  # 确保引擎已初始化
    db = SessionLocalAgent()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception as e:
            logger.warning(f"Error closing database session: {e}")


async def get_async_session_ops() -> AsyncSession:
    """获取ops数据库的异步会话"""
    _init_engines()  # 确保引擎已初始化
    if AsyncSessionLocalOps is None:
        raise RuntimeError("异步数据库驱动不可用，无法创建异步会话")
    async with AsyncSessionLocalOps() as session:
        yield session


async def get_async_session_agent() -> AsyncSession:
    """获取agent数据库的异步会话"""
    _init_engines()  # 确保引擎已初始化
    if AsyncSessionLocalAgent is None:
        raise RuntimeError("异步数据库驱动不可用，无法创建异步会话")
    async with AsyncSessionLocalAgent() as session:
        yield session


def create_database_tables():
    """创建数据库表"""
    try:
        _init_engines()  # 确保引擎已初始化
        logger.info(f"Creating tables for {settings.DB_TYPE} database...")

        # 创建OPS数据库表
        Base.metadata.create_all(bind=engine)
        logger.info("OPS database tables created successfully")

        # 创建Agent数据库表
        BaseAgent.metadata.create_all(bind=engine_agent)
        logger.info("Agent database tables created successfully")

        # Reset all tasks with status 'running' to 'failed' to prevent orphaned zombie tasks after service restart
        reset_orphaned_running_jobs(engine)

        logger.info("Evaluation database tables creation completed")

    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        # 如果是驱动相关的错误，提供友好的提示
        error_str = str(e).lower()
        if "pymysql" in error_str:
            logger.error("提示: 请安装MySQL驱动: pip install pymysql")
        elif "sqlite3" in error_str:
            logger.error("提示: SQLite驱动问题，请检查Python环境")
        elif "aiosqlite" in error_str or "aiomysql" in error_str:
            logger.warning("提示: 异步驱动不可用，但不影响同步功能")
        else:
            logger.error(f"未知错误: {e}")
        raise


def get_database_info():
    """获取当前数据库配置信息"""
    DATABASE_URL_OPS = get_database_url("ops")
    DATABASE_URL_AGENT = get_database_url("agent")

    return {
        "type": settings.DB_TYPE,
        "ops_url": DATABASE_URL_OPS.split("://")[0] + "://***",  # 隐藏密码
        "agent_url": DATABASE_URL_AGENT.split("://")[0] + "://***",  # 隐藏密码
        "debug": settings.DEBUG
    }


# 导出便利函数
def is_mysql() -> bool:
    """检查是否使用MySQL"""
    return settings.DB_TYPE.lower() == "mysql"


def is_sqlite() -> bool:
    """检查是否使用SQLite"""
    return settings.DB_TYPE.lower() == "sqlite"


def reset_orphaned_running_jobs(ops_engine):
    """
    Reset all 'running' jobs in job_user_info table to 'failed' after unexpected shutdown.
    Uses raw SQL to avoid ORM/model dependency and circular import risks.
    """
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(ops_engine)
        if "job_user_info" not in inspector.get_table_names():
            logger.warning("Table 'job_user_info' does not exist. Skipping job reset.")
            return 0
        current_time = get_china_datetime()
        with ops_engine.connect() as conn:
            update_sql = """
                UPDATE job_user_info 
                SET status = :status,
                    errorMsg = :errorMsg,
                    updated_at = :updated_at
                WHERE status = :old_status
            """
            result = conn.execute(
                text(update_sql),
                {
                    "status": "failed",
                    "errorMsg": "System terminated abnormally",
                    "old_status": "running",
                    "updated_at": current_time

                }
            )
            conn.commit()
            count = result.rowcount
            logger.info(f"Successfully reset {count} orphaned running job(s) to 'failed'.")
            return count

    except Exception as e:
        logger.error(f"Failed to reset orphaned jobs: {e}")
        return 0
