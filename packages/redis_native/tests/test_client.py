# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""NativeRedisClient 单测：核心面委托翻译 + 生命周期/能力探测/pipeline。"""

from __future__ import annotations

import asyncio

import pytest
import redis.exceptions as redis_exc

from redis_native.client import NativeRedisClient
from redis_native.pipeline import NativePipeline

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
from redis_spi.exceptions import (
    CapabilityNotSupportedError,
    RedisCommandError,
    RedisConnectionError,
    RedisTimeoutError,
)
from redis_spi.types import Duration, ScanBatch, SetCondition

from redis_native_test_fakes import FakePipeline, FakeRedisClient


def make_client(results=None, exceptions=None, **kwargs):
    fake = FakeRedisClient(results=results, exceptions=exceptions)
    client = NativeRedisClient(fake, **kwargs)
    return client, fake


class TestStringCommands:
    @staticmethod
    def test_set_returns_ok_bytes():
        client, fake = make_client(results={"set": True})
        assert asyncio.run(client.set("k", b"v")) == b"OK"
        assert fake.calls == [("set", ("k", b"v"), {})]

    @staticmethod
    def test_set_text_mode_returns_ok_str():
        client, _ = make_client(results={"set": True}, text_mode=True)
        assert asyncio.run(client.set("k", "v")) == "OK"

    @staticmethod
    def test_set_condition_miss_returns_none():
        client, fake = make_client(results={"set": None})
        assert asyncio.run(client.set("k", b"v", condition=SetCondition.NX)) is None
        assert fake.calls[0][2] == {"nx": True}

    @staticmethod
    def test_set_condition_and_duration_translated():
        client, fake = make_client(results={"set": True})
        asyncio.run(
            client.set(
                "k", b"v", condition=SetCondition.XX, duration=Duration.milliseconds(1500)
            )
        )
        assert fake.calls[0][2] == {"xx": True, "px": 1500}

    @staticmethod
    def test_set_ttl_conflict_rejected_before_delegate():
        client, fake = make_client(results={"set": True})
        with pytest.raises(RedisCommandError, match="互斥"):
            asyncio.run(
                client.set("k", b"v", duration=Duration.seconds(5), keep_ttl=True)
            )
        assert fake.calls == []

    @staticmethod
    def test_setrange_negative_offset_rejected():
        client, fake = make_client()
        with pytest.raises(RedisCommandError, match="offset"):
            asyncio.run(client.setrange("k", -1, b"v"))
        assert fake.calls == []

    @staticmethod
    def test_get_passthrough():
        client, fake = make_client(results={"get": b"v"})
        assert asyncio.run(client.get("k")) == b"v"
        assert fake.calls == [("get", ("k",), {})]


class TestKeyCommands:
    @staticmethod
    def test_expire_ceil_to_seconds():
        client, fake = make_client(results={"expire": True})
        assert asyncio.run(client.expire("k", Duration.milliseconds(1500))) is True
        assert fake.calls == [("expire", ("k", 2), {})]

    @staticmethod
    def test_pexpire_keeps_milliseconds():
        client, fake = make_client(results={"pexpire": True})
        asyncio.run(client.pexpire("k", Duration.milliseconds(1500)))
        assert fake.calls == [("pexpire", ("k", 1500), {})]

    @staticmethod
    def test_expire_at_seconds_passthrough():
        client, fake = make_client(results={"expireat": True})
        asyncio.run(client.expire_at("k", 1700000000))
        assert fake.calls == [("expireat", ("k", 1700000000), {})]

    @staticmethod
    def test_pexpire_at_milliseconds_passthrough():
        client, fake = make_client(results={"pexpireat": True})
        asyncio.run(client.pexpire_at("k", 1700000000000))
        assert fake.calls == [("pexpireat", ("k", 1700000000000), {})]

    @staticmethod
    def test_exists_empty_rejected():
        client, fake = make_client()
        with pytest.raises(RedisCommandError, match="至少一个 key"):
            asyncio.run(client.exists())
        assert fake.calls == []

    @staticmethod
    def test_key_type():
        client, _ = make_client(results={"type": b"hash"})
        assert asyncio.run(client.key_type("k")) == b"hash"


class TestScanCommands:
    @staticmethod
    def test_scan_type_param_mapped():
        client, fake = make_client(results={"scan": (0, [b"a", b"b"])})
        batch = asyncio.run(
            client.scan(7, match=b"u:*", count=10, type_name=b"string")
        )
        assert isinstance(batch, ScanBatch)
        assert batch.cursor == 0
        assert batch.items == (b"a", b"b")
        name, args, kwargs = fake.calls[0]
        assert name == "scan"
        assert args == (7,)
        assert kwargs == {"match": b"u:*", "count": 10, "_type": b"string"}

    @staticmethod
    def test_scan_iter_delegates_and_iterates():
        client, fake = make_client(results={"scan_iter_items": [b"a", b"b"]})

        async def run():
            return [key async for key in client.scan_iter(match=b"u:*", count=100)]

        assert asyncio.run(run()) == [b"a", b"b"]
        assert fake.calls[-1] == ("scan_iter", (), {"match": b"u:*", "count": 100})


class TestHashCommands:
    @staticmethod
    def test_hset_mapping_path():
        client, fake = make_client(results={"hset": 1})
        assert asyncio.run(client.hset("k", {"f": b"v"})) == 1
        assert fake.calls == [("hset", ("k",), {"mapping": {"f": b"v"}, "key": None, "value": None})]

    @staticmethod
    def test_hset_field_value_path():
        client, fake = make_client(results={"hset": 1})
        asyncio.run(client.hset("k", field="f", value=b"v"))
        assert fake.calls == [("hset", ("k",), {"mapping": None, "key": "f", "value": b"v"})]

    @pytest.mark.parametrize("mapping,field,value", [
        ({"f": b"v"}, "f2", b"v2"),  # 同给
        (None, None, None),  # 均空
    ])
    def test_hset_rejected(self, mapping, field, value):
        client, fake = make_client()
        with pytest.raises(RedisCommandError):
            asyncio.run(client.hset("k", mapping, field=field, value=value))
        assert fake.calls == []

    @staticmethod
    def test_hscan_list_payload_normalized():
        client, _ = make_client(
            results={"hscan": (0, [b"f1", b"v1", b"f2", b"v2"])}
        )
        cursor, mapping = asyncio.run(client.hscan("k"))
        assert cursor == 0
        assert mapping == {b"f1": b"v1", b"f2": b"v2"}

    @staticmethod
    def test_hscan_dict_payload_passthrough():
        payload = {b"f": b"v"}
        client, _ = make_client(results={"hscan": (0, payload)})
        _, mapping = asyncio.run(client.hscan("k"))
        assert mapping == payload


class TestListCommands:
    @staticmethod
    def test_rpush_empty_rejected():
        client, fake = make_client()
        with pytest.raises(RedisCommandError, match="至少一个 value"):
            asyncio.run(client.rpush("k"))
        assert fake.calls == []

    @staticmethod
    def test_lpop_passthrough():
        client, _ = make_client(results={"lpop": b"x"})
        assert asyncio.run(client.lpop("k")) == b"x"


class TestSetCommands:
    @staticmethod
    def test_sadd_empty_rejected():
        client, fake = make_client()
        with pytest.raises(RedisCommandError, match="至少一个 member"):
            asyncio.run(client.sadd("k"))
        assert fake.calls == []

    @staticmethod
    def test_sinter_empty_rejected():
        client, fake = make_client()
        with pytest.raises(RedisCommandError, match="至少一个 key"):
            asyncio.run(client.sinter())
        assert fake.calls == []

    @staticmethod
    def test_spop_set_passthrough():
        client, _ = make_client(results={"spop": {b"a", b"b"}})
        assert asyncio.run(client.spop("k", 2)) == {b"a", b"b"}


class TestLifecycle:
    @staticmethod
    def test_ping_true():
        client, _ = make_client(results={"ping": True})
        assert asyncio.run(client.ping()) is True

    @staticmethod
    def test_ping_timeout_translated_result_known():
        client, _ = make_client(
            exceptions={"ping": redis_exc.TimeoutError("t/o")}
        )
        with pytest.raises(RedisTimeoutError) as excinfo:
            asyncio.run(client.ping())
        # ping 幂等：超时结果可知（可重试）
        assert excinfo.value.result_known is True

    @staticmethod
    def test_ping_connection_translated():
        client, _ = make_client(
            exceptions={"ping": redis_exc.ConnectionError("refused")}
        )
        with pytest.raises(RedisConnectionError):
            asyncio.run(client.ping())

    @staticmethod
    def test_aclose_dedupes_shared_clients():
        fake = FakeRedisClient()
        client = NativeRedisClient(fake)  # subscriber/blocking 回退主池
        asyncio.run(client.aclose())
        asyncio.run(client.aclose())  # 幂等
        closes = [c for c in fake.calls if c[0] == "aclose"]
        assert len(closes) == 1

    @staticmethod
    def test_aclose_closes_each_underlying_once():
        main = FakeRedisClient()
        subscriber = FakeRedisClient()
        blocking = FakeRedisClient()
        client = NativeRedisClient(
            main, subscriber=subscriber, blocking=blocking
        )
        asyncio.run(client.aclose())
        for fake in (main, subscriber, blocking):
            closes = [c for c in fake.calls if c[0] == "aclose"]
            assert len(closes) == 1


class TestCapabilityDispatch:
    ALL_CAPABILITIES = [
        BitmapCapability,
        BlockingCommands,
        CounterCapability,
        GeoCapability,
        HyperLogLogCapability,
        PubSubCapability,
        ScriptingCapability,
        SortedSetCapability,
    ]

    def test_supports_all_eight(self):
        client, _ = make_client()
        assert all(client.supports(cap) for cap in self.ALL_CAPABILITIES)

    @staticmethod
    def test_as_capability_unknown_rejected():
        client, _ = make_client()
        with pytest.raises(CapabilityNotSupportedError):
            client.as_capability(dict)

    @staticmethod
    def test_views_bound_to_matching_pools():
        main = FakeRedisClient()
        subscriber = FakeRedisClient()
        blocking = FakeRedisClient()
        client = NativeRedisClient(
            main, subscriber=subscriber, blocking=blocking
        )

        asyncio.run(client.as_capability(CounterCapability).incr("c"))
        assert [c[0] for c in main.calls] == ["incr"]

        client.as_capability(PubSubCapability).pubsub()
        assert [c[0] for c in subscriber.calls] == ["pubsub"]
        assert main.calls[-1][0] == "incr"  # publish 未经调用

        asyncio.run(client.as_capability(BlockingCommands).blpop(["k"]))
        assert [c[0] for c in blocking.calls] == ["blpop"]

    @staticmethod
    def test_views_fall_back_to_main_when_shared():
        # cluster 共享主池形态：subscriber/blocking 为 None → 回退主池
        main = FakeRedisClient()
        main.pubsub_obj = FakeRedisClient()
        client = NativeRedisClient(main)
        client.as_capability(PubSubCapability).pubsub()
        asyncio.run(client.as_capability(BlockingCommands).blpop(["k"]))
        names = [c[0] for c in main.calls]
        assert "pubsub" in names and "blpop" in names

    @staticmethod
    def test_native_client_view():
        fake = FakeRedisClient()
        client = NativeRedisClient(fake)
        assert client.native_client() is fake

    @staticmethod
    def test_text_mode_property():
        assert NativeRedisClient(FakeRedisClient(), text_mode=True).text_mode is True


class TestPipeline:
    @staticmethod
    def test_transaction_default_resolution():
        fake = FakeRedisClient()
        client = NativeRedisClient(fake)
        client.pipeline()
        assert fake.calls[0][2]["transaction"] is True
        client.pipeline(transaction=False)
        assert fake.calls[1][2]["transaction"] is False

    @staticmethod
    def test_transaction_default_from_constructor():
        fake = FakeRedisClient()
        NativeRedisClient(fake, transaction_default=False).pipeline()
        assert fake.calls[0][2]["transaction"] is False

    @staticmethod
    def test_enqueue_chain_and_execute():
        outer = FakeRedisClient()
        inner = FakePipeline(results={"execute": [b"OK", 2]})
        outer.pipeline_obj = inner
        client = NativeRedisClient(outer)

        pipe = client.pipeline()
        returned = (
            pipe.get("a")
            .set("b", b"2", duration=Duration.milliseconds(1500))
            .expire("c", Duration.milliseconds(999))
        )
        assert returned is pipe  # 链式
        assert asyncio.run(pipe.execute()) == [b"OK", 2]
        assert inner.calls == [
            ("get", ("a",), {}),
            ("set", ("b", b"2"), {"px": 1500}),
            ("expire", ("c", 1), {}),  # 999ms → ceil 1s
            ("execute", (), {}),
        ]

    @staticmethod
    def test_hset_validation_fails_at_enqueue():
        outer = FakeRedisClient()
        inner = FakePipeline()
        outer.pipeline_obj = inner
        pipe = NativeRedisClient(outer).pipeline()
        with pytest.raises(RedisCommandError):
            pipe.hset("k", {"f": b"v"}, field="f2", value=b"v2")
        assert inner.calls == []

    @staticmethod
    def test_execute_error_translated():
        outer = FakeRedisClient()
        inner = FakePipeline(
            exceptions={"execute": redis_exc.ResponseError("ERR bad")}
        )
        outer.pipeline_obj = inner
        pipe = NativeRedisClient(outer).pipeline()
        with pytest.raises(RedisCommandError, match="ERR bad"):
            asyncio.run(pipe.execute())

    @staticmethod
    def test_aclose_delegates():
        outer = FakeRedisClient()
        inner = FakePipeline()
        outer.pipeline_obj = inner
        pipe = NativeRedisClient(outer).pipeline()
        asyncio.run(pipe.aclose())
        assert [c[0] for c in inner.calls] == ["aclose"]

    @staticmethod
    def test_pipeline_type():
        outer = FakeRedisClient()
        pipe = NativeRedisClient(outer).pipeline()
        assert isinstance(pipe, NativePipeline)
