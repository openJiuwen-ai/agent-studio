# -*- coding: UTF-8 -*-
"""请求级 OTel trace 上下文（issue 1754）。

根 Span 建立后由 Studio handler 写入真实 trace_id/span_id（32/16 hex）与
业务关联 ID；HTTP 层（响应头/SSE）在提交前读取并对外输出。

- trace_id/span_id：来自 Runtime 根 Span 的 SpanContext（不依赖业务 trace_id）
- correlation_id：入站业务关联 ID（= session trace_id / openjiuwen.trace.id，
  经 Manager 时等于 Manager 下发的 TraceID）
"""
from __future__ import annotations

import contextvars
import threading
from collections import OrderedDict
from typing import Optional, Tuple

# 登记表上限：仅做跨任务传递的短期缓冲，异常未清理时按 LRU 淘汰，避免无界增长。
_REGISTRY_MAX_SIZE = 4096

_otel_trace_ctx: contextvars.ContextVar[Optional[Tuple[str, str, str]]] = (
    contextvars.ContextVar("agent_runtime_otel_trace_ctx", default=None)
)

# 根 Span 在 runner 的异步任务内建立，ContextVar 不跨 task 传播；
# 以 session_id(=conversation_id) 为键做进程级登记，HTTP 层按请求读取。
# 嵌套登记：conversation_id -> {execution_id -> (trace_id, span_id, correlation_id)}
# 同一 conversation 并发执行时各自持有条目，互不覆盖（issue 1754 复审）。
_session_registry: "OrderedDict[str, OrderedDict[str, Tuple[str, str, str]]]" = OrderedDict()
_registry_lock = threading.Lock()

# 单会话最多保留的执行条目数（并发上限保护）。
_MAX_EXEC_ENTRIES = 8


def register_session_trace(session_id: str, trace_id: str, span_id: str,
                           correlation_id: str = "", execution_id: str = "") -> None:
    """登记会话的真实 OTel 上下文（issue 1754）。

    execution_id 区分同一 conversation 下的并发执行；每执行独立条目，
    读取/清理只命中本执行，互不覆盖。
    """
    if not session_id or not trace_id or not span_id:
        return
    key = str(session_id)
    exec_key = str(execution_id or "")
    with _registry_lock:
        entries = _session_registry.get(key)
        if entries is None:
            entries = OrderedDict()
            _session_registry[key] = entries
        entries[exec_key] = (trace_id, span_id, correlation_id or "")
        entries.move_to_end(exec_key)
        _session_registry.move_to_end(key)
        while len(entries) > _MAX_EXEC_ENTRIES:
            entries.popitem(last=False)
        while len(_session_registry) > _REGISTRY_MAX_SIZE:
            _session_registry.popitem(last=False)


def get_session_trace(session_id: str, execution_id: str = ""):
    """读取登记条目：指定 execution_id 时精确命中；为空时取该会话最新条目。"""
    with _registry_lock:
        entries = _session_registry.get(str(session_id))
        if not entries:
            return None
        if execution_id:
            return entries.get(str(execution_id))
        return next(reversed(entries.values()))


def clear_session_trace(session_id: str, execution_id: str = "") -> None:
    """清理本执行条目；未带 execution_id 时清空该会话全部条目（兼容语义）。"""
    with _registry_lock:
        key = str(session_id)
        entries = _session_registry.get(key)
        if not entries:
            return
        if execution_id:
            entries.pop(str(execution_id), None)
            if not entries:
                _session_registry.pop(key, None)
        else:
            _session_registry.pop(key, None)


def build_otel_trace_headers_for(session_id: str, execution_id: str = "") -> dict:
    value = get_session_trace(session_id, execution_id)
    if not value:
        return {}
    trace_id, span_id = value[0], value[1]
    return {
        "X-OTel-Trace-Id": trace_id,
        "traceresponse": "00-%s-%s-01" % (trace_id, span_id),
    }


_business_trace_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "agent_runtime_business_trace", default=""
)


def set_business_trace_id(value: str) -> None:
    """入站业务关联 ID（TraceID 头 / 经 Manager 时下发的 TraceID）。"""
    if value:
        _business_trace_ctx.set(str(value))


def get_business_trace_id() -> str:
    return _business_trace_ctx.get() or ""


def set_otel_trace_context(trace_id: str, span_id: str, correlation_id: str = "") -> None:
    if trace_id and span_id:
        _otel_trace_ctx.set((trace_id, span_id, correlation_id or ""))


def get_otel_trace_id() -> str:
    value = _otel_trace_ctx.get()
    return value[0] if value else ""


def get_otel_span_id() -> str:
    value = _otel_trace_ctx.get()
    return value[1] if value else ""


def get_correlation_id() -> str:
    value = _otel_trace_ctx.get()
    return value[2] if value else ""


def build_otel_trace_headers() -> dict:
    """对外输出头：X-OTel-Trace-Id（便于一键查询）+ W3C traceresponse。"""
    value = _otel_trace_ctx.get()
    if not value:
        return {}
    trace_id, span_id = value[0], value[1]
    if not trace_id or not span_id:
        return {}
    return {
        "X-OTel-Trace-Id": trace_id,
        "traceresponse": "00-%s-%s-01" % (trace_id, span_id),
    }