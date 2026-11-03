# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""核心面契约：全量语义矩阵（设计文档 §七 覆盖内容）。

对任何 Provider 目标（REDIS_CONTRACT_TARGET 注入）运行同一套断言：
方法语义 / 返回哨兵值 / 集合运算 / SCAN 游标不变量。实现细节不测——
只测 SPI 协议承诺的行为。

事件循环：统一经会话级 ``loop`` fixture 执行（契约总则 #5，跨循环调用未定义）。
"""

from redis_spi.types import SCAN_START, Duration, SetCondition

# TTL 断言容差（秒）：实现允许向上取整，不允许提前过期。
TTL_TOLERANCE = 2


def run(loop, coro):
    """会话循环上执行协程（套件统一入口）。"""
    return loop.run_until_complete(coro)


class TestStringCommands:
    @staticmethod
    def test_get_set_round_trip_and_overwrite(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}kv"
            assert await provider_client.get(key) is None
            assert await provider_client.set(key, b"value-1") == b"OK"
            assert await provider_client.get(key) == b"value-1"
            assert await provider_client.set(key, b"value-2") == b"OK"
            assert await provider_client.get(key) == b"value-2"

        run(loop, scenario())

    @staticmethod
    def test_set_condition_nx_xx(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}nx"
            assert await provider_client.set(key, b"first", condition=SetCondition.NX) == b"OK"
            # NX：已存在则不写，返回 None
            assert await provider_client.set(key, b"second", condition=SetCondition.NX) is None
            assert await provider_client.get(key) == b"first"
            # XX：存在才写
            assert await provider_client.set(key, b"third", condition=SetCondition.XX) == b"OK"
            assert await provider_client.get(key) == b"third"
            # XX：不存在则不写
            assert await provider_client.set(f"{key_prefix}xx-miss", b"x", condition=SetCondition.XX) is None
            assert await provider_client.get(f"{key_prefix}xx-miss") is None

        run(loop, scenario())

    @staticmethod
    def test_set_nx_with_duration(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}nx-ttl"
            assert await provider_client.set(
                key, b"locked", condition=SetCondition.NX, duration=Duration.seconds(100)
            ) == b"OK"
            assert 0 < await provider_client.ttl(key) <= 100 + TTL_TOLERANCE
            # NX 不满足时即便带 duration 也不写入
            assert await provider_client.set(
                key, b"again", condition=SetCondition.NX, duration=Duration.seconds(100)
            ) is None

        run(loop, scenario())

    @staticmethod
    def test_set_keep_ttl_preserves_expiry(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}keepttl"
            await provider_client.set(key, b"v1", duration=Duration.seconds(100))
            await provider_client.set(key, b"v2", keep_ttl=True)
            assert await provider_client.get(key) == b"v2"
            # KEEPTTL：覆写后 TTL 保留
            remaining = await provider_client.ttl(key)
            assert 0 < remaining <= 100 + TTL_TOLERANCE
            # 普通覆写清 TTL
            await provider_client.set(key, b"v3")
            assert await provider_client.ttl(key) == -1

        run(loop, scenario())

    @staticmethod
    def test_get_set_and_mget_mset(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}getset"
            assert await provider_client.get_set(key, b"new") is None
            assert await provider_client.get_set(key, b"newer") == b"new"
            # MSET/MGET：保序、缺失位 None
            k1, k2, k3 = f"{key_prefix}m1", f"{key_prefix}m2", f"{key_prefix}m3"
            await provider_client.mset({k1: b"a", k2: b"b"})
            assert await provider_client.mget([k1, k3, k2]) == [b"a", None, b"b"]
            assert await provider_client.mget([]) == []

        run(loop, scenario())

    @staticmethod
    def test_msetnx_atomic_all_or_nothing(provider_client, key_prefix, loop):
        async def scenario():
            base = f"{key_prefix}msetnx"
            await provider_client.set(f"{base}-exists", b"v")
            # 任一 key 已存在 → 全部不写
            assert await provider_client.msetnx(
                {f"{base}-a": b"1", f"{base}-exists": b"2"}
            ) is False
            assert await provider_client.get(f"{base}-a") is None
            # 全新 key → 全部写入
            assert await provider_client.msetnx({f"{base}-b": b"3", f"{base}-c": b"4"}) is True
            assert await provider_client.get(f"{base}-b") == b"3"

        run(loop, scenario())

    @staticmethod
    def test_append_strlen_getrange_setrange(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}str"
            assert await provider_client.append(key, b"hel") == 3
            assert await provider_client.append(key, b"lo") == 5
            assert await provider_client.strlen(key) == 5
            # GETRANGE 闭区间 + 负索引
            assert await provider_client.getrange(key, 0, 4) == b"hello"
            assert await provider_client.getrange(key, -5, -1) == b"hello"
            assert await provider_client.getrange(key, 1, -2) == b"ell"
            assert await provider_client.getrange(f"{key_prefix}missing", 0, 1) == b""
            # SETRANGE：越界补 \x00、返回新长度
            pad = f"{key_prefix}pad"
            assert await provider_client.setrange(pad, 5, b"ab") == 7
            assert await provider_client.get(pad) == b"\x00\x00\x00\x00\x00ab"
            assert await provider_client.setrange(key, 1, b"E") == 5
            assert await provider_client.get(key) == b"hEllo"

        run(loop, scenario())


class TestKeyCommands:
    @staticmethod
    def test_exists_delete_counts(provider_client, key_prefix, loop):
        async def scenario():
            k1, k2 = f"{key_prefix}d1", f"{key_prefix}d2"
            await provider_client.set(k1, b"v")
            await provider_client.set(k2, b"v")
            assert await provider_client.exists(k1, k2, f"{key_prefix}missing") == 2
            assert await provider_client.delete(k1, k2, f"{key_prefix}missing") == 2
            assert await provider_client.exists(k1) == 0

        run(loop, scenario())

    @staticmethod
    def test_key_type_by_container(provider_client, key_prefix, loop):
        async def scenario():
            base = f"{key_prefix}type"
            await provider_client.set(f"{base}-s", b"v")
            await provider_client.hset(f"{base}-h", field=b"f", value=b"v")
            await provider_client.rpush(f"{base}-l", b"v")
            await provider_client.sadd(f"{base}-t", b"m")
            assert await provider_client.key_type(f"{base}-s") == b"string"
            assert await provider_client.key_type(f"{base}-h") == b"hash"
            assert await provider_client.key_type(f"{base}-l") == b"list"
            assert await provider_client.key_type(f"{base}-t") == b"set"
            assert await provider_client.key_type(f"{base}-none") == b"none"

        run(loop, scenario())

    @staticmethod
    def test_ttl_sentinels_and_expire_family(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}ttl"
            await provider_client.set(key, b"v")
            # 永久 key：-1；不存在：-2
            assert await provider_client.ttl(key) == -1
            assert await provider_client.ttl(f"{key_prefix}missing") == -2
            assert await provider_client.pttl(f"{key_prefix}missing") == -2
            # EXPIRE（秒）
            assert await provider_client.expire(key, Duration.seconds(100)) is True
            assert 0 < await provider_client.ttl(key) <= 100 + TTL_TOLERANCE
            # PEXPIRE（毫秒）+ PTTL
            assert await provider_client.pexpire(key, Duration.milliseconds(5000)) is True
            pttl = await provider_client.pttl(key)
            assert 0 < pttl <= 5000
            # PERSIST 转永久
            assert await provider_client.persist(key) is True
            assert await provider_client.ttl(key) == -1
            assert await provider_client.persist(key) is False
            # 不存在 key 的 EXPIRE：False
            assert await provider_client.expire(f"{key_prefix}missing", Duration.seconds(10)) is False

        run(loop, scenario())

    @staticmethod
    def test_expire_at_absolute_timestamps(provider_client, key_prefix, loop):
        async def scenario():
            import time

            key = f"{key_prefix}expireat"
            await provider_client.set(key, b"v")
            now = time.time()
            assert await provider_client.expire_at(key, int(now) + 100) is True
            assert 0 < await provider_client.ttl(key) <= 100 + TTL_TOLERANCE
            assert await provider_client.pexpire_at(key, int((now + 50) * 1000)) is True
            pttl = await provider_client.pttl(key)
            assert 0 < pttl <= 50_000 + TTL_TOLERANCE * 1000

        run(loop, scenario())

    @staticmethod
    def test_expiration_removes_key(provider_client, key_prefix, loop):
        async def scenario():
            import asyncio

            key = f"{key_prefix}vanish"
            await provider_client.set(key, b"v", duration=Duration.milliseconds(200))
            assert await provider_client.exists(key) == 1
            await asyncio.sleep(0.4)
            assert await provider_client.exists(key) == 0
            assert await provider_client.get(key) is None

        run(loop, scenario())


class TestHashCommands:
    @staticmethod
    def test_hset_forms_and_validation(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}h"
            # field/value 形态
            assert await provider_client.hset(key, field=b"f1", value=b"v1") == 1
            assert await provider_client.hget(key, b"f1") == b"v1"
            # mapping 形态；已存在 field 覆盖不计数
            assert await provider_client.hset(key, {b"f1": b"v1b", b"f2": b"v2"}) == 1
            assert await provider_client.hget(key, b"f1") == b"v1b"

        run(loop, scenario())

    @staticmethod
    def test_hsetnx_hexists_hlen(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}hnx"
            assert await provider_client.hsetnx(key, b"f", b"v") is True
            assert await provider_client.hsetnx(key, b"f", b"v2") is False
            assert await provider_client.hget(key, b"f") == b"v"
            assert await provider_client.hexists(key, b"f") is True
            assert await provider_client.hexists(key, b"missing") is False
            assert await provider_client.hlen(key) == 1
            assert await provider_client.hlen(f"{key_prefix}missing-hash") == 0

        run(loop, scenario())

    @staticmethod
    def test_hgetall_hkeys_hvals_hmget_hdel(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}hfull"
            await provider_client.hset(key, {b"a": b"1", b"b": b"2", b"c": b"3"})
            assert await provider_client.hgetall(key) == {b"a": b"1", b"b": b"2", b"c": b"3"}
            assert set(await provider_client.hkeys(key)) == {b"a", b"b", b"c"}
            assert set(await provider_client.hvals(key)) == {b"1", b"2", b"3"}
            assert await provider_client.hmget(key, [b"a", b"missing", b"c"]) == [b"1", None, b"3"]
            assert await provider_client.hgetall(f"{key_prefix}missing-hash2") == {}
            assert await provider_client.hdel(key, b"a", b"missing") == 1
            # 删空最后一个 field → key 整体消失
            assert await provider_client.hdel(key, b"b", b"c") == 2
            assert await provider_client.exists(key) == 0

        run(loop, scenario())

    @staticmethod
    def test_hincr_by_and_float(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}hincr"
            assert await provider_client.hincr_by(key, b"n", 5) == 5
            assert await provider_client.hincr_by(key, b"n", -2) == 3
            assert await provider_client.hincr_by_float(key, b"x", 1.5) == 1.5
            result = await provider_client.hincr_by_float(key, b"x", 2.25)
            assert abs(result - 3.75) < 1e-9

        run(loop, scenario())

    @staticmethod
    def test_hscan_loops_to_start_cursor(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}hscan"
            mapping = {f"field-{i}".encode(): str(i).encode() for i in range(5)}
            await provider_client.hset(key, mapping)
            collected: dict = {}
            cursor = SCAN_START
            for _ in range(100):  # 防御性上限
                next_cursor, batch = await provider_client.hscan(key, cursor, count=2)
                collected.update(batch)
                cursor = next_cursor
                if cursor == SCAN_START:
                    break
            assert cursor == SCAN_START, "HSCAN must terminate at cursor 0"
            assert collected == mapping

        run(loop, scenario())


class TestListCommands:
    @staticmethod
    def test_push_variants_and_pushx(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}list"
            assert await provider_client.rpush(key, b"a", b"b") == 2
            assert await provider_client.lpush(key, b"z") == 3
            assert await provider_client.lrange(key, 0, -1) == [b"z", b"a", b"b"]
            # pushx：缺失 key 返回 0 不创建
            assert await provider_client.lpushx(f"{key_prefix}missing-list", b"x") == 0
            assert await provider_client.rpushx(f"{key_prefix}missing-list", b"x") == 0
            assert await provider_client.exists(f"{key_prefix}missing-list") == 0
            assert await provider_client.lpushx(key, b"y") == 4
            assert await provider_client.rpushx(key, b"c") == 5

        run(loop, scenario())

    @staticmethod
    def test_pop_single_and_count(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}pop"
            await provider_client.rpush(key, b"1", b"2", b"3")
            assert await provider_client.lpop(key) == b"1"
            assert await provider_client.rpop(key) == b"3"
            # count 形态：返回列表，不足全返
            assert await provider_client.lpop(key, 10) == [b"2"]
            assert await provider_client.lpop(key) is None
            # 缺失 key 的 count 形态
            assert await provider_client.rpop(f"{key_prefix}missing", 3) is None

        run(loop, scenario())

    @staticmethod
    def test_lrange_ltrim_boundaries(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}trim"
            await provider_client.rpush(key, b"a", b"b", b"c", b"d", b"e")
            assert await provider_client.lrange(key, 1, -2) == [b"b", b"c", b"d"]
            assert await provider_client.lrange(key, -2, -1) == [b"d", b"e"]
            assert await provider_client.lrange(f"{key_prefix}missing", 0, -1) == []
            # LTRIM 闭区间保留
            assert await provider_client.ltrim(key, 1, 3) is None
            assert await provider_client.lrange(key, 0, -1) == [b"b", b"c", b"d"]
            await provider_client.ltrim(key, 0, -1)
            assert await provider_client.llen(key) == 3

        run(loop, scenario())

    @staticmethod
    def test_lindex_lset_lrem(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}lidx"
            await provider_client.rpush(key, b"a", b"b", b"a", b"b", b"a")
            assert await provider_client.lindex(key, 0) == b"a"
            assert await provider_client.lindex(key, -1) == b"a"
            assert await provider_client.lindex(key, 99) is None
            await provider_client.lset(key, 1, b"B")
            assert await provider_client.lindex(key, 1) == b"B"
            # lrem count 语义：>0 从头删、<0 从尾删、=0 全删
            assert await provider_client.lrem(key, 1, b"a") == 1
            assert await provider_client.lrange(key, 0, -1) == [b"B", b"a", b"b", b"a"]
            assert await provider_client.lrem(key, -1, b"a") == 1
            assert await provider_client.lrange(key, 0, -1) == [b"B", b"a", b"b"]
            # count=0：全删（当前仅剩 1 个 b）
            assert await provider_client.lrem(key, 0, b"b") == 1
            assert await provider_client.lrange(key, 0, -1) == [b"B", b"a"]

        run(loop, scenario())

    @staticmethod
    def test_rpoplpush_moves_tail_to_head(provider_client, key_prefix, loop):
        async def scenario():
            src, dst = f"{key_prefix}src", f"{key_prefix}dst"
            await provider_client.rpush(src, b"1", b"2", b"3")
            await provider_client.rpush(dst, b"x")
            assert await provider_client.rpoplpush(src, dst) == b"3"
            assert await provider_client.lrange(src, 0, -1) == [b"1", b"2"]
            assert await provider_client.lrange(dst, 0, -1) == [b"3", b"x"]
            # 空 source（缺失）→ None，destination 不被创建
            assert await provider_client.rpoplpush(f"{key_prefix}no", dst) is None

        run(loop, scenario())


class TestSetCommands:
    @staticmethod
    def test_sadd_srem_smembers_scard(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}set"
            assert await provider_client.sadd(key, b"a", b"b", b"a") == 2
            assert await provider_client.smembers(key) == {b"a", b"b"}
            assert await provider_client.scard(key) == 2
            assert await provider_client.srem(key, b"a", b"missing") == 1
            assert await provider_client.smembers(key) == {b"b"}
            assert await provider_client.smembers(f"{key_prefix}missing-set") == set()
            assert await provider_client.scard(f"{key_prefix}missing-set") == 0

        run(loop, scenario())

    @staticmethod
    def test_sismember_returns_bool(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}sism"
            await provider_client.sadd(key, b"m")
            # 契约显式要求 bool（实现不得透传服务端 int 0/1）
            assert await provider_client.sismember(key, b"m") is True
            assert await provider_client.sismember(key, b"other") is False
            assert await provider_client.sismember(f"{key_prefix}missing", b"m") is False

        run(loop, scenario())

    @staticmethod
    def test_spop_and_srandmember(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}spop"
            await provider_client.sadd(key, b"a", b"b", b"c")
            # 单成员弹出
            popped = await provider_client.spop(key)
            assert popped in {b"a", b"b", b"c"}
            assert await provider_client.scard(key) == 2
            # count 弹出集合
            popped_set = await provider_client.spop(key, 5)
            assert set(popped_set) and len(popped_set) == 2
            assert await provider_client.scard(key) == 0
            # srandmember 不删除；count<0 允许重复
            key2 = f"{key_prefix}srand"
            await provider_client.sadd(key2, b"x", b"y")
            assert await provider_client.srandmember(key2) in {b"x", b"y"}
            assert await provider_client.scard(key2) == 2
            repeated = await provider_client.srandmember(key2, -10)
            assert len(repeated) == 10
            assert set(repeated) == {b"x", b"y"}
            distinct = await provider_client.srandmember(key2, 5)
            assert len(distinct) == 2

        run(loop, scenario())

    @staticmethod
    def test_smove(provider_client, key_prefix, loop):
        async def scenario():
            src, dst = f"{key_prefix}mv-src", f"{key_prefix}mv-dst"
            await provider_client.sadd(src, b"a", b"b")
            assert await provider_client.smove(src, dst, b"a") is True
            assert await provider_client.smembers(src) == {b"b"}
            assert await provider_client.smembers(dst) == {b"a"}
            # source 缺 member → False
            assert await provider_client.smove(src, dst, b"missing") is False
            # source 缺失 → False，destination 不创建
            assert await provider_client.smove(f"{key_prefix}no", dst, b"a") is False

        run(loop, scenario())

    @staticmethod
    def test_set_operations_and_stores(provider_client, key_prefix, loop):
        async def scenario():
            base = f"{key_prefix}ops"
            k1, k2, missing = f"{base}-1", f"{base}-2", f"{base}-missing"
            await provider_client.sadd(k1, b"a", b"b", b"c")
            await provider_client.sadd(k2, b"b", b"c", b"d")
            # 缺失 key 按空集处理
            assert await provider_client.sinter(k1, k2) == {b"b", b"c"}
            assert await provider_client.sunion(k1, missing) == {b"a", b"b", b"c"}
            assert await provider_client.sdiff(k1, k2) == {b"a"}
            # store 变体写入 destination 并返回成员数
            dst = f"{base}-dst"
            assert await provider_client.sinterstore(dst, k1, k2) == 2
            assert await provider_client.smembers(dst) == {b"b", b"c"}
            assert await provider_client.sunionstore(dst, k1, missing) == 3
            assert await provider_client.sdiffstore(dst, k1, k2) == 1
            assert await provider_client.smembers(dst) == {b"a"}

        run(loop, scenario())

    @staticmethod
    def test_sscan_loops_to_start_cursor(provider_client, key_prefix, loop):
        async def scenario():
            key = f"{key_prefix}sscan"
            members = {f"m{i}".encode() for i in range(5)}
            await provider_client.sadd(key, *members)
            collected: set = set()
            cursor = SCAN_START
            for _ in range(100):
                next_cursor, batch = await provider_client.sscan(key, cursor, count=2)
                collected.update(batch)
                cursor = next_cursor
                if cursor == SCAN_START:
                    break
            assert cursor == SCAN_START, "SSCAN must terminate at cursor 0"
            assert collected == members

        run(loop, scenario())


class TestScanCommands:
    @staticmethod
    def test_scan_completes_at_start_cursor(provider_client, key_prefix, loop):
        async def scenario():
            keys = {f"{key_prefix}scan:{i}".encode() for i in range(5)}
            for key in keys:
                await provider_client.set(key, b"v")
            cursor, seen = SCAN_START, set()
            # 上限须覆盖整个键空间（真实 Redis SCAN 游标走全部桶，match 只过滤产出）
            for _ in range(10_000):
                batch = await provider_client.scan(cursor, count=2, match=f"{key_prefix}scan:*".encode())
                seen.update(batch.items)
                cursor = batch.cursor
                if cursor == SCAN_START:
                    break
            assert cursor == SCAN_START, "SCAN must terminate at cursor 0"
            assert seen == keys

        run(loop, scenario())

    @staticmethod
    def test_scan_type_filter(provider_client, key_prefix, loop):
        async def scenario():
            s, h = f"{key_prefix}t-s", f"{key_prefix}t-h"
            await provider_client.set(s, b"v")
            await provider_client.hset(h, field=b"f", value=b"v")
            cursor, seen = SCAN_START, set()
            for _ in range(10_000):
                batch = await provider_client.scan(cursor, match=f"{key_prefix}t-*".encode(), type_name=b"hash")
                seen.update(batch.items)
                cursor = batch.cursor
                if cursor == SCAN_START:
                    break
            assert seen == {h.encode()}

        run(loop, scenario())

    @staticmethod
    def test_scan_iter_yields_all_matches(provider_client, key_prefix, loop):
        async def scenario():
            keys = {f"{key_prefix}it:{i}".encode() for i in range(4)}
            for key in keys:
                await provider_client.set(key, b"v")

            async def collect():
                found = set()
                async for key in provider_client.scan_iter(match=f"{key_prefix}it:*".encode()):
                    found.add(key)
                return found

            assert await collect() == keys

        run(loop, scenario())
