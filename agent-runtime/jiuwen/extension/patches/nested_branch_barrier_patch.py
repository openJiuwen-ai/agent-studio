# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Fix barrier deadlock when nested branch nodes sit between a conditional
branch target and a ``wait_for_all`` node's predecessors.

Must be applied *after* ``apply_parallel_branch_grouping_patch``.
"""
# pylint: disable=protected-access

from __future__ import annotations

import asyncio
import inspect
import itertools

from collections import defaultdict, deque
from typing import Any

from openjiuwen.core.common.logging import workflow_logger as logger

_NESTED_PATCH_APPLIED = False

# 嵌套菱形笛卡尔配对允许生成的 CNF 子句数上限。DNF→CNF 的全组合展开子句数
# 为 ∏|route|，在深层级联嵌套（n 个桶、每桶多前驱）上会指数膨胀；超过上限
# 时告警并回退到 base 的单 AND 组（宁可放弃配对升级，也不拖垮编译期）。
_MAX_DIAMOND_CNF_GROUPS = 256


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
                    # G.CTL.03：拆成 early-continue，避免单 if 布尔表达式过多
                    if inner_bn == branch_node_id or inner_bn not in reachable:
                        continue
                    if inner_bn in parent or _would_create_cycle(
                        parent, inner_bn, branch_node_id
                    ):
                        continue
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
            continue
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                queue.append(neighbor)
    return visited


def _bounded_reach_has_cycle(
    self, start_node: str, stop_at: str | None = None
) -> bool:
    """检测从 ``start_node`` 出发、在 ``stop_at`` 截断的前向区域内是否含环。

    邻接表对判定分支节点**无条件展开全部臂**。无环图里从某条件目标出发不可
    能逆流回到上游分支节点；但含 Loop 回边时，有界 BFS 会沿回边绕回某个判定
    分支，再沿其另一臂漏出，把本不可达的前驱纳入 arm_reach，污染互斥/共行
    签名（与 ``_always_executes`` / ``_build_branch_parent_patched`` 面临的
    环拓扑问题同源）。

    用迭代 DFS 的灰/黑染色判定有向回边：邻居落在 gray 集合（当前 DFS 栈上）
    即存在环。``stop_at`` 节点视为叶子不再扩展，与有界可达的截断口径一致。
    """
    adj = getattr(self, "_adj_cache", None)
    if adj is None:
        adj = _build_adjacency_list(self)
        self._adj_cache = adj  # type: ignore[attr-defined]

    gray: set[str] = {start_node}
    black: set[str] = set()
    order: list[str] = [start_node]
    indices: list[int] = [0]

    def _neighbors_of(node: str) -> list[str]:
        if stop_at is not None and node == stop_at:
            return []
        return adj.get(node, [])

    while order:
        node = order[-1]
        neighbors = _neighbors_of(node)
        index = indices[-1]
        if index < len(neighbors):
            nxt = neighbors[index]
            indices[-1] = index + 1
            if nxt in gray:
                return True
            if nxt in black:
                continue
            gray.add(nxt)
            order.append(nxt)
            indices.append(0)
        else:
            gray.discard(node)
            black.add(node)
            order.pop()
            indices.pop()
    return False


def _bounded_region_has_polluting_cycle(
    self, target_id: str, cond_targets: dict[str, dict[str, set[str]]]
) -> bool:
    """任一判定臂起点（含 legacy 分支目标）在汇聚点截断区域内可达环 => 该汇聚
    点的臂可达签名可能被 loop 回边污染，嵌套菱形配对不可信。"""
    starts: list[str] = []
    for cmap in cond_targets.values():
        for targets in cmap.values():
            starts.extend(targets)
    for bn, targets in self.branch_targets.items():
        if bn in cond_targets:
            continue
        starts.extend(targets)
    return any(
        _bounded_reach_has_cycle(self, start, target_id) for start in starts
    )


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


def _compute_route_signatures(
    self, target_id: str, source_list: list[set[str]]
) -> tuple[
    list[tuple[frozenset, list[str]]],
    list[str],
    dict[str, set[str]],
]:
    """按"有界可达路径签名"把直接前驱分桶。

    返回 ``(routes, shared, pred_multi_arm)``：

    - ``routes``：每项为 ``(signature, predecessors)``。``signature`` 是
      ``frozenset[(branch_node, arm)]``——前驱在这些判定分支上**恰好**只从
      单臂可达；同一签名的多个前驱是同一条执行路径上的 co-executing 前驱
      （需要全部完成）。
    - ``shared``：不受任何判定分支约束的前驱（必经/共享节点，签名为空集）。
    - ``pred_multi_arm``：``p -> {该前驱在其上多臂可达的判定分支}``。多臂
      可达分两种，不能一概归 shared：分支本身只存活于外层某单臂内时是良性
      的（如真菱形 lane 头 P 的两臂都到 D1，而 P 只在 B-if 臂内）；只有在
      **贯穿全部路由的外层锚点**上多臂可达，才是汇合后的共行前驱。条件4
      据此外层锚点裁决，排除共行拓扑。

    有界 BFS 在汇聚点 ``target_id`` 处截断，避免一条臂的前驱经汇聚点污染
    另一条臂的可达集合。
    """
    cond_targets = _build_condition_targets(self)

    arm_reach: list[tuple[str, str, set[str]]] = []
    # 每个「真」判定分支（带 router 条件）的各臂可达集合，用于判定一个分支
    # 节点是否被外层判定的某条单臂支配（inner branch）。
    cond_arm_reach: dict[str, list[set[str]]] = defaultdict(list)
    for bn, cmap in cond_targets.items():
        for cond_id, targets in cmap.items():
            reach: set[str] = set()
            for t in targets:
                reach |= _forward_reachable_bounded(self, t, target_id)
            arm_reach.append((bn, cond_id, reach))
            cond_arm_reach[bn].append(reach)
    for bn, targets in self.branch_targets.items():
        if bn in cond_targets:
            continue
        for t in targets:
            arm_reach.append(
                (bn, f"__target__:{t}", _forward_reachable_bounded(self, t, target_id))
            )

    # inner branch：该分支节点本身只从某个外层判定的**恰好一条臂**可达，即它
    # 被约束在该外层单臂内部。lane 头分支（真菱形的 P/Q，只存活于 B-if）是
    # inner；汇合点之后的分支（外层两臂都可达 Y，Y 再分叉）不是 inner。
    branch_node_ids = set(self.branches.keys())
    inner_branches: set[str] = set()
    for outer_arms in cond_arm_reach.values():
        if len(outer_arms) < 2:
            continue
        for bn in branch_node_ids:
            containing = sum(1 for reach in outer_arms if bn in reach)
            if containing == 1:
                inner_branches.add(bn)

    all_predecessors: set[str] = set()
    for g in source_list:
        all_predecessors |= g

    buckets: dict[frozenset, set[str]] = defaultdict(set)
    # 前驱 -> 在哪些判定分支上多臂可达（不论该分支是否 inner）。
    pred_multi_arm: dict[str, set[str]] = defaultdict(set)
    # 前驱 -> 在哪些「非 inner」判定分支上多臂可达。在非 inner 分支上多臂
    # 可达意味着它是外层多臂汇合后的共行节点（如 S/U 经汇合点 Y 对外层 X
    # 两臂都可达），必须归 shared；而在 inner 分支（lane 头 P）上多臂可达是
    # 良性的，该分支整体只活在某外层单臂内，不影响外层互斥性。
    shared_candidates: set[str] = set()
    for p in all_predecessors:
        arms_per_branch: dict[str, set[str]] = defaultdict(set)
        for bn, arm, reach in arm_reach:
            if p in reach:
                arms_per_branch[bn].add(arm)
        for bn, arms in arms_per_branch.items():
            if len(arms) >= 2:
                pred_multi_arm[p].add(bn)
                if bn not in inner_branches:
                    shared_candidates.add(p)
        signature = frozenset(
            (bn, next(iter(arms)))
            for bn, arms in arms_per_branch.items()
            if len(arms) == 1
        )
        buckets[signature].add(p)

    # 两类 shared：签名为空集（不受任何判定约束的必经节点），以及在非 inner
    # 分支上多臂可达的汇合后共行前驱（从各签名桶中剔除）。
    shared_preds = set(buckets.pop(frozenset(), set())) | shared_candidates
    routes = [
        (sig, sorted(preds - shared_candidates))
        for sig, preds in buckets.items()
        if preds - shared_candidates
    ]
    return routes, sorted(shared_preds), pred_multi_arm


def _resolve_barrier_groups_hybrid(
    self, target_id: str, source_list: list[set[str]]
) -> list[set[str]]:
    """在既有 co-exec/latch 解析之上，叠加嵌套菱形的笛卡尔配对。

    绝大多数拓扑（普通并行 fork、单判定多臂汇聚、共行前驱 latch/standalone、
    同一外层臂内的嵌套分叉、环拓扑回退等）继续走
    :func:`_resolve_barrier_groups_nested_patched` 的成熟结论；只有当下面
    **全部**条件成立时，才判定为嵌套菱形并用笛卡尔积展开，以修复"外层一臂
    内并行 lane 与另一外层互斥直达臂共享汇聚"导致的重复执行/死锁：

    1. 至少识别出 2 条非空执行路径（签名不同的前驱桶）；
    2. 其中至少一条路径含 ≥2 个 co-executing 前驱（某外层臂内部并行 fork
       的多个 lane done）；
    3. 不存在 ``shared`` 前驱——排除汇合后共行前驱、部分条件覆盖（如 2/3
       出口汇聚）、case-C latch、环污染等应由既有逻辑处理的拓扑；
    4. 至少存在**同一个判定分支节点（外层互斥锚点）**，使全部路径在该节点
       上绑定的臂构成**臂↔路径一一对应**（``len(arms) == route_count``，每条
       路径恰好一个互不相同的臂）。这条是嵌套菱形区别于"同一外层臂内的嵌套
       分叉"的关键：菱形的并行 lane 在外层分支的 if 臂、直达前驱在 default
       臂；而同臂内的嵌套分叉（如 ir13：default 臂既扇出内层分支又扇出并行
       节点）各前驱在外层分支上同属一臂，必须整体 AND 等待，不能配对。
       仅要求 ``len(arms) >= 2`` 并不够：若 route_count 多于锚点臂数（如外层
       if 臂内既有并行 fork 又有内层判断产生额外子路由、default 臂直达），共
       享同一外层臂的子路由彼此并不互斥，全笛卡尔积会让汇聚点被部分前驱提前
       满足——因此必须严格一一对应。

    满足时 DNF ``(routeA: p1 ∧ p2) ∨ (routeB: q)`` 展开为 CNF
    ``[{p1,q},{p2,q}]``：任一外层路径完成都恰好满足全部 OR 组一次。
    """
    base = _resolve_barrier_groups_nested_patched(self, target_id, source_list)
    if not self.branch_targets or not source_list:
        return base

    # 环拓扑保护（走读意见）：含 Loop 回边时，有界 BFS 会沿回边绕回判定分支、
    # 再沿另一臂漏出，污染 arm_reach / inner_branches / shared 的判定，可能把
    # 共行前驱误判为互斥路由（或反之），让嵌套菱形条件被错误满足并生成不安全
    # 的笛卡尔配对。检测到任一判定臂起点在汇聚点截断区域内可达环时，整体回退
    # 到 base 的成熟结论（与 _always_executes / _build_branch_parent_patched
    # 的环保护口径一致），绝不升级配对。
    if _bounded_region_has_polluting_cycle(
        self, target_id, _build_condition_targets(self)
    ):
        return base

    routes, shared, pred_multi_arm = _compute_route_signatures(
        self, target_id, source_list
    )

    # 条件 1、2、3
    if len(routes) < 2 or shared or not any(len(preds) >= 2 for _, preds in routes):
        return base

    # 条件 4：存在**同一个分支节点（外层互斥锚点）贯穿全部路径**，这些路径
    # 在该节点上绑定彼此不同的臂，且**没有任何前驱在该锚点上多臂可达**。
    #
    # 「贯穿全部路径 + 锚点对所有前驱都是干净单臂」缺一不可：
    # - 真菱形（外层 B：if 臂内部并行 fork、default 臂直达汇聚）：D1/D2 的
    #   签名都锚定 B-if，直达前驱 DD 锚定 B-default，且三者在 B 上都只单臂
    #   可达（D1 虽在 lane 头 P 的两臂可达，但 P 只存活于 B-if 内，与 B 锚
    #   点无关）—— B 是干净锚点，展开为笛卡尔配对；
    # - 同一外层臂内的内层分叉（ir13）：D1/D2/E1/E2 在外层 B 上同属
    #   B-default（单臂），内层判定 I 只出现在 D1/D2 两条路由、并不贯穿
    #   E1/E2 所在的并行桶 —— 没有贯穿全部路由的互斥锚点，回退 base；
    # - 汇合后共行前驱（外层 X 两臂先合流到 Y，Y 再分叉 S/U）：S/U 经汇合
    #   点 Y 对 X 两臂都可达（在 X 上多臂可达，记于 pred_multi_arm）。一旦
    #   X 作为贯穿各桶的锚点，就会因存在「在 X 上多臂可达」的共行前驱而不
    #   干净，判定不成立 —— 共行前驱绝不参与笛卡尔配对，交回 base 处理。
    route_count = len(routes)
    all_preds = {p for _sig, preds in routes for p in preds}
    arms_by_branch: dict[str, set[str]] = defaultdict(set)
    routes_seen_by_branch: dict[str, set[int]] = defaultdict(set)
    # branch -> arm -> 绑定到该 (branch, arm) 的路由集合。嵌套菱形要求每条
    # 路由在锚点上占用一个**互不相同**的臂（臂↔路由一一对应）；若两条路由
    # 共享同一锚点臂，它们其实同属一条外层激活路径、并不互斥，不得配对。
    arm_routes_by_branch: dict[str, dict[str, set[int]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for route_index, (signature, _preds) in enumerate(routes):
        for bn, arm in signature:
            arms_by_branch[bn].add(arm)
            routes_seen_by_branch[bn].add(route_index)
            arm_routes_by_branch[bn][arm].add(route_index)

    def _anchor_is_clean(bn: str) -> bool:
        # 锚点 bn 必须对每一个前驱都是「恰从单臂可达」：任何前驱在 bn 上多
        # 臂可达，说明它是 bn 两臂汇合后的共行节点，配对会让 wait_for_all
        # 在该前驱先到的路径上被提前满足。
        return all(bn not in pred_multi_arm.get(p, ()) for p in all_preds)

    def _arms_match_routes_one_to_one(bn: str) -> bool:
        # 锚点贯穿全部路由（上面已校验），且不同臂数恰为路由数、每个臂只被
        # 一条路由绑定——这两点合起来保证臂与路由是双射，所有路由才两两互斥。
        arm_map = arm_routes_by_branch.get(bn, {})
        return (
            len(arms_by_branch[bn]) == route_count
            and all(len(owners) == 1 for owners in arm_map.values())
        )

    is_nested_diamond = any(
        len(routes_seen_by_branch[bn]) == route_count
        and _arms_match_routes_one_to_one(bn)
        and _anchor_is_clean(bn)
        for bn in arms_by_branch
    )
    if not is_nested_diamond:
        return base

    # 规模护栏：全组合展开的子句数为各路由桶大小的乘积，深层嵌套下指数
    # 膨胀。超过上限时放弃配对，回退 base 的成熟结论，避免编译期 CPU/内存
    # 被海量 CNF 组拖垮。
    combo_count = 1
    for _sig, preds in routes:
        combo_count *= len(preds)
        if combo_count > _MAX_DIAMOND_CNF_GROUPS:
            logger.warning(
                "nested-diamond CNF expansion at target %s yields %s groups "
                "(> %s cap); fallback to base barrier groups",
                target_id,
                combo_count,
                _MAX_DIAMOND_CNF_GROUPS,
            )
            return base

    result: list[set[str]] = []
    for combo in itertools.product(*[preds for _sig, preds in routes]):
        result.append(set(combo))
    return result if result else base


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



def _make_filtered_selector(original_selector, skip_targets: set[str]):
    """Wrap a branch selector to filter out targets that have regular incoming edges.

    When a wait_for_all node has both conditional (branch) and regular incoming
    edges, the conditional edge is redundant: it fires before data is ready
    (branch nodes evaluate near-instantly, while data-producing nodes take time).
    This wrapper removes such targets from the selector's return value so the
    ConditionalRouter no longer sends TriggerMessages that bypass the barrier.
    """
    is_async = asyncio.iscoroutinefunction(original_selector) or (
        callable(original_selector)
        and asyncio.iscoroutinefunction(getattr(original_selector, "__call__", None))
    )

    if is_async:
        async def _filtered(*args, **kwargs):
            targets = await original_selector(*args, **kwargs)
            if isinstance(targets, str):
                targets = [targets]
            return [t for t in (targets or []) if t not in skip_targets]
    else:
        def _filtered(*args, **kwargs):
            targets = original_selector(*args, **kwargs)
            if isinstance(targets, str):
                targets = [targets]
            return [t for t in (targets or []) if t not in skip_targets]

    return _filtered


def _compile_nested_patched(self, graph_store=None, step_callback=None, nodes=None):
    """Patched ``PregelGraph._compile`` — skip redundant conditional edges to
    multi-input join nodes.

    Problem: a join node with both conditional (branch) and regular edges is
    triggered prematurely by the conditional edge's TriggerMessage, which
    bypasses the BarrierChannel.

    Fix: for targets with both conditional and regular incoming edges,
    verify deadlock-safety **before** adding to ``self.waits``. Only safe
    targets are promoted to barrier mode and have their conditional edge
    selectors filtered.

    Safety check (Step 1.5): for each candidate target J, call
    ``_resolve_barrier_groups`` to get the CNF groups. Then:

    - **Single group**: for each branch condition c that targets J via a
      conditional edge, verify that at least one group member fires when c
      is taken (co-occurrence check). J is only reached on paths where a
      group member fires, so the group is automatically satisfied.

    - **Multiple groups**: every group must have at least one standalone
      member (not owned by any branch condition). Standalone members fire
      on ALL paths, so whenever J is reached via any group's member, all
      other groups are also satisfied. Without this, J could be reached
      via group A's member while group B has no firing member on that
      path → deadlock.

    A member P fires when condition (b_node, c_id) is taken if:
      - P is standalone (not owned by any branch condition), or
      - ALL of P's owning conditions co-occur with (b_node, c_id) — i.e. b_node is
        reachable from cond_id's targets AND from no other condition of
        the same branch node.

    Branches without ``branch_id`` are skipped (matching
    ``_build_condition_targets``) to avoid merging unidentified conditions.
    """
    original_waits: set[str] = set(self.waits)

    # Step 1: Detect targets with both conditional and regular incoming edges.
    regular_pred_map: dict[str, set[str]] = defaultdict(set)
    for (src, tgt) in self.edges:
        if isinstance(tgt, str):
            if isinstance(src, str):
                regular_pred_map[tgt].add(src)
            elif isinstance(src, list):
                for s in src:
                    regular_pred_map[tgt].add(s)

    mixed_targets: dict[str, set[str]] = defaultdict(set)
    for branch_node, routers in self.branches.items():
        for _name, br in routers.items():
            router = getattr(br, "condition", None)
            if router is None:
                continue
            branches_list = getattr(router, "_branches", None)
            if not branches_list:
                continue
            for b in branches_list:
                tgt = b.target
                if isinstance(tgt, str):
                    tgt = [tgt]
                for t in tgt or []:
                    if t in regular_pred_map:
                        mixed_targets[branch_node].add(t)

    # Step 1.5: Safety check — only add to self.waits if filtering is safe.
    # _resolve_barrier_groups does not depend on self.waits (takes source_list
    # as parameter), so we can call it before _original_compile.
    cond_targets = _build_condition_targets(self)

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

    # Forward map of regular (non-conditional) edge targets per source node.
    # Used by _pred_covers BFS to avoid traversing other branch nodes'
    # conditional edges (which are non-deterministic at runtime).
    regular_targets: dict[str, set[str]] = defaultdict(set)
    for (src, tgt) in self.edges:
        if isinstance(tgt, str):
            if isinstance(src, str):
                regular_targets[src].add(tgt)
            elif isinstance(src, list):
                for s in src:
                    regular_targets[s].add(tgt)

    # Reverse conditional edge map: target -> set of branch nodes with
    # conditional edges to it. Used by _pred_covers to detect independent
    # incoming edges to b_node that bypass bn entirely.
    cond_pred_map: dict[str, set[str]] = defaultdict(set)
    for bn_id, routers in self.branches.items():
        for _name, br in routers.items():
            router = getattr(br, "condition", None)
            if router is None:
                continue
            bl = getattr(router, "_branches", None)
            if not bl:
                continue
            for b in bl:
                tgt = b.target
                if isinstance(tgt, str):
                    tgt = [tgt]
                for t in tgt or []:
                    cond_pred_map[t].add(bn_id)

    branch_node_ids: set[str] = set(self.branches.keys())

    def _pred_covers(p: str, b_node: str, c_id: str, join_target: str) -> bool:
        """True if regular pred *p* fires when condition (b_node, c_id) is taken.

        A pred can be owned by multiple conditions (reachable from multiple
        branch targets). It fires when ANY owning condition co-occurs with
        (b_node, c_id) AND has a path to *p* that does not pass through
        b_node\'s other conditions\' conditional edges. The path check
        prevents false positives where ownership is transitive through a
        mutually-exclusive branch (e.g. P-default -> B -> B-if -> C, where
        C is only reachable if B takes B-if, not B-default).

        Additional safety checks:
        - BFS does not traverse OTHER branch nodes\' conditional edges
          (only regular edges), preventing false positives when the path
          passes through a downstream branch node whose specific condition
          may not be taken at runtime.
        - Co-occurrence check verifies b_node has no independent incoming
          edges that bypass bn entirely. If b_node can be reached without
          bn, it may fire without bn taking cond_id, so p is not guaranteed.
        - BFS stops expanding the join target\'s outgoing edges when
          reached. This prevents false positives in cyclic topologies where
          the join target has a back edge to p (e.g. J -> A where A is a
          regular predecessor of J). Without this, BFS would traverse
          J\'s back edge and find p, claiming coverage when p actually
          fires after J — causing a barrier deadlock.
        """
        p_conds: set[tuple[str, str]] = set()
        for (bn, cond_id, _t), nodes in reachable_cond.items():
            if p in nodes:
                p_conds.add((bn, cond_id))
        p_legacy: set[str] = set()
        for (bn, _t), nodes in reachable_legacy.items():
            if p in nodes:
                p_legacy.add(bn)
        if not p_conds and not p_legacy:
            return True
        if p_legacy:
            return False
        # Collect b_node other conditions' targets to exclude from BFS.
        excluded_targets: set[str] = set()
        for _name, br in self.branches.get(b_node, {}).items():
            router = getattr(br, "condition", None)
            if router is None:
                continue
            bl = getattr(router, "_branches", None)
            if not bl:
                continue
            for b in bl:
                cid = getattr(b, "branch_id", None) or ""
                if cid != c_id:
                    tgt = b.target
                    if isinstance(tgt, str):
                        tgt = [tgt]
                    excluded_targets.update(tgt or [])
        adj = getattr(self, "_adj_cache", None)
        if adj is None:
            adj = _build_adjacency_list(self)
            self._adj_cache = adj
        for (bn, cond_id) in p_conds:
            if bn == b_node:
                if cond_id != c_id:
                    continue
                for ct in cond_targets.get(bn, {}).get(cond_id, set()):
                    visited_b: set[str] = set()
                    queue_b: deque[str] = deque([ct])
                    while queue_b:
                        node = queue_b.popleft()
                        if node in visited_b:
                            continue
                        visited_b.add(node)
                        if node == p:
                            return True
                        if node == join_target:
                            continue
                        for neighbor in adj.get(node, []):
                            if node == b_node:
                                if neighbor in excluded_targets:
                                    continue
                            elif node in branch_node_ids:
                                if neighbor not in regular_targets.get(node, set()):
                                    continue
                            if neighbor not in visited_b:
                                queue_b.append(neighbor)
                continue
            cond_reaches = False
            other_reaches = False
            for cid, cts in cond_targets.get(bn, {}).items():
                for ct in cts:
                    nodes = reachable_cond.get((bn, cid, ct), set())
                    if b_node in nodes:
                        if cid == cond_id:
                            cond_reaches = True
                        else:
                            other_reaches = True
            if not (cond_reaches and not other_reaches):
                continue
            # Check for independent incoming edges to b_node that bypass
            # bn entirely. If b_node has any predecessor not reachable
            # from bn's conditions, b_node can fire without bn taking
            # cond_id, so p is not guaranteed.
            bn_all_reachable: set[str] = set()
            for cid, cts in cond_targets.get(bn, {}).items():
                for ct in cts:
                    bn_all_reachable |= reachable_cond.get((bn, cid, ct), set())
            b_preds = (regular_pred_map.get(b_node, set())
                       | cond_pred_map.get(b_node, set()))
            if any(pr != bn and pr not in bn_all_reachable for pr in b_preds):
                continue
            # Co-occurs. Verify p is reachable from cond_id's targets
            # without traversing b_node's other conditions' edges or
            # other branch nodes' conditional edges.
            for ct in cond_targets.get(bn, {}).get(cond_id, set()):
                visited: set[str] = set()
                queue: deque[str] = deque([ct])
                while queue:
                    node = queue.popleft()
                    if node in visited:
                        continue
                    visited.add(node)
                    if node == p:
                        return True
                    if node == join_target:
                        continue
                    for neighbor in adj.get(node, []):
                        if node == b_node:
                            if neighbor in excluded_targets:
                                continue
                        elif node in branch_node_ids:
                            if neighbor not in regular_targets.get(node, set()):
                                continue
                        if neighbor not in visited:
                            queue.append(neighbor)
        return False

    skip_targets: dict[str, set[str]] = defaultdict(set)
    for branch_node, targets in mixed_targets.items():
        if branch_node not in cond_targets:
            continue
        bn_conds = cond_targets[branch_node]
        for t in targets:
            regular_preds = regular_pred_map.get(t, set())
            if not regular_preds:
                continue
            targeting_conds = [
                cid for cid, cts in bn_conds.items() if t in cts
            ]
            if not targeting_conds:
                continue
            source_list: list[set[str]] = []
            for (src, tgt) in self.edges:
                if tgt == t:
                    if isinstance(src, str):
                        source_list.append({src})
                    elif isinstance(src, list):
                        for s in src:
                            source_list.append({s})
            if not source_list:
                continue
            groups = self._resolve_barrier_groups(t, source_list)

            safe = True
            # 环回边保护：若 t 可达 branch_node，则 bn->t 是环的一部分
            # （t 是循环回边目标，如 dryrun 转账"转账主控_意图识别"复合循环：
            # 环尾分支 -default-> 环首分支，环首另有 cycle_begin 常驻入边）。
            # 此时"常驻前驱必然先触发、条件边冗余"的论证只在第一圈成立——
            # 循环再次进入 t 只能靠这条条件边，过滤后第二圈起迭代失效
            # （工作流提前结束/下一轮重启）。故判不安全，不做过滤。
            if branch_node in self._forward_reachable(t):
                safe = False
            elif len(groups) <= 1:
                # Single group: verify co-occurrence for targeting conditions.
                # J is only reached when a group member fires, so the group
                # is automatically satisfied.
                for c_id in targeting_conds:
                    for g in groups:
                        if not any(
                            _pred_covers(p, branch_node, c_id, t) for p in g
                        ):
                            safe = False
                            break
                    if not safe:
                        break
            else:
                # Multiple CNF groups (e.g. nested-diamond cartesian pairing
                # [{D1,DD},{D2,DD}]). The legacy "every group must contain a
                # standalone member" contract rejects the new pairing outright
                # (in a nested diamond every predecessor is condition-owned),
                # silently abandoning the barrier upgrade.
                #
                # Per-arm group-coverage instead. For EACH arm c of branch_node
                # count the groups that contain a predecessor guaranteed to
                # fire on that arm (_pred_covers):
                # - targeting arm (bears the direct conditional edge to t,
                #   which selector filtering removes): t must still be reached
                #   via regular preds, so EVERY group must be covered —
                #   otherwise filtering loses t on that arm;
                # - non-targeting arm: t can only be reached via regular preds.
                #   Either no group fires (t simply not reached on this arm) or
                #   EVERY group fires — a partial coverage means t is reached
                #   while some group can never complete (e.g. arm B-if reaches
                #   J only via a standalone pred Z, while the {C} group is
                #   exclusive to B-default) → barrier deadlock.
                for c_id in bn_conds:
                    covered = 0
                    for g in groups:
                        if any(
                            _pred_covers(p, branch_node, c_id, t) for p in g
                        ):
                            covered += 1
                    if c_id in targeting_conds:
                        if covered != len(groups):
                            safe = False
                            break
                    elif 0 < covered < len(groups):
                        safe = False
                        break

            if safe:
                skip_targets[branch_node].add(t)

    # Step 1.6: Global per-target decision. A target t may have conditional
    # edges from multiple branch nodes. self.waits.add(t) is a global side
    # effect — if any branch's conditional edge to t is NOT filtered, its
    # TriggerMessage bypasses the BarrierChannel and causes premature
    # execution. Therefore, only promote t to barrier mode when ALL branch
    # nodes targeting t are safe (or t was already a barrier node).
    for t in {t for targets in mixed_targets.values() for t in targets}:
        safe_branches = {bn for bn, skip in skip_targets.items() if t in skip}
        all_safe = bool(safe_branches)
        if all_safe:
            # Verify every branch_node with a conditional edge to t is safe.
            for bn, targets in mixed_targets.items():
                if t in targets:
                    if bn not in safe_branches:
                        all_safe = False
                        break
        if all_safe:
            self.waits.add(t)
        elif t not in original_waits:
            # Not all safe and t was not already a barrier node — do NOT
            # promote to barrier mode and do NOT filter any selector.
            for bn in list(skip_targets.keys()):
                skip_targets[bn].discard(t)
        # else: t was already in original_waits (pre-existing barrier node).
        # Keep partial filtering — filter safe selectors, leave unsafe ones.

    # Step 2: Run original _compile (only safe targets are in self.waits).
    # core d8cd86e12（0.1.17_hotfix 线）给 PregelGraph._compile 加了 nodes
    # 形参且 compile() 以关键字传入；本补丁整体替换 _compile，签名不同步
    # 会让工作流在编译期 TypeError（表现为点执行无响应）。develop 线 core
    # 尚无该形参，探测后按需转发，两条 core 线都可加载本补丁
    # （test_nested_branch_barrier_compile_sync 钉住转发语义）。
    if "nodes" in inspect.signature(_original_compile).parameters:
        compiled = _original_compile(
            self, graph_store=graph_store, step_callback=step_callback, nodes=nodes
        )
    else:
        compiled = _original_compile(
            self, graph_store=graph_store, step_callback=step_callback
        )

    # Step 3: Replace ConditionalRouter selectors on safe branch nodes.
    for branch_node, targets_to_skip in skip_targets.items():
        if not targets_to_skip:
            continue
        node = compiled.nodes.get(branch_node)
        if node is None:
            continue
        for router in node.routers:
            selector = getattr(router, "selector", None)
            if selector is None:
                continue
            router.selector = _make_filtered_selector(
                selector, targets_to_skip
            )

    return compiled

_original_forward_reachable: Any = None
_original_compile: Any = None
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
    global _original_compile

    if _NESTED_PATCH_APPLIED:
        return False

    from openjiuwen.core.graph.graph import PregelGraph

    _original_forward_reachable = PregelGraph._forward_reachable
    _original_resolve_barrier_groups = PregelGraph._resolve_barrier_groups
    _original_build_branch_parent = PregelGraph._build_branch_parent
    _original_branch_root = PregelGraph._branch_root
    _original_compile = PregelGraph._compile

    PregelGraph._forward_reachable = _forward_reachable_patched  # type: ignore[assignment]
    PregelGraph._resolve_barrier_groups = _resolve_barrier_groups_hybrid  # type: ignore[assignment]
    PregelGraph._build_branch_parent = _build_branch_parent_patched  # type: ignore[assignment]
    PregelGraph._branch_root = staticmethod(_branch_root_patched)  # type: ignore[assignment]
    PregelGraph._compile = _compile_nested_patched  # type: ignore[assignment]

    _NESTED_PATCH_APPLIED = True
    logger.info("nested_branch_barrier_patch applied")
    return True
