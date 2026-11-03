# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""ScriptingCapability 实现（Lua EVAL 族）。

redis-py 8.x 签名：``eval(script, numkeys, *keys_and_args)``——SPI 的
``keys``/``args`` 序列展开后拼接；SCRIPT LOAD/EXISTS **无响应回调**，
bytes 模式与 0/1 int 须自行归一（契约：str sha / bool 列表）。
"""

from __future__ import annotations

from typing import Any, Sequence

import redis.exceptions as redis_exc

from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisScriptError
from redis_spi.types import Key, Value


class NativeScriptingCapability:
    """脚本能力组（redis-py 委托）。"""

    def __init__(self, redis) -> None:
        self._redis = redis

    @spi_command("eval")
    async def eval(
        self,
        script: str,
        keys: Sequence[Key],
        args: Sequence[Value] = (),
    ) -> Any:
        # eval 语境下的任何 ResponseError（含脚本内 redis.call 报错与 NOSCRIPT）
        # 均为脚本执行失败——按契约抛 RedisScriptError（而非通用 CommandError）。
        try:
            return await self._redis.eval(script, len(keys), *keys, *args)
        except redis_exc.ResponseError as exc:
            raise RedisScriptError(
                f"eval failed: {exc}", command="eval", detail=str(exc)
            ) from exc

    @spi_command("evalsha")
    async def evalsha(
        self,
        sha1: str,
        keys: Sequence[Key],
        args: Sequence[Value] = (),
    ) -> Any:
        # 同 eval：未缓存（NOSCRIPT）与脚本运行期错误统一 RedisScriptError。
        try:
            return await self._redis.evalsha(sha1, len(keys), *keys, *args)
        except redis_exc.ResponseError as exc:
            raise RedisScriptError(
                f"evalsha failed: {exc}", command="evalsha", detail=str(exc)
            ) from exc

    @spi_command("script_load")
    async def script_load(self, script: str) -> str:
        sha = await self._redis.script_load(script)
        if isinstance(sha, bytes):
            # sha1 为 16 进制 ASCII（服务端保证），bytes 模式下需解码为 str。
            return sha.decode("ascii")
        return sha

    @spi_command("script_exists")
    async def script_exists(self, *sha1: str) -> list[bool]:
        result = await self._redis.script_exists(*sha1)
        # 无响应回调：RESP2 返回 0/1 int，契约要求 bool 列表。
        return [bool(item) for item in result]
