# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Verify nested_branch_barrier_patch cycle detection (A+B fix).

Regression tests for the production incident where a complex workflow with
Loop components caused mutually-reachable branch nodes, producing a cyclic
``parent`` dict in ``_build_branch_parent_patched`` and an infinite loop
in ``_branch_root``.
"""
import pytest

from openjiuwen.core.graph.graph import PregelGraph
from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

from jiuwen.extension.patches.parallel_branch_grouping_patch import (
    apply_parallel_branch_grouping_patch,
)
from jiuwen.extension.patches.nested_branch_barrier_patch import (
    apply_nested_branch_barrier_patch,
)

apply_parallel_branch_grouping_patch()
apply_nested_branch_barrier_patch()


class _FakeExec:
    def __call__(self, **kw):
        pass

    def component_type(self):
        return "fake"


def _make_graph(node_ids, *, wait_for_all_ids=()):
    g = PregelGraph()
    for nid in node_ids:
        g.add_node(nid, _FakeExec(), wait_for_all=nid in wait_for_all_ids)
    return g


def test_cycle_topology_no_infinite_loop():
    """Loop topology: branchA and branchB mutually reachable via a Loop node.

    Before A+B fix: _branch_root infinite-loops on parent={A:B, B:A}.
    After A+B fix: _build_branch_parent skips cycle, _branch_root terminates.
    """
    g = _make_graph(
        ["branchA", "node_mid", "loop_node", "branchB", "nodeC", "end", "agg"],
        wait_for_all_ids={"agg"},
    )

    r1 = BranchRouter()
    r1.add_branch("True", ["node_mid"], branch_id="A-if")
    r1.add_branch("False", ["nodeC"], branch_id="A-default")
    g.add_conditional_edges("branchA", r1)
    g.register_branch_targets("branchA", {"node_mid", "nodeC"})

    r2 = BranchRouter()
    r2.add_branch("True", ["nodeC"], branch_id="B-if")
    r2.add_branch("False", ["node_mid"], branch_id="B-default")
    g.add_conditional_edges("branchB", r2)
    g.register_branch_targets("branchB", {"nodeC", "node_mid"})

    g.add_edge("node_mid", "loop_node")
    g.add_edge("loop_node", "branchB")
    g.add_edge("nodeC", "agg")
    g.add_edge("nodeC", "loop_node")  # cycle back to loop
    g.add_edge("agg", "end")
    g.add_edge(["end"], "__end__")

    # Must not hang
    resolved = g._resolve_barrier_groups("agg", [{"nodeC"}])
    assert isinstance(resolved, list)

    # parent dict must not contain a cycle
    parent = g._build_branch_parent()
    for node in parent:
        root = g._branch_root(node, parent)
        assert root is not None


def test_cycle_topology_with_barrier():
    """Cycle topology with a wait_for_all barrier.

    Two branch nodes in a loop (like the real 工行 workflow), with
    predecessors feeding into a barrier node. _resolve_barrier_groups
    must terminate and return a valid result.
    """
    g = _make_graph(
        ["branchA", "branchB", "predA", "predB", "loop1", "loop2", "barrier"],
        wait_for_all_ids={"barrier"},
    )

    r1 = BranchRouter()
    r1.add_branch("True", ["loop1"], branch_id="A-if")
    r1.add_branch("False", ["predA"], branch_id="A-default")
    g.add_conditional_edges("branchA", r1)
    g.register_branch_targets("branchA", {"loop1", "predA"})

    r2 = BranchRouter()
    r2.add_branch("True", ["loop2"], branch_id="B-if")
    r2.add_branch("False", ["predB"], branch_id="B-default")
    g.add_conditional_edges("branchB", r2)
    g.register_branch_targets("branchB", {"loop2", "predB"})

    g.add_edge("loop1", "branchB")
    g.add_edge("loop2", "branchA")  # cycle: A -> loop1 -> B -> loop2 -> A
    g.add_edge("predA", "barrier")
    g.add_edge("predB", "barrier")

    resolved = g._resolve_barrier_groups("barrier", [{"predA"}, {"predB"}])
    assert isinstance(resolved, list)
    all_preds = set()
    for grp in resolved:
        all_preds |= grp
    assert "predA" in all_preds
    assert "predB" in all_preds


def test_self_referencing_branch():
    """Edge case: a branch whose target is itself."""
    g = _make_graph(
        ["branchA", "nodeA", "end", "agg"],
        wait_for_all_ids={"agg"},
    )

    r1 = BranchRouter()
    r1.add_branch("True", ["branchA"], branch_id="A-self")
    r1.add_branch("False", ["nodeA"], branch_id="A-default")
    g.add_conditional_edges("branchA", r1)
    g.register_branch_targets("branchA", {"branchA", "nodeA"})

    g.add_edge("nodeA", "agg")
    g.add_edge("agg", "end")
    g.add_edge(["end"], "__end__")

    parent = g._build_branch_parent()
    assert "branchA" not in parent or parent["branchA"] != "branchA"

    resolved = g._resolve_barrier_groups("agg", [{"nodeA"}])
    assert isinstance(resolved, list)
