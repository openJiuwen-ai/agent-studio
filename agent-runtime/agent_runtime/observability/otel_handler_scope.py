# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""按 execution 作用域隔离 OTel workflow handler（纯本仓，不改 openjiuwen core）。

上游 ``Tracer.init`` 仍向每个请求注入 registry 中的同一扩展 handler 实例；
状态键又是静态 ``workflow_id`` / ``executable_id``，同工作流并发会串 span。

本模块用 OTel Context（contextvars）携带 ``execution_id``：runner 入口 attach
后，core 内 ``create_task`` 会复制 context，同一次执行的事件落到同一个
``StudioOtelWorkflowHandler`` 子实例。无需 monkeypatch ``Tracer.init``。
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Optional

from openjiuwen.core.session.tracer.handler import TraceExtWorkflowHandler

try:
    from opentelemetry import context as otel_context
except ImportError:  # pragma: no cover - 无 OTel 时降级为无作用域
    otel_context = None  # type: ignore[assignment]

try:
    from agent_runtime.observability.tracer_otel_studio import StudioOtelWorkflowHandler
except ImportError:  # pragma: no cover
    from openjiuwen.extensions.tracer_otel.handler import (
        OtelWorkflowHandler as StudioOtelWorkflowHandler,
    )

# OTel Context 是 contextvars 实现：runner 入口写入后，core 内部 create_task 会复制
EXEC_SCOPE_KEY = (
    otel_context.create_key("studio.execution_scope") if otel_context is not None else None
)
_UNSCOPED = "__unscoped__"


def set_execution_scope(execution_id: str):
    """runner 入口调用：返回 token，与现有 otel_token 一起在 finally detach。"""
    if otel_context is None or EXEC_SCOPE_KEY is None:
        return None
    return otel_context.attach(
        otel_context.set_value(EXEC_SCOPE_KEY, execution_id)
    )


def current_execution_scope() -> str:
    if otel_context is None or EXEC_SCOPE_KEY is None:
        return _UNSCOPED
    return otel_context.get_value(EXEC_SCOPE_KEY) or _UNSCOPED


def _handler_has_live_spans(handler: Any) -> bool:
    """上游在 QA 中断时有意保留未收尾 mapping / span，供 resume 复用同一 OTel trace。"""
    for attr in ("_layer_root_spans", "_component_spans"):
        mapping = getattr(handler, attr, None)
        if isinstance(mapping, dict) and mapping:
            return True
    mgr = getattr(handler, "_span_manager", None)
    spans = getattr(mgr, "_spans", None) if mgr is not None else None
    return isinstance(spans, dict) and bool(spans)


def release_execution_scope(execution_id: str, *, force: bool = False) -> bool:
    """执行结束时释放对应子 handler。

    默认若仍有 live span（QA 中断 / 客户端提前关闭），保留 keyed 子 handler 与
    ``_cached_root_ctx``，避免 resume 同 exec_id 时被拆成新 OTel trace。
    返回是否真正释放。
    """
    try:
        from openjiuwen.core.session.tracer import TracerHandlerRegistry
    except ImportError:  # pragma: no cover
        return False
    dispatcher = TracerHandlerRegistry.get_workflow_handlers().get("otel_workflow")
    if isinstance(dispatcher, ExecutionScopedWorkflowHandler):
        return dispatcher.release_execution_scope(execution_id, force=force)
    return False


def stamp_current_scope_identity(
    trace_id: str = "",
    session_id: Optional[str] = None,
) -> None:
    """在已 attach 的 execution scope 下，把本次 Tracer 身份打到子 handler。

    ``Tracer.init`` 常在 scope attach 之前调用，只会改写分发器上的 pending；
    runner 在 attach 后调用本函数，避免并发 init 把错误的 pending 绑到本执行。
    """
    try:
        from openjiuwen.core.session.tracer import TracerHandlerRegistry
    except ImportError:  # pragma: no cover
        return
    dispatcher = TracerHandlerRegistry.get_workflow_handlers().get("otel_workflow")
    if not isinstance(dispatcher, ExecutionScopedWorkflowHandler):
        return
    if current_execution_scope() == _UNSCOPED:
        return
    if trace_id:
        dispatcher.set_trace_id(trace_id)
    dispatcher.set_session_id(session_id)


def attach_execution_scope(
    execution_id: str,
    *,
    trace_id: str = "",
    session_id: Optional[str] = None,
):
    """attach scope 并立刻 stamp 身份；返回 detach 用的 token。"""
    token = set_execution_scope(execution_id)
    stamp_current_scope_identity(trace_id=trace_id, session_id=session_id)
    return token


class ExecutionScopedWorkflowHandler(TraceExtWorkflowHandler):
    """按执行作用域分发到独立的 StudioOtelWorkflowHandler 实例。

    - 注册点替换单例 StudioOtelWorkflowHandler，接口仍走公开扩展基类；
    - 每个 execution 独立 span 状态；
    - 无作用域调用方回落到 ``__unscoped__``，保持单组件调试/旧单测行为。
    """

    def __init__(self, otel_tracer: Any, config: Any, max_scopes: int = 256):
        super().__init__()
        self._otel_tracer = otel_tracer
        self._config = config
        self._max_scopes = max_scopes
        self._lock = threading.RLock()
        self._handlers: OrderedDict[str, Any] = OrderedDict()
        self._pending_trace_id = ""
        self._pending_session_id: Optional[str] = None

    def _sub(self) -> Any:
        scope = current_execution_scope()
        with self._lock:
            handler = self._handlers.get(scope)
            if handler is None:
                handler = StudioOtelWorkflowHandler(self._otel_tracer, self._config)
                if self._pending_trace_id:
                    handler.set_trace_id(self._pending_trace_id)
                if self._pending_session_id is not None:
                    handler.set_session_id(self._pending_session_id)
                self._handlers[scope] = handler
            self._handlers.move_to_end(scope)
            self._evict_idle_overflow_locked()
            return handler

    def _evict_idle_overflow_locked(self) -> None:
        """LRU 淘汰空闲 scope；有 live span 的保留（QA resume / 未收尾）。"""
        while len(self._handlers) > self._max_scopes:
            evict_key = None
            for key, candidate in self._handlers.items():
                if not _handler_has_live_spans(candidate):
                    evict_key = key
                    break
            if evict_key is None:
                # 全部 live：允许暂时超过 max_scopes，避免拆 resume trace
                break
            evicted = self._handlers.pop(evict_key)
            cleanup = getattr(evicted, "_cleanup_stale_spans", None)
            if callable(cleanup):
                cleanup()

    def release_execution_scope(self, execution_id: str, *, force: bool = False) -> bool:
        with self._lock:
            handler = self._handlers.get(execution_id)
            if handler is None:
                return False
            if not force and _handler_has_live_spans(handler):
                # 中断/提前关闭：保留状态供同 exec_id 恢复
                self._handlers.move_to_end(execution_id)
                return False
            self._handlers.pop(execution_id, None)
        cleanup = getattr(handler, "_cleanup_stale_spans", None)
        if callable(cleanup):
            cleanup()
        return True

    def set_trace_id(self, trace_id: str) -> None:
        self._pending_trace_id = trace_id
        if current_execution_scope() != _UNSCOPED:
            self._sub().set_trace_id(trace_id)

    def set_session_id(self, session_id: Optional[str]) -> None:
        self._pending_session_id = session_id
        if current_execution_scope() != _UNSCOPED:
            self._sub().set_session_id(session_id)

    async def _forward(self, name: str, *args, **kwargs):
        return await getattr(self._sub(), name)(*args, **kwargs)

    async def on_call_start(self, *args, **kwargs):
        return await self._forward("on_call_start", *args, **kwargs)

    async def on_call_done(self, *args, **kwargs):
        return await self._forward("on_call_done", *args, **kwargs)

    async def on_pre_invoke(self, *args, **kwargs):
        return await self._forward("on_pre_invoke", *args, **kwargs)

    async def on_pre_stream(self, *args, **kwargs):
        return await self._forward("on_pre_stream", *args, **kwargs)

    async def on_invoke(self, *args, **kwargs):
        return await self._forward("on_invoke", *args, **kwargs)

    async def on_post_invoke(self, *args, **kwargs):
        return await self._forward("on_post_invoke", *args, **kwargs)

    async def on_post_stream(self, *args, **kwargs):
        return await self._forward("on_post_stream", *args, **kwargs)

    async def on_interact(self, *args, **kwargs):
        return await self._forward("on_interact", *args, **kwargs)

    def __getattr__(self, name: str):
        # 其余事件（如 on_call_finalize）直接转发给当前执行的子 handler
        if name.startswith("_") or not hasattr(StudioOtelWorkflowHandler, name):
            raise AttributeError(name)
        return getattr(self._sub(), name)
