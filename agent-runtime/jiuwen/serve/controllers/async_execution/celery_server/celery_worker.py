#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
This module contains the initialization of celery app.
"""

import importlib.util
import os
import sys

from celery import Celery
from jiuwen.common.configs.env_constants import (
    EXECUTION_CRYPTOR_CLASS_KEY,
    EXECUTION_CRYPTOR_MODULE_KEY,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.store.redis import get_redis_config, RedisConfig, RedisMode


def load_cryptor():
    """
    Load user-configured encryption and decryption algorithms.
    """
    cryptor_path = os.environ.get(EXECUTION_CRYPTOR_MODULE_KEY)
    cryptor_name = os.environ.get(EXECUTION_CRYPTOR_CLASS_KEY, "Crypt")

    if not cryptor_path:
        logger.info("Crypt module is not configured. Falling back to the default Crypt")

        from jiuwen.common.security.cryptor import Crypt as JiuWenCrypt

        return JiuWenCrypt()

    spec = importlib.util.spec_from_file_location(cryptor_name, cryptor_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[cryptor_name] = module
    spec.loader.exec_module(module)

    # 获取类对象
    cryptor_class = getattr(module, cryptor_name)
    logger.info(f"Successfully loading cryptor {module}")

    from jiuwen.common.security.cryptor import Crypt as JiuWenCrypt

    JiuWenCrypt.decrypt = staticmethod(cryptor_class.decrypt)
    JiuWenCrypt.encrypt = staticmethod(cryptor_class.encrypt)

    return cryptor_class()


def get_celery_broker_and_backend_url():
    """
    Generate celery broker and backend url from redis config.
    """
    cryptor = load_cryptor()

    redis_config: RedisConfig = get_redis_config()
    if not redis_config.passwd:
        raise JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_ASYNC_CELERY_BROKER_INIT_ERROR.code,
            message=StatusCode.WORKFLOW_ASYNC_CELERY_BROKER_INIT_ERROR.errmsg.format(
                reason="please configure the password for redis"
            ),
        )
    redis_config.passwd = cryptor.decrypt(redis_config.passwd)

    if redis_config.mode == RedisMode.SINGLE.value:
        broker = f"redis://:{redis_config.passwd}@{redis_config.host}:{redis_config.port}/{str(redis_config.db)}"
        backend = f"redis://:{redis_config.passwd}@{redis_config.host}:{redis_config.port}/{str(redis_config.db)}"
    else:
        broker = f"rediscluster://:{redis_config.passwd}@{redis_config.cluster_node}/{str(redis_config.db)}"
        backend = f"rediscluster://:{redis_config.passwd}@{redis_config.cluster_node}/{str(redis_config.db)}"

    redis_config.passwd = ""
    return broker, backend


def make_celery(app_name, broker="", backend=""):
    """
    Returns a celery instance.
    """
    if not broker or not backend:
        broker, backend = get_celery_broker_and_backend_url()
    celery_instance = Celery(
        main=app_name,
        broker=broker,
        backend=backend,
        include=["jiuwen.serve.controllers.async_execution.add_task"],
    )
    # Celery配置
    celery_instance.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        message_compression="zlib",  # 减少网络传输量
        broker_connection_retry=True,
        broker_connection_max_retry=10,
        broker_connection_retry_on_startup=True,
    )
    return celery_instance
