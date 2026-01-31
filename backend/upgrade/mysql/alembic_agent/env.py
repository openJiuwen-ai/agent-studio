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

# 将项目根目录添加到 sys.path
sys.path.append(PROJECT_ROOT)

# 加载 .env 文件
dotenv_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from openjiuwen_studio.models.db_fun_base import Base

# Dynamically import all models to ensure they are registered with Base.metadata
models_dir = os.path.join(PROJECT_ROOT, 'backend', 'openjiuwen_studio', 'models')
for filename in os.listdir(models_dir):
    if filename.endswith('.py') and filename != '__init__.py':
        module_name = f"openjiuwen_studio.models.{filename[:-3]}"
        try:
            importlib.import_module(module_name)
        except Exception as e:
            logging.error(f"Failed to import module {module_name}: {e}")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Build URL from env vars for offline mode as well
    db_type = os.getenv("DB_TYPE", "mysql")
    if db_type == "sqlite":
        sqlite_db = os.getenv("AGENT_SQLITE_DB")
        url = f"sqlite:///{sqlite_db}"
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("AGENT_DB_NAME")
        
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {})
    
    # Override sqlalchemy.url with environment variables
    db_type = os.getenv("DB_TYPE", "mysql")
    if db_type == "sqlite":
        sqlite_db = os.getenv("AGENT_SQLITE_DB")
        url = f"sqlite:///{sqlite_db}"
        section["sqlalchemy.url"] = url
        render_as_batch = True
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("AGENT_DB_NAME")
        
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
