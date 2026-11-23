#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from concurrent.futures import ThreadPoolExecutor

from jiuwen.common.log.base import logger
from utils.constants import (
    REDIS_GLOBAL_VALS_NAME,
    REDIS_LTM_VALS_PREFIX,
    REDIS_LTM_CHAT_PREFIX,
)

from . import long_memory_config
from .storage.vector_db_factory import VectorDbFactory
from .utils import handle_exceptions

REDIS_SCAN_BATCH_SIZE = 500


def clean_workflow_memory(workflow_id):
    if long_memory_config.enable:
        with ThreadPoolExecutor() as executor:
            executor.submit(async_clear_workflow_memory, workflow_id)

    # 清理全局变量redis数据
    remove_redis_workflow_global_vals(f"{REDIS_GLOBAL_VALS_NAME}.{workflow_id}*")


@handle_exceptions
def async_clear_workflow_memory(workflow_id):
    logger.info("start clear workflow memory")
    # 清理向量数据库里的文件
    VectorDbFactory.get_storage().remove(tags=[workflow_id])
    # 清理obs里的文件
    remove_redis_workflow_global_vals(f"{REDIS_LTM_VALS_PREFIX}:{workflow_id}*")
    remove_redis_workflow_global_vals(f"{REDIS_LTM_CHAT_PREFIX}:{workflow_id}*")
    logger.info("done clear workflow memory")


def remove_redis_workflow_global_vals(store_key):
    from .global_vals_callback_handler import redis_client

    if not redis_client:
        return
    # python没有do-while，用字符0进入循环
    cursor = "0"
    deleted_count = 0
    try:
        # 使用SCAN命令迭代匹配前缀
        while cursor != 0:
            cursor, keys = redis_client._redis.scan(
                cursor=cursor, match=store_key, count=REDIS_SCAN_BATCH_SIZE
            )
            if keys:
                redis_client._redis.delete(*keys)
                deleted_count += len(keys)
        logger.info(f"delete {store_key} redis record {deleted_count}")
    except Exception as e:
        logger.error("delete redis memory file error", e)
