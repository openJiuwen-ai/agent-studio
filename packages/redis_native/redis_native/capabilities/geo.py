# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""GeoCapability 实现（GEO 族）。

redis-py 8.x 签名差异（已逐一核对）：
  - geoadd 收**扁平序列** ``[lon, lat, member, ...]``（非旧版 varargs）；
  - geodist 的 unit 为 str（GeoUnit 枚举已约束合法值，DataError 不可达）；
  - geopos 返回 GeoCoordinate 双形态（tuple/list），契约要求 (lon, lat) 归一；
  - georadius(/bymember) 仍在（Redis 7 起服务端标注 deprecated，自研代理
    场景按白名单可用性决定；不支持时服务端报错 → RedisCommandError）。
"""

from __future__ import annotations

from typing import Any, Sequence

from redis_native.converters import condition_options
from redis_native.error_mapping import spi_command

from redis_spi.exceptions import RedisCommandError
from redis_spi.types import (
    GeoMember,
    GeoUnit,
    Key,
    SetCondition,
    Value,
)


class NativeGeoCapability:
    """地理空间能力组（redis-py 委托）。"""

    def __init__(self, redis) -> None:
        self._redis = redis

    @spi_command("geoadd")
    async def geoadd(
        self,
        key: Key,
        members: Sequence[GeoMember],
        *,
        condition: SetCondition | None = None,
    ) -> int:
        if not members:
            raise RedisCommandError("geoadd 需要至少一个 GeoMember", command="geoadd")
        # GeoMember 值对象 → redis-py 扁平序列（经纬度范围已在构造期校验）。
        values: list[Any] = []
        for member in members:
            values.extend((member.longitude, member.latitude, member.member))
        return await self._redis.geoadd(key, values, **condition_options(condition))

    @spi_command("geodist")
    async def geodist(
        self,
        key: Key,
        member1: Value,
        member2: Value,
        unit: GeoUnit = GeoUnit.M,
    ) -> float | None:
        return await self._redis.geodist(key, member1, member2, unit=unit.value)

    @spi_command("geopos")
    async def geopos(
        self, key: Key, *members: Value
    ) -> list[tuple[float, float] | None]:
        result = await self._redis.geopos(key, *members)
        return [_to_coord(item) for item in result]

    @spi_command("geohash")
    async def geohash(self, key: Key, *members: Value) -> list[Value | None]:
        return await self._redis.geohash(key, *members)

    @spi_command("georadius")
    async def georadius(
        self,
        key: Key,
        longitude: float,
        latitude: float,
        radius: float,
        unit: GeoUnit = GeoUnit.M,
        *,
        with_coord: bool = False,
        with_dist: bool = False,
        count: int | None = None,
    ) -> list[Any]:
        # 返回形态与 Redis 一致（契约口径），坐标/距离元素由服务端回调装配。
        return await self._redis.georadius(
            key,
            longitude,
            latitude,
            radius,
            unit=unit.value,
            withdist=with_dist,
            withcoord=with_coord,
            count=count,
        )

    @spi_command("georadiusbymember")
    async def georadiusbymember(
        self,
        key: Key,
        member: Value,
        radius: float,
        unit: GeoUnit = GeoUnit.M,
        *,
        with_coord: bool = False,
        with_dist: bool = False,
        count: int | None = None,
    ) -> list[Any]:
        return await self._redis.georadiusbymember(
            key,
            member,
            radius,
            unit=unit.value,
            withdist=with_dist,
            withcoord=with_coord,
            count=count,
        )


def _to_coord(item: Any) -> tuple[float, float] | None:
    """GEOPOS 元素归一：GeoCoordinate 双形态（tuple/list）→ (lon, lat)。"""
    if item is None:
        return None
    return (float(item[0]), float(item[1]))
