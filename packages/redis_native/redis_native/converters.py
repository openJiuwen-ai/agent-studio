# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SPI 值对象 → redis-py 调用参数的换算（client / pipeline / capabilities 共用）。"""

from __future__ import annotations

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import Duration, SetCondition


def duration_to_seconds(duration: Duration) -> int:
    """Duration → 秒（向上取整；EXPIRE / EXPIREAT 秒级命令语义）。

    毫秒向上取整保证 TTL 不被截短为 0（正毫秒 → 至少 1 秒）。
    """
    return -(-duration.milliseconds // 1000)


def set_options(
    *,
    condition: SetCondition | None,
    duration: Duration | None,
    keep_ttl: bool,
) -> dict:
    """SPI set 条件参数 → redis-py set kwargs。

    TTL 一律走 px（毫秒）保持精度；duration 与 keep_ttl 的互斥由调用方校验
    （SPI 契约：同给抛 RedisCommandError）。
    """
    options: dict = {}
    if condition is SetCondition.NX:
        options["nx"] = True
    elif condition is SetCondition.XX:
        options["xx"] = True
    if duration is not None:
        options["px"] = duration.milliseconds
    if keep_ttl:
        options["keepttl"] = True
    return options


def condition_options(condition: SetCondition | None) -> dict:
    """SPI SetCondition → redis-py zadd/geoadd 的 nx/xx kwargs（多命令共用）。"""
    if condition is SetCondition.NX:
        return {"nx": True}
    if condition is SetCondition.XX:
        return {"xx": True}
    return {}


def blocking_timeout(timeout: Duration | None) -> int:
    """阻塞命令超时：Duration → 整数秒（redis-py 0 = 无限阻塞；None = 无限阻塞）。

    真实 Redis 要求阻塞超时为整数秒（非整数报 "timeout is not an integer
    or out of range"）——正毫秒向上取整（1500ms→2s，宁可多等不提前醒），
    避免浮点经 redis-py 编码成 1.0 形态。
    """
    if timeout is None:
        return 0
    return -(-timeout.milliseconds // 1000)


def validate_range_paired(command: str, start: object, end: object) -> None:
    """字节区间参数成对校验（bitcount/bitpos：契约要求给就成对）。"""
    if (start is None) != (end is None):
        raise RedisCommandError(
            f"{command} 的 start/end 须成对给出（当前 start={start!r}, end={end!r}）",
            command=command,
        )


def validate_hset_args(
    mapping: dict | None, field: object, value: object
) -> None:
    """HSET 入参二选一校验（mapping 与 field/value 互斥，均空报错）。

    统一在入队/调用期抛 RedisCommandError——否则 redis-py 会在自身边界抛
    DataError，泄漏原生异常（契约总则 #4）。
    """
    has_mapping = mapping is not None and len(mapping) > 0
    has_pair = field is not None and value is not None
    if has_mapping and has_pair:
        raise RedisCommandError(
            "hset 的 mapping 与 field/value 只能二选一", command="hset"
        )
    if not has_mapping and not has_pair:
        raise RedisCommandError(
            "hset 需要 mapping 或 field/value（不可同时为空）", command="hset"
        )


def validate_set_ttl(duration: Duration | None, keep_ttl: bool) -> None:
    """SET 的 duration 与 keep_ttl 互斥校验（契约：同给抛 RedisCommandError）。"""
    if duration is not None and keep_ttl:
        raise RedisCommandError(
            "set 的 duration 与 keep_ttl 互斥，只能设置其一", command="set"
        )
