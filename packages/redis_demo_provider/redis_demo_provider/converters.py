# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Acme demo：SPI 值对象 → fakeredis（redis-py 兼容）调用参数换算。

企业实现参考：这是"你的 SDK 参数风格"与 SPI 契约之间的适配层——demo 的
SDK 是 redis-py 兼容（fakeredis），TTL 走 px 毫秒保持精度、条件走 nx/xx。
"""

from __future__ import annotations

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import Duration, SetCondition


def duration_to_seconds(duration: Duration) -> int:
    """Duration → 秒（向上取整；秒级命令语义，正毫秒至少 1 秒）。"""
    return -(-duration.milliseconds // 1000)


def set_options(
    *,
    condition: SetCondition | None,
    duration: Duration | None,
    keep_ttl: bool,
) -> dict:
    """SPI set 条件参数 → redis-py set kwargs（TTL 走 px 毫秒保精度）。"""
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


def blocking_timeout(timeout: Duration | None) -> int:
    """阻塞命令超时：Duration → 整数秒（真实 Redis 拒绝非整数）；None → 0（无限阻塞）。"""
    if timeout is None:
        return 0
    return -(-timeout.milliseconds // 1000)


def validate_hset_args(mapping: dict | None, field: object, value: object) -> None:
    """HSET 入参二选一校验（入队/调用期 fail-fast，防底层 DataError 泄漏）。"""
    has_mapping = mapping is not None and len(mapping) > 0
    has_pair = field is not None and value is not None
    if has_mapping and has_pair:
        raise RedisCommandError("hset 的 mapping 与 field/value 只能二选一", command="hset")
    if not has_mapping and not has_pair:
        raise RedisCommandError(
            "hset 需要 mapping 或 field/value（不可同时为空）", command="hset"
        )


def validate_set_ttl(duration: Duration | None, keep_ttl: bool) -> None:
    """SET 的 duration 与 keep_ttl 互斥校验。"""
    if duration is not None and keep_ttl:
        raise RedisCommandError(
            "set 的 duration 与 keep_ttl 互斥，只能设置其一", command="set"
        )
