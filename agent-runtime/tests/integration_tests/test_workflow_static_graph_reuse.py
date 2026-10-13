# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""静态图复用真实引擎集成测试（spec §9.2；issue #1555 验收标准 2/3/5）。

真实 openjiuwen 引擎 + 真实 IR 构建（三个无 LLM fixture：
``workflow_message.json`` Start/Message/End 纯消息流、``workflow_branch.json``
纯布尔条件分支、``workflow_aggregation.json`` 纯聚合流）：

- 同一 Workflow 实例 N 路并发 stream、不同 session → 输出互不串扰（验收 5）；
- 分支路由按各自输入走向、聚合各汇聚各自输入（并发，Patch C/D 敏感路径）；
- static_graph 模式下缓存命中（同内容取同实例）与重发布失效（验收 2/3）；
- 缓存实例的执行事件序列与"每请求新建实例"（off 模式语义）逐帧等价。

断言策略为语义断言：每路执行产出完整终结帧（workflow_final）、终结帧
``answer`` 回显本路 query（串扰会直接把别路 query 带进来）、非 tracer 帧
内容序列与"同 query 顺序执行"参考逐帧一致、各路事件序列骨架（chunk 类名 /
type / node_id）一致、缓存同内容恒同对象。

spec §9.2 补充测试项记录（Task 17 落盘，三子项在下方标注覆盖状态）：

1. **分支路由按各自输入走向**——已由 ``TestConcurrentBranchAndAggregation``
   用 ``workflow_branch.json``（纯布尔条件 ``length(query) > 10``）覆盖：
   并发长短 query 各走各自分支（partial_content 帧来源 message 节点不同）；
2. **join/aggregate 汇聚正确**——aggregation 节点（``jiuwen.aggregation``
   first-non-null）汇聚已由 ``workflow_aggregation.json`` 覆盖（各自聚合
   结果 = 各自 query）；**并行 join/barrier（菱形并行分支汇聚）仍为缺口**
   ——现有 fixture 无并行分支菱形结构；
3. **checkpointer 隔离**——本层（各 session store 按 session_id 各自建/删、
   执行后无残留、输出不互串）已由并发用例断言覆盖；**状态级隔离
   （跨 session 的中断/恢复、checkpoint 复用）仍为缺口**——见下。

已知不可驱动缺口（Task 17 记入 spec §9.2）：
1. 缓存实例上的中断/恢复——需 Questioner 交互的 IR；
2. 嵌套子工作流复用——需含 SubWorkflow 的 IR；
3. CID（ComplexIntentDetection）并发 invoke 的 ``_state`` 共享写竞争
   （T14 遗留观察点）——需 ``EI.ComplexIntentDetection`` IR + LLM 支撑的
   IntentDetection；且该竞争的可观测面在分支/子工作流执行窗口，无 LLM
   时无法真实驱动（详见 task-16-report.md）；
4. 并行 join/barrier 汇聚（见上子项 2）与 checkpointer 状态级隔离
   （见上子项 3）。
"""
import asyncio
import copy
import json
from pathlib import Path

import pytest

# 先触发 patch 应用链（circular import 规避：引擎类后取）。
# ir_converter 的 import 完成 sub_stream → ... → static_graph_patch（四件套）
# 的应用；引擎类（CompiledGraph/PregelGraph/Workflow）在其后取。
import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

from agent_runtime.common.config import settings
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.session.checkpointer.checkpointer import CheckpointerFactory
from openjiuwen.core.workflow import create_workflow_session

_IR_DIR = Path(__file__).resolve().parents[1] / "resource" / "ir_file"
IR_PATH = _IR_DIR / "workflow_message.json"
BRANCH_IR_PATH = _IR_DIR / "workflow_branch.json"
AGGREGATION_IR_PATH = _IR_DIR / "workflow_aggregation.json"

# workflow_branch.json 的两条消息节点（分支路由落点判别）：
# - query 长度 > 10 → node_1781166116130（"query长度大于10"）
# - 否则（default）→ node_1781166121959（"query是{{query}}"）
_BRANCH_LONG_NODE = "node_1781166116130"
_BRANCH_DEFAULT_NODE = "node_1781166121959"


@pytest.fixture(autouse=True)
def _static_graph_mode(monkeypatch):
    """每用例强制 static_graph 模式并清空进程级实例缓存。"""
    monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


def _load_ir(ir_path=IR_PATH):
    ir_data = json.loads(ir_path.read_text(encoding="utf-8"))
    ir_data["is_published"] = True
    return ir_data


async def _drive(wf, session, query):
    """真实 stream 一路执行（query 为完整输入），收集全部 chunk。"""
    chunks = []
    async for chunk in wf.stream({"query": query}, session):
        chunks.append(chunk)
    return chunks


def _final_payload(chunks):
    """取唯一 workflow_final 终结帧的 payload（缺失/重复即执行不完整）。"""
    finals = [c for c in chunks if getattr(c, "type", None) == "workflow_final"]
    assert len(finals) == 1, f"workflow_final 终结帧数量异常：{len(finals)}"
    return finals[0].payload


def _shape(chunks):
    """执行事件序列骨架：(chunk 类名, chunk.type)。

    第三分量 node_id 非引擎 chunk 字段（OutputSchema/TraceSchema 无该字段，
    getattr 恒 None；实测本 fixture 各帧均无该属性），不构成判别维度。
    """
    return [
        (type(c).__name__, getattr(c, "type", None), getattr(c, "node_id", None))
        for c in chunks
    ]


def _non_tracer_frames(chunks):
    """非 tracer 帧的内容序列（给定 query 时确定，用于内容级隔离比较）。"""
    frames = []
    for chunk in chunks:
        if type(chunk).__name__ == "TraceSchema":
            continue
        if hasattr(chunk, "payload"):
            frames.append((chunk.type, chunk.payload))
        else:
            frames.append((chunk.type, dict(getattr(chunk, "__pydantic_extra__", {}) or {})))
    return frames


def _streamed_message_node_ids(chunks):
    """分支路由判别：partial_content 帧的来源 message 节点 id 集合。"""
    node_ids = set()
    for chunk in chunks:
        if getattr(chunk, "type", None) != "partial_content":
            continue
        node_ids.add((getattr(chunk, "data", None) or {}).get("node_id"))
    return node_ids


class TestConcurrentIsolationOnSharedInstance:
    @pytest.mark.asyncio
    async def test_concurrent_streams_on_same_instance_are_isolated(self):
        """同一 Workflow 实例 4 路并发、不同 session：全部完成且输出互不串扰。

        判别：① 每路终结帧 ``answer`` 回显本路 query；② 每路非 tracer 帧
        内容序列与"同 query 顺序执行"参考逐帧一致（内容级隔离）；③ 各路
        事件序列骨架一致；④ 各 session 的 checkpointer store 按 session_id
        各自建/删、执行后无残留。
        """
        wf = await (await IRConverter.async_ir_to_workflow(_load_ir())).instantiate()
        queries = [f"hello-{i}" for i in range(4)]

        # 顺序参考（同实例、同 query）：并发输出须与其逐帧一致
        references = [
            await _drive(wf, create_workflow_session(session_id=f"ref-{i}"), query)
            for i, query in enumerate(queries)
        ]

        sessions = [create_workflow_session(session_id=f"sess-{i}") for i in range(4)]
        results = await asyncio.gather(*[
            _drive(wf, s, query) for s, query in zip(sessions, queries)
        ])

        shapes = []
        for i, chunks in enumerate(results):
            assert len(chunks) > 0, f"执行 {i} 输出为空——并发串扰"
            assert _final_payload(chunks).get("answer") == f"hello-{i}", (
                f"执行 {i} 终结帧 answer 未回显本路 query——并发串扰"
            )
            # 内容级隔离：非 tracer 帧逐帧等于同 query 的顺序参考
            assert _non_tracer_frames(chunks) == _non_tracer_frames(references[i]), (
                f"执行 {i} 中间帧内容与顺序参考不一致——并发串扰"
            )
            shapes.append(_shape(chunks))
        # 四路执行事件序列骨架一致：并发未污染任一执行的路径
        assert all(s == shapes[0] for s in shapes[1:])

        # compile 产物已绑定（Patch A 保留 self.pregel 属性写入，指向最近一次
        # compile 的产物——本断言只证"已绑定"，每执行独立 Pregel 的隔离
        # 由上方的执行/内容断言承担）
        graph = wf._internal._graph
        assert graph.pregel is not None

        # checkpointer 隔离（本层）：各 session 的 checkpoint store 按
        # session_id 各自建/删，执行完成后无残留——跨 session 共享 store
        # 或清理遗漏会在此暴露
        checkpointer = CheckpointerFactory.get_checkpointer()
        for i in range(4):
            assert not await checkpointer.session_exists(f"sess-{i}")

    @pytest.mark.asyncio
    async def test_repeated_execution_matches_fresh_build_output(self):
        """等价性：缓存实例的执行输出 == 每请求新建实例的输出（事件序列语义）。"""
        # 新建实例路径（off 模式语义）
        ir_fresh = _load_ir()
        wf_fresh = await (await IRConverter.async_ir_to_workflow(ir_fresh)).instantiate()
        out_fresh = await _drive(
            wf_fresh, create_workflow_session(session_id="fresh"), "hello-fresh"
        )

        # 缓存实例路径（static_graph 语义）——两次取（第二次为复用）两次执行
        ir_reuse = _load_ir()
        wf_reuse = await wic.aget_or_create_workflow_instance(
            "integration/reuse.json", ir_reuse, IRConverter.async_ir_to_workflow
        )
        out1 = await _drive(wf_reuse, create_workflow_session(session_id="reuse-1"), "hello-r1")
        wf_reuse2 = await wic.aget_or_create_workflow_instance(
            "integration/reuse.json", ir_reuse, IRConverter.async_ir_to_workflow
        )
        assert wf_reuse2 is wf_reuse  # 同内容命中同一 LazyWorkflow
        out2 = await _drive(wf_reuse2, create_workflow_session(session_id="reuse-2"), "hello-r2")

        # 三次执行事件序列骨架一致（消息型流的确定性骨架），且各自终结帧
        # 回显各自 query——复用实例不串扰
        assert _shape(out_fresh) == _shape(out1) == _shape(out2)
        assert _final_payload(out_fresh).get("answer") == "hello-fresh"
        assert _final_payload(out1).get("answer") == "hello-r1"
        assert _final_payload(out2).get("answer") == "hello-r2"

    @pytest.mark.asyncio
    async def test_republish_invalidates_cache(self):
        """同内容恒命中；重发布（内容 hash 变化）→ miss 并稳定命中新实例。"""
        ir_v1 = _load_ir()
        w1 = await wic.aget_or_create_workflow_instance(
            "integration/republish.json", ir_v1, IRConverter.async_ir_to_workflow
        )
        again = await wic.aget_or_create_workflow_instance(
            "integration/republish.json", ir_v1, IRConverter.async_ir_to_workflow
        )
        assert again is w1  # 未重发布：命中

        # 内容变化 → miss：以 metadata.updatedAt 变更为例。发布流本身只置
        # status/visibility/publishedAt；IR 重建发生在保存/校验流——"编辑后
        # 重发布 → 内容变 → miss"成立；纯重发布（未重建 IR、内容不变）时
        # 命中是正确行为（缓存 key 即内容 hash）
        ir_v2 = copy.deepcopy(ir_v1)
        ir_v2["metadata"]["updatedAt"] = ir_v1["metadata"]["updatedAt"] + 1
        w2 = await wic.aget_or_create_workflow_instance(
            "integration/republish.json", ir_v2, IRConverter.async_ir_to_workflow
        )
        assert w2 is not w1  # 内容变化 → miss

        # 新内容此后稳定命中新实例（不存在旧图窗口）
        w2_again = await wic.aget_or_create_workflow_instance(
            "integration/republish.json", ir_v2, IRConverter.async_ir_to_workflow
        )
        assert w2_again is w2


class TestConcurrentBranchAndAggregation:
    """分支/聚合最敏感路径的并发隔离（spec §9.2 补充测试项子项 1/2）。

    两个 fixture 均无 LLM：``workflow_branch.json`` 的分支条件为纯布尔
    表达式 ``(length(${node_start.systemFields.query}) > 10)``；
    ``workflow_aggregation.json`` 为 start → aggregation(first-non-null) →
    end 纯聚合流。分支路由经 Patch C/D（BranchRouter session 解析）——
    复用实例下并发执行时路由必须按各自 session 的输入走向。
    """

    @pytest.mark.asyncio
    async def test_concurrent_branch_routing_follows_each_session_input(self):
        """同一实例 4 路并发、长短 query 交替：各走各自分支，输出不串扰。"""
        wf = await (
            await IRConverter.async_ir_to_workflow(_load_ir(BRANCH_IR_PATH))
        ).instantiate()

        # 长度 ≤ 10 走 default 分支；> 10 走 if 分支
        queries = ["s1", "a-very-long-query-01", "s2", "a-very-long-query-02"]
        expected_nodes = [
            _BRANCH_DEFAULT_NODE,
            _BRANCH_LONG_NODE,
            _BRANCH_DEFAULT_NODE,
            _BRANCH_LONG_NODE,
        ]

        results = await asyncio.gather(*[
            _drive(wf, create_workflow_session(session_id=f"branch-{i}"), q)
            for i, q in enumerate(queries)
        ])

        for i, (query, chunks) in enumerate(zip(queries, results)):
            assert _streamed_message_node_ids(chunks) == {expected_nodes[i]}, (
                f"执行 {i}（query 长度 {len(query)}）分支路由错位——并发串扰"
            )
            assert _final_payload(chunks).get("answer") == query, (
                f"执行 {i} 终结帧 answer 未回显本路 query——并发串扰"
            )

    @pytest.mark.asyncio
    async def test_concurrent_aggregation_join_per_session(self):
        """同一实例 4 路并发：聚合（first-non-null）各汇聚各自输入，不串扰。"""
        wf = await (
            await IRConverter.async_ir_to_workflow(_load_ir(AGGREGATION_IR_PATH))
        ).instantiate()

        queries = ["agg-a", "agg-bb", "agg-ccc", "agg-dddd"]
        results = await asyncio.gather(*[
            _drive(wf, create_workflow_session(session_id=f"agg-{i}"), q)
            for i, q in enumerate(queries)
        ])

        shapes = []
        for i, (query, chunks) in enumerate(zip(queries, results)):
            assert _final_payload(chunks).get("answer") == query, (
                f"执行 {i} 聚合结果未汇聚本路输入——并发串扰"
            )
            shapes.append(_shape(chunks))
        # 四路事件序列骨架一致（同一聚合路径，无并发污染）
        assert all(s == shapes[0] for s in shapes[1:])


class TestCacheConcurrentAccess:
    @pytest.mark.asyncio
    async def test_concurrent_aget_on_same_key_yields_single_instance(self):
        """并发首调同一 key（build 含真实让出点）：锁内 miss 构建一次，其余转 hit。

        判别力依赖 build 工厂的让出点：``yielding_build`` 在构建前
        ``await asyncio.sleep(0)`` 让出，使 4 路 gather 真并发进入
        ``aget_or_create_workflow_instance`` 的 miss 窗口——锁生效时首个
        miss 构建、其余在锁后转 hit（同一对象）；去掉 ``async with _lock``
        时 4 路各自 miss → 4 个不同对象（反向验证记录见 task-16-report.md）。
        """
        ir_data = _load_ir()

        async def yielding_build(ir_data, **kwargs):
            await asyncio.sleep(0)  # 真实让出点：制造并发 miss 窗口
            return await IRConverter.async_ir_to_workflow(ir_data, **kwargs)

        instances = await asyncio.gather(*[
            wic.aget_or_create_workflow_instance(
                "integration/concurrent.json", ir_data, yielding_build
            )
            for _ in range(4)
        ])
        assert len({id(inst) for inst in instances}) == 1
