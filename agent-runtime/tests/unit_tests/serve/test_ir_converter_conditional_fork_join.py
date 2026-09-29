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
from openjiuwen.core.workflow.components.component import WorkflowComponent

from jiuwen.extension.patches.parallel_branch_grouping_patch import (
    apply_parallel_branch_grouping_patch,
)
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
