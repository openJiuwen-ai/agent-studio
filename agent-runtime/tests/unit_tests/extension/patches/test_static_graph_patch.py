# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""static_graph_patch 结构断言与降级语义单测。

断言策略：真实 venv（openjiuwen 0.1.19，已由 ir_converter import 时应用
sub_stream 补丁）→ 断言全过；monkeypatch 破坏结构 → 对应断言命中。
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
    def test_real_engine_passes_all_assertions(self):
        """真实 openjiuwen 0.1.19 + 已应用 sub_stream 补丁 → 断言全过。

        前置：import ir_converter（应用 sub_stream 补丁）。测试文件顶部只
        import static_graph_patch（其仅 import openjiuwen.core.common.logging，
        不导入引擎类），sub_stream 补丁需 ir_converter 的 import 时应用——
        此处显式 import 保证顺序。
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
