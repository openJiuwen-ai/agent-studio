# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""能力组契约：按 Provider 声明的能力矩阵跑批（设计文档 §七）。

口径：
  - 每组先 ``supports()`` 探测——未声明组自动 skip（"实现多少声明多少"的
    可测试承诺：声明的组必须通过，未声明的组无需实现）；
  - 脚本组额外探测 Lua 引擎可用性：fakeredis 未安装 lua 扩展时后端虽声明
    脚本能力但引擎不支持 EVAL——skip 而非误报（真实实例后端不受影响）。
"""

import asyncio

import pytest

from redis_spi.capabilities import (
    BitmapCapability,
    BlockingCommands,
    CounterCapability,
    GeoCapability,
    HyperLogLogCapability,
    PubSubCapability,
    ScriptingCapability,
    SortedSetCapability,
)
from redis_spi.exceptions import RedisCommandError, RedisError, RedisScriptError
from redis_spi.types import (
    SCAN_START,
    Duration,
    GeoMember,
    GeoUnit,
    SetCondition,
)

from redis_contract_tests.test_core_contract import run


def require(provider_client, capability):
    """声明探测：未声明组 skip；声明组返回能力视图。"""
    if not provider_client.supports(capability):
        pytest.skip(f"target 未声明 {capability.__name__}")
    return provider_client.as_capability(capability)


class TestCounterCapability:
    @staticmethod
    def test_incr_decr_and_float(provider_client, key_prefix, loop):
        async def scenario():
            counter = require(provider_client, CounterCapability)
            key = f"{key_prefix}ctr"
            assert await counter.incr(key) == 1
            assert await counter.incr(key, 5) == 6
            assert await counter.decr(key, 2) == 4
            assert await counter.decr(key) == 3
            fkey = f"{key_prefix}fctr"
            result = await counter.incr_by_float(fkey, 1.5)
            assert abs(result - 1.5) < 1e-9

        run(loop, scenario())

    @staticmethod
    def test_incr_non_integer_rejected(provider_client, key_prefix, loop):
        async def scenario():
            counter = require(provider_client, CounterCapability)
            key = f"{key_prefix}ctr-bad"
            await provider_client.set(key, b"not-a-number")
            with pytest.raises(RedisCommandError):
                await counter.incr(key)

        run(loop, scenario())


class TestSortedSetCapability:
    @staticmethod
    def test_zadd_zscore_zcard_zrank(provider_client, key_prefix, loop):
        async def scenario():
            zset = require(provider_client, SortedSetCapability)
            key = f"{key_prefix}z"
            assert await zset.zadd(key, {b"a": 1.0, b"b": 2.0, b"c": 3.0}) == 3
            assert await zset.zcard(key) == 3
            assert await zset.zscore(key, b"b") == 2.0
            assert await zset.zscore(key, b"missing") is None
            assert await zset.zrank(key, b"a") == 0
            assert await zset.zrevrank(key, b"a") == 2
            assert await zset.zrank(key, b"missing") is None
            assert await zset.zrem(key, b"a", b"missing") == 1
            assert await zset.zcard(key) == 2

        run(loop, scenario())

    @staticmethod
    def test_zadd_condition(provider_client, key_prefix, loop):
        async def scenario():
            zset = require(provider_client, SortedSetCapability)
            key = f"{key_prefix}zcond"
            await zset.zadd(key, {b"a": 1.0})
            # NX：已存在跳过
            assert await zset.zadd(key, {b"a": 9.0}, condition=SetCondition.NX) == 0
            assert await zset.zscore(key, b"a") == 1.0
            # XX：只更新已存在
            assert await zset.zadd(key, {b"a": 2.0, b"new": 5.0}, condition=SetCondition.XX) == 0
            assert await zset.zscore(key, b"a") == 2.0
            assert await zset.zscore(key, b"new") is None

        run(loop, scenario())

    @staticmethod
    def test_zincrby_zcount_zrange(provider_client, key_prefix, loop):
        async def scenario():
            zset = require(provider_client, SortedSetCapability)
            key = f"{key_prefix}zrange"
            await zset.zadd(key, {b"a": 1.0, b"b": 2.0, b"c": 3.0})
            assert await zset.zincrby(key, 10.0, b"a") == 11.0
            assert await zset.zcount(key, 2, 11) == 3
            assert await zset.zrange(key, 0, -1) == [b"b", b"c", b"a"]
            assert await zset.zrange(key, 0, -1, desc=True) == [b"a", b"c", b"b"]
            with_scores = await zset.zrange(key, 0, -1, withscores=True)
            assert [member for member, _ in with_scores] == [b"b", b"c", b"a"]
            assert [score for _, score in with_scores] == [2.0, 3.0, 11.0]

        run(loop, scenario())

    @staticmethod
    def test_zrangebyscore_and_bylex(provider_client, key_prefix, loop):
        async def scenario():
            zset = require(provider_client, SortedSetCapability)
            key = f"{key_prefix}zbs"
            await zset.zadd(key, {b"a": 1.0, b"b": 2.0, b"c": 3.0, b"d": 4.0})
            assert await zset.zrangebyscore(key, 2, 3) == [b"b", b"c"]
            # 开区间 "(3"
            assert await zset.zrangebyscore(key, 2, "(3") == [b"b"]
            # 分页
            assert await zset.zrangebyscore(key, "-inf", "+inf", offset=1, limit=2) == [b"b", b"c"]
            # 字典序（同 score 前提）
            lex = f"{key_prefix}zlex"
            await zset.zadd(lex, {b"a": 0.0, b"b": 0.0, b"c": 0.0, b"d": 0.0})
            assert await zset.zrangebylex(lex, "[b", "[c") == [b"b", b"c"]
            assert await zset.zrangebylex(lex, "[b", "(c") == [b"b"]
            assert await zset.zlexcount(lex, "[a", "(d") == 3

        run(loop, scenario())

    @staticmethod
    def test_zremrange_and_stores(provider_client, key_prefix, loop):
        async def scenario():
            zset = require(provider_client, SortedSetCapability)
            key = f"{key_prefix}zrem"
            await zset.zadd(key, {b"a": 1.0, b"b": 2.0, b"c": 3.0, b"d": 4.0})
            assert await zset.zremrangebyrank(key, 0, 1) == 2
            assert await zset.zrange(key, 0, -1) == [b"c", b"d"]
            assert await zset.zremrangebyscore(key, 4, 4) == 1
            # 并集/交集 + 聚合策略
            k1, k2, dst = f"{key_prefix}u1", f"{key_prefix}u2", f"{key_prefix}udst"
            await zset.zadd(k1, {b"a": 1.0, b"b": 2.0})
            await zset.zadd(k2, {b"a": 2.0, b"c": 3.0})
            assert await zset.zunionstore(dst, [k1, k2]) == 3
            assert await zset.zscore(dst, b"a") == 3.0  # SUM 默认
            assert await zset.zunionstore(dst, [k1, k2], aggregate="MIN") == 3
            assert await zset.zscore(dst, b"a") == 1.0
            assert await zset.zinterstore(dst, [k1, k2]) == 1
            assert await zset.zscore(dst, b"a") == 3.0

        run(loop, scenario())

    @staticmethod
    def test_zscan_loops_to_start_cursor(provider_client, key_prefix, loop):
        async def scenario():
            zset = require(provider_client, SortedSetCapability)
            key = f"{key_prefix}zscan"
            mapping = {f"m{i}".encode(): float(i) for i in range(5)}
            await zset.zadd(key, mapping)
            collected: dict = {}
            cursor = SCAN_START
            for _ in range(100):
                next_cursor, pairs = await zset.zscan(key, cursor, count=2)
                for member, score in pairs:
                    collected[member] = score
                cursor = next_cursor
                if cursor == SCAN_START:
                    break
            assert cursor == SCAN_START
            assert collected == mapping

        run(loop, scenario())


class TestBitmapCapability:
    @staticmethod
    def test_bit_operations(provider_client, key_prefix, loop):
        async def scenario():
            bitmap = require(provider_client, BitmapCapability)
            key = f"{key_prefix}bm"
            assert await bitmap.setbit(key, 0, 1) == 0
            assert await bitmap.setbit(key, 1, 1) == 0
            assert await bitmap.setbit(key, 1, 1) == 1  # 原位值
            assert await bitmap.getbit(key, 0) == 1
            assert await bitmap.getbit(key, 99) == 0
            assert await bitmap.bitcount(key) == 2
            # 字节区间统计（成对）
            assert await bitmap.bitcount(key, 0, 0) == 2
            assert await bitmap.bitpos(key, 0) == 2  # 首个 0 位
            # 位运算
            other, dst = f"{key_prefix}bm2", f"{key_prefix}bmdst"
            await bitmap.setbit(other, 2, 1)
            assert await bitmap.bitop("AND", dst, key, other) == 1
            assert await bitmap.bitcount(dst) == 0
            assert await bitmap.bitop("OR", dst, key, other) == 1
            assert await bitmap.bitcount(dst) == 3
            assert await bitmap.bitop("NOT", dst, key) == 1
            assert await bitmap.bitcount(dst) == 6  # 1 字节 8 位 - 2 个 1

        run(loop, scenario())


class TestHyperLogLogCapability:
    @staticmethod
    def test_pf_family(provider_client, key_prefix, loop):
        async def scenario():
            hll = require(provider_client, HyperLogLogCapability)
            key = f"{key_prefix}hll"
            assert await hll.pfadd(key, b"a", b"b", b"c") == 1
            assert await hll.pfadd(key, b"a") == 0  # 基数无变化
            # 小基数下估计通常精确；容差 ±1 防实现差异
            count = await hll.pfcount(key)
            assert 2 <= count <= 4
            other, merged = f"{key_prefix}hll2", f"{key_prefix}hllm"
            await hll.pfadd(other, b"d", b"e")
            assert await hll.pfmerge(merged, key, other) is True
            total = await hll.pfcount(merged)
            assert 4 <= total <= 6

        run(loop, scenario())


class TestGeoCapability:
    # Redis 文档经典坐标（西西里三城）
    _PALERMO = GeoMember(longitude=13.361389, latitude=38.115556, member=b"Palermo")
    _CATANIA = GeoMember(longitude=15.087269, latitude=37.502669, member=b"Catania")
    _AGRIGENTO = GeoMember(longitude=13.5765, latitude=37.2965, member=b"Agrigento")

    def test_geoadd_geopos_geodist_geohash(self, provider_client, key_prefix, loop):
        async def scenario():
            geo = require(provider_client, GeoCapability)
            key = f"{key_prefix}geo"
            assert await geo.geoadd(key, [self._PALERMO, self._CATANIA, self._AGRIGENTO]) == 3
            positions = await geo.geopos(key, b"Palermo", b"missing")
            assert positions[0] is not None
            assert abs(positions[0][0] - 13.361389) < 1e-4
            assert positions[1] is None
            dist = await geo.geodist(key, b"Palermo", b"Catania")
            assert dist is not None and 150_000 < dist < 180_000  # 文档值 ~166274m
            dist_km = await geo.geodist(key, b"Palermo", b"Catania", GeoUnit.KM)
            assert 150 < dist_km < 180
            hashes = await geo.geohash(key, b"Palermo", b"missing")
            assert hashes[0] not in (None, b"", "")
            assert hashes[1] is None

        run(loop, scenario())

    def test_georadius_family(self, provider_client, key_prefix, loop):
        async def scenario():
            geo = require(provider_client, GeoCapability)
            key = f"{key_prefix}geor"
            await geo.geoadd(key, [self._PALERMO, self._CATANIA, self._AGRIGENTO])
            # 以 Catania 为中心 100km：只含 Catania
            near = await geo.georadiusbymember(key, b"Catania", 100, GeoUnit.KM)
            assert near == [b"Catania"] or list(near) == [b"Catania"]
            # 300km：三城全中；count 截断
            found = await geo.georadiusbymember(key, b"Catania", 300, GeoUnit.KM, count=2)
            assert len(found) == 2
            # 坐标中心查询
            coords = await geo.georadius(key, 15.0, 37.5, 200, GeoUnit.KM)
            assert b"Catania" in list(coords)

        run(loop, scenario())


class TestScriptingCapability:
    @staticmethod
    async def _lua_available(capability) -> bool:
        """Lua 引擎探测：fakeredis 未装 lua 扩展时声明组但引擎不支持——skip。"""
        try:
            return await capability.eval("return 1", [], []) == 1
        except RedisError:
            return False

    def test_eval_and_script_cache(self, provider_client, key_prefix, loop):
        async def scenario():
            scripting = require(provider_client, ScriptingCapability)
            if not await self._lua_available(scripting):
                pytest.skip("后端引擎不支持 Lua（如 fakeredis 未安装 lua 扩展）")
            # EVAL：ARGV 透传
            assert await scripting.eval("return ARGV[1]", [], [b"boom"]) == b"boom"
            # EVAL：KEYS 操作真实数据
            key = f"{key_prefix}lua"
            await provider_client.set(key, b"42")
            result = await scripting.eval("return redis.call('get', KEYS[1])", [key], [])
            assert result == b"42"
            # SCRIPT LOAD → EVALSHA → SCRIPT EXISTS（脚本取 ARGV，返回类型跨后端稳定；
            # 状态回复类返回值如 redis.call('ping') 会以后端 bytes 形态出现，不作契约）
            sha = await scripting.script_load("return ARGV[1]")
            assert isinstance(sha, str) and len(sha) == 40
            assert await scripting.evalsha(sha, [], [b"cache-hit"]) == b"cache-hit"
            exists = await scripting.script_exists(sha, "0" * 40)
            assert exists[0] is True and exists[1] is False

        run(loop, scenario())

    def test_script_errors_map_to_script_error(self, provider_client, key_prefix, loop):
        async def scenario():
            scripting = require(provider_client, ScriptingCapability)
            if not await self._lua_available(scripting):
                pytest.skip("后端引擎不支持 Lua（如 fakeredis 未安装 lua 扩展）")
            # NOSCRIPT：未缓存的 sha
            with pytest.raises(RedisScriptError):
                await scripting.evalsha("0" * 40, [], [])
            # 脚本运行期错误（对 string key 执行 incr）→ RedisScriptError
            key = f"{key_prefix}lua-bad"
            await provider_client.set(key, b"not-a-number")
            with pytest.raises(RedisScriptError):
                await scripting.eval("return redis.call('incr', KEYS[1])", [key], [])

        run(loop, scenario())


class TestPubSubCapability:
    @staticmethod
    def test_subscribe_publish_roundtrip(provider_client, key_prefix, loop):
        async def scenario():
            pub = require(provider_client, PubSubCapability)
            channel = f"{key_prefix}chan".encode()
            handle = pub.pubsub()
            await handle.subscribe(channel)
            received = []

            async def consume():
                async for message in handle.listen():
                    received.append(message)
                    if message.type == "message":
                        return

            task = asyncio.ensure_future(consume())
            await asyncio.sleep(0.1)  # 消费者启动 + 订阅注册
            receivers = await pub.publish(channel, b"payload")
            await asyncio.wait_for(task, timeout=10)
            try:
                messages = [m for m in received if m.type == "message"]
                assert messages and messages[0].data == b"payload"
                assert messages[0].channel == channel
                assert receivers >= 1, "PUBLISH 应返回接收端个数（订阅中）"
            finally:
                await handle.aclose()

        run(loop, scenario())

    @staticmethod
    def test_psubscribe_pattern_messages(provider_client, key_prefix, loop):
        async def scenario():
            pub = require(provider_client, PubSubCapability)
            pattern = b"contract:*:pat"
            handle = pub.pubsub()
            await handle.psubscribe(pattern)
            received = []

            async def consume():
                async for message in handle.listen():
                    received.append(message)
                    if message.type == "pmessage":
                        return

            task = asyncio.ensure_future(consume())
            await asyncio.sleep(0.1)
            await pub.publish(f"{key_prefix}pat".encode(), b"hit")
            await asyncio.wait_for(task, timeout=10)
            try:
                messages = [m for m in received if m.type == "pmessage"]
                assert messages and messages[0].data == b"hit"
                assert messages[0].pattern == pattern
            finally:
                await handle.aclose()

        run(loop, scenario())

    @staticmethod
    def test_subscribe_requires_channel(provider_client, loop):
        async def scenario():
            pub = require(provider_client, PubSubCapability)
            handle = pub.pubsub()
            with pytest.raises(RedisCommandError):
                await handle.subscribe()
            await handle.aclose()

        run(loop, scenario())

    @staticmethod
    def test_commands_usable_while_subscribed(provider_client, key_prefix, loop):
        """订阅期间业务命令可用（独立订阅池契约：订阅连接不侵蚀命令池）。"""
        async def scenario():
            pub = require(provider_client, PubSubCapability)
            handle = pub.pubsub()
            await handle.subscribe(f"{key_prefix}iso".encode())
            try:
                # 订阅保持激活的同时并发执行普通命令——若订阅错误占用命令池
                # （或独占共享连接）将超时失败
                async def burst():
                    await asyncio.gather(
                        *[
                            provider_client.set(f"{key_prefix}iso:{i}".encode(), b"v")
                            for i in range(4)
                        ]
                    )

                await asyncio.wait_for(burst(), timeout=10)
            finally:
                await handle.aclose()

        run(loop, scenario())


class TestBlockingCapability:
    @staticmethod
    def test_blpop_immediate_and_timeout(provider_client, key_prefix, loop):
        async def scenario():
            blocking = require(provider_client, BlockingCommands)
            key = f"{key_prefix}bl"
            await provider_client.rpush(key, b"v1", b"v2")
            result = await blocking.blpop([key])
            assert result == (key.encode(), b"v1")
            # 超时返回 None（且真实等待超时时长）
            import time

            started = time.monotonic()
            result = await blocking.blpop([f"{key_prefix}empty"], Duration.seconds(1))
            elapsed = time.monotonic() - started
            assert result is None
            assert elapsed >= 0.8, f"BLPOP 超时应真实等待（elapsed={elapsed:.2f}s）"

        run(loop, scenario())

    @staticmethod
    def test_brpop_and_brpoplpush(provider_client, key_prefix, loop):
        async def scenario():
            blocking = require(provider_client, BlockingCommands)
            key = f"{key_prefix}br"
            await provider_client.rpush(key, b"1", b"2")
            assert await blocking.brpop([key]) == (key.encode(), b"2")
            assert await blocking.brpoplpush(
                f"{key_prefix}no", f"{key_prefix}dst", Duration.seconds(1)
            ) is None
            # 有数据：尾弹入目标头
            src, dst = f"{key_prefix}src", f"{key_prefix}dst"
            await provider_client.rpush(src, b"a", b"b")
            assert await blocking.brpoplpush(src, dst, Duration.seconds(1)) == b"b"
            assert await provider_client.lrange(dst, 0, -1) == [b"b"]

        run(loop, scenario())

    @staticmethod
    def test_blpop_requires_keys(provider_client, loop):
        async def scenario():
            blocking = require(provider_client, BlockingCommands)
            with pytest.raises(RedisCommandError):
                await blocking.blpop([])

        run(loop, scenario())
