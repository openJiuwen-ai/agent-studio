# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Patch openjiuwen ``PregelGraph`` to fix barrier deadlock when nested branch
nodes sit between a conditional branch target and a ``wait_for_all`` node's
predecessors.

Three bugs cause the deadlock:

1. ``_forward_reachable`` only traverses ``self.edges`` (static edges), not
   ``self.branches`` (conditional edges).  When a branch node (e.g. branch2)
   is on the path from a branch1 target to a barrier node's predecessor, BFS
   cannot cross branch2's conditional edge, so the predecessor is unreachable
   from any branch1 condition → classified as "standalone" → becomes a
   separate AND-group → deadlock when only one condition fires.

2. Ownership classification (``len(co) == 1``) sends any predecessor owned by
   *multiple* conditions of the *same* branch to "standalone" (AND-group).
   This happens when a branch maps multiple conditions to the same target
   (e.g. default and elseIf-1 both route to node_X).  The predecessor behind
   node_X is reachable from both conditions → ``len(co) == 2`` → standalone →
   AND-group → deadlock.  Fix: allow ``len(co) >= 1``; the merge step at
   L155-164 already correctly merges same-branch different-condition groups
   into one OR-group.

3. ``_build_branch_parent`` only checks whether a branch target *is* a nested
   branch node.  It misses indirect nesting where branch2 is reachable from
   branch1's target via intermediate nodes.  Fix: use ``_forward_reachable``
   to detect indirect nesting so branch2's conditions are hoisted to branch1.

All three fixes are applied in a single new monkey-patch that replaces both
``_forward_reachable`` and ``_resolve_barrier_groups``.  The original
``parallel_branch_grouping_patch`` is left untouched; this patch must be
applied *after* it (it re-replaces ``_resolve_barrier_groups``).

Applied at import time from ``IRConverter.build_openjiuwen_workflow_from_ir``
after ``apply_parallel_branch_grouping_patch``.

Safety:
  - Level 2 fix does not change "same-condition → AND" or
    "different-condition → OR" merge semantics; it only allows multi-owned
    predecessors to enter the correct bucket instead of being discarded as
    standalone.
  - Level 3 fix only affects nested branches; non-nested branches are
    unchanged.
  - Existing parallel co-execute logic (same-condition siblings kept as
    separate AND-groups) is fully preserved.
"""
# pylint: disable=protected-access
#   This module monkey-patches ``PregelGraph`` internals and must reach into
#   protected graph methods.  The patched functions run bound to a
#   ``PregelGraph`` instance, so the access is intra-class.

from __future__ import annotations

from collections import defaultdict
from typing import Any

from openjiuwen.core.common.logging import workflow_logger as logger

_NESTED_PATCH_APPLIED = False


# ---------------------------------------------------------------------------
# Level 1: _forward_reachable — traverse conditional edges too
# ---------------------------------------------------------------------------

def _forward_reachable_patched(self, start_node: str) -> set[str]:
    """BFS forward search: all nodes reachable from *start_node*.

    Fixes two bugs in the original:

    1. **List-source edges**: ``src == node`` fails when ``src`` is a list
       (e.g. ``add_connection([done_a, done_b, done_c], target)`` in parallel
       join wiring).  The fix checks ``node in src`` when ``src`` is a list.

    2. **Conditional edges**: the original only traversed ``self.edges``
       (static edges), missing ``self.branches`` (conditional edges).  When a
       branch node sits on the path between a branch target and the barrier
       node's predecessors, those predecessors are unreachable.  The fix also
       traverses all possible branch targets.
    """
    visited: set[str] = set()
    queue = [start_node]
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        # Traverse static edges
        for (src, tgt) in self.edges:
            if isinstance(src, list):
                if node in src and isinstance(tgt, str) and tgt not in visited:
                    queue.append(tgt)
            elif src == node and isinstance(tgt, str) and tgt not in visited:
                queue.append(tgt)
        # Traverse conditional edges (all possible branch targets)
        if node in self.branches:
            for _name, br in self.branches[node].items():
                router = getattr(br, "condition", None)
                if router is None:
                    continue
                branches = getattr(router, "_branches", None)
                if not branches:
                    continue
                for b in branches:
                    tgt = b.target
                    if isinstance(tgt, str):
                        tgt = [tgt]
                    for t in tgt or []:
                        if t not in visited:
                            queue.append(t)
    return visited


# ---------------------------------------------------------------------------
# Level 3: _build_branch_parent — detect indirect nesting via reachability
# ---------------------------------------------------------------------------

def _build_branch_parent_patched(self) -> dict[str, str]:
    """Map nested branch nodes to their parent branch node.

    Uses ``_forward_reachable`` to detect indirect nesting: if branch2 is
    reachable from any branch1 target (through intermediate nodes), branch2
    is nested under branch1.
    """
    parent: dict[str, str] = {}
    nested_branch_nodes = set(self.branch_targets) | set(self.branches)
    for branch_node_id, targets in self.branch_targets.items():
        for target in targets:
            if target in nested_branch_nodes:
                # Direct nesting: target is itself a branch node
                parent[target] = branch_node_id
            else:
                # Indirect nesting: branch node reachable from this target
                reachable = self._forward_reachable(target)
                for inner_bn in nested_branch_nodes:
                    if inner_bn != branch_node_id and inner_bn in reachable:
                        # Only set if not already mapped to a closer parent
                        if inner_bn not in parent:
                            parent[inner_bn] = branch_node_id
    return parent


# ---------------------------------------------------------------------------
# Reuse _build_condition_targets from the original patch
# ---------------------------------------------------------------------------

def _build_condition_targets(self) -> dict[str, dict[str, set[str]]]:
    """Map ``{branch_node: {condition_id: set(targets)}}`` from the branch
    routers registered via ``add_conditional_edges``.

    Copied from ``parallel_branch_grouping_patch._build_condition_targets``
    to keep this module self-contained.
    """
    out: dict[str, dict[str, set[str]]] = {}
    for branch_node, routers in self.branches.items():
        cond_map: dict[str, set[str]] = {}
        has_unidentified = False
        for _name, br in routers.items():
            router = getattr(br, "condition", None)
            if router is None:
                continue
            branches = getattr(router, "_branches", None)
            if not branches:
                continue
            for b in branches:
                cond_id = getattr(b, "branch_id", None)
                if not cond_id:
                    has_unidentified = True
                    break
                tgt = b.target
                if isinstance(tgt, str):
                    tgt = [tgt]
                cond_map.setdefault(cond_id, set()).update(tgt or [])
            if has_unidentified:
                break
        if has_unidentified or not cond_map:
            continue
        out[branch_node] = cond_map
    return out


# ---------------------------------------------------------------------------
# Level 2 + patched _build_branch_parent: _resolve_barrier_groups
# ---------------------------------------------------------------------------

def _resolve_barrier_groups_nested_patched(
    self, target_id: str, source_list: list[set[str]]
) -> list[set[str]]:
    """CNF OR-group resolution with nested-branch awareness.

    Incorporates all three fixes:
    - Uses patched ``_forward_reachable`` (traverses conditional edges).
    - Allows ``len(co) >= 1`` instead of ``== 1`` for ownership classification.
    - Uses patched ``_build_branch_parent`` (detects indirect nesting).
    """
    if not self.branch_targets or not source_list:
        return source_list

    cond_targets = _build_condition_targets(self)

    all_predecessors: set[str] = set()
    for g in source_list:
        all_predecessors |= g

    # Reachability per (branch, condition, target) for condition-aware branches.
    reachable_cond: dict[tuple[str, str, str], set[str]] = {}
    for bn, cond_map in cond_targets.items():
        for cond_id, targets in cond_map.items():
            for t in targets:
                reachable_cond[(bn, cond_id, t)] = self._forward_reachable(t)

    # Reachability per (branch, target) for legacy branches (no condition info).
    reachable_legacy: dict[tuple[str, str], set[str]] = {}
    for bn, targets in self.branch_targets.items():
        if bn in cond_targets:
            continue
        for t in targets:
            reachable_legacy[(bn, t)] = self._forward_reachable(t)

    cond_owned: dict[str, set[tuple[str, str]]] = defaultdict(set)
    legacy_owned: dict[str, set[str]] = defaultdict(set)
    for p in all_predecessors:
        for (bn, cond_id, t), nodes in reachable_cond.items():
            if p in nodes:
                cond_owned[p].add((bn, cond_id))
        for (bn, t), nodes in reachable_legacy.items():
            if p in nodes:
                legacy_owned[p].add(bn)

    # Level 2 fix: allow len(co) >= 1 (not just == 1).
    # A predecessor owned by multiple conditions of the same branch will be
    # added to each condition's bucket; the merge step below already correctly
    # merges same-branch different-condition buckets into one OR-group.
    cond_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    legacy_bucket: dict[str, set[str]] = defaultdict(set)
    standalone: list[set[str]] = []
    for p in all_predecessors:
        co = cond_owned.get(p, set())
        lo = legacy_owned.get(p, set())
        if co and not lo:
            # Add to every condition that owns this predecessor
            for (bn, cond_id) in co:
                cond_bucket[(bn, cond_id)].add(p)
        elif lo and not co:
            for bn in lo:
                legacy_bucket[bn].add(p)
        else:
            standalone.append({p})

    # Level 3 fix: hoist nested branch nodes to their root branch ancestor.
    # Uses patched _build_branch_parent that detects indirect nesting.
    branch_parent = _build_branch_parent_patched(self)
    root_cond: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for (bn, cond_id), preds in cond_bucket.items():
        root = self._branch_root(bn, branch_parent)
        root_cond[root][cond_id] |= preds
    root_legacy: dict[str, set[str]] = defaultdict(set)
    for bn, preds in legacy_bucket.items():
        root = self._branch_root(bn, branch_parent)
        root_legacy[root] |= preds

    result: list[set[str]] = []
    # Condition-aware branches: same condition -> separate (AND, co-execute);
    # different conditions (same branch) -> merge (OR, mutually exclusive).
    for root, cond_map in root_cond.items():
        if len(cond_map) == 1:
            # Single condition: each predecessor is its own AND-group
            # (co-executing siblings must not truncate each other).
            for p in next(iter(cond_map.values())):
                result.append({p})
        else:
            # Multiple conditions of the same branch: merge into one OR-group.
            merged: set[str] = set()
            for preds in cond_map.values():
                merged |= preds
            if merged:
                result.append(merged)
    # Legacy branches: merge all same-branch producers (current behavior).
    for root, preds in root_legacy.items():
        if preds:
            result.append(preds)
    for s in standalone:
        result.append(s)
    return result if result else source_list


# ---------------------------------------------------------------------------
# Apply / entry point
# ---------------------------------------------------------------------------

_original_forward_reachable: Any = None
_original_resolve_barrier_groups: Any = None
_original_build_branch_parent: Any = None


def apply_nested_branch_barrier_patch() -> bool:
    """Monkey-patch ``PregelGraph`` methods for nested-branch barrier fix.

    Replaces ``_forward_reachable``, ``_resolve_barrier_groups`` and
    ``_build_branch_parent``.  Must be called *after*
    ``apply_parallel_branch_grouping_patch`` (which first replaces
    ``_resolve_barrier_groups``); this patch re-replaces it with the
    nested-aware version.
    """
    global _NESTED_PATCH_APPLIED
    global _original_forward_reachable, _original_resolve_barrier_groups
    global _original_build_branch_parent

    if _NESTED_PATCH_APPLIED:
        return False

    from openjiuwen.core.graph.graph import PregelGraph

    _original_forward_reachable = PregelGraph._forward_reachable
    _original_resolve_barrier_groups = PregelGraph._resolve_barrier_groups
    _original_build_branch_parent = PregelGraph._build_branch_parent

    PregelGraph._forward_reachable = _forward_reachable_patched  # type: ignore[assignment]
    PregelGraph._resolve_barrier_groups = _resolve_barrier_groups_nested_patched  # type: ignore[assignment]
    PregelGraph._build_branch_parent = _build_branch_parent_patched  # type: ignore[assignment]

    _NESTED_PATCH_APPLIED = True
    logger.info(
        "nested_branch_barrier_patch applied "
        "(PregelGraph._forward_reachable, _resolve_barrier_groups, _build_branch_parent)"
    )
    return True
