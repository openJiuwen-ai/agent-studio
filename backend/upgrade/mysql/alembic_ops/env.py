import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# 定义项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# 将项目根目录添加到 sys.path
sys.path.append(PROJECT_ROOT)

# 加载 .env 文件
dotenv_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from openjiuwen_studio.ops.modules.prompt.infra.database import Base
# Import the module that defines the models to register them with Base
from openjiuwen_studio.ops.modules.prompt.infra.repositories import orm_repo

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Build URL from env vars for offline mode as well
    db_type = os.getenv("DB_TYPE", "mysql")
    if db_type == "sqlite":
        sqlite_db = os.getenv("OPS_SQLITE_DB")
        url = f"sqlite:///{sqlite_db}"
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("OPS_DB_NAME")
        
        if all([db_user, db_password, db_host, db_port, db_name]):
            url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            # Fallback to .ini value if env vars missing
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
    section = config.get_section(config.config_ini_section, {})
    
    # Override sqlalchemy.url with environment variables
    db_type = os.getenv("DB_TYPE", "mysql")
    if db_type == "sqlite":
        sqlite_db = os.getenv("OPS_SQLITE_DB")
        url = f"sqlite:///{sqlite_db}"
        section["sqlalchemy.url"] = url
        render_as_batch = True
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("OPS_DB_NAME")
        
        if all([db_user, db_password, db_host, db_port, db_name]):
            url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            section["sqlalchemy.url"] = url
        render_as_batch = False

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

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
