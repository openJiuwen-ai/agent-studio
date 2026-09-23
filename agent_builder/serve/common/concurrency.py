# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""DEF-07: Builder 线程池日志 ContextVar 传播与清理（SYNC-01 P3.3 从旧分支移植）。

三个提交器，按传播范围递减：

- ``submit_with_log_context``：顶层任务。同时传播 Python ContextVar 快照 + Flask
  请求上下文（``copy_current_request_context``）。固定顺序：Context 外层、Flask 内层。
- ``submit_with_contextvars``：全量复制当前 ContextVar（``copy_context()``），不传播
  Flask。用于确认提交点不存在不应扩散的 Flask 请求上下文的受控调用。
- ``submit_with_log_vars``：内层任务。只传播经批准的 trace_id + Builder 请求桥
  （``RequestContext``），通过 token/set/reset 安装，不 ``copy_context()``——避免
  ``copy_context()`` 连带扩散 Flask 请求/应用上下文到内层工作线程。

工作线程结束 finally 逆序恢复，不串号、不残留。
"""

import contextvars

from flask import copy_current_request_context
try:
    from openjiuwen.core.common.logging import reset_session_id
except ImportError:
    def reset_session_id(_token):
        pass  # 兼容 agent-core 未合入 DEF-03

from agent_builder.adapter.logger_bridge import get_session_id, set_session_id
from agent_builder.adapter.request_context_bridge import (
    _request_ctx,
    get_request_context,
)


def submit_with_log_context(executor, func, *args, **kwargs):
    """顶层任务提交器：传播 ContextVar 快照 + Flask 请求上下文。

    ``copy_current_request_context`` 必须在提交者线程上 Flask 请求上下文激活时调用；
    Flask push 发生在 ``ctx.run`` 内，以保持 ContextVar 快照不被 Flask 覆写。
    """
    flask_wrapped = copy_current_request_context(func)
    ctx = contextvars.copy_context()
    return executor.submit(ctx.run, flask_wrapped, *args, **kwargs)


def submit_with_contextvars(executor, func, *args, **kwargs):
    """全量 ContextVar 传播（非 Flask）。复制所有当前 ContextVar，不仅是日志变量。"""
    ctx = contextvars.copy_context()
    return executor.submit(ctx.run, func, *args, **kwargs)


def submit_with_log_vars(executor, func, *args, **kwargs):
    """内层任务提交器：只传播 trace_id + Builder 请求桥（token/set/reset）。

    在提交时捕获 trace_id 与 bridge（RequestContext），在工作线程上用 token
    重新安装，finally 逆序恢复。不 ``copy_context()``——避免内层池扩散 Flask
    请求/应用上下文。
    """
    trace_id = get_session_id()
    bridge = get_request_context()

    def _runner():
        trace_token = set_session_id(trace_id)
        bridge_token = _request_ctx.set(bridge)
        try:
            return func(*args, **kwargs)
        finally:
            _request_ctx.reset(bridge_token)
            reset_session_id(trace_token)

    return executor.submit(_runner)
