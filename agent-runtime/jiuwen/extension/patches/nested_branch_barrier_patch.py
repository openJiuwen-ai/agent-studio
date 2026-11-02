# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Fix barrier deadlock when nested branch nodes sit between a conditional
branch target and a ``wait_for_all`` node's predecessors.

Must be applied *after* ``apply_parallel_branch_grouping_patch``.
"""
# pylint: disable=protected-access

from __future__ import annotations

import itertools
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


def _forward_reachable_bounded(
    self, start_node: str, stop_at: str | None = None
) -> set[str]:
    """前向 BFS，可穿越条件分支边，但在 ``stop_at`` 节点处停止扩展。

    判定前驱属于哪条互斥臂时，只关心它"能否到达汇聚点 stop_at"，绝不能
    越过汇聚点继续向下——否则一条臂的前驱会经由汇聚点"污染"到另一条臂
    的可达集合（嵌套菱形里 B-default 的 DD 会经汇聚点 X 变得从 B-if 也
    可达，从而抹掉互斥签名）。
    """
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
        if stop_at is not None and node == stop_at:
            # 记录可达汇聚点本身，但不越过它继续扩展。
            continue
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                queue.append(neighbor)
    return visited


def _resolve_barrier_groups_nested_patched(
    self, target_id: str, source_list: list[set[str]]
) -> list[set[str]]:
    """CNF OR-group resolution with precise per-branch route signatures.

    每个直接前驱按其"可达路径签名"分类：对每个判定分支节点，仅当前驱
    **恰好**从该分支的某一条臂可达时，记录 ``(branch, arm)``；从多臂都
    可达（分支汇合点之后的共享节点）或完全不可达，则该分支不构成互斥
    约束。前驱的签名即所有此类 ``(branch, arm)`` 的集合。

    分类语义：
    - 签名相同的前驱在同一次执行中要么全部可达、要么全部不可达，属于
      同一条执行路径上需要**全部完成**的 co-executing 前驱（AND，例如
      外层同一判定臂内并行 fork 的各 lane done）。
    - 签名不同的前驱属于**互斥执行路径**，目标节点在任一路径完成时即
      应触发（OR）。
    - 空签名前驱不受任何判定分支约束（起点直连或所有路径汇合后的共享
      节点），作为独立 AND 组，与每条路径都要求同时满足。

    于是触发条件为 DNF ``(route A: p1 ∧ p2) ∨ (route B: q)``，再按
    笛卡尔积展开为引擎需要的 CNF（list 中每个 set 是一个 OR 组，组间
    AND）：``[{p1,q},{p2,q}]``。

    该签名天然编码嵌套层级（内层判定臂作为签名的一部分），因此无需再
    做 branch hoist，可同时正确处理：
    - 普通并行 fork（所有 done 空签名 -> 纯 AND，正确等待）；
    - 单判定多臂汇聚（不同签名 -> OR，只执行一次）；
    - 嵌套菱形：外层一臂内的并行 lane done（同签名 AND 组）与另一臂的
      直达前驱（另一签名）笛卡尔配对，既不会重复执行也不会死锁。
    """
    if not self.branch_targets or not source_list:
        return source_list

    cond_targets = _build_condition_targets(self)

    # 收集每个判定分支节点上每条互斥臂的前向可达集合。
    # 元组：(branch_node, arm_key, reachable_set)。
    arm_reach: list[tuple[str, str, set[str]]] = []
    for bn, cmap in cond_targets.items():
        for cond_id, targets in cmap.items():
            reach: set[str] = set()
            for t in targets:
                reach |= _forward_reachable_bounded(self, t, target_id)
            arm_reach.append((bn, cond_id, reach))
    # 兼容旧的仅注册了 branch_targets、没有 cond 信息的判定节点：
    # 其每个 target 视作一条独立互斥臂。
    for bn, targets in self.branch_targets.items():
        if bn in cond_targets:
            continue
        for t in targets:
            arm_reach.append(
                (bn, f"__target__:{t}", _forward_reachable_bounded(self, t, target_id))
            )

    all_predecessors: set[str] = set()
    for g in source_list:
        all_predecessors |= g

    # 按路径签名归类前驱。
    routes: dict[frozenset, set[str]] = defaultdict(set)
    for p in all_predecessors:
        arms_per_branch: dict[str, set[str]] = defaultdict(set)
        for bn, arm, reach in arm_reach:
            if p in reach:
                arms_per_branch[bn].add(arm)
        signature = frozenset(
            (bn, next(iter(arms)))
            for bn, arms in arms_per_branch.items()
            if len(arms) == 1
        )
        routes[signature].add(p)

    # 空签名：不受互斥约束的共享/必经前驱，独立 AND 组。
    shared = routes.pop(frozenset(), set())

    result: list[set[str]] = []
    nonempty_routes = [sorted(preds) for preds in routes.values() if preds]
    if nonempty_routes:
        # DNF(路由间 OR、路由内 AND) -> CNF：各路由取一个前驱做笛卡尔积。
        # 单路由时 product 退化为逐元素 AND 组（co-executing 前驱不被误并 OR）。
        for combo in itertools.product(*nonempty_routes):
            result.append(set(combo))
    for p in sorted(shared):
        result.append({p})

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
