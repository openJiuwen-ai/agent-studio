# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SubWorkflow 组件跨执行隔离测试（静态图复用前提，issue #1555 / Task 10）。

审计发现：实例复用后，`_interrupt_child_node_id` / `_last_child_completed` 等
执行期状态落在组件实例上，跨执行串台——尤其 `_interrupt_child_node_id` 在成功
完成后从不清空，下一执行误走 resume 路径，query 被上一执行残留值污染。

本测试钉住：
1. 实例上不再挂执行期字段（`node_state` 等构建期遗留 API 除外）；
2. 中断子节点 ID / 上次子工作流完成标记走 session state（跨请求由 checkpoint
   承载、跨 session 天然隔离）；
3. 成功完成清空中断标记（下一执行不再误走 resume）；
4. 末帧输出走 Task 1 的 ContextVar 通道，且执行入口复位（上一执行的末帧不串到
   本执行）；
5. `_global_var_names` / `_workflow_instance` / `node_state.status` 不再被
   执行路径写回实例。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from openjiuwen.core.common.constants.constant import INTERACTION
from openjiuwen.core.session.interaction.interaction import InteractionOutput
from openjiuwen.core.session.stream.base import OutputSchema

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node.sub_workflow import (
    ExecutionStatus,
    SubWorkflow,
)

INTERRUPT_CHILD_KEY = "__sub_wf_interrupt_child"
LAST_CHILD_COMPLETED_KEY = "__sub_wf_last_child_completed"

# 执行期字段：修复后不得再挂在组件实例上
_EXEC_ATTRS = (
    "_interrupt_child_node_id",
    "_last_child_completed",
    "_current_query",
    "_pending_interact_prompt",
    "_stream_state",
    "_global_var_names",
)


@pytest.fixture(autouse=True)
def _clean_final_output_channel():
    """末帧 ContextVar 通道在进程内共享，用例前后复位避免互相串扰。"""
    ctx.set_stream_final_output(None)
    yield
    ctx.set_stream_final_output(None)


def _conf():
    return {
        "node_id": "sub_node",
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {"inputs": [], "outputs": []},
        "preDefineFields": {},
        "reference": {"id": "child", "path": "child.json"},
    }


def _mock_session(state=None, component_id="sub_node"):
    """带 state 字典的 mock session（get_state/update_state 语义对齐 NodeSession）。"""
    session = MagicMock()
    store = dict(state or {})
    session.get_state.side_effect = lambda key=None: (
        store.get(key) if key else dict(store)
    )
    session.update_state.side_effect = lambda data: store.update(data)
    session.get_global_state.return_value = {}
    session.get_env.return_value = None
    session.get_component_id.return_value = component_id
    session.write_stream = AsyncMock()
    session.write_custom_stream = AsyncMock()
    session.trace = AsyncMock()
    session.interact = AsyncMock()
    session._store = store
    return session


def _inputs(query="hello"):
    return {
        "systemFields": {"query": query},
        "userFields": {},
        "memory": {},
    }


class _FakeChildWorkflow:
    """子工作流替身：记录调用参数，按脚本产帧。"""

    def __init__(self, chunks=(), result=None):
        self.chunks = list(chunks)
        self.result = result if result is not None else {}
        self.stream_kwargs = None
        self.invoke_kwargs = None

    def stream(self, **kwargs):
        self.stream_kwargs = kwargs

        async def _gen():
            for chunk in self.chunks:
                yield chunk

        return _gen()

    async def invoke(self, **kwargs):
        self.invoke_kwargs = kwargs
        return self.result


async def _drain(agen):
    return [item async for item in agen]


class TestSubWorkflowStatelessAttrs:
    def test_instance_has_no_execution_state_attrs(self):
        """执行期字段不再落在实例属性上（复用实例的共享面）。"""
        component = SubWorkflow(_conf())
        for attr in _EXEC_ATTRS:
            assert not hasattr(component, attr), attr


class TestInterruptChildNodeIdInSessionState:
    @pytest.mark.asyncio
    async def test_interrupt_child_id_written_to_session_state(self):
        """中断子节点 ID 写 session state，不落实例属性。"""
        component = SubWorkflow(_conf())
        session = _mock_session()
        chunk = OutputSchema(
            type=INTERACTION,
            index=0,
            payload=InteractionOutput(id="childA", value="ask me"),
        )

        await component._raise_user_interact_from_chunk(session, chunk)

        assert session._store[INTERRUPT_CHILD_KEY] == "childA"
        assert not hasattr(component, "_interrupt_child_node_id")
        session.interact.assert_awaited_once_with("ask me")

    @pytest.mark.asyncio
    async def test_interrupt_id_not_leaked_to_new_session(self):
        """上一执行的中断子节点 ID 不得污染全新执行（跨 session 隔离）。

        修复前：ID 存在组件实例上，第二次执行（新 session）仍走 resume 分支，
        query 被上一执行残留的 resume 值覆盖。
        """
        component = SubWorkflow(_conf())
        session_old = _mock_session()

        # 执行 1：子工作流中断，写入中断子节点 ID
        await component._raise_user_interact_from_chunk(
            session_old,
            OutputSchema(
                type=INTERACTION,
                index=0,
                payload=InteractionOutput(id="childA", value="ask me"),
            ),
        )
        assert session_old._store[INTERRUPT_CHILD_KEY] == "childA"

        # 执行 2：全新 session，不得进入 resume 分支
        session_new = _mock_session()
        spy = MagicMock(return_value="STALE_REPLY")
        component._extract_parent_resume_query = spy

        params = await component._build_invoke_params(
            _inputs(query="fresh"), session_new, None
        )

        assert params["query"] == "fresh"
        spy.assert_not_called()
        assert session_new._store.get(INTERRUPT_CHILD_KEY) is None

    @pytest.mark.asyncio
    async def test_interrupt_id_read_from_same_session_state(self):
        """同一 session（恢复请求）内中断 ID 仍从 session state 生效。"""
        component = SubWorkflow(_conf())
        session = _mock_session({INTERRUPT_CHILD_KEY: "childA"})
        spy = MagicMock(return_value="RESUME_REPLY")
        component._extract_parent_resume_query = spy

        params = await component._build_invoke_params(
            _inputs(query="stale"), session, None
        )

        assert params["query"] == "RESUME_REPLY"
        spy.assert_called_once_with(session)


class TestLastChildCompletedInSessionState:
    @pytest.mark.asyncio
    async def test_reset_sub_outputs_read_from_session_state(self):
        """reset_sub_outputs 读 session state（上次子工作流已完成 → True）。"""
        child = _FakeChildWorkflow()
        component = SubWorkflow(_conf(), sub_workflow=child)
        session = _mock_session({LAST_CHILD_COMPLETED_KEY: True})

        await _drain(component.stream(_inputs(), session, None))

        assert child.stream_kwargs["reset_sub_outputs"] is True

    @pytest.mark.asyncio
    async def test_reset_sub_outputs_false_on_fresh_session(self):
        """全新 session 无残留完成标记 → reset_sub_outputs 不为真。"""
        child = _FakeChildWorkflow()
        component = SubWorkflow(_conf(), sub_workflow=child)
        session = _mock_session()

        await _drain(component.stream(_inputs(), session, None))

        assert not child.stream_kwargs["reset_sub_outputs"]


class TestStreamCompletionClearsInterruptMarker:
    @pytest.mark.asyncio
    async def test_stream_success_clears_interrupt_and_marks_completed(self):
        """成功完成：清空中断标记 + 写完成标记（下一执行不再误走 resume）。"""
        child = _FakeChildWorkflow(
            chunks=[
                OutputSchema(
                    type="workflow_final",
                    index=0,
                    payload={"user_fields": {"out": "v"}},
                )
            ]
        )
        component = SubWorkflow(_conf(), sub_workflow=child)
        session = _mock_session(
            {INTERRUPT_CHILD_KEY: "childA", LAST_CHILD_COMPLETED_KEY: False}
        )

        await _drain(component.stream(_inputs(), session, None))

        assert session._store[INTERRUPT_CHILD_KEY] is None
        assert session._store[LAST_CHILD_COMPLETED_KEY] is True
        assert component.get_stream_output() == {
            "responseContent": "",
            "userFields": {"out": "v"},
        }

    @pytest.mark.asyncio
    async def test_invoke_success_clears_interrupt_and_marks_completed(self):
        """invoke 成功路径同样清空中断标记 + 写完成标记。"""
        child = _FakeChildWorkflow(result={"answer": "done", "user_fields": {"a": 1}})
        component = SubWorkflow(_conf(), sub_workflow=child)
        session = _mock_session(
            {INTERRUPT_CHILD_KEY: "childA", LAST_CHILD_COMPLETED_KEY: False}
        )

        result = await component.invoke(_inputs(), session, None)

        assert result["responseContent"] == "done"
        assert session._store[INTERRUPT_CHILD_KEY] is None
        assert session._store[LAST_CHILD_COMPLETED_KEY] is True
        assert component.get_stream_output() == {
            "responseContent": "done",
            "userFields": {"a": 1},
        }


class TestStreamFinalOutputChannel:
    def test_stream_output_via_contextvar(self):
        """get_stream_output 读 ContextVar 通道（引擎 Vertex._post_stream 读）。"""
        component = SubWorkflow.__new__(SubWorkflow)  # 跳过重构造，仅测方法
        ctx.set_stream_final_output({"frame": 1})
        assert component.get_stream_output() == {"frame": 1}
        ctx.set_stream_final_output({"frame": 2})
        assert component.get_stream_output() == {"frame": 2}

    @pytest.mark.asyncio
    async def test_stream_output_not_leaked_to_next_execution(self):
        """上一执行的末帧不得串到本执行（入口复位）。"""
        child = _FakeChildWorkflow(
            chunks=[
                OutputSchema(
                    type="workflow_final",
                    index=0,
                    payload={"user_fields": {"out": "v"}},
                )
            ]
        )
        component = SubWorkflow(_conf(), sub_workflow=child)
        await _drain(component.stream(_inputs(), _mock_session(), None))
        assert component.get_stream_output() is not None

        # 第二次执行：子工作流直接中断，提前 return，不写末帧
        component._workflow_instance = _FakeChildWorkflow(
            chunks=[
                OutputSchema(
                    type=INTERACTION,
                    index=0,
                    payload=InteractionOutput(id="childA", value="ask me"),
                )
            ]
        )
        await _drain(component.stream(_inputs(), _mock_session(), None))

        assert component.get_stream_output() is None


class TestLocalizedExecutionState:
    def test_global_var_names_not_stored_on_instance(self):
        """_global_var_names 局部化：经返回值传递，不落实例。"""
        component = SubWorkflow(_conf())
        session = MagicMock()
        session.get_node_config.return_value = None

        global_vars, global_var_names = component._collect_global_vars(
            _inputs(), session
        )

        assert global_vars is None
        assert global_var_names is None
        assert not hasattr(component, "_global_var_names")

    def test_collect_updated_memory_takes_names_parameter(self):
        """_collect_updated_memory 经参数接收变量名列表。"""
        component = SubWorkflow(_conf())
        session = MagicMock()
        values = {"MEMORY_VARIABLE.parent_mem_one": "8272", "parent_mem_one": None}
        session.get_global_state.side_effect = lambda key=None: values.get(key)

        assert component._collect_updated_memory(session, ["parent_mem_one"]) == {
            "parent_mem_one": "8272"
        }
        assert component._collect_updated_memory(session, None) is None

    @pytest.mark.asyncio
    async def test_workflow_instance_from_session_not_cached(self):
        """None 降级路径：session 里的子工作流实例不写回组件实例。"""
        child = _FakeChildWorkflow(result={"answer": "done", "user_fields": {}})
        component = SubWorkflow(_conf())  # 未构造传入 → 走 session 降级路径
        session = _mock_session()
        session.get_global_state.side_effect = lambda key=None: (
            {"sub_node": child} if key == "workflow_instance_dict" else {}
        )

        assert await component._get_workflow_instance(session) is child
        await component.invoke(_inputs(), session, None)
        # per-execution 实例不落到复用组件上（否则跨 session 串台）
        assert component._workflow_instance is None

    @pytest.mark.asyncio
    async def test_node_state_not_mutated_by_execution(self):
        """执行路径不再写 node_state（遗留 reset/load_state API 之外无读写）。"""
        child = _FakeChildWorkflow(result={"answer": "done", "user_fields": {}})
        component = SubWorkflow(_conf(), sub_workflow=child)

        await component.invoke(_inputs(), _mock_session(), None)

        assert component.node_state.status == ExecutionStatus.START
