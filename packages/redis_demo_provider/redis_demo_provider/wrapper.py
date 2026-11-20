# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""WrapperDemoProvider（demo 形态二）：包装 NativeRedisClient 的治理演示。

教学口径（设计文档 §八 形态 2）：向企业展示"如何在不改框架的前提下给
Redis 链路加自研鉴权 / 审计 / 抖动注入"——

  1. **自研鉴权**：start 期以 appId/passport 做（模拟的）代理鉴权，带
     maxAttempts 重试与 authFailures 抖动模拟，失败抛 RedisAuthFailureError
     （启动期 fail-fast，不进入业务）；
  2. **逐命令治理**：InstrumentedClient 对核心命令面包一层——结构化日志
     （命令名/耗时/错误，内存 command_log + logger）→ 可配置延迟注入
     （delayMs）→ 限流（rateLimitPerSec）→ 失败注入（failureRate，
     模拟自研代理抖动，抛 RedisConnectionError）；
  3. **专属参数**：全部经 ``REDIS_PROVIDER_CONFIG`` 注入（raw_provider_config）。

注入默认全关（0/未配置）——治理层"透明模式"下契约套件全绿（形态二的
契约跑批即在此模式下进行）。依赖 redis-native（包装对象），form 1 不需要。
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import random
import time
from typing import Any

from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import RedisAuthFailureError, RedisConnectionError
from redis_spi.factory import RedisProvider
from redis_spi.protocols import RedisClient

logger = logging.getLogger(__name__)

#: 不做逐命令注入的成员（生命周期/能力面/同步工厂方法：健康检查与视图获取）。
_INSTRUMENTED_SKIP = frozenset(
    {"ping", "aclose", "text_mode", "supports", "as_capability", "native_client", "pipeline", "pubsub"}
)


class InstrumentedClient:
    """核心命令面的透明代理：日志 → 延迟 → 限流 → 失败注入 → 委托。

    - 仅包裹**异步命令方法**；pipeline()/pubsub() 产出物、属性与能力视图
      原样透传（治理面覆盖核心命令，声明口径见 README）；
    - ``command_log`` 为结构化日志的内存形态（单测/演示观察用）。
    """

    def __init__(self, inner: Any, config: dict[str, Any]) -> None:
        self._inner = inner
        self._delay_seconds = float(config.get("delayMs", 0)) / 1000.0
        self._failure_rate = float(config.get("failureRate", 0.0))
        self._rate_limit = int(config.get("rateLimitPerSec", 0)) or None
        self._window_start = time.monotonic()
        self._window_count = 0
        self.command_log: list[dict[str, Any]] = []

    def __getattr__(self, name: str):
        attr = getattr(self._inner, name)
        if name in _INSTRUMENTED_SKIP or not inspect.iscoroutinefunction(attr):
            return attr

        @functools.wraps(attr)
        async def instrumented(*args: Any, **kwargs: Any) -> Any:
            self._rate_guard(name)
            if self._delay_seconds > 0:
                await asyncio.sleep(self._delay_seconds)
            if self._failure_rate > 0 and random.random() < self._failure_rate:
                self._log_entry(name, 0.0, f"injected(failureRate={self._failure_rate})")
                raise RedisConnectionError(
                    f"acme 代理抖动注入（failureRate={self._failure_rate}）",
                    operation=name,
                )
            started = time.perf_counter()
            try:
                result = await attr(*args, **kwargs)
            except Exception as exc:
                self._log_entry(name, (time.perf_counter() - started) * 1000.0, repr(exc))
                raise
            self._log_entry(name, (time.perf_counter() - started) * 1000.0, None)
            return result

        return instrumented

    # ---------------------------------------------------------------- internal

    def _rate_guard(self, name: str) -> None:
        """简单滑动窗口限流：每秒 rateLimitPerSec 条，超出抛连接类错误。"""
        if not self._rate_limit:
            return
        now = time.monotonic()
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._window_count = 0
        self._window_count += 1
        if self._window_count > self._rate_limit:
            self._log_entry(name, 0.0, f"rate-limited({self._rate_limit}/s)")
            raise RedisConnectionError(
                f"acme 代理限流（rateLimitPerSec={self._rate_limit}）",
                operation=name,
            )

    def _log_entry(self, name: str, elapsed_ms: float, error: str | None) -> None:
        """结构化审计日志（内存形态 command_log + logger 双写）。"""
        entry = {"command": name, "elapsed_ms": elapsed_ms, "error": error}
        self.command_log.append(entry)
        if error:
            logger.warning("acme audit: %s failed in %.1fms: %s", name, elapsed_ms, error)
        else:
            logger.info("acme audit: %s ok in %.1fms", name, elapsed_ms)


class WrapperDemoProvider(RedisProvider):
    """Wrapper 形态：REDIS_PROVIDER=acme_wrapper（entry_points）。"""

    def __init__(self) -> None:
        self._inner_provider: RedisProvider | None = None
        self._client: InstrumentedClient | None = None

    async def start(self, settings: RedisProviderSettings) -> RedisClient:
        config = settings.raw_provider_config()
        await self._authenticate(config)
        underlying = await self._build_underlying(settings, config)
        self._client = InstrumentedClient(underlying, config)
        return self._client

    async def stop(self) -> None:
        if self._inner_provider is not None:
            provider, self._inner_provider = self._inner_provider, None
            await provider.stop()
        elif self._client is not None:
            client, self._client = self._client, None
            await client.aclose()
        self._client = None

    def capabilities(self) -> list[type]:
        # 声明面随被包装实现（native 全能力组）。
        from redis_native.capabilities import SUPPORTED_CAPABILITIES

        return list(SUPPORTED_CAPABILITIES)

    # ---------------------------------------------------------------- internal

    async def _authenticate(self, config: dict[str, Any]) -> None:
        """模拟自研代理鉴权：appId/passport 必填 + maxAttempts 内重试。"""
        app_id = config.get("appId")
        passport = config.get("passport")
        if not app_id or not passport:
            raise RedisAuthFailureError(
                "acme 代理鉴权需要 appId 与 passport"
                "（经 REDIS_PROVIDER_CONFIG 注入，如 "
                '{"appId":"demo-app","passport":"demo-pass"}）',
                operation="auth",
            )
        max_attempts = max(1, int(config.get("maxAttempts", 3)))
        auth_failures = max(0, int(config.get("authFailures", 0)))
        for attempt in range(1, max_attempts + 1):
            if attempt <= auth_failures:
                if attempt == max_attempts:
                    raise RedisAuthFailureError(
                        f"acme 鉴权连续失败 {max_attempts} 次（appId={app_id}）",
                        operation="auth",
                    )
                logger.info(
                    "acme auth attempt %d/%d failed (simulated), retrying",
                    attempt,
                    max_attempts,
                )
                continue
            logger.info("acme auth ok (appId=%s, attempt=%d)", app_id, attempt)
            return

    async def _build_underlying(
        self, settings: RedisProviderSettings, config: dict[str, Any]
    ) -> Any:
        """被包装的 NativeRedisClient：真实连接，或 fakeredis（离线演示/契约跑批）。"""
        from redis_native.client import NativeRedisClient

        if config.get("fakeredis"):
            import fakeredis.aioredis

            return NativeRedisClient(
                fakeredis.aioredis.FakeRedis(decode_responses=settings.text_mode),
                text_mode=settings.text_mode,
                transaction_default=settings.redis_transaction_enabled,
            )
        from redis_native.provider import NativeRedisProvider

        self._inner_provider = NativeRedisProvider()
        return await self._inner_provider.start(settings)
