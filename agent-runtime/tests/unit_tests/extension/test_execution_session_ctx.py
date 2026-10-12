# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""execution_session_ctx：执行期 session 的 ContextVar 通道单测。

三个通道的写入/读取/隔离语义（模块 docstring 详述"谁写谁读"），
以及 resolve_routing_session 的三层解析顺序（Patch C 语义）。
"""
import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


class TestWorkflowSessionChannel:
    def test_set_and_reset(self):
        sentinel = object()
        token = ctx.set_workflow_session(sentinel)
        assert ctx.current_workflow_session() is sentinel
        ctx.reset_workflow_session(token)
        assert ctx.current_workflow_session() is None

    def test_default_is_none(self):
        assert ctx.current_workflow_session() is None


class TestComponentExecChannel:
    def test_set_and_reset(self):
        s, c = object(), object()
        token = ctx.set_component_exec(s, c)
        assert ctx.current_component_exec() == (s, c)
        ctx.reset_component_exec(token)
        assert ctx.current_component_exec() == (None, None)


class TestStreamFinalOutputChannel:
    def test_set_without_reset_is_visible(self):
        # 语义：不 reset——引擎 Vertex._post_stream 在 generator 耗尽后读取
        ctx.set_stream_final_output({"userFields": "x"})
        assert ctx.get_stream_final_output() == {"userFields": "x"}
        ctx.set_stream_final_output(None)
        assert ctx.get_stream_final_output() is None


class TestResolveRoutingSession:
    def test_priority_component_over_workflow_over_fallback(self):
        component_s, workflow_s, fallback_s = object(), object(), object()

        # 仅 fallback
        assert ctx.resolve_routing_session(fallback_s) is fallback_s

        # + workflow 层
        t1 = ctx.set_workflow_session(workflow_s)
        assert ctx.resolve_routing_session(fallback_s) is workflow_s

        # + component 层（最高优先级）
        t2 = ctx.set_component_exec(component_s, None)
        assert ctx.resolve_routing_session(fallback_s) is component_s

        # 逐层退栈
        ctx.reset_component_exec(t2)
        assert ctx.resolve_routing_session(fallback_s) is workflow_s
        ctx.reset_workflow_session(t1)
        assert ctx.resolve_routing_session(fallback_s) is fallback_s
