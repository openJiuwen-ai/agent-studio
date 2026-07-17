# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for RequestContext moderation_engine field."""

from agent_runtime.context.request_context import RequestContext, _request_ctx


class TestRequestContextModerationEngine:

    @staticmethod
    def test_default_moderation_engine_is_none():
        ctx = RequestContext()
        assert ctx.moderation_engine is None

    @staticmethod
    def test_moderation_engine_can_be_set():
        class FakeEngine:
            pass
        engine = FakeEngine()
        ctx = RequestContext(moderation_engine=engine)
        assert ctx.moderation_engine is engine

    @staticmethod
    def test_moderation_engine_via_context_var():
        class FakeEngine:
            pass
        engine = FakeEngine()
        ctx = RequestContext(moderation_engine=engine)
        _request_ctx.set(ctx)
        retrieved = _request_ctx.get()
        assert retrieved.moderation_engine is engine
        # Cleanup
        _request_ctx.set(RequestContext())
