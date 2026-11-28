# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""NativeBlockingCapability blpop/brpop 空键 fail-fast 单测。

与 demo provider 已合入的守卫（!2566）对齐：空输入校验必须先于单键包装——
否则空串被包成 [""] 绕过 `if not keys` 校验后下发到空键上，消费方无限阻塞
（与本套件要防的单字符拆键失败模式同类）。
"""

import asyncio

import pytest
from redis_spi.exceptions import RedisCommandError

from redis_native.capabilities.blocking import NativeBlockingCapability
from redis_native_test_fakes import FakeRedisClient


def test_blpop_empty_string_fails_fast():
    fake = FakeRedisClient()
    with pytest.raises(RedisCommandError):
        asyncio.run(NativeBlockingCapability(fake).blpop(""))
    assert fake.calls == []  # 不得把 [""] 下发到底层


def test_brpop_empty_string_fails_fast():
    fake = FakeRedisClient()
    with pytest.raises(RedisCommandError):
        asyncio.run(NativeBlockingCapability(fake).brpop(""))
    assert fake.calls == []  # 不得把 [""] 下发到底层


def test_blpop_bare_string_still_wraps_single_key():
    """既有单键包装语义不回归：非空裸串仍按 ["k"] 下发。"""
    fake = FakeRedisClient(results={"blpop": ("k", b"v")})
    assert asyncio.run(NativeBlockingCapability(fake).blpop("queue:1")) == ("k", b"v")
    assert fake.calls == [("blpop", (["queue:1"], 0.0), {})]
