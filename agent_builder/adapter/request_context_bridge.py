# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""agent_builder 自有请求上下文桥——独立于 agent_runtime.context.request_context。

为 model_service ``StudioModelClient._resolve_inputs`` 提供请求头（取 projectId /
workspaceId 等）。agent_builder 在 ``server_fastapi`` 中间件里 set，并经
``model_service.ports.set_request_headers`` 注册 getter，从而 agent_builder 不依赖 agent_runtime。

用 contextvars 实现协程安全的请求作用域存储；中间件在 ``await call_next`` 期间持有，
保证 StreamingResponse 流式过程中 context 有效（与 agent_runtime RequestContextMiddleware 同范式）。
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    """请求级上下文 — 透传到深层调用栈的请求头集合。"""

    headers: dict = field(default_factory=dict)


_request_ctx: ContextVar[RequestContext] = ContextVar(
    "agent_builder_request_ctx", default=RequestContext()
)


def get_request_context() -> RequestContext:
    return _request_ctx.get()


def get_request_headers() -> dict:
    """请求头 getter，供 model_service ports 注入。"""
    return _request_ctx.get().headers or {}
