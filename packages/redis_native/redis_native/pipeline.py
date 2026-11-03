# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""NativePipeline：SPI Pipeline 协议 → redis-py pipeline 委托。

行为契约（protocols.Pipeline）：
  - 命令方法仅入队并返回 self（链式）；``execute()`` 一次性提交；
  - transaction 由创建点显式解析（REDIS_TRANSACTION_ENABLED 默认），
    不依赖 redis-py 包装类默认；
  - 参数校验在入队期完成（fail-fast），redis-py 原生 DataError 不外泄；
  - execute 的异常统一经 translate_error 收口（事务批失败 ExecAbortError →
    RedisCommandError）。
"""

from __future__ import annotations

import inspect
from typing import Any

from redis_native.converters import (
    duration_to_seconds,
    set_options,
    validate_hset_args,
    validate_set_ttl,
)
from redis_native.error_mapping import REDIS_PY_ERRORS, translate_error

from redis_spi.types import Duration, Key, ScanCursor, SetCondition, Value


class NativePipeline:
    """redis-py pipeline 的 SPI 视图（句柄非协程安全：单协程使用）。"""

    def __init__(self, pipeline: Any, *, operation: str = "pipeline.execute") -> None:
        self._pipe = pipeline
        self._operation = operation
        # redis-py 支持 execute(raise_on_error=False)（命令级错误以原始对象返回结果列表）；
        # 部分替身客户端（fakeredis FakePipeline 等）不支持该参数，回退 raise 路径
        # （替身错误消息含原文，translate_error 子串识别可覆盖）。构造期探测一次；
        # execute 尚未就绪（测试替身构造后才注入）时同样回退 raise 路径。
        execute_method = getattr(pipeline, "execute", None)
        try:
            params = inspect.signature(execute_method).parameters if execute_method else {}
        except (TypeError, ValueError):
            params = {}
        self._collect_errors = "raise_on_error" in params

    # ---- 入队（返回 self 支持链式）----

    def get(self, key: Key) -> "NativePipeline":
        self._pipe.get(key)
        return self

    def set(
        self,
        key: Key,
        value: Value,
        *,
        condition: SetCondition | None = None,
        duration: Duration | None = None,
        keep_ttl: bool = False,
    ) -> "NativePipeline":
        validate_set_ttl(duration, keep_ttl)
        self._pipe.set(
            key,
            value,
            **set_options(condition=condition, duration=duration, keep_ttl=keep_ttl),
        )
        return self

    def delete(self, *keys: Key) -> "NativePipeline":
        self._pipe.delete(*keys)
        return self

    def exists(self, *keys: Key) -> "NativePipeline":
        self._pipe.exists(*keys)
        return self

    def expire(self, key: Key, duration: Duration) -> "NativePipeline":
        self._pipe.expire(key, duration_to_seconds(duration))
        return self

    def hset(
        self,
        key: Key,
        mapping: dict[Value, Value] | None = None,
        *,
        field: Value | None = None,
        value: Value | None = None,
    ) -> "NativePipeline":
        validate_hset_args(mapping, field, value)
        self._pipe.hset(key, mapping=mapping, key=field, value=value)
        return self

    def hget(self, key: Key, field: Value) -> "NativePipeline":
        self._pipe.hget(key, field)
        return self

    def hgetall(self, key: Key) -> "NativePipeline":
        self._pipe.hgetall(key)
        return self

    def hdel(self, key: Key, *fields: Value) -> "NativePipeline":
        self._pipe.hdel(key, *fields)
        return self

    def rpush(self, key: Key, *values: Value) -> "NativePipeline":
        self._pipe.rpush(key, *values)
        return self

    def lrange(self, key: Key, start: int, stop: int) -> "NativePipeline":
        self._pipe.lrange(key, start, stop)
        return self

    def sadd(self, key: Key, *members: Value) -> "NativePipeline":
        self._pipe.sadd(key, *members)
        return self

    def scan(
        self,
        cursor: ScanCursor = 0,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> "NativePipeline":
        self._pipe.scan(cursor, match=match, count=count)
        return self

    # ---- 提交 / 回收 ----

    async def execute(self) -> list[Any]:
        try:
            if self._collect_errors:
                # 命令级错误以「原始异常对象」形式出现在结果列表中（redis-py 各版本一致）。
                # 不走 raise 路径的原因：redis-py 6.4.0 的 raise 消息模板存在格式化缺陷
                # （输出字面量 "{exception.args}"，原始错误文本丢失，WRONGTYPE 等分类
                # 无从识别），结果列表中的对象不受该缺陷影响。
                results = await self._pipe.execute(raise_on_error=False)
            else:
                # 替身/不支持 raise_on_error 的客户端：走 raise 路径（原行为）
                return await self._pipe.execute()
        except REDIS_PY_ERRORS as exc:
            # 连接/协议层错误（非命令级）：整体失败，翻译上抛
            raise translate_error(exc, operation=self._operation) from exc
        # 命令级错误：翻译第一个错误上抛（已执行命令生效——Redis 无事务回滚，
        # 与 raise 路径执行范围一致：非事务命令缓冲一次性发送，事务 EXEC 全执行）。
        for item in results:
            if isinstance(item, BaseException):
                raise translate_error(item, operation=self._operation) from item
        return results

    async def aclose(self) -> None:
        await self._pipe.aclose()
