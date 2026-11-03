# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""可选能力组协议（Provider 按声明实现；未声明组对应命令可不实现）。

分层规则（设计文档 2.6/4.3/4.5）：
  - 核心组（protocols.py）必选；本模块各组**按 Provider 声明**实现；
  - 调用方调用可选能力前应先 ``client.supports(XxxCapability)`` 探测；
    未探测直接调用收到 CapabilityNotSupportedError（错误而非静默）；
  - 契约套件（redis_contract_tests）按声明的能力矩阵跑批：声明的组必须通过，
    未声明的组自动 skip；
  - 各组契约总则与 protocols.py 相同（值类型/异常体系/集群同槽/原子性），
    逐方法只写差异项。

连接池约定（设计文档 4.3）：
  - PubSub 订阅连接走**独立连接池**（subscriber_pool_size，默认 1）——
    长期占用不侵蚀业务命令池；
  - 阻塞命令（BLPOP/BRPOP/BRPOPLPUSH）走**独立连接池**（blocking_pool_size，
    默认 2）——阻塞期间不占用业务池；
  - 其余能力组共用业务命令池。
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol, Sequence, runtime_checkable

from redis_spi.types import (
    SCAN_START,
    Duration,
    GeoMember,
    GeoUnit,
    Key,
    PubSubMessage,
    ScanCursor,
    ScoreBoundary,
    SetCondition,
    Value,
)


@runtime_checkable
class CounterCapability(Protocol):
    """计数器能力组（INCR/DECR 族）。"""

    async def incr(self, key: Key, amount: int = 1) -> int:
        """INCR/INCRBY（amount 默认 1）：整数自增，返回增量后的值。

        值非整数或溢出抛 RedisCommandError。**超时结果未知**：实现须以
        RedisTimeoutError(result_known=False) 标注，禁止调用方盲重试。
        """
        ...

    async def incr_by_float(self, key: Key, amount: float) -> float:
        """INCRBYFLOAT：浮点自增，返回增量后的值。result_known 契约同 incr。"""
        ...

    async def decr(self, key: Key, amount: int = 1) -> int:
        """DECR/DECRBY（amount 默认 1）：整数自减，返回减量后的值。"""
        ...


@runtime_checkable
class SortedSetCapability(Protocol):
    """有序集合能力组（ZSET 族）。"""

    async def zadd(
        self,
        key: Key,
        mapping: dict[Value, float],
        *,
        condition: SetCondition | None = None,
    ) -> int:
        """ZADD：member→score 批量写入。返回新增 member 个数。

        condition=NX：只新增已存在的跳过；XX：只更新已存在的（新增全跳过）。
        """
        ...

    async def zrem(self, key: Key, *members: Value) -> int:
        """ZREM：返回实际删除的 member 个数。"""
        ...

    async def zscore(self, key: Key, member: Value) -> float | None:
        """ZSCORE：member 的 score；缺失返回 None。"""
        ...

    async def zcard(self, key: Key) -> int:
        """ZCARD：member 数；key 缺失返回 0。"""
        ...

    async def zrank(self, key: Key, member: Value) -> int | None:
        """ZRANK：按 score 升序的排名（0 起）；member 缺失返回 None。"""
        ...

    async def zrevrank(self, key: Key, member: Value) -> int | None:
        """ZREVRANK：降序排名（0 起）；member 缺失返回 None。"""
        ...

    async def zincrby(self, key: Key, amount: float, member: Value) -> float:
        """ZINCRBY：member score 增量，返回增量后的 score。"""
        ...

    async def zcount(self, key: Key, min_value, max_value) -> int:
        """ZCOUNT：闭区间 [min, max] 内的 member 数（开区间用 "(5" 形态）。"""
        ...

    async def zlexcount(self, key: Key, min_value, max_value) -> int:
        """ZLEXCOUNT：按字典序计数（要求全部 member 同 score）；边界用 "["/"(" 前缀。"""
        ...

    async def zrange(
        self,
        key: Key,
        start: int,
        stop: int,
        *,
        withscores: bool = False,
        desc: bool = False,
    ) -> list[Value] | list[tuple[Value, float]]:
        """ZRANGE/ZREVRANGE：按排名区间取 member（含负索引；0 -1 = 全量）。

        withscores=True 返回 (member, score) 元组列表。desc=True 等价 ZREVRANGE。
        """
        ...

    async def zrangebyscore(
        self,
        key: Key,
        min_value,
        max_value,
        *,
        withscores: bool = False,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Value] | list[tuple[Value, float]]:
        """ZRANGEBYSCORE：按 score 闭区间取 member（升序），支持分页。

        limit 给定时按 (offset, limit) 分页；offset 缺省 0——limit 单给即取
        前 limit 个。withscores=True 返回 (member, score) 元组列表。
        """
        ...

    async def zrangebylex(
        self,
        key: Key,
        min_value,
        max_value,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Value]:
        """ZRANGEBYLEX：按字典序取 member（要求全部 member 同 score）。边界用 "["/"("。"""
        ...

    async def zremrangebyrank(self, key: Key, start: int, stop: int) -> int:
        """ZREMRANGEBYRANK：按排名区间删除，返回删除数。"""
        ...

    async def zremrangebyscore(self, key: Key, min_value, max_value) -> int:
        """ZREMRANGEBYSCORE：按 score 区间删除，返回删除数。"""
        ...

    async def zremrangebylex(self, key: Key, min_value, max_value) -> int:
        """ZREMRANGEBYLEX：按字典序区间删除，返回删除数。"""
        ...

    async def zunionstore(
        self,
        destination: Key,
        keys: Sequence[Key],
        *,
        aggregate: str | None = None,
    ) -> int:
        """ZUNIONSTORE：并集写入 destination，返回结果 member 数。

        aggregate ∈ {"SUM","MIN","MAX"}（默认 SUM）；非法值抛 RedisCommandError。
        集群：destination 与全部 source 须同槽。
        """
        ...

    async def zinterstore(
        self,
        destination: Key,
        keys: Sequence[Key],
        *,
        aggregate: str | None = None,
    ) -> int:
        """ZINTERSTORE：交集写入 destination。约束同 zunionstore。集群：同槽。"""
        ...

    async def zscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, list[tuple[Value, float]]]:
        """ZSCAN：返回 (下一游标, 本批 (member, score))。弱一致语义同 SCAN。"""
        ...


@runtime_checkable
class BitmapCapability(Protocol):
    """位图能力组。"""

    async def setbit(self, key: Key, offset: int, value: int) -> int:
        """SETBIT：置位，返回原位值（0/1）。offset < 0 或 value 非 0/1 抛 RedisCommandError。"""
        ...

    async def getbit(self, key: Key, offset: int) -> int:
        """GETBIT：返回位值（超界返回 0）。"""
        ...

    async def bitcount(self, key: Key, start: int | None = None, end: int | None = None) -> int:
        """BITCOUNT：置位个数；start/end 给定时按**字节**区间统计（须成对）。"""
        ...

    async def bitpos(self, key: Key, bit: int, start: int | None = None, end: int | None = None) -> int:
        """BITPOS：首个 bit（0/1）的字节偏移；不存在返回 -1。bit 非 0/1 抛 RedisCommandError。"""
        ...

    async def bitop(self, operation: str, destination: Key, *keys: Key) -> int:
        """BITOP AND/OR/XOR/NOT：位运算写入 destination，返回结果字节长度。

        NOT 仅允许 1 个 source key；非法 operation 抛 RedisCommandError。集群：同槽。
        """
        ...


@runtime_checkable
class HyperLogLogCapability(Protocol):
    """HyperLogLog 能力组（基数估计，标准误 ~0.81%）。"""

    async def pfadd(self, key: Key, *elements: Value) -> int:
        """PFADD：返回 1 = 基数估计变化，0 = 无变化。空 elements 抛 RedisCommandError。"""
        ...

    async def pfcount(self, *keys: Key) -> int:
        """PFCOUNT：基数估计并集值。空参抛 RedisCommandError。集群：同槽。"""
        ...

    async def pfmerge(self, destination: Key, *source_keys: Key) -> bool:
        """PFMERGE：多 HLL 并入 destination，成功返回 True。集群：同槽。"""
        ...


@runtime_checkable
class GeoCapability(Protocol):
    """地理空间能力组。"""

    async def geoadd(
        self,
        key: Key,
        members: Sequence[GeoMember],
        *,
        condition: SetCondition | None = None,
    ) -> int:
        """GEOADD：批量写入 (经度, 纬度, member)，返回新增个数。

        前置条件：经纬度范围校验在 GeoMember 构造期完成；condition 语义同 zadd。
        """
        ...

    async def geodist(
        self,
        key: Key,
        member1: Value,
        member2: Value,
        unit: GeoUnit = GeoUnit.M,
    ) -> float | None:
        """GEODIST：两 member 距离；任一 member 缺失返回 None。"""
        ...

    async def geopos(self, key: Key, *members: Value) -> list[tuple[float, float] | None]:
        """GEOPOS：按 member 顺序返回 (经度, 纬度)；缺失位置为 None。"""
        ...

    async def geohash(self, key: Key, *members: Value) -> list[Value | None]:
        """GEOHASH：按 member 顺序返回 geohash 字符串（text_mode 语义同值规则）。"""
        ...

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
        """GEORADIUS：以 (经度, 纬度) 为中心查询。返回 member 列表；

        with_coord/with_dist=True 时元素为 [member, (lon, lat)] / [member, dist] /
        [member, dist, (lon, lat)] 组合形态（与 Redis 一致）。
        """
        ...

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
        """GEORADIUSBYMEMBER：以既有 member 为中心查询。返回形态同 georadius。

        member 缺失返回空列表。
        """
        ...


@runtime_checkable
class ScriptingCapability(Protocol):
    """脚本能力组（Lua）。"""

    async def eval(
        self,
        script: str,
        keys: Sequence[Key],
        args: Sequence[Value] = (),
    ) -> Any:
        """EVAL：执行 Lua 脚本，返回脚本返回值（按 Redis 类型映射）。

        脚本运行时错误抛 RedisScriptError（command="eval"，detail 含 Lua 报错）；
        keys 须同槽（集群）。
        """
        ...

    async def evalsha(
        self,
        sha1: str,
        keys: Sequence[Key],
        args: Sequence[Value] = (),
    ) -> Any:
        """EVALSHA：按 sha1 执行已缓存脚本；未缓存抛 RedisScriptError（NOSCRIPT）。"""
        ...

    async def script_load(self, script: str) -> str:
        """SCRIPT LOAD：缓存脚本，返回 sha1 十六进制串。"""
        ...

    async def script_exists(self, *sha1: str) -> list[bool]:
        """SCRIPT EXISTS：按 sha1 顺序返回是否已缓存。"""
        ...


class PubSubHandle(Protocol):
    """PubSub 订阅句柄（pubsub() 产出；独立订阅连接池，与业务命令池隔离）。

    契约：
      - 独立生命周期：句柄随自身 aclose() 关闭（不随主客户端 aclose 关闭时，
        主客户端 aclose 应级联关闭其产出的全部句柄——实现须二选一并声明）；
      - listen() 为 async iterator，产出 PubSubMessage（含 subscribe 确认消息）；
      - 未订阅任何频道/模式时 listen() 不产出业务消息（实现可自旋保活或阻塞等订阅）；
      - 句柄非协程安全：单协程消费。
    """

    async def subscribe(self, *channels: Value) -> None:
        """订阅指定频道（空参抛 RedisCommandError）。"""
        ...

    async def psubscribe(self, *patterns: Value) -> None:
        """按 glob 模式订阅。空参抛 RedisCommandError。"""
        ...

    def listen(self) -> AsyncIterator[PubSubMessage]:
        """消息迭代器：``async for msg in handle.listen(): ...``。"""
        ...

    async def unsubscribe(self, *channels: Value) -> None:
        """退订频道；空参 = 退订全部频道。"""
        ...

    async def punsubscribe(self, *patterns: Value) -> None:
        """退订模式；空参 = 退订全部模式。"""
        ...

    async def aclose(self) -> None:
        """关闭句柄（释放订阅连接）。幂等。"""
        ...


@runtime_checkable
class PubSubCapability(Protocol):
    """PubSub 能力组（订阅走独立连接池）。"""

    def pubsub(self) -> PubSubHandle:
        """创建订阅句柄（独立订阅连接池，不占用业务命令池）。"""
        ...

    async def publish(self, channel: Value, message: Value) -> int:
        """PUBLISH：发布消息，返回接收该消息的订阅端个数。"""
        ...


@runtime_checkable
class BlockingCommands(Protocol):
    """阻塞命令能力组（独立阻塞连接池，不占用业务命令池）。"""

    async def blpop(self, keys: Sequence[Key], timeout: Duration | None = None) -> tuple[Key, Value] | None:
        """BLPOP：阻塞弹头。返回 (key, value)；超时返回 None（timeout=None = 无限阻塞，慎用）。

        集群：keys 须同槽。
        """
        ...

    async def brpop(self, keys: Sequence[Key], timeout: Duration | None = None) -> tuple[Key, Value] | None:
        """BRPOP：阻塞弹尾。返回语义同 blpop。"""
        ...

    async def brpoplpush(
        self,
        source: Key,
        destination: Key,
        timeout: Duration | None = None,
    ) -> Value | None:
        """BRPOPLPUSH：阻塞版 rpoplpush。超时返回 None。集群：同槽。"""
        ...
