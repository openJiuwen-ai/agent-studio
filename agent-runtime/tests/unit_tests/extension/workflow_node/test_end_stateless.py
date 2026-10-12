# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""End 组件跨执行隔离测试（静态图复用前提，issue #1555 / Task 9）。

End 在 wait_for_all=False 下会被 Pregel 引擎按入边多次触发，组件用四个能力
幂等标志（invoke/stream/collect/transform）防重复。实例复用后这些标志与 mix
协调状态若仍落在实例属性上，第二次执行会被直接短路（返回空）。本测试钉住：
1. 执行期状态按执行容器隔离（容器随会话 GC 回收）；
2. 容器键归一：引擎 on_invoke/on_stream/on_collect/on_transform 每次调用新建
   Session 包装器（component.py:95-119），包装器无 __eq__/__hash__ → 必须以
   底层 NodeSession 为键，否则同一执行的四个能力各建容器（mix 双路断裂、
   幂等失效）；
3. 末帧输出走 Task 1 的 ContextVar 通道（引擎 Vertex._post_stream 流耗尽后读取）；
4. 渲染隔离：共享 TemplateProcessor 按执行克隆，且能力入口不变更任何共享属性
   （否则并发执行 B 的入口会打断 A 在途的父类 _render）。
"""

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from openjiuwen.core.session.internal.workflow import NodeSession, WorkflowSession
from openjiuwen.core.session.node import Session as EngineSession

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node import end as end_module
from jiuwen.extension.workflow_node.end import End, _EndExecState


class _FakeSession:
    """可弱引用的会话替身（object() 实例不支持 weakref）。"""


def _end_conf():
    return {"name": "end", "outputMode": "direct", "responseTemplate": "{{answer}}"}


def _node_session(comp_id: str = "end_node") -> NodeSession:
    wf = WorkflowSession(workflow_id="test_wf", session_id="test_sess")
    return NodeSession(wf, comp_id, "End")


def _wrapper(node_session, stream_mode: bool = False) -> EngineSession:
    """引擎 on_* 每次调用新建的 Session 包装器（component.py:95-119）。"""
    return EngineSession(node_session, stream_mode)


def _mock_session(node_session=None) -> MagicMock:
    """驱动能力方法的 session 替身：包装器语义（_inner → NodeSession）+ io mock。

    `_inner` 是引擎 Session 包装器指向底层 NodeSession 的字段（session/node.py:14），
    也是容器键归一读取的字段。
    """
    session = MagicMock()
    session._inner = node_session if node_session is not None else _node_session()
    session.write_custom_stream = AsyncMock()
    session.get_global_state.return_value = ""
    session.get_env.return_value = 0.2  # 模板渲染超时（env 读取链路）
    return session


class TestEndExecStateIsolation:
    def test_exec_state_keyed_by_session(self):
        end = End(_end_conf())
        s1, s2 = _FakeSession(), _FakeSession()
        st1 = end._exec_state(s1)
        st2 = end._exec_state(s2)
        assert isinstance(st1, _EndExecState)
        assert st1 is not st2
        assert end._exec_state(s1) is st1  # 同 session 复用同一容器

    def test_engine_wrappers_normalize_to_same_container(self):
        """引擎每次能力调用新建的包装器 → 归一底层 NodeSession（C1）。"""
        end = End(_end_conf())
        node = _node_session()
        batch = _wrapper(node, False)      # on_invoke/on_stream 包装器
        stream = _wrapper(node, True)      # on_collect/on_transform 包装器
        assert batch is not stream
        assert end._exec_state(batch) is end._exec_state(stream)
        assert end._exec_state(node) is end._exec_state(batch)  # 裸 NodeSession 亦同键

    def test_flags_do_not_leak_across_executions(self):
        end = End(_end_conf())
        s1, s2 = _FakeSession(), _FakeSession()
        st1 = end._exec_state(s1)
        st1.invoke_executed = True
        st1.stream_executed = True
        st1.collect_executed = True
        st1.transform_executed = True
        st1.mix_render_complete = True
        st1.mix_push_count = 2
        st1.mix_batch_pushed = True
        st1.mix_data["batch"] = {"inputs": {}, "outputs": {}}

        st2 = end._exec_state(s2)
        assert st2.invoke_executed is False
        assert st2.stream_executed is False
        assert st2.collect_executed is False
        assert st2.transform_executed is False
        assert st2.mix_render_complete is False
        assert st2.mix_push_count == 0
        assert st2.mix_batch_pushed is False
        assert st2.mix_data == {}
        assert st2.mix_condition is None

    def test_weakref_releases_with_session(self):
        end = End(_end_conf())
        s = _FakeSession()
        end._exec_state(s)
        assert len(end._exec_states) == 1
        del s
        gc.collect()
        assert len(end._exec_states) == 0

    def test_instance_has_no_shared_exec_attrs(self):
        """执行期字段不再落在实例属性上（复用实例的共享面）。"""
        end = End(_end_conf())
        for attr in (
            "_stream_output",
            "_invoke_executed",
            "_stream_executed",
            "_collect_executed",
            "_transform_executed",
            "_mix_condition",
            "_mix_data",
            "_mix_push_count",
            "_mix_render_complete",
            "_mix_batch_pushed",
        ):
            assert not hasattr(end, attr), attr

    def test_stream_output_via_contextvar(self):
        """get_stream_output 读 ContextVar 通道，两次执行互不串扰。"""
        end = End(_end_conf())
        ctx.set_stream_final_output({"userFields": "first"})
        assert end.get_stream_output() == {"userFields": "first"}
        ctx.set_stream_final_output({"userFields": "second"})
        assert end.get_stream_output() == {"userFields": "second"}

    def test_reset_stream_output_delegates_to_contextvar(self):
        """_reset_stream_output 保留（外部 patch 调用方）但改走 ContextVar。"""
        end = End(_end_conf())
        ctx.set_stream_final_output({"userFields": "stale"})
        end._reset_stream_output()
        assert end.get_stream_output() is None


class TestEndCapabilityIsolation:
    @pytest.mark.asyncio
    async def test_second_execution_invoke_not_short_circuited(self):
        """复用实例：第二次执行（新 NodeSession → 新包装器）不被幂等标志短路。"""
        end = End(_end_conf())
        r1 = await end.invoke({"answer": "first"}, _mock_session(), None)
        assert r1 is not None and r1["answer"] == "first"
        assert r1["userFields"]["answer"] == "first"

        r2 = await end.invoke({"answer": "second"}, _mock_session(), None)
        # 修复前：self._invoke_executed 恒为 True → 第二次执行返回 {}
        assert r2 is not None and r2 != {}
        assert r2["answer"] == "second"
        assert r2["userFields"]["answer"] == "second"

    @pytest.mark.asyncio
    async def test_same_execution_two_wrappers_still_idempotent(self):
        """同一执行内两个包装器（引擎按入边分别触发）归一同一容器 → 仍幂等。"""
        end = End(_end_conf())
        node = _node_session()
        first_wrapper = _wrapper(node, False)
        second_wrapper = _wrapper(node, False)
        assert first_wrapper is not second_wrapper

        first = await end.invoke({"answer": "first"}, first_wrapper, None)
        assert first
        assert await end.invoke({"answer": "first"}, second_wrapper, None) == {}

    @pytest.mark.asyncio
    async def test_invoke_entry_resets_and_writes_final_output_channel(self):
        end = End(_end_conf())
        ctx.set_stream_final_output({"userFields": "stale"})
        await end.invoke({"answer": "fresh"}, _mock_session(), None)
        final = end.get_stream_output()
        assert final is not None
        assert final["user_fields"]["answer"] == "fresh"

    @pytest.mark.asyncio
    async def test_mix_two_paths_share_one_exec_state(self):
        """mix 双路（batch 包装器 + stream 包装器）解析同一容器：

        批路径 push 后等待，流路径 push 合并渲染并唤醒批路径；批路径让位
        （is_renderer=False）而非各等满 3s 超时自渲染出双份结束帧。
        键未归一时两路各建容器：批路径等满 3s 超时自渲染（本用例经
        asyncio.wait_for 1s 兜底暴露），push_count 也各自停在 1。
        """
        end = End(_end_conf())
        end.set_mix()
        node = _node_session()
        batch_sess = _mock_session(node)   # invoke/stream 路径包装器
        stream_sess = _mock_session(node)  # collect/transform 路径包装器
        assert end._exec_state(batch_sess) is end._exec_state(stream_sess)

        batch_task = asyncio.create_task(
            end._mix_coordinate("batch", {"b": 1}, {"ob": 1}, batch_sess)
        )
        await asyncio.sleep(0.05)  # 让批路径先 push 并进入等待
        merged_inputs, merged_outputs, is_renderer = await end._mix_coordinate(
            "stream", {"s": 2}, {"os": 2}, stream_sess
        )
        assert is_renderer is True  # 流路径负责渲染
        assert merged_inputs == {"s": 2, "b": 1}  # batch 侧优先
        assert merged_outputs == {"os": 2, "ob": 1}

        _, _, batch_is_renderer = await asyncio.wait_for(batch_task, timeout=1.0)
        assert batch_is_renderer is False  # 批路径让位，未超时自渲染

        st = end._exec_state(batch_sess)
        assert st.mix_push_count == 2
        assert st.mix_batch_pushed is True
        assert st.mix_render_complete is True


class TestEndRenderIsolation:
    def test_template_cloned_per_execution(self):
        end = End(_end_conf())
        pristine = end._template_source
        st1 = end._exec_state(_FakeSession())
        st2 = end._exec_state(_FakeSession())
        end._prepare_render_state(st1)
        end._prepare_render_state(st2)
        assert st1.template is not st2.template
        assert st1.template is not pristine
        assert type(st1.template) is type(pristine)
        # 执行外：解析回 build 期原对象（永不触碰）
        assert end._template is pristine

    def test_template_resolves_to_exec_clone_inside_execution(self):
        end = End(_end_conf())
        s1 = _FakeSession()
        st1 = end._exec_state(s1)
        end._prepare_render_state(st1)
        assert end._template is end._template_source  # 执行外
        token = end_module._current_exec_key.set(end._exec_key(s1))
        try:
            assert end._template is st1.template  # 执行内
        finally:
            end_module._current_exec_key.reset(token)
        assert end._template is end._template_source

    def test_template_clone_shared_within_execution(self):
        """同一执行内 batch/stream 两路必须共用同一克隆（mix 依赖共享位置推进）。"""
        end = End(_end_conf())
        st = end._exec_state(_FakeSession())
        end._prepare_render_state(st)
        t1 = st.template
        end._prepare_render_state(st)
        assert st.template is t1

    def test_template_clone_starts_at_zero_position(self):
        """克隆复位渲染位置（等价父类 set_mix 的 reset 语义）。"""
        end = End(_end_conf())
        end._template_source._current_position = 5
        end._template_source._chunk_index = 3
        end._template_source._count = 1
        st = end._exec_state(_FakeSession())
        end._prepare_render_state(st)
        assert st.template._current_position == 0
        assert st.template._chunk_index == 0

    def test_template_clone_has_own_sync_primitives(self):
        """克隆不共享 _lock/_condition（跨执行队头阻塞防护）。

        父类 _render_stream 在持有 _lock 期间逐帧 yield（模板变量为上游流式
        生成器时可长时间挂起）：浅拷贝共享同步原语会让执行 B 的渲染阻塞在
        执行 A 的在途帧上。同一执行内两路共用同一克隆，协调语义不变。
        """
        end = End(_end_conf())
        source = end._template_source
        st1 = end._exec_state(_FakeSession())
        st2 = end._exec_state(_FakeSession())
        end._prepare_render_state(st1)
        end._prepare_render_state(st2)
        assert st1.template._lock is not st2.template._lock
        assert st1.template._condition is not st2.template._condition
        assert st1.template._lock is not source._lock
        assert st2.template._condition is not source._condition
        # 同一执行复用同一克隆（同步原语不重建）
        lock1 = st1.template._lock
        end._prepare_render_state(st1)
        assert st1.template._lock is lock1

    def test_capability_entry_does_not_mutate_shared_attrs(self):
        """能力入口不得变更共享属性（I1 不变量）。

        原实现入口做 `self._template = 克隆` + `self._batch_template = None`：
        执行 B 的入口会清掉执行 A 在途 _render 的 latch（end_comp.py:239-240
        在 await 后重读 self._batch_template → None → AttributeError）。
        """
        end = End(_end_conf())
        pristine = end._template_source
        st = end._exec_state(_FakeSession())
        end._prepare_render_state(st)
        assert end._template_source is pristine
        assert end._template is pristine
        assert end._batch_template_source is None
        assert end._batch_template is None

    def test_batch_template_latch_resolves_per_execution(self):
        """父类 _render 的 batch 渲染器 latch 按执行隔离（不落共享属性）。"""
        end = End(_end_conf())
        s1, s2 = _FakeSession(), _FakeSession()
        st1 = end._exec_state(s1)
        token = end_module._current_exec_key.set(end._exec_key(s1))
        try:
            end._batch_template = "processor-of-exec-1"
            assert st1.batch_template == "processor-of-exec-1"
            assert end._batch_template == "processor-of-exec-1"
        finally:
            end_module._current_exec_key.reset(token)
        assert end._batch_template is None  # 执行外
        assert end._batch_template_source is None

        token = end_module._current_exec_key.set(end._exec_key(s2))
        try:
            assert end._batch_template is None  # 另一执行看不到执行 1 的 latch
        finally:
            end_module._current_exec_key.reset(token)
        assert end._exec_state(s2).batch_template is None

    @pytest.mark.asyncio
    async def test_entry_does_not_break_inflight_batch_render(self):
        """执行 A 在途 _render 挂起期间执行 B 走完整入口：A 不受影响（I1）。

        A 的模板变量喂入阻塞生成器 → A 确定性地停在渲染中（不依赖超时窗口）；
        B 在此期间走完整入口 + 渲染。原实现 B 的入口清 self._batch_template
        → A 恢复即 AttributeError（end_comp.py:239-240）。
        """
        end = End(_end_conf())
        release = asyncio.Event()

        async def _blocking_answer():
            yield "a"  # 首帧后阻塞，A 稳定停在渲染中
            await release.wait()
            yield "!"

        a_sess = _mock_session(_node_session("end_a"))
        a_task = asyncio.create_task(
            end.invoke({"answer": _blocking_answer()}, a_sess, None)
        )
        st_a = end._exec_state(a_sess)
        deadline = asyncio.get_running_loop().time() + 1.0
        while st_a.batch_template is None and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.01)
        assert not a_task.done()
        assert st_a.batch_template is not None  # A 在途持有 batch latch
        assert st_a.template._current_position == 0  # A 仍停在渲染中（未推进）

        b_result = await end.invoke(
            {"answer": "b"}, _mock_session(_node_session("end_b")), None
        )
        assert b_result is not None and b_result["answer"] == "b"
        assert not a_task.done()  # B 完整执行期间 A 始终在途（真实重叠）
        # B 的入口/渲染不改动 A 的执行状态
        assert end._exec_state(a_sess).batch_template is st_a.batch_template

        release.set()
        a_result = await asyncio.wait_for(a_task, timeout=2.0)
        assert a_result is not None and a_result["answer"] == "a!"  # A 自身渲染完成
