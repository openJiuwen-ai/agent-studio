# coding: utf-8
"""parallelBranchId 逗号拼接标记的 fork/join 匹配与方案去重验证。

背景（线上问题：判断节点多分支汇聚到同一代码节点被重复执行）：
前端会把汇聚点同时所属的多个并行组标记为逗号拼接串（如 ``"geqp,yumx"``），
fork 侧始终是单 id。修复前 ``build_parallel_join_plan`` 用整串去查
``fork_groups`` 永远 miss，lane/done 机制完全不启用。

本文件覆盖：
1. ``_split_parallel_ids`` 拆分（单元）
2. 判断节点分支扇出 + 逗号 join 标记 → lane 正确建出且去重（4fbd3713 拓扑）
3. start 并行扇出 + 单 id join 标记 → 行为不变（114ba3f6 拓扑，回归保护）
4. 无 fork 匹配 / 无标记 → 不建方案（保持原行为）
"""

from jiuwen.serve.controllers.execution.ir_parallel_utils import (
    _split_parallel_ids,
    build_parallel_join_plan,
)


def _branch_node(node_id: str, if_id: str) -> dict:
    return {
        "id": node_id,
        "type": "jiuwen.branch",
        "configs": {
            "branches": [
                {
                    "boolExpression": "(length(${node_start.systemFields.query}) > 0)",
                    "id": if_id,
                },
                {"id": "default"},
            ]
        },
    }


def _edge(
    source_id: str,
    target_id: str,
    *,
    branch_id: str | None = None,
    parallel_id: str | None = None,
    target_parallel_id: str | None = None,
) -> dict:
    """构造一条 IR connection，避免超长的内联 dict 字面量。

    parallel_id 是 fork 侧标记（source），target_parallel_id 是 join 侧标记（target）。
    """
    source: dict = {"componentId": source_id}
    if branch_id is not None:
        source["branchId"] = branch_id
    if parallel_id is not None:
        source["parallelBranchId"] = parallel_id
    target: dict = {"componentId": target_id}
    if target_parallel_id is not None:
        target["parallelBranchId"] = target_parallel_id
    return {"source": source, "target": target}


def _conditional_fork_node_by_id() -> dict:
    nodes = [
        {"id": "node_start", "type": "jiuwen.start"},
        _branch_node("node_b2", "node_b2-if"),
        _branch_node("node_p", "node_p-if"),
        _branch_node("node_q", "node_q-if"),
        {"id": "node_llm", "type": "jiuwen.LLMComponent"},
        {"id": "node_llm1", "type": "jiuwen.LLMComponent"},
        {"id": "node_llm2", "type": "jiuwen.LLMComponent"},
        {"id": "node_code", "type": "jiuwen.code"},
        {"id": "node_msg", "type": "jiuwen.message"},
    ]
    node_by_id: dict = {}
    for node in nodes:
        node_by_id[node["id"]] = node
    return node_by_id


def _conditional_fork_connections() -> list[dict]:
    """判断_2 的 if/default 都扇出到 判断/判断_1，汇聚点标记为逗号拼接串。"""
    comma = "geqp,yumx"
    return [
        _edge("node_start", "node_b2"),
        _edge("node_b2", "node_p", branch_id="node_b2-if", parallel_id="geqp"),
        _edge("node_b2", "node_q", branch_id="node_b2-if", parallel_id="geqp"),
        _edge("node_b2", "node_p", branch_id="node_b2-default", parallel_id="yumx"),
        _edge("node_b2", "node_q", branch_id="node_b2-default", parallel_id="yumx"),
        _edge("node_p", "node_llm", branch_id="node_p-if"),
        _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id=comma),
        _edge("node_q", "node_llm1", branch_id="node_q-if"),
        _edge("node_q", "node_code", branch_id="node_q-default", target_parallel_id=comma),
        _edge("node_llm", "node_code", target_parallel_id=comma),
        _edge("node_llm1", "node_llm2"),
        _edge("node_llm2", "node_code", target_parallel_id=comma),
        _edge("node_code", "node_msg"),
    ]


def _start_fork_connections() -> list[dict]:
    """start 并行扇出到 判断/判断_1，汇聚点标记为单个 parallel id。"""
    return [
        _edge("node_start", "node_p", parallel_id="zzja"),
        _edge("node_start", "node_q", parallel_id="zzja"),
        _edge("node_p", "node_llm", branch_id="node_p-if"),
        _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id="zzja"),
        _edge("node_q", "node_llm1", branch_id="node_q-if"),
        _edge("node_q", "node_code", branch_id="node_q-default", target_parallel_id="zzja"),
        _edge("node_llm", "node_code", target_parallel_id="zzja"),
        _edge("node_llm1", "node_llm2"),
        _edge("node_llm2", "node_code", target_parallel_id="zzja"),
        _edge("node_code", "node_msg"),
    ]


def _expected_lane_terminals() -> dict[str, set[tuple[str, str | None]]]:
    """两种拓扑推导出的 lane 终端应一致（lane 内 if/default 出口互斥，恰好触发一次）。"""
    return {
        "node_p": {("node_p", "node_p-default"), ("node_llm", None)},
        "node_q": {("node_q", "node_q-default"), ("node_llm2", None)},
    }


class TestSplitParallelIds:
    @staticmethod
    def test_none_and_non_string():
        assert _split_parallel_ids(None) == []
        assert _split_parallel_ids(123) == []
        assert _split_parallel_ids("") == []

    @staticmethod
    def test_single_id():
        assert _split_parallel_ids("zzja") == ["zzja"]
        assert _split_parallel_ids("  zzja  ") == ["zzja"]

    @staticmethod
    def test_comma_joined():
        assert _split_parallel_ids("geqp,yumx") == ["geqp", "yumx"]
        assert _split_parallel_ids(" a , b ,c ") == ["a", "b", "c"]
        assert _split_parallel_ids("a,,b") == ["a", "b"]


class TestConditionalForkCommaJoin:
    """判断节点分支扇出 + 逗号 join 标记（线上 4fbd3713 拓扑）。"""

    @staticmethod
    def test_lanes_built_and_deduped():
        plan = build_parallel_join_plan(
            _conditional_fork_connections(), _conditional_fork_node_by_id()
        )
        # 逗号拆分后 geqp/yumx 两个 id 推导出的方案内容相同，只保留一个
        assert len(plan.joins) == 1
        spec = next(iter(plan.joins.values()))
        assert spec.fork_source == "node_b2"
        assert spec.join_target == "node_code"

        lanes = {lane.lane_start: lane for lane in spec.lanes}
        assert set(lanes) == {"node_p", "node_q"}
        expected = _expected_lane_terminals()
        for lane_start, lane in lanes.items():
            assert set(lane.terminals) == expected[lane_start], lane_start

        # 4 条 join 入边全部改写，且 done 节点属于同一个方案（同一 parallel id 前缀）
        assert len(plan.terminal_to_done) == 4
        done_ids = set(plan.terminal_to_done.values())
        assert len(done_ids) == 2
        assert len(plan.done_nodes) == 2

    @staticmethod
    def test_terminal_rewrite_covers_all_join_edges():
        plan = build_parallel_join_plan(
            _conditional_fork_connections(), _conditional_fork_node_by_id()
        )
        for source, branch in [
            ("node_p", "node_p-default"),
            ("node_q", "node_q-default"),
            ("node_llm", None),
            ("node_llm2", None),
        ]:
            assert (source, "node_code", branch) in plan.terminal_to_done


class TestStartForkSingleIdUnchanged:
    """start 并行扇出 + 单 id 标记（114ba3f6 拓扑），修复不应改变既有行为。"""

    @staticmethod
    def test_lanes_built_as_before():
        plan = build_parallel_join_plan(
            _start_fork_connections(), _conditional_fork_node_by_id()
        )
        assert len(plan.joins) == 1
        spec = next(iter(plan.joins.values()))
        assert spec.fork_source == "node_start"
        assert spec.join_target == "node_code"
        lanes = {lane.lane_start: lane for lane in spec.lanes}
        assert set(lanes) == {"node_p", "node_q"}
        expected = _expected_lane_terminals()
        for lane_start, lane in lanes.items():
            assert set(lane.terminals) == expected[lane_start], lane_start


class TestNoForkOrNoMarker:
    @staticmethod
    def test_comma_join_without_fork_marker_builds_nothing():
        connections = [
            _edge("node_start", "node_p"),
            _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id="geqp,yumx"),
            _edge("node_p", "node_llm", branch_id="node_p-if"),
            _edge("node_llm", "node_code", target_parallel_id="geqp,yumx"),
        ]
        plan = build_parallel_join_plan(connections, _conditional_fork_node_by_id())
        assert plan.joins == {}
        assert plan.terminal_to_done == {}

    @staticmethod
    def test_plain_convergence_without_marker_builds_nothing():
        connections = [
            _edge("node_start", "node_p"),
            _edge("node_p", "node_llm", branch_id="node_p-if"),
            _edge("node_p", "node_code", branch_id="node_p-default"),
            _edge("node_llm", "node_code"),
        ]
        plan = build_parallel_join_plan(connections, _conditional_fork_node_by_id())
        assert plan.joins == {}


def _dual_fork_connections() -> list[dict]:
    """两个 fork source（node_b2/node_c）都扇出到 P/Q，join 标记逗号拼接。

    geqp/yumx 各自推导出 fork source 不同但 terminals 重叠的 lane 方案，
    用于验证 terminal 归属冲突时整个 join_target 回退 wait_for_all。
    """
    comma = "geqp,yumx"
    return [
        _edge("node_start", "node_b2"),
        _edge("node_start", "node_c"),
        _edge("node_b2", "node_p", branch_id="node_b2-if", parallel_id="geqp"),
        _edge("node_b2", "node_q", branch_id="node_b2-if", parallel_id="geqp"),
        _edge("node_b2", "node_p", branch_id="node_b2-default"),
        _edge("node_b2", "node_q", branch_id="node_b2-default"),
        _edge("node_c", "node_p", branch_id="node_c-if", parallel_id="yumx"),
        _edge("node_c", "node_q", branch_id="node_c-if", parallel_id="yumx"),
        _edge("node_c", "node_p", branch_id="node_c-default"),
        _edge("node_c", "node_q", branch_id="node_c-default"),
        _edge("node_p", "node_llm", branch_id="node_p-if"),
        _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id=comma),
        _edge("node_q", "node_llm1", branch_id="node_q-if"),
        _edge("node_q", "node_code", branch_id="node_q-default", target_parallel_id=comma),
        _edge("node_llm", "node_code", target_parallel_id=comma),
        _edge("node_llm1", "node_llm2"),
        _edge("node_llm2", "node_code", target_parallel_id=comma),
        _edge("node_code", "node_msg"),
    ]


class TestErrorBranchEdgeExcluded:
    """错误分支连接（branchId 含 @@）不纳入 lane 归属，由 error_branch 机制接管。"""

    @staticmethod
    def test_error_branch_edge_not_registered_in_terminal_to_done():
        connections = _conditional_fork_connections()
        connections.append(
            _edge(
                "node_p",
                "node_code",
                branch_id="node_p@@error_1",
                target_parallel_id="geqp,yumx",
            )
        )
        plan = build_parallel_join_plan(connections, _conditional_fork_node_by_id())
        # @@ 错误分支边不被 lane 声领（phase1 不会对它执行 rewrite_target）
        assert ("node_p", "node_code", "node_p@@error_1") not in plan.terminal_to_done
        # 正常 join 入边的 lane 归属不受影响
        assert ("node_p", "node_code", "node_p-default") in plan.terminal_to_done
        assert len(plan.joins) == 1


class TestAmbiguousLaneOverlapsFallBack:
    """terminal 归属冲突（重叠 lanes）时整个 join_target 放弃 lane 接管。"""

    @staticmethod
    def test_conflicting_lane_specs_rejected():
        node_by_id = _conditional_fork_node_by_id()
        node_by_id["node_c"] = _branch_node("node_c", "node_c-if")
        plan = build_parallel_join_plan(_dual_fork_connections(), node_by_id)
        # 两套方案对同一批 terminal 声领不同 done 节点 → 全部丢弃，回退 wait_for_all
        assert plan.joins == {}
        assert plan.terminal_to_done == {}


def _disjoint_dual_group_connections() -> list[dict]:
    """两个并行组分别覆盖同一汇聚点的不同入边（terminals 不重叠）。

    geqp 组经 P/Q 子图汇聚到 node_code，yumx 组经 R/S 子图汇聚到同一
    node_code。无 terminal 冲突，但多 spec 会各自产生一条 [done 列表]
    列表边 barrier——没有 wait_for_all 时退化为「任一 barrier 完成即触发」。
    """
    return [
        _edge("node_start", "node_a"),
        _edge("node_start", "node_c"),
        _edge("node_a", "node_p", branch_id="node_a-if", parallel_id="geqp"),
        _edge("node_a", "node_q", branch_id="node_a-if", parallel_id="geqp"),
        _edge("node_a", "node_p", branch_id="node_a-default"),
        _edge("node_a", "node_q", branch_id="node_a-default"),
        _edge("node_c", "node_r", branch_id="node_c-if", parallel_id="yumx"),
        _edge("node_c", "node_s", branch_id="node_c-if", parallel_id="yumx"),
        _edge("node_c", "node_r", branch_id="node_c-default"),
        _edge("node_c", "node_s", branch_id="node_c-default"),
        _edge("node_p", "node_llm", branch_id="node_p-if"),
        _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id="geqp"),
        _edge("node_q", "node_llm1", branch_id="node_q-if"),
        _edge("node_q", "node_code", branch_id="node_q-default", target_parallel_id="geqp"),
        _edge("node_llm", "node_code", target_parallel_id="geqp"),
        _edge("node_llm1", "node_llm2"),
        _edge("node_llm2", "node_code", target_parallel_id="geqp"),
        _edge("node_r", "node_llm3", branch_id="node_r-if"),
        _edge("node_r", "node_code", branch_id="node_r-default", target_parallel_id="yumx"),
        _edge("node_s", "node_code", branch_id="node_s-default", target_parallel_id="yumx"),
        _edge("node_llm3", "node_code", target_parallel_id="yumx"),
        _edge("node_code", "node_msg"),
    ]


class TestMultiSpecJoinTargetFallsBack:
    """同一汇聚点被多个 spec（terminals 不重叠）接管时也整体回退。"""

    @staticmethod
    def test_disjoint_lane_specs_rejected():
        node_by_id = _conditional_fork_node_by_id()
        node_by_id["node_a"] = _branch_node("node_a", "node_a-if")
        node_by_id["node_c"] = _branch_node("node_c", "node_c-if")
        node_by_id["node_r"] = _branch_node("node_r", "node_r-if")
        node_by_id["node_s"] = _branch_node("node_s", "node_s-if")
        node_by_id["node_llm3"] = {"id": "node_llm3", "type": "jiuwen.LLMComponent"}
        plan = build_parallel_join_plan(_disjoint_dual_group_connections(), node_by_id)
        # 多 spec（geqp + yumx）接管同一 join_target → 全部丢弃，回退 wait_for_all，
        # 避免多条 [done 列表] 列表边在无 wait_for_all 时按组重复触发
        assert plan.joins == {}
        assert plan.terminal_to_done == {}


def _exclusive_dual_source_connections() -> list[dict]:
    """互斥双 fork 源共享汇聚点（线上 PMB-W-1 拓扑骨架）。

    node_neg 是判断节点：if 链上的 node_llm 扇出（u1 波）与 default 锚点
    扇出（u2 波）都汇聚到 node_code，两波互斥（同一判断节点的不同条件）。
    修复前两个 spec 因 fork_source 不同无法去重 → 多 spec 整体回退
    wait_for_all，而 wait_for_all 下分支路由边（TriggerMessage 直达）
    绕过 barrier，汇聚节点按到达波数重复执行。
    """
    comma = "u1,u2"
    return [
        _edge("node_start", "node_neg"),
        _edge("node_neg", "node_llm", branch_id="node_neg-if"),
        _edge("node_neg", "node_p", branch_id="node_neg-default", parallel_id="u2"),
        _edge("node_neg", "node_q", branch_id="node_neg-default", parallel_id="u2"),
        _edge("node_llm", "node_p", parallel_id="u1"),
        _edge("node_llm", "node_q", parallel_id="u1"),
        _edge("node_p", "node_llm1", branch_id="node_p-if"),
        _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id=comma),
        _edge("node_q", "node_code", branch_id="node_q-default", target_parallel_id=comma),
        _edge("node_llm1", "node_llm2"),
        _edge("node_llm2", "node_code", target_parallel_id=comma),
        _edge("node_code", "node_msg"),
    ]


class TestExclusiveDualForkMerged:
    """互斥双 fork 源（lane 结构等价、波互斥）→ 合并为单 spec 接管汇聚点。"""

    @staticmethod
    def test_merged_into_single_spec():
        node_by_id = _conditional_fork_node_by_id()
        node_by_id["node_neg"] = _branch_node("node_neg", "node_neg-if")
        plan = build_parallel_join_plan(_exclusive_dual_source_connections(), node_by_id)
        # u1（fork=node_llm）与 u2（fork=node_neg default 锚点）结构等价且互斥
        # → 合并为一个 spec，lane 接管生效
        assert len(plan.joins) == 1
        spec = next(iter(plan.joins.values()))
        assert spec.join_target == "node_code"
        lanes = {lane.lane_start: lane for lane in spec.lanes}
        assert set(lanes) == {"node_p", "node_q"}
        # 全部 join 入边被同一方案接管，仅一套 done 节点
        assert len(plan.terminal_to_done) == 3
        assert len(set(plan.terminal_to_done.values())) == 2
        assert len(plan.done_nodes) == 2
        assert ("node_p", "node_code", "node_p-default") in plan.terminal_to_done
        assert ("node_q", "node_code", "node_q-default") in plan.terminal_to_done
        assert ("node_llm2", "node_code", None) in plan.terminal_to_done

    @staticmethod
    def test_non_exclusive_dual_fork_still_falls_back():
        """fork 源无必经分支条件（start 直达，波可能同时触发）时不合并。"""
        # 把 u1 的 fork 源换成 start 直达（无入边分支条件，与 u2 不互斥）：
        # 删除 node_llm 的扇出边与 node_neg 的 if 入边
        filtered: list[dict] = []
        for c in _exclusive_dual_source_connections():
            src = c["source"]
            if src.get("componentId") == "node_llm":
                continue
            is_neg_if_edge = (
                src.get("componentId") == "node_neg"
                and src.get("branchId") == "node_neg-if"
            )
            if not is_neg_if_edge:
                filtered.append(c)
        connections = [
            _edge("node_start", "node_p", parallel_id="u1"),
            _edge("node_start", "node_q", parallel_id="u1"),
            *filtered,
        ]
        node_by_id = _conditional_fork_node_by_id()
        node_by_id["node_neg"] = _branch_node("node_neg", "node_neg-if")
        plan = build_parallel_join_plan(connections, node_by_id)
        # 两波可能同时触发 → 保持多 spec → 整体回退 wait_for_all
        assert plan.joins == {}
        assert plan.terminal_to_done == {}
