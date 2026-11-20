# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""核心能力协议（必选面——任何 Provider 必须完整实现并通过契约套件）。

契约总则（对全部方法生效；逐方法 docstring 只写该方法差异项）：
  1. 语义与 Redis 原生命令对齐（nos 兼容口径，见设计文档 4.5 映射表）；
  2. Key/Value 为 ``str | bytes``（str 按 UTF-8 编码）；返回值默认 bytes，
     ``text_mode`` 视图返回 str；同一客户端两种模式不得混用（构造期固化）；
  3. 前置条件：key/field/member 非 None；数值参数按 Redis 语义取值；
  4. 错误：全部以 redis_spi.exceptions 体系抛出，实现不得外抛底层客户端异常
     （连接失败→RedisConnectionError；超时→RedisTimeoutError；参数/类型错→
     RedisCommandError/RedisWrongTypeError；未实现→CapabilityNotSupportedError）；
  5. 并发：客户端可被多协程并发使用（内部连接池）；绑定启动期 event loop，
     跨 loop 使用应显式报错而非静默错乱；
  6. 集群：多 key 命令的同槽（same-slot）要求逐方法标注；hash-tag 规划由调用方
     负责；实现不支持跨槽时抛 RedisClusterError，不得静默丢弃或错写；
  7. 原子性：单命令原子；未标注"非原子"的方法均要求原子语义；实现若把某方法
     拆解为多条底层命令，必须在该实现文档中声明。

能力分层（设计文档 2.6/4.5）：核心（本模块）∪ 可选能力组（capabilities.py）
并集 = nos 全命令面；框架自身业务路径仅依赖核心 + PubSub + Blocking。
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from redis_spi.types import (
    SCAN_START,
    Duration,
    Key,
    ScanBatch,
    ScanCursor,
    SetCondition,
    Value,
)


class KeyCommands(Protocol):
    """Key 级命令（核心必选）。"""

    async def exists(self, *keys: Key) -> int:
        """EXISTS：返回存在的 key 个数。空参抛 RedisCommandError。"""
        ...

    async def delete(self, *keys: Key) -> int:
        """DEL：返回实际删除的 key 个数（不存在不计数）。原子。"""
        ...

    async def key_type(self, key: Key) -> Value:
        """TYPE：返回 b"string"/b"list"/b"set"/b"zset"/b"hash"/b"none"（缺失）。"""
        ...

    async def expire(self, key: Key, duration: Duration) -> bool:
        """EXPIRE：设置 TTL。返回是否生效（key 不存在返回 False）。"""
        ...

    async def pexpire(self, key: Key, duration: Duration) -> bool:
        """PEXPIRE：以毫秒级 Duration 设置 TTL。语义同 expire。"""
        ...

    async def expire_at(self, key: Key, unix_seconds: int) -> bool:
        """EXPIREAT：以 Unix 秒级时间戳设置过期点。"""
        ...

    async def pexpire_at(self, key: Key, unix_milliseconds: int) -> bool:
        """PEXPIREAT：以 Unix 毫秒级时间戳设置过期点。"""
        ...

    async def ttl(self, key: Key) -> int:
        """TTL（秒）：-1 = 永久，-2 = key 不存在。"""
        ...

    async def pttl(self, key: Key) -> int:
        """PTTL（毫秒）：哨兵语义同 ttl。"""
        ...

    async def persist(self, key: Key) -> bool:
        """PERSIST：移除 TTL 转永久。返回是否生效。"""
        ...


class StringCommands(Protocol):
    """String 命令（核心必选）。"""

    async def get(self, key: Key) -> Value | None:
        """GET：缺失返回 None。"""
        ...

    async def set(
        self,
        key: Key,
        value: Value,
        *,
        condition: SetCondition | None = None,
        duration: Duration | None = None,
        keep_ttl: bool = False,
    ) -> Value | None:
        """SET：成功返回 b"OK"（text_mode 为 "OK"）；condition 不满足返回 None。

        - duration 与 keep_ttl 互斥，同时设置抛 RedisCommandError；
        - keep_ttl=True 等价 KEEPTTL（保留既有 TTL）；
        - condition=NX 的 set 是框架侧推荐的分布式锁原语。
        """
        ...

    async def get_set(self, key: Key, value: Value) -> Value | None:
        """GETSET：返回旧值（缺失为 None）。原子。"""
        ...

    async def mget(self, keys: list[Key]) -> list[Value | None]:
        """MGET：按入参顺序返回；缺失位置为 None。集群：所有 key 须同槽。"""
        ...

    async def mset(self, mapping: dict[Key, Value]) -> None:
        """MSET：批量写入，整体原子。集群：所有 key 须同槽。"""
        ...

    async def msetnx(self, mapping: dict[Key, Value]) -> bool:
        """MSETNX：任一 key 已存在则全部不写，返回 False。原子。集群：同槽。"""
        ...

    async def append(self, key: Key, value: Value) -> int:
        """APPEND：追加，返回追加后的总长度。"""
        ...

    async def strlen(self, key: Key) -> int:
        """STRLEN：value 字节长度；缺失返回 0。"""
        ...

    async def getrange(self, key: Key, start: int, end: int) -> Value:
        """GETRANGE：闭区间字节切片（含负索引语义）；缺失/空返回 b""。"""
        ...

    async def setrange(self, key: Key, offset: int, value: Value) -> int:
        """SETRANGE：从 offset 覆写；返回修改后的总长度。offset < 0 报错。"""
        ...


class HashCommands(Protocol):
    """Hash 命令（核心必选）。"""

    async def hset(
        self,
        key: Key,
        mapping: dict[Value, Value] | None = None,
        *,
        field: Value | None = None,
        value: Value | None = None,
    ) -> int:
        """HSET：field/value 与 mapping 二选一（均空或同给抛 RedisCommandError）。

        返回新建 field 个数（已存在 field 覆盖不计）。
        """
        ...

    async def hsetnx(self, key: Key, field: Value, value: Value) -> bool:
        """HSETNX：field 不存在才写入。原子。"""
        ...

    async def hget(self, key: Key, field: Value) -> Value | None:
        """HGET：field 缺失返回 None。"""
        ...

    async def hgetall(self, key: Key) -> dict[Value, Value]:
        """HGETALL：整 hash；key 缺失返回空 dict。大 hash 慎用（建议 hscan）。"""
        ...

    async def hmget(self, key: Key, fields: list[Value]) -> list[Value | None]:
        """HMGET：按 field 顺序返回；缺失位置为 None。"""
        ...

    async def hdel(self, key: Key, *fields: Value) -> int:
        """HDEL：返回实际删除的 field 个数。"""
        ...

    async def hexists(self, key: Key, field: Value) -> bool:
        """HEXISTS。"""
        ...

    async def hlen(self, key: Key) -> int:
        """HLEN：field 数；key 缺失返回 0。"""
        ...

    async def hkeys(self, key: Key) -> list[Value]:
        """HKEYS：全部 field。大 hash 慎用（建议 hscan）。"""
        ...

    async def hvals(self, key: Key) -> list[Value]:
        """HVALS：全部 value。大 hash 慎用。"""
        ...

    async def hincr_by(self, key: Key, field: Value, amount: int) -> int:
        """HINCRBY：整数自增（amount 可为负），返回增量后的值。field 非整数报错。"""
        ...

    async def hincr_by_float(self, key: Key, field: Value, amount: float) -> float:
        """HINCRBYFLOAT：浮点自增，返回增量后的值。"""
        ...

    async def hscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, dict[Value, Value]]:
        """HSCAN：返回 (下一游标, 本批 field→value)。游标回到 SCAN_START 即遍历结束。

        弱一致语义同 SCAN（可能重复/漏返），count 仅为提示值。
        """
        ...


class ListCommands(Protocol):
    """List 命令（核心必选）。"""

    async def rpush(self, key: Key, *values: Value) -> int:
        """RPUSH：尾部追加，返回追加后的长度。空 values 抛 RedisCommandError。"""
        ...

    async def lpush(self, key: Key, *values: Value) -> int:
        """LPUSH：头部插入，返回插入后的长度。"""
        ...

    async def lpushx(self, key: Key, value: Value) -> int:
        """LPUSHX：key 存在才插入；返回插入后长度，key 缺失返回 0。"""
        ...

    async def rpushx(self, key: Key, value: Value) -> int:
        """RPUSHX：key 存在才插入；语义同 lpushx（尾部）。"""
        ...

    async def lpop(self, key: Key, count: int | None = None) -> Value | list[Value] | None:
        """LPOP：弹出头部。count=None 返回单个值或 None；count>0 返回列表（可能为空）。

        count > 剩余元素数返回剩余全部；服务端不支持 count 时实现需自行降级并声明。
        """
        ...

    async def rpop(self, key: Key, count: int | None = None) -> Value | list[Value] | None:
        """RPOP：弹出尾部。返回语义同 lpop。"""
        ...

    async def lrange(self, key: Key, start: int, stop: int) -> list[Value]:
        """LRANGE：闭区间切片（含负索引；0 -1 = 全量）。key 缺失返回空列表。"""
        ...

    async def ltrim(self, key: Key, start: int, stop: int) -> None:
        """LTRIM：只保留闭区间内元素，其余删除。key 缺失为 no-op。"""
        ...

    async def llen(self, key: Key) -> int:
        """LLEN：长度；key 缺失返回 0。"""
        ...

    async def lindex(self, key: Key, index: int) -> Value | None:
        """LINDEX：按索引取元素（支持负索引）；越界返回 None。"""
        ...

    async def lset(self, key: Key, index: int, value: Value) -> None:
        """LSET：按索引覆写。key 不存在或索引越界抛 RedisCommandError。"""
        ...

    async def lrem(self, key: Key, count: int, value: Value) -> int:
        """LREM：count>0 从头删、<0 从尾删、=0 全删；返回实际删除数。"""
        ...

    async def rpoplpush(self, source: Key, destination: Key) -> Value | None:
        """RPOPLPUSH：source 尾弹入 destination 头，原子；source 空（缺失/空表）返回 None。

        集群：source 与 destination 须同槽。
        """
        ...


class SetCommands(Protocol):
    """Set 命令（核心必选）。"""

    async def sadd(self, key: Key, *members: Value) -> int:
        """SADD：返回新增 member 个数（已存在不计）。空 members 抛 RedisCommandError。"""
        ...

    async def srem(self, key: Key, *members: Value) -> int:
        """SREM：返回实际删除的 member 个数。"""
        ...

    async def smembers(self, key: Key) -> set[Value]:
        """SMEMBERS：全量成员（无序）；key 缺失返回空 set。"""
        ...

    async def sismember(self, key: Key, member: Value) -> bool:
        """SISMEMBER。"""
        ...

    async def scard(self, key: Key) -> int:
        """SCARD：成员数；key 缺失返回 0。"""
        ...

    async def spop(self, key: Key, count: int | None = None) -> Value | set[Value] | None:
        """SPOP：随机弹出。count=None 返回单个值或 None；count>0 返回集合（可能为空）。"""
        ...

    async def srandmember(self, key: Key, count: int | None = None) -> Value | list[Value] | None:
        """SRANDMEMBER：随机读取不删除。

        count=None：单个值或 None；count>0：不重复的至多 count 个；
        count<0：**允许重复**的 |count| 个（Redis 语义）。
        """
        ...

    async def smove(self, source: Key, destination: Key, member: Value) -> bool:
        """SMOVE：原子迁移。source 缺 member 返回 False；成功返回 True。

        集群：source 与 destination 须同槽。
        """
        ...

    async def sinter(self, *keys: Key) -> set[Value]:
        """SINTER：交集。空参抛 RedisCommandError；含缺失 key 按空集处理。集群：同槽。"""
        ...

    async def sunion(self, *keys: Key) -> set[Value]:
        """SUNION：并集。语义约束同 sinter。集群：同槽。"""
        ...

    async def sdiff(self, *keys: Key) -> set[Value]:
        """SDIFF：第一个 key 相对后续的差集。集群：同槽。"""
        ...

    async def sinterstore(self, destination: Key, *keys: Key) -> int:
        """SINTERSTORE：交集写入 destination，返回结果成员数。集群：全部 key 同槽。"""
        ...

    async def sunionstore(self, destination: Key, *keys: Key) -> int:
        """SUNIONSTORE：并集写入 destination。集群：同槽。"""
        ...

    async def sdiffstore(self, destination: Key, *keys: Key) -> int:
        """SDIFFSTORE：差集写入 destination。集群：同槽。"""
        ...

    async def sscan(
        self,
        key: Key,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> tuple[ScanCursor, list[Value]]:
        """SSCAN：返回 (下一游标, 本批成员)。弱一致语义同 SCAN。"""
        ...


class ScanCommands(Protocol):
    """SCAN 命令（核心必选）。"""

    async def scan(
        self,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
        type_name=None,
    ) -> ScanBatch:
        """SCAN：返回单批结果。游标回到 SCAN_START 即遍历结束。

        - match：glob 通配；count：单批提示值（非硬上限）；type：b"string"/b"zset"/... 过滤；
        - 弱一致：可能重复/漏返，遍历期间删 key 是安全的；调用方需去重；
        - 语义保证：从 SCAN_START 完整遍历期间**始终存在**的 key 至少返回一次。
        """
        ...

    def scan_iter(
        self,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> AsyncIterator[Key]:
        """SCAN 迭代器形态：内部循环游标至 SCAN_START，产出可能重复的 key。

        返回 async iterator（``async for key in client.scan_iter(match=b"user:*")``）。
        """
        ...


class Pipeline(Protocol):
    """Pipeline 句柄：命令入队（返回 self 支持链式），execute 一次性提交。

    契约：
      - execute 返回与入队顺序一一对应的结果列表；任一命令失败时整批结果
        形态由 transaction 与实现决定（非事务：失败前结果保留、失败位起为错误）；
      - transaction=True 要求底层 MULTI/EXEC：EXEC 期间不与其他客户端交错
        （原子执行）；队列期语法错误整批作废；EXEC 内单命令**运行期**错误
        （如 WRONGTYPE）不回滚其余命令——redis-py execute() 抛出首个错误，
        此前命令已生效（Redis 事务无回滚，与 SQL 语义不同）；
      - transaction=False 仅批量发送（非原子，逐条执行，允许其他客户端交错）；
      - 必须成对调用 aclose()（或用实现提供的 async with 支持）；
      - 句柄非线程/协程安全：单协程使用。
    """

    def get(self, key: Key) -> "Pipeline":
        ...

    def set(
        self,
        key: Key,
        value: Value,
        *,
        condition: SetCondition | None = None,
        duration: Duration | None = None,
        keep_ttl: bool = False,
    ) -> "Pipeline":
        ...

    def delete(self, *keys: Key) -> "Pipeline":
        ...

    def exists(self, *keys: Key) -> "Pipeline":
        ...

    def expire(self, key: Key, duration: Duration) -> "Pipeline":
        ...

    def hset(
        self,
        key: Key,
        mapping: dict[Value, Value] | None = None,
        *,
        field: Value | None = None,
        value: Value | None = None,
    ) -> "Pipeline":
        ...

    def hget(self, key: Key, field: Value) -> "Pipeline":
        ...

    def hgetall(self, key: Key) -> "Pipeline":
        ...

    def hdel(self, key: Key, *fields: Value) -> "Pipeline":
        ...

    def rpush(self, key: Key, *values: Value) -> "Pipeline":
        ...

    def lrange(self, key: Key, start: int, stop: int) -> "Pipeline":
        ...

    def sadd(self, key: Key, *members: Value) -> "Pipeline":
        ...

    def scan(
        self,
        cursor: ScanCursor = SCAN_START,
        *,
        match: Value | None = None,
        count: int | None = None,
    ) -> "Pipeline":
        ...

    async def execute(self) -> list[Any]:
        ...

    async def aclose(self) -> None:
        ...


class PipelineCommands(Protocol):
    """Pipeline 装配（核心必选）。"""

    def pipeline(self, *, transaction: bool | None = None) -> Pipeline:
        """创建 pipeline 句柄。

        - transaction=None：取连接配置默认（REDIS_TRANSACTION_ENABLED）；
        - transaction=True：MULTI/EXEC 事务；False：批量发送非原子。
        """
        ...


@runtime_checkable
class RedisClient(
    KeyCommands,
    StringCommands,
    HashCommands,
    ListCommands,
    SetCommands,
    ScanCommands,
    PipelineCommands,
    Protocol,
):
    """核心必选能力聚合 + 生命周期与能力探测。

    任何 Provider 经 RedisProviderFactory.create() 产出的客户端必须满足本聚合
    （实现类无需显式继承——结构化 Protocol；但契约套件按方法面跑批验证）。
    """

    @property
    def text_mode(self) -> bool:
        """本客户端的值返回模式（构造期固化）：False=bytes（默认），True=str。"""
        ...

    def supports(self, capability: type) -> bool:
        """探测是否支持某可选能力组（capabilities.py 中的 Protocol 类）。

        返回 False 时调用 as_capability() 将抛 CapabilityNotSupportedError。
        """
        ...

    def as_capability(self, capability: type) -> Any:
        """取可选能力组视图（如 ``client.as_capability(CounterCapability)``）。

        不支持抛 CapabilityNotSupportedError；返回对象与客户端共享连接池与生命周期。
        """
        ...

    async def ping(self) -> bool:
        """PING：连接活性探测（工厂 create 后首检，业务侧健康检查也可用）。"""
        ...

    async def aclose(self) -> None:
        """释放客户端全部资源（普通/订阅/阻塞三类连接池）。幂等。"""
        ...
