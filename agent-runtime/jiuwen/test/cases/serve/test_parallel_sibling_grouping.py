# coding: utf-8
"""Tests for parallel-sibling stream source grouping (issue2 fix).

`_resolve_barrier_groups` must NOT merge two stream producers that sit behind
the SAME branch condition (parallel siblings that co-execute) into one CNF
OR-group -- doing so makes `_close_inactive_group_sources` truncate one when
the other fires (the bingxingduofenzhi "输出不完整" bug: aaa missing its last
token, eee empty). It MUST still merge producers behind DIFFERENT conditions
of the same exclusive branch (if vs default) so the not-fired branch's stream
source is sanitized (the 112052 sentinel fix depends on this).

These tests build a PregelGraph with the bingxingduofenzhi branch structure and
assert the resolver's grouping directly.
"""
# pylint: disable=protected-access
#   White-box tests assert on ``PregelGraph._resolve_barrier_groups`` directly.
import pytest

# Warm up openjiuwen fully (graph.graph <-> workflow.workflow cycle resolves here);
# deferred per-function imports below then succeed.
pytest.importorskip("openjiuwen.core.workflow.workflow_config")


def _build_bingxing_graph():
    from openjiuwen.core.graph.graph import PregelGraph
    from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter

    g = PregelGraph()
    # edges
    for src, tgt in [
        ("node_start", "判断"), ("node_start", "判断_1"),
        ("判断", "node_llm"), ("判断", "大模型_2"), ("判断", "代码_1"),
        ("判断_1", "代码"), ("判断_1", "大模型_1"),
        ("node_llm", "END"), ("大模型_2", "END"),
        ("大模型_1", "done_1"), ("代码", "sentinel"),
        ("sentinel", "done_1"), ("done_1", "END"),
        ("代码_1", "END"),
    ]:
        g.add_edge(src, tgt)

    # 判断: if -> [node_llm, 大模型_2] (parallel), default -> 代码_1
    r1 = BranchRouter()
    r1.add_branch("x > 0", ["node_llm", "大模型_2"], branch_id="判断-if")
    r1.add_branch("True", ["代码_1"], branch_id="判断-default")
    g.add_conditional_edges("判断", r1)
    g.register_branch_targets("判断", {"node_llm", "大模型_2", "代码_1"})

    # 判断_1: if -> 代码, default -> 大模型_1
    r2 = BranchRouter()
    r2.add_branch("x > 0", ["代码"], branch_id="判断_1-if")
    r2.add_branch("True", ["大模型_1"], branch_id="判断_1-default")
    g.add_conditional_edges("判断_1", r2)
    g.register_branch_targets("判断_1", {"代码", "大模型_1"})

    return g


def _groups_containing(groups, producer_id):
    return [grp for grp in groups if producer_id in grp]


def test_parallel_siblings_not_merged_into_or_group():
    """node_llm and 大模型_2 (both behind 判断-if, co-execute) must land in
    SEPARATE groups so neither truncates the other."""
    from jiuwen.extension.patches.parallel_branch_grouping_patch import (
        apply_parallel_branch_grouping_patch,
    )
    apply_parallel_branch_grouping_patch()

    g = _build_bingxing_graph()
    groups = g._resolve_barrier_groups("END", [{"node_llm"}, {"大模型_2"}, {"done_1"}])

    llm_groups = _groups_containing(groups, "node_llm")
    big2_groups = _groups_containing(groups, "大模型_2")
    assert len(llm_groups) == 1 and len(big2_groups) == 1
    assert llm_groups[0] is not big2_groups[0], (
        "parallel siblings (same condition) must be in separate groups, "
        f"got merged: {groups}"
    )
    # done_1 is standalone (not behind 判断's branches).
    done_groups = _groups_containing(groups, "done_1")
    assert len(done_groups) == 1 and done_groups[0] == {"done_1"}


def test_exclusive_branch_preserves_or_group():
    """sentinel (判断_1-if) and 大模型_1 (判断_1-default) are behind DIFFERENT
    exclusive conditions -> must stay merged into one OR-group (the sentinel
    fix for 112052 depends on this)."""
    from jiuwen.extension.patches.parallel_branch_grouping_patch import (
        apply_parallel_branch_grouping_patch,
    )
    apply_parallel_branch_grouping_patch()

    g = _build_bingxing_graph()
    groups = g._resolve_barrier_groups("done_1", [{"sentinel"}, {"大模型_1"}])
    merged = [grp for grp in groups if "sentinel" in grp and "大模型_1" in grp]
    assert merged, (
        "exclusive-branch producers (if vs default) must be in one OR-group, "
        f"got {groups}"
    )
