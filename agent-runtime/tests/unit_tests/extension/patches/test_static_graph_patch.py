# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""static_graph_patch 结构断言与降级语义单测。

断言策略：真实 venv（openjiuwen 0.1.19，已由 ir_converter import 时应用
sub_stream 补丁）→ 断言全过；monkeypatch 破坏结构 → 对应断言命中。
"""
import sys
from pathlib import Path

# 打断 openjiuwen 循环 import（单用例 -k 独立运行必需）：
# graph.py → vertex.py → workflow.components.base → 包 openjiuwen.core.workflow.__init__
# → workflow.py:34 → 回引 graph.py（尚未执行完，PregelGraph 未定义）。
# 先导入包 __init__ 即打断该环；否则进程内首个 openjiuwen 子模块若为
# openjiuwen.core.graph.graph，任何用例都会 ImportError。
import openjiuwen.core.workflow  # noqa: F401
import pytest

from jiuwen.extension.patches import static_graph_patch


@pytest.fixture
def _restore_flags():
    """恢复模块级 flag（apply 测试会翻转它们）。"""
    saved = (
        static_graph_patch._STATIC_GRAPH_PATCH_APPLIED,
        static_graph_patch.STATIC_GRAPH_DOWNGRADED,
    )
    yield
    static_graph_patch._STATIC_GRAPH_PATCH_APPLIED = saved[0]
    static_graph_patch.STATIC_GRAPH_DOWNGRADED = saved[1]


class TestStructureAssertions:
    def test_real_engine_passes_all_assertions(self):
        """真实 openjiuwen 0.1.19 + 已应用 sub_stream 补丁 → 断言全过。

        前置：import ir_converter（应用 sub_stream 补丁）。static_graph_patch
        自身不应用 sub_stream 补丁（B1 断言要求调用方保证应用顺序），
        sub_stream 补丁需 ir_converter 的 import 时应用——此处显式 import
        保证顺序。
        """
        import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

        assert static_graph_patch._structure_assertions() == []

    def test_compile_structure_change_detected(self, monkeypatch):
        """模拟上游改掉 compile 的 'pregel is None' 模式 → 断言命中。"""
        from openjiuwen.core.graph.graph import PregelGraph

        def _alien_compile(self, session, **kwargs):
            return None

        monkeypatch.setattr(PregelGraph, "compile", _alien_compile)
        failures = static_graph_patch._structure_assertions()
        assert any("PregelGraph.compile" in f for f in failures)

    def test_invoke_ordering_violation_detected(self, monkeypatch):
        """模拟 sub_stream 补丁未先行应用（_invoke 不是其版本）→ 断言命中。"""
        from openjiuwen.core.graph.graph import CompiledGraph

        async def _alien_invoke(self, inputs, session, config=None):
            return None

        monkeypatch.setattr(CompiledGraph, "_invoke", _alien_invoke)
        failures = static_graph_patch._structure_assertions()
        assert any("CompiledGraph._invoke" in f for f in failures)

    def test_branch_router_structure_change_detected(self, monkeypatch):
        """模拟 BranchRouter.__call__ 不再读 self._session → 断言命中。"""
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

        async def _alien_call(self, *args, **kwargs):
            return []

        monkeypatch.setattr(BranchRouter, "__call__", _alien_call)
        failures = static_graph_patch._structure_assertions()
        assert any("BranchRouter" in f for f in failures)

    def test_vertex_shape_change_detected(self, monkeypatch):
        """模拟 Vertex.__init__ 签名变化 → 断言命中。"""
        from openjiuwen.core.graph.vertex import Vertex

        def _alien_init(self, node_id, executable=None, extra=None):
            self._node_id = node_id

        monkeypatch.setattr(Vertex, "__init__", _alien_init)
        failures = static_graph_patch._structure_assertions()
        assert any("Vertex" in f for f in failures)

    def test_engine_import_failure_degrades_not_raises(self, monkeypatch):
        """引擎导入失败（循环 import 未打断/上游改名）→ 记为断言失败，不抛异常。

        spec §7.2：断言失败必须走降级（STATIC_GRAPH_DOWNGRADED=True），
        因此 _structure_assertions 对引擎导入失败必须返回失败消息而非抛
        ImportError。sys.modules 置 None 使 `from ... import ...` 抛 ImportError。
        """
        monkeypatch.setitem(sys.modules, "openjiuwen.core.graph.graph", None)
        failures = static_graph_patch._structure_assertions()
        assert failures
        assert any("引擎导入失败" in f for f in failures)

    def test_missing_attributes_degrade_not_raise(self, monkeypatch):
        """上游删除引擎属性（改名）→ 记为断言失败，不抛 AttributeError。

        Task 2 审查遗留：属性获取未设防时 AttributeError 会逃出降级路径
        （spec §7.2 要求断言失败必须降级而非抛异常）。四处属性（_compile
        为上级指定必测项）逐一删除后断言 _structure_assertions 仍返回失败
        消息列表、不抛异常。
        """
        from openjiuwen.core.graph.graph import PregelGraph
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
        from jiuwen.extension.patches import workflow_sub_stream_patch

        monkeypatch.delattr(PregelGraph, "compile")
        monkeypatch.delattr(PregelGraph, "_compile")
        monkeypatch.delattr(workflow_sub_stream_patch, "_patched_compiled_invoke")
        monkeypatch.delattr(BranchRouter, "__call__")

        failures = static_graph_patch._structure_assertions()

        # PregelGraph.compile 删除后 getattr 回退到基类 Graph.compile（stub），
        # 不命中"不存在"分支但同样记为断言失败（源码模式不匹配），不抛异常。
        assert any("PregelGraph.compile" in f for f in failures)
        assert "PregelGraph._compile 不存在（结构断言失败，自动降级）" in failures
        assert (
            "workflow_sub_stream_patch._patched_compiled_invoke 不存在（结构断言失败，自动降级）"
            in failures
        )
        assert "BranchRouter.__call__ 不存在（结构断言失败，自动降级）" in failures


class TestPatchB:
    """Patch B：包装当前 _invoke，执行期间 workflow session ContextVar 可见。"""

    def _make_wrapped(self, seen):
        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        async def fake_prev_invoke(self, inputs, session, config=None):
            seen["during"] = ctx.current_workflow_session()
            seen["session_arg"] = session
            return "result"

        return _wrap_compiled_invoke(fake_prev_invoke)

    @pytest.mark.asyncio
    async def test_sets_and_resets_workflow_session(self):
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        seen = {}
        wrapped = self._make_wrapped(seen)
        sentinel_session = object()

        class FakeCompiled:
            pass

        result = await wrapped(FakeCompiled(), {"i": 1}, sentinel_session, None)

        assert result == "result"
        assert seen["during"] is sentinel_session
        assert seen["session_arg"] is sentinel_session
        assert ctx.current_workflow_session() is None  # finally 已 reset

    @pytest.mark.asyncio
    async def test_nested_invoke_stack_semantics(self):
        """嵌套（子工作流）场景：内层 set 后恢复外层——token 栈式。"""
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        seen = {}
        wrapped = self._make_wrapped(seen)
        outer_session, inner_session = object(), object()

        class FakeCompiled:
            pass

        async def inner_prev(self, inputs, session, config=None):
            return ctx.current_workflow_session()

        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke
        inner_wrapped = _wrap_compiled_invoke(inner_prev)

        async def outer_prev(self, inputs, session, config=None):
            # 外层执行中调用内层（模拟子工作流）
            inner_result = await inner_wrapped(self, inputs, inner_session, None)
            return {"inner_saw": inner_result, "outer_saw": ctx.current_workflow_session()}

        outer_wrapped = _wrap_compiled_invoke(outer_prev)
        result = await outer_wrapped(FakeCompiled(), {}, outer_session, None)

        assert result["inner_saw"] is inner_session
        assert result["outer_saw"] is outer_session
        assert ctx.current_workflow_session() is None

    @pytest.mark.asyncio
    async def test_exception_still_resets(self):
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        async def boom_prev(self, inputs, session, config=None):
            raise RuntimeError("boom")

        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke
        wrapped = _wrap_compiled_invoke(boom_prev)

        class FakeCompiled:
            pass

        with pytest.raises(RuntimeError):
            await wrapped(FakeCompiled(), {}, object(), None)
        assert ctx.current_workflow_session() is None


class TestPatchA:
    """Patch A：compile 纯函数化——fresh Pregel/checkpointer/Vertex per compile。"""

    IR_PATH = (
        Path(__file__).resolve().parents[3] / "resource" / "ir_file" / "workflow_message.json"
    )

    @staticmethod
    def _fake_session():
        """MagicMock session（计划期已实验验证可走通真实 compile）。"""
        from unittest.mock import MagicMock

        session = MagicMock()
        session.checkpointer.return_value.graph_store.return_value = MagicMock()
        return session

    @pytest.fixture
    def _patched_compile(self, monkeypatch):
        from openjiuwen.core.graph.graph import PregelGraph
        from jiuwen.extension.patches.static_graph_patch import (
            _patched_pregel_graph_compile,
        )

        monkeypatch.setattr(PregelGraph, "compile", _patched_pregel_graph_compile)

    @pytest.mark.asyncio
    async def test_two_compiles_yield_independent_pregel_and_checkpointer(self, _patched_compile):
        import json

        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph  # BaseWorkflow._graph 即 PregelGraph
        original_vertices = dict(graph.nodes)

        s1, s2 = self._fake_session(), self._fake_session()
        c1 = graph.compile(s1)
        c2 = graph.compile(s2)

        # 每次编译产出全新 Pregel（全新 channels）与全新 checkpointer
        assert c1._pregel is not c2._pregel
        assert c1._checkpointer is not c2._checkpointer
        # 属性保留写入（读取方兼容，spec §4.1 偏离②）
        assert graph.pregel is c2._pregel
        assert graph.checkpointer is c2._checkpointer
        assert graph._session is s2

        # 原 build 期 Vertex 未被 init 污染、self.nodes 未被替换
        for node_id, vertex in original_vertices.items():
            assert vertex is graph.nodes[node_id]
            assert vertex._session is None

    @pytest.mark.asyncio
    async def test_fresh_vertices_are_initialized_and_isolated(self, _patched_compile):
        import json

        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph

        s1 = self._fake_session()
        c1 = graph.compile(s1)

        # 两次 compile 的 PregelNode 内包装的是不同 Vertex 实例
        n1 = c1._pregel.nodes["node_start"]
        c2 = graph.compile(self._fake_session())
        n2 = c2._pregel.nodes["node_start"]
        assert n1 is not n2

    @pytest.mark.asyncio
    async def test_after_step_commits_captured_session_not_shared_attr(self, _patched_compile):
        """after_step 闭包捕获 session 参数——竞态根源（原版读 self._session）消除。"""
        import json
        from unittest.mock import MagicMock

        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph

        s1, s2 = self._fake_session(), self._fake_session()
        c1 = graph.compile(s1)
        graph.compile(s2)  # self._session 已被 s2 覆写（属性保留写入）

        loop_stub = MagicMock()
        loop_stub.step = 1
        loop_stub.config = {"ns": "wf", "session_id": "s1"}
        loop_stub.active_nodes = []

        c1._pregel.after_step(loop_stub)  # c1 的 after_step 应 commit s1 而非 s2
        s1.state().commit.assert_called()
        s2.state().commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_compile_equivalence_off_mode(self, _patched_compile):
        """off 模式等价性：每请求新实例的首次 compile，产物类型与属性绑定正确。"""
        import json

        from openjiuwen.core.graph.graph import CompiledGraph
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        lazy = await IRConverter.async_ir_to_workflow(ir_data)
        wf = await lazy.instantiate()
        graph = wf._internal._graph

        compiled = graph.compile(self._fake_session())
        assert isinstance(compiled, CompiledGraph)
        assert compiled._pregel is graph.pregel
