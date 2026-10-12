# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""static_graph_patch 结构断言与降级语义单测。

断言策略：真实 venv（openjiuwen 0.1.19，已由 ir_converter import 时应用
sub_stream 补丁）→ 断言全过；monkeypatch 破坏结构 → 对应断言命中。
"""
import asyncio
import sys
from pathlib import Path

# 打断 openjiuwen 循环 import（单用例 -k 独立运行必需）：
# graph.py → vertex.py → workflow.components.base → 包 openjiuwen.core.workflow.__init__
# → workflow.py:34 → 回引 graph.py（尚未执行完，PregelGraph 未定义）。
# 先导入包 __init__ 即打断该环；否则进程内首个 openjiuwen 子模块若为
# openjiuwen.core.graph.graph，任何用例都会 ImportError。
import openjiuwen.core.workflow  # noqa: F401
import pytest
from openjiuwen.core.workflow.components.condition.condition import FuncCondition

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

    def test_stream_actor_structure_change_detected(self, monkeypatch):
        """A4：模拟 ActorManager/StreamActor 构造模式变化（C1 修复注入点缺失）→ 断言命中。"""
        from openjiuwen.core.graph.stream_actor.base import StreamActor
        from openjiuwen.core.graph.stream_actor.manager import ActorManager

        def _alien_actor_init(self, node_id, vertex, abilities, source_groups,
                              stream_generator_timeout=1):
            self._node_id = node_id

        def _alien_manager_init(self, workflow_spec, graph, sub_graph, session):
            self._streams = {}

        monkeypatch.setattr(StreamActor, "__init__", _alien_actor_init)
        monkeypatch.setattr(ActorManager, "__init__", _alien_manager_init)

        failures = static_graph_patch._structure_assertions()

        assert any("StreamActor" in f for f in failures)
        assert any("ActorManager" in f for f in failures)

    def test_stream_actor_attributes_missing_degrade_not_raise(self, monkeypatch):
        """A4：上游删除 __init__（改名）→ 记为断言失败而非 AttributeError。"""
        from openjiuwen.core.graph.stream_actor.base import StreamActor
        from openjiuwen.core.graph.stream_actor.manager import ActorManager

        monkeypatch.delattr(StreamActor, "__init__")
        monkeypatch.delattr(ActorManager, "__init__")

        failures = static_graph_patch._structure_assertions()

        assert any("StreamActor" in f for f in failures)
        assert any("ActorManager" in f for f in failures)


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

        # 每次编译产出全新 Pregel（全新 channels）与全新 checkpointer。
        # 注：真实 WorkflowSession.checkpointer() 无父 session 时走
        # CheckpointerFactory 进程级单例（session/internal/workflow.py:72-77），
        # 生产语义是"重新取工厂实例 + GraphStore 全新包装"；MagicMock session
        # 下两次调用返回不同 mock，本断言据此成立（执行隔离本体是 fresh Pregel）。
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
        # PregelNode.func 才是 Vertex（pregel/base.py:46-50）；两次 compile 各自
        # 新建，且本次 compile 的 fresh vertex 已被 init——Vertex.init 会把
        # session 包成 NodeSession，故以 parent() 校验绑定的是本次 compile 的 session。
        assert n1.func is not n2.func
        assert c1._pregel.nodes["node_start"].func._session.parent() is s1

    @pytest.mark.asyncio
    async def test_structural_equivalence_vs_original_compile_on_fresh_graph(self):
        """I3：patched 产物与"全新图实例 + 原版 compile"结构逐项等价。

        原版 compile 需要未被 monkeypatch 的类属性，故本用例不挂
        `_patched_compile` fixture，直接调用 `_patched_pregel_graph_compile`。
        "全新图实例 + 原版 compile"即 off 模式下每请求新实例的等价基线。
        """
        import json

        from openjiuwen.core.graph.pregel.channels import BarrierChannel
        from jiuwen.extension.patches.static_graph_patch import (
            _patched_pregel_graph_compile,
        )
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(self.IR_PATH.read_text(encoding="utf-8"))
        patched_graph = (await (await IRConverter.async_ir_to_workflow(ir_data)).instantiate())._internal._graph
        original_graph = (await (await IRConverter.async_ir_to_workflow(ir_data)).instantiate())._internal._graph

        patched = _patched_pregel_graph_compile(patched_graph, self._fake_session())
        original = original_graph.compile(self._fake_session())  # 原版 compile（未打补丁）

        # 各节点 PregelNode.func 的 _executable 同一性：fresh vertex 包装的是
        # 本图 build 期同一 executable 实例（共享，不复制）；build 期 Vertex
        # 本身不再进入 Pregel。（__start__/__end__ 为 builder 内置 lambda，
        # 非 Vertex，故只遍历图节点。）
        assert set(patched._pregel.nodes) == set(original._pregel.nodes)
        for node_id in patched_graph.nodes:
            assert (
                patched._pregel.nodes[node_id].func._executable
                is patched_graph.nodes[node_id]._executable
            )
            assert patched._pregel.nodes[node_id].func is not patched_graph.nodes[node_id]

        # channels 数量与类型序列
        assert [type(c).__name__ for c in patched._pregel.channels] == [
            type(c).__name__ for c in original._pregel.channels
        ]

        # 各节点 routers 类型集合
        def _router_types(pregel):
            return {
                node_id: sorted(type(router).__name__ for router in node.routers)
                for node_id, node in pregel.nodes.items()
            }

        assert _router_types(patched._pregel) == _router_types(original._pregel)

        # BarrierChannel.expected_groups（barrier/CNF 语义，含仓库 barrier 补丁效果）
        def _barrier_groups(pregel):
            return sorted(
                (channel.key, sorted(sorted(group) for group in channel.expected_groups))
                for channel in pregel.channels
                if isinstance(channel, BarrierChannel)
            )

        assert _barrier_groups(patched._pregel) == _barrier_groups(original._pregel)

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


class TestPatchAStreamEdge:
    """C1：stream 边工作流——StreamActor 必须换成本次执行的 fresh vertex。

    复现记录（修复前，本类用例失败）：patched compile 只 init fresh vertex，
    build 期 vertex 永不 init；而 ActorManager（每执行新建，manager.py:53 经
    `StreamGraph.get_node()` 持有 build 期 vertex）里的 StreamActor.send 会调
    `should_handle_message()/is_done()/stream_call()`——这些依赖 `Vertex.init`
    设置的 `_component_ability/_session`。实测失败形态：
    `TypeError: 'NoneType' object is not iterable`（`_stream_abilities()` 迭代
    `_component_ability=None`），经 `ActorManager.produce()` 冒泡为
    `ExecutionError[100054] component 'node_producer' execute 'stream' error,
    reason=''NoneType' object is not iterable'`。补丁始终应用，故 off 模式
    （每请求新实例）同样崩。
    """

    @pytest.fixture
    def _patched_compile(self, monkeypatch):
        from openjiuwen.core.graph.graph import PregelGraph
        from jiuwen.extension.patches.static_graph_patch import (
            _patched_pregel_graph_compile,
        )

        monkeypatch.setattr(PregelGraph, "compile", _patched_pregel_graph_compile)

    @staticmethod
    def _build_stream_workflow():
        """程序化最小 stream 边工作流（不走 IR）：start → STREAM → COLLECT(end)。"""
        from openjiuwen.core.workflow.base import WorkflowCard
        from openjiuwen.core.workflow.components.base import ComponentAbility
        from openjiuwen.core.workflow.components.component import WorkflowComponent
        from openjiuwen.core.workflow.workflow import Workflow

        class StartStub(WorkflowComponent):
            async def invoke(self, inputs, session, context):
                return {"query": (inputs or {}).get("query")}

        class StreamStub(WorkflowComponent):
            async def stream(self, inputs, session, context):
                for i in range(3):
                    yield {"result": f"chunk{i}"}

        class CollectEndStub(WorkflowComponent):
            async def invoke(self, inputs, session, context):
                return {}

            async def collect(self, inputs, session, context):
                chunks = []
                generator = ((inputs or {}).get("userFields") or {}).get("chunk")
                if hasattr(generator, "__aiter__"):
                    async for chunk in generator:
                        chunks.append(chunk)
                return {"collected": chunks}

        workflow = Workflow(card=WorkflowCard(id="wf_stream_edge", name="stream_edge"))
        workflow.set_start_comp("node_start", StartStub(), inputs_schema={"userFields": {}})
        workflow.add_workflow_comp(
            "node_producer", StreamStub(),
            comp_ability=[ComponentAbility.STREAM],
            outputs_schema={"userFields": {}},
        )
        workflow.set_end_comp(
            "node_end", CollectEndStub(),
            stream_inputs_schema={"userFields": {"chunk": "${node_producer.result}"}},
        )
        workflow.add_connection("node_start", "node_producer")
        workflow.add_stream_connection("node_producer", "node_end")
        return workflow

    @staticmethod
    async def _run_once(workflow, session_id):
        from openjiuwen.core.session.workflow import create_workflow_session

        session = create_workflow_session(session_id=session_id)
        finals = []
        async for chunk in workflow.stream({"query": "hello"}, session):
            if getattr(chunk, "type", None) == "workflow_final":
                finals.append(chunk.payload)
        return finals

    @pytest.mark.asyncio
    async def test_actor_vertex_replaced_with_fresh_vertex(self, _patched_compile):
        """C1 修复机制白盒断言：per-execution ActorManager 的 StreamActor._vertex
        被换成本次 compile 的 fresh vertex（而非 build 期 vertex）。"""
        from openjiuwen.core.session.stream import BaseStreamMode
        from openjiuwen.core.session.workflow import create_workflow_session

        workflow = self._build_stream_workflow()
        session = create_workflow_session(session_id="sess-c1-actor")
        workflow_session = workflow._create_workflow_session(
            session, stream_modes=[BaseStreamMode.OUTPUT], is_sub=False
        )
        compiled = workflow._internal.compile(workflow_session, context=None)

        actor = workflow_session.actor_manager()._streams["node_end"]
        assert actor._vertex is compiled._pregel.nodes["node_end"].func
        assert actor._vertex is not workflow._internal._graph.nodes["node_end"]

    @pytest.mark.asyncio
    async def test_stream_edge_workflow_runs_twice_on_same_instance(self, _patched_compile):
        """同一实例两次执行均成功、chunk 流完整（COLLECT 汇聚到 3 个 chunk）。"""
        workflow = self._build_stream_workflow()

        first = await self._run_once(workflow, "sess-c1-run1")
        second = await self._run_once(workflow, "sess-c1-run2")

        assert first == [{"collected": ["chunk0", "chunk1", "chunk2"]}]
        assert second == [{"collected": ["chunk0", "chunk1", "chunk2"]}]

    @pytest.mark.asyncio
    async def test_stream_edge_workflow_concurrent_runs(self, _patched_compile):
        """并发两次执行同一实例：各自 session/actor 独立，chunk 流完整。

        对照：原版 compile 并发两次执行时共享 Pregel/vertex，实测其中一次
        产出为空（final 缺失）——本用例即该场景的回归守卫。
        """
        workflow = self._build_stream_workflow()

        first, second = await asyncio.gather(
            self._run_once(workflow, "sess-c1-conc1"),
            self._run_once(workflow, "sess-c1-conc2"),
        )

        assert first == [{"collected": ["chunk0", "chunk1", "chunk2"]}]
        assert second == [{"collected": ["chunk0", "chunk1", "chunk2"]}]


class _SessionArgFuncCondition(FuncCondition):
    """FuncCondition 的 session 透传变体（测试专用）。

    引擎原版 FuncCondition.invoke 为**无参**调用（condition.py:44
    `self._func()`），条件函数收不到 session；本变体把 session 透传给
    条件函数，使 TestPatchC 能以 `lambda s: s is marker` 直接断言
    "Patch C 解析出的 session 是哪一个"。
    """

    def invoke(self, inputs, session):
        return self._func(session)


def _routing_session_markers():
    """真实 session 三元组（组件级 NodeSession / workflow 级 WorkflowSession / 回退）。

    引擎 BranchRouter.set_session 只接受 Session/BaseSession
    （branch_router.py:83-90，普通对象抛 ValueError），且
    Condition.__call__ → AtomicNode._validate_session_and_state 要求
    BaseSession + CommitState——故测试用真实 session（构建零成本）而非
    object() 哨兵。
    """
    from openjiuwen.core.session import NodeSession, WorkflowSession

    wf_marker = WorkflowSession(workflow_id="wf_patch_c", session_id="wf-sess")
    comp_marker = NodeSession(wf_marker, "node_a")
    fallback_marker = WorkflowSession(workflow_id="wf_patch_c", session_id="fb-sess")
    return comp_marker, wf_marker, fallback_marker


class TestPatchC:
    """Patch C：BranchRouter 解析链 组件级 → workflow 级 → self._session。"""

    @pytest.fixture
    def _patched_call(self, monkeypatch):
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
        from jiuwen.extension.patches.static_graph_patch import _patched_branch_router_call

        monkeypatch.setattr(BranchRouter, "__call__", _patched_branch_router_call)

    @pytest.mark.asyncio
    async def test_resolution_order_three_tiers(self, _patched_call):
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
        from jiuwen.extension.workflow import execution_session_ctx as ctx

        comp_marker, wf_marker, fallback_marker = _routing_session_markers()

        router = BranchRouter(report_trace=False)
        router.add_branch(_SessionArgFuncCondition(lambda s: s is comp_marker), ["component_tier"])
        router.add_branch(_SessionArgFuncCondition(lambda s: s is wf_marker), ["workflow_tier"])
        router.add_branch(_SessionArgFuncCondition(lambda s: s is fallback_marker), ["fallback_tier"])
        router.set_session(fallback_marker)

        # 仅 fallback（兼容层：与原版行为一致）
        assert await router() == ["fallback_tier"]

        # + workflow 层（add_conditional_connection 注册的路由今日语义：ProxySession→workflow session）
        t1 = ctx.set_workflow_session(wf_marker)
        assert await router() == ["workflow_tier"]

        # + component 层（_RoutedIntentDetection 今日语义：set_session(NodeSession)）
        t2 = ctx.set_component_exec(comp_marker, None)
        assert await router() == ["component_tier"]

        # 逐层退栈
        ctx.reset_component_exec(t2)
        assert await router() == ["workflow_tier"]
        ctx.reset_workflow_session(t1)
        assert await router() == ["fallback_tier"]

    @pytest.mark.asyncio
    async def test_set_session_still_works_as_fallback(self, _patched_call):
        """set_session 保留（兼容层）：无 ContextVar 时与原版行为一致。"""
        from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

        _, _, marker = _routing_session_markers()
        router = BranchRouter(report_trace=False)
        router.add_branch(_SessionArgFuncCondition(lambda s: s is marker), ["hit"])
        router.set_session(marker)
        assert await router() == ["hit"]
