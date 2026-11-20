# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""as_native_client 单测：duck-typed 过渡视图（Q3；Phase 4 移除）。"""

from __future__ import annotations

import pytest

from redis_native.client import NativeRedisClient
from redis_native.compat import as_native_client

from redis_spi.exceptions import RedisConfigError

from redis_native_test_fakes import FakeRedisClient


class _WithNativeView:
    @staticmethod
    def native_client():
        return "raw-view"


class _Plain:
    pass


class _NonCallable:
    native_client = "not-a-method"


class TestAsNativeClient:
    @staticmethod
    def test_duck_typed_getter_used():
        assert as_native_client(_WithNativeView()) == "raw-view"

    @staticmethod
    def test_native_client_integration():
        fake = FakeRedisClient()
        client = NativeRedisClient(fake)
        assert as_native_client(client) is fake

    @staticmethod
    def test_plain_object_rejected():
        with pytest.raises(RedisConfigError, match="_Plain"):
            as_native_client(_Plain())

    @staticmethod
    def test_non_callable_attr_rejected():
        with pytest.raises(RedisConfigError, match="_NonCallable"):
            as_native_client(_NonCallable())

    @staticmethod
    def test_error_mentions_transition_scope():
        # 自描述：仅 native provider 支持 + 过渡期 API（引导 Phase 4 收口）
        with pytest.raises(RedisConfigError, match="native provider"):
            as_native_client(_Plain())
