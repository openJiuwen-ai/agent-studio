# coding: utf-8
"""判断节点多分支汇聚到同一代码节点：lane 接管后汇聚节点只执行一次。

背景（线上问题，工作流 4fbd3713）：开始 → 判断_2，其 if/default 分支都扇出到
相同的 判断/判断_1 子图，多路 LLM/default 流最后汇聚到同一个代码节点。
- 修复前：join 标记是逗号拼接串（"geqp,yumx"），与 fork 侧单 id 匹配不上，
  lane/done 机制不启用；代码节点仅靠 wait_for_all + CNF resolver 兜底，
  而各前驱从判断_2 的两个条件都可达，被误并成一个 OR 组 → barrier 退化为
  「任一到达即触发」→ 代码节点按到达 token 数重复执行（query>0 时执行 2 次）。
- 修复后：join 标记按逗号拆分匹配 fork，lane/done 接管汇聚（4 条入边改写为
  2 个 lane-done，[done 列表]→代码 的列表边 barrier 提供 AND 等待），且
  lane 完整覆盖的汇聚点不再叠加 wait_for_all（绕开会误分组的 CNF resolver）。

本文件覆盖：
1. 转换器集成：done 节点建出且去重、join 入边改写、汇聚点不标 wait_for_all
2. 保守回退：join 入边未被 lane 完整覆盖时保留 wait_for_all
3. 引擎级：修复后的接线在 if/default 两种输入下代码节点均只执行一次
4. 自动补边交互：lane 接管的 message 汇聚点，跨跳 schema 引用不补直达边，
   引用源折叠为纯数据引用（不进 [done 列表] barrier——互斥分支下引用源
   永不执行会把 AND barrier 拖死，见 test_schema_ref_source_folded_...）
5. End 汇聚点交互：被折叠的流式引用按批量源切分，字段留在 inputs_schema
   （io_state 解析），不再滞留在无人消费的 stream_inputs_schema 中
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from unittest.mock import patch

import pytest

from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.ir_parallel_utils import (
    build_parallel_join_plan,
    build_dead_lane_skip_plan,
)
from openjiuwen.core.workflow.components.component import WorkflowComponent

from jiuwen.extension.patches.parallel_branch_grouping_patch import (
    apply_parallel_branch_grouping_patch,
)
from jiuwen.extension.patches import nested_branch_barrier_patch as nested_patch
from jiuwen.extension.patches.nested_branch_barrier_patch import (
    apply_nested_branch_barrier_patch,
)

apply_parallel_branch_grouping_patch()
apply_nested_branch_barrier_patch()

# 引擎级测试运行 NodeTask.trigger 回调，需要框架单例存在
try:
    from openjiuwen.core.runner import Runner
    from openjiuwen.core.runner.callback import AsyncCallbackFramework

    if getattr(Runner, "callback_framework", None) is None:
        Runner.callback_framework = AsyncCallbackFramework()
except Exception:  # pragma: no cover
    pass


COMMA = "geqp,yumx"


def _branch_configs(if_id: str) -> dict:
    return {
        "branches": [
            {
                "boolExpression": "(length(${node_start.systemFields.query}) > 0)",
                "id": if_id,
            },
            {"id": "default"},
        ]
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


def _build_conditional_fork_ir(
    *,
    extra_uncovered_edge: bool = False,
    error_branch_edge: bool = False,
    message_join: bool = False,
    end_join: bool = False,
) -> dict:
    """复刻线上 4fbd3713 拓扑：start → 判断_2(if/default 均扇出) → 判断/判断_1 → LLM/default → 代码。

    message_join=True 时汇聚点改为 message 类型，并跨跳引用流式 node_llm1
    （无 IR 直连边的 schema $ref），覆盖「lane 接管 + schema 自动补边」交互。
    end_join=True 时汇聚点改为 End 类型（isStreamOut=False），responseTemplate
    同样跨跳引用流式 node_llm1，覆盖「lane 接管 + End 折叠 + schema 切分」交互。
    """
    if end_join:
        join_node = {
            "id": "node_code",
            "type": "jiuwen.end",
            "configs": {"responseTemplate": "{{result}}", "isStreamOut": False},
            "inputs": {"userFields": {"result": "${node_llm1.userFields.raw_output}"}},
        }
    else:
        join_node = (
            {
                "id": "node_code",
                "type": "jiuwen.message",
                "configs": {"template": "{{text}}"},
                "inputs": {"userFields": {"text": "${node_llm1.userFields.raw_output}"}},
            }
            if message_join
            else {
                "id": "node_code",
                "type": "jiuwen.code",
                "configs": {"code": "def main(args): return {'key0': 'x'}"},
                "inputs": {"userFields": {"test": "111"}},
            }
        )
    components = [
        {
            "id": "node_start",
            "type": "jiuwen.start",
            "inputs": {
                "userFields": {},
                "systemFields": {"query": "", "sys": {}},
            },
            "configs": {"userFields": {"inputs": [], "outputs": []}},
        },
        {"id": "node_b2", "type": "jiuwen.branch", "configs": _branch_configs("node_b2-if")},
        {"id": "node_p", "type": "jiuwen.branch", "configs": _branch_configs("node_p-if")},
        {"id": "node_q", "type": "jiuwen.branch", "configs": _branch_configs("node_q-if")},
        {
            "id": "node_llm",
            "type": "jiuwen.llm",
            "configs": {"stream": False, "responseFormat": {"type": "text"}},
            "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
        },
        {
            "id": "node_llm1",
            "type": "jiuwen.llm",
            "configs": {
                "stream": bool(message_join or end_join),
                "responseFormat": {"type": "text"},
            },
            "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
        },
        {
            "id": "node_llm2",
            "type": "jiuwen.llm",
            "configs": {"stream": False, "responseFormat": {"type": "text"}},
            "inputs": {"userFields": {"query": "${node_llm1.userFields.raw_output}"}},
        },
        join_node,
    ]
    if not end_join:
        # end_join 时汇聚点自身就是 End（终点），不再挂 message → end 尾巴
        components.extend(
            [
                {
                    "id": "node_msg",
                    "type": "jiuwen.message",
                    "configs": {"template": "{{query}}"},
                    "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
                },
                {
                    "id": "node_end",
                    "type": "jiuwen.end",
                    "configs": {"responseTemplate": "{{result}}", "isStreamOut": False},
                    "inputs": {"userFields": {"result": "${node_msg.result}"}},
                },
            ]
        )
    connections = [
        _edge("node_start", "node_b2"),
        _edge("node_b2", "node_p", branch_id="node_b2-if", parallel_id="geqp"),
        _edge("node_b2", "node_q", branch_id="node_b2-if", parallel_id="geqp"),
        _edge("node_b2", "node_p", branch_id="node_b2-default", parallel_id="yumx"),
        _edge("node_b2", "node_q", branch_id="node_b2-default", parallel_id="yumx"),
        _edge("node_p", "node_llm", branch_id="node_p-if"),
        _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id=COMMA),
        _edge("node_q", "node_llm1", branch_id="node_q-if"),
        _edge("node_q", "node_code", branch_id="node_q-default", target_parallel_id=COMMA),
        _edge("node_llm", "node_code", target_parallel_id=COMMA),
        _edge("node_llm1", "node_llm2"),
        _edge("node_llm2", "node_code", target_parallel_id=COMMA),
    ]
    if not end_join:
        connections.extend(
            [_edge("node_code", "node_msg"), _edge("node_msg", "node_end")]
        )
    if extra_uncovered_edge:
        # 一条不属于任何 lane 的直达入边（source 从 lane 出发不可达）
        components.append(
            {
                "id": "node_extra",
                "type": "jiuwen.code",
                "configs": {"code": "def main(args): return {}"},
                "inputs": {"userFields": {}},
            }
        )
        connections.insert(0, _edge("node_start", "node_extra"))
        connections.append(_edge("node_extra", "node_code", target_parallel_id=COMMA))
    if error_branch_edge:
        # node_p 的错误分支直连汇聚点（branchId 含 @@，phase1 跳过 rewrite，
        # 由 _error_branch 节点接管该边）
        connections.append(
            _edge(
                "node_p",
                "node_code",
                branch_id="node_p@@error_1",
                target_parallel_id=COMMA,
            )
        )
    return {"components": components, "connections": connections}


class _MockLLM(WorkflowComponent):
    async def invoke(self, inputs, session, context):
        return {"result": "mock"}


async def _build_workflow(ir: dict):
    original_create = getattr(IRConverter, "_create_component")

    async def _mock_create(node, global_model, *, node_by_id=None, ir_connections=None):
        if node.get("type") == "jiuwen.llm":
            return _MockLLM(), "jiuwen.llm", dict(node.get("configs") or {})
        return await original_create(
            node, global_model, node_by_id=node_by_id, ir_connections=ir_connections
        )

    with patch.object(IRConverter, "_create_component", side_effect=_mock_create):
        lazy = await IRConverter.async_ir_to_workflow(ir)
        return await lazy.instantiate()


def _get_internal(workflow):
    internal = getattr(workflow, "_internal", workflow)
    internal = getattr(internal, "_wrapped", internal)
    internal = getattr(internal, "_internal", internal)
    return internal


def _get_graph(internal):
    return getattr(internal, "_graph")


@pytest.mark.asyncio
async def test_conditional_fork_join_managed_by_lanes():
    """lane 接管汇聚：done 去重建出、join 入边改写、代码节点不标 wait_for_all。"""
    workflow = await _build_workflow(_build_conditional_fork_ir())
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    # 1) 仅一套（2 个）lane-done 节点：逗号拆分出的 geqp/yumx 方案去重
    done_ids = sorted(
        comp_id
        for comp_id in spec.comp_configs
        if comp_id.startswith("_parallel_done__") and "__node_code__" in comp_id
    )
    assert len(done_ids) == 2, f"应恰好 2 个 lane-done，实际 {done_ids}"
    done_p = f"_parallel_done__geqp__node_code__node_p"
    done_q = f"_parallel_done__geqp__node_code__node_q"
    assert done_ids == sorted([done_p, done_q])

    # 2) join 入边全部改写到 lane-done；done 列表以 barrier 汇入代码节点
    assert (spec.edges.get("node_llm") or []) == [done_p]
    assert (spec.edges.get("node_llm2") or []) == [done_q]
    assert (spec.edges.get(done_p) or []) == ["node_code"]
    assert (spec.edges.get(done_q) or []) == ["node_code"]
    # 原始直达边不再存在
    assert "node_code" not in (spec.edges.get("node_llm") or [])

    # 3) 判断节点的 default 分支目标被改写为 lane-done（Phase 1 分支路由改写）
    branch_targets = _collect_branch_targets(graph, "node_p")
    assert branch_targets.get("node_p-default") == [done_p]
    assert branch_targets.get("node_p-if") == ["node_llm"]
    branch_targets_q = _collect_branch_targets(graph, "node_q")
    assert branch_targets_q.get("node_q-default") == [done_q]
    assert branch_targets_q.get("node_q-if") == ["node_llm1"]

    # 4) lane 完整覆盖的汇聚点不再叠加 wait_for_all（绕开会误分组的 CNF resolver）
    assert "node_code" not in graph.waits


@pytest.mark.asyncio
async def test_uncovered_join_keeps_wait_for_all():
    """保守回退：存在未被 lane 覆盖的直达入边时，保留 wait_for_all 兜底。"""
    workflow = await _build_workflow(
        _build_conditional_fork_ir(extra_uncovered_edge=True)
    )
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    done_ids = [
        comp_id
        for comp_id in spec.comp_configs
        if comp_id.startswith("_parallel_done__") and "__node_code__" in comp_id
    ]
    assert len(done_ids) == 2
    # node_extra → node_code 未被 lane 覆盖，保持直达边 + wait_for_all
    assert "node_code" in (spec.edges.get("node_extra") or [])
    assert "node_code" in graph.waits


@pytest.mark.asyncio
async def test_error_branch_join_keeps_wait_for_all():
    """错误分支入边不被 lane 覆盖：保留 wait_for_all，由 _error_branch 节点直连汇聚点。"""
    workflow = await _build_workflow(
        _build_conditional_fork_ir(error_branch_edge=True)
    )
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    # lane 方案仍为其余 4 条 join 入边建立（去重后 2 个 lane-done）
    done_ids = [
        comp_id
        for comp_id in spec.comp_configs
        if comp_id.startswith("_parallel_done__") and "__node_code__" in comp_id
    ]
    assert len(done_ids) == 2
    # @@ 错误分支边未被 lane 接管 → 汇聚点保留 wait_for_all 兜底
    assert "node_code" in graph.waits
    # 错误分支由 _error_branch 节点接管，直连原 join target
    assert "node_p_error_branch" in spec.comp_configs
    error_targets = _collect_branch_targets(graph, "node_p_error_branch")
    assert "node_code" in sum(error_targets.values(), [])


@pytest.mark.asyncio
async def test_schema_ref_source_folded_without_barrier_or_direct_edge():
    """lane 接管的 message 汇聚点：跨跳 schema 引用既不补直达边，也不进 barrier。

    历史行为一（未折叠）：wait_for_all 已被移除，schema 自动补边会给出
    node_llm1 -> node_code 直达边（独立触发边），与 [done 列表] barrier 并存，
    汇聚点可能提前/重复执行。
    历史行为二（折叠进 barrier）：node_llm1 被无条件并入 [done 列表] AND
    barrier。node_llm1 仅在 node_q 的 if 分支执行；query 为空走 default 分支
    时 node_llm1 永不执行，barrier 的 {node_llm1} 组永不满足，汇聚点及其
    下游全部静默不执行（死锁）。引擎无 skip 传播：未触发节点不发
    BarrierMessage。修复：引用源折叠为纯数据引用（io_state 解析），barrier
    仅由 lane-done 组成——lane 内引用源的完成由该 lane 的 done 蕴含，
    互斥分支不执行时由未执行引用兜底。
    """
    workflow = await _build_workflow(_build_conditional_fork_ir(message_join=True))
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    join_id = "node_code"
    done_p = "_parallel_done__geqp__node_code__node_p"
    done_q = "_parallel_done__geqp__node_code__node_q"

    # lane 接管仍然生效：汇聚点无 wait_for_all，且 done 节点正常建出
    assert join_id not in graph.waits
    assert done_p in spec.comp_configs and done_q in spec.comp_configs
    # 跨跳引用的流式 LLM 不再补直达流边
    assert join_id not in (spec.stream_edges.get("node_llm1") or [])
    # 图层面：无 (node_llm1 -> join) 字符串直达边；barrier 列表边仅由两个
    # lane-done 组成，折叠引用源绝不进入（唯一一条进入 join 的列表边）
    into_join = [edge for edge in graph.edges if edge[1] == join_id]
    assert ("node_llm1", join_id) not in into_join
    barrier_edges = [edge for edge in into_join if isinstance(edge[0], list)]
    assert len(barrier_edges) == 1, into_join
    assert set(barrier_edges[0][0]) == {done_p, done_q}


@pytest.mark.asyncio
async def test_end_join_folded_stream_ref_stays_batch():
    """lane 接管的 End 汇聚点：被折叠的流式引用字段必须留在批量侧。

    修复前行为：schema 切分按全局流式源把 result 放进 stream_inputs_schema，
    折叠又删掉了唯一投递通道（流式边）→ End 无 StreamActor/producer，
    INVOKE 只解析 inputs_schema，result 被静默丢弃（模板渲染为空）。
    修复后：折叠源按批量源切分，全量 schema 进 inputs_schema（走 io_state），
    End 只有 INVOKE 能力，不持有无人消费的 stream schema / COLLECT。
    """
    workflow = await _build_workflow(_build_conditional_fork_ir(end_join=True))
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    join_id = "node_code"
    done_p = "_parallel_done__geqp__node_code__node_p"
    done_q = "_parallel_done__geqp__node_code__node_q"

    # 触发语义与 message 场景一致：不补直达流边，barrier 仅由 lane-done 组成
    # （折叠引用源不进 barrier，避免互斥分支下 AND 死锁）
    assert join_id not in (spec.stream_edges.get("node_llm1") or [])
    into_join = [edge for edge in graph.edges if edge[1] == join_id]
    assert ("node_llm1", join_id) not in into_join
    barrier_edges = [edge for edge in into_join if isinstance(edge[0], list)]
    assert len(barrier_edges) == 1, into_join
    assert set(barrier_edges[0][0]) == {done_p, done_q}

    # 修复核心：End 只持批量 schema（含折叠流源字段），无 stream schema
    end_spec = spec.comp_configs[join_id]
    stream_inputs = (
        end_spec.stream_io_configs.inputs_schema
        if end_spec.stream_io_configs is not None
        else None
    )
    assert stream_inputs is None
    inputs_schema = end_spec.io_configs.inputs_schema
    assert (
        inputs_schema["userFields"]["result"]
        == "${node_llm1.userFields.raw_output}"
    )
    # 无 COLLECT：set_end_comp 不因死掉的 stream schema 叠加 wait_for_all
    # （能力枚举 name 在不同引擎版本大小写不一，按大写比较）
    assert [a.name.upper() for a in end_spec.abilities] == ["INVOKE"]
    assert join_id not in graph.waits


def _collect_branch_targets(graph, branch_node_id: str) -> dict[str, list[str]]:
    """收集某分支节点 router 上各 branchId 的目标（duck-typing 访问内部 router）。"""
    targets: dict[str, list[str]] = {}
    for router_holder in graph.branches.get(branch_node_id, {}).values():
        router = getattr(router_holder, "condition", None)
        for branch in getattr(router, "_branches", None) or []:
            tgt = branch.target
            if isinstance(tgt, str):
                tgt = [tgt]
            targets[branch.branch_id] = list(tgt or [])
    return targets


# ---------------------------------------------------------------------------
# 引擎级验证：修复后的接线下，汇聚节点在 if/default 两种输入下均只执行一次
# ---------------------------------------------------------------------------


class _MiniBranch:
    """带 branch_id 的最小分支项，供编译期 _build_condition_targets 识别。"""

    def __init__(self, branch_id: str, cond, targets: list[str]):
        self.branch_id = branch_id
        self.cond = cond
        self.target = list(targets)


class _MiniRouter:
    def __init__(self, branches: list[_MiniBranch]):
        self._branches = branches

    def __call__(self, *args, **kwargs):
        for branch in self._branches:
            if branch.cond():
                return list(branch.target)
        raise RuntimeError("no branch matched")


EXEC_LOG: dict[str, list[int]] = defaultdict(list)


def _make_fn(name: str):
    async def fn(*args, **kwargs):
        EXEC_LOG[name].append(1)

    return fn


def _build_fixed_wiring_graph(query_nonempty: bool):
    """复刻修复后 converter 的接线（lane-done + 列表边 barrier，X 不标 wait_for_all）。"""
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["B2", "P", "Q", "LLM", "LLM1", "LLM2", "D1", "D2", "X", "MSG"]:
        g.add_node(node_id, object())  # X 不标 wait_for_all

    g.start_node("B2")

    def if_taken():
        return query_nonempty

    def default_taken():
        return not query_nonempty

    g.add_conditional_edges(
        "B2",
        _MiniRouter([
            _MiniBranch("B2-if", if_taken, ["P", "Q"]),
            _MiniBranch("B2-default", default_taken, ["P", "Q"]),
        ]),
    )
    g.register_branch_targets("B2", {"P", "Q"})

    g.add_conditional_edges(
        "P",
        _MiniRouter([
            _MiniBranch("P-if", if_taken, ["LLM"]),
            _MiniBranch("P-default", default_taken, ["D1"]),
        ]),
    )
    g.register_branch_targets("P", {"LLM", "D1"})

    g.add_conditional_edges(
        "Q",
        _MiniRouter([
            _MiniBranch("Q-if", if_taken, ["LLM1"]),
            _MiniBranch("Q-default", default_taken, ["D2"]),
        ]),
    )
    g.register_branch_targets("Q", {"LLM1", "D2"})

    for src, tgt in [("LLM", "D1"), ("LLM1", "LLM2"), ("LLM2", "D2"), ("X", "MSG")]:
        g.add_edge(src, tgt)
    g.add_edge(["D1", "D2"], "X")

    pregel = getattr(g, "_compile")()
    for node_name, pnode in pregel.nodes.items():
        pnode.func = _make_fn(node_name)
    return pregel


@pytest.fixture()
def _event_loop():
    """引擎级同步测试专用：Vertex 在构造期创建 asyncio.Future，需要可用的事件循环。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    asyncio.set_event_loop(None)
    loop.close()


@pytest.mark.parametrize("query_nonempty", [True, False])
def test_join_executes_once(query_nonempty, _event_loop):
    """if 路径（LLM 与 LLM2 不同超步到达）与 default 路径下，X/MSG 都只执行一次。

    该接线与修复后 converter 对 message/end join（schema 跨跳引用 node_llm1）
    的实际产出一致：barrier 仅由 lane-done [D1, D2] 组成，折叠引用源 LLM1
    不在其中——因此 default 路径（LLM1 永不执行）下 X 仍会被触发恰好一次；
    修复前 LLM1 被并入 barrier，default 路径下 X/MSG 全部静默不执行。
    """

    async def _run():
        pregel = _build_fixed_wiring_graph(query_nonempty)
        EXEC_LOG.clear()
        from openjiuwen.core.graph.pregel.config import PregelConfig

        await pregel.run(config=PregelConfig(session_id=None, ns=None))

    _event_loop.run_until_complete(_run())
    assert len(EXEC_LOG.get("X", [])) == 1, (
        f"汇聚代码节点应只执行 1 次，实际 {len(EXEC_LOG.get('X', []))} 次；"
        f"执行记录: { {k: len(v) for k, v in EXEC_LOG.items()} }"
    )
    assert len(EXEC_LOG.get("MSG", [])) == 1
    # 每个 lane-done 恰好触发一次（lane 内 if/default 出口互斥）
    assert len(EXEC_LOG.get("D1", [])) == 1
    assert len(EXEC_LOG.get("D2", [])) == 1


# ---------------------------------------------------------------------------
# 互斥双 fork 源共享汇聚点（线上 PMB-W-1 拓扑骨架）：
# 判断节点 neg 的 if 链上节点扇出（u1 波）与 default 锚点扇出（u2 波）
# 推导出 lane 结构完全相同、但 fork_source 不同的两套方案。修复前签名含
# fork_source 无法去重 → 多 spec 整体回退 wait_for_all → 分支路由边
#（TriggerMessage 直达）绕过 barrier，汇聚节点按到达波数重复执行。
# ---------------------------------------------------------------------------


def _build_exclusive_dual_fork_ir() -> dict:
    """PMB-W-1 骨架：neg-if→llm 扇出（u1）/ neg-default 锚点扇出（u2）共享 node_code。

    每条 lane 内 if 链 vs default 直达：P-if→pllm→code、Q-if→qllm→code。
    """
    comma = "u1,u2"
    components = [
        {
            "id": "node_start",
            "type": "jiuwen.start",
            "inputs": {
                "userFields": {},
                "systemFields": {"query": "", "sys": {}},
            },
            "configs": {"userFields": {"inputs": [], "outputs": []}},
        },
        {"id": "node_neg", "type": "jiuwen.branch", "configs": _branch_configs("node_neg-if")},
        {
            "id": "node_llm",
            "type": "jiuwen.llm",
            "configs": {"stream": False, "responseFormat": {"type": "text"}},
            "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
        },
        {"id": "node_p", "type": "jiuwen.branch", "configs": _branch_configs("node_p-if")},
        {"id": "node_q", "type": "jiuwen.branch", "configs": _branch_configs("node_q-if")},
        {
            "id": "node_pllm",
            "type": "jiuwen.llm",
            "configs": {"stream": False, "responseFormat": {"type": "text"}},
            "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
        },
        {
            "id": "node_qllm",
            "type": "jiuwen.llm",
            "configs": {"stream": False, "responseFormat": {"type": "text"}},
            "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
        },
        {
            "id": "node_code",
            "type": "jiuwen.code",
            "configs": {"code": "def main(args): return {'key0': 'x'}"},
            "inputs": {"userFields": {"test": "111"}},
        },
        {
            "id": "node_msg",
            "type": "jiuwen.message",
            "configs": {"template": "{{query}}"},
            "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
        },
        {
            "id": "node_end",
            "type": "jiuwen.end",
            "configs": {"responseTemplate": "{{result}}", "isStreamOut": False},
            "inputs": {"userFields": {"result": "${node_msg.result}"}},
        },
    ]
    connections = [
        _edge("node_start", "node_neg"),
        _edge("node_neg", "node_llm", branch_id="node_neg-if"),
        _edge("node_neg", "node_p", branch_id="node_neg-default", parallel_id="u2"),
        _edge("node_neg", "node_q", branch_id="node_neg-default", parallel_id="u2"),
        _edge("node_llm", "node_p", parallel_id="u1"),
        _edge("node_llm", "node_q", parallel_id="u1"),
        _edge("node_p", "node_pllm", branch_id="node_p-if"),
        _edge("node_p", "node_code", branch_id="node_p-default", target_parallel_id=comma),
        _edge("node_q", "node_qllm", branch_id="node_q-if"),
        _edge("node_q", "node_code", branch_id="node_q-default", target_parallel_id=comma),
        _edge("node_pllm", "node_code", target_parallel_id=comma),
        _edge("node_qllm", "node_code", target_parallel_id=comma),
        _edge("node_code", "node_msg"),
        _edge("node_msg", "node_end"),
    ]
    return {"components": components, "connections": connections}


@pytest.mark.asyncio
async def test_exclusive_dual_fork_join_managed_by_lanes():
    """互斥双 fork 源合并为单 spec：done 去重、分支目标改写、不标 wait_for_all。"""
    workflow = await _build_workflow(_build_exclusive_dual_fork_ir())
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    # u1/u2 两套方案合并：仅一套（2 个）lane-done，且以首个 parallel id（u1）命名
    done_ids = sorted(
        comp_id
        for comp_id in spec.comp_configs
        if comp_id.startswith("_parallel_done__") and "__node_code__" in comp_id
    )
    assert len(done_ids) == 2, f"应恰好 2 个 lane-done，实际 {done_ids}"
    done_p = "_parallel_done__u1__node_code__node_p"
    done_q = "_parallel_done__u1__node_code__node_q"
    assert done_ids == sorted([done_p, done_q])

    # join 入边全部改写到所属 lane 的 done；done 列表以 barrier 汇入代码节点
    assert (spec.edges.get("node_pllm") or []) == [done_p]
    assert (spec.edges.get("node_qllm") or []) == [done_q]
    assert (spec.edges.get(done_p) or []) == ["node_code"]
    assert (spec.edges.get(done_q) or []) == ["node_code"]
    # fork 锚点分支（neg-default）直达 lane 头；lane 内分支边（p/q-default）改写为 done
    branch_targets = _collect_branch_targets(graph, "node_neg")
    assert sorted(branch_targets.get("node_neg-default") or []) == ["node_p", "node_q"]
    assert branch_targets.get("node_neg-if") == ["node_llm"]
    branch_targets_p = _collect_branch_targets(graph, "node_p")
    assert branch_targets_p.get("node_p-default") == [done_p]
    branch_targets_q = _collect_branch_targets(graph, "node_q")
    assert branch_targets_q.get("node_q-default") == [done_q]
    # 汇聚点不叠加 wait_for_all（lane 完整覆盖，绕开会误分组的 CNF resolver）
    assert "node_code" not in graph.waits


def _build_dual_fork_wiring_graph(neg_if: bool):
    """复刻修复后 converter 对互斥双 fork 源拓扑的实际接线。

    neg=if → LLM 扇出 P/Q；neg=default → 锚点直接扇出 P/Q。两种取向下
    X 都只能执行一次；修复前（wait_for_all 回退 + 分支 Trigger 直达）
    neg=default 时 P/Q 的 default 边直达 X，X 执行 2 次。
    """
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["NEG", "LLM", "P", "Q", "LLM1", "LLM2", "D1", "D2", "X", "MSG"]:
        g.add_node(node_id, object())  # X 不标 wait_for_all

    g.start_node("NEG")

    def if_taken():
        return neg_if

    def default_taken():
        return not neg_if

    g.add_conditional_edges(
        "NEG",
        _MiniRouter([
            _MiniBranch("NEG-if", if_taken, ["LLM"]),
            _MiniBranch("NEG-default", default_taken, ["P", "Q"]),
        ]),
    )
    g.register_branch_targets("NEG", {"LLM", "P", "Q"})

    g.add_conditional_edges(
        "P",
        _MiniRouter([
            _MiniBranch("P-if", if_taken, ["LLM1"]),
            _MiniBranch("P-default", default_taken, ["D1"]),
        ]),
    )
    g.register_branch_targets("P", {"LLM1", "D1"})

    g.add_conditional_edges(
        "Q",
        _MiniRouter([
            _MiniBranch("Q-if", if_taken, ["LLM2"]),
            _MiniBranch("Q-default", default_taken, ["D2"]),
        ]),
    )
    g.register_branch_targets("Q", {"LLM2", "D2"})

    # LLM 扇出普通边；lane 内链边全部改写汇入各自 done
    for src, tgt in [("LLM", "P"), ("LLM", "Q"),
                     ("LLM1", "D1"), ("LLM2", "D2"), ("X", "MSG")]:
        g.add_edge(src, tgt)
    g.add_edge(["D1", "D2"], "X")

    pregel = getattr(g, "_compile")()
    for node_name, pnode in pregel.nodes.items():
        pnode.func = _make_fn(node_name)
    return pregel


@pytest.mark.parametrize("neg_if", [True, False])
def test_dual_fork_join_executes_once(neg_if, _event_loop):
    """neg 走 if（LLM 链扇出）与 default（锚点直扇出）两种取向下 X/MSG 只执行一次。"""

    async def _run():
        pregel = _build_dual_fork_wiring_graph(neg_if)
        EXEC_LOG.clear()
        from openjiuwen.core.graph.pregel.config import PregelConfig

        await pregel.run(config=PregelConfig(session_id=None, ns=None))

    _event_loop.run_until_complete(_run())
    assert len(EXEC_LOG.get("X", [])) == 1, (
        f"汇聚代码节点应只执行 1 次，实际 {len(EXEC_LOG.get('X', []))} 次；"
        f"执行记录: { {k: len(v) for k, v in EXEC_LOG.items()} }"
    )
    assert len(EXEC_LOG.get("MSG", [])) == 1
    assert len(EXEC_LOG.get("D1", [])) == 1
    assert len(EXEC_LOG.get("D2", [])) == 1


# ---------------------------------------------------------------------------
# 互斥分支下 Message 混合引用 start 字段（线上『判断-消息』58ec2759 拓扑）：
# start → 判断；if → end；default → LLM(stream) → 消息 → end。
# 消息同时引用 LLM 流式输出（sd）与 start.query（批量源）。修复前 schema
# 自动补边给出 start → 消息 的批量直达边（独立触发边）：if 命中时 LLM 不执行，
# 消息仍被 INVOKE 触发且无流数据可收，抛 GRAPH_VERTEX_STREAM_CALL_ERROR
#（"no stream data in"）。修复后：目标已有触发入边时不再补批量直达边。
# ---------------------------------------------------------------------------


def _build_branch_message_ir() -> dict:
    """『判断-消息』拓扑：消息混合引用流式 LLM 输出与 start.query。"""
    components = [
        {
            "id": "node_start",
            "type": "jiuwen.start",
            "inputs": {
                "userFields": {},
                "systemFields": {"query": "", "sys": {}},
            },
            "configs": {"userFields": {"inputs": [], "outputs": []}},
        },
        {"id": "node_br", "type": "jiuwen.branch", "configs": _branch_configs("node_br-if")},
        {
            "id": "node_llm",
            "type": "jiuwen.llm",
            "configs": {"stream": True, "responseFormat": {"type": "text"}},
            "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
        },
        {
            "id": "node_msg",
            "type": "jiuwen.message",
            "configs": {"template": "1221 {{sd}}"},
            "inputs": {
                "userFields": {
                    "sd": "${node_llm.userFields.raw_output}",
                    "query": "${node_start.systemFields.query}",
                }
            },
        },
        {
            "id": "node_end",
            "type": "jiuwen.end",
            "configs": {"responseTemplate": "{{result}}", "isStreamOut": False},
            "inputs": {"userFields": {"result": "${node_msg.result}"}},
        },
    ]
    connections = [
        _edge("node_start", "node_br"),
        _edge("node_br", "node_end", branch_id="node_br-if"),
        _edge("node_br", "node_llm", branch_id="node_br-default"),
        _edge("node_llm", "node_msg"),
        _edge("node_msg", "node_end"),
    ]
    return {"components": components, "connections": connections}


@pytest.mark.asyncio
async def test_mixed_ref_message_not_pulled_by_auto_batch_edge():
    """混合引用的消息节点：不再补 start → 消息 批量直达边，流式投递与分支路由不变。"""
    workflow = await _build_workflow(_build_branch_message_ir())
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    # 修复核心：不补出 start → 消息 的独立触发边
    assert "node_msg" not in (spec.edges.get("node_start") or [])
    assert ("node_start", "node_msg") not in graph.edges
    # 消息仍由 LLM 的流式边投递（COLLECT 路径）
    assert "node_msg" in (spec.stream_edges.get("node_llm") or [])
    # 分支路由不受影响：if → end，default → LLM
    targets = _collect_branch_targets(graph, "node_br")
    assert targets.get("node_br-if") == ["node_end"]
    assert targets.get("node_br-default") == ["node_llm"]
    # 消息 → end 的原有边保持
    assert "node_end" in (spec.edges.get("node_msg") or [])


@pytest.mark.asyncio
async def test_auto_batch_edge_kept_for_end_mixed_ref():
    """守卫不扩大化：End（wait_for_all barrier，非流式消费注册）混合引用时补边保留。"""
    ir = _build_branch_message_ir()
    # End 同时引用流式 LLM 输出与 start.query（batch 源）
    end_node = next(c for c in ir["components"] if c["id"] == "node_end")
    end_node["inputs"] = {
        "userFields": {
            "result": "${node_llm.userFields.raw_output}",
            "q": "${node_start.systemFields.query}",
        }
    }
    workflow = await _build_workflow(ir)
    internal = _get_internal(workflow)
    spec = internal.config().spec

    # End 不在 stream_input_target_ids（isStreamOut=False），
    # start → end 的 batch 补边保留（barrier 场景行为不变）
    assert "node_end" in (spec.edges.get("node_start") or [])
    # 修复核心同时成立：消息不被补独立触发边
    assert "node_msg" not in (spec.edges.get("node_start") or [])


# ---------------------------------------------------------------------------
# 嵌套菱形（死锁 + 重复执行）：外层判定 B 的 if 臂内并行 fork P/Q（单波）
# 汇聚 X，B 的 default 臂经 DD 直达 X。converter 对这种「单波 + 互斥直达
# 前驱」汇聚点保留 wait_for_all，接线为 DD→X 直达 + [D1,D2]→X 列表边。
# 既有 co-exec/latch resolver 会把 {D1,D2,DD} 误并成单个 OR 组：query 非空
# 时 D1、D2 各触发一次 X（X=2 重复执行）；嵌套菱形特化按路径签名展开为
# [{D1,DD},{D2,DD}]：
#   - if 路径：两个 OR 组各由 D1、D2 满足（DD 不执行）→ X 恰好 1 次；
#   - default 路径：两个 OR 组都由 DD 满足 → X 恰好 1 次。
# ---------------------------------------------------------------------------


def _build_nested_diamond_graph(query_nonempty: bool):
    """复刻 converter 对嵌套菱形的接线：X 保留 wait_for_all + DD 直达 + 列表边。"""
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["B", "P", "Q", "LLM", "LLM1", "LLM2", "D1", "D2", "DD", "X", "MSG"]:
        g.add_node(node_id, object(), wait_for_all=(node_id == "X"))

    g.start_node("B")

    def if_taken():
        return query_nonempty

    def default_taken():
        return not query_nonempty

    g.add_conditional_edges(
        "B",
        _MiniRouter([
            _MiniBranch("B-if", if_taken, ["P", "Q"]),
            _MiniBranch("B-default", default_taken, ["DD"]),
        ]),
    )
    g.register_branch_targets("B", {"P", "Q", "DD"})

    g.add_conditional_edges(
        "P",
        _MiniRouter([
            _MiniBranch("P-if", if_taken, ["LLM"]),
            _MiniBranch("P-default", default_taken, ["D1"]),
        ]),
    )
    g.register_branch_targets("P", {"LLM", "D1"})

    g.add_conditional_edges(
        "Q",
        _MiniRouter([
            _MiniBranch("Q-if", if_taken, ["LLM1"]),
            _MiniBranch("Q-default", default_taken, ["D2"]),
        ]),
    )
    g.register_branch_targets("Q", {"LLM1", "D2"})

    for src, tgt in [
        ("LLM", "D1"),
        ("LLM1", "LLM2"),
        ("LLM2", "D2"),
        ("DD", "X"),
        ("X", "MSG"),
    ]:
        g.add_edge(src, tgt)
    g.add_edge(["D1", "D2"], "X")
    return g


def test_nested_diamond_barrier_groups_are_cnf_paired(_event_loop):
    """CNF 分组：外层 default 直达前驱 DD 与外层 if 臂内两条 lane done 配对。"""
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入

    g = _build_nested_diamond_graph(True)
    # 白盒验证引擎私有 CNF 屏障分组算法本身，需直调其内部方法
    groups = g._resolve_barrier_groups(  # pylint: disable=protected-access
        "X", [{"D1"}, {"D2"}, {"DD"}]
    )
    assert {frozenset(grp) for grp in groups} == {
        frozenset({"D1", "DD"}),
        frozenset({"D2", "DD"}),
    }, groups


@pytest.mark.parametrize("query_nonempty", [True, False])
def test_nested_diamond_join_executes_once(query_nonempty, _event_loop):
    """if 路径（内层并行两 lane）与 default 路径（DD 直达）下 X/MSG 都只执行一次。"""

    async def _run():
        g = _build_nested_diamond_graph(query_nonempty)
        pregel = getattr(g, "_compile")()
        for node_name, pnode in pregel.nodes.items():
            pnode.func = _make_fn(node_name)
        EXEC_LOG.clear()
        from openjiuwen.core.graph.pregel.config import PregelConfig

        await pregel.run(config=PregelConfig(session_id=None, ns=None))

    _event_loop.run_until_complete(asyncio.wait_for(_run(), timeout=15))
    assert len(EXEC_LOG.get("X", [])) == 1, (
        f"嵌套菱形汇聚节点应只执行 1 次，实际 {len(EXEC_LOG.get('X', []))} 次；"
        f"执行记录: { {k: len(v) for k, v in EXEC_LOG.items()} }"
    )
    assert len(EXEC_LOG.get("MSG", [])) == 1
    if query_nonempty:
        # if 路径：内层并行两 lane 各完成一次，default 直达 DD 不执行
        assert len(EXEC_LOG.get("D1", [])) == 1
        assert len(EXEC_LOG.get("D2", [])) == 1
        assert len(EXEC_LOG.get("DD", [])) == 0
    else:
        # default 路径：仅 DD 执行，内层两 lane 不执行
        assert len(EXEC_LOG.get("DD", [])) == 1
        assert len(EXEC_LOG.get("D1", [])) == 0
        assert len(EXEC_LOG.get("D2", [])) == 0


# ---------------------------------------------------------------------------
# 跨分支 lane 复用死锁（线上『理财推荐1030』工作流，trace 9df83bc3）：
#   外层判断 B：if → 内层判断 I；elseIf-1 → end；default → 并行扇出 M0/M1
#   内层判断 I：if → M1；elseIf-1 → M0；default → end
#   M0 → VA → Code；M1 → VB → Code；Code 汇聚 [done_M0, done_M1] 硬 AND。
# B.default 时两条 lane 都活，AND 正常；但 B.if→I.if 只活 M1（done_M0 永不
# 触发）、B.if→I.elseIf-1 只活 M0（done_M1 永不触发）→ Code 永久等待、0 次
# 执行，工作流在无报错的情况下提前结束。
# 修复：dead-lane skip 哨兵给「只激活严格子集 lane 的互斥分支臂」各补一个
# no-op 节点，与该臂真实目标合并进同一次 add_branch，skip → 死掉 lane 的
# done 标记，使 AND barrier 在该臂上也能恰好完成一次。
# ---------------------------------------------------------------------------

_B = "node_1793339784253"
_I = "node_1793339959077"
_M0 = "node_1793340512826"  # Message
_M1 = "node_1793340484999"  # Message
_VA = "node_1793340588854"  # SetVariable（M0 lane）
_VB = "node_1793340680767"  # SetVariable（M1 lane）
_CODE = "node_1793340726610"
_PID = "wf"


def _par_edge(src, dst, *, branch=None, sfork=None, tjoin=None):
    source = {"componentId": src}
    if branch is not None:
        source["branchId"] = branch
    if sfork is not None:
        source["parallelBranchId"] = sfork
    target = {"componentId": dst}
    if tjoin is not None:
        target["parallelBranchId"] = tjoin
    return {"source": source, "target": target}


def _branch_cfg(*conds):
    branches = [{"boolExpression": expr, "id": bid} for bid, expr in conds]
    branches.append({"id": "default"})
    return {"branches": branches}


def _build_cross_branch_lane_reuse_ir() -> dict:
    """复刻理财推荐1030：外层 B(if/elseIf/default) 嵌套内层 I(if/elseIf/default)，
    I 的 if/elseIf 各复用外层 default 并行 fork 两条 lane 中的一条。"""
    components = [
        {
            "id": "node_start",
            "type": "jiuwen.start",
            "inputs": {
                "userFields": {},
                "systemFields": {"type": 0, "llm": "", "query": "", "sys": {}},
            },
            "configs": {"userFields": {"inputs": [], "outputs": []}},
        },
        {
            "id": _B,
            "type": "jiuwen.branch",
            "configs": _branch_cfg(
                (_B + "-if", "(${node_start.systemFields.type} != 0)"),
                (_B + "-elseIf-1", "(${node_start.systemFields.type} == 99)"),
            ),
        },
        {
            "id": _I,
            "type": "jiuwen.branch",
            "configs": _branch_cfg(
                (_I + "-if", "(${node_start.systemFields.type} == 1)"),
                (_I + "-elseIf-1", "(${node_start.systemFields.type} == 2)"),
            ),
        },
        {
            "id": _M0,
            "type": "jiuwen.message",
            "configs": {"template": "m0"},
            "inputs": {"userFields": {"res": "${node_start.systemFields.query}"}},
        },
        {
            "id": _M1,
            "type": "jiuwen.message",
            "configs": {"template": "m1"},
            "inputs": {"userFields": {"res": "${node_start.systemFields.query}"}},
        },
        {
            "id": _VA,
            "type": "jiuwen.setVariable",
            "configs": {"settings": []},
            "inputs": {"userFields": {}},
        },
        {
            "id": _VB,
            "type": "jiuwen.setVariable",
            "configs": {"settings": []},
            "inputs": {"userFields": {}},
        },
        {
            "id": _CODE,
            "type": "jiuwen.code",
            "configs": {"code": "def main(args): return {'aa': 'x'}"},
            "inputs": {"userFields": {"aa": "${node_start.systemFields.query}"}},
        },
        {
            "id": "node_end",
            "type": "jiuwen.end",
            "configs": {"responseTemplate": "{{result}}", "isStreamOut": False},
            "inputs": {"userFields": {"result": "${" + _CODE + ".aa}"}},
        },
    ]
    connections = [
        _par_edge("node_start", _B),
        _par_edge(_B, _I, branch=_B + "-if"),
        _par_edge(_B, "node_end", branch=_B + "-elseIf-1"),
        # 外层 default 锚点并行扇出两条 lane（fork 侧标记）
        _par_edge(_B, _M0, branch=_B + "-default", sfork=_PID),
        _par_edge(_B, _M1, branch=_B + "-default", sfork=_PID),
        # 内层 if/elseIf 各只进入一条 lane（跨分支复用单 lane）
        _par_edge(_I, _M1, branch=_I + "-if"),
        _par_edge(_I, _M0, branch=_I + "-elseIf-1"),
        _par_edge(_I, "node_end", branch=_I + "-default"),
        _par_edge(_M0, _VA),
        _par_edge(_M1, _VB),
        # 汇聚点 Code 的两条 lane 入边（join 侧标记）
        _par_edge(_VA, _CODE, tjoin=_PID),
        _par_edge(_VB, _CODE, tjoin=_PID),
        _par_edge(_CODE, "node_end"),
    ]
    return {"components": components, "connections": connections}


def test_dead_lane_skip_plan_targets_only_inner_single_lane_arms():
    """纯分析器：仅内层 I 的 if/elseIf 单 lane 臂补 skip；外层 default 双 lane 不补。"""
    ir = _build_cross_branch_lane_reuse_ir()
    plan = build_parallel_join_plan(ir["connections"])
    assert (_PID, _CODE) in plan.joins

    skip_plan = build_dead_lane_skip_plan(ir["connections"], plan)
    by_branch = {(s.branch_node, s.branch_id): s for s in skip_plan.skips}
    assert set(by_branch) == {(_I, _I + "-if"), (_I, _I + "-elseIf-1")}

    done_m0 = f"_parallel_done__{_PID}__{_CODE}__{_M0}"
    done_m1 = f"_parallel_done__{_PID}__{_CODE}__{_M1}"
    # I.if 只走 M1 → 死掉的是 M0 lane，skip 补 done_M0
    assert by_branch[(_I, _I + "-if")].done_node == done_m0
    # I.elseIf-1 只走 M0 → 死掉的是 M1 lane，skip 补 done_M1
    assert by_branch[(_I, _I + "-elseIf-1")].done_node == done_m1
    # 外层 default 同时激活两条 lane，绝不补偿
    assert all(s.branch_node == _I for s in skip_plan.skips)


async def _build_cross_branch_workflow(ir: dict):
    original_create = getattr(IRConverter, "_create_component")

    async def _mock_create(node, global_model, *, node_by_id=None, ir_connections=None):
        if node.get("type") in ("jiuwen.message", "jiuwen.setVariable"):
            return _NoopComp(), node["type"], dict(node.get("configs") or {})
        return await original_create(
            node, global_model, node_by_id=node_by_id, ir_connections=ir_connections
        )

    with patch.object(IRConverter, "_create_component", side_effect=_mock_create):
        lazy = await IRConverter.async_ir_to_workflow(ir)
        return await lazy.instantiate()


class _NoopComp(WorkflowComponent):
    async def invoke(self, inputs, session, context):
        return {}


@pytest.mark.asyncio
async def test_converter_wires_dead_lane_skips_into_inner_arms():
    """转换器：skip 注册为合法组件、并入内层分支臂、skip→done，Code 由双 done 列表 barrier 接管且不标 wait_for_all。"""
    workflow = await _build_cross_branch_workflow(_build_cross_branch_lane_reuse_ir())
    internal = _get_internal(workflow)
    spec = internal.config().spec
    graph = _get_graph(internal)

    done_m0 = f"_parallel_done__{_PID}__{_CODE}__{_M0}"
    done_m1 = f"_parallel_done__{_PID}__{_CODE}__{_M1}"
    assert done_m0 in spec.comp_configs and done_m1 in spec.comp_configs

    skip_ids = sorted(c for c in spec.comp_configs if c.startswith("_lane_skip__"))
    assert len(skip_ids) == 2, skip_ids
    # 真实节点 id 很长：skip 节点名必须满足引擎 [1,100] 长度与字符集约束
    for skip_id in skip_ids:
        assert 1 <= len(skip_id) <= 100, skip_id

    # skip → 对应死 lane 的 done
    skip_to_done = {sid: (spec.edges.get(sid) or [None])[0] for sid in skip_ids}
    skip_for_m0 = {sid for sid, d in skip_to_done.items() if d == done_m0}
    skip_for_m1 = {sid for sid, d in skip_to_done.items() if d == done_m1}
    assert len(skip_for_m0) == 1 and len(skip_for_m1) == 1

    # skip 与真实目标合并进同一次分支路由：I.if=[M1, skip死M0]，
    # I.elseIf-1=[M0, skip死M1]
    targets = _collect_branch_targets(graph, _I)
    assert set(targets[_I + "-if"]) == {_M1} | skip_for_m0
    assert set(targets[_I + "-elseIf-1"]) == {_M0} | skip_for_m1
    # 内层 default 与外层各臂不被注入 skip
    assert targets[_I + "-default"] == ["node_end"]
    outer = _collect_branch_targets(graph, _B)
    assert set(outer[_B + "-default"]) == {_M0, _M1}
    assert outer[_B + "-if"] == [_I]
    assert outer[_B + "-elseIf-1"] == ["node_end"]

    # Code 由唯一一条 [done_M0, done_M1] 列表边 barrier 接管，不标 wait_for_all
    assert _CODE not in graph.waits
    into_code = [edge for edge in graph.edges if edge[1] == _CODE]
    barriers = [edge for edge in into_code if isinstance(edge[0], list)]
    assert len(barriers) == 1, into_code
    assert set(barriers[0][0]) == {done_m0, done_m1}


def _build_cross_branch_wiring_graph(type_val: int):
    """复刻转换器对跨分支 lane 复用拓扑的实际接线（含 skip 哨兵）。"""
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    nodes = [
        "B", "I", "M0", "M1", "VA", "VB", "S_IF", "S_ELIF",
        "D0", "D1", "CODE", "END",
    ]
    for node_id in nodes:
        g.add_node(node_id, object())  # CODE 不标 wait_for_all（lane 接管）
    g.start_node("B")

    def b_if():
        # 进内层 I 的取向（type=1/2）；与 elif/default 互斥，保证三臂都可独立覆盖
        return type_val in (1, 2)

    def b_elif():
        return type_val == 99

    def i_if():
        return type_val == 1

    def i_elif():
        return type_val == 2

    g.add_conditional_edges(
        "B",
        _MiniRouter([
            _MiniBranch("B-if", b_if, ["I"]),
            _MiniBranch("B-elseIf-1", b_elif, ["END"]),
            _MiniBranch("B-default", lambda: True, ["M0", "M1"]),
        ]),
    )
    g.register_branch_targets("B", {"I", "END", "M0", "M1"})

    g.add_conditional_edges(
        "I",
        _MiniRouter([
            # 真实活 lane M1 + skip 哨兵补偿死 lane M0 的 done
            _MiniBranch("I-if", i_if, ["M1", "S_IF"]),
            # 真实活 lane M0 + skip 哨兵补偿死 lane M1 的 done
            _MiniBranch("I-elseIf-1", i_elif, ["M0", "S_ELIF"]),
            _MiniBranch("I-default", lambda: True, ["END"]),
        ]),
    )
    g.register_branch_targets("I", {"M1", "M0", "S_IF", "S_ELIF", "END"})

    for src, tgt in [
        ("M0", "VA"), ("VA", "D0"),
        ("M1", "VB"), ("VB", "D1"),
        ("S_IF", "D0"), ("S_ELIF", "D1"),
        ("CODE", "END"),
    ]:
        g.add_edge(src, tgt)
    g.add_edge(["D0", "D1"], "CODE")
    return g


@pytest.mark.parametrize(
    "type_val,expect",
    [
        # B.if → I.if：仅 M1 lane 真跑，S_IF 补偿死 lane M0
        (1, {"live_real": "M1", "skip": "S_IF", "idle_skip": "S_ELIF"}),
        # B.if → I.elseIf-1：仅 M0 lane 真跑，S_ELIF 补偿死 lane M1
        (2, {"live_real": "M0", "skip": "S_ELIF", "idle_skip": "S_IF"}),
        # B.default：两 lane 并行真跑，无任何 skip
        (0, {"live_real": "BOTH", "skip": None, "idle_skip": None}),
    ],
)
def test_cross_branch_lane_reuse_code_executes_once(type_val, expect, _event_loop):
    """三种取向下 Code/End 都恰好执行一次（修复前 1/2 取向 Code 永久 0 次死锁）。"""

    async def _run():
        g = _build_cross_branch_wiring_graph(type_val)
        pregel = getattr(g, "_compile")()
        for node_name, pnode in pregel.nodes.items():
            pnode.func = _make_fn(node_name)
        EXEC_LOG.clear()
        from openjiuwen.core.graph.pregel.config import PregelConfig

        await pregel.run(config=PregelConfig(session_id=None, ns=None))

    _event_loop.run_until_complete(asyncio.wait_for(_run(), timeout=15))
    assert len(EXEC_LOG.get("CODE", [])) == 1, (
        f"汇聚 Code 应只执行 1 次（type={type_val}），实际 "
        f"{len(EXEC_LOG.get('CODE', []))}；记录: "
        f"{ {k: len(v) for k, v in EXEC_LOG.items()} }"
    )
    assert len(EXEC_LOG.get("END", [])) == 1
    # 每个 lane-done 在每种取向下都恰好满足一次（真 terminal 或 skip 二选一）
    assert len(EXEC_LOG.get("D0", [])) == 1
    assert len(EXEC_LOG.get("D1", [])) == 1

    if expect["live_real"] == "M1":
        assert len(EXEC_LOG.get("VB", [])) == 1
        assert len(EXEC_LOG.get("VA", [])) == 0
    elif expect["live_real"] == "M0":
        assert len(EXEC_LOG.get("VA", [])) == 1
        assert len(EXEC_LOG.get("VB", [])) == 0
    else:
        assert len(EXEC_LOG.get("VA", [])) == 1
        assert len(EXEC_LOG.get("VB", [])) == 1

    if expect["skip"]:
        assert len(EXEC_LOG.get(expect["skip"], [])) == 1
    if expect["idle_skip"]:
        assert len(EXEC_LOG.get(expect["idle_skip"], [])) == 0
    if expect["live_real"] == "BOTH":
        assert len(EXEC_LOG.get("S_IF", [])) == 0
        assert len(EXEC_LOG.get("S_ELIF", [])) == 0


def test_outer_elif_arm_skips_join_without_deadlock(_event_loop):
    """B.elseIf-1 直达 end：不进并行区，Code 不执行也不死锁，End 正常完成。"""

    async def _run():
        g = _build_cross_branch_wiring_graph(99)
        pregel = getattr(g, "_compile")()
        for node_name, pnode in pregel.nodes.items():
            pnode.func = _make_fn(node_name)
        EXEC_LOG.clear()
        from openjiuwen.core.graph.pregel.config import PregelConfig

        await pregel.run(config=PregelConfig(session_id=None, ns=None))

    _event_loop.run_until_complete(asyncio.wait_for(_run(), timeout=15))
    assert len(EXEC_LOG.get("CODE", [])) == 0
    assert len(EXEC_LOG.get("END", [])) == 1


# ===========================================================================
# MR !2569 评审反例（已全部修复，现为正常回归用例，直接通过、无 xfail 标记）
#
# 下列拓扑来自评审意见，用于把「守卫过宽 / 补偿遗漏」固化为回归断言：
# 1) 条件4 无法排除「同一外层臂内层分叉」（ir13）；
# 2) shared 只在签名为空集时识别，漏掉「汇合后共行前驱」；
# 3) build_dead_lane_skip_plan 整体跳过 fork_source，漏掉同源单 lane 臂；
# 4) 根级 build_dead_lane_skip_plan 未排除 loop body，skip 泄漏到根 workflow。
# ===========================================================================


def _norm_groups(groups) -> list[list[str]]:
    """把 barrier 分组（list[set]）规范化为可比较的有序结构。"""
    return sorted(sorted(g) for g in groups)


def _resolve_barrier_groups(graph, target, preds):
    # 使用 getattr 访问受保护方法，避免静态检测 G.CLS.11
    return getattr(graph, "_resolve_barrier_groups")(target, preds)


def _build_same_arm_inner_fork_graph():
    """ir13：同一外层 B.default 臂内既扇出内层判断 I(if/else)，又并行 fork E1/E2。

    start→B；B.if 走无关节点 JNK；B.default 同时到 [I, E1, E2]；
    I.if→D1 / I.else→D2。D1/D2（内层互斥两臂终端）与 E1/E2（并行双 lane）
    一并汇入 wait_for_all 的 X。

    正确语义：这四个前驱同属 B.default 这一条激活路径，D1/D2 由内层 I 二选一，
    X 必须等待「D1 或 D2」且 E1 且 E2 —— 即整体 AND（base 单组），绝不能把
    内层互斥桶与并行桶做笛卡尔配对。
    """
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["B", "JNK", "I", "D1", "D2", "E1", "E2", "X"]:
        g.add_node(node_id, object(), wait_for_all=(node_id == "X"))
    g.start_node("B")
    t = True
    g.add_conditional_edges("B", _MiniRouter([
        _MiniBranch("B-if", lambda: not t, ["JNK"]),
        _MiniBranch("B-default", lambda: t, ["I", "E1", "E2"]),
    ]))
    g.register_branch_targets("B", {"JNK", "I", "E1", "E2"})
    g.add_conditional_edges("I", _MiniRouter([
        _MiniBranch("I-if", lambda: t, ["D1"]),
        _MiniBranch("I-else", lambda: not t, ["D2"]),
    ]))
    g.register_branch_targets("I", {"D1", "D2"})
    for pred in ["D1", "D2", "E1", "E2"]:
        g.add_edge(pred, "X")
    return g, "X", ["D1", "D2", "E1", "E2"]


def _build_merged_coexec_graph():
    """汇合后共行前驱：X.if/default 先汇合到 Y（共行节点，两臂都可达），
    Y 再分叉 if→S / default→U；同时 X.if 另有并行 T1/T2 汇入 J。

    S、U 都能从 X 两臂到达（经汇合点 Y），属于「汇合后共行前驱」：
    它们虽在 Y 上互斥，但应被识别为 shared（对 X 而言两臂都可达），
    从而整体退回 AND，而不是被当成互斥 route 参与笛卡尔配对。
    """
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["X", "Y", "S", "U", "T1", "T2", "J"]:
        g.add_node(node_id, object(), wait_for_all=(node_id == "J"))
    g.start_node("X")
    t = True
    # X.if -> [Y, T1, T2]（if 臂既去汇合点 Y，又并行扇出 T1/T2）
    # X.default -> Y（default 臂只去 Y）
    g.add_conditional_edges("X", _MiniRouter([
        _MiniBranch("X-if", lambda: t, ["Y", "T1", "T2"]),
        _MiniBranch("X-default", lambda: not t, ["Y"]),
    ]))
    g.register_branch_targets("X", {"Y", "T1", "T2"})
    # 汇合点 Y 再分叉：if->S，default->U
    g.add_conditional_edges("Y", _MiniRouter([
        _MiniBranch("Y-if", lambda: t, ["S"]),
        _MiniBranch("Y-default", lambda: not t, ["U"]),
    ]))
    g.register_branch_targets("Y", {"S", "U"})
    for pred in ["S", "U", "T1", "T2"]:
        g.add_edge(pred, "J")
    return g, "J", ["S", "U", "T1", "T2"]


def test_same_arm_inner_fork_should_keep_single_and_group(_event_loop):
    g, target, preds = _build_same_arm_inner_fork_graph()
    # 正确：四个前驱在同一条 default 激活路径上，只能是单个 AND 组
    groups = _resolve_barrier_groups(g, target, [{p} for p in preds])
    assert _norm_groups(groups) == [["D1", "D2", "E1", "E2"]]


def _build_three_routes_sharing_outer_arm_graph():
    """评审 High 场景：外层 B 的 if 臂内**既有**并行 fork（lane 终端 D1/D2），
    **又有**内层判断 I 产生另一条子路由（I.if→E）；B.default 臂直达 DD。
    D1/D2/E/DD 一并汇入 wait_for_all 的 X。

    关键：这是 3 条路由，但在外层锚点 B 上只有 if / default 两个臂——D1/D2
    桶与 E 桶共享 B-if 臂，它们同属一次激活路径、并不互斥。若仅按
    ``len(arms) >= 2`` 就做全笛卡尔积，E 与 D1/D2 会被误当互斥析取项，内层
    臂上部分前驱到达即提前满足全部 CNF 组。正确行为是回退 base 的单 AND 组。
    """
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["B", "P", "Q", "I", "IE", "D1", "D2", "E", "DD", "X"]:
        g.add_node(node_id, object(), wait_for_all=(node_id == "X"))
    g.start_node("B")
    t = True
    # B.if 臂内：并行节点 P/Q（各自到 lane 终端 D1/D2）+ 内层判断 I
    g.add_conditional_edges("B", _MiniRouter([
        _MiniBranch("B-if", lambda: t, ["P", "Q", "I"]),
        _MiniBranch("B-default", lambda: not t, ["DD"]),
    ]))
    g.register_branch_targets("B", {"P", "Q", "I", "DD"})
    # 内层判断 I：if 臂产生子路由终端 E；else 臂到不汇聚 X 的 IE
    g.add_conditional_edges("I", _MiniRouter([
        _MiniBranch("I-if", lambda: t, ["E"]),
        _MiniBranch("I-else", lambda: not t, ["IE"]),
    ]))
    g.register_branch_targets("I", {"E", "IE"})
    g.add_edge("P", "D1")
    g.add_edge("Q", "D2")
    for pred in ["D1", "D2", "E", "DD"]:
        g.add_edge(pred, "X")
    return g, "X", ["D1", "D2", "E", "DD"]


def test_three_routes_sharing_outer_arm_must_not_cross_pair(_event_loop):
    g, target, preds = _build_three_routes_sharing_outer_arm_graph()
    groups = _resolve_barrier_groups(g, target, [{p} for p in preds])
    normed = _norm_groups(groups)
    # 共享 B-if 臂的 D1/D2 桶与 E 桶不互斥，绝不能展开成多组笛卡尔配对；
    # 必须回退为覆盖全部前驱的单个 AND（wait_for_all）组。
    assert normed == [["D1", "D2", "DD", "E"]], normed


def test_merged_coexec_preds_should_be_treated_as_shared(_event_loop):
    g, target, preds = _build_merged_coexec_graph()
    groups = _resolve_barrier_groups(g, target, [{p} for p in preds])
    # 正确：S/U 是汇合后共行前驱，整体退回单个 AND 组
    assert _norm_groups(groups) == [["S", "T1", "T2", "U"]]


def test_fork_source_single_lane_arm_still_gets_skip():
    """fork_source 自己的单 lane 臂也需补 skip（全 lane 臂由 live==lane_starts 自然排除）。"""
    pid = "wf"
    connections = [
        _par_edge("node_start", "B"),
        # B.if 只进 M0（单 lane 臂，无 fork 标记）；B.default 锚点 fork M0+M1
        _par_edge("B", "M0", branch="B-if"),
        _par_edge("B", "M0", branch="B-default", sfork=pid),
        _par_edge("B", "M1", branch="B-default", sfork=pid),
        _par_edge("M0", "VA"),
        _par_edge("M1", "VB"),
        _par_edge("VA", "C", tjoin=pid),
        _par_edge("VB", "C", tjoin=pid),
    ]
    plan = build_parallel_join_plan(connections)
    assert (pid, "C") in plan.joins
    done_m1 = f"_parallel_done__{pid}__C__M1"

    skip_plan = build_dead_lane_skip_plan(connections, plan)
    by_branch = {(s.branch_node, s.branch_id): s for s in skip_plan.skips}
    # B.if 只激活 M0，死的是 M1 lane，应补 skip -> done(M1)
    assert by_branch[("B", "B-if")].done_node == done_m1


def test_shared_fork_source_other_group_marker_must_not_skip_compensation():
    """同一 fork_source 节点 F 同时参与两个并行组：
      - pida：lane M0/M1 汇聚 CA
      - pidb：lane N0/N1 汇聚 CB
    F-x 臂携带【pidb】的全 lane fork 标记（F-x→N0/N1），同时又以一条无标记
    普通边只进入 pida 的 M0（F-x→M0）。因此对 pida 而言 F-x 是只激活严格
    子集（M0）、死 M1 需补偿的普通臂。
    旧逻辑把 fork 标记跨 parallel_id 聚合到 fork_source 整节点，会因 F-x 带了
    pidb 标记而错误跳过 pida 的 M1 补偿；修复后按 parallel_id 隔离，必须补 M1。
    """
    pida, pidb = "pida", "pidb"
    connections = [
        _par_edge("node_start", "F"),
        # F-x：pidb 的全 lane fork（N0/N1，带 pidb 标记）+ 仅进 pida 的 M0
        _par_edge("F", "N0", branch="F-x", sfork=pidb),
        _par_edge("F", "N1", branch="F-x", sfork=pidb),
        _par_edge("F", "M0", branch="F-x"),
        # F-default：pida 的全 lane fork（M0/M1，带 pida 标记），承担 M1 覆盖
        _par_edge("F", "M0", branch="F-default", sfork=pida),
        _par_edge("F", "M1", branch="F-default", sfork=pida),
        # pida 汇聚 CA
        _par_edge("M0", "VA"),
        _par_edge("M1", "VB"),
        _par_edge("VA", "CA", tjoin=pida),
        _par_edge("VB", "CA", tjoin=pida),
        # pidb 汇聚 CB（与 CA 互不相通，避免形成 lane-free 捷径）
        _par_edge("N0", "WA"),
        _par_edge("N1", "WB"),
        _par_edge("WA", "CB", tjoin=pidb),
        _par_edge("WB", "CB", tjoin=pidb),
    ]
    plan = build_parallel_join_plan(connections)
    assert (pida, "CA") in plan.joins
    assert (pidb, "CB") in plan.joins
    # 两个组的 fork_source 都是同一节点 F
    assert plan.joins[(pida, "CA")].fork_source == "F"
    assert plan.joins[(pidb, "CB")].fork_source == "F"

    done_m1 = f"_parallel_done__{pida}__CA__M1"
    skip_plan = build_dead_lane_skip_plan(connections, plan)
    by_branch = {(s.branch_node, s.branch_id): s for s in skip_plan.skips}

    # F-x 对 pida 只激活 M0，死 M1 必须补偿，即便它携带了 pidb 的 fork 标记
    assert ("F", "F-x") in by_branch
    assert by_branch[("F", "F-x")].done_node == done_m1
    # F-default 是 pida 全 lane fork，不应产生任何 pida 补偿；
    # 也不应出现任何 pidb 的误补偿（F-x 对 pidb 本就激活全部 lane）。
    assert ("F", "F-default") not in by_branch
    for skip in skip_plan.skips:
        assert skip.done_node.startswith(f"_parallel_done__{pida}__")


def test_error_branch_arm_must_not_get_dead_lane_skip():
    """@@ 错误分支不是普通判定臂，绝不能为其生成死 lane skip。

    拓扑（评审警告#3 最小反例）：并行组 pid 的两条 lane M0/M1 汇聚 C；
    B.default 是双 lane fork（M0+M1，承担全部 lane 覆盖）；另有一条
    B@@errorBranch 错误分支只进入 M0。旧逻辑把 @@ 臂也纳入 branch_arms，
    会生成 branch_id="B@@errorBranch" 的 skip，而 converter 的普通分支接线
    无法把该 skip 挂到 _error_branch 路由上，留下无触发源的 skip 组件。
    修复后必须过滤 @@，错误分支进入单 lane 的同步交回既有 error_branch 语义。
    """
    pid = "wf"
    connections = [
        _par_edge("node_start", "B"),
        # 错误分支：只进入 M0 单 lane（branchId 含 @@，无 fork 标记）
        _par_edge("B", "M0", branch="B@@errorBranch"),
        # default：pid 的全 lane fork，覆盖 M0/M1（Guard2 的互斥覆盖臂）
        _par_edge("B", "M0", branch="B-default", sfork=pid),
        _par_edge("B", "M1", branch="B-default", sfork=pid),
        _par_edge("M0", "VA"),
        _par_edge("M1", "VB"),
        _par_edge("VA", "C", tjoin=pid),
        _par_edge("VB", "C", tjoin=pid),
    ]
    plan = build_parallel_join_plan(connections)
    assert (pid, "C") in plan.joins

    skip_plan = build_dead_lane_skip_plan(connections, plan)
    # 不得为 @@ 错误分支生成任何 skip；default 是全 lane 臂本也无需补偿，
    # 因此该拓扑下 skips 必须为空（整体回退到 error_branch / wait_for_all）。
    assert len(skip_plan.skips) == 0
    assert not any("@@" in s.branch_id for s in skip_plan.skips)


class _FakeLoopGroup:
    """最小 LoopGroup 替身：仅记录接线与注册的补偿/done 组件。"""

    def __init__(self):
        self.comps: dict = {}
        self.connections: list = []

    def add_workflow_comp(self, cid, comp, inputs_schema=None):
        self.comps[cid] = comp

    def add_connection(self, src, tgt):
        self.connections.append((src, tgt))


def _wire_loop_body_parallel_lanes(group, raw_conns, by_id,
                                   branch_conns, regular_conns):
    """测试辅助：经 getattr 调用转换器的 loop body lane 接线逻辑，
    避免在类外直接访问受保护成员（G.CLS.11）。"""
    wire = getattr(IRConverter, "_wire_loop_body_parallel_lanes")
    return wire(group, raw_conns, by_id, {}, branch_conns, regular_conns)


def _loop_body_parallel_ir(*, extra_direct_edge: bool):
    """loop body 内并行 fork：P→M0/M1（fork 侧标记），经 VA/VB 汇聚 C（join
    侧标记）。extra_direct_edge=True 时额外挂一条未被 lane 覆盖的直达边
    ZZ→C（ZZ 由条件臂 B→ZZ 进入），用于验证全覆盖回退。"""
    pid = "looppid"
    conns = [
        _par_edge("lb_start", "P"),
        _par_edge("P", "M0", sfork=pid),
        _par_edge("P", "M1", sfork=pid),
        _par_edge("M0", "VA"),
        _par_edge("M1", "VB"),
        _par_edge("VA", "C", tjoin=pid),
        _par_edge("VB", "C", tjoin=pid),
    ]
    if extra_direct_edge:
        conns += [
            _par_edge("B", "ZZ", branch="B-if"),
            _par_edge("ZZ", "C"),
        ]
    by_id = {nid: {"id": nid, "type": "jiuwen.message", "configs": {}}
             for nid in ["lb_start", "P", "M0", "M1", "VA", "VB", "C", "B", "ZZ"]}
    return conns, by_id, pid


def test_loop_body_join_with_uncovered_edge_keeps_wait_for_all():
    """未被 lane 覆盖的直达入边：VA/VB→C 保留直接边，loop body 不接管、不插列表 barrier。"""
    raw_conns, by_id, _pid = _loop_body_parallel_ir(extra_direct_edge=True)
    plan = build_parallel_join_plan(raw_conns)
    assert (_pid, "C") in plan.joins

    branch_conns, regular_conns = [], []
    for c in raw_conns:
        s = (c.get("source") or {}).get("componentId") or ""
        d = (c.get("target") or {}).get("componentId") or ""
        bid = (c.get("source") or {}).get("branchId") or ""
        if bid:
            branch_conns.append((s, d, bid))
        else:
            regular_conns.append((s, d))

    group = _FakeLoopGroup()
    branch_conns, regular_conns = _wire_loop_body_parallel_lanes(
        group, raw_conns, by_id, branch_conns, regular_conns
    )

    # 未接管：VA/VB 仍直接到 C（不出现 lane-done），无列表 barrier
    assert ("VA", "C") in regular_conns
    assert ("VB", "C") in regular_conns
    assert not any(isinstance(src, list) for src, _t in group.connections)
    assert group.comps == {}


def test_loop_body_join_fully_covered_is_lane_managed():
    """对照组：全部入边都被 lane 覆盖时，正常接管为列表 barrier（证明回退只在有未覆盖边时触发，不误伤正常并行汇聚）。"""
    raw_conns, by_id, pid = _loop_body_parallel_ir(extra_direct_edge=False)
    plan = build_parallel_join_plan(raw_conns)
    spec = plan.joins[(pid, "C")]
    done_nodes = [lane.done_node for lane in spec.lanes]

    regular_conns = [
        (
            (c.get("source") or {}).get("componentId"),
            (c.get("target") or {}).get("componentId"),
        )
        for c in raw_conns
    ]
    group = _FakeLoopGroup()
    _b, regular_conns = _wire_loop_body_parallel_lanes(
        group, raw_conns, by_id, [], regular_conns
    )

    # 已接管：VA/VB→C 被改写为到各自 done，并插入 [done,...]→C 列表 barrier
    assert ("VA", "C") not in regular_conns
    assert ("VB", "C") not in regular_conns
    assert (done_nodes, "C") in group.connections


@pytest.mark.asyncio
async def test_loop_body_lane_reuse_skip_must_not_leak_to_root():
    """loop body 内的跨分支 lane 复用：补偿节点必须建在 LoopGroup 内，不得泄漏到根。"""
    ir, pid = _build_loop_body_lane_reuse_ir()

    workflow = await _build_workflow(ir)
    spec = _get_internal(workflow).config().spec
    root_ids = set(spec.comp_configs)
    # 根 workflow 不应出现任何只服务于 loop body 并行汇聚的补偿/lane-done 节点
    assert not [i for i in root_ids if i.startswith("_lane_skip__")]
    assert not [i for i in root_ids if i.startswith("_parallel_done__")]

    # 正向断言：body 的 lane-done / 死 lane skip 必须确实注册在 LoopGroup 内部
    loop_group = _find_component_instance(workflow, lambda c: type(c).__name__ == "LoopGroup")
    assert loop_group is not None, "LoopGroup 组件未构建"
    body_ids = set(getattr(loop_group, "_node_ids", []))
    expected_done = {
        f"_parallel_done__{pid}__lb_CODE__lb_M0",
        f"_parallel_done__{pid}__lb_CODE__lb_M1",
    }
    # body 汇聚由两个 lane-done 接管
    assert expected_done.issubset(body_ids)
    # B.if 臂只激活 M1（经 lb_I-if→M1 这一支只走单 lane 的场景由 I 的臂产生），
    # 至少存在一个建在 LoopGroup 内的 skip 补偿节点，且根图没有同名节点。
    body_skips = {i for i in body_ids if i.startswith("_lane_skip__")}
    assert body_skips, "LoopGroup 内缺少死 lane 补偿 skip 节点"
    assert body_skips.isdisjoint(root_ids)


def _build_loop_body_lane_reuse_ir():
    """构造 loop body 内跨分支 lane 复用的 IR：返回 (ir, parallel_id)。

    body 锚点 lb_B 的 if/default 复用同一并行组（lb_M0/lb_M1 → lb_CODE），
    default 臂双 lane fork，而 I 的臂各自只走单 lane，需要在 LoopGroup 内补 skip。
    """

    def _comp(cid, ctype, configs=None, inputs=None):
        return {
            "id": cid,
            "type": ctype,
            "configs": configs or {},
            "inputs": inputs or {},
        }

    body_nodes = [
        _comp("lb_B", "jiuwen.branch", _branch_cfg(
            ("lb_B-if", "(${node_start.systemFields.type} != 0)"),
        )),
        _comp("lb_I", "jiuwen.branch", _branch_cfg(
            ("lb_I-if", "(${node_start.systemFields.type} == 1)"),
            ("lb_I-elseIf-1", "(${node_start.systemFields.type} == 2)"),
        )),
        _comp("lb_M0", "jiuwen.message", {"template": "m0"}),
        _comp("lb_M1", "jiuwen.message", {"template": "m1"}),
        _comp("lb_VA", "jiuwen.message", {"template": "va"}),
        _comp("lb_VB", "jiuwen.message", {"template": "vb"}),
        _comp("lb_CODE", "jiuwen.code", {"code": "def main(args): return {'aa': 'x'}"}),
    ]
    loop_node = {
        "id": "node_loop",
        "type": "jiuwen.loop",
        "configs": {"loopType": "numLoop", "loopBody": body_nodes},
        "inputs": {"numLoopVar": 1},
        "outputs": {},
    }
    pid = "wf"
    connections = [
        _par_edge("node_start", "node_loop_input"),
        _par_edge("node_loop_output", "node_end"),
        # 虚拟锚点：loop 输入 -> body 起点 lb_B；lb_CODE -> loop 输出
        _par_edge("node_loop_input", "lb_B"),
        _par_edge("lb_CODE", "node_loop_output"),
        _par_edge("lb_B", "lb_I", branch="lb_B-if"),
        _par_edge("lb_B", "lb_M0", branch="lb_B-default", sfork=pid),
        _par_edge("lb_B", "lb_M1", branch="lb_B-default", sfork=pid),
        _par_edge("lb_I", "lb_M1", branch="lb_I-if"),
        _par_edge("lb_I", "lb_M0", branch="lb_I-elseIf-1"),
        _par_edge("lb_I", "node_loop_output", branch="lb_I-default"),
        _par_edge("lb_M0", "lb_VA"),
        _par_edge("lb_M1", "lb_VB"),
        _par_edge("lb_VA", "lb_CODE", tjoin=pid),
        _par_edge("lb_VB", "lb_CODE", tjoin=pid),
    ]
    ir = {
        "configs": {},
        "components": [
            _comp("node_start", "jiuwen.start", inputs={
                "userFields": {},
                "systemFields": {"type": 1, "llm": "", "query": "", "sys": {}},
            }),
            loop_node,
            _comp("node_end", "jiuwen.end"),
        ],
        "metadata": {},
        "connections": connections,
    }
    return ir, pid


def _find_component_instance(workflow, predicate):
    """在已实例化的 workflow 中查找满足谓词的组件实例。覆盖两条注册路径：
    根图节点 pregel node 的 _executable，以及循环节点 LoopComponent 内的
    _loop_group（LoopGroup 是 BaseWorkflow，body 组件就注册在它的 _node_ids）。"""
    internal = _get_internal(workflow)
    graph = getattr(internal, "_graph", None)
    nodes = getattr(graph, "nodes", None)
    if not isinstance(nodes, dict):
        return None

    found = []

    def _scan(obj, depth=0):
        if depth > 4 or obj is None or found:
            return
        if predicate(obj):
            found.append(obj)
            return
        container = getattr(obj, "__dict__", None)
        if not isinstance(container, dict):
            return
        for value in list(container.values()):
            if isinstance(value, (str, int, float, bytes, bool)) or callable(value):
                continue
            _scan(value, depth + 1)

    for pregel_node in nodes.values():
        _scan(getattr(pregel_node, "_executable", None))
    return found[0] if found else None


@pytest.mark.asyncio
async def test_loop_body_error_branch_edge_must_not_register_on_root():
    """loopBody 内 @@ 错误边不得在根 workflow 注册孤立的 {body_node}_error_branch 组件。评审警告#2。"""
    ir, _pid = _build_loop_body_lane_reuse_ir()
    # body 内部一条 @@ 错误分支边：源/目标都是 loop body 节点
    ir["connections"].append(
        _par_edge("lb_M1", "lb_CODE", branch="lb_M1@@errorBranch")
    )

    workflow = await _build_workflow(ir)
    root_ids = set(_get_internal(workflow).config().spec.comp_configs)

    # 根图只能含 start/loop/end 三个顶层组件，不得出现任何 body 节点派生的
    # _error_branch（尤其不能出现以 lb_ 开头的孤立错误分支组件）。
    assert root_ids == {"node_start", "node_loop", "node_end"}
    assert not [i for i in root_ids if "_error_branch" in i]


def _build_simple_loop_body_error_ir(*, error_target_outer: bool):
    """最小 loop：start → loop(input→lb_MSG→lb_CODE→output) → end。

    error_target_outer=False：lb_MSG（非分支源 jiuwen.message）的 @@error_1
    指向 body 内 lb_CODE，验证错误路由不会被静默丢弃，而会在 LoopGroup 内
    合成 {src}_error_branch。
    error_target_outer=True：@@error_1 跨出 body 指向体外 node_end（body→外层
    边界 @@ 边），验证它既不会在根图合成孤立错误分支，也不会被 LoopGroup 接管。
    """

    def _comp(cid, ctype, configs=None, inputs=None):
        return {
            "id": cid,
            "type": ctype,
            "configs": configs or {},
            "inputs": inputs or {},
        }

    body_nodes = [
        _comp("lb_MSG", "jiuwen.message", {"template": "hi"}),
        _comp("lb_CODE", "jiuwen.code", {"code": "def main(args): return {'k': 'v'}"}),
    ]
    error_target = "node_end" if error_target_outer else "lb_CODE"
    connections = [
        _par_edge("node_start", "node_loop_input"),
        _par_edge("node_loop_output", "node_end"),
        # 虚拟锚点：loop 输入 -> body 起点；body 终点 -> loop 输出
        _par_edge("node_loop_input", "lb_MSG"),
        _par_edge("lb_CODE", "node_loop_output"),
        # 正常成功边 + @@ 错误边（message 无 add_branch，旧逻辑会静默丢弃后者）
        _par_edge("lb_MSG", "lb_CODE"),
        _par_edge("lb_MSG", error_target, branch="lb_MSG@@error_1"),
    ]
    return {
        "configs": {},
        "components": [
            _comp("node_start", "jiuwen.start", inputs={
                "userFields": {},
                "systemFields": {"type": 1, "query": "", "sys": {}},
            }),
            {
                "id": "node_loop",
                "type": "jiuwen.loop",
                "configs": {"loopType": "numLoop", "loopBody": body_nodes},
                "inputs": {"numLoopVar": 1},
                "outputs": {},
            },
            _comp("node_end", "jiuwen.end"),
        ],
        "metadata": {},
        "connections": connections,
    }


def _get_loop_group(workflow):
    return _find_component_instance(
        workflow, lambda c: type(c).__name__ == "LoopGroup"
    )


@pytest.mark.asyncio
async def test_loop_body_non_branch_source_error_branch_not_dropped():
    """非分支源（message）的 body 内 @@ 错误边必须在 LoopGroup 内合成错误路由，不得静默丢弃。"""
    ir = _build_simple_loop_body_error_ir(error_target_outer=False)

    workflow = await _build_workflow(ir)

    loop_group = _get_loop_group(workflow)
    assert loop_group is not None, "LoopGroup 组件未构建"

    # 合成节点必须注册在 LoopGroup 内（而非根图）
    body_ids = set(getattr(loop_group, "_node_ids", []))
    error_node = "lb_MSG_error_branch"
    assert error_node in body_ids

    # src -> 合成错误路由 的接线存在于 LoopGroup
    group_edges = getattr(
        getattr(loop_group, "_workflow_spec"), "edges", {}
    )
    assert error_node in group_edges.get("lb_MSG", [])

    # 合成的是 BranchComponent，且错误臂路由到 body 内目标 lb_CODE
    group_graph = getattr(loop_group, "_graph", None)
    error_executable = getattr(group_graph.nodes[error_node], "_executable", None)
    assert type(error_executable).__name__ == "BranchComponent"
    branches = getattr(error_executable.router(), "_branches", [])
    routed = [(b.branch_id, tuple(b.target)) for b in branches]
    assert ("lb_MSG@@error_1", ("lb_CODE",)) in routed

    # 正常成功边仍然保留
    assert "lb_CODE" in group_edges.get("lb_MSG", [])

    # 根图保持干净：只有 start/loop/end，无任何 body 派生错误分支
    root_ids = set(_get_internal(workflow).config().spec.comp_configs)
    assert root_ids == {"node_start", "node_loop", "node_end"}
    assert error_node not in root_ids


@pytest.mark.asyncio
async def test_body_to_outer_error_branch_fails_fast_not_silently_dropped():
    """body→外层的 @@ 跨边界错误边不得被静默丢弃（掩盖配置错误），必须编译期显式报错。

    跨 LoopGroup 边界的错误路由没有任何运行时接线语义：源节点只存在于隔离的
    LoopGroup 子图，目标节点只存在于根图。旧逻辑无条件 continue 悄悄吞掉该边，
    用户配置的错误处理“不生效”却无任何提示。修复后必须 fail-fast，并在错误信息
    中指明源/目标/所属 loop，引导用户改为 body 内目标或把错误处理挪到 loop 之后。
    """
    ir = _build_simple_loop_body_error_ir(error_target_outer=True)

    with pytest.raises(ValueError) as exc_info:
        await _build_workflow(ir)

    message = str(exc_info.value)
    assert "cross-boundary error route" in message
    # 精确定位三要素，便于用户排查
    assert "lb_MSG" in message
    assert "lb_MSG@@error_1" in message
    assert "node_end" in message


# ---------------------------------------------------------------------------
# 评审 ③：多组安全判定契约冲突
#   嵌套菱形汇聚点 X 同时是外层判定 B 的「直达条件边」目标（B.if 既扇出内层
#   并行 P/Q，又直达 X）。hybrid 产出多 CNF 组 [{D1,DD},{D2,DD}]，而其中没有
#   任何 standalone 前驱（全部条件可达）。旧的「每组必须含 standalone」判定会
#   误判不安全，放弃 barrier 升级与条件边过滤 —— B.if 的直达边直接触发 X，
#   与 lane done 一起使 X 执行 2 次。修复后改为按 targeting 条件逐组做
#   _pred_covers 覆盖检查，B.if 同时覆盖两组 → 安全 → X 只执行 1 次。
# ---------------------------------------------------------------------------

def _build_nested_diamond_mixed_target_graph(query_nonempty: bool):
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["B", "P", "Q", "D1", "D2", "DD", "X", "MSG"]:
        g.add_node(node_id, object(), wait_for_all=(node_id == "X"))

    g.start_node("B")

    def if_taken():
        return query_nonempty

    def default_taken():
        return not query_nonempty

    # B.if 既扇出内层并行 P/Q（普通节点，经普通边到 lane done D1/D2），又带
    # 一条直达汇聚点 X 的条件边；B.default 仅经 DD 直达 X。
    g.add_conditional_edges(
        "B",
        _MiniRouter([
            _MiniBranch("B-if", if_taken, ["P", "Q", "X"]),
            _MiniBranch("B-default", default_taken, ["DD"]),
        ]),
    )
    g.register_branch_targets("B", {"P", "Q", "X", "DD"})
    for src, tgt in [
        ("P", "D1"),
        ("Q", "D2"),
        ("DD", "X"),
        ("X", "MSG"),
    ]:
        g.add_edge(src, tgt)
    g.add_edge(["D1", "D2"], "X")
    return g


def test_nested_diamond_mixed_target_join_executes_once(_event_loop):
    """if 路径下 B 直达 X 的条件边被安全过滤，X/MSG 各只执行一次。"""

    async def _run():
        g = _build_nested_diamond_mixed_target_graph(True)
        pregel = getattr(g, "_compile")()
        for node_name, pnode in pregel.nodes.items():
            pnode.func = _make_fn(node_name)
        EXEC_LOG.clear()
        from openjiuwen.core.graph.pregel.config import PregelConfig

        await pregel.run(config=PregelConfig(session_id=None, ns=None))

    _event_loop.run_until_complete(asyncio.wait_for(_run(), timeout=15))
    assert len(EXEC_LOG.get("X", [])) == 1, (
        f"直达条件边被过滤后 X 应只执行 1 次，实际 {len(EXEC_LOG.get('X', []))} 次；"
        f"执行记录: { {k: len(v) for k, v in EXEC_LOG.items()} }"
    )
    assert len(EXEC_LOG.get("MSG", [])) == 1


# ---------------------------------------------------------------------------
# 评审 ④：笛卡尔积全组合展开的规模护栏
#   正常嵌套菱形生成 2 个 CNF 组；把组数上限临时调到 1 时，hybrid 必须放弃
#   配对并回退 base 的单 AND 组，而不是产出超限的笛卡尔组。
# ---------------------------------------------------------------------------

def test_diamond_cnf_expansion_respects_group_cap(_event_loop):
    g = _build_nested_diamond_graph(True)
    with patch.object(nested_patch, "_MAX_DIAMOND_CNF_GROUPS", 1):
        groups = g._resolve_barrier_groups(  # pylint: disable=protected-access
            "X", [{"D1"}, {"D2"}, {"DD"}]
        )
    # 超过上限 → 回退 base：三个前驱并入单个 AND 组，不做笛卡尔配对
    assert _norm_groups(groups) == [["D1", "D2", "DD"]], groups


# ===========================================================================
# MR !2569 第二轮走读意见回归（3 Medium + 1 Low）
#  M1  route signatures 有界 BFS 的 loop 环保护（环污染→回退 base）
#  M2  Guard 2 跨分支节点覆盖证据（外层全 lane fork 臂激活死 lane）
#  M3  loop body 并行回退路径必须真正设置 wait_for_all
#  Low4 body→外层 @@ 跨边界错误边 fail-fast（见上方
#       test_body_to_outer_error_branch_fails_fast_not_silently_dropped）
# ===========================================================================


def _build_cyclic_nested_diamond_graph():
    """在标准嵌套菱形（见 _build_nested_diamond_graph）上加一条 loop 回边
    D2 -> B，模拟含 Loop 时分支节点被回边重新可达的环拓扑。

    有界 BFS（在 X 处截断）从外层 if 臂头 Q 出发会沿 Q→…→D2→B 绕回判定节点
    B，再沿其另一臂漏出，污染 arm_reach 的互斥签名。此时 hybrid 绝不能做
    笛卡尔配对，必须回退 base 的成熟结论。
    """
    import openjiuwen.core.workflow  # noqa: F401  规避循环导入
    from openjiuwen.core.graph.graph import PregelGraph

    g = PregelGraph()
    for node_id in ["B", "P", "Q", "LLM", "LLM1", "LLM2", "D1", "D2", "DD", "X"]:
        g.add_node(node_id, object(), wait_for_all=(node_id == "X"))
    g.start_node("B")
    t = True
    g.add_conditional_edges("B", _MiniRouter([
        _MiniBranch("B-if", lambda: t, ["P", "Q"]),
        _MiniBranch("B-default", lambda: not t, ["DD"]),
    ]))
    g.register_branch_targets("B", {"P", "Q", "DD"})
    g.add_conditional_edges("P", _MiniRouter([
        _MiniBranch("P-if", lambda: t, ["LLM"]),
        _MiniBranch("P-default", lambda: not t, ["D1"]),
    ]))
    g.register_branch_targets("P", {"LLM", "D1"})
    g.add_conditional_edges("Q", _MiniRouter([
        _MiniBranch("Q-if", lambda: t, ["LLM1"]),
        _MiniBranch("Q-default", lambda: not t, ["D2"]),
    ]))
    g.register_branch_targets("Q", {"LLM1", "D2"})
    for src, tgt in [
        ("LLM", "D1"),
        ("LLM1", "LLM2"),
        ("LLM2", "D2"),
        ("DD", "X"),
        # loop 回边：lane 终端 D2 绕回外层判定 B（有界区域内成环）
        ("D2", "B"),
    ]:
        g.add_edge(src, tgt)
    g.add_edge(["D1", "D2"], "X")
    return g


def test_bounded_reach_cycle_detection(_event_loop):
    """环检测器：有界区域内有回边判 True；去掉回边（无环钻石）判 False。"""
    cyclic = _build_cyclic_nested_diamond_graph()
    # 从外层 if 臂头 Q 出发、在 X 截断，会经 D2→B 成环
    assert nested_patch._bounded_reach_has_cycle(  # pylint: disable=protected-access
        cyclic, "Q", "X"
    ) is True
    # default 臂头 DD 直达 X，不绕环
    assert nested_patch._bounded_reach_has_cycle(  # pylint: disable=protected-access
        cyclic, "DD", "X"
    ) is False

    acyclic = _build_nested_diamond_graph(True)
    assert nested_patch._bounded_reach_has_cycle(  # pylint: disable=protected-access
        acyclic, "Q", "X"
    ) is False


def test_cyclic_nested_diamond_hybrid_falls_back_to_base(_event_loop):
    """环污染下 hybrid 必须整体回退 base，绝不产出笛卡尔配对。"""
    g = _build_cyclic_nested_diamond_graph()
    source_list = [{"D1"}, {"D2"}, {"DD"}]
    base_groups = nested_patch._resolve_barrier_groups_nested_patched(  # pylint: disable=protected-access
        g, "X", source_list
    )
    # 打补丁后的公开入口 = hybrid；环污染时其结论必须与 base 完全一致
    groups = _resolve_barrier_groups(g, "X", source_list)
    assert _norm_groups(groups) == _norm_groups(base_groups)
    # 对照组：同拓扑无环时 hybrid 正常升级为两组 CNF 配对（证明回退确由环触发）
    acyclic = _build_nested_diamond_graph(True)
    paired = _resolve_barrier_groups(acyclic, "X", source_list)
    assert {frozenset(x) for x in paired} == {
        frozenset({"D1", "DD"}),
        frozenset({"D2", "DD"}),
    }


def _build_inner_arm_outer_fork_coverage_ir(*, inner_reachable_from_outer_fork):
    """M2 拓扑：外层判定 B 与内层判定 I。

    - B.default：携带当前并行组 pid fork 标记的全 lane 臂（M0+M1），汇聚 C；
    - B.if：进入内层判定 I；I.if 只进 M0 单 lane，I.else 去不汇聚 C 的 Z；
    - 于是 I.if 臂下死 lane=M1，I 的同节点兄弟臂（I.else→Z）无法覆盖 M1，
      只有【跨分支节点】的 B.default 全 lane fork 臂能覆盖 M1。

    inner_reachable_from_outer_fork=True 时额外加 M0→I，使 I 也能从
    B.default 全 lane 臂到达 → 两路径不再互斥，跨分支证据必须被拒绝。
    """
    pid = "wf"
    conns = [
        _par_edge("node_start", "B"),
        _par_edge("B", "I", branch="B-if"),
        _par_edge("B", "M0", branch="B-default", sfork=pid),
        _par_edge("B", "M1", branch="B-default", sfork=pid),
        _par_edge("I", "M0", branch="I-if"),
        _par_edge("I", "Z", branch="I-else"),
        _par_edge("M0", "VA"),
        _par_edge("M1", "VB"),
        _par_edge("VA", "C", tjoin=pid),
        _par_edge("VB", "C", tjoin=pid),
        _par_edge("C", "node_end"),
    ]
    if inner_reachable_from_outer_fork:
        # 让 I 也落在 B.default 全 lane 臂的可达集内 → 破坏互斥前提
        conns.append(_par_edge("M0", "I"))
    return conns, pid


def test_inner_arm_dead_lane_covered_by_outer_fork_arm():
    """内层单 lane 臂的死 lane 由跨分支节点的外层全 lane fork 臂覆盖时，应补 skip。"""
    conns, pid = _build_inner_arm_outer_fork_coverage_ir(
        inner_reachable_from_outer_fork=False
    )
    plan = build_parallel_join_plan(conns)
    assert (pid, "C") in plan.joins

    skip_plan = build_dead_lane_skip_plan(conns, plan)
    by_branch = {(s.branch_node, s.branch_id): s for s in skip_plan.skips}
    # 旧逻辑只在 I 的兄弟臂里找覆盖（I.else→Z 不覆盖 M1），漏掉 I.if 的补偿；
    # 修复后跨分支节点找到 B.default 全 lane fork 臂覆盖 M1，且 I 只活在 B.if
    # 兄弟臂内（与 B.default 互斥），于是为 I.if 补 dead lane=M1 的 skip。
    inner_skip = by_branch.get(("I", "I-if"))
    assert inner_skip is not None, by_branch.keys()
    assert inner_skip.done_node == f"_parallel_done__{pid}__C__M1"


def test_inner_arm_outer_fork_coverage_requires_mutual_exclusion():
    """反例：内层判定也能从外层全 lane fork 臂到达时两路径不互斥，不得跨节点补 skip。"""
    conns, pid = _build_inner_arm_outer_fork_coverage_ir(
        inner_reachable_from_outer_fork=True
    )
    plan = build_parallel_join_plan(conns)
    assert (pid, "C") in plan.joins

    skip_plan = build_dead_lane_skip_plan(conns, plan)
    by_branch = {(s.branch_node, s.branch_id): s for s in skip_plan.skips}
    # I 出现在 B.default 全 lane 臂可达集内，互斥前提不成立——宁漏补也不能让
    # AND barrier 被错误满足；不得为 I.if 生成跨节点 skip。
    assert ("I", "I-if") not in by_branch


# ---- M3：loop body 并行回退路径真正设置 wait_for_all ----

def _build_loop_body_parallel_join_ir(*, uncovered_extra_pred: bool):
    """Loop body 内并行：input→P，P 全 lane fork M0/M1，经 VA/VB 汇聚 code 节点 C。

    uncovered_extra_pred=True 时另挂一条未被 lane 覆盖的直达边 P→ZZ→C，触发
    全覆盖回退（不接管为列表 barrier），此时 C 必须带 wait_for_all。
    """

    def _comp(cid, ctype, configs=None, inputs=None):
        return {
            "id": cid,
            "type": ctype,
            "configs": configs or {},
            "inputs": inputs or {},
        }

    pid = "bodypid"
    body_nodes = [
        _comp("lb_P", "jiuwen.message", {"template": "p"}),
        _comp("lb_M0", "jiuwen.message", {"template": "m0"}),
        _comp("lb_M1", "jiuwen.message", {"template": "m1"}),
        _comp("lb_VA", "jiuwen.message", {"template": "va"}),
        _comp("lb_VB", "jiuwen.message", {"template": "vb"}),
        _comp("lb_C", "jiuwen.code", {"code": "def main(args): return {'k': 1}"}),
    ]
    connections = [
        _par_edge("node_start", "node_loop_input"),
        _par_edge("node_loop_output", "node_end"),
        _par_edge("node_loop_input", "lb_P"),
        _par_edge("lb_P", "lb_M0", sfork=pid),
        _par_edge("lb_P", "lb_M1", sfork=pid),
        _par_edge("lb_M0", "lb_VA"),
        _par_edge("lb_M1", "lb_VB"),
        _par_edge("lb_VA", "lb_C", tjoin=pid),
        _par_edge("lb_VB", "lb_C", tjoin=pid),
        _par_edge("lb_C", "node_loop_output"),
    ]
    if uncovered_extra_pred:
        body_nodes.append(_comp("lb_ZZ", "jiuwen.message", {"template": "z"}))
        connections += [
            _par_edge("lb_P", "lb_ZZ"),
            _par_edge("lb_ZZ", "lb_C"),
        ]
    return {
        "configs": {},
        "components": [
            _comp("node_start", "jiuwen.start", inputs={
                "userFields": {},
                "systemFields": {"type": 1, "query": "", "sys": {}},
            }),
            {
                "id": "node_loop",
                "type": "jiuwen.loop",
                "configs": {"loopType": "numLoop", "loopBody": body_nodes},
                "inputs": {"numLoopVar": 1},
                "outputs": {},
            },
            _comp("node_end", "jiuwen.end"),
        ],
        "metadata": {},
        "connections": connections,
    }


@pytest.mark.asyncio
async def test_loop_body_fallback_join_gets_wait_for_all():
    """未被 lane 完整覆盖的 loop body 汇聚点必须真正带 wait_for_all（M3 修复点）。"""
    ir = _build_loop_body_parallel_join_ir(uncovered_extra_pred=True)
    workflow = await _build_workflow(ir)
    loop_group = _get_loop_group(workflow)
    assert loop_group is not None
    body_graph = getattr(loop_group, "_graph", None)
    # 旧逻辑 loop body 从不传 parallel_join_nodes，回退汇聚点没有 wait_for_all
    # → 直达边可提前/重复触发 C。修复后回退汇聚点必须进 waits。
    assert "lb_C" in getattr(body_graph, "waits", set())


@pytest.mark.asyncio
async def test_loop_body_fully_covered_join_not_wait_for_all():
    """对照组：lane 完整覆盖时由列表 barrier 接管，不叠加 wait_for_all。"""
    ir = _build_loop_body_parallel_join_ir(uncovered_extra_pred=False)
    workflow = await _build_workflow(ir)
    loop_group = _get_loop_group(workflow)
    body_graph = getattr(loop_group, "_graph", None)
    assert "lb_C" not in getattr(body_graph, "waits", set())

