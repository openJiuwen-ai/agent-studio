# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""_pop（lpop/rpop 共用实现）与真实 Redis 语义对齐单测。

覆盖两处背离：
1. rpop count=0：[-0:] 切片会返回整个剩余列表（反转）且不删除，而 lpop
   半边 [:0] 正确返回 []——真实 Redis RPOP key 0 返回空数组且无副作用。
2. 单值 pop 弹空列表后不删 key：exists→1 / type→list / scan 可见，真实
   Redis 列表清空即删 key（exists→0 / type→none）。
"""

import asyncio

import pytest

try:
    from redis_contract_tests.stubs.redis_py_stub import InMemoryRedisPyStub
except ImportError:
    # 包本体仅依赖 redis-spi（零 redis-py）：企业自研 Provider 未安装 redis-py 的
    # 环境下整文件跳过，保证 pytest --pyargs redis_contract_tests 收集不炸
    pytest.skip("redis-py not installed; stub tests skipped", allow_module_level=True)


def test_rpop_count_zero_returns_empty_and_keeps_list():
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.rpush("k", "a", "b"))
    assert asyncio.run(stub.rpop("k", 0)) == []
    # 无副作用：列表原样保留
    assert asyncio.run(stub.lrange("k", 0, -1)) == [b"a", b"b"]


def test_lpop_count_zero_returns_empty():
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.rpush("k", "a"))
    assert asyncio.run(stub.lpop("k", 0)) == []


def test_single_lpop_empties_list_deletes_key():
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.rpush("k", "a"))
    assert asyncio.run(stub.lpop("k")) == b"a"
    assert asyncio.run(stub.exists("k")) == 0
    assert asyncio.run(stub.type("k")) == b"none"


def test_single_rpop_empties_list_deletes_key():
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.rpush("k", "a"))
    assert asyncio.run(stub.rpop("k")) == b"a"
    assert asyncio.run(stub.exists("k")) == 0
    assert asyncio.run(stub.type("k")) == b"none"


def test_single_pop_on_multi_element_keeps_key():
    """非弹空路径不受影响：弹一个还剩一个，key 存活。"""
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.rpush("k", "a", "b"))
    assert asyncio.run(stub.lpop("k")) == b"a"
    assert asyncio.run(stub.exists("k")) == 1
    assert asyncio.run(stub.type("k")) == b"list"
