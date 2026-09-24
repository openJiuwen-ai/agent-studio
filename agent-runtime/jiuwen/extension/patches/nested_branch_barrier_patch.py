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


def _would_create_cycle(
    parent: dict[str, str], child: str, ancestor: str
) -> bool:
    """检查将 parent[child] = ancestor 是否会形成环。

    沿 parent 链从 ancestor 向上遍历，如果能回到 child 则会成环。
    """
    node = ancestor
    visited: set[str] = set()
    while node in parent and node not in visited:
        visited.add(node)
        node = parent[node]
        if node == child:
            return True
    return False


def _build_branch_parent_patched(self) -> dict[str, str]:
    """Map nested branch nodes to their parent branch node.

    Uses ``_forward_reachable`` to detect indirect nesting.
    赋值前检查是否会形成环（含 loop 的工作流中分支节点互相可达），
    若会成环则跳过——环拓扑中的分支不是真正的嵌套关系。
    """
    parent: dict[str, str] = {}
    nested_branch_nodes = set(self.branch_targets) | set(self.branches)
    for branch_node_id, targets in self.branch_targets.items():
        for target in targets:
            if target in nested_branch_nodes:
                if target != branch_node_id and not _would_create_cycle(
                    parent, target, branch_node_id
                ):
                    parent[target] = branch_node_id
            else:
                reachable = self._forward_reachable(target)
                for inner_bn in nested_branch_nodes:
                    if inner_bn != branch_node_id and inner_bn in reachable:
                        if inner_bn not in parent and not _would_create_cycle(
                            parent, inner_bn, branch_node_id
                        ):
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


def _always_executes(
    co: set[tuple[str, str]],
    branch_all_conds: dict[str, set[str]],
    reachable_cond: dict[tuple[str, str, str], set[str]],
) -> bool:
    """判断前驱是否为"共行前驱"：无论涉及的分支走哪个条件，它都会执行。

    ``co`` 是该前驱可达的 ``(branch_node, cond_id)`` 集合。当 ``co`` 覆盖了
    每个涉及分支节点的**全部**条件时（典型场景：分支的多条路径在 fork 之前
    就已合流，所有并行车道对每个条件都可达），该前驱不是互斥备选，而是
    必然执行的共行前驱。

    环拓扑保护：含 Loop 的工作流中，分支节点可能在环上，从某条件目标出发
    会绕环重新进入分支节点、再沿其他条件边到达本不可达的节点，造成"覆盖
    全部条件"的假象。检测到任一涉及分支节点 bn 出现在**其他条件**目标的
    可达集中时（同 bn 不同条件不算——那是正常的分支多出口），判 False
    （回退原 OR-group 语义，避免误加闩锁导致单边路径死锁）。
    """
    involved_branches: dict[str, set[str]] = defaultdict(set)
    for bn, cond_id in co:
        involved_branches[bn].add(cond_id)
    for bn, conds in involved_branches.items():
        all_conds = branch_all_conds.get(bn)
        if not all_conds or not all_conds <= conds:
            return False

    # 环拓扑保护：bn 出现在任何条件目标的可达集中（含自身其他条件——
    # 单 bn 在环上绕回也算污染）=> 环让可达性绕回分支节点再沿其他条件边
    # 到达本不可达的节点，造成"覆盖全部条件"的假象。判 False 回退原
    # OR-group 语义，避免误加闩锁导致单边路径死锁。
    for bn in involved_branches:
        for (_bn, _cond_id, _t), nodes in reachable_cond.items():
            if bn in nodes:
                return False
    return bool(involved_branches)


def _classify_coexec(
    p: str,
    root_cond: dict[str, dict[str, set[str]]],
) -> str:
    """对共行前驱 p 分类：从所在 OR-group 中概念性移除后判断剩余形态。

    返回:
    - "latch": 移除后同 root 某条件仅剩 1 个成员（互斥备选退化为单元素
      AND-group）→ 必须追加单例闩锁并保留 OR 成员身份（case C）。
    - "standalone": 移除后所有条件仍剩 ≥2 成员 → 共行前驱独立成 AND-group
      并从 OR-group 中移除（意见1：避免冗余覆盖导致 join 提前触发）。
    - "noop": p 不在任何 OR-group 中（纯共行，如客户6车道的每个 done
      都是同条件多目标的共行兄弟）→ 独立成 AND-group（已被 single-condition
      分支处理，此处无需操作）。
    """
    needs_latch = False
    in_or_group = False
    for _root, cond_map in root_cond.items():
        for _cond_id, preds in cond_map.items():
            if p in preds:
                in_or_group = True
                if len(preds) == 2:
                    needs_latch = True
    if not in_or_group:
        return "noop"
    return "latch" if needs_latch else "standalone"


def _resolve_barrier_groups_nested_patched(
    self, target_id: str, source_list: list[set[str]]
) -> list[set[str]]:
    """CNF OR-group resolution with nested-branch awareness.

    Fixes:
    - Uses patched ``_forward_reachable`` (traverses conditional edges).
    - Allows ``len(co) >= 1`` instead of ``== 1`` for ownership classification.
    - Uses patched ``_build_branch_parent`` (detects indirect nesting).
    - Co-executing predecessors (reachable from ALL conditions of every
      involved branch) are identified; a singleton AND-group latch is appended
      ONLY when removing the predecessor would degenerate its OR-group's
      exclusive siblings into a single-member AND-group (case C). When
      exclusive siblings remain ≥2 after removal, no latch is added—the
      OR-group already guarantees exclusive alternatives can trigger the join
      alone, and a latch would redundantly cover the OR-group in CNF, firing
      the join on the co-executing predecessor's arrival before exclusive
      siblings finish (truncating their stream output).
    - Cycle topology guard: a branch node that appears in another condition's
      reachable set indicates reachability was polluted by a loop; the
      predecessor is classified as exclusive (OR-group only), avoiding
      spurious latches that deadlock single-path executions.
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

    branch_all_conds: dict[str, set[str]] = {
        bn: set(cond_map.keys()) for bn, cond_map in cond_targets.items()
    }

    # Level 2 fix: len(co) >= 1 (not just == 1)
    cond_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)
    legacy_bucket: dict[str, set[str]] = defaultdict(set)
    standalone: list[set[str]] = []
    coexec_candidates: set[str] = set()  # 共行前驱候选，待 root_cond 合并后分类
    for p in all_predecessors:
        co = cond_owned.get(p, set())
        lo = legacy_owned.get(p, set())
        if co and not lo:
            if _always_executes(co, branch_all_conds, reachable_cond):
                coexec_candidates.add(p)
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

    # 分类共行前驱：决定从 OR-group 移除 / 追加闩锁 / 不操作
    latch_preds: set[str] = set()      # 保留 OR 成员 + 追加单例闩锁
    remove_preds: set[str] = set()    # 从 OR-group 移除，独立成 AND-group
    for p in coexec_candidates:
        kind = _classify_coexec(p, root_cond)
        if kind == "latch":
            latch_preds.add(p)
        elif kind == "standalone":
            remove_preds.add(p)

    result: list[set[str]] = []
    for _root, cond_map in root_cond.items():
        if len(cond_map) == 1:
            # Single condition: co-executing siblings stay as separate AND-groups
            for p in next(iter(cond_map.values())):
                result.append({p})
        else:
            # Multiple conditions of same branch: merge into one OR-group,
            # excluding standalone-classified co-executing predecessors.
            merged: set[str] = set()
            for preds in cond_map.values():
                for p in preds:
                    if p not in remove_preds:
                        merged.add(p)
            if merged:
                result.append(merged)
    for _root, preds in root_legacy.items():
        if preds:
            result.append(preds)
    for s in standalone:
        result.append(s)
    # 共行前驱独立 AND-group（意见1：移出 OR-group 避免冗余覆盖提前触发）
    for p in remove_preds:
        result.append({p})
    # 共行前驱单例闩锁（case C：保留 OR 成员 + 追加闩锁防迟到重武装）
    for p in latch_preds:
        singleton = {p}
        if singleton not in result:
            result.append(singleton)
    return result if result else source_list


def _branch_root_patched(
    branch_node_id: str, branch_parent: dict[str, str]
) -> str:
    """带环检测的 _branch_root，防止 parent dict 含环时死循环。

    原始 _branch_root 假设 parent 是一棵树（无环），但含 loop 的
    工作流中 _build_branch_parent_patched 可能产生环（已被 B 方案
    源头修复），此为兜底防护。
    """
    root = branch_node_id
    visited: set[str] = set()
    while root in branch_parent and root not in visited:
        visited.add(root)
        root = branch_parent[root]
    return root


_original_forward_reachable: Any = None
_original_resolve_barrier_groups: Any = None
_original_build_branch_parent: Any = None
_original_branch_root: Any = None


def apply_nested_branch_barrier_patch() -> bool:
    """Monkey-patch ``PregelGraph`` for nested-branch barrier fix.

    Must be called *after* ``apply_parallel_branch_grouping_patch``.
    """
    global _NESTED_PATCH_APPLIED
    global _original_forward_reachable, _original_resolve_barrier_groups
    global _original_build_branch_parent, _original_branch_root

    if _NESTED_PATCH_APPLIED:
        return False

    from openjiuwen.core.graph.graph import PregelGraph

    _original_forward_reachable = PregelGraph._forward_reachable
    _original_resolve_barrier_groups = PregelGraph._resolve_barrier_groups
    _original_build_branch_parent = PregelGraph._build_branch_parent
    _original_branch_root = PregelGraph._branch_root

    PregelGraph._forward_reachable = _forward_reachable_patched  # type: ignore[assignment]
    PregelGraph._resolve_barrier_groups = _resolve_barrier_groups_nested_patched  # type: ignore[assignment]
    PregelGraph._build_branch_parent = _build_branch_parent_patched  # type: ignore[assignment]
    PregelGraph._branch_root = staticmethod(_branch_root_patched)  # type: ignore[assignment]

    _NESTED_PATCH_APPLIED = True
    logger.info("nested_branch_barrier_patch applied")
    return True
