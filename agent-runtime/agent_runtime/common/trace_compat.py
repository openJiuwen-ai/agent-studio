# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""trace_id / 会话事实传递兼容层。

openjiuwen 0.1.16 的 create_workflow_session / create_agent_session 尚不接受 trace_id 参数，
待新版本已支持。本模块在 import 时检测签名，仅在底层支持时
才透传 trace_id，保证升级前后均不会报错。source_metadata（会话事实，
供遥测桥供给 openjiuwen.gen_ai.user.id）同一检测策略：旧版底层无该参数
且无 **kwargs 兜底时摘出不传，遥测增强不得劣化会话创建。
"""

from __future__ import annotations

import inspect

from jiuwen.common.log.base import get_x_request_id
from openjiuwen.core.session.agent import create_agent_session as _create_agent_session
from openjiuwen.core.workflow import create_workflow_session as _create_workflow_session


# 一次性检测底层是否支持目标参数
def _accepts_param(sig_params, name: str) -> bool:
    """Check if a function accepts a named param — either as explicit param or via **kwargs."""
    if name in sig_params:
        return True
    for p in sig_params.values():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False


_agent_params = inspect.signature(_create_agent_session).parameters
_wf_params = inspect.signature(_create_workflow_session).parameters
_agent_accepts_trace_id = _accepts_param(_agent_params, "trace_id")
_agent_accepts_source_metadata = _accepts_param(_agent_params, "source_metadata")
_wf_accepts_trace_id = _accepts_param(_wf_params, "trace_id")


def create_agent_session_with_trace(session_id: str = None, **kwargs):
    """创建 agent session，底层支持时透传 trace_id / source_metadata。"""
    trace_id = get_x_request_id()
    if _agent_accepts_trace_id and trace_id:
        kwargs["trace_id"] = trace_id
    # 旧版 create_agent_session 既无 source_metadata 参数也无 **kwargs 兜底，
    # 原样透传会 TypeError 破坏会话创建；不支持时摘出（遥测事实优雅降级）
    source_metadata = kwargs.pop("source_metadata", None)
    if _agent_accepts_source_metadata and source_metadata is not None:
        kwargs["source_metadata"] = source_metadata
    return _create_agent_session(session_id=session_id, **kwargs)


def create_workflow_session_with_trace(session_id: str = None, trace_id: str = None, **kwargs):
    """创建 workflow session，底层支持时透传 trace_id。"""
    # 优先使用显式传入的 trace_id（如 QA 恢复时从 Redis 读取的）
    if trace_id is None:
        trace_id = get_x_request_id()
    
    if _wf_accepts_trace_id and trace_id:
        kwargs["trace_id"] = trace_id
    return _create_workflow_session(session_id=session_id, **kwargs)
