# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 本文件是静态图补丁的白盒断言测试：断言观测面即引擎类与补丁模块的受保护成员
# （CompiledGraph._invoke、PregelGraph._compile、补丁模块的 _original_compiled_invoke
# 基线与 _structure_assertions 等），上游引擎未提供公开访问入口，只能直接读取这些
# 成员来验证补丁应用、包装链与降级行为。
# pylint: disable=protected-access
"""static_graph_patch 能力探测、Patch B 与降级语义单测。

断言策略：真实 venv（openjiuwen 含 reentrant compile）→ 断言全过；
monkeypatch 破坏结构 → 对应断言命中。接线后 import ir_converter /
sub_workflow 即完成 sub_stream → static_graph_patch 的应用序列，进程内
CompiledGraph._invoke 为"已应用态"；B1 断言容忍两种合法态（_invoke 为
sub_stream 补丁版 = apply 前，或 Patch B 包装版 = apply 后，其包装链最内层
仍须是 sub_stream 补丁版）。

Patch A/C/D 与循环执行期状态会话化已随 openjiuwen
`fix/0.1.17.post2-compile-reentrant` 上游化，其行为回归由引擎自带测试与
本仓库 tests/integration_tests/test_workflow_static_graph_reuse.py 覆盖。
"""
import sys

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
    @staticmethod
    def test_real_engine_passes_all_assertions():
        """真实 venv（含 reentrant compile）+ import 链已应用补丁 → 断言全过。

        前置：import ir_converter。其应用序列为 sub_stream → ... →
        static_graph_patch（接线），故进程内 CompiledGraph._invoke 已是
        Patch B 包装版（B1 断言必须容忍"已包装态"，否则接线后本用例必红）；
        _structure_assertions 对已包装态经包装链最内层校验，仍须等价于
        sub_stream 补丁先行应用。sub_stream 补丁由 ir_converter 的 import
        应用——此处显式 import 保证顺序。

        注：上游分支曾因目标环境引擎 `_compile` 结构变化把本用例标记 skip；
        本分支依赖已 pin 到含 reentrant compile 的 agent-core 修复分支
        （requirements.txt），探测恒过，skip 随之移除。
        """
        import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

        from openjiuwen.core.graph.graph import CompiledGraph
        from jiuwen.extension.patches import workflow_sub_stream_patch

        # 接线后 _invoke 为 Patch B 包装版（合法态之一）
        assert getattr(CompiledGraph._invoke, "__name__", "") == "_invoke_with_session_ctx"
        assert (
            static_graph_patch._invoke_chain_root(CompiledGraph._invoke)
            is workflow_sub_stream_patch._patched_compiled_invoke
        )
        assert static_graph_patch._structure_assertions() == []

    @staticmethod
    def test_reentrant_compile_probe_accepts_real_engine():
        """真实引擎 `_compile` 带 nodes 注入点 → 能力探测为真。"""
        assert static_graph_patch._engine_has_reentrant_compile() is True

    @staticmethod
    def test_missing_reentrant_compile_detected(monkeypatch):
        """模拟依赖回退到未含修复的引擎（_compile 无 nodes 参数）→ 断言命中。"""
        from openjiuwen.core.graph.graph import PregelGraph

        def _legacy_compile(self, graph_store=None, step_callback=None):
            return None

        monkeypatch.setattr(PregelGraph, "_compile", _legacy_compile)
        failures = static_graph_patch._structure_assertions()
        assert any("reentrant compile" in f for f in failures)

    @staticmethod
    def test_invoke_ordering_violation_detected(monkeypatch):
        """模拟 sub_stream 补丁未先行应用（_invoke 不是其版本）→ 断言命中。"""
        from openjiuwen.core.graph.graph import CompiledGraph

        async def _alien_invoke(self, inputs, session, config=None):
            return None

        monkeypatch.setattr(CompiledGraph, "_invoke", _alien_invoke)
        failures = static_graph_patch._structure_assertions()
        assert any("CompiledGraph._invoke" in f for f in failures)

    @staticmethod
    def test_engine_import_failure_degrades_not_raises(monkeypatch):
        """引擎导入失败 → 记为断言失败，不抛 ImportError（spec §7.2）。"""
        monkeypatch.setitem(sys.modules, "openjiuwen.core.graph.graph", None)

        failures = static_graph_patch._structure_assertions()
        assert failures  # 非空即"降级而非抛异常"

    @staticmethod
    def test_missing_attributes_degrade_not_raise(monkeypatch):
        """引擎类属性缺失（如 _compile 被删）→ 记断言失败而非抛异常。"""
        from openjiuwen.core.graph.graph import PregelGraph

        monkeypatch.delattr(PregelGraph, "_compile", raising=False)
        failures = static_graph_patch._structure_assertions()
        assert any("reentrant compile" in f for f in failures)


class TestPatchB:
    """Patch B：包装当前 _invoke，执行期间 workflow session ContextVar 可见。

    写入的是**引擎自己的**通道（``openjiuwen.core.session.execution_session_ctx``）：
    引擎 BranchRouter.__call__ / BaseWorkflow.new_router 都经它解析。
    """

    @staticmethod
    def _make_wrapped(seen):
        from openjiuwen.core.session import execution_session_ctx as ctx
        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke

        async def fake_prev_invoke(self, inputs, session, config=None):
            seen["during"] = ctx.current_workflow_session()
            seen["session_arg"] = session
            return "result"

        return _wrap_compiled_invoke(fake_prev_invoke)

    @pytest.mark.asyncio
    async def test_sets_and_resets_workflow_session(self):
        from openjiuwen.core.session import execution_session_ctx as ctx

        seen = {}
        wrapped = TestPatchB._make_wrapped(seen)
        sentinel_session = object()

        class FakeCompiled:
            pass

        result = await wrapped(FakeCompiled(), {"i": 1}, sentinel_session, None)

        assert result == "result"
        assert seen.get("during") is sentinel_session
        assert seen.get("session_arg") is sentinel_session
        assert ctx.current_workflow_session() is None  # finally 已 reset

    @pytest.mark.asyncio
    async def test_nested_invoke_stack_semantics(self):
        """嵌套（子工作流）场景：内层 set 后恢复外层——token 栈式。"""
        from openjiuwen.core.session import execution_session_ctx as ctx
        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke

        outer_session, inner_session = object(), object()

        class FakeCompiled:
            pass

        async def inner_prev(self, inputs, session, config=None):
            return ctx.current_workflow_session()

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
        from openjiuwen.core.session import execution_session_ctx as ctx
        from jiuwen.extension.patches.static_graph_patch import _wrap_compiled_invoke

        async def boom_prev(self, inputs, session, config=None):
            raise RuntimeError("boom")

        wrapped = _wrap_compiled_invoke(boom_prev)

        class FakeCompiled:
            pass

        with pytest.raises(RuntimeError):
            await wrapped(FakeCompiled(), {}, object(), None)
        assert ctx.current_workflow_session() is None


class TestApplyAndDowngrade:
    """apply 编排：正常应用、幂等、断言失败自动降级（接线后的语义）。

    接线后 import ir_converter / sub_workflow 即完成应用，进程内引擎类属性
    为"已应用态"、`_STATIC_GRAPH_PATCH_APPLIED` 为 True。`_restore_engine`
    fixture 在 setup 阶段把引擎恢复到首次 apply 替换前保存的
    `_original_compiled_invoke` 基线（未应用态）并复位 flag，使本类用例能
    真实重放 apply（而非依赖 import 期的既成应用，也避免在已包装态上二次
    包装）；teardown 恢复保存的已应用态。`_original_*` 自身不改动——apply
    仅在其为 None 时捕获，保证基线恒为原版。
    """

    @pytest.fixture
    def _restore_engine(self):
        """保存/恢复引擎类方法与模块 flag（apply 会改类属性）。"""
        # import 触发接线：若本进程尚未应用，首次 apply 在此完成并捕获 _original_*
        import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

        from openjiuwen.core.graph.graph import CompiledGraph

        assert static_graph_patch._original_compiled_invoke is not None, (
            "首次 apply 未成功捕获原版基线（真实 venv 下断言应全过）"
        )
        saved = (
            CompiledGraph._invoke,
            static_graph_patch._STATIC_GRAPH_PATCH_APPLIED,
            static_graph_patch.STATIC_GRAPH_DOWNGRADED,
        )
        # 复位到未应用基线，供测试内真实重放 apply
        CompiledGraph._invoke = static_graph_patch._original_compiled_invoke
        static_graph_patch._STATIC_GRAPH_PATCH_APPLIED = False
        static_graph_patch.STATIC_GRAPH_DOWNGRADED = False
        yield
        CompiledGraph._invoke = saved[0]
        static_graph_patch._STATIC_GRAPH_PATCH_APPLIED = saved[1]
        static_graph_patch.STATIC_GRAPH_DOWNGRADED = saved[2]

    @staticmethod
    def test_apply_wraps_invoke_and_is_idempotent(_restore_engine):
        from openjiuwen.core.graph.graph import CompiledGraph
        from jiuwen.extension.patches import workflow_sub_stream_patch

        baseline_invoke = static_graph_patch._original_compiled_invoke

        assert static_graph_patch.apply_static_graph_patch() is True
        # _invoke 是包装版（包装了 sub_stream 的 _patched_compiled_invoke），
        # 包装链最内层仍是 sub_stream 补丁版（Patch B 不改写执行语义）
        assert CompiledGraph._invoke.__name__ == "_invoke_with_session_ctx"
        assert (
            static_graph_patch._invoke_chain_root(CompiledGraph._invoke)
            is workflow_sub_stream_patch._patched_compiled_invoke
        )
        assert not static_graph_patch.STATIC_GRAPH_DOWNGRADED
        # apply 后结构断言仍全过（B1 容忍已包装态）
        assert static_graph_patch._structure_assertions() == []
        # 重放 apply 不覆盖原版基线（_original_* 仅首次捕获）
        assert static_graph_patch._original_compiled_invoke is baseline_invoke

        # 幂等：第二次调用返回 False
        assert static_graph_patch.apply_static_graph_patch() is False

    @staticmethod
    def test_assertion_failure_downgrades_and_skips_patch(
        _restore_engine, monkeypatch, caplog
    ):
        from openjiuwen.core.graph.graph import CompiledGraph

        original_invoke = CompiledGraph._invoke
        monkeypatch.setattr(
            static_graph_patch, "_structure_assertions", lambda: ["模拟上游结构变更"]
        )

        assert static_graph_patch.apply_static_graph_patch() is False
        assert static_graph_patch.STATIC_GRAPH_DOWNGRADED is True
        assert CompiledGraph._invoke is original_invoke  # 未被替换
        assert any("结构断言失败" in r.message for r in caplog.records)

        # 降级后再次调用不重复告警（幂等守卫）
        assert static_graph_patch.apply_static_graph_patch() is False

    @pytest.mark.asyncio
    async def test_downgraded_intent_detection_routing_resolves(
        self, _restore_engine, monkeypatch
    ):
        """降级态下意图识别路由可解析：组件兼容写入喂饱兜底读点。

        能力探测失败 → Patch B 不安装（apply_static_graph_patch 降级分支），
        workflow 级通道无人写；未含修复引擎的 ``BranchRouter.__call__``
        直接读 ``self._session``（唯一写入方 ``set_session``）——组件 invoke
        的降级兼容写入保证该字段有值，不写则路由 session=None、分支条件
        （ExpressionCondition 求值需 NodeSession.state()）直接失败。本仓
        venv 为含修复引擎，以"清空两级通道"等价复现该兜底读侧（解析链
        第三级 组件级 → workflow 级 → ``self._session``）。
        """
        from unittest.mock import AsyncMock, MagicMock

        from openjiuwen.core.graph.graph import CompiledGraph
        from openjiuwen.core.session import NodeSession, WorkflowSession
        from openjiuwen.core.session import execution_session_ctx as engine_ctx
        from openjiuwen.core.session.node import Session
        from jiuwen.extension.workflow_node.intent_detection import IntentDetection

        monkeypatch.setattr(
            static_graph_patch, "_structure_assertions", lambda: ["模拟上游结构变更"]
        )
        assert static_graph_patch.apply_static_graph_patch() is False
        assert static_graph_patch.STATIC_GRAPH_DOWNGRADED is True
        # 降级态：_invoke 保持原样（Patch B 未包装）；引擎 __call__ 本仓不再
        # 替换（原 Patch C 已上游化，含修复引擎自带解析链）
        assert getattr(CompiledGraph._invoke, "__name__", "") != "_invoke_with_session_ctx"

        comp = IntentDetection(
            {
                "name": "intent",
                "branches": [
                    {"id": "branch_0", "catalog": "其他意图"},
                    {"id": "branch_1", "catalog": "查天气"},
                ],
                "prompt": "test prompt",
                "enableHistory": False,
                "enableInput": True,
                "chatHistoryMaxTurn": 3,
                "exampleContent": [],
                "overridable": False,
            }
        )
        comp.get_llm_result = AsyncMock(
            return_value='{"class": "分类1", "reason": "r"}'
        )
        wf_session = WorkflowSession(workflow_id="wf-downgrade", session_id="s-dg")
        node_session = NodeSession(wf_session, "intent_node")

        await comp.invoke({"input": "你好"}, Session(node_session, False), MagicMock())

        # 兼容写入已落（set_session 解包）→ 清空两级通道后走 self._session
        # 兜底，条件求值解析出目标分支
        comp._router.add_branch(
            _session_arg_condition(lambda s: s is node_session), ["hit"]
        )
        token_comp = engine_ctx.set_component_exec(None, None)
        token_wf = engine_ctx.set_workflow_session(None)
        try:
            assert await comp._router() == ["hit"]
        finally:
            engine_ctx.reset_workflow_session(token_wf)
            engine_ctx.reset_component_exec(token_comp)


def _session_arg_condition(func):
    """session 透传条件（测试专用，与 test_intent_detection_stateless 同构）。

    引擎 FuncCondition.invoke 为**无参**调用，条件函数收不到 session；
    本变体把 session 透传给条件函数，使断言能直接观察解析出的 session 对象。
    """
    from openjiuwen.core.workflow.components.condition.condition import FuncCondition

    class _SessionArgFuncCondition(FuncCondition):
        def invoke(self, inputs, session):
            return self._func(session)

    return _SessionArgFuncCondition(func)
