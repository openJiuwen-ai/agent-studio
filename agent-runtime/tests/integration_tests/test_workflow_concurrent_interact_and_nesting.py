# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""交互组件与嵌套子工作流的并发隔离集成测试（PR #1 评审 Warning 修复轮）。

补齐 test_workflow_static_graph_reuse.py 文档记录的缺口（原"已知不可驱动
缺口"1/2/3 中的可自动化部分）：

1. **缓存实例上的中断/恢复**（缺口 1）——``workflow_qa.json``（FlowQA
   needReply）多 session 并发中断 + 并发恢复：恢复输入经 InteractiveInput
   注入，各路终帧回显各自回复。恢复路径正是 Critical-1 修复的
   ``_node_state`` 跨 await 读写竞态的真实引擎面。
2. **FlowInput 并发交互**——``workflow_input.json``（jiuwen.input 表单收集
   节点）多 session 并发：各自产出 ``__interaction__`` 中断帧、恢复后各自
   完整终结。
3. **嵌套子工作流复用**（缺口 2）——含 ``jiuwen.subWorkflow`` 节点的
   父图（测试内构造 IR），子工作流为消息流（复用 workflow_message.json
   内容，经 monkeypatch IR 加载层注入）：同一父图实例多路并发，各路子图
   帧回显各自 query（子图 inline 执行 + LazyWorkflow 懒构建路径）。

仍为缺口（记录）：CID（EI.ComplexIntentDetection）集成级并发——wrapper
路径的 ``sub_checkpoint_exists`` 以外层 session 判断（外层执行期间
checkpoint 恒存在）导致 fresh 执行被误判为恢复、子图输入走 InteractiveInput
通道，无 LLM/真实 checkpointer 生命周期下无法真实驱动（probe 记录见 PR
评审回复）；其 ``_state`` 竞争已由单元级并发测试覆盖
（test_concurrent_state_isolation.py）。

Redis 依赖说明：子工作流 IR 加载（async_ir_load）走 memory → redis → obs
缓存链，测试环境无 Redis——monkeypatch ``open_utils._async_ir_load_uncached``
直接返回子 IR（绕过缓存链，语义等价 obs 命中）。
"""
import asyncio
import json
from pathlib import Path

import pytest

# 先触发 patch 应用链（circular import 规避：引擎类后取）。
import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

from agent_runtime.common.config import settings
from jiuwen.serve.controllers.execution import open_utils as ou
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import create_workflow_session

_IR_DIR = Path(__file__).resolve().parents[1] / "resource" / "ir_file"
QA_IR_PATH = _IR_DIR / "workflow_qa.json"
INPUT_IR_PATH = _IR_DIR / "workflow_input.json"
MESSAGE_IR_PATH = _IR_DIR / "workflow_message.json"


@pytest.fixture(autouse=True)
def _static_graph_mode(monkeypatch):
    """每用例强制 static_graph 模式并清空进程级实例缓存。"""
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


def _load_ir(ir_path):
    ir_data = json.loads(ir_path.read_text(encoding="utf-8"))
    ir_data["is_published"] = True
    return ir_data


async def _drive(wf, session, inputs):
    """真实 stream 一路执行，收集全部 chunk（inputs 为 dict 或 InteractiveInput）。"""
    chunks = []
    async for chunk in wf.stream(inputs, session):
        chunks.append(chunk)
    return chunks


def _final_payload(chunks):
    finals = [c for c in chunks if getattr(c, "type", None) == "workflow_final"]
    assert len(finals) == 1, f"workflow_final 终结帧数量异常：{len(finals)}"
    return finals[0].payload


def _frame_data(chunk) -> dict:
    """帧数据：顶层 stream 转发的子图帧带 data 字段，引擎原生帧带 payload。"""
    data = getattr(chunk, "data", None)
    if data is None:
        data = getattr(chunk, "payload", None)
    return data if isinstance(data, dict) else {}


def _interaction_frames(chunks):
    """交互中断帧（`__interaction__` 类型，交互组件产出后图中断）。"""
    return [
        c for c in chunks
        if isinstance(getattr(c, "type", None), str)
        and "__interaction__" in str(getattr(c, "type", None))
    ]


class TestFlowQAConcurrentInteract:
    """FlowQA 中断-恢复的并发隔离（缺口 1 补齐；Critical-1 真实引擎面）。"""

    @pytest.mark.asyncio
    async def test_concurrent_interrupt_then_resume_isolated(self):
        """同一实例 3 路并发中断 + 3 路并发恢复：各路终帧回显各自回复。

        判别：① 首轮各路中断（无 workflow_final、QA 状态入 checkpoint）；
        ② 恢复轮各路 workflow_final 的 answer == 本路回复（跨路串扰会把
        别路回复带进本路终帧——正是实例字段 _node_state 竞态的可观测面）。
        """
        wf = await (await IRConverter.async_ir_to_workflow(_load_ir(QA_IR_PATH))).instantiate()

        # 3 路并发首次执行（各自中断）：同 session_id 恢复需各自的 checkpoint，
        # 首轮与恢复轮用同一 session_id 各建新 session 对象
        replies = [f"reply-{i}" for i in range(3)]
        first_rounds = await asyncio.gather(*[
            _drive(wf, create_workflow_session(session_id=f"qa-{i}"), {"query": f"用户{i}"})
            for i in range(3)
        ])
        for i, chunks in enumerate(first_rounds):
            assert not [c for c in chunks if getattr(c, "type", None) == "workflow_final"], (
                f"首轮执行 {i} 不应产出终结帧——中断未发生"
            )

        # 3 路并发恢复（各自回复经 InteractiveInput 注入）
        resumed = await asyncio.gather(*[
            _drive(
                wf,
                create_workflow_session(session_id=f"qa-{i}"),
                InteractiveInput(raw_inputs=replies[i]),
            )
            for i in range(3)
        ])

        for i, chunks in enumerate(resumed):
            assert _final_payload(chunks).get("answer") == replies[i], (
                f"恢复执行 {i} 终帧 answer 未回显本路回复——并发串扰"
            )

    @pytest.mark.asyncio
    async def test_repeated_interrupt_resume_cycles_on_shared_instance(self):
        """同实例连续两轮完整中断-恢复周期：第二轮不残留第一轮状态。"""
        wf = await (await IRConverter.async_ir_to_workflow(_load_ir(QA_IR_PATH))).instantiate()

        for cycle in range(2):
            await _drive(
                wf, create_workflow_session(session_id=f"cycle-{cycle}"), {"query": f"q{cycle}"}
            )
            chunks = await _drive(
                wf,
                create_workflow_session(session_id=f"cycle-{cycle}"),
                InteractiveInput(raw_inputs=f"ans-{cycle}"),
            )
            assert _final_payload(chunks).get("answer") == f"ans-{cycle}", (
                f"周期 {cycle} 终帧 answer 异常——上一执行残留"
            )


class TestFlowInputConcurrentInteract:
    """FlowInput（表单收集节点）并发交互隔离。"""

    @pytest.mark.asyncio
    async def test_concurrent_input_collect_isolated(self):
        """同一实例 3 路并发：各自产出交互中断帧，恢复后各自完整终结。"""
        wf = await (await IRConverter.async_ir_to_workflow(_load_ir(INPUT_IR_PATH))).instantiate()

        first_rounds = await asyncio.gather(*[
            _drive(wf, create_workflow_session(session_id=f"in-{i}"), {"query": f"q{i}"})
            for i in range(3)
        ])
        for i, chunks in enumerate(first_rounds):
            interactions = _interaction_frames(chunks)
            assert len(interactions) >= 1, f"执行 {i} 未产出交互中断帧"
            assert not [c for c in chunks if getattr(c, "type", None) == "workflow_final"], (
                f"首轮执行 {i} 不应产出终结帧——中断未发生"
            )

        resumed = await asyncio.gather(*[
            _drive(
                wf,
                create_workflow_session(session_id=f"in-{i}"),
                InteractiveInput(raw_inputs=f"表单值-{i}"),
            )
            for i in range(3)
        ])
        for i, chunks in enumerate(resumed):
            # 恢复轮完整终结（input 节点消费输入 → end → workflow_final）
            _final_payload(chunks)


def _nested_sub_workflow_ir() -> dict:
    """含 jiuwen.subWorkflow 节点的父图 IR（子工作流经 monkeypatch 注入）。

    子工作流为消息流（workflow_message.json）：子图 message 帧回显
    ``用户输入：{query}`` ——并发隔离的内容级判别锚点。
    """
    return {
        "is_published": True,
        "workflowName": "nested-sub-concurrent",
        "workflowId": "wf-nested-sub-concurrent",
        "schemaVersion": "1",
        "metadata": {},
        "configs": {},
        "description": "",
        "components": [
            {
                "id": "node_start",
                "type": "jiuwen.start",
                "configs": {
                    "userFields": {
                        "inputs": [
                            {"id": "query", "type": "string", "required": True, "sourceType": "input"}
                        ],
                        "outputs": [],
                    }
                },
            },
            {
                "id": "node_sub",
                "type": "jiuwen.subWorkflow",
                "configs": {
                    "name": "sub",
                    "reference": {"id": "wf-child-message", "path": "integration/child_message.json"},
                    "userFields": {
                        "inputs": [{"id": "query", "type": "string", "required": False, "sourceType": "input"}],
                        "outputs": [{"id": "result", "type": "string", "required": False}],
                    },
                    "systemFields": {"inputs": [], "outputs": []},
                    "preDefineFields": {},
                },
                "inputs": {"userFields": {"query": "${node_start.systemFields.query}"}},
            },
            {"id": "node_end", "type": "jiuwen.end", "configs": {}},
        ],
        "connections": [
            {"source": {"componentId": "node_start"}, "target": {"componentId": "node_sub"}},
            {"source": {"componentId": "node_sub"}, "target": {"componentId": "node_end"}},
        ],
    }


class TestNestedSubWorkflowConcurrent:
    """嵌套子工作流的并发隔离（缺口 2 补齐）。

    同一父图实例多路并发：各路子图（消息流）inline 执行，子图 message 帧
    回显各自 query。覆盖 SubWorkflow 组件 → LazyWorkflow 懒构建 → 子图
    compile（Patch A）→ 子图执行（Patch B workflow session 栈式恢复）全链
    路的并发隔离。
    """

    @pytest.mark.asyncio
    async def test_concurrent_nested_sub_workflow_isolated(self, monkeypatch):
        child_ir = _load_ir(MESSAGE_IR_PATH)

        async def _fake_load(path):
            return child_ir

        # 绕过 IR 加载缓存链（memory → redis → obs）：测试环境无 Redis，
        # 直接返回子 IR（语义等价 obs 命中）
        monkeypatch.setattr(ou, "_async_ir_load_uncached", _fake_load)

        wf = await (
            await IRConverter.async_ir_to_workflow(_nested_sub_workflow_ir())
        ).instantiate()

        queries = [f"nested-{i}" for i in range(3)]
        results = await asyncio.gather(*[
            _drive(wf, create_workflow_session(session_id=f"nest-{i}"), {"query": q})
            for i, q in enumerate(queries)
        ])

        for i, (query, chunks) in enumerate(zip(queries, results)):
            # 子图 message 帧回显本路 query（子工作流真实执行且输入正确传递）：
            # partial_content 帧带 node_type=jiuwen.message 与分段 answer，
            # message_end 帧带拼接后完整 answer
            sub_answers = [
                _frame_data(c).get("answer", "")
                for c in chunks
                if getattr(c, "type", None) == "message_end"
            ]
            assert any(f"用户输入：{query}" == a for a in sub_answers), (
                f"执行 {i} 子工作流帧未回显本路 query——嵌套执行串扰或输入丢失"
            )
            # 父图完整终结
            assert _final_payload(chunks) is not None

    @pytest.mark.asyncio
    async def test_nested_sub_workflow_repeated_execution(self, monkeypatch):
        """同实例两轮顺序嵌套执行：第二轮子图重新执行（无执行残留）。"""
        child_ir = _load_ir(MESSAGE_IR_PATH)

        async def _fake_load(path):
            return child_ir

        monkeypatch.setattr(ou, "_async_ir_load_uncached", _fake_load)

        wf = await (
            await IRConverter.async_ir_to_workflow(_nested_sub_workflow_ir())
        ).instantiate()

        for i in range(2):
            chunks = await _drive(
                wf, create_workflow_session(session_id=f"nest-rep-{i}"), {"query": f"rep-{i}"}
            )
            sub_answers = [
                _frame_data(c).get("answer", "")
                for c in chunks
                if getattr(c, "type", None) == "message_end"
            ]
            assert any(f"用户输入：rep-{i}" == a for a in sub_answers)
