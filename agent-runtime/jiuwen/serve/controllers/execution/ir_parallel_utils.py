# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Utilities for IR parallel-branch fork/join conversion."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import re


@dataclass(frozen=True)
class ParallelLane:
    lane_key: str
    lane_start: str
    done_node: str
    terminals: frozenset[tuple[str, str | None]] = frozenset()


@dataclass(frozen=True)
class ParallelJoinSpec:
    parallel_id: str
    fork_source: str
    join_target: str
    lanes: tuple[ParallelLane, ...]


@dataclass
class ParallelJoinPlan:
    joins: dict[tuple[str, str], ParallelJoinSpec] = field(default_factory=dict)
    terminal_to_done: dict[tuple[str, str, str | None], str] = field(
        default_factory=dict
    )

    @property
    def done_nodes(self) -> tuple[str, ...]:
        result: list[str] = []
        for spec in self.joins.values():
            result.extend(lane.done_node for lane in spec.lanes)
        return tuple(result)

    def rewrite_target(
        self, source: str, target: str, branch_id: str | None = None
    ) -> str | None:
        return self.terminal_to_done.get((source, target, branch_id or None))


def _component_id(endpoint: dict) -> str:
    return (endpoint.get("componentId") or "").strip()


def _split_parallel_ids(raw: object) -> list[str]:
    """拆分 parallelBranchId 标记。

    前端在汇聚点会把同时所属的多个并行组标记为逗号拼接串（如 ``"idA,idB"``），
    fork 侧始终是单 id。若不拆分，join 侧的整串与 fork 侧的单 id 永远匹配不上，
    lane/done 机制不会启用（判断节点多分支汇聚场景下汇聚节点会被重复触发）。
    """
    if not isinstance(raw, str):
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _build_reachability_graph(
    connections: list[dict],
    node_by_id: dict[str, dict] | None,
) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for connection in connections:
        source = _component_id(connection.get("source") or {})
        target = _component_id(connection.get("target") or {})
        if source and target:
            adjacency[source].add(target)

    for node_id, node in (node_by_id or {}).items():
        if (node.get("type") or "") != "jiuwen.loop":
            continue
        # Root IR represents loop internals with synthetic input/output nodes.
        # Treat the loop node as reaching its input so loop-body paths are
        # visible when filtering cyclic incoming edges.
        adjacency[node_id].add(f"{node_id}_input")

    return adjacency


def _is_reachable(adjacency: dict[str, set[str]], start: str, target: str) -> bool:
    if not start or not target:
        return False

    visited = {start}
    queue = deque(adjacency.get(start, ()))
    while queue:
        node_id = queue.popleft()
        if node_id == target:
            return True
        if node_id in visited:
            continue
        visited.add(node_id)
        queue.extend(adjacency.get(node_id, ()))
    return False


def _sanitize_node_id(value: str) -> str:
    sanitized = re.sub(r"[^0-9a-zA-Z_]+", "_", value or "")
    return sanitized.strip("_") or "unknown"


def _parse_branch_condition(branch_id: str | None) -> tuple[str, str] | None:
    """解析 branchId（IR 格式 ``nodeId-condition``）为 (分支节点, 条件)。"""
    if not branch_id:
        return None
    node, sep, condition = branch_id.rpartition("-")
    if not node or not sep or not condition:
        return None
    return node, condition


def _wave_conditions(
    fork_source: str,
    fork_edge_branch_ids: set[str | None],
    incoming_branch_ids: set[str | None],
) -> dict[str, set[str]]:
    """推导并行组「波」的必经分支条件，返回 {branch_node: {条件}}。

    仅在能严格证明「波必经某分支节点的某条件」时给出条件：
    1. 锚点 fork：fork 边全部带同一 branchId（挂在同一分支锚点）时，锚点
       仅在分支节点选择该条件时发消息，波必经该条件；
    2. 普通节点 fork：fork 边全部无 branchId，且入边全部带 branchId（无普通
       入边）时，fork source 仅能从这些分支条件路径到达，波必经这些条件；
    其余情况（混合来源/存在普通入边）返回空——不构成互斥证据。
    """
    conds: dict[str, set[str]] = defaultdict(set)
    edge_branches = {b for b in fork_edge_branch_ids if b}
    if len(edge_branches) > 1:
        return conds
    if len(edge_branches) == 1:
        parsed = _parse_branch_condition(next(iter(edge_branches)))
        if parsed:
            conds[parsed[0]].add(parsed[1])
        return conds
    if None in incoming_branch_ids:
        return conds
    for branch_id in incoming_branch_ids:
        parsed = _parse_branch_condition(branch_id)
        if parsed:
            conds[parsed[0]].add(parsed[1])
    return conds


def _waves_mutually_exclusive(
    a: dict[str, set[str]], b: dict[str, set[str]]
) -> bool:
    """两组波的条件在同一分支节点上不相交时，运行时互斥（至多一组触发）。"""
    for node_id in set(a) & set(b):
        if a[node_id] and b[node_id] and not (a[node_id] & b[node_id]):
            return True
    return False


def _shortest_distance(
    adjacency: dict[str, set[str]],
    start: str,
    target: str,
    *,
    stop_nodes: set[str],
) -> int | None:
    if start == target:
        return 0
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        node_id, distance = queue.popleft()
        if node_id in stop_nodes and node_id != start:
            continue
        for next_id in adjacency.get(node_id, ()):
            if next_id == target:
                return distance + 1
            if next_id in visited:
                continue
            visited.add(next_id)
            queue.append((next_id, distance + 1))
    return None


def build_parallel_join_plan(
    connections: list[dict],
    node_by_id: dict[str, dict] | None = None,
) -> ParallelJoinPlan:
    """Build a converter-side plan for parallel fork/join edge rewriting.

    The old BPMN converter treats ``source.parallelBranchId`` as a fork marker
    and ``target.parallelBranchId`` as a join marker.  This plan groups target
    incoming edges by the lane that starts at the matching fork source.
    """

    adjacency = _build_reachability_graph(connections, node_by_id)
    fork_groups: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    fork_edge_branch_ids: dict[str, dict[str, set[str | None]]] = defaultdict(
        lambda: defaultdict(set)
    )
    incoming_branch_ids: dict[str, set[str | None]] = defaultdict(set)
    join_groups: dict[str, dict[str, list[tuple[str, str | None]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for connection in connections:
        source_info = connection.get("source") or {}
        target_info = connection.get("target") or {}
        source = _component_id(source_info)
        target = _component_id(target_info)
        if not source or not target:
            continue
        if source.endswith("_input") or target.endswith("_output"):
            continue
        source_parallel_ids = _split_parallel_ids(source_info.get("parallelBranchId"))
        target_parallel_ids = _split_parallel_ids(target_info.get("parallelBranchId"))
        branch_id = (source_info.get("branchId") or "").strip() or None
        incoming_branch_ids[target].add(branch_id)
        for parallel_id in source_parallel_ids:
            fork_groups[parallel_id][source].add(target)
            fork_edge_branch_ids[parallel_id][source].add(branch_id)
        # 错误分支连接（branchId 含 "@@"）由 converter 的 error_branch 机制
        # 生成 _error_branch 节点直连原 join target，phase1 不会对它执行
        # rewrite_target。若纳入 join 侧登记，lane 覆盖判定会误以为该边被
        # lane 接管而移除 wait_for_all，错误分支退化为独立触发边，汇聚节点
        # 可能提前或重复执行。
        if branch_id and "@@" in branch_id:
            continue
        for parallel_id in target_parallel_ids:
            join_groups[parallel_id][target].append((source, branch_id))

    # 同一汇聚点的候选方案，先推导再按 lane 结构聚类：
    # raw_candidates[join_target] = [(parallel_id, 结构签名, fork_source, selected)]
    raw_candidates: dict[str, list[tuple[str, frozenset, str, list]]] = defaultdict(list)
    for parallel_id, targets in join_groups.items():
        forks = fork_groups.get(parallel_id) or {}
        if not forks:
            continue

        for join_target, incoming_edges in targets.items():
            lane_candidates: list[tuple[str, str, list[tuple[str, str | None]]]] = []
            for fork_source, lane_starts in forks.items():
                lane_to_terminals: dict[str, list[tuple[str, str | None]]] = defaultdict(
                    list
                )
                for incoming_source, branch_id in incoming_edges:
                    best_lane: tuple[int, str] | None = None
                    for lane_start in lane_starts:
                        distance = _shortest_distance(
                            adjacency,
                            lane_start,
                            incoming_source,
                            stop_nodes={join_target},
                        )
                        if distance is None:
                            continue
                        candidate = (distance, lane_start)
                        if best_lane is None or candidate < best_lane:
                            best_lane = candidate
                    if best_lane is not None:
                        lane_to_terminals[best_lane[1]].append(
                            (incoming_source, branch_id)
                        )

                if len(lane_to_terminals) >= 2:
                    for lane_start, terminals in lane_to_terminals.items():
                        lane_candidates.append((fork_source, lane_start, terminals))

            if len(lane_candidates) < 2:
                continue

            # Prefer a single fork source when possible; mixed fork sources for one
            # join are ambiguous and should be handled by future validation.
            first_fork_source = lane_candidates[0][0]
            selected = [
                item for item in lane_candidates if item[0] == first_fork_source
            ]
            if len(selected) < 2:
                continue

            # 结构签名只含 lane 结构（lane_start -> terminals 归属），不含
            # fork_source / parallel_id：同一汇聚点的入边可能同时标记多个并行组
            #（逗号拼接），也可能由不同 fork 源（分支锚点扇出 + 其互斥分支内的
            # 节点扇出）推导出结构完全相同的方案。
            structure_signature = frozenset(
                (lane_start, frozenset(terminals))
                for _, lane_start, terminals in selected
            )
            raw_candidates[join_target].append(
                (parallel_id, structure_signature, first_fork_source, selected)
            )

    def _conditions_for(parallel_id: str, fork_source: str) -> dict[str, set[str]]:
        return _wave_conditions(
            fork_source,
            fork_edge_branch_ids.get(parallel_id, {}).get(fork_source, set()),
            incoming_branch_ids.get(fork_source, set()),
        )

    candidates_by_target: dict[str, list[ParallelJoinSpec]] = defaultdict(list)
    for join_target, items in raw_candidates.items():
        # 按 lane 结构聚类。重复注册会产生两套 done 节点，且第二套的
        # terminal_to_done 会覆盖第一套 → 第一套 done 拿不到入边，barrier
        # 永不满足（死锁）。
        clusters: dict[frozenset, list[tuple[str, frozenset, str, list]]] = {}
        for item in items:
            clusters.setdefault(item[1], []).append(item)

        # 类内多成员仅当两两波互斥时合并为一个 spec：互斥（如同一判断节点
        # if/default 各自扇出到相同子图，或分支锚点扇出与该分支另一条件链内
        # 节点扇出）意味着运行时至多一组波触发，单套 lane-done barrier 的
        # AND 等待语义不变；不互斥（如兄弟分支节点可同时触发两波）时保持
        # 多 spec —— 由下方整体回退 wait_for_all 兜底。
        merged: list[tuple[str, frozenset, str, list]] = []
        for members in clusters.values():
            mutually_exclusive = True
            for i, member_i in enumerate(members):
                for member_j in members[i + 1:]:
                    if not _waves_mutually_exclusive(
                        _conditions_for(member_i[0], member_i[2]),
                        _conditions_for(member_j[0], member_j[2]),
                    ):
                        mutually_exclusive = False
                        break
                if not mutually_exclusive:
                    break
            if len(members) == 1 or mutually_exclusive:
                merged.append(members[0])
            else:
                merged.extend(members)

        for parallel_id, _signature, first_fork_source, selected in merged:
            lanes: list[ParallelLane] = []
            for _, lane_start, terminals in selected:
                lane_key = _sanitize_node_id(lane_start)
                done_node = (
                    f"_parallel_done__{_sanitize_node_id(parallel_id)}"
                    f"__{_sanitize_node_id(join_target)}__{lane_key}"
                )
                lanes.append(
                    ParallelLane(
                        lane_key=lane_key,
                        lane_start=lane_start,
                        done_node=done_node,
                        terminals=frozenset(terminals),
                    )
                )

            candidates_by_target[join_target].append(
                ParallelJoinSpec(
                    parallel_id=parallel_id,
                    fork_source=first_fork_source,
                    join_target=join_target,
                    lanes=tuple(sorted(lanes, key=lambda item: item.done_node)),
                )
            )

    # 同一 join_target 仅允许恰好一个 spec 接管。多个并行组（如逗号拆分
    # 出的非去重方案）接管同一汇聚点时：
    # 1) terminals 重叠的方案会在 terminal_to_done 中互相覆盖映射：被覆盖
    #    的 lane-done 永远等不到该 terminal 的入边（barrier 死锁），或该边
    #    被路由到错误的 done 节点；
    # 2) terminals 不重叠时，Phase 2 也会为每个 spec 各加一条 [done 列表]
    #    -> join_target 的列表边 barrier；没有 wait_for_all 时，多条列表边
    #    退化为「任一 barrier 完成即触发」，汇聚节点会按 barrier 组数重复
    #    执行。
    # 因此多 spec 一律放弃 lane 接管，回退 wait_for_all 兜底；converter 侧
    # 的 wait_for_all 移除判定依赖该单 spec 不变式。
    plan = ParallelJoinPlan()
    for join_target, specs in candidates_by_target.items():
        if len(specs) != 1:
            continue
        spec = specs[0]
        plan.joins[(spec.parallel_id, spec.join_target)] = spec
        for lane in spec.lanes:
            for terminal_source, branch_id in lane.terminals:
                plan.terminal_to_done[
                    (terminal_source, join_target, branch_id or None)
                ] = lane.done_node

    return plan


def collect_parallel_join_nodes(
    connections: list[dict],
    node_by_id: dict[str, dict] | None = None,
) -> frozenset[str]:
    """Return node IDs that join two or more parallel branches.

    IR marks branch convergence with ``parallelBranchId`` on the connection
    target.  The old BPMN converter inserts an inclusive gateway there; the
    openjiuwen workflow needs ``wait_for_all=True`` on the same nodes.
    """
    adjacency = _build_reachability_graph(connections, node_by_id)
    groups: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for connection in connections:
        source_info = connection.get("source") or {}
        target_info = connection.get("target") or {}
        source = _component_id(source_info)
        target = _component_id(target_info)
        parallel_id = (target_info.get("parallelBranchId") or "").strip()
        if not source or not target or not parallel_id:
            continue
        if source.endswith("_input") or target.endswith("_output"):
            continue
        if _is_reachable(adjacency, target, source):
            continue
        groups[target][parallel_id].add(source)

    join_nodes: set[str] = set()
    for target, parallel_groups in groups.items():
        for sources in parallel_groups.values():
            if len(sources) >= 2:
                join_nodes.add(target)
    return frozenset(join_nodes)
