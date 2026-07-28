# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Patch openjiuwen ``PregelGraph._resolve_barrier_groups`` to distinguish
parallel-co-executing branch targets from mutually-exclusive ones.

Problem (issue2, bingxingduofenzhi "输出不完整"):
  ``_resolve_barrier_groups`` merged ALL stream producers reachable from the
  same branch node into one CNF OR-group, keyed only on ``branch_node_id``.
  When a branch condition routes to MULTIPLE parallel targets that all
  execute (e.g. 判断-if -> [node_llm, 大模型_2], both LLMs stream to END),
  they are NOT mutually exclusive -- they co-execute. Merging them into one
  OR-group makes ``_close_inactive_group_sources`` close one sibling's queue
  when the other's first token arrives, truncating the sibling (aaa loses its
  last token, eee comes out empty). This was masked while the mixed-lane
  112052 bug aborted the run before END rendered.

Fix:
  Use the branch router's per-condition ``branch_id`` (e.g. ``...-if`` /
  ``...-default``) carried in ``self.branches[*].condition._branches``:
    * producers reachable from the SAME (branch, condition) co-execute ->
      each in its OWN single-member group (AND) -- no mutual truncation.
    * producers reachable from DIFFERENT conditions of the same branch are
      mutually exclusive -> merge into one OR-group (preserves the 112052
      sentinel fix, which relies on {LLM_default, sentinel_if} being OR'd).

Branch routers without ``branch_id`` info (e.g. some IntentDetection) fall
back to legacy semantics (merge all same-branch producers into one OR-group),
so those paths are unchanged.

Applied at import time from ``IRConverter.build_openjiuwen_workflow_from_ir``
(next to ``register_error_recovery_handler``) until agent-core develop merges
the fix. The installed ``openjiuwen`` is a non-editable 0.1.16, so a source
edit in ``agent-core/`` would not reach the running service -- hence this
runtime monkey-patch.
"""
# pylint: disable=protected-access
#   This module monkey-patches ``PregelGraph._resolve_barrier_groups`` and must
#   reach into protected graph internals (``_forward_reachable``,
#   ``_build_branch_parent``, ``_branch_root``). The patched function runs bound
#   to a ``PregelGraph`` instance, so the access is intra-class -- the flag is a
#   false positive of the module-scope definition.

from __future__ import annotations

from collections import defaultdict
from typing import Any

from openjiuwen.core.common.logging import workflow_logger as logger

_PATCH_APPLIED = False


def _build_condition_targets(self) -> dict[str, dict[str, set[str]]]:
    """Map ``{branch_node: {condition_id: set(targets)}}`` from the branch
    routers registered via ``add_conditional_edges``.

    Only branch nodes whose router exposes per-branch ``branch_id`` are
    included; others are omitted so the resolver falls back to legacy OR
    grouping for them.
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


def _resolve_barrier_groups_patched(self, target_id: str, source_list: list[set[str]]) -> list[set[str]]:
    """CNF OR-group resolution aware of per-condition branch targets.

    See module docstring. Falls back to legacy when no per-condition info.
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

    cond_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    legacy_bucket: dict[str, set[str]] = defaultdict(set)
    standalone: list[set[str]] = []
    for p in all_predecessors:
        co = cond_owned.get(p, set())
        lo = legacy_owned.get(p, set())
        if len(co) == 1 and not lo:
            cond_bucket[next(iter(co))].add(p)
        elif len(lo) == 1 and not co:
            legacy_bucket[next(iter(lo))].add(p)
        else:
            standalone.append({p})

    # Hoist nested branch nodes to their root branch ancestor.
    branch_parent = self._build_branch_parent()
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
            for p in next(iter(cond_map.values())):
                result.append({p})
        else:
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


# Preserve the original for fallback / introspection.
_original_resolve_barrier_groups: Any = None


def apply_parallel_branch_grouping_patch() -> bool:
    """Monkey-patch ``PregelGraph._resolve_barrier_groups`` once per process."""
    global _PATCH_APPLIED, _original_resolve_barrier_groups
    if _PATCH_APPLIED:
        return False

    from openjiuwen.core.graph.graph import PregelGraph

    _original_resolve_barrier_groups = PregelGraph._resolve_barrier_groups
    PregelGraph._resolve_barrier_groups = _resolve_barrier_groups_patched  # type: ignore[assignment]

    _PATCH_APPLIED = True
    logger.info("parallel_branch_grouping_patch applied (PregelGraph._resolve_barrier_groups)")
    return True
