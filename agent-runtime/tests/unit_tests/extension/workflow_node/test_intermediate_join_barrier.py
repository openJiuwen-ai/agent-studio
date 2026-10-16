# -*- coding: UTF-8 -*-
# pylint: disable=protected-access
"""Verify intermediate join node barrier fix for multiple topologies.

Tests cover:
- IR(13) topology: join node with conditional edge + regular edges from
  parent branch → safe to filter
- Deadlock topology: conditional edge is sole trigger from one path → keep
- node_end topology: only regular edges → no filtering needed
"""
import asyncio

import pytest

import openjiuwen.core.workflow  # noqa: F401
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


def _make_ir13_join_graph(*, join_already_wait: bool = True):
    """Build graph matching IR(13) 代码_1 join topology WITH parent branch.

    判断(default) → 判断_3 + 大模型_1
    判断_3(if) → 大模型_3 → 代码_1 (regular)
    判断_3(default) → 代码_1 (conditional)
    大模型_1 → 代码 → 代码_1 (regular)
    大模型_1 → 大模型 → 代码_1 (regular)
    大模型_1 → 大模型_1_1 → 代码_1 (regular)
    """
    g = PregelGraph()
    for nid in ["判断", "判断_3", "大模型_3", "大模型_1",
                "代码", "大模型", "大模型_1_1", "代码_1"]:
        g.add_node(nid, _FakeExec(),
                   wait_for_all=(nid == "代码_1" and join_already_wait))

    g.add_edge("大模型_3", "代码_1")
    g.add_edge("大模型", "代码_1")
    g.add_edge("大模型_1_1", "代码_1")
    g.add_edge("代码", "代码_1")
    g.add_edge("大模型_1", "代码")
    g.add_edge("大模型_1", "大模型")
    g.add_edge("大模型_1", "大模型_1_1")

    router_p = BranchRouter()
    router_p.add_branch("query == '0'", [], branch_id="判断-if")
    router_p.add_branch("True", ["判断_3", "大模型_1"], branch_id="判断-default")
    g.add_conditional_edges("判断", router_p)
    g.register_branch_targets("判断", {"判断_3", "大模型_1"})

    router_b = BranchRouter()
    router_b.add_branch("query == '1'", ["大模型_3"], branch_id="判断_3-if")
    router_b.add_branch("True", ["代码_1"], branch_id="判断_3-default")
    g.add_conditional_edges("判断_3", router_b)
    g.register_branch_targets("判断_3", {"大模型_3", "代码_1"})
    return g


def test_join_already_in_waits_selector_filtered():
    """代码_1 already wait_for_all → conditional edge still filtered."""
    g = _make_ir13_join_graph(join_already_wait=True)
    compiled = g._compile()

    assert "代码_1" in g.waits
    node = compiled.nodes.get("判断_3")
    assert node is not None
    for router in node.routers:
        sel = getattr(router, "selector", None)
        sel_name = getattr(sel, "__name__", str(sel))
        assert "_filtered" in sel_name, f"selector not filtered: {sel_name}"


def test_join_not_in_waits_selector_filtered():
    """代码_1 NOT in waits → patch adds it AND filters selector."""
    g = _make_ir13_join_graph(join_already_wait=False)
    compiled = g._compile()

    assert "代码_1" in g.waits
    node = compiled.nodes.get("判断_3")
    assert node is not None
    for router in node.routers:
        sel = getattr(router, "selector", None)
        sel_name = getattr(sel, "__name__", str(sel))
        assert "_filtered" in sel_name, f"selector not filtered: {sel_name}"


def test_node_end_topology_no_conditional_edge():
    """node_end with only regular edges → no selector filtering needed."""
    g = PregelGraph()
    for nid in ["判断", "大模型_2", "代码_1", "node_end"]:
        g.add_node(nid, _FakeExec(), wait_for_all=(nid == "代码_1"))
    g.add_edge("大模型_2", "node_end")
    g.add_edge("代码_1", "node_end")
    r = BranchRouter()
    r.add_branch("query == '0'", ["大模型_2"], branch_id="判断-if")
    r.add_branch("True", [], branch_id="判断-default")
    g.add_conditional_edges("判断", r)
    g.register_branch_targets("判断", {"大模型_2"})
    compiled = g._compile()
    assert "node_end" not in g.waits
    node = compiled.nodes.get("判断")
    assert node is not None
    for router in node.routers:
        sel = getattr(router, "selector", None)
        sel_name = getattr(sel, "__name__", str(sel))
        assert "_filtered" not in sel_name, f"selector should NOT be filtered: {sel_name}"


def test_deadlock_topology_conditional_edge_kept():
    """B-if -> A -> J (regular); B-default -> J (conditional only).
    Filtering would deadlock when B takes default — conditional edge kept.
    """
    g = PregelGraph()
    for nid in ["B", "A", "J"]:
        g.add_node(nid, _FakeExec())
    g.add_edge("A", "J")
    r = BranchRouter()
    r.add_branch("cond_if", ["A"], branch_id="B-if")
    r.add_branch("True", ["J"], branch_id="B-default")
    g.add_conditional_edges("B", r)
    g.register_branch_targets("B", {"A", "J"})
    compiled = g._compile()
    node = compiled.nodes.get("B")
    assert node is not None
    for router in node.routers:
        sel = getattr(router, "selector", None)
        sel_name = getattr(sel, "__name__", str(sel))
        assert "_filtered" not in sel_name, (
            f"selector should NOT be filtered (deadlock risk): {sel_name}"
        )


def test_deadlock_topology_j_not_in_waits():
    """B-if -> A -> J (regular); B-default -> J (conditional only).
    J must NOT be added to self.waits — barrier would deadlock on default path.
    """
    g = PregelGraph()
    for nid in ["B", "A", "J"]:
        g.add_node(nid, _FakeExec())
    g.add_edge("A", "J")
    r = BranchRouter()
    r.add_branch("cond_if", ["A"], branch_id="B-if")
    r.add_branch("True", ["J"], branch_id="B-default")
    g.add_conditional_edges("B", r)
    g.register_branch_targets("B", {"A", "J"})
    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — barrier would deadlock on B-default path"
    )


def test_multi_group_deadlock_kept():
    """Multiple groups where one group has no standalone member.
    B-if -> A -> J (regular, on B-if path)
    B-default -> J (conditional) AND C -> J (regular, on B-default path)
    Also: Z -> J (regular, standalone — always fires)

    Groups: [{A, C}, {Z}]. When B takes B-if, Z fires (reaching J), but
    neither A nor C fires on a path where Z also fires... actually A fires
    on B-if path, so group {A,C} is satisfied by A. But if we remove A:

    B-if -> other (not J), B-default -> C -> J AND B-default -> J (cond)
    Z -> J (standalone)
    Groups: [{C}, {Z}]. When B takes B-if, Z fires (reaching J) but C
    doesn't fire → {C} deadlocks. Must not add to waits.
    """
    g = PregelGraph()
    for nid in ["B", "C", "Z", "J"]:
        g.add_node(nid, _FakeExec())
    g.add_edge("C", "J")
    g.add_edge("Z", "J")
    r = BranchRouter()
    r.add_branch("cond_if", [], branch_id="B-if")
    r.add_branch("True", ["C", "J"], branch_id="B-default")
    g.add_conditional_edges("B", r)
    g.register_branch_targets("B", {"C", "J"})
    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — group {C} deadlocks when B takes B-if "
        "and Z reaches J via standalone"
    )


def test_ir12_node_end_filtered():
    """IR(12) node_end topology: 判断_3-default -> node_end (conditional)
    while 大模型_2 -> node_end (regular, 判断-if path) and
    代码_1 -> node_end (regular, 判断-default path).

    代码_1 is owned by both (判断_3, 判断_3-if) [doesn't co-occur with
    判断_3-default] and (判断, 判断-default) [co-occurs]. The modified
    reachability check must find 代码_1 reachable from 判断-default's
    targets without going through 判断_3-if's edges.
    """
    g = PregelGraph()
    for nid in ["判断", "判断_3", "大模型_2", "大模型_3", "大模型_1",
                "代码", "大模型", "大模型_1_1", "代码_1", "node_end"]:
        g.add_node(nid, _FakeExec())

    g.add_edge("大模型_2", "node_end")
    g.add_edge("代码_1", "node_end")
    g.add_edge("大模型_1", "代码")
    g.add_edge("代码", "代码_1")
    g.add_edge("大模型_1", "大模型")
    g.add_edge("大模型", "代码_1")
    g.add_edge("大模型_1", "大模型_1_1")
    g.add_edge("大模型_1_1", "代码_1")
    g.add_edge("大模型_3", "代码_1")

    router_p = BranchRouter()
    router_p.add_branch("query == '0'", ["大模型_2"], branch_id="判断-if")
    router_p.add_branch("True", ["判断_3", "大模型_1"], branch_id="判断-default")
    g.add_conditional_edges("判断", router_p)
    g.register_branch_targets("判断", {"大模型_2", "判断_3", "大模型_1"})

    router_b = BranchRouter()
    router_b.add_branch("query == '1'", ["大模型_3"], branch_id="判断_3-if")
    router_b.add_branch("True", ["node_end"], branch_id="判断_3-default")
    g.add_conditional_edges("判断_3", router_b)
    g.register_branch_targets("判断_3", {"大模型_3", "node_end"})

    g._compile()

    assert "node_end" in g.waits, (
        "node_end should be in self.waits — regular edges provide coverage"
    )
    compiled = g._compile()
    node = compiled.nodes.get("判断_3")
    assert node is not None
    for router in node.routers:
        sel = getattr(router, "selector", None)
        sel_name = getattr(sel, "__name__", str(sel))
        assert "_filtered" in sel_name, (
            f"判断_3 selector should be filtered: {sel_name}"
        )


def test_cyclic_topology_no_false_positive():
    """Loop topology: B-if->A->J (regular), B-default->J (conditional),
    J->C->B (cycle). forward_reachable(J) includes A via the cycle
    J->C->B->(B-if edge)->A, making A appear owned by (B, B-default).
    The modified BFS must exclude B-if's edge at B, preventing the
    false positive that would cause barrier deadlock.
    """
    g = PregelGraph()
    for nid in ["B", "A", "J", "C"]:
        g.add_node(nid, _FakeExec())
    g.add_edge("A", "J")
    g.add_edge("J", "C")
    g.add_edge("C", "B")
    r = BranchRouter()
    r.add_branch("cond_if", ["A"], branch_id="B-if")
    r.add_branch("True", ["J"], branch_id="B-default")
    g.add_conditional_edges("B", r)
    g.register_branch_targets("B", {"A", "J"})
    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — A is only reachable from "
        "B-default's target via cycle through B-if, not genuinely on path"
    )
    compiled = g._compile()
    node = compiled.nodes.get("B")
    assert node is not None
    for router in node.routers:
        sel = getattr(router, "selector", None)
        sel_name = getattr(sel, "__name__", str(sel))
        assert "_filtered" not in sel_name, (
            f"B selector should NOT be filtered (cycle false positive): {sel_name}"
        )


def test_downstream_branch_conditional_edge_no_false_positive():
    """BFS must not traverse other branch nodes' conditional edges.

    Topology: B-if -> J (conditional), B-default -> M -> X
    X-if -> p -> J (regular), X-else -> other

    When B takes B-if, J is reached via conditional edge. p is only
    reachable from B-default's path through X's X-if condition. The BFS
    from B-default's targets must NOT find p reachable via X-if
    (conditional edge), otherwise _pred_covers returns True incorrectly,
    causing J to be added to waits and B-if->J filtered → deadlock when
    X takes X-else.
    """
    g = PregelGraph()
    for nid in ["B", "M", "X", "p", "other", "J"]:
        g.add_node(nid, _FakeExec())

    g.add_edge("M", "X")
    g.add_edge("p", "J")

    r_b = BranchRouter()
    r_b.add_branch("cond_if", ["J"], branch_id="B-if")
    r_b.add_branch("True", ["M"], branch_id="B-default")
    g.add_conditional_edges("B", r_b)
    g.register_branch_targets("B", {"J", "M"})

    r_x = BranchRouter()
    r_x.add_branch("x_if", ["p"], branch_id="X-if")
    r_x.add_branch("True", ["other"], branch_id="X-else")
    g.add_conditional_edges("X", r_x)
    g.register_branch_targets("X", {"p", "other"})

    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — p is only reachable via X-if "
        "(conditional edge of a downstream branch), not guaranteed when "
        "X takes X-else. BFS must not traverse X's conditional edges."
    )


def test_independent_incoming_edge_no_false_positive():
    """b_node with independent incoming edge must not be marked safe.

    Topology: B-if -> J (conditional), B-default -> M -> p -> J (regular)
    Also: E -> B (independent regular edge, E not reachable from B)

    When E fires, B fires, B-if->J conditional edge triggers. But p
    (on B-default path) doesn't fire. The co-occurrence check must detect
    that B has an independent predecessor E and reject filtering.
    """
    g = PregelGraph()
    for nid in ["E", "B", "M", "p", "J"]:
        g.add_node(nid, _FakeExec())

    g.add_edge("E", "B")
    g.add_edge("M", "p")
    g.add_edge("p", "J")

    r_b = BranchRouter()
    r_b.add_branch("cond_if", ["J"], branch_id="B-if")
    r_b.add_branch("True", ["M"], branch_id="B-default")
    g.add_conditional_edges("B", r_b)
    g.register_branch_targets("B", {"J", "M"})

    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — B has independent predecessor E "
        "that bypasses the branch, so p is not guaranteed when E triggers B."
    )


def test_join_back_edge_no_false_positive():
    """BFS must stop expanding join target's outgoing edges.

    Topology: B-if -> A (conditional), A -> J (regular),
    B-default -> J (conditional), J -> A (regular back edge).

    When B takes B-default, A does NOT fire before J — A is only
    reachable via J's back edge. BFS from B-default's target (J) must
    NOT traverse J -> A, otherwise it finds A and returns True,
    causing J to be added to waits and B-default->J filtered →
    deadlock (J waits for A, A waits for J).
    """
    g = PregelGraph()
    for nid in ["B", "A", "J"]:
        g.add_node(nid, _FakeExec())

    g.add_edge("A", "J")
    g.add_edge("J", "A")

    r_b = BranchRouter()
    r_b.add_branch("cond_if", ["A"], branch_id="B-if")
    r_b.add_branch("True", ["J"], branch_id="B-default")
    g.add_conditional_edges("B", r_b)
    g.register_branch_targets("B", {"A", "J"})

    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — A is only reachable via J's "
        "back edge (J->A), not genuinely on the B-default path. "
        "BFS must stop expanding J's outgoing edges."
    )


def test_mixed_safety_multiple_branches_same_join():
    """Multiple branch nodes targeting same join with mixed safety.

    B1-default -> J (conditional) + M (conditional, same condition)
    M -> p -> J (regular)
    B2-default -> J (conditional only, no path to J's regular preds)
    B2-if -> other (conditional)

    B1 is safe (p fires when B1 takes B1-default via M->p).
    B2 is unsafe (p doesn't fire when B2 takes B2-default).

    Since not all branches are safe and J was not originally a barrier
    node, J must NOT be added to self.waits and NO selector should be
    filtered — otherwise B2's unfiltered conditional edge bypasses the
    barrier and causes premature execution.
    """
    g = PregelGraph()
    for nid in ["B1", "M", "p", "J", "B2", "other"]:
        g.add_node(nid, _FakeExec())

    g.add_edge("M", "p")
    g.add_edge("p", "J")

    r_b1 = BranchRouter()
    r_b1.add_branch("True", ["J", "M"], branch_id="B1-default")
    r_b1.add_branch("cond_b1", ["other"], branch_id="B1-if")
    g.add_conditional_edges("B1", r_b1)
    g.register_branch_targets("B1", {"J", "M", "other"})

    r_b2 = BranchRouter()
    r_b2.add_branch("True", ["J"], branch_id="B2-default")
    r_b2.add_branch("cond_b2", ["other"], branch_id="B2-if")
    g.add_conditional_edges("B2", r_b2)
    g.register_branch_targets("B2", {"J", "other"})

    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — B2's conditional edge is unsafe "
        "and unfiltered, so adding J to waits would let B2's TriggerMessage "
        "bypass the barrier"
    )
    compiled = g._compile()
    for bn in ["B1", "B2"]:
        node = compiled.nodes.get(bn)
        assert node is not None
        for router in node.routers:
            sel = getattr(router, "selector", None)
            sel_name = getattr(sel, "__name__", str(sel))
            assert "_filtered" not in sel_name, (
                f"{bn} selector should NOT be filtered (mixed safety)"
            )


def test_legacy_branch_same_join_no_premature_trigger():
    """Legacy branch (no branch_id) + safe cond-aware branch same join.

    B1-default -> J (conditional) + M (conditional, has branch_id)
    M -> p -> J (regular)
    B2-default -> J (conditional, NO branch_id — legacy branch)

    B1 is safe (p fires via M->p). B2 is legacy (never safety-checked,
    selector never filtered). Step 1.6 must detect B2 as unsafe and
    NOT promote J to barrier mode — otherwise B2's unfiltered
    TriggerMessage bypasses the BarrierChannel.
    """
    g = PregelGraph()
    for nid in ["B1", "M", "p", "J", "B2"]:
        g.add_node(nid, _FakeExec())

    g.add_edge("M", "p")
    g.add_edge("p", "J")

    r_b1 = BranchRouter()
    r_b1.add_branch("True", ["J", "M"], branch_id="B1-default")
    r_b1.add_branch("cond_b1", [], branch_id="B1-if")
    g.add_conditional_edges("B1", r_b1)
    g.register_branch_targets("B1", {"J", "M"})

    r_b2 = BranchRouter()
    r_b2.add_branch("True", ["J"])  # no branch_id → legacy
    g.add_conditional_edges("B2", r_b2)
    g.register_branch_targets("B2", {"J"})

    g._compile()
    assert "J" not in g.waits, (
        "J should NOT be in self.waits — B2 is a legacy branch whose "
        "selector cannot be filtered; adding J to waits would let B2's "
        "TriggerMessage bypass the barrier"
    )
