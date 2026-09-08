# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Fix barrier deadlock when nested branch nodes sit between a conditional
branch target and a ``wait_for_all`` node's predecessors.

Must be applied *after* ``apply_parallel_branch_grouping_patch``.
"""
# pylint: disable=protected-access

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from openjiuwen.core.common.logging import workflow_logger as logger

_NESTED_PATCH_APPLIED = False


def _build_adjacency_list(self) -> dict[str, list[str]]:
    """构建邻接表：dict[node -> [neighbors]]，覆盖所有边类型。

    覆盖三类边：
    1. 普通边 self.edges 中 src 是 str 的边
    2. list-source 边 self.edges 中 src 是 list 的边（每个子节点都映射到 tgt）
    3. 条件分支边 self.branches 中每个 router 的 _branches 的 target
    """
    adj: dict[str, list[str]] = defaultdict(list)
    # 普通边 + list-source 边
    for (src, tgt) in self.edges:
        if isinstance(tgt, str):
            if isinstance(src, str):
                adj[src].append(tgt)
            elif isinstance(src, list):
                for s in src:
                    adj[s].append(tgt)
    # 条件分支边
    for branch_node, routers in self.branches.items():
        for _name, br in routers.items():
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
                    adj[branch_node].append(t)
    return adj


def _forward_reachable_patched(self, start_node: str) -> set[str]:
    """BFS forward search: all nodes reachable from *start_node*.

    使用邻接表 O(V+E)，覆盖普通边、list-source 边、条件分支边。
    邻接表缓存在 self._adj_cache 上，整个 compile 期间图拓扑不变，可安全复用。
    结果缓存在 self._reachable_cache 上，同一 start_node 只算一次。
    """
    # 结果缓存：同一 start_node 只算一次
    result_cache = getattr(self, "_reachable_cache", None)
    if result_cache is None:
        result_cache = {}
        self._reachable_cache = result_cache  # type: ignore[attr-defined]
    if start_node in result_cache:
        return result_cache[start_node]

    # 邻接表缓存：整个 compile 期间共享
    adj = getattr(self, "_adj_cache", None)
    if adj is None:
        adj = _build_adjacency_list(self)
        self._adj_cache = adj  # type: ignore[attr-defined]

    visited: set[str] = set()
    queue: deque[str] = deque([start_node])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                queue.append(neighbor)
    result_cache[start_node] = visited
    return visited


def _build_branch_parent_patched(self) -> dict[str, str]:
    """Map nested branch nodes to their parent branch node.

    Uses ``_forward_reachable`` to detect indirect nesting.
    """
    parent: dict[str, str] = {}
    nested_branch_nodes = set(self.branch_targets) | set(self.branches)
    for branch_node_id, targets in self.branch_targets.items():
        for target in targets:
            if target in nested_branch_nodes:
                parent[target] = branch_node_id
            else:
                reachable = self._forward_reachable(target)
                for inner_bn in nested_branch_nodes:
                    if inner_bn != branch_node_id and inner_bn in reachable:
                        if inner_bn not in parent:
                            parent[inner_bn] = branch_node_id
    return parent


def _build_condition_targets(self) -> dict[str, dict[str, set[str]]]:
    """Map ``{branch_node: {condition_id: set(targets)}}`` from branch routers."""
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


def _resolve_barrier_groups_nested_patched(
    self, target_id: str, source_list: list[set[str]]
) -> list[set[str]]:
    """CNF OR-group resolution with nested-branch awareness.

    Fixes:
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

    reachable_cond: dict[tuple[str, str, str], set[str]] = {}
    for bn, cond_map in cond_targets.items():
        for cond_id, targets in cond_map.items():
            for t in targets:
                reachable_cond[(bn, cond_id, t)] = self._forward_reachable(t)

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

    # Level 2 fix: len(co) >= 1 (not just == 1)
    cond_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    legacy_bucket: dict[str, set[str]] = defaultdict(set)
    standalone: list[set[str]] = []
    for p in all_predecessors:
        co = cond_owned.get(p, set())
        lo = legacy_owned.get(p, set())
        if co and not lo:
            for (bn, cond_id) in co:
                cond_bucket[(bn, cond_id)].add(p)
        elif lo and not co:
            for bn in lo:
                legacy_bucket[bn].add(p)
        else:
            standalone.append({p})

    # Level 3 fix: hoist nested branches to root via reachability
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
    for _root, cond_map in root_cond.items():
        if len(cond_map) == 1:
            # Single condition: co-executing siblings stay as separate AND-groups
            for p in next(iter(cond_map.values())):
                result.append({p})
        else:
            # Multiple conditions of same branch: merge into one OR-group
            merged: set[str] = set()
            for preds in cond_map.values():
                merged |= preds
            if merged:
                result.append(merged)
    for _root, preds in root_legacy.items():
        if preds:
            result.append(preds)
    for s in standalone:
        result.append(s)
    return result if result else source_list


_original_forward_reachable: Any = None
_original_resolve_barrier_groups: Any = None
_original_build_branch_parent: Any = None


def apply_nested_branch_barrier_patch() -> bool:
    """Monkey-patch ``PregelGraph`` for nested-branch barrier fix.

    Must be called *after* ``apply_parallel_branch_grouping_patch``.
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
    logger.info("nested_branch_barrier_patch applied")
    return True
