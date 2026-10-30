# -*- coding: UTF-8 -*-
"""workflow 遥测作用域（ContextVar 载体）单测（issue #1583 第 7 节）。

覆盖：默认空、进出作用域的绑定/恢复、None 容忍（空操作）、嵌套作用域
恢复外层、异常路径恢复、asyncio 任务继承（engine 组件任务的取用机制）、
scoped_astream 消费包装（绑定收敛到内层步进期间，跨 yield 零残留）。
"""

import asyncio

import pytest

from jiuwen.insight.workflow_trace_scope import (
    current_workflow_trace_manager,
    scoped_astream,
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


class TestScopedAstream:
    """scoped_astream：作用域绑定收敛到内层流步进期间（检视意见）。"""

    @pytest.mark.asyncio
    async def test_inner_bound_sibling_tasks_between_yields_clean(self):
        """with 直接包住含 yield 的 async for 会让绑定滞留在消费方 Task
        上下文——两次 yield 之间 create_task 的兄弟任务继承该作用域、
        错误归属遥测。scoped_astream 只在步进内层期间绑定。"""

        async def _read():
            return current_workflow_trace_manager()

        sentinel = object()
        seen = []

        async def _gen():
            for i in range(2):
                seen.append(current_workflow_trace_manager())
                yield i

        got = []
        async for item in scoped_astream(lambda: _gen(), sentinel):
            got.append(item)
            # 消费方两次 yield 之间：自身与兄弟任务都不得继承工作流作用域
            assert current_workflow_trace_manager() is None
            assert await asyncio.create_task(_read()) is None

        assert got == [0, 1]
        assert seen == [sentinel, sentinel]  # 内层步进期间始终绑定

    @pytest.mark.asyncio
    async def test_none_trace_manager_passthrough(self):
        """独立工作流（无 trace_handlers）：None 容忍，照常透传流内容。"""

        async def _nums():
            for i in range(3):
                yield i

        got = []
        async for item in scoped_astream(lambda: _nums(), None):
            got.append(item)
        assert got == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_early_close_propagates_to_inner(self):
        """提前关闭（上层 break / aclose）：关闭透传给内层生成器。"""
        closed = []

        async def _gen():
            try:
                yield 1
                yield 2
            finally:
                closed.append(True)

        gen = scoped_astream(lambda: _gen(), object())
        assert await gen.__anext__() == 1
        await gen.aclose()
        assert closed == [True]
