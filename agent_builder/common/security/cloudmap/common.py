#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
cloud map common
"""

import functools
import time
from datetime import datetime
from datetime import timedelta

from agent_builder.common.logging.base import logger


class RetryException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def retry(retry_times, retry_delay, retry_exceptions=(Exception,)):
    """retry func"""

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            error = None
            for attempt in range(retry_times):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions:
                    logger.error(
                        "Operation failed due to configuration or network issue."
                    )
                logger.error("Trying attempt %s of %s.", attempt + 1, retry_times)
                time.sleep(retry_delay)
            raise RetryException(
                f"Exceed max retry times {retry_times} failed!"
            ) from error

        return wrapper

    return decorator


class PollingException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def polling(polling_timeout, polling_delay, continue_exceptions=(Exception,)):
    """polling func"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            error = None
            start_time = time.time()
            cost = 0
            while cost < polling_timeout:
                try:
                    return func(*args, **kwargs)
                except continue_exceptions:
                    logger.error(
                        "Operation failed due to configuration or network issue."
                    )
                    end_time = time.time()
                    cost = int(end_time - start_time)
                logger.warning(
                    "Trying attempt %s seconds of %s.", cost, polling_timeout
                )
                time.sleep(polling_delay)
            raise PollingException(
                f"Exceed max polling time {polling_timeout} seconds failed!"
            ) from error

        return wrapper

    return decorator


def timed_lru_cache(seconds: int, maxsize: int = 128, typed: bool = False):
    """timed_lru_cache"""

    def decorator(func):
        func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
        func.life_time = timedelta(seconds=seconds)
        func.expire_time = datetime.utcnow() + func.life_time

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if datetime.utcnow() > func.expire_time:
                func.cache_clear()
                func.expire_time = datetime.utcnow() + func.life_time

            return func(*args, **kwargs)

        wrapper.cache_info = func.cache_info
        wrapper.cache_clear = func.cache_clear
        return wrapper

    return decorator
