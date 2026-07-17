# -*- coding: utf-8 -*-
"""MODEL/ROUTER 策略、failover/retry/timeout 循环、审计与告警。

移植自 Java ``RuntimeModelServiceManager.chatCompletions`` 循环及 ``ModelApiLog`` /
``AlarmLogUtil``。

- 限流（``applyRateLimit``）：未迁移。
- OBS 内容审计管线（input/output 全文 → 本地文件 → OBS）：未迁移。
- 结构化审计日志（元数据 INFO）与告警 logger：保留。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from .resolver import ModelServiceDetail, ModelStrategy, ModelServiceError, StrategyType


# 审计数据（对应 Java ModelApiLog 元数据字段集；全文内容部分未迁移）。

@dataclass
class AuditLog:
    model_id: str
    model_name: str
    api_url: str
    stream: bool
    status: str                       # "success" | "fail"
    duration_ms: int
    project_id: str
    workspace_id: str
    auth_id: str
    provider_id: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    first_token_ms: Optional[int] = None
    reason: Optional[str] = None


_audit_logger = logging.getLogger("model_service.audit")
_alarm_logger = logging.getLogger("model_service.alarm")


def record_audit(log: AuditLog) -> None:
    """记录一条结构化 INFO 审计日志（对应 Java aspect finally 的常驻 INFO）。"""
    _audit_logger.info(
        "Invoke model service. model:%s status:%s cost:%dms tokens:%s stream:%s project:%s workspace:%s",
        log.model_name, log.status, log.duration_ms,
        log.total_tokens, log.stream, log.project_id, log.workspace_id,
    )


def alarm(source: str, resource: str, cause: str, *, severity: str = "WARN") -> None:
    """输出结构化告警 JSON 到 named logger（对应 Java ``AlarmLogUtil.logAlarm``）。

    模型调用失败时调用；开关由 logging 配置控制，默认 WARN 级别，按需提级。
    """
    _alarm_logger.warning(
        '{"source":"%s","resource":"%s","severity":"%s","cause":"%s","create_time":%d}',
        source, resource, severity, cause, int(time.time()),
    )


# failover / retry / timeout 循环（对应 Java RuntimeModelServiceManager.chatCompletions）。
#
# 单模型单次实际调用由 ``StudioModelClient._invoke_one_model`` 提供（内含 dispatch → openjiuwen
# client）。stream=False 返回 AssistantMessage；stream=True 返回 AsyncIterator[chunk]（lazy handle）。
InvokeOne = Callable[[ModelServiceDetail, bool], Awaitable]


async def invoke_with_strategy(
    strategy: ModelStrategy,
    invoke_one: InvokeOne,
    *,
    stream: bool,
    on_attempt: Optional[Callable[[ModelServiceDetail], None]] = None,
) -> object:
    """按策略执行模型调用（对应 Java ``chatCompletions`` 循环）。

    - ``MODEL``：单次 ``invoke_one``。
    - ``ROUTER``：按 ``models`` 顺序遍历；跳过 ``!available`` 的非 free 模型，free 模型始终尝试；
      每模型重试 ``retry_count + 1`` 次；每轮先检查总 ``strategy_timeout``；成功即停。
      全部失败且无可用模型 → ``MD_MODEL_SERVICE_NOT_AVAILABLE``；有可用但全部失败 →
      ``MD_STRATEGY_FAILED``。

    openjiuwen 的 ``max_retries`` 仅重试单次 HTTP，不覆盖此处的多模型 failover。

    Args:
        strategy: 已解析的策略。
        invoke_one: 单模型单次调用回调，签名为 ``(detail, stream)``。
        stream: 是否流式调用。
        on_attempt: 每次实际调用前的回调，参数为本次 attempt 的 detail；用于审计归因到
            真正调用的模型（ROUTER failover 时避免审计指向 ``models[0]``）。
    """
    if strategy.type == StrategyType.MODEL:
        if on_attempt is not None:
            on_attempt(strategy.models[0])
        return await invoke_one(strategy.models[0], stream)

    retry = max(strategy.retry_count, 0)
    timeout_ms = max(strategy.strategy_timeout_ms or 600_000, 5000)
    begin = time.monotonic()
    have_available = False
    result = None

    for detail in strategy.models:
        if not detail.is_free_model and not detail.available:
            continue
        have_available = True
        cur = retry + 1
        while cur > 0:
            cur -= 1
            if (time.monotonic() - begin) * 1000 > timeout_ms:
                raise ModelServiceError(
                    "MD_STRATEGY_TIMEOUT",
                    f"strategy timeout {timeout_ms}ms",
                )
            if on_attempt is not None:
                on_attempt(detail)
            try:
                result = await invoke_one(detail, stream)
                break
            except Exception as e:  # noqa: BLE001  对应 Java catch Throwable → 重试
                _alarm_logger.warning("strategy retry remaining %d: %s", cur, e)
        if result is not None:
            break

    if result is not None:
        return result
    if not have_available:
        raise ModelServiceError("MD_MODEL_SERVICE_NOT_AVAILABLE", "no available model")
    raise ModelServiceError("MD_STRATEGY_FAILED", "strategy process failed")
