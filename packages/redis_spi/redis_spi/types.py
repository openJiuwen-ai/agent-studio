# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis_spi 值对象与公共类型（零 redis-py 依赖）。

全局类型约定（与 protocols.py 契约总则一致）：
  - Key/Value 一律 ``str | bytes``：str 由实现按 UTF-8 编码为 bytes；
  - 客户端返回值默认 bytes（``text_mode=False``），text_mode 视图返回 str，
    同一客户端两种模式不得混用（Provider 构造期固化）；
  - TTL 一律使用 :class:`Duration` 值对象（显式单位），禁止裸 int 隐式猜测单位；
    例外：绝对过期时间戳（EXPIREAT/PEXPIREAT 的 Unix 秒/毫秒）为独立语义，显式裸 int；
  - SCAN 游标起点/终点均为 :data:`SCAN_START`（0）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Union

#: 键类型：str 按 UTF-8 编码。
Key = Union[str, bytes]
#: 值类型：str 按 UTF-8 编码。
Value = Union[str, bytes]

#: SCAN 游标（服务端无符号整数）。遍历必须持续到游标回到 SCAN_START。
ScanCursor = int
#: SCAN 起点与终点游标。
SCAN_START: ScanCursor = 0

#: SortedSet score 边界：数值、``"+inf"``、``"-inf"``；加括号表示开区间（如 ``(5``）。
ScoreBoundary = Union[float, int, str]


@dataclass(frozen=True)
class Duration:
    """TTL / 超时时长值对象（内部归一为正整数毫秒）。

    契约：
      - 前置条件：必须为正。0 与负数在构造期抛 ``ValueError``——TTL=0 在 Redis 语义中
        等价于立即删除，本接口不允许以 Duration 表达删除（请显式 ``delete``）。
      - 单位显式（nos 契约要求）::

            Duration.seconds(30)        # 30 秒
            Duration(milliseconds=500)  # 500 毫秒
    """

    milliseconds: int

    def __post_init__(self) -> None:
        if isinstance(self.milliseconds, bool) or not isinstance(self.milliseconds, int):
            raise TypeError(
                f"milliseconds must be int, got {type(self.milliseconds).__name__}"
            )
        if self.milliseconds <= 0:
            raise ValueError(f"duration must be positive, got {self.milliseconds}ms")

    @classmethod
    def seconds(cls, value: float) -> "Duration":
        """以秒构造；亚毫秒精度向上取整（避免正 TTL 被截断为 0）。

        前置条件：必须为正有限数——0 / 负数 / NaN / inf 构造期抛 ``ValueError``
        （含亚毫秒级负数，如 -0.0005s，禁止取整后翻成正时长）。
        """
        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"duration must be a positive finite number of seconds, got {value}"
            )
        return cls(milliseconds=math.ceil(value * 1000))

    @classmethod
    def milliseconds(cls, value: int) -> "Duration":
        """以毫秒构造。"""
        return cls(milliseconds=value)

    @property
    def total_seconds(self) -> float:
        """换算为秒（浮点，仅用于日志/展示）。"""
        return self.milliseconds / 1000

    def __str__(self) -> str:
        return f"{self.milliseconds}ms"


class SetCondition(str, Enum):
    """SET 条件参数（等价 SET NX / SET XX）。

    - NX：键不存在才写入；
    - XX：键存在才写入。
    """

    NX = "nx"
    XX = "xx"


@dataclass(frozen=True)
class ScanBatch:
    """SCAN 单批结果（key 扫描）。

    契约：
      - ``cursor == SCAN_START`` 表示本轮遍历结束；
      - SCAN 为弱一致：同一 key 可能重复返回，遍历期间变动的 key 可能漏返；
        依赖精确集合的调用方必须自行去重。
    """

    cursor: ScanCursor
    items: tuple[Key, ...]

    def __post_init__(self) -> None:
        # items 统一冻结为 tuple（防调用方/实现方持有可变引用）。
        object.__setattr__(self, "items", tuple(self.items))
        if self.cursor < 0:
            raise ValueError(f"scan cursor must be >= 0, got {self.cursor}")


class GeoUnit(str, Enum):
    """GEO 距离单位。"""

    M = "m"
    KM = "km"
    FT = "ft"
    MI = "mi"


@dataclass(frozen=True)
class GeoMember:
    """GEO 成员（geoadd 入参）。

    前置条件：longitude ∈ [-180, 180]，latitude ∈ [-90, 90]。
    """

    longitude: float
    latitude: float
    member: Value

    def __post_init__(self) -> None:
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"longitude must be in [-180, 180], got {self.longitude}")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"latitude must be in [-90, 90], got {self.latitude}")


@dataclass(frozen=True)
class ScoreMember:
    """SortedSet 成员与 score 对（便捷值对象）。

    协议签名按 Python 惯例表达：zadd 入参用 ``dict[Value, float]``、
    zscan 产出用 ``(member, score)`` 元组；本类型供调用方组装入参 /
    转换产出结果使用（平台自身不强制）。
    """

    member: Value
    score: float


@dataclass(frozen=True)
class PubSubMessage:
    """PubSub 订阅消息（``PubSubHandle.listen()`` 迭代产出）。

    - type：``message`` / ``pmessage`` / ``subscribe`` / ``unsubscribe`` /
      ``psubscribe`` / ``punsubscribe``（确认类消息由实现按需产出，业务侧应忽略未知 type）；
    - channel/data：bytes（text_mode 视图为 str）；
    - pattern：仅 pmessage 时非 None。
    """

    type: str
    channel: Value
    data: Value
    pattern: Value | None = None
