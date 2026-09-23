# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Verify barrier CNF grouping distinguishes co-executing predecessors from
mutually-exclusive ones.

Regression tests for the production incident where a conditional branch's
paths re-converged before a parallel fork, making every lane reachable from
ALL branch conditions. The nested-branch patch (len(co) >= 1) classified the
6 co-executing lane-done nodes as mutually exclusive and merged them into a
single OR-group. BarrierChannel then re-armed after consume() on each late
lane arrival, re-running the join/LLM/End once per lane (End activated 8
times, hundreds of stream chunks discarded).

Correct semantics:
- predecessor reachable from ALL conditions of every involved branch
  (co-executing, always runs) -> standalone AND-group.
- predecessor reachable from only SOME conditions (mutually exclusive
  alternative) -> merged OR-group (preserves the nested-branch deadlock fix).
"""
import asyncio

import pytest

from openjiuwen.core.graph.graph import PregelGraph
from openjiuwen.core.graph.pregel.channels import BarrierChannel
from openjiuwen.core.graph.pregel.base import BarrierMessage
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
    """PregelGraph.__init__ creates asyncio.Future, requiring a running loop."""
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


def _make_graph(node_ids, *, wait_for_all_ids=()):
    g = PregelGraph()
    for nid in node_ids:
        g.add_node(nid, _FakeExec(), wait_for_all=nid in wait_for_all_ids)
    return g


def _groups_as_sets(resolved):
    return sorted((frozenset(grp) for grp in resolved), key=lambda s: sorted(s))


def test_coexecuting_lanes_stay_and_groups():
    """Customer topology: branch paths re-converge before the fork.

    判断(if->变量赋值 / default->大模型) -> 合流 -> fork -> 6 lanes -> join.
    Every lane-done is reachable from BOTH conditions, so all of them always
    execute; they must stay as 6 standalone AND-groups, not one OR-group.
    """
    g = _make_graph(
        ["判断", "变量赋值", "大模型", "合流", "拼接token"]
        + [f"lane{i}" for i in range(1, 7)]
        + [f"done{i}" for i in range(1, 7)]
        + ["JOIN", "合并代码", "END"],
        wait_for_all_ids={"JOIN"},
    )
    r = BranchRouter()
    r.add_branch("is_empty(ctx)", ["变量赋值"], branch_id="判断-if")
    r.add_branch("True", ["大模型"], branch_id="判断-default")
    g.add_conditional_edges("判断", r)
    g.register_branch_targets("判断", {"变量赋值", "大模型"})
    g.add_edge("变量赋值", "合流")
    g.add_edge("大模型", "合流")
    g.add_edge("合流", "拼接token")
    for i in range(1, 7):
        g.add_edge("拼接token", f"lane{i}")
        g.add_edge(f"lane{i}", f"done{i}")
        g.add_edge(f"done{i}", "JOIN")
    g.add_edge("JOIN", "合并代码")
    g.add_edge("合并代码", "END")

    sources = [{f"done{i}"} for i in range(1, 7)]
    resolved = g._resolve_barrier_groups("JOIN", sources)

    # Every lane-done must own a singleton AND-group (one-shot latch). A pure
    # OR-group would re-arm the barrier on each late lane and re-run the join.
    groups = _groups_as_sets(resolved)
    for i in range(1, 7):
        assert frozenset({f"done{i}"}) in groups

    # End-to-end barrier semantics: only ready after ALL 6 senders arrive,
    # and exactly once across the whole run.
    barrier = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
    fire_count = 0
    for i in range(1, 7):
        barrier.accept(BarrierMessage(sender=f"done{i}", target=barrier.key))
        if barrier.is_ready():
            fire_count += 1
            barrier.consume()
        if i < 6:
            assert fire_count == 0, f"barrier fired after only {i} senders"
    assert fire_count == 1


def test_exclusive_conditions_still_merge_or():
    """Original nested-branch deadlock scenario must be preserved.

    Branch A routes if/elif to the same target T1 (reaching p1) and default
    to T2 (reaching p2). p1 is owned by 2 of 3 conditions (not all) -> still
    a mutually-exclusive alternative; p1 and p2 merge into one OR-group so
    whichever path executes satisfies the barrier (no deadlock).
    """
    g = _make_graph(
        ["branchA", "T1", "T2", "p1", "p2", "JOIN"],
        wait_for_all_ids={"JOIN"},
    )
    r = BranchRouter()
    r.add_branch("cond1", ["T1"], branch_id="A-if")
    r.add_branch("cond2", ["T1"], branch_id="A-elif")
    r.add_branch("True", ["T2"], branch_id="A-default")
    g.add_conditional_edges("branchA", r)
    g.register_branch_targets("branchA", {"T1", "T2"})
    g.add_edge("T1", "p1")
    g.add_edge("T2", "p2")
    g.add_edge("p1", "JOIN")
    g.add_edge("p2", "JOIN")

    resolved = g._resolve_barrier_groups("JOIN", [{"p1"}, {"p2"}])
    assert _groups_as_sets(resolved) == [frozenset({"p1", "p2"})]

    # Either path alone satisfies the OR-group.
    barrier = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
    barrier.accept(BarrierMessage(sender="p1", target=barrier.key))
    assert barrier.is_ready()


def test_mixed_coexecuting_and_exclusive():
    """Co-executing lane AND exclusive alternatives in the same join.

    done_always is reachable from all conditions (paths converge before it);
    p1/p2 are condition-exclusive. Result: {done_always} standalone AND-group
    + {p1, p2} OR-group.
    """
    g = _make_graph(
        ["branchA", "T1", "T2", "合流", "fork", "done_always", "p1", "p2", "JOIN"],
        wait_for_all_ids={"JOIN"},
    )
    r = BranchRouter()
    r.add_branch("cond1", ["T1"], branch_id="A-if")
    r.add_branch("True", ["T2"], branch_id="A-default")
    g.add_conditional_edges("branchA", r)
    g.register_branch_targets("branchA", {"T1", "T2"})
    # both paths converge before the fork -> done_always always executes
    g.add_edge("T1", "合流")
    g.add_edge("T2", "合流")
    g.add_edge("合流", "fork")
    g.add_edge("fork", "done_always")
    g.add_edge("done_always", "JOIN")
    # exclusive alternatives branch after the fork
    r2 = BranchRouter()
    r2.add_branch("cond_x", ["p1"], branch_id="B-if")
    r2.add_branch("True", ["p2"], branch_id="B-default")
    g.add_conditional_edges("fork", r2)
    g.register_branch_targets("fork", {"p1", "p2"})
    g.add_edge("p1", "JOIN")
    g.add_edge("p2", "JOIN")

    resolved = g._resolve_barrier_groups(
        "JOIN", [{"done_always"}, {"p1"}, {"p2"}]
    )
    groups = _groups_as_sets(resolved)
    # done_always is co-executing and its OR-group still has ≥2 exclusive
    # siblings after removal -> it is split out as a standalone AND-group
    # (NOT a latch) so the OR-group is not redundantly covered in CNF.
    assert frozenset({"done_always"}) in groups
    # p1/p2 stay mutually exclusive inside their own OR-group (done_always
    # removed from it to avoid the join firing on done_always alone before
    # the exclusive siblings finish their stream output).
    assert frozenset({"p1", "p2"}) in groups

    def _fires(arrivals):
        b = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
        n = 0
        for s in arrivals:
            b.accept(BarrierMessage(sender=s, target=b.key))
            if b.is_ready():
                n += 1
                b.consume()
        return n

    # done_always alone must NOT fire (exclusive sibling still pending)...
    assert _fires(["done_always"]) == 0
    # ...both exclusive paths must fire the join exactly once (no deadlock)...
    assert _fires(["done_always", "p1"]) == 1
    assert _fires(["done_always", "p2"]) == 1
    # ...and a late sibling arriving after the join fired must not re-arm it.
    assert _fires(["done_always", "p1", "p2"]) == 1


def test_single_condition_parallel_targets_coexecute():
    """Same condition routing to multiple parallel targets (grouping-patch
    scenario, issue2 "输出不完整"): both targets co-execute when the if-path
    is taken, so each must stay in its own AND-group -- merging them into one
    OR-group would let the join re-run when the second sibling arrives.
    """
    g = _make_graph(
        ["branchA", "llm_1", "llm_2", "dead_end", "JOIN"],
        wait_for_all_ids={"JOIN"},
    )
    r = BranchRouter()
    r.add_branch("cond1", ["llm_1", "llm_2"], branch_id="A-if")
    r.add_branch("True", ["dead_end"], branch_id="A-default")
    g.add_conditional_edges("branchA", r)
    g.register_branch_targets("branchA", {"llm_1", "llm_2", "dead_end"})
    g.add_edge("llm_1", "JOIN")
    g.add_edge("llm_2", "JOIN")

    resolved = g._resolve_barrier_groups("JOIN", [{"llm_1"}, {"llm_2"}])
    assert _groups_as_sets(resolved) == [
        frozenset({"llm_1"}),
        frozenset({"llm_2"}),
    ]

    # Ready only after BOTH co-executing siblings arrive, exactly once.
    barrier = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
    barrier.accept(BarrierMessage(sender="llm_1", target=barrier.key))
    assert not barrier.is_ready()
    barrier.accept(BarrierMessage(sender="llm_2", target=barrier.key))
    assert barrier.is_ready()


def test_coexecuting_with_exclusive_sibling_no_deadlock():
    """Regression (review case C): co-executing predecessor must NOT be
    removed from the OR-group when an exclusive sibling depends on it.

    Topology: 判断 if->T1 / default->T2; T1 and T2 converge into merge->p1
    (p1 reachable from BOTH conditions -> co-executing); T2 also routes to
    p2 (default-only -> exclusive). p1 and p2 both feed JOIN.

    A previous fix candidate pulled p1 out of the OR-group into a standalone
    AND-group, degenerating p2 into a single-member AND-group: on the if-path
    p2 never executes, JOIN never becomes ready -> deadlock.

    Correct grouping keeps {p1, p2} as an OR-group (exclusive alternatives
    may trigger the join alone) AND appends singleton {p1} as a one-shot
    latch (a late p2 on the default path cannot re-arm the barrier alone).
    """
    g = _make_graph(
        ["判断", "T1", "T2", "merge", "p1", "p2", "JOIN"],
        wait_for_all_ids={"JOIN"},
    )
    r = BranchRouter()
    r.add_branch("ctx_empty", ["T1"], branch_id="判断-if")
    r.add_branch("True", ["T2"], branch_id="判断-default")
    g.add_conditional_edges("判断", r)
    g.register_branch_targets("判断", {"T1", "T2"})
    g.add_edge("T1", "merge")
    g.add_edge("T2", "merge")
    g.add_edge("merge", "p1")
    g.add_edge("T2", "p2")
    g.add_edge("p1", "JOIN")
    g.add_edge("p2", "JOIN")

    resolved = g._resolve_barrier_groups("JOIN", [{"p1"}, {"p2"}])
    groups = _groups_as_sets(resolved)
    # Exclusive siblings must remain OR-merged (if-path fires via p1 alone).
    assert frozenset({"p1", "p2"}) in groups
    # Co-executing p1 gets the singleton latch (blocks p2-only re-arming).
    assert frozenset({"p1"}) in groups

    # if-path: only p1 executes -> JOIN must become ready (no deadlock).
    barrier = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
    barrier.accept(BarrierMessage(sender="p1", target=barrier.key))
    assert barrier.is_ready(), "if-path deadlock: p2-only AND-group never satisfied"

    # default-path: p1 then late p2 -> fires once, p2 alone cannot re-arm.
    barrier2 = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
    barrier2.accept(BarrierMessage(sender="p1", target=barrier2.key))
    assert barrier2.is_ready()
    barrier2.consume()
    barrier2.accept(BarrierMessage(sender="p2", target=barrier2.key))
    assert not barrier2.is_ready(), "late exclusive sibling re-armed the barrier"


def test_coexecuting_not_latched_when_exclusives_remain():
    """Regression (review issue 1): co-executing predecessor must NOT get a
    latch when its OR-group still has ≥2 exclusive siblings after removal.

    A latch would redundantly cover the OR-group in CNF, firing the join on
    the co-executing predecessor's arrival alone, before exclusive siblings
    finish streaming (truncating their output). The co-executing predecessor
    must be split out as a standalone AND-group (no latch) instead.

    Topology: branchA if->T1 / default->T2 (both reach 合流->fork);
    fork->done_always (co-executing) AND fork->p1/p2 (exclusive via branchB).
    done_always + p1 + p2 all feed JOIN. Expected groups:
    [{done_always} AND] + [{p1,p2} OR] — join waits for done_always AND one
    exclusive, never fires on done_always alone.
    """
    g = _make_graph(
        ["branchA", "T1", "T2", "合流", "fork", "done_always", "p1", "p2", "JOIN"],
        wait_for_all_ids={"JOIN"},
    )
    r = BranchRouter()
    r.add_branch("cond1", ["T1"], branch_id="A-if")
    r.add_branch("True", ["T2"], branch_id="A-default")
    g.add_conditional_edges("branchA", r)
    g.register_branch_targets("branchA", {"T1", "T2"})
    g.add_edge("T1", "合流")
    g.add_edge("T2", "合流")
    g.add_edge("合流", "fork")
    g.add_edge("fork", "done_always")
    g.add_edge("done_always", "JOIN")
    r2 = BranchRouter()
    r2.add_branch("cond_x", ["p1"], branch_id="B-if")
    r2.add_branch("True", ["p2"], branch_id="B-default")
    g.add_conditional_edges("fork", r2)
    g.register_branch_targets("fork", {"p1", "p2"})
    g.add_edge("p1", "JOIN")
    g.add_edge("p2", "JOIN")

    resolved = g._resolve_barrier_groups(
        "JOIN", [{"done_always"}, {"p1"}, {"p2"}]
    )
    groups = _groups_as_sets(resolved)
    assert frozenset({"done_always"}) in groups
    assert frozenset({"p1", "p2"}) in groups
    # done_always must NOT be latched into the OR-group.
    assert frozenset({"done_always", "p1", "p2"}) not in groups

    barrier = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
    barrier.accept(BarrierMessage(sender="done_always", target=barrier.key))
    assert not barrier.is_ready(), (
        "join fired on done_always alone — latch redundantly covered the "
        "OR-group, truncating exclusive siblings' stream output"
    )


def test_cycle_topology_no_spurious_coexec_latch():
    """Regression (review issue 2): cycle topology must not misclassify
    exclusive predecessors as co-executing via loop-polluted reachability.

    branchA is on a loop (node_if -> branchA, node_def -> branchA). p is
    reachable only via the if-path, q only via the default-path. Without
    the cycle guard, _forward_reachable from node_def traverses the loop
    back to branchA then along the if-edge to node_if -> p, making p look
    reachable from ALL conditions -> spurious latch {p} (and {q}) appended.
    Single-path execution then deadlocks (the other latch never satisfied).

    Expected: [{p, q}] single OR-group; either path alone fires the join.
    """
    g = _make_graph(
        ["branchA", "node_if", "node_def", "p", "q", "JOIN"],
        wait_for_all_ids={"JOIN"},
    )
    r = BranchRouter()
    r.add_branch("c1", ["node_if"], branch_id="A-if")
    r.add_branch("True", ["node_def"], branch_id="A-default")
    g.add_conditional_edges("branchA", r)
    g.register_branch_targets("branchA", {"node_if", "node_def"})
    g.add_edge("node_if", "p")
    g.add_edge("p", "JOIN")
    g.add_edge("node_def", "q")
    g.add_edge("q", "JOIN")
    g.add_edge("node_if", "branchA")  # cycle back
    g.add_edge("node_def", "branchA")  # cycle back

    resolved = g._resolve_barrier_groups("JOIN", [{"p"}, {"q"}])
    groups = _groups_as_sets(resolved)
    assert groups == [frozenset({"p", "q"})], (
        f"cycle polluted reachability -> spurious latches: {groups}"
    )

    # Either single path must satisfy the OR-group (no deadlock).
    for sender in ("p", "q"):
        barrier = BarrierChannel("JOIN", expected_groups=[set(grp) for grp in resolved])
        barrier.accept(BarrierMessage(sender=sender, target=barrier.key))
        assert barrier.is_ready(), f"single-path {sender} deadlocked"
