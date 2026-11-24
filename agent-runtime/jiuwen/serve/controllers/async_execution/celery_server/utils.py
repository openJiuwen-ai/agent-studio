#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

"""
This module contains utility functions for celery.
"""

import os

from jiuwen.common.configs.env_constants import EXECUTION_CELERY_POOL_KEY

_PREFORK = "prefork"


def is_force_terminate() -> bool:
    """
    Currently, force termination is supported only when celery_pool is configured as 'prefork'.
    """
    celery_pool = os.environ.get(EXECUTION_CELERY_POOL_KEY, "")
    if celery_pool.lower() in [_PREFORK]:
        return True
    return False
