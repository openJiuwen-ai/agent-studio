# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Acme demo：redis-py 异常 → redis_spi 异常翻译（demo 自带，不依赖 redis_native）。

企业实现参考要点（契约总则 #4）：业务层不得接触底层客户端异常——在与自研
SDK 的**边界处**统一翻译为 redis_spi 体系，原始异常挂 ``__cause__`` 不吞掉。
demo 的"自研 SDK"是 fakeredis（redis-py 兼容），故翻译表按 redis-py 异常书写；
企业按自身 SDK 的异常体系同构替换本模块即可。
"""

from __future__ import annotations

import functools
from typing import Any, Callable

import redis.exceptions as redis_exc

from redis_spi.exceptions import (
    RedisAuthFailureError,
    RedisCommandError,
    RedisConnectionError,
    RedisError,
    RedisScriptError,
    RedisTimeoutError,
    RedisWrongTypeError,
)

#: 需要翻译的 redis-py 异常根（RedisClusterException 不继承 RedisError，并列收录）。
REDIS_PY_ERRORS: tuple[type[BaseException], ...] = (
    redis_exc.RedisError,
    redis_exc.RedisClusterException,
)

#: 认证/鉴权失败（AuthenticationError ⊂ ConnectionError，须先判）。
_AUTH_ERRORS = (
    redis_exc.AuthenticationError,
    redis_exc.AuthorizationError,
    redis_exc.AuthenticationWrongNumberOfArgsError,
    redis_exc.NoPermissionError,
)

#: 错误上下文中 key 的截断长度。
_KEY_CONTEXT_LIMIT = 128


def acme_translate(
    exc: BaseException,
    *,
    operation: str,
    redis_key: str | None = None,
    result_known: bool = True,
) -> RedisError:
    """redis-py 异常 → redis_spi 异常（不 raise；调用方 ``raise ... from exc``）。"""
    message = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, _AUTH_ERRORS):
        return RedisAuthFailureError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.TimeoutError):
        return RedisTimeoutError(
            message, result_known=result_known, redis_key=redis_key, operation=operation
        )
    if isinstance(exc, redis_exc.NoScriptError):
        return RedisScriptError(message, command=operation, detail=str(exc))
    if isinstance(exc, redis_exc.ResponseError):
        # WRONGTYPE 识别用子串而非前缀：pipeline/代理层错误消息可能带上下文前缀。
        if "WRONGTYPE" in str(exc).upper():
            return RedisWrongTypeError(message, redis_key=redis_key, operation=operation)
        return RedisCommandError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.ConnectionError):
        return RedisConnectionError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.DataError):
        return RedisCommandError(message, redis_key=redis_key, operation=operation)
    return RedisCommandError(message, redis_key=redis_key, operation=operation)


def acme_command(operation: str, *, timeout_result_known: bool = True) -> Callable:
    """异步命令装饰器：统一异常翻译 + operation/key 错误上下文。

    只捕 redis-py 异常；redis_spi 异常（本层参数校验）与编程错误原样透传。
    ``timeout_result_known=False`` 用于非幂等命令（计数/写类超时结果未知）。
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(self, *args, **kwargs)
            except REDIS_PY_ERRORS as exc:
                raise acme_translate(
                    exc,
                    operation=operation,
                    redis_key=_context_key(args),
                    result_known=timeout_result_known,
                ) from exc

        return wrapper

    return decorator


def _context_key(args: tuple) -> str | None:
    """尽力提取首个 key 作错误上下文（截断；bytes 容错解码）。"""
    for arg in args:
        if isinstance(arg, bytes):
            return arg.decode("utf-8", errors="replace")[:_KEY_CONTEXT_LIMIT]
        if isinstance(arg, str):
            return arg[:_KEY_CONTEXT_LIMIT]
    return None
