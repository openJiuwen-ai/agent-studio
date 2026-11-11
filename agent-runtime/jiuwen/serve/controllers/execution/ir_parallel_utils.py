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
        source_parallel_id = (source_info.get("parallelBranchId") or "").strip()
        target_parallel_id = (target_info.get("parallelBranchId") or "").strip()
        branch_id = (source_info.get("branchId") or "").strip() or None
        if source_parallel_id:
            fork_groups[source_parallel_id][source].add(target)
        if target_parallel_id:
            join_groups[target_parallel_id][target].append((source, branch_id))

    plan = ParallelJoinPlan()
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

            lanes: list[ParallelLane] = []
            for _, lane_start, terminals in selected:
                lane_key = _sanitize_node_id(lane_start)
                done_node = (
                    f"_parallel_done__{_sanitize_node_id(parallel_id)}"
                    f"__{_sanitize_node_id(join_target)}__{lane_key}"
                )
                terminal_set = frozenset(terminals)
                lanes.append(
                    ParallelLane(
                        lane_key=lane_key,
                        lane_start=lane_start,
                        done_node=done_node,
                        terminals=terminal_set,
                    )
                )
                for terminal_source, branch_id in terminal_set:
                    plan.terminal_to_done[
                        (terminal_source, join_target, branch_id or None)
                    ] = done_node

            plan.joins[(parallel_id, join_target)] = ParallelJoinSpec(
                parallel_id=parallel_id,
                fork_source=first_fork_source,
                join_target=join_target,
                lanes=tuple(sorted(lanes, key=lambda item: item.done_node)),
            )

    return plan


def collect_parallel_join_nodes(
    connections: list[dict],
    node_by_id: dict[str, dict] | None = None,
) -> frozenset[str]:
    """Return node IDs that join two or more incoming edges.

    Two detection paths:
    1. Explicit: ``parallelBranchId`` on the connection target (IR marks
       branch convergence; the old BPMN converter inserts an inclusive
       gateway there).
    2. Auto: in-degree >= 2 from real (non-synthetic, non-back-edge)
       sources.  Restores the old BPMN engine's implicit AND-join semantics
       (multi-incoming = wait for all) without requiring ``parallelBranchId``.

    Branch exclusivity (same-branch predecessors) is resolved at compile time
    by ``_resolve_barrier_groups`` into CNF OR-groups, so mutually exclusive
    branches (intent/branch routing) won't deadlock.
    """
    adjacency = _build_reachability_graph(connections, node_by_id)
    groups: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    in_degree: dict[str, set[str]] = defaultdict(set)

    for connection in connections:
        source_info = connection.get("source") or {}
        target_info = connection.get("target") or {}
        source = _component_id(source_info)
        target = _component_id(target_info)

        # Shared filters for both detection paths:
        # - skip synthetic paired nodes (_input/_output)
        # - skip back-edges (cycle: target can reach source)
        if not source or not target:
            continue
        if source.endswith("_input") or target.endswith("_output"):
            continue
        if _is_reachable(adjacency, target, source):
            continue

        # Path 1: explicit parallelBranchId detection (backward compatible)
        parallel_id = (target_info.get("parallelBranchId") or "").strip()
        if parallel_id:
            groups[target][parallel_id].add(source)

        # Path 2: auto in-degree detection (set of unique real sources)
        in_degree[target].add(source)

    join_nodes: set[str] = set()

    # Path 1 results: parallelBranchId convergence
    for target, parallel_groups in groups.items():
        for sources in parallel_groups.values():
            if len(sources) >= 2:
                join_nodes.add(target)

    # Path 2 results: any node with >=2 unique real predecessors.
    # Branch exclusivity handled by _resolve_barrier_groups (CNF OR-groups).
    for target, sources in in_degree.items():
        if len(sources) >= 2:
            join_nodes.add(target)

    return frozenset(join_nodes)
