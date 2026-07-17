#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
请求级上下文 — 透传 HTTP 请求头和请求级参数到深层调用栈

使用 contextvars 实现协程安全的请求作用域存储。
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestContext:
    """请求级上下文 — 所有需要透传到深层的参数集中管理"""

    headers: dict = field(default_factory=dict)
    user_id: str = ""
    conversation_id: str = ""
    execution_id: str = ""
    request_id: str = ""
    secret_env_keys: list = field(default_factory=list)
    # 当前节点引用了加密环境变量的字段名集合（由 on_* 入口设置，供模板渲染层读取）
    current_secret_field_names: dict = field(default_factory=dict)
    # 内容审核引擎实例（由请求入口设置，供审核节点读取）
    moderation_engine: Any = None


_request_ctx: ContextVar[RequestContext] = ContextVar(
    "request_ctx", default=RequestContext()
)
