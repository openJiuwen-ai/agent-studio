# -*- coding: UTF-8 -*-
# pylint: disable=protected-access
"""Verify cross-branch coverage check: a regular pred owned by a parent
branch's mutually-exclusive condition must NOT be treated as external.
"""
import asyncio
import pytest
import openjiuwen.core.workflow  # noqa: F401
from openjiuwen.core.graph.graph import PregelGraph
from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
from jiuwen.extension.patches.parallel_branch_grouping_patch import apply_parallel_branch_grouping_patch
from jiuwen.extension.patches.nested_branch_barrier_patch import apply_nested_branch_barrier_patch

apply_parallel_branch_grouping_patch()
apply_nested_branch_barrier_patch()


@pytest.fixture(autouse=True)
def _ensure_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()
    asyncio.set_event_loop(None)


class _FakeExec:
    def __call__(self, **kw):
        pass

    @staticmethod
    def component_type():
        return "fake"


def test_parent_branch_mutually_exclusive_not_external():
    """Comment 2 scenario:
    P-if -> A -> J (regular); P-default -> B; B-if -> C -> J (regular);
    B-default -> J (conditional). When P-default/B-default is taken,
    neither A nor C fires → filtering deadlocks.
    """
    g = PregelGraph()
    for nid in ["P", "A", "B", "C", "J"]:
        g.add_node(nid, _FakeExec())
    g.add_edge("A", "J")  # regular
    g.add_edge("C", "J")  # regular

    router_p = BranchRouter()
    router_p.add_branch("cond_p_if", ["A"], branch_id="P-if")
    router_p.add_branch("True", ["B"], branch_id="P-default")
    g.add_conditional_edges("P", router_p)
    g.register_branch_targets("P", {"A", "B"})

    router_b = BranchRouter()
    router_b.add_branch("cond_b_if", ["C"], branch_id="B-if")
    router_b.add_branch("True", ["J"], branch_id="B-default")
    g.add_conditional_edges("B", router_b)
    g.register_branch_targets("B", {"C", "J"})

    compiled = g._compile()
    node = compiled.nodes.get("B")
    assert node is not None
    for router in node.routers:
        sel = getattr(router, "selector", None)
        sel_name = getattr(sel, "__name__", str(sel))
        assert "_filtered" not in sel_name, (
            f"B selector should NOT be filtered (cross-branch deadlock): {sel_name}"
        )
