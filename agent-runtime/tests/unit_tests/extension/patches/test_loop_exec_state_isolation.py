# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 本文件是循环执行期状态隔离的白盒回归测试：断言观测面即补丁模块的执行期
# ContextVar（_LOOP_EXEC_SESSION）与引擎实例的 _post_body——二者都没有公开
# 访问入口，只能直接读写以模拟并发执行窗口、验证 A/B 会话状态互不可见。
# pylint: disable=protected-access
"""AdvancedLoopComponent 执行期状态会话隔离单测（10 并发压测第 3~5 轮失败回归）。

背景（issue：静态图复用 10 并发压测 round3 失败率 ~70%）：

静态图复用后同一 ``AdvancedLoopComponent`` 实例被并发会话共享，而引擎把
循环执行期状态放在共享实例字段上：

1. ``self._node_session``：``break_loop()`` 把 ``_broken`` 写进「最后进入
   循环的会话」的 session，``is_broken()`` 也从它读——并发下 A 的 break
   标志丢失，循环不退出 → 循环体重跑 → 体内子工作流二次执行（中断恢复
   场景下 QA 节点以 END 状态重入并重复提问）；
2. ``PostLoopBody._finish_index``：轮次完成计数跨会话串值。

用例以「进入循环 = 设置执行期上下文（ContextVar）」模拟 on_invoke 的
执行期窗口，断言 A/B 两个并发执行的 break 标志与轮次计数互不可见。
"""
import asyncio
from unittest.mock import MagicMock

import pytest

# 打断 openjiuwen 循环 import（与 test_static_graph_patch 同因）
import openjiuwen.core.workflow  # noqa: F401

from jiuwen.extension.patches import loop_body_session_cleanup_patch as patch_mod


@pytest.fixture(autouse=True)
def _apply_patches():
    """确保三处循环补丁已应用（import 链外独立运行 -k 时兜底）。"""
    patch_mod.apply_loop_body_session_cleanup_patch()
    patch_mod.apply_loop_state_cleanup_patch()
    patch_mod.apply_loop_exec_state_isolation_patch()
    yield


def _make_loop_session(tag: str):
    """最小循环 session mock：state() 具备真实 dict 语义（get/update/commit）。"""
    store: dict = {}
    state = MagicMock()

    def _get_state(key=None):
        return store.get(key) if key is not None else dict(store)

    def _update_state(data):
        store.update(data)

    state.get.side_effect = _get_state
    state.update.side_effect = _update_state
    state.commit = MagicMock()
    state.set_outputs = MagicMock()
    session = MagicMock()
    session.session_id.return_value = f"sess-{tag}"
    session.state.return_value = state
    session.store = store
    return session


def _make_loop_component():
    from openjiuwen.core.workflow.components.condition.condition import AlwaysTrue
    from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
        AdvancedLoopComponent,
    )

    return AdvancedLoopComponent(body=MagicMock(), condition=AlwaysTrue())


class TestLoopExecStateIsolation:
    @pytest.mark.asyncio
    async def test_break_flag_isolated_between_concurrent_executions(self):
        """A 的 break 标志不得因 B 进入循环（覆盖共享实例字段）而丢失。

        旧实现：break 写共享实例的 ``_node_session``，B 进入循环后 A 的
        条件判定读到 B 的会话 → False → 循环不退出、循环体重跑。
        """
        comp = _make_loop_component()
        session_a = _make_loop_session("A")
        session_b = _make_loop_session("B")

        # A 执行：循环体内 LoopBreakComponent 触发 break
        token_a = patch_mod._LOOP_EXEC_SESSION.set(session_a)
        try:
            comp.break_loop()
        finally:
            patch_mod._LOOP_EXEC_SESSION.reset(token_a)

        # B 执行：条件判定不得看到 A 的 break 标志
        token_b = patch_mod._LOOP_EXEC_SESSION.set(session_b)
        try:
            assert comp.is_broken() is False, (
                "B 读到 A 的 break 标志——退出标志跨并发执行串台"
            )
        finally:
            patch_mod._LOOP_EXEC_SESSION.reset(token_b)

        # A 恢复执行：自己的 break 标志仍在
        token_a = patch_mod._LOOP_EXEC_SESSION.set(session_a)
        try:
            assert comp.is_broken() is True, (
                "A 的 break 标志丢失——循环不会退出，循环体将重跑"
            )
        finally:
            patch_mod._LOOP_EXEC_SESSION.reset(token_a)

    @pytest.mark.asyncio
    async def test_finish_index_isolated_between_concurrent_executions(self):
        """轮次完成计数按执行期会话累计：B 的首轮计数不得叠在 A 的计数上。"""
        comp = _make_loop_component()
        post_body = comp._post_body
        session_a = _make_loop_session("A")
        session_b = _make_loop_session("B")

        token_a = patch_mod._LOOP_EXEC_SESSION.set(session_a)
        try:
            await post_body.on_invoke({}, session_a)
            await post_body.on_invoke({}, session_a)
            assert post_body.get_finish_index() == 1
        finally:
            patch_mod._LOOP_EXEC_SESSION.reset(token_a)

        token_b = patch_mod._LOOP_EXEC_SESSION.set(session_b)
        try:
            await post_body.on_invoke({}, session_b)
            assert post_body.get_finish_index() == 0, (
                "B 的首轮计数叠加了 A 的计数——轮次计数跨执行串台"
            )
        finally:
            patch_mod._LOOP_EXEC_SESSION.reset(token_b)

        # A 的计数不受 B 影响
        token_a = patch_mod._LOOP_EXEC_SESSION.set(session_a)
        try:
            assert post_body.get_finish_index() == 1
        finally:
            patch_mod._LOOP_EXEC_SESSION.reset(token_a)

    @pytest.mark.asyncio
    async def test_concurrent_tasks_see_own_execution_state(self):
        """真实并发任务下（ContextVar 按任务隔离）：交错执行的 break 不互踩。"""
        comp = _make_loop_component()
        session_a = _make_loop_session("A")
        session_b = _make_loop_session("B")

        a_broken = asyncio.Event()
        b_checked = asyncio.Event()
        seen = {}

        async def run_a():
            token = patch_mod._LOOP_EXEC_SESSION.set(session_a)
            try:
                comp.break_loop()
                a_broken.set()
                await b_checked.wait()
                seen["a"] = comp.is_broken()
            finally:
                patch_mod._LOOP_EXEC_SESSION.reset(token)

        async def run_b():
            token = patch_mod._LOOP_EXEC_SESSION.set(session_b)
            try:
                await a_broken.wait()
                seen["b"] = comp.is_broken()
                b_checked.set()
            finally:
                patch_mod._LOOP_EXEC_SESSION.reset(token)

        await asyncio.gather(run_a(), run_b())

        assert seen["b"] is False, "B 读到 A 的 break 标志（并发任务间串台）"
        assert seen["a"] is True, "A 恢复后自己的 break 标志丢失"
