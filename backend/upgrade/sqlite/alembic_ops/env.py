import importlib
import logging
import os
import sys
from logging.config import fileConfig
from os.path import abspath, dirname

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# 定义项目根目录
PROJECT_ROOT = dirname(dirname(dirname(dirname(dirname(abspath(__file__))))))

# 定义backend根目录（用于数据库路径）
BACKEND_ROOT = dirname(dirname(dirname(dirname(abspath(__file__)))))

# 将项目根目录添加到 sys.path
sys.path.append(PROJECT_ROOT)

# 加载 .env 文件
dotenv_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)



from openjiuwen_studio.ops.modules.prompt.infra.repositories import orm_repo

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ==================== SQLite 索引名称冲突处理 ====================
# 为 SQLite 重命名索引以避免不同表间索引名称冲突
# 这与 main.py 中的逻辑保持一致
logger = logging.getLogger(__name__)


def rename_sqlite_indexes():
    """重命名 SQLite 索引以避免冲突"""
    db_type = os.getenv("DB_TYPE", "mysql").lower()
    if db_type == "sqlite":
        for table in orm_repo.Base.metadata.tables.values():
            if hasattr(table, "indexes"):
                for idx in list(table.indexes):  # 使用 list() 避免迭代时修改
                    old_name = idx.name
                    new_name = f"{old_name}_{table.name}"
                    if old_name != new_name:  # 只在需要时重命名
                        idx.name = new_name
                        logger.info(f"[Alembic] Renamed index: {table.name}.{old_name} -> {new_name}")

rename_sqlite_indexes()
# ==================== 索引重命名完成 ====================

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = orm_repo.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    db_type = os.getenv("DB_TYPE", "mysql")
    url = None
    if db_type == "sqlite":
        sqlite_db = os.getenv("OPS_SQLITE_DB", "ops.db")
        # 确保数据库文件路径是绝对路径
        if not os.path.isabs(sqlite_db):
            sqlite_db = os.path.join(BACKEND_ROOT, "data", "databases", sqlite_db)
        url = f"sqlite:///{sqlite_db}"
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("OPS_DB_NAME")
        if all([db_user, db_password, db_host, db_port, db_name]):
            url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    if url is None:
        url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    db_type = os.getenv("DB_TYPE", "mysql")
    render_as_batch = False
    url = None
    if db_type == "sqlite":
        sqlite_db = os.getenv("OPS_SQLITE_DB", "ops.db")
        # 确保数据库文件路径是绝对路径
        if not os.path.isabs(sqlite_db):
            sqlite_db = os.path.join(BACKEND_ROOT, "data", "databases", sqlite_db)
        url = f"sqlite:///{sqlite_db}"
        render_as_batch = True
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("OPS_DB_NAME")
        if all([db_user, db_password, db_host, db_port, db_name]):
            url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    if url is None:
        url = config.get_main_option("sqlalchemy.url")

    from sqlalchemy import create_engine
    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=render_as_batch
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
