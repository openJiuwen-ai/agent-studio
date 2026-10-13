# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""FlowQA / ComplexIntentDetection 同实例并发执行隔离测试（PR #1 评审修复轮）。

评审 Critical-1 / Critical-2：静态图复用后同一组件实例被并发执行共享，
执行期状态不能再落在共享实例字段上——

1. ``FlowQA._node_state``：invoke 把执行期 state 写共享实例字段并在
   await 点（``_write_interaction_stream`` / ``session.interact``）之后
   回读。并发执行 A/B 时，A 挂起期间 B 入口重建 ``self._node_state``，
   A 恢复后 ``_store_state_to_session(self._node_state, session_a)`` 会把
   B 的 state 存进 A 的 session（inputs/question 污染）。
2. ``ComplexIntentDetection._state``：invoke 入口重建共享实例字段，
   同步链读写（子工作流返回 → status → 聚合）虽然原子，但落实例违反
   spec「执行期状态不落实例」原则，且 ``_invoke_sub_workflow`` 的
   await 点（``_init_sub_workflow`` 的 storage 读）之后存在
   ``self._state`` 读点（is_resuming / interrupt_child_node_id），
   未来任一读点活化即成真竞态。局部化 + 调用链显式传递。

用例以 ``asyncio.Event`` / ``Future`` 编排确定性交错（真挂起、真恢复），
不依赖 sleep 时序。
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


@pytest.fixture(autouse=True)
def _clean_exec_channels():
    """执行期 ContextVar 通道进程内共享，用例前后复位避免互相串扰。"""
    ctx.set_component_exec(None, None)
    ctx.set_component_state(None)
    ctx.set_stream_final_output(None)
    yield
    ctx.set_component_exec(None, None)
    ctx.set_component_state(None)
    ctx.set_stream_final_output(None)


def _qa_conf(need_reply: bool) -> dict:
    return {
        "name": "qa",
        "needReply": need_reply,
        "qaStrategy": "index",
        "options": ["opt-{{name}}"],
        "index_key": "index",
    }


def _make_qa_session(tag: str, interact_impl=None):
    """FlowQA 最小 session mock：状态字典持久化模拟 session 真源。

    update_state 写入 / get_state 读出同一底层 dict，模拟真实 Session 的
    state 行为（FlowQA 的中断-恢复依赖入口 _load_state_from_session）。
    """
    session = MagicMock()
    session.get_component_id.return_value = f"node-{tag}"
    session.get_session_id.return_value = f"sess-{tag}"
    session.get_session_id = MagicMock(return_value=f"sess-{tag}")
    stored: dict = {}
    session.update_state.side_effect = lambda d, _s=stored: _s.update(d)
    session.get_state.side_effect = lambda *a, **k: dict(stored)
    session.stored = stored
    session.written = []

    async def _write(data):
        session.written.append(data)

    session.write_custom_stream = AsyncMock(side_effect=_write)
    if interact_impl is not None:
        session.interact = AsyncMock(side_effect=interact_impl)
    return session


class TestFlowQAConcurrentIsolation:
    @pytest.mark.asyncio
    async def test_concurrent_no_reply_executions_isolate_session_state(self):
        """need_reply=False 并发：A 挂起在流式写期间 B 完整执行，A 恢复后
        存进自己 session 的必须是 A 的 inputs（Critical-1 行为回归）。"""
        from jiuwen.extension.workflow_node.flow_qa import FlowQA

        qa = FlowQA(_qa_conf(need_reply=False))

        a_at_write = asyncio.Event()
        b_done = asyncio.Event()

        def make_session(tag: str):
            session = _make_qa_session(tag)

            async def _write(data):
                if tag == "A":
                    a_at_write.set()
                    await b_done.wait()
                session.written.append(data)

            session.write_custom_stream = AsyncMock(side_effect=_write)
            return session

        session_a = make_session("A")
        session_b = make_session("B")

        task_a = asyncio.create_task(qa.invoke({"name": "A"}, session_a, MagicMock()))
        await a_at_write.wait()  # A 挂起在 write_custom_stream（_node_state.inputs == A）

        result_b = await qa.invoke({"name": "B"}, session_b, MagicMock())
        b_done.set()
        result_a = await task_a

        # 返回值链是局部变量传递，两执行各自正确
        assert result_a == {"userFields": {"response": "opt-A"}}
        assert result_b == {"userFields": {"response": "opt-B"}}

        # session 持久化真源互不污染：修复前 A 存入的是被 B 重建覆盖的 state
        assert session_a.stored["flow_qa_state"]["inputs"] == {"name": "A"}
        assert session_a.stored["flow_qa_state"]["status"] == "end"
        assert session_b.stored["flow_qa_state"]["inputs"] == {"name": "B"}
        assert session_b.stored["flow_qa_state"]["status"] == "end"

    @pytest.mark.asyncio
    async def test_concurrent_need_reply_resume_isolates_session_state(self):
        """need_reply=True 并发：A 恢复轮挂起在 interact 期间 B 交错执行，
        A 的用户回复到达后，A session 里的终态必须是 A 自己的
        question/inputs（Critical-1 恢复路径回归）。

        中断-恢复语义：START 轮 invoke 返回 None（interact 返回即结束），
        恢复轮走 USER_INTERACT 分支返回用户回复。污染点是恢复轮
        ``await session.interact`` 之后的状态写回（status=END + store）。
        """
        from jiuwen.extension.workflow_node.flow_qa import FlowQA

        qa = FlowQA(_qa_conf(need_reply=True))

        a_at_interact = asyncio.Event()
        a_futures: list = []

        async def _interact_a(value):
            fut = asyncio.get_event_loop().create_future()
            a_futures.append(fut)
            a_at_interact.set()
            return await fut

        async def _interact_b(value):
            return "answer-B"

        session_a = _make_qa_session("A", interact_impl=_interact_a)
        session_b = _make_qa_session("B", interact_impl=_interact_b)

        # A START 轮：流式写 → 存 USER_INTERACT → 挂起在 interact
        task_a1 = asyncio.create_task(qa.invoke({"name": "A"}, session_a, MagicMock()))
        await a_at_interact.wait()
        a_at_interact.clear()

        # B 完整周期（A 挂起期间交错）：START 轮 + 恢复轮
        await qa.invoke({"name": "B"}, session_b, MagicMock())
        result_b = await qa.invoke({"name": "B"}, session_b, MagicMock())
        assert result_b == {"userFields": {"response": "answer-B"}}

        # A START 轮收尾（语义上返回 None）
        a_futures[0].set_result("answer-A")
        assert await task_a1 is None

        # A 恢复轮：USER_INTERACT 分支，挂起在 interact 等第二次用户回复
        task_a2 = asyncio.create_task(qa.invoke({"name": "A"}, session_a, MagicMock()))
        await a_at_interact.wait()

        # B 重开一轮（A 恢复轮挂起期间交错：END → 重新开始 → START）
        await qa.invoke({"name": "B"}, session_b, MagicMock())

        # A 的第二次用户回复到达，A 恢复轮写回终态
        a_futures[1].set_result("answer-A2")
        result_a = await task_a2
        assert result_a == {"userFields": {"response": "answer-A2"}}

        # A session 终态是 A 自己的状态：修复前恢复轮挂起期间 B 交错，
        # 写回的是 B 交错的 state（question == "opt-B"、inputs == {"name": "B"}）
        final_a = session_a.stored["flow_qa_state"]
        assert final_a["status"] == "end"
        assert final_a["question"] == "opt-A"
        assert final_a["inputs"] == {"name": "A"}

    def test_no_shared_node_state_instance_field(self):
        """源码级：执行期状态不再落实例字段（spec 附录 A 4 型审计项）。"""
        import inspect

        from jiuwen.extension.workflow_node.flow_qa import FlowQA

        src = inspect.getsource(FlowQA)
        assert "self._node_state" not in src

        qa = FlowQA(_qa_conf(need_reply=False))
        assert not hasattr(qa, "_node_state")

    def test_escape_surface_reads_component_state_channel(self):
        """逃逸面 get_state/get_node_status/should_interrupt 经执行期组件状态
        通道读取（invoke 外无执行期上下文 → 初始状态）。"""
        from jiuwen.extension.workflow_node.flow_qa import (
            ExecutionStatus,
            FlowQA,
            QAState,
        )

        qa = FlowQA(_qa_conf(need_reply=False))

        # invoke 外：无执行期上下文
        assert isinstance(qa.get_state(), QAState)
        assert qa.get_state().status == ExecutionStatus.START
        assert qa.get_node_status() == ExecutionStatus.START
        assert qa.should_interrupt() is False

        # invoke 内（模拟）：通道值可见
        state = QAState(status=ExecutionStatus.USER_INTERACT, question="q")
        token = ctx.set_component_state(state)
        try:
            assert qa.get_state() is state
            assert qa.get_node_status() == ExecutionStatus.USER_INTERACT
            assert qa.should_interrupt() is True
        finally:
            ctx.reset_component_state(token)


def _cid_conf() -> dict:
    """双分支 CID 配置（并发执行走不同分支）。"""
    return {
        "name": "cid",
        "intentDetectionContainerNodeId": "sub",
        "branches": [
            {
                "id": "branch_0",
                "catalog": "其他意图",
                "configs": {"workflow_id": "wf-a"},
            },
            {
                "id": "branch_1",
                "catalog": "业务办理",
                "configs": {"workflow_id": "wf-b"},
            },
        ],
        "groups": {"g1": ["${branch_0.result}"], "g2": ["${branch_1.result}"]},
    }


class TestCIDConcurrentIsolation:
    @staticmethod
    def _component():
        from agent_runtime.extension.workflow_node.complex_intent_detection import (
            ComplexIntentDetection,
        )

        return ComplexIntentDetection(_cid_conf(), node_id="cid_node", node_name="cid")

    @pytest.mark.asyncio
    async def test_concurrent_executions_isolate_branch_and_aggregation(self):
        """同实例并发执行：A 挂起在意图识别 await 期间 B 完整执行，A/B 的
        分支选择与分组聚合互不覆盖（Critical-2 行为回归）。"""
        comp = self._component()

        a_at_intent = asyncio.Event()
        b_done = asyncio.Event()

        async def _intent_invoke(inputs, session, context, **kwargs):
            tag = "A" if inputs.get("input") == "a" else "B"
            if tag == "A":
                a_at_intent.set()
                await b_done.wait()
                return {"classificationId": 0, "result": "A-intent"}
            return {"classificationId": 1, "result": "B-intent"}

        comp._intent_detection = MagicMock()
        comp._intent_detection.invoke = _intent_invoke

        async def _fake_init(workflow_id, branch_config, sub_workflows):
            tag = "A" if workflow_id == "wf-a" else "B"
            sub_workflow = MagicMock()

            async def _sub_invoke(
                sub_inputs, sub_session, sub_context, is_resuming=False, **kw
            ):
                return {"responseContent": f"{tag}-res", "result": f"{tag}-out"}

            sub_workflow.invoke = _sub_invoke
            sub_workflow.get_state = MagicMock(return_value={"status": "END"})
            sub_workflows[workflow_id] = {
                "instance": sub_workflow,
                "sub_instance": None,
                "configs": {},
            }

        comp._init_sub_workflow = _fake_init

        def make_session(tag: str):
            session = MagicMock(spec_set=["get_state", "get_session_id"])
            session.get_state = MagicMock(return_value={})
            session.get_session_id = MagicMock(return_value=f"sess-{tag}")
            return session

        session_a = make_session("A")
        session_b = make_session("B")

        task_a = asyncio.create_task(comp.invoke({"input": "a"}, session_a, MagicMock()))
        await a_at_intent.wait()  # A 挂起在 _intent_detection.invoke

        result_b = await comp.invoke({"input": "b"}, session_b, MagicMock())
        b_done.set()
        result_a = await task_a

        # 各自的分支选择与子工作流结果
        assert result_a["responseContent"] == "A-res"
        assert result_b["responseContent"] == "B-res"
        # 各自的分组聚合（branch_0 → g1 / branch_1 → g2）
        assert result_a["g1"] == "A-out"
        assert result_b["g2"] == "B-out"
        assert result_a["result"] == "A-intent"
        assert result_b["result"] == "B-intent"

    @pytest.mark.asyncio
    async def test_concurrent_graph_interrupt_propagates(self):
        """并发下 GraphInterrupt 正常传播（中断路径行为不变）。"""
        from openjiuwen.core.graph.pregel import GraphInterrupt

        comp = self._component()

        a_at_intent = asyncio.Event()
        b_done = asyncio.Event()

        async def _intent_invoke(inputs, session, context, **kwargs):
            tag = "A" if inputs.get("input") == "a" else "B"
            if tag == "A":
                a_at_intent.set()
                await b_done.wait()
                return {"classificationId": 0, "result": "A-intent"}
            return {"classificationId": 1, "result": "B-intent"}

        comp._intent_detection = MagicMock()
        comp._intent_detection.invoke = _intent_invoke

        async def _fake_init(workflow_id, branch_config, sub_workflows):
            tag = "A" if workflow_id == "wf-a" else "B"
            sub_workflow = MagicMock()

            async def _sub_invoke(
                sub_inputs, sub_session, sub_context, is_resuming=False, **kw
            ):
                if tag == "A":
                    raise GraphInterrupt("child interact")
                return {"responseContent": f"{tag}-res", "result": f"{tag}-out"}

            sub_workflow.invoke = _sub_invoke
            sub_workflow.get_state = MagicMock(return_value={"status": "END"})
            sub_workflows[workflow_id] = {
                "instance": sub_workflow,
                "sub_instance": None,
                "configs": {},
            }

        comp._init_sub_workflow = _fake_init

        def make_session(tag: str):
            session = MagicMock(spec_set=["get_state", "get_session_id"])
            session.get_state = MagicMock(return_value={})
            session.get_session_id = MagicMock(return_value=f"sess-{tag}")
            return session

        session_a = make_session("A")
        session_b = make_session("B")

        task_a = asyncio.create_task(comp.invoke({"input": "a"}, session_a, MagicMock()))
        await a_at_intent.wait()

        result_b = await comp.invoke({"input": "b"}, session_b, MagicMock())
        b_done.set()

        with pytest.raises(GraphInterrupt):
            await task_a

        # B 不受 A 中断影响
        assert result_b["responseContent"] == "B-res"

    def test_no_shared_state_instance_field(self):
        """源码级：执行期 _state/_state_retry 不再落实例字段。"""
        import inspect

        from agent_runtime.extension.workflow_node.complex_intent_detection import (
            ComplexIntentDetection,
        )

        src = inspect.getsource(ComplexIntentDetection)
        assert "self._state" not in src
        assert "self._state_retry" not in src

        comp = self._component()
        assert not hasattr(comp, "_state")
        assert not hasattr(comp, "_state_retry")
