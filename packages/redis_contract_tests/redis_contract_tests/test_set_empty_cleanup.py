# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""set 命令空容器清理单测：集合被弹空/移空后应删 key。

真实 Redis：集合最后一个成员被移除后 key 自动删除（exists→0/type→none）。
替身中 srem(:698)/spop count 分支(:729)/ltrim 等同族路径均已做
`if not container: self._delete_key(...)` 清理，spop 单值分支与 smove 遗漏。
"""

import asyncio

from redis_contract_tests.stubs.redis_py_stub import InMemoryRedisPyStub


def test_spop_single_last_member_deletes_key():
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.sadd("s", "m"))
    assert asyncio.run(stub.spop("s")) == b"m"
    assert asyncio.run(stub.exists("s")) == 0
    assert asyncio.run(stub.type("s")) == b"none"


def test_spop_single_on_multi_member_keeps_key():
    """非弹空路径不受影响。"""
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.sadd("s", "m1", "m2"))
    member = asyncio.run(stub.spop("s"))
    assert member in (b"m1", b"m2")
    assert asyncio.run(stub.exists("s")) == 1
    assert asyncio.run(stub.type("s")) == b"set"


def test_smove_empties_source_deletes_source_key():
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.sadd("src", "m"))
    assert asyncio.run(stub.smove("src", "dst", "m")) is True
    assert asyncio.run(stub.exists("src")) == 0
    assert asyncio.run(stub.type("src")) == b"none"
    # 目的地集合正常接收成员
    assert asyncio.run(stub.sismember("dst", "m")) == 1


def test_smove_non_empty_source_keeps_key():
    """源集合仍有成员时不删 key。"""
    stub = InMemoryRedisPyStub()
    asyncio.run(stub.sadd("src", "m1", "m2"))
    assert asyncio.run(stub.smove("src", "dst", "m1")) is True
    assert asyncio.run(stub.exists("src")) == 1
    assert asyncio.run(stub.sismember("src", "m2")) == 1
