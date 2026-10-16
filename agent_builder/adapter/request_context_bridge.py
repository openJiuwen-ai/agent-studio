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
from enum import Enum


class ContextSource(str, Enum):
    """请求上下文的入口来源标记（COM-05）。

    仅由内部入口代码设置，不从外部输入读取；默认 NONE 以区分"尚未建立"
    与"已建立的 Flask direct"。mounted 形态下外层 FastAPI 中间件已建立
    上下文，Flask before_request 据此桥接而非二次建立。
    """

    NONE = "NONE"
    FASTAPI_MOUNT = "FASTAPI_MOUNT"
    FLASK_DIRECT = "FLASK_DIRECT"


@dataclass
class RequestContext:
    """请求级上下文 — 透传到深层调用栈的请求头集合。

    分仓：``headers`` 为平台 header（X-*），``customer_headers`` 为客户 header
    （cust-*，值为 ``HeaderValue``）。两者独立，compat ``headers`` 不含客户 header。
    """

    headers: dict = field(default_factory=dict)
    customer_headers: dict = field(default_factory=dict)
    # 已加载的环境变量（load_environment_variables 产出；由 populate_request_context
    # 中间件按 X-Environment-Id 加载写入，供 StudioModelClient 解析 apiUrl 占位符）
    env_variables: dict = field(default_factory=dict)
    # COM-05: Builder 固定外层 request_id 槽位；缺失时输出空串，不回退 trace_id。
    request_id: str = ""
    # 入口来源标记（mounted 桥接 / Flask direct / 未建立）
    source: ContextSource = ContextSource.NONE


_request_ctx: ContextVar[RequestContext] = ContextVar(
    "agent_builder_request_ctx", default=RequestContext()
)


def get_request_context() -> RequestContext:
    return _request_ctx.get()


def get_request_headers() -> dict:
    """请求头 getter，供 model_service ports 注入。"""
    return _request_ctx.get().headers or {}


def get_request_customer_headers() -> dict:
    """客户 header getter（Mapping[str, HeaderValue]），供 model_service ports 注入。

    无请求上下文时返回空 dict，不回退静态认证 Header。
    """
    return _request_ctx.get().customer_headers or {}


def get_env_variables() -> dict:
    """环境变量 getter，供 model_service ports 注入（StudioModelClient 解析 apiUrl 占位符）。"""
    return _request_ctx.get().env_variables or {}


def get_request_id() -> str:
    """返回当前请求的 request_id；无上下文或 COM-05 尚未选定时返回空串。

    调用方据此输出空槽，不得以 trace_id 或其他字段回填（DEF-05）。
    """
    return _request_ctx.get().request_id or ""
