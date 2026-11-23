# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""setup_otel_tracer 导入隔离/回退单测。

M1 评审关注点固化：StudioOtelWorkflowHandler 子类导入失败（openjiuwen 升级后
私有符号缺失/改名）时，回退官方 OtelWorkflowHandler，OTel 不静默停用。
"""
import builtins

import pytest

from openjiuwen.core.session.tracer import TracerHandlerRegistry
from openjiuwen.extensions.tracer_otel.handler import OtelWorkflowHandler

import agent_runtime.observability.tracer_otel as tracer_otel_mod

_real_import = builtins.__import__
_EXPLICIT_PARENT_SYM = "_explicit_parent_context"


def _block_studio_import(name, gdict=None, ldict=None, fromlist=(), level=0):
    if (
        name == "agent_runtime.observability.tracer_otel_studio"
        and fromlist
        and "StudioOtelWorkflowHandler" in fromlist
    ):
        raise ImportError("simulated: upstream private symbol missing")
    return _real_import(name, gdict, ldict, fromlist, level)


def _snapshot_explicit_parent():
    """保存上游 ``_explicit_parent_context``，setup 可能 monkey-patch 之。"""
    try:
        import openjiuwen.extensions.tracer_otel.handler as otel_handler
    except ImportError:
        return None, None
    handler_ns = getattr(otel_handler, "__dict__", {})
    if _EXPLICIT_PARENT_SYM not in handler_ns:
        return otel_handler, None
    return otel_handler, handler_ns[_EXPLICIT_PARENT_SYM]


def _restore_explicit_parent(otel_handler, original):
    if otel_handler is None or original is None:
        return
    setattr(otel_handler, _EXPLICIT_PARENT_SYM, original)


@pytest.mark.asyncio
async def test_fallbacks_to_official_handler_when_studio_unavailable(monkeypatch):
    prev_enabled = tracer_otel_mod.settings.otel.enabled
    tracer_otel_mod.settings.otel.enabled = True
    monkeypatch.setattr(builtins, "__import__", _block_studio_import)
    otel_handler, original_parent = _snapshot_explicit_parent()
    try:
        TracerHandlerRegistry.clear()
        tracer_otel_mod.setup_otel_tracer()
        handlers = TracerHandlerRegistry.get_workflow_handlers()
        assert isinstance(handlers.get("otel_workflow"), OtelWorkflowHandler)
    finally:
        tracer_otel_mod.settings.otel.enabled = prev_enabled
        TracerHandlerRegistry.clear()
        _restore_explicit_parent(otel_handler, original_parent)
