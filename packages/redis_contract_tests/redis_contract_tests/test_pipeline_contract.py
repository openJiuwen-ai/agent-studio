# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Pipeline 契约：入队/执行语义、事务差异、入队期校验 fail-fast、部分失败行为。

口径（protocols.Pipeline，与 Redis MULTI/EXEC 真实语义对齐）：
  - execute 结果与入队顺序一一对应；
  - transaction=True：EXEC 期间不与其他客户端交错（原子执行）；运行期单命令
    错误不回滚此前命令（Redis 事务无回滚）；
  - transaction=False：批量发送非原子，逐条执行；
  - 参数校验在**入队期** fail-fast（不等 execute）。
"""

from redis_spi.exceptions import RedisCommandError, RedisWrongTypeError
from redis_spi.types import Duration

from redis_contract_tests.test_core_contract import run


class TestPipelineContract:
    @staticmethod
    def test_execute_returns_results_in_queue_order(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}pipe"
            pipe = provider_client.pipeline(transaction=False)
            pipe.set(key, b"v1")
            pipe.get(key)
            pipe.exists(key)
            pipe.rpush(f"{key}-list", b"a", b"b")
            pipe.lrange(f"{key}-list", 0, -1)
            pipe.sadd(f"{key}-set", b"m")
            pipe.hset(f"{key}-hash", field=b"f", value=b"1")
            pipe.hget(f"{key}-hash", b"f")
            pipe.delete(f"{key}-hash")
            results = await pipe.execute()
            await pipe.aclose()
            assert results == [
                True,            # set（redis-py 原生 True；SPI set 的 b"OK" 归一仅在客户端方法面）
                b"v1",           # get
                1,               # exists
                2,               # rpush
                [b"a", b"b"],    # lrange
                1,               # sadd
                1,               # hset
                b"1",            # hget
                1,               # delete
            ]

        run(loop, scenario())

    @staticmethod
    def test_transaction_modes_same_final_state_on_success(provider_client, key_prefix, loop):
        async def scenario():
            for transaction in (True, False):
                base = f"{key_prefix}tx-{transaction}"
                pipe = provider_client.pipeline(transaction=transaction)
                pipe.set(f"{base}-a", b"1")
                pipe.set(f"{base}-b", b"2")
                pipe.delete(f"{base}-a")
                await pipe.execute()
                await pipe.aclose()
                assert await provider_client.get(f"{base}-a") is None
                assert await provider_client.get(f"{base}-b") == b"2"

        run(loop, scenario())

    @staticmethod
    def test_runtime_error_raises_translated_and_keeps_prior_commands(provider_client, key_prefix, loop):
        async def scenario():
            # 事务与批量的运行期错误口径一致：execute 抛翻译后异常，
            # 此前命令已生效（Redis 事务无回滚——protocols.Pipeline 契约明示）。
            for transaction in (True, False):
                base = f"{key_prefix}perr-{transaction}"
                await provider_client.set(f"{base}-str", b"v")  # string key
                pipe = provider_client.pipeline(transaction=transaction)
                pipe.set(f"{base}-ok", b"applied")
                pipe.hgetall(f"{base}-str")  # WRONGTYPE：运行期错误
                try:
                    await pipe.execute()
                except RedisWrongTypeError:
                    pass
                else:
                    raise AssertionError(
                        f"transaction={transaction}: expected RedisWrongTypeError from execute()"
                    )
                finally:
                    await pipe.aclose()
                assert await provider_client.get(f"{base}-ok") == b"applied"

        run(loop, scenario())

    @staticmethod
    def test_enqueue_time_validation_fail_fast(provider_client, key_prefix, loop):
        async def scenario():
            pipe = provider_client.pipeline(transaction=False)
            # hset 两形态同给 / 均空：入队期即抛（不进 execute）
            for kwargs in (
                {"mapping": {b"f": b"v"}, "field": b"f", "value": b"v"},
                {},
            ):
                try:
                    pipe.hset(f"{key_prefix}bad", **kwargs)
                except RedisCommandError:
                    pass
                else:
                    raise AssertionError("hset 入参校验应在入队期 fail-fast")
            # set 的 duration 与 keep_ttl 互斥：入队期抛
            try:
                pipe.set(
                    f"{key_prefix}bad",
                    b"v",
                    duration=Duration.seconds(10),
                    keep_ttl=True,
                )
            except RedisCommandError:
                pass
            else:
                raise AssertionError("set duration/keep_ttl 互斥应在入队期 fail-fast")
            await pipe.aclose()

        run(loop, scenario())

    @staticmethod
    def test_expire_then_ttl_executes_in_order(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}pttl"
            await provider_client.set(key, b"v")
            pipe = provider_client.pipeline(transaction=True)
            pipe.expire(key, Duration.seconds(100))
            pipe.get(key)
            results = await pipe.execute()
            await pipe.aclose()
            # 入队顺序即执行顺序：expire 先于 get；批内无 TTL 查询则用批后查询
            assert results[0] is True
            assert results[1] == b"v"
            assert 0 < await provider_client.ttl(key) <= 100 + 2

        run(loop, scenario())

    @staticmethod
    def test_scan_in_pipeline_returns_batch_tuple(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}pscan"
            await provider_client.set(key, b"v")
            pipe = provider_client.pipeline(transaction=False)
            pipe.scan(0, match=f"{key_prefix}pscan".encode(), count=100)
            results = await pipe.execute()
            await pipe.aclose()
            cursor, items = results[0]
            # 单批形态契约：(cursor, keys) 元组；键在本批或遍历未结束
            # （cursor 值是服务端分页选择，单批不承诺完备——循环语义由核心面用例覆盖）
            assert isinstance(cursor, int) and cursor >= 0
            assert key.encode() in items or cursor != 0

        run(loop, scenario())
