# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""静态图复用真实引擎集成测试（spec §9.2；issue #1555 验收标准 2/3/5）。

真实 openjiuwen 引擎 + 真实 IR 构建（``workflow_message.json``：Start/Message/End
纯消息流，无 LLM 依赖，可真实 stream）：

- 同一 Workflow 实例 N 路并发 stream、不同 session → 输出互不串扰（验收 5）；
- static_graph 模式下缓存命中（同内容取同实例）与重发布失效（验收 2/3）；
- 缓存实例的执行事件序列与"每请求新建实例"（off 模式语义）逐帧等价。

断言策略为语义断言：每路执行产出完整终结帧（workflow_final）、终结帧
``answer`` 回显本路 query（串扰会直接把别路 query 带进来）、各路事件序列
骨架（chunk 类名 / type / node_id）一致、缓存同内容恒同对象。

已知缺口（本 fixture 不可驱动，Task 17 记入 spec §9.2 补充测试项）：
1. 缓存实例上的中断/恢复——需 Questioner 交互的 IR；
2. 嵌套子工作流复用——需含 SubWorkflow 的 IR；
3. CID（ComplexIntentDetection）并发 invoke 的 ``_state`` 共享写竞争
   （T14 遗留观察点）——需 ``EI.ComplexIntentDetection`` IR + LLM 支撑的
   IntentDetection；且该竞争的可观测面在分支/子工作流执行窗口，无 LLM
   时无法真实驱动（详见 task-16-report.md）。
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
from openjiuwen.core.workflow import create_workflow_session

IR_PATH = Path(__file__).resolve().parents[1] / "resource" / "ir_file" / "workflow_message.json"


@pytest.fixture(autouse=True)
def _static_graph_mode(monkeypatch):
    """每用例强制 static_graph 模式并清空进程级实例缓存。"""
    monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


def _load_ir():
    ir_data = json.loads(IR_PATH.read_text(encoding="utf-8"))
    ir_data["is_published"] = True
    return ir_data


async def _drive(wf, session, tag):
    """真实 stream 一路执行，收集全部 chunk。"""
    chunks = []
    async for chunk in wf.stream({"query": f"hello-{tag}"}, session):
        chunks.append(chunk)
    return chunks


def _final_payload(chunks):
    """取唯一 workflow_final 终结帧的 payload（缺失/重复即执行不完整）。"""
    finals = [c for c in chunks if getattr(c, "type", None) == "workflow_final"]
    assert len(finals) == 1, f"workflow_final 终结帧数量异常：{len(finals)}"
    return finals[0].payload


def _shape(chunks):
    """执行事件序列骨架：(chunk 类名, chunk.type, node_id)。"""
    return [
        (type(c).__name__, getattr(c, "type", None), getattr(c, "node_id", None))
        for c in chunks
    ]


class TestConcurrentIsolationOnSharedInstance:
    @pytest.mark.asyncio
    async def test_concurrent_streams_on_same_instance_are_isolated(self):
        """同一 Workflow 实例 4 路并发、不同 session：全部完成且输出互不串扰。

        串扰判别：每路终结帧 ``answer`` 必须回显本路 query（Patch A 前
        共享 Pregel/Vertex 时曾出现其中一路产出为空/错乱）。
        """
        wf = await (await IRConverter.async_ir_to_workflow(_load_ir())).instantiate()

        sessions = [create_workflow_session(session_id=f"sess-{i}") for i in range(4)]
        results = await asyncio.gather(*[
            _drive(wf, s, str(i)) for i, s in enumerate(sessions)
        ])

        shapes = []
        for i, chunks in enumerate(results):
            assert len(chunks) > 0, f"执行 {i} 输出为空——并发串扰"
            assert _final_payload(chunks).get("answer") == f"hello-{i}", (
                f"执行 {i} 终结帧 answer 未回显本路 query——并发串扰"
            )
            shapes.append(_shape(chunks))
        # 四路执行事件序列骨架一致：并发未污染任一执行的路径
        assert all(s == shapes[0] for s in shapes[1:])

        # 图实例的编译产物未被并发污染（Patch A：每执行独立 Pregel）
        graph = wf._internal._graph
        assert graph.pregel is not None

    @pytest.mark.asyncio
    async def test_repeated_execution_matches_fresh_build_output(self):
        """等价性：缓存实例的执行输出 == 每请求新建实例的输出（事件序列语义）。"""
        # 新建实例路径（off 模式语义）
        ir_fresh = _load_ir()
        wf_fresh = await (await IRConverter.async_ir_to_workflow(ir_fresh)).instantiate()
        out_fresh = await _drive(
            wf_fresh, create_workflow_session(session_id="fresh"), "fresh"
        )

        # 缓存实例路径（static_graph 语义）——两次取（第二次为复用）两次执行
        ir_reuse = _load_ir()
        wf_reuse = await wic.aget_or_create_workflow_instance(
            "integration/reuse.json", ir_reuse, IRConverter.async_ir_to_workflow
        )
        out1 = await _drive(wf_reuse, create_workflow_session(session_id="reuse-1"), "r1")
        wf_reuse2 = await wic.aget_or_create_workflow_instance(
            "integration/reuse.json", ir_reuse, IRConverter.async_ir_to_workflow
        )
        assert wf_reuse2 is wf_reuse  # 同内容命中同一 LazyWorkflow
        out2 = await _drive(wf_reuse2, create_workflow_session(session_id="reuse-2"), "r2")

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

        # 重发布：metadata.updatedAt 变更（Java 侧重发布必然更新该字段）→
        # canonical JSON 变化 → 内容 hash 变化 → 旧图不再复用
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


class TestCacheConcurrentAccess:
    @pytest.mark.asyncio
    async def test_concurrent_aget_on_same_key_yields_single_instance(self):
        """并发首调同一 key：锁内 miss 构建一次，其余转 hit——同一对象。"""
        ir_data = _load_ir()
        instances = await asyncio.gather(*[
            wic.aget_or_create_workflow_instance(
                "integration/concurrent.json", ir_data, IRConverter.async_ir_to_workflow
            )
            for _ in range(4)
        ])
        assert len({id(inst) for inst in instances}) == 1
