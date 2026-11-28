#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
Authorization module
"""

from functools import wraps
from typing import Callable

from jiuwen.common.log.base import logger
from jiuwen.serve.common.context import g

DEFAULT_PROJECT_ID = "0"
DEFAULT_DOMAIN_ID = "0"


class Auth:
    """
    一个用于提供RESTful API授权的装饰器类。
    """

    @staticmethod
    def authenticate(func: Callable):
        """
        用于API授权的装饰器函数。

        Args:
        func (Callable): 需要被装饰的函数。

        Returns:
        decorator: 返回一个装饰后的函数，该函数在执行时会先进行授权相关的操作。
        """

        @wraps(func)
        def decorator(*args, **kwargs):
            # copy-then-set: ContextVar 的 default={} 是模块级共享对象，
            # 原地写入会污染所有后续请求/任务的上下文
            g.set(
                {
                    **(g.get() or {}),
                    "domain_id": DEFAULT_DOMAIN_ID,
                    "project_id": DEFAULT_DOMAIN_ID,
                }
            )
            logger.debug(f"basic auth: {func.__name__}")
            return func(*args, **kwargs)

        return decorator
