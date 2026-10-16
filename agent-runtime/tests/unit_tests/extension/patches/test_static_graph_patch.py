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
