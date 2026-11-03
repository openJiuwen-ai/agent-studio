# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""types.py 值对象契约测试。"""

import pytest

from redis_spi.types import (
    Duration,
    GeoMember,
    GeoUnit,
    ScanBatch,
    SetCondition,
)

TEST_CASE = "redis_spi/types"


class TestDuration:
    @staticmethod
    def test_seconds_to_milliseconds():
        assert Duration.seconds(30).milliseconds == 30000

    @staticmethod
    def test_half_second():
        assert Duration.seconds(0.5).milliseconds == 500

    @staticmethod
    def test_sub_millisecond_rounds_up():
        # 0.5ms 向上取整为 1ms：避免正 TTL 被截断为 0
        assert Duration.seconds(0.0005).milliseconds == 1

    @pytest.mark.parametrize("bad", [-1, 0, -0.0005])
    def test_seconds_non_positive_rejected(self, bad):
        # 含亚毫秒级负数：禁止 ceil 后翻成正时长
        with pytest.raises(ValueError):
            Duration.seconds(bad)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_seconds_non_finite_rejected(self, bad):
        with pytest.raises(ValueError):
            Duration.seconds(bad)

    @staticmethod
    def test_milliseconds_factory():
        assert Duration.milliseconds(500).milliseconds == 500

    @staticmethod
    def test_zero_rejected():
        with pytest.raises(ValueError):
            Duration(milliseconds=0)

    @staticmethod
    def test_negative_rejected():
        with pytest.raises(ValueError):
            Duration(milliseconds=-5)

    @pytest.mark.parametrize("bad", [True, "100", 1.5, None])
    def test_non_int_rejected(self, bad):
        with pytest.raises(TypeError):
            Duration(milliseconds=bad)

    @staticmethod
    def test_frozen():
        duration = Duration.seconds(10)
        with pytest.raises(Exception):
            duration.milliseconds = 20  # type: ignore[misc]

    @staticmethod
    def test_str_for_logging():
        assert str(Duration.seconds(2)) == "2000ms"


class TestScanBatch:
    @staticmethod
    def test_freezes_items_to_tuple():
        batch = ScanBatch(cursor=0, items=["a", "b"])
        assert batch.items == ("a", "b")
        assert isinstance(batch.items, tuple)

    @staticmethod
    def test_negative_cursor_rejected():
        with pytest.raises(ValueError):
            ScanBatch(cursor=-1, items=())


class TestGeoMember:
    @staticmethod
    def test_valid():
        member = GeoMember(longitude=116.4, latitude=39.9, member="beijing")
        assert member.member == "beijing"

    @staticmethod
    def test_longitude_out_of_range():
        with pytest.raises(ValueError):
            GeoMember(longitude=200.0, latitude=0.0, member="x")

    @staticmethod
    def test_latitude_out_of_range():
        with pytest.raises(ValueError):
            GeoMember(longitude=0.0, latitude=-91.0, member="x")


class TestEnums:
    @staticmethod
    def test_set_condition_values():
        assert SetCondition.NX.value == "nx"
        assert SetCondition.XX.value == "xx"

    @staticmethod
    def test_geo_units():
        assert {unit.value for unit in GeoUnit} == {"m", "km", "ft", "mi"}
