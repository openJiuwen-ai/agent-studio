# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""exceptions.py 异常体系契约测试。"""

from redis_spi.exceptions import (
    REDIS_ERROR_CODE_BASE,
    CapabilityNotSupportedError,
    RedisAuthFailureError,
    RedisClusterError,
    RedisCommandError,
    RedisConfigError,
    RedisConnectionError,
    RedisError,
    RedisScriptError,
    RedisTimeoutError,
    RedisWrongTypeError,
)

ALL_EXCEPTIONS = [
    RedisError,
    RedisConfigError,
    RedisConnectionError,
    RedisAuthFailureError,
    RedisTimeoutError,
    RedisCommandError,
    RedisWrongTypeError,
    CapabilityNotSupportedError,
    RedisScriptError,
    RedisClusterError,
]


class TestHierarchy:
    @staticmethod
    def test_all_within_error_code_segment():
        # Q7：260000 段内
        assert all(260000 <= exc.code < 261000 for exc in ALL_EXCEPTIONS)

    @staticmethod
    def test_codes_unique():
        codes = [exc.code for exc in ALL_EXCEPTIONS]
        assert len(codes) == len(set(codes))

    @staticmethod
    def test_expected_code_values():
        assert RedisConfigError.code == 260001
        assert RedisConnectionError.code == 260002
        assert RedisAuthFailureError.code == 260003
        assert RedisTimeoutError.code == 260004
        assert RedisCommandError.code == 260005
        assert RedisWrongTypeError.code == 260006
        assert CapabilityNotSupportedError.code == 260007
        assert RedisScriptError.code == 260008
        assert RedisClusterError.code == 260009
        assert REDIS_ERROR_CODE_BASE == 260000

    @staticmethod
    def test_subclass_relationships():
        # 审计区分：AuthFailure 归连接类
        assert issubclass(RedisAuthFailureError, RedisConnectionError)
        # WRONGTYPE / 脚本错误归命令类
        assert issubclass(RedisWrongTypeError, RedisCommandError)
        assert issubclass(RedisScriptError, RedisCommandError)
        # 全部归根
        assert all(issubclass(exc, RedisError) for exc in ALL_EXCEPTIONS)


class TestContextFields:
    @staticmethod
    def test_str_contains_code_operation_key():
        error = RedisCommandError(
            "wrong args", command="SET", redis_key="k1", operation="session_save"
        )
        text = str(error)
        assert "260005" in text
        assert "operation=session_save" in text
        assert "key=k1" in text

    @staticmethod
    def test_timeout_result_known_default():
        assert RedisTimeoutError("t").result_known is True

    @staticmethod
    def test_timeout_result_unknown_marks_non_idempotent():
        # nos Counter 提醒：写超时结果未知，禁止盲重试
        error = RedisTimeoutError("incr timed out", result_known=False)
        assert error.result_known is False

    @staticmethod
    def test_capability_context():
        error = CapabilityNotSupportedError("no geo", capability="GeoCapability")
        assert error.capability == "GeoCapability"

    @staticmethod
    def test_command_and_detail():
        error = RedisScriptError("lua failed", command="eval", detail="attempt to index nil")
        assert error.command == "eval"
        assert error.detail == "attempt to index nil"
