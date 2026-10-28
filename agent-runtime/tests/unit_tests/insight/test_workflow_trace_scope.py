# -*- coding: UTF-8 -*-
"""workflow 遥测作用域（ContextVar 载体）单测（issue #1583 第 7 节）。

覆盖：默认空、进出作用域的绑定/恢复、None 容忍（空操作）、嵌套作用域
恢复外层、异常路径恢复、asyncio 任务继承（engine 组件任务的取用机制）。
"""

import asyncio

import pytest

from jiuwen.insight.workflow_trace_scope import (
    current_workflow_trace_manager,
    workflow_trace_scope,
)


class TestWorkflowTraceScope:
    def test_default_is_none(self):
        assert current_workflow_trace_manager() is None

    def test_bound_inside_and_restored_after_exit(self):
        sentinel = object()
        with workflow_trace_scope(sentinel) as bound:
            assert bound is sentinel
            assert current_workflow_trace_manager() is sentinel
        assert current_workflow_trace_manager() is None

    def test_none_is_noop(self):
        with workflow_trace_scope(None) as bound:
            assert bound is None
            assert current_workflow_trace_manager() is None

    def test_nested_scope_restores_outer(self):
        outer, inner = object(), object()
        with workflow_trace_scope(outer):
            with workflow_trace_scope(inner):
                assert current_workflow_trace_manager() is inner
            assert current_workflow_trace_manager() is outer
        assert current_workflow_trace_manager() is None

    def test_exception_path_still_resets(self):
        sentinel = object()
        with pytest.raises(RuntimeError):
            with workflow_trace_scope(sentinel):
                assert current_workflow_trace_manager() is sentinel
                raise RuntimeError("boom")
        assert current_workflow_trace_manager() is None

    @pytest.mark.asyncio
    async def test_asyncio_task_inherits_binding(self):
        """engine 为组件执行创建的 asyncio 任务在创建时拷贝当前
        context——这是 LLM 节点协程内能取到作用域绑定的机制基础。"""

        async def _read():
            return current_workflow_trace_manager()

        sentinel = object()
        with workflow_trace_scope(sentinel):
            task = asyncio.create_task(_read())
            assert await task is sentinel
        # 作用域退出后，本协程不受影响（任务内绑定随任务 context 生灭）
        assert current_workflow_trace_manager() is None
