# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""End 组件跨执行隔离测试（静态图复用前提，issue #1555 / Task 9）。

End 在 wait_for_all=False 下会被 Pregel 引擎按入边多次触发，组件用四个能力
幂等标志（invoke/stream/collect/transform）防重复。实例复用后这些标志与 mix
协调状态若仍落在实例属性上，第二次执行会被直接短路（返回空）。本测试钉住：
1. 执行期状态按 NodeSession 隔离（容器随执行回收）；
2. 末帧输出走 Task 1 的 ContextVar 通道（引擎 Vertex._post_stream 流耗尽后读取）；
3. 渲染隔离：共享 TemplateProcessor 按执行克隆（位置字段互不互踩）。
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node.end import End, _EndExecState


class _FakeSession:
    """可弱引用的会话替身（object() 实例不支持 weakref）。"""


def _end_conf():
    return {"name": "end", "outputMode": "direct", "responseTemplate": "{{answer}}"}


def _mock_session() -> MagicMock:
    """驱动能力方法的 session 替身（io 写入链路异步 mock）。"""
    session = MagicMock()
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
        """复用实例：第二次执行的 invoke 不被第一次执行的幂等标志短路。"""
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
    async def test_same_execution_invoke_still_idempotent(self):
        """同一执行内（同 NodeSession）多入边触发仍只执行一次。"""
        end = End(_end_conf())
        session = _mock_session()
        first = await end.invoke({"answer": "first"}, session, None)
        assert first
        assert await end.invoke({"answer": "first"}, session, None) == {}

    @pytest.mark.asyncio
    async def test_invoke_entry_resets_and_writes_final_output_channel(self):
        end = End(_end_conf())
        ctx.set_stream_final_output({"userFields": "stale"})
        await end.invoke({"answer": "fresh"}, _mock_session(), None)
        final = end.get_stream_output()
        assert final is not None
        assert final["user_fields"]["answer"] == "fresh"


class TestEndRenderIsolation:
    def test_template_cloned_per_execution(self):
        end = End(_end_conf())
        end._prepare_render_state(end._exec_state(_FakeSession()))
        t1 = end._template
        end._prepare_render_state(end._exec_state(_FakeSession()))
        t2 = end._template
        assert t1 is not t2
        assert type(t1) is type(t2)

    def test_template_clone_shared_within_execution(self):
        """同一执行内 batch/stream 两路必须共用同一克隆（mix 依赖共享位置推进）。"""
        end = End(_end_conf())
        st = end._exec_state(_FakeSession())
        end._prepare_render_state(st)
        t1 = end._template
        end._prepare_render_state(st)
        assert end._template is t1
        assert st.template is t1

    def test_template_clone_starts_at_zero_position(self):
        """克隆复位渲染位置（等价父类 set_mix 的 reset 语义）。"""
        end = End(_end_conf())
        end._template._current_position = 5
        end._template._chunk_index = 3
        end._template._count = 1
        end._prepare_render_state(end._exec_state(_FakeSession()))
        assert end._template._current_position == 0
        assert end._template._chunk_index == 0

    def test_stale_batch_renderer_cache_cleared_on_new_execution(self):
        """父类 _batch_template latch 属执行期状态，新执行入口清残留。"""
        end = End(_end_conf())
        end._batch_template = object()  # 模拟上一执行异常路径残留
        end._prepare_render_state(end._exec_state(_FakeSession()))
        assert end._batch_template is None
