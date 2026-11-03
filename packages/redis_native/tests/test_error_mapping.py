# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""error_mapping 单测：异常映射表全分支 + @spi_command 装饰器行为。

映射正确性依据 redis-py 8.x 异常继承链（本文件用**精确类型断言**，避免
子类关系让判定顺序错误侥幸通过——AuthenticationError ⊂ ConnectionError、
ClusterDownError ⊂ ClusterError+ResponseError 是顺序敏感点）。
"""

from __future__ import annotations

import asyncio

import pytest
import redis.exceptions as redis_exc

from redis_native.error_mapping import spi_command, translate_error

from redis_spi.exceptions import (
    RedisAuthFailureError,
    RedisClusterError,
    RedisCommandError,
    RedisConnectionError,
    RedisScriptError,
    RedisTimeoutError,
    RedisWrongTypeError,
)


class TestTranslateError:
    @pytest.mark.parametrize(
        ("exc", "expected"),
        [
            # 认证先于连接（AuthenticationError ⊂ ConnectionError）
            (redis_exc.AuthenticationError("bad password"), RedisAuthFailureError),
            (redis_exc.AuthorizationError("no perms"), RedisAuthFailureError),
            (redis_exc.NoPermissionError("denied"), RedisAuthFailureError),
            (redis_exc.TimeoutError("t/o"), RedisTimeoutError),
            # 集群先于 ResponseError 兜底（ClusterDownError 双继承）
            (redis_exc.ClusterDownError("down"), RedisClusterError),
            (redis_exc.ClusterError("cluster"), RedisClusterError),
            (redis_exc.RedisClusterException("cluster exc"), RedisClusterError),
            # AskError/MovedError 构造期解析 "slot host:port"（须给合法形态）
            (redis_exc.AskError("3999 127.0.0.1:6381"), RedisClusterError),
            (redis_exc.TryAgainError("try again"), RedisClusterError),
            (redis_exc.ClusterCrossSlotError("crossslot"), RedisClusterError),
            (redis_exc.MovedError("3999 127.0.0.1:6381"), RedisClusterError),
            (redis_exc.NoScriptError("NOSCRIPT"), RedisScriptError),
            (redis_exc.ResponseError("WRONGTYPE against key"), RedisWrongTypeError),
            (redis_exc.ResponseError("ERR unknown command"), RedisCommandError),
            (redis_exc.ConnectionError("refused"), RedisConnectionError),
            (redis_exc.DataError("bad args"), RedisCommandError),
            (redis_exc.WatchError("watch"), RedisCommandError),
        ],
    )
    def test_mapping_table(self, exc, expected):
        err = translate_error(exc, operation="op")
        # 精确类型：子类断言会让判定顺序错误侥幸通过。
        assert err.__class__ is expected
        assert err.operation == "op"
        assert err.__cause__ is None  # translate 只构造，raise 由调用方挂 cause
        assert exc.__class__.__name__ in err.message

    @staticmethod
    def test_wrongtype_requires_upper_prefix():
        # WRONGTYPE 判定大小写不敏感且是前缀匹配
        err = translate_error(
            redis_exc.ResponseError("wrongtype skey"), operation="hget"
        )
        # 精确类型断言（G.TYP.08 有意豁免）：子类断言会让判定顺序错误侥幸通过
        assert err.__class__ is RedisWrongTypeError

    @staticmethod
    def test_redis_key_context_carried():
        err = translate_error(
            redis_exc.ConnectionError("refused"), operation="get", redis_key="k1"
        )
        assert err.redis_key == "k1"

    @staticmethod
    def test_timeout_result_known_default_true():
        err = translate_error(redis_exc.TimeoutError("t"), operation="get")
        assert err.result_known is True

    @staticmethod
    def test_timeout_result_known_false():
        err = translate_error(
            redis_exc.TimeoutError("t"), operation="incr", result_known=False
        )
        assert err.result_known is False


class _Probe:
    """被测宿主：@spi_command 装饰行为探针。"""

    @spi_command("incr", timeout_result_known=False)
    async def incr_unknown(self, key):
        raise redis_exc.TimeoutError("t/o")

    @spi_command("get", timeout_result_known=True)
    async def get_known(self, key):
        raise redis_exc.TimeoutError("t/o")

    @spi_command("set")
    async def set_raises_native(self, key, value):
        raise ValueError("programmer bug")

    @spi_command("hset")
    async def set_raises_spi(self, key, mapping):
        raise RedisCommandError("spi validation", command="hset")

    @spi_command("set")
    async def ok(self, key, value):
        return "result"


class TestSpiCommand:
    @staticmethod
    def test_timeout_result_unknown_annotated():
        with pytest.raises(RedisTimeoutError) as excinfo:
            asyncio.run(_Probe().incr_unknown("counter:1"))
        assert excinfo.value.result_known is False
        assert excinfo.value.operation == "incr"
        assert excinfo.value.redis_key == "counter:1"
        assert isinstance(excinfo.value.__cause__, redis_exc.TimeoutError)

    @staticmethod
    def test_timeout_result_known_default():
        with pytest.raises(RedisTimeoutError) as excinfo:
            asyncio.run(_Probe().get_known("k"))
        assert excinfo.value.result_known is True

    @staticmethod
    def test_non_redis_exception_passthrough():
        # 编程错误不吞不裹
        with pytest.raises(ValueError, match="programmer bug"):
            asyncio.run(_Probe().set_raises_native("k", b"v"))

    @staticmethod
    def test_spi_exception_passthrough():
        # 本层（前置校验）的 redis_spi 异常原样透传，不被二次包装
        with pytest.raises(RedisCommandError, match="spi validation"):
            asyncio.run(_Probe().set_raises_spi("k", {"f": b"v"}))

    @staticmethod
    def test_result_passthrough():
        assert asyncio.run(_Probe().ok("k", b"v")) == "result"


class TestContextKey:
    """redis_key 提取（经装饰器间接验证）。"""

    @spi_command("op")
    async def boom(self, *args):
        raise redis_exc.ConnectionError("x")

    def test_bytes_key_decoded(self):
        with pytest.raises(RedisConnectionError) as excinfo:
            asyncio.run(self.boom(b"cache:\xe4\xb8\xad"))
        assert excinfo.value.redis_key == "cache:中"

    def test_long_key_truncated(self):
        long_key = "k" * 300
        with pytest.raises(RedisConnectionError) as excinfo:
            asyncio.run(self.boom(long_key))
        assert len(excinfo.value.redis_key) == 128

    def test_non_string_first_args_yield_no_key(self):
        # 首个位置参为 int 时继续找后续 str/bytes
        with pytest.raises(RedisConnectionError) as excinfo:
            asyncio.run(self.boom(5, "second"))
        assert excinfo.value.redis_key == "second"
