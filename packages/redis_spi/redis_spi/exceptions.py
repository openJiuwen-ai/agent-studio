# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis_spi 统一异常体系。

契约总则（设计文档 4.4）：
  - 所有对外错误以本体系抛出；实现负责在边界把底层客户端异常翻译为对应类型
    （业务层不直接接触 redis-py / Redisson 等原生异常）；
  - 每个异常携带数字 ``code``（260000 段，实施期与平台状态码登记表避让——Q7）
    与出错时的 ``redis_key`` / ``operation`` 上下文（可用时）；
  - 原始异常通过 ``raise ... from e`` 挂在 ``__cause__``，禁止吞掉。
"""

from __future__ import annotations

from typing import Any

#: redis_spi 错误码基段（需在平台错误码登记表登记避让，见设计文档 Q7）。
REDIS_ERROR_CODE_BASE = 260000


class RedisError(Exception):
    """redis_spi 异常根。所有子类错误码在 260000 段内唯一。"""

    code: int = REDIS_ERROR_CODE_BASE

    def __init__(
        self,
        message: str,
        *,
        redis_key: str | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.redis_key = redis_key
        self.operation = operation

    def __str__(self) -> str:
        # 保持 code/operation/key 上下文，便于日志排查。
        parts = [f"[{self.code}] {self.message}"]
        if self.operation:
            parts.append(f"operation={self.operation}")
        if self.redis_key:
            parts.append(f"key={self.redis_key}")
        return ", ".join(parts)


class RedisConfigError(RedisError):
    """配置缺失/非法、Provider 未初始化、插件加载失败（启动期 fail-fast，不可重试）。"""

    code = REDIS_ERROR_CODE_BASE + 1


class RedisConnectionError(RedisError):
    """连接失败/连接被拒/断连（可重试的基础设施错误；业务可降级）。"""

    code = REDIS_ERROR_CODE_BASE + 2


class RedisAuthFailureError(RedisConnectionError):
    """认证/鉴权失败（自研鉴权链路失败独立成类，便于审计与告警区分）。"""

    code = REDIS_ERROR_CODE_BASE + 3


class RedisTimeoutError(RedisError):
    """连接或命令超时。

    契约（nos Counter 提醒）：写/计数类命令超时后**结果未知**——``result_known=False``
    时禁止盲重试（非幂等），由调用方决定（NX 核对 / 查询核对 / 放弃）。
    """

    code = REDIS_ERROR_CODE_BASE + 4

    def __init__(
        self,
        message: str,
        *,
        result_known: bool = True,
        redis_key: str | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message, redis_key=redis_key, operation=operation)
        self.result_known = result_known


class RedisCommandError(RedisError):
    """命令被拒/参数错误/协议错误（调用方错误，修代码而非重试）。"""

    code = REDIS_ERROR_CODE_BASE + 5

    def __init__(
        self,
        message: str,
        *,
        command: str | None = None,
        detail: str | None = None,
        redis_key: str | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message, redis_key=redis_key, operation=operation)
        self.command = command
        self.detail = detail


class RedisWrongTypeError(RedisCommandError):
    """对错误类型的 key 执行命令（WRONGTYPE），便于调用方精确分支。"""

    code = REDIS_ERROR_CODE_BASE + 6


class CapabilityNotSupportedError(RedisError):
    """调用了 Provider 未实现的能力组/命令（应先 supports() 探测）。"""

    code = REDIS_ERROR_CODE_BASE + 7

    def __init__(
        self,
        message: str,
        *,
        capability: Any = None,
        redis_key: str | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message, redis_key=redis_key, operation=operation)
        self.capability = capability


class RedisScriptError(RedisCommandError):
    """Lua 脚本运行时错误（eval/evalsha 执行失败）。"""

    code = REDIS_ERROR_CODE_BASE + 8


class RedisClusterError(RedisError):
    """集群拓扑/MOVED/ASK 等集群层错误。

    实现应内部消化集群细节（重定向跟随、拓扑刷新）；本异常外抛即视为实现缺陷或
    不可自愈的集群故障。
    """

    code = REDIS_ERROR_CODE_BASE + 9
