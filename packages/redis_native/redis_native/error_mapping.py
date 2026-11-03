# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis-py 异常 → redis_spi 异常翻译（SPI 契约总则 #4：业务不接触原生异常）。

映射表（redis-py 8.x 异常体系实测核对）：

  redis.exceptions.AuthenticationError / AuthorizationError /
  AuthenticationWrongNumberOfArgsError / NoPermissionError
      → RedisAuthFailureError（⊂ Connection，便于审计告警区分）
  redis.exceptions.TimeoutError
      → RedisTimeoutError（result_known 由调用点声明：计数/写类超时结果未知）
  redis.exceptions.ClusterError / RedisClusterException / AskError /
  MovedError / TryAgainError / ClusterCrossSlotError
      → RedisClusterError
  redis.exceptions.NoScriptError → RedisScriptError（⊂ Command）
  redis.exceptions.ResponseError("WRONGTYPE ...") → RedisWrongTypeError
  redis.exceptions.ConnectionError（含 MaxConnectionsError/BusyLoadingError）
      → RedisConnectionError
  redis.exceptions.PubSubError → RedisConnectionError（订阅连接断开语义）
  redis.exceptions.DataError → RedisCommandError（调用方用法错误）
  redis.exceptions.ResponseError（其余）/ WatchError / InvalidResponse /
  OutOfMemoryError 及其他 RedisError 子类
      → RedisCommandError（兜底，服务端错误回复）

注意：ClusterDownError 同时继承 ClusterError 与 ResponseError，AskError 族
只继承 ResponseError——**Cluster 判定必须先于 ResponseError 兜底**。
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

import redis.exceptions as redis_exc

from redis_spi.exceptions import (
    RedisAuthFailureError,
    RedisClusterError,
    RedisCommandError,
    RedisConnectionError,
    RedisError,
    RedisScriptError,
    RedisTimeoutError,
    RedisWrongTypeError,
)

#: redis-py 侧需要翻译的异常根（RedisClusterException 不继承 RedisError，须并列）。
REDIS_PY_ERRORS: tuple[type[BaseException], ...] = (
    redis_exc.RedisError,
    redis_exc.RedisClusterException,
)

#: 认证/鉴权失败（注意 AuthenticationError ⊂ ConnectionError，须先判）。
_AUTH_ERRORS = (
    redis_exc.AuthenticationError,
    redis_exc.AuthorizationError,
    redis_exc.AuthenticationWrongNumberOfArgsError,
    redis_exc.NoPermissionError,
)

#: 集群语义的 ResponseError 子类（继承链上不带 ClusterError，须显式枚举；
#: MOVED/ASK/TRYAGAIN/CROSSSLOT 均为集群重定向/拓扑语义）。
_CLUSTER_RESPONSE_ERRORS = (
    redis_exc.MovedError,
    redis_exc.AskError,
    redis_exc.TryAgainError,
    redis_exc.ClusterCrossSlotError,
)

#: 错误上下文中 key 的截断长度（防超长 key 刷屏日志）。
_KEY_CONTEXT_LIMIT = 128


def translate_error(
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
    if isinstance(exc, redis_exc.ClusterError) or isinstance(
        exc, redis_exc.RedisClusterException
    ) or isinstance(exc, _CLUSTER_RESPONSE_ERRORS):
        return RedisClusterError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.NoScriptError):
        return RedisScriptError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.ResponseError):
        # WRONGTYPE 识别用子串而非前缀：pipeline/代理层错误消息可能带上下文前缀
        # （如 fakeredis："Command # 2 (...) of pipeline caused error: ('WRONGTYPE ...')"）。
        if "WRONGTYPE" in str(exc).upper():
            return RedisWrongTypeError(message, redis_key=redis_key, operation=operation)
        return RedisCommandError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.ConnectionError):
        return RedisConnectionError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.PubSubError):
        return RedisConnectionError(message, redis_key=redis_key, operation=operation)
    if isinstance(exc, redis_exc.DataError):
        return RedisCommandError(message, redis_key=redis_key, operation=operation)
    # 兜底：WatchError / InvalidResponse / OutOfMemoryError / LockError 等其余子类。
    return RedisCommandError(message, redis_key=redis_key, operation=operation)


def spi_command(operation: str, *, timeout_result_known: bool = True) -> Callable:
    """异步命令方法装饰器：统一异常翻译 + operation/key 错误上下文。

    - 只捕 redis-py 异常；redis_spi 异常（本层参数校验）与非 redis 异常
      （编程错误）原样透传，不吞不裹；
    - ``timeout_result_known=False`` 用于非幂等命令（计数/写）：超时后结果未知，
      禁止调用方盲重试（nos Counter 契约）；
    - redis_key 为尽力提取的首个 str/bytes 位置参数（诊断上下文，非精确契约）。
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(self, *args, **kwargs)
            except REDIS_PY_ERRORS as exc:
                raise translate_error(
                    exc,
                    operation=operation,
                    redis_key=_context_key(args),
                    result_known=timeout_result_known,
                ) from exc

        return wrapper

    return decorator


def _context_key(args: tuple) -> str | None:
    """尽力提取首个 key 作错误上下文（截断；bytes 按 UTF-8 容错解码）。"""
    for arg in args:
        if isinstance(arg, bytes):
            return arg.decode("utf-8", errors="replace")[:_KEY_CONTEXT_LIMIT]
        if isinstance(arg, str):
            return arg[:_KEY_CONTEXT_LIMIT]
    return None
