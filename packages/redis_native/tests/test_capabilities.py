# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""8 个能力组实现单测：调用翻译 / 前置校验 / 结果归一 / 池绑定。

断言口径：fake 记录的 (name, args, kwargs) 必须与 redis-py 8.x 真实签名
逐一对应（调用翻译正确性），非法入参在客户端侧确定性拒绝（fake.calls
保持空 = 未触达 redis-py）。
"""

from __future__ import annotations

import asyncio

import pytest
import redis.exceptions as redis_exc

from redis_native.capabilities import capability_view
from redis_native.capabilities.bitmap import NativeBitmapCapability
from redis_native.capabilities.blocking import NativeBlockingCapability
from redis_native.capabilities.counter import NativeCounterCapability
from redis_native.capabilities.geo import NativeGeoCapability
from redis_native.capabilities.hll import NativeHyperLogLogCapability
from redis_native.capabilities.pubsub import NativePubSubCapability
from redis_native.capabilities.scripting import NativeScriptingCapability
from redis_native.capabilities.sortedset import NativeSortedSetCapability
from redis_native.pubsub_handle import NativePubSubHandle

from redis_spi.capabilities import (
    BitmapCapability,
    BlockingCommands,
    CounterCapability,
    PubSubCapability,
    ScriptingCapability,
)
from redis_spi.exceptions import RedisCommandError, RedisTimeoutError
from redis_spi.types import Duration, GeoMember, GeoUnit, SetCondition

from redis_native_test_fakes import FakePubSub, FakeRedisClient


class TestCounter:
    @staticmethod
    def test_incr_delegation():
        fake = FakeRedisClient(results={"incr": 6})
        cap = NativeCounterCapability(fake)
        assert asyncio.run(cap.incr("c", 5)) == 6
        assert fake.calls == [("incr", ("c", 5), {})]

    @staticmethod
    def test_decr_default_amount():
        fake = FakeRedisClient(results={"decr": 4})
        asyncio.run(NativeCounterCapability(fake).decr("c"))
        assert fake.calls == [("decr", ("c", 1), {})]

    @staticmethod
    def test_incr_timeout_result_unknown():
        # 非幂等写：超时后禁止盲重试（result_known=False）
        fake = FakeRedisClient(exceptions={"incr": redis_exc.TimeoutError("t")})
        with pytest.raises(RedisTimeoutError) as excinfo:
            asyncio.run(NativeCounterCapability(fake).incr("c"))
        assert excinfo.value.result_known is False

    @staticmethod
    def test_incr_by_float():
        fake = FakeRedisClient(results={"incrbyfloat": 1.5})
        asyncio.run(NativeCounterCapability(fake).incr_by_float("c", 0.5))
        assert fake.calls == [("incrbyfloat", ("c", 0.5), {})]


class TestSortedSet:
    @staticmethod
    def test_zadd_nx_kwargs():
        fake = FakeRedisClient(results={"zadd": 1})
        asyncio.run(
            NativeSortedSetCapability(fake).zadd(
                "z", {"m": 1.0}, condition=SetCondition.NX
            )
        )
        assert fake.calls == [("zadd", ("z", {"m": 1.0}), {"nx": True})]

    @staticmethod
    def test_zincrby_arg_order():
        fake = FakeRedisClient(results={"zincrby": 2.5})
        asyncio.run(NativeSortedSetCapability(fake).zincrby("z", 1.5, "m"))
        assert fake.calls == [("zincrby", ("z", 1.5, "m"), {})]

    @staticmethod
    def test_zrangebyscore_limit_with_offset():
        fake = FakeRedisClient(results={"zrangebyscore": []})
        asyncio.run(
            NativeSortedSetCapability(fake).zrangebyscore(
                "z", 0, 100, offset=10, limit=5
            )
        )
        assert fake.calls == [
            ("zrangebyscore", ("z", 0, 100), {"start": 10, "num": 5, "withscores": False})
        ]

    @staticmethod
    def test_zrangebyscore_pagination_kwargs():
        # redis-py 要求 start/num 成对：无分页时不传这对参数（契约修正：
        # offset 缺省 0，limit 单给即取前 limit 个——"同给校验"与缺省值矛盾）。
        fake = FakeRedisClient(results={"zrangebyscore": []})
        asyncio.run(NativeSortedSetCapability(fake).zrangebyscore("z", 0, 100))
        assert fake.calls == [
            ("zrangebyscore", ("z", 0, 100), {"withscores": False})
        ]
        asyncio.run(
            NativeSortedSetCapability(fake).zrangebyscore(
                "z", 0, 100, offset=2, limit=5
            )
        )
        assert fake.calls[-1] == (
            "zrangebyscore",
            ("z", 0, 100),
            {"withscores": False, "start": 2, "num": 5},
        )

    @staticmethod
    def test_zrangebylex_pagination_kwargs():
        fake = FakeRedisClient(results={"zrangebylex": []})
        asyncio.run(NativeSortedSetCapability(fake).zrangebylex("z", "-", "+"))
        assert fake.calls == [("zrangebylex", ("z", "-", "+"), {})]
        asyncio.run(
            NativeSortedSetCapability(fake).zrangebylex(
                "z", "-", "+", offset=1, limit=2
            )
        )
        assert fake.calls[-1] == ("zrangebylex", ("z", "-", "+"), {"start": 1, "num": 2})

    @staticmethod
    def test_zrange_kwargs():
        fake = FakeRedisClient(results={"zrange": []})
        asyncio.run(
            NativeSortedSetCapability(fake).zrange(
                "z", 0, -1, withscores=True, desc=True
            )
        )
        assert fake.calls == [
            ("zrange", ("z", 0, -1), {"desc": True, "withscores": True})
        ]

    @staticmethod
    def test_zunionstore_aggregate_normalized():
        fake = FakeRedisClient(results={"zunionstore": 3})
        asyncio.run(
            NativeSortedSetCapability(fake).zunionstore(
                "dest", ["k1", "k2"], aggregate="min"
            )
        )
        assert fake.calls == [
            ("zunionstore", ("dest", ["k1", "k2"]), {"aggregate": "MIN"})
        ]

    @pytest.mark.parametrize("aggregate", ["AVG", "bogus"])
    def test_zunionstore_bad_aggregate(self, aggregate):
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="aggregate"):
            asyncio.run(
                NativeSortedSetCapability(fake).zunionstore(
                    "dest", ["k1"], aggregate=aggregate
                )
            )
        assert fake.calls == []

    @staticmethod
    def test_zinterstore_keys_listified():
        fake = FakeRedisClient(results={"zinterstore": 2})
        asyncio.run(NativeSortedSetCapability(fake).zinterstore("dest", ("k1", "k2")))
        assert fake.calls == [
            ("zinterstore", ("dest", ["k1", "k2"]), {"aggregate": None})
        ]

    @staticmethod
    def test_zscan_score_normalization():
        fake = FakeRedisClient(
            results={"zscan": (0, [("a", b"1.5"), ("b", "2")])}
        )
        cursor, pairs = asyncio.run(
            NativeSortedSetCapability(fake).zscan("z", cursor=7)
        )
        assert cursor == 0
        assert pairs == [("a", 1.5), ("b", 2.0)]
        assert all(isinstance(score, float) for _, score in pairs)
        assert fake.calls == [
            ("zscan", ("z",), {"cursor": 7, "match": None, "count": None})
        ]

    @staticmethod
    def test_zscan_unparseable_score_rejected():
        fake = FakeRedisClient(results={"zscan": (0, [("a", b"xyz")])})
        with pytest.raises(RedisCommandError, match="score"):
            asyncio.run(NativeSortedSetCapability(fake).zscan("z"))
        assert fake.calls != []


class TestBitmap:
    @staticmethod
    def test_setbit_value_out_of_range():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="0/1"):
            asyncio.run(NativeBitmapCapability(fake).setbit("k", 0, 2))
        assert fake.calls == []

    @staticmethod
    def test_setbit_negative_offset():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="offset"):
            asyncio.run(NativeBitmapCapability(fake).setbit("k", -1, 1))
        assert fake.calls == []

    @staticmethod
    def test_bitcount_range_paired():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="成对"):
            asyncio.run(NativeBitmapCapability(fake).bitcount("k", 0))
        assert fake.calls == []

    @staticmethod
    def test_bitcount_full_range():
        fake = FakeRedisClient(results={"bitcount": 8})
        assert asyncio.run(NativeBitmapCapability(fake).bitcount("k")) == 8
        assert fake.calls == [("bitcount", ("k", None, None), {})]

    @staticmethod
    def test_bitpos_bit_validation():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="0/1"):
            asyncio.run(NativeBitmapCapability(fake).bitpos("k", 3))
        assert fake.calls == []

    @staticmethod
    def test_bitop_lowercase_normalized():
        fake = FakeRedisClient(results={"bitop": 4})
        asyncio.run(NativeBitmapCapability(fake).bitop("and", "dest", "k1", "k2"))
        assert fake.calls == [("bitop", ("AND", "dest", "k1", "k2"), {})]

    @staticmethod
    def test_bitop_invalid_op():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="operation"):
            asyncio.run(NativeBitmapCapability(fake).bitop("nand", "dest", "k1"))
        assert fake.calls == []

    @staticmethod
    def test_bitop_not_multi_key_rejected():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="仅允许 1 个"):
            asyncio.run(NativeBitmapCapability(fake).bitop("not", "dest", "k1", "k2"))
        assert fake.calls == []

    @staticmethod
    def test_bitop_no_keys_rejected():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="至少一个 source key"):
            asyncio.run(NativeBitmapCapability(fake).bitop("or", "dest"))
        assert fake.calls == []

    @staticmethod
    def test_getbit_passthrough():
        fake = FakeRedisClient(results={"getbit": 1})
        assert asyncio.run(NativeBitmapCapability(fake).getbit("k", 3)) == 1
        assert fake.calls == [("getbit", ("k", 3), {})]


class TestHyperLogLog:
    @staticmethod
    def test_pfadd_empty_rejected():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="至少一个 element"):
            asyncio.run(NativeHyperLogLogCapability(fake).pfadd("k"))
        assert fake.calls == []

    @staticmethod
    def test_pfadd_delegation():
        fake = FakeRedisClient(results={"pfadd": 1})
        assert asyncio.run(NativeHyperLogLogCapability(fake).pfadd("k", "a", "b")) == 1
        assert fake.calls == [("pfadd", ("k", "a", "b"), {})]

    @staticmethod
    def test_pfcount_empty_rejected():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="至少一个 key"):
            asyncio.run(NativeHyperLogLogCapability(fake).pfcount())
        assert fake.calls == []

    @staticmethod
    def test_pfmerge_passthrough():
        fake = FakeRedisClient(results={"pfmerge": True})
        assert (
            asyncio.run(NativeHyperLogLogCapability(fake).pfmerge("dest", "s1", "s2"))
            is True
        )
        assert fake.calls == [("pfmerge", ("dest", "s1", "s2"), {})]


class TestGeo:
    @staticmethod
    def test_geoadd_flattens_members():
        fake = FakeRedisClient(results={"geoadd": 1})
        asyncio.run(
            NativeGeoCapability(fake).geoadd(
                "geo", [GeoMember(116.4, 39.9, "bj"), GeoMember(121.5, 31.2, "sh")]
            )
        )
        assert fake.calls == [
            (
                "geoadd",
                ("geo", [116.4, 39.9, "bj", 121.5, 31.2, "sh"]),
                {},
            )
        ]

    @staticmethod
    def test_geoadd_empty_rejected():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="至少一个 GeoMember"):
            asyncio.run(NativeGeoCapability(fake).geoadd("geo", []))
        assert fake.calls == []

    @staticmethod
    def test_geoadd_nx_kwargs():
        fake = FakeRedisClient(results={"geoadd": 0})
        asyncio.run(
            NativeGeoCapability(fake).geoadd(
                "geo", [GeoMember(116.4, 39.9, "bj")], condition=SetCondition.NX
            )
        )
        assert fake.calls == [
            ("geoadd", ("geo", [116.4, 39.9, "bj"]), {"nx": True})
        ]

    @staticmethod
    def test_geodist_unit_value():
        fake = FakeRedisClient(results={"geodist": 1067000.0})
        asyncio.run(
            NativeGeoCapability(fake).geodist("geo", "bj", "sh", unit=GeoUnit.KM)
        )
        assert fake.calls == [
            ("geodist", ("geo", "bj", "sh"), {"unit": "km"})
        ]

    @staticmethod
    def test_geopos_coord_normalization():
        fake = FakeRedisClient(
            results={"geopos": [(116.0, 39.0), None, [116.5, 39.5]]}
        )
        result = asyncio.run(NativeGeoCapability(fake).geopos("geo", "a", "b", "c"))
        assert result == [(116.0, 39.0), None, (116.5, 39.5)]
        assert all(
            isinstance(item, tuple) for item in result if item is not None
        )
        assert fake.calls == [("geopos", ("geo", "a", "b", "c"), {})]

    @staticmethod
    def test_geohash_passthrough():
        fake = FakeRedisClient(results={"geohash": [b"wx4g0", None]})
        assert asyncio.run(NativeGeoCapability(fake).geohash("geo", "a", "b")) == [
            b"wx4g0",
            None,
        ]

    @staticmethod
    def test_georadius_kwargs():
        fake = FakeRedisClient(results={"georadius": []})
        asyncio.run(
            NativeGeoCapability(fake).georadius(
                "geo",
                116.0,
                39.0,
                100.0,
                GeoUnit.KM,
                with_coord=True,
                with_dist=True,
                count=3,
            )
        )
        assert fake.calls == [
            (
                "georadius",
                ("geo", 116.0, 39.0, 100.0),
                {"unit": "km", "withdist": True, "withcoord": True, "count": 3},
            )
        ]

    @staticmethod
    def test_georadiusbymember_kwargs():
        fake = FakeRedisClient(results={"georadiusbymember": []})
        asyncio.run(
            NativeGeoCapability(fake).georadiusbymember(
                "geo", "bj", 50.0, GeoUnit.M, count=2
            )
        )
        assert fake.calls == [
            (
                "georadiusbymember",
                ("geo", "bj", 50.0),
                {"unit": "m", "withdist": False, "withcoord": False, "count": 2},
            )
        ]


class TestScripting:
    @staticmethod
    def test_eval_splices_keys_and_args():
        fake = FakeRedisClient(results={"eval": 1})
        asyncio.run(NativeScriptingCapability(fake).eval("return 1", ["k1", "k2"], ["a1"]))
        assert fake.calls == [("eval", ("return 1", 2, "k1", "k2", "a1"), {})]

    @staticmethod
    def test_evalsha_splices():
        fake = FakeRedisClient(results={"evalsha": 1})
        asyncio.run(NativeScriptingCapability(fake).evalsha("sha", ["k1"], ["a1"]))
        assert fake.calls == [("evalsha", ("sha", 1, "k1", "a1"), {})]

    @staticmethod
    def test_script_load_bytes_sha_decoded():
        fake = FakeRedisClient(results={"script_load": b"abc123"})
        assert asyncio.run(NativeScriptingCapability(fake).script_load("s")) == "abc123"

    @staticmethod
    def test_script_load_text_sha_passthrough():
        fake = FakeRedisClient(results={"script_load": "abc123"})
        assert asyncio.run(NativeScriptingCapability(fake).script_load("s")) == "abc123"

    @staticmethod
    def test_script_exists_int_to_bool():
        fake = FakeRedisClient(results={"script_exists": [1, 0, 1]})
        assert asyncio.run(
            NativeScriptingCapability(fake).script_exists("s1", "s2", "s3")
        ) == [True, False, True]
        assert fake.calls == [("script_exists", ("s1", "s2", "s3"), {})]


class TestPubSubCapability:
    @staticmethod
    def test_pubsub_uses_subscriber_pool():
        main = FakeRedisClient()
        subscriber = FakeRedisClient()
        handle = NativePubSubCapability(main, subscriber).pubsub()
        assert isinstance(handle, NativePubSubHandle)
        assert [c[0] for c in subscriber.calls] == ["pubsub"]
        assert main.calls == []

    @staticmethod
    def test_publish_uses_main_pool():
        main = FakeRedisClient(results={"publish": 2})
        subscriber = FakeRedisClient()
        assert (
            asyncio.run(NativePubSubCapability(main, subscriber).publish("ch", "msg"))
            == 2
        )
        assert main.calls == [("publish", ("ch", "msg"), {})]
        assert subscriber.calls == []


class TestBlocking:
    @staticmethod
    def test_blpop_default_timeout_zero():
        fake = FakeRedisClient(results={"blpop": ("k", b"v")})
        assert asyncio.run(NativeBlockingCapability(fake).blpop(["k"])) == ("k", b"v")
        assert fake.calls == [("blpop", (["k"], 0.0), {})]

    @staticmethod
    def test_blpop_sub_second_timeout():
        fake = FakeRedisClient(results={"blpop": None})
        asyncio.run(
            NativeBlockingCapability(fake).blpop(
                ["a", "b"], Duration.milliseconds(1500)
            )
        )
        assert fake.calls == [("blpop", (["a", "b"], 2), {})]

    @staticmethod
    def test_blpop_empty_rejected():
        fake = FakeRedisClient()
        with pytest.raises(RedisCommandError, match="至少一个 key"):
            asyncio.run(NativeBlockingCapability(fake).blpop([]))
        assert fake.calls == []

    @staticmethod
    def test_brpoplpush_timeout():
        fake = FakeRedisClient(results={"brpoplpush": b"v"})
        asyncio.run(
            NativeBlockingCapability(fake).brpoplpush(
                "src", "dst", Duration.seconds(2)
            )
        )
        assert fake.calls == [("brpoplpush", ("src", "dst", 2.0), {})]


class TestCapabilityViewDispatch:
    @staticmethod
    def test_dispatch_table():
        # capability_view 按 SPI 协议类分发（传实现类返回 None）
        main = FakeRedisClient()
        subscriber = FakeRedisClient()
        subscriber.pubsub_obj = FakePubSub()
        blocking = FakeRedisClient()

        class _Client:
            redis_client = main
            subscriber_client = subscriber
            blocking_client = blocking

        view = capability_view(_Client(), PubSubCapability)
        assert isinstance(view, NativePubSubCapability)
        assert getattr(view, "_main") is main and getattr(view, "_subscriber") is subscriber  # noqa: SLF001

        view = capability_view(_Client(), BlockingCommands)
        assert isinstance(view, NativeBlockingCapability)
        assert getattr(view, "_redis") is blocking  # noqa: SLF001

        view = capability_view(_Client(), CounterCapability)
        assert isinstance(view, NativeCounterCapability)
        assert getattr(view, "_redis") is main  # noqa: SLF001

        view = capability_view(_Client(), BitmapCapability)
        assert isinstance(view, NativeBitmapCapability)
        view = capability_view(_Client(), ScriptingCapability)
        assert isinstance(view, NativeScriptingCapability)

    @staticmethod
    def test_unknown_capability_returns_none():
        class _Unknown:
            pass

        class _Client:
            redis_client = FakeRedisClient()
            subscriber_client = FakeRedisClient()
            blocking_client = FakeRedisClient()

        assert capability_view(_Client(), _Unknown) is None
        # native 实现类同样不是分发键（协议类才是）
        assert capability_view(_Client(), NativeBitmapCapability) is None
