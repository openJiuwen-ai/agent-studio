# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""blpop/brpop 单键字符串守卫单测：裸 str 不得被 list() 拆成单字符键列表。

对照 redis_native.capabilities.blocking 的同款守卫（注释明示该失败模式：
消费方将永远阻塞在错误的单字符键上）。
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import Duration

from redis_demo_provider.client import AcmeDemoClient


def test_blpop_bare_string_kept_as_single_key():
    """blpop("demo:q") 必须以 ["demo:q"] 传入底层，而不是 ['d','e','m',...]。"""
    fake_redis = AsyncMock()
    client = AcmeDemoClient(fake_redis)

    asyncio.run(client.blpop("demo:q", Duration.seconds(1)))

    args, _ = fake_redis.blpop.await_args
    assert list(args[0]) == ["demo:q"]


def test_brpop_bare_string_kept_as_single_key():
    """brpop("demo:q") 同守卫。"""
    fake_redis = AsyncMock()
    client = AcmeDemoClient(fake_redis)

    asyncio.run(client.brpop("demo:q", Duration.seconds(1)))

    args, _ = fake_redis.brpop.await_args
    assert list(args[0]) == ["demo:q"]


def test_blpop_list_input_passed_through():
    """列表输入保持原样，守卫不引入额外包装。"""
    fake_redis = AsyncMock()
    client = AcmeDemoClient(fake_redis)

    asyncio.run(client.blpop(["demo:a", "demo:b"], Duration.seconds(1)))

    args, _ = fake_redis.blpop.await_args
    assert list(args[0]) == ["demo:a", "demo:b"]


def test_blpop_empty_string_fails_fast():
    """空串在单键包装前先被空输入校验拦截（不得包成 [""] 绕过校验后无限阻塞）。"""
    fake_redis = AsyncMock()
    client = AcmeDemoClient(fake_redis)

    with pytest.raises(RedisCommandError):
        asyncio.run(client.blpop("", Duration.seconds(1)))

    fake_redis.blpop.assert_not_awaited()


def test_brpop_empty_string_fails_fast():
    """brpop 空串同守卫顺序。"""
    fake_redis = AsyncMock()
    client = AcmeDemoClient(fake_redis)

    with pytest.raises(RedisCommandError):
        asyncio.run(client.brpop("", Duration.seconds(1)))

    fake_redis.brpop.assert_not_awaited()
