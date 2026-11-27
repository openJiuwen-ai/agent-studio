# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""请求派生 OTel Trace ID：X-Request-Id → trace_id，且不构造未导出的父 Span。

背景：
- 早期版本用 X-Request-Id 派生 OTel trace_id（32 位 hex 直接用，否则 md5），
  调用方可直接用 X-Request-Id 在追踪后端检索。但实现方式是注入一个不导出的
  NonRecordingSpan 作为父节点，导致链路缺根。
- 去掉虚构父节点后，trace_id 改由 SDK 随机生成，X-Request-Id 不再能直接检索。

本模块在“生成根 Span 的 trace_id”这一步恢复派生：中间件在没有合法上游
追踪上下文（traceparent）时，把由 request_id 派生的 trace_id 绑定到当前请求；
tracer 的 IdGenerator 为根 Span 生成 trace_id 时优先使用该值。根 Span 仍是
真实、可导出的根节点，不引入任何虚构父节点。

规则：
- 32 位 hex（非全 0）直接作为 trace_id；其他值取 md5（与早期版本一致，便于
  调用方沿用既有检索方式）。
- 上游携带合法 traceparent 时以上游为准（根 Span 有父节点，不调用生成器）。
- 请求外（无绑定）回退随机 trace_id。
"""

from __future__ import annotations

import hashlib
from contextvars import ContextVar, Token
from typing import Any, Optional

from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator

_HEX_CHARS = frozenset("0123456789abcdefABCDEF")
_INVALID_TRACE_ID = 0

_REQUEST_TRACE_ID: ContextVar[Optional[int]] = ContextVar(
    "oj_request_derived_trace_id", default=None
)


def derive_trace_id(request_id: str) -> Optional[int]:
    """由业务 request_id 派生 128 位 OTel trace_id；无法派生时返回 None。"""
    if not request_id:
        return None
    if len(request_id) == 32 and frozenset(request_id) <= _HEX_CHARS:
        value = int(request_id, 16)
    else:
        # 非安全用途：仅把任意字符串映射为固定 128 位标识（与早期版本一致）
        value = int(
            hashlib.md5(request_id.encode("utf-8"), usedforsecurity=False).hexdigest(), 16
        )
    return None if value == _INVALID_TRACE_ID else value


def bind_request_trace_id(request_id: str) -> Optional[Token]:
    """把由 request_id 派生的 trace_id 绑定到当前上下文；返回 Token 供 reset。"""
    value = derive_trace_id(request_id)
    if value is None:
        return None
    return _REQUEST_TRACE_ID.set(value)


def reset_request_trace_id(token: Optional[Token]) -> None:
    """解除绑定；token 为 None（未绑定）时跳过。"""
    if token is not None:
        _REQUEST_TRACE_ID.reset(token)


def current_request_trace_id() -> Optional[int]:
    """当前请求绑定的派生 trace_id（未绑定返回 None）。"""
    return _REQUEST_TRACE_ID.get()


class RequestDerivedIdGenerator(IdGenerator):
    """根 Span 优先使用请求派生的 trace_id；span_id 与无绑定时委托原生成器。"""

    def __init__(self, fallback: Optional[IdGenerator] = None):
        self._fallback = fallback or RandomIdGenerator()

    def generate_span_id(self) -> int:
        return self._fallback.generate_span_id()

    def generate_trace_id(self) -> int:
        value = _REQUEST_TRACE_ID.get()
        if value:
            return value
        return self._fallback.generate_trace_id()


def install_request_trace_id_generator(tracer: Any) -> bool:
    """为 SDK Tracer 安装请求派生 IdGenerator（幂等）；不支持时返回 False。

    Core 的 init_otel_tracer 使用私有 TracerProvider 且不暴露 id_generator 参数，
    SDK Tracer 在 start_span 时读取实例属性 ``id_generator``，故在此包装替换。
    """
    current = getattr(tracer, "id_generator", None)
    if current is None:
        return False
    if isinstance(current, RequestDerivedIdGenerator):
        return True
    tracer.id_generator = RequestDerivedIdGenerator(current)
    return True
