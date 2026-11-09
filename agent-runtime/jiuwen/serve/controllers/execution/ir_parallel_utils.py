# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Utilities for IR parallel-branch fork/join conversion."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
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


@dataclass(frozen=True)
class DeadLaneSkip:
    """A compensating trigger for a parallel lane that the active outer-branch
    arm can never start.

    When an upstream (outer) branch arm routes into only *some* lane heads of a
    parallel join, the other lanes are structurally unreachable on that run, so
    the join's hard AND barrier ``[done_a, done_b, ...] -> join`` can never be
    satisfied (the unreachable lanes' done markers never fire) and the join
    silently deadlocks.

    The fix appends a no-op *skip* node to that arm's branch target list and
    wires ``skip -> dead_lane_done``. The skip fires only on that mutually
    exclusive arm, satisfying the dead lane's done marker while the genuinely
    active lanes run for real. The AND barrier then completes exactly once.
    """

    branch_node: str
    branch_id: str
    skip_node: str
    done_node: str
    join_target: str


@dataclass(frozen=True)
class DeadLaneSkipPlan:
    skips: tuple[DeadLaneSkip, ...] = ()

    @property
    def skip_nodes(self) -> frozenset[str]:
        return frozenset(item.skip_node for item in self.skips)

    @property
    def branch_targets(self) -> tuple[tuple[str, str, str], ...]:
        """Extra ``(branch_node, skip_node, branch_id)`` branch routes."""
        return tuple(
            (item.branch_node, item.skip_node, item.branch_id) for item in self.skips
        )

    @property
    def done_edges(self) -> tuple[tuple[str, str], ...]:
        """Extra ``(skip_node, done_node)`` plain edges."""
        return tuple((item.skip_node, item.done_node) for item in self.skips)


def _endpoint_id(endpoint: object) -> str:
    if isinstance(endpoint, dict):
        return (endpoint.get("componentId") or "").strip()
    if isinstance(endpoint, str):
        return endpoint.strip()
    return ""


def _plain_adjacency(connections: list[dict]) -> dict[str, set[str]]:
    """Adjacency over *unconditional* (``branchId``-less) edges only.

    A plain edge is statically taken regardless of branch decisions, so a node
    reachable over plain edges from a branch arm's head is guaranteed to run on
    that arm without any further condition. Conditional edges are excluded:
    descending them would assume an inner branch's decision we cannot make.
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    for connection in connections:
        source_info = connection.get("source") or {}
        branch_id = ""
        if isinstance(source_info, dict):
            branch_id = (source_info.get("branchId") or "").strip()
        if branch_id:
            continue
        source = _endpoint_id(source_info)
        target = _endpoint_id(connection.get("target"))
        if source and target:
            adjacency[source].add(target)
    return adjacency


def _plain_reach(
    adjacency: dict[str, set[str]], starts: set[str], stop: str | None = None
) -> set[str]:
    reachable: set[str] = set(starts)
    queue = deque(starts)
    while queue:
        node_id = queue.popleft()
        if stop is not None and node_id == stop and node_id not in starts:
            continue
        for nxt in adjacency.get(node_id, ()):
            if nxt in reachable:
                continue
            reachable.add(nxt)
            if nxt != stop:
                queue.append(nxt)
    return reachable


def _arm_reaches_join_without_lane(
    plain_adj: dict[str, set[str]],
    heads: set[str],
    join_target: str,
    lane_starts: frozenset[str],
) -> bool:
    """True if an arm head can reach the join over plain edges WITHOUT passing
    through any lane head.

    Reverse-BFS from the join, never expanding *through* a lane head (a lane
    head is a barrier: paths may end there but cannot bypass it). If a head then
    shows up as a non-lane node that reaches the join, the arm has a lane-free
    route to the join and we cannot prove the AND barrier is what synchronizes
    it -> compensating that arm is unsafe.
    """
    reverse: dict[str, set[str]] = defaultdict(set)
    for source, targets in plain_adj.items():
        for target in targets:
            reverse[target].add(source)

    can_reach = {join_target}
    queue = deque([join_target])
    while queue:
        node_id = queue.popleft()
        for predecessor in reverse.get(node_id, ()):
            if predecessor in can_reach:
                continue
            can_reach.add(predecessor)
            if predecessor not in lane_starts:
                queue.append(predecessor)

    return any(head in can_reach and head not in lane_starts for head in heads)


def _dead_start_covered_by_other_arm(
    dead_start: str,
    *,
    reaches: dict[str, set[str]],
    branch_id: str,
    branch_node: str,
    join_target: str,
    arm_reach: dict[str, dict[str, set[str]]],
    parallel_id: str,
    fork_arm_parallel_ids: dict[tuple[str, str], frozenset[str]],
) -> bool:
    """Guard 2: dead lane ``dead_start`` is covered by a mutually-exclusive arm
    whose branch reaches both the dead start and the join.

    Two kinds of covering evidence are accepted, both runtime-exclusive with
    the arm currently being compensated:

    (a) a sibling arm of the *same* decision node (one decision takes exactly
        one arm, so they are mutually exclusive by construction);
    (b) a *different* decision node's (typically the outer fork_source's)
        full-lane fork arm carrying the *current* parallel_id marker: such an
        arm structurally fans out to every lane without routing through the
        inner decision, so coverage is strongest and cannot over-compensate.
        The current inner decision node must live only on some sibling arm of
        that outer decision and never inside the full-lane arm's reach, which
        proves the two paths are mutually exclusive.
    """

    # (a) same-node sibling arms
    for other_id, other_reach in reaches.items():
        if other_id == branch_id:
            continue
        if dead_start in other_reach and join_target in other_reach:
            return True
    # (b) cross-branch-node current-parallel-group full-lane fork arms
    for other_bn, other_arms in arm_reach.items():
        if other_bn == branch_node:
            continue
        for other_id, other_reach in other_arms.items():
            if parallel_id not in fork_arm_parallel_ids.get(
                (other_bn, other_id), set()
            ):
                continue
            if not (dead_start in other_reach and join_target in other_reach):
                continue
            # Mutual exclusion: the current decision node branch_node must live
            # only on some non-other_id sibling arm of other_bn -- it must appear
            # in a sibling reach and never in the other_id full-lane reach (else
            # the two paths could both hold, are not exclusive, and we must not
            # compensate).
            if branch_node in other_reach:
                continue
            on_sibling_arm = False
            for sibling_id, sibling_reach in other_arms.items():
                if sibling_id != other_id and branch_node in sibling_reach:
                    on_sibling_arm = True
                    break
            if on_sibling_arm:
                return True
    return False


def build_dead_lane_skip_plan(
    connections: list[dict],
    join_plan: ParallelJoinPlan,
) -> DeadLaneSkipPlan:
    """Plan skip sentinels that prevent cross-branch lane-reuse deadlocks.

    Scenario (nested branch reusing a downstream parallel fork's lanes)::

        B.if -> I
        I.if     -> m0 -> va -> C
        I.elseIf -> m1 -> vb -> C
        B.default forks BOTH m0 and m1 (the parallel wave anchored at B)
        C joins [done_m0, done_m1] with a hard AND.

    On ``I.if`` only lane m0 runs; done_m1 can never fire -> C deadlocks, even
    though the graph finishes "normally". This planner adds, per outer arm that
    activates only a strict subset of the lanes, one skip node per dead lane.

    Safety guards (all must hold, otherwise no skip is emitted for that arm):
      * the arm activates at least one lane and does not activate all lanes
        (nothing to compensate otherwise);
      * every plain path from the arm heads to the join passes through a lane
        head (so the AND barrier genuinely gates that arm);
      * every dead lane is provably activated by a *different, mutually
        exclusive* arm of the same branch that itself reaches the join — i.e.
        the lane is only "dead on this arm", not dead in every execution.
    """
    if not join_plan.joins:
        return DeadLaneSkipPlan()

    plain_adj = _plain_adjacency(connections)

    # (fork_source, branch_id) -> {parallel_id}：锚点并行 fork 臂及其所属的并行
    # 组。fork_source 自己有两类臂：
    #   - 带 parallelBranchId 标记的 fork 臂（如 B.default 同时扇出全部 lane）：
    #     该臂必然激活全部 lane，live==lane_starts 会自然排除，绝不补偿；
    #   - 不带标记的普通臂（如 B.if 只路由到单条 lane M0）：该臂只能激活严格
    #     子集，死 lane 与「内层独立判断分支复用 lane」并无二致，必须补偿。
    # 因此不能再对 fork_source 整节点 continue（那会漏掉单 lane 臂），只按
    # 「该臂是否带【当前并行组】的 fork 标记」来排除真正的全 lane fork 臂。
    # 必须把标记按 parallel_id 一并隔离：同一个 fork_source 节点可能参与多个
    # 并行组，某条臂只携带【另一个组】的 fork 标记时，对当前组它仍是普通臂，
    # 不能据此跳过当前组的死 lane 补偿。
    all_parallel_ids = {spec.parallel_id for spec in join_plan.joins.values()}
    fork_arm_parallel_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    for connection in connections:
        source_info = connection.get("source") or {}
        if not isinstance(source_info, dict):
            continue
        branch_id = (source_info.get("branchId") or "").strip()
        if not branch_id:
            continue
        marked_ids = set(_split_parallel_ids(source_info.get("parallelBranchId")))
        tracked = marked_ids & all_parallel_ids
        if tracked:
            fork_arm_parallel_ids[
                (_endpoint_id(source_info), branch_id)
            ] |= tracked

    # branch_node -> {branch_id: {arm head targets}}
    branch_arms: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for connection in connections:
        source_info = connection.get("source") or {}
        branch_id = ""
        if isinstance(source_info, dict):
            branch_id = (source_info.get("branchId") or "").strip()
        if not branch_id:
            continue
        # 错误分支（branchId 含 "@@"）由 converter 的 error_branch 机制单独接线，
        # 不属于普通判定臂：绝不能把它当成一条需要死 lane 补偿的臂，否则会生成
        # branch_id="X@@errorBranch" 的 skip，而普通分支接线无法把该 skip 挂到
        # _error_branch 路由上，最终留下无触发源的 skip 组件。错误分支进入单
        # lane 的汇聚同步交回既有 wait_for_all / error_branch 语义处理（回退）。
        if "@@" in branch_id:
            continue
        source = _endpoint_id(source_info)
        target = _endpoint_id(connection.get("target"))
        if source and target:
            branch_arms[source][branch_id].add(target)

    skips: list[DeadLaneSkip] = []
    seen: set[tuple[str, str, str]] = set()

    for join_spec in join_plan.joins.values():
        join_target = join_spec.join_target
        lanes = join_spec.lanes
        if len(lanes) < 2:
            continue
        lane_starts = frozenset(lane.lane_start for lane in lanes)
        done_by_start = {lane.lane_start: lane.done_node for lane in lanes}

        # branch_node -> {branch_id: plain-reachable set from that arm's heads}
        # 注意：fork 标记臂（全 lane fork）也必须纳入 reach —— Guard 2 需要它
        # 证明「死 lane 在另一条互斥臂上确实会跑」；只是在下方发射补偿时跳过。
        arm_reach: dict[str, dict[str, set[str]]] = {}
        arm_heads: dict[str, dict[str, set[str]]] = {}
        for branch_node, arms in branch_arms.items():
            arm_reach[branch_node] = {}
            arm_heads[branch_node] = {}
            for branch_id, heads in arms.items():
                arm_heads[branch_node][branch_id] = set(heads)
                arm_reach[branch_node][branch_id] = _plain_reach(
                    plain_adj, set(heads), stop=join_target
                )

        for branch_node, reaches in arm_reach.items():
            for branch_id, reach in reaches.items():
                # fork_source 上锚定【当前并行组】的全 lane fork 臂激活全部
                # lane，无需补偿；但其 reach 仍保留供其他臂的 Guard 2 覆盖判定。
                # 仅当该臂携带的是当前 join_spec.parallel_id 标记时才跳过——
                # 携带的若是另一个并行组的标记，对当前组它仍是普通臂，必须补偿。
                if branch_node == join_spec.fork_source and (
                    join_spec.parallel_id
                    in fork_arm_parallel_ids.get(
                        (join_spec.fork_source, branch_id), set()
                    )
                ):
                    continue
                live = lane_starts & reach
                if not live or live == lane_starts:
                    continue
                heads = arm_heads[branch_node][branch_id]

                # Guard 1: the arm must be gated by the lane AND barrier (no
                # lane-free shortcut to the join).
                if _arm_reaches_join_without_lane(
                    plain_adj, heads, join_target, lane_starts
                ):
                    continue

                dead = lane_starts - live

                # Guard 2: each dead lane must be covered by a different,
                # mutually exclusive arm that completes a path to the join.
                # 覆盖证据（同节点兄弟臂 / 跨分支节点外层当前组全 lane fork 臂）
                # 及其严格互斥证明见 _dead_start_covered_by_other_arm。
                covered_all = all(
                    _dead_start_covered_by_other_arm(
                        dead_start,
                        reaches=reaches,
                        branch_id=branch_id,
                        branch_node=branch_node,
                        join_target=join_target,
                        arm_reach=arm_reach,
                        parallel_id=join_spec.parallel_id,
                        fork_arm_parallel_ids=fork_arm_parallel_ids,
                    )
                    for dead_start in dead
                )
                if not covered_all:
                    continue

                for dead_start in dead:
                    done_node = done_by_start[dead_start]
                    # Compact deterministic id: real node ids are long
                    # (e.g. node_1793340726610) and the engine caps component
                    # ids at 100 chars, so spelling out
                    # done + branch_node + branch_id overflows. Hash the stable
                    # identity tuple to a short, collision-resistant suffix that
                    # stays within the limit and is reproducible across builds.
                    identity = f"{done_node}|{branch_node}|{branch_id}"
                    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]
                    skip_node = f"_lane_skip__{digest}"
                    key = (branch_node, branch_id, done_node)
                    if key in seen:
                        continue
                    seen.add(key)
                    skips.append(
                        DeadLaneSkip(
                            branch_node=branch_node,
                            branch_id=branch_id,
                            skip_node=skip_node,
                            done_node=done_node,
                            join_target=join_target,
                        )
                    )

    return DeadLaneSkipPlan(skips=tuple(skips))
