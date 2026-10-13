# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""CID（EI.ComplexIntentDetection）真实引擎集成测试（issue #1 第 1/2 项）。

覆盖 test_workflow_concurrent_interact_and_nesting.py 文档记录的最后缺口：
wrapper 路径的 ``sub_checkpoint_exists`` 以外层 session 判定（外层执行期间
checkpoint 恒存在）导致 fresh 执行被误判为恢复、子图输入走 InteractiveInput
通道、子图 start 节点拿不到输入（AttributeError）。

fixture 策略（无 LLM 环境可驱动）：

- **IntentDetection 打桩**：monkeypatch 类方法 ``invoke`` 返回固定
  ``classificationId=1`` → 恒走 ``branch_1``（挂子工作流的分支）；
- **子工作流 IR**：消息流（复用 workflow_message.json），经 monkeypatch
  storage provider 注入（绕过 obs/redis 加载链）——子图 message 帧回显
  ``用户输入：{query}`` 为并发隔离的内容级判别锚点。

判别：

1. **fresh 执行链路**（issue 第 1 项）：单路 fresh 执行 → 子图 message 帧回显
   本路 query、父图 workflow_final 的 answer 携带子图输出——误判恢复时子图
   输入被替换为 ``InteractiveInput(raw_inputs="")``，子图 start 节点对
   InteractiveInput 调 ``.get()`` 直接 AttributeError，以上断言全部不成立；
2. **并发隔离**（issue 第 2 项）：同一 CID 实例多路并发 fresh，各路子图
   回显各自 query（子工作流执行窗口 + 分支路由的并发串扰可观测面）。
"""
import asyncio
import json
from pathlib import Path

import pytest

# 先触发 patch 应用链（circular import 规避：引擎类后取）。
import jiuwen.serve.controllers.execution.ir_converter  # noqa: F401

from agent_runtime.common.config import settings
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.workflow import create_workflow_session

_IR_DIR = Path(__file__).resolve().parents[1] / "resource" / "ir_file"
MESSAGE_IR_PATH = _IR_DIR / "workflow_message.json"

# 分支路由：classificationId=1 → branch_1（挂子工作流）
_STUB_BRANCH_ID = 1
_STUB_BRANCH_NAME = "业务"


@pytest.fixture(autouse=True)
def _static_graph_mode(monkeypatch):
    """每用例强制 static_graph 模式并清空进程级实例缓存。"""
    monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


@pytest.fixture(autouse=True)
def _stub_intent_detection(monkeypatch):
    """IntentDetection 打桩：恒返回固定分支，免除 LLM 依赖。"""

    async def _fake_invoke(self, inputs, session, context, **kwargs):
        return {
            "classificationId": _STUB_BRANCH_ID,
            "result": _STUB_BRANCH_NAME,
            "reason": "stubbed",
            "name": _STUB_BRANCH_NAME,
        }

    monkeypatch.setattr(IntentDetection, "invoke", _fake_invoke)


class _FakeStorageProvider:
    """测试用 storage provider：ir_path → 子工作流 IR JSON 字符串。"""

    def __init__(self, ir_by_path: dict):
        self._ir_by_path = ir_by_path

    async def get_content(self, path):
        if path not in self._ir_by_path:
            raise KeyError(path)
        return self._ir_by_path[path]


def _patch_child_ir_loading(monkeypatch, child_ir_path=MESSAGE_IR_PATH):
    """monkeypatch storage provider：子工作流 IR 直接返回消息流 fixture。

    子图 end 的 result 引用改为 message 节点输出（默认回显 start.query，
    与本路 query 同值会削弱判别力；引用 message 输出后，子图最终输出
    ``用户输入：{query}`` 经 CID responseContent → 父图终帧，任何一环
    断裂（输入丢失/串扰/聚合失败）都会使终帧 answer 失真）。
    """
    import storage

    child_ir = json.loads(child_ir_path.read_text(encoding="utf-8"))
    for comp in child_ir.get("components", []):
        if comp.get("type") == "jiuwen.end":
            comp.setdefault("inputs", {}).setdefault("userFields", {})[
                "result"
            ] = "${node_1781166866717.result}"
    child_ir_json = json.dumps(child_ir, ensure_ascii=False)
    provider = _FakeStorageProvider({"integration/child_message.json": child_ir_json})
    monkeypatch.setattr(storage, "get_storage_provider", lambda: provider)


def _cid_parent_ir() -> dict:
    """含 EI.ComplexIntentDetection 节点的父图 IR。

    start → cid → end；cid 的 branch_1 挂子工作流（消息流，回显
    ``用户输入：{query}``），end 回显 cid 聚合输出（responseContent）。
    """
    return {
        "is_published": True,
        "workflowName": "cid-integration-parent",
        "workflowId": "wf-cid-integration-parent",
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
                "id": "node_cid",
                "type": "EI.ComplexIntentDetection",
                "outputs": {
                    "result": "",
                    "reason": "",
                    "name": "",
                    "classificationId": "",
                    "responseContent": "",
                },
                "configs": {
                    "name": "cid",
                    "intentDetectionContainerNodeId": "node_intent_container",
                    "branches": [
                        {"id": "branch_0", "catalog": "其他"},
                        {
                            "id": "branch_1",
                            "catalog": "业务",
                            "configs": {
                                "workflow_id": "wf-child-message",
                                "ir_path": "integration/child_message.json",
                            },
                        },
                    ],
                    "groups": {"result": ["${node_cid.responseContent}"]},
                },
                "inputs": {"input": "${node_start.systemFields.query}", "userFields": {}},
            },
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "configs": {
                    "responseMode": "directResponse",
                    "userFields": {
                        "inputs": [
                            {
                                "sourceType": "ref",
                                "description": "最终输出",
                                "id": "result",
                                "type": "string",
                                "required": False,
                            }
                        ],
                        "outputs": [],
                    },
                    "responseTemplate": "{{result}}",
                    "systemFields": {"inputs": [], "outputs": []},
                    "isStreamOut": True,
                    "enable_history": True,
                    "isStructMessage": False,
                },
                "inputs": {"userFields": {"result": "${node_cid.responseContent}"}},
            },
        ],
        "connections": [
            {"source": {"componentId": "node_start"}, "target": {"componentId": "node_cid"}},
            {"source": {"componentId": "node_cid"}, "target": {"componentId": "node_end"}},
        ],
    }


async def _drive(wf, session, query):
    """真实 stream 一路执行（query 为完整输入），收集全部 chunk。"""
    chunks = []
    async for chunk in wf.stream({"query": query}, session):
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


def _sub_workflow_echo_answers(chunks):
    """子图消息流的完整回显（message_end 帧的 answer，拼接后内容）。"""
    return [
        _frame_data(c).get("answer", "")
        for c in chunks
        if getattr(c, "type", None) == "message_end"
    ]


class TestCIDFreshExecution:
    """CID 嵌套子工作流 fresh 执行链路（issue 第 1 项——checkpoint 误判修复）。"""

    @pytest.mark.asyncio
    async def test_fresh_execution_drives_sub_workflow_with_real_input(self, monkeypatch):
        """fresh 执行：子图拿到真实输入（非 InteractiveInput 恢复通道）。

        判别：① 子图 message 帧回显本路 query（fresh 输入真实进入子图）；
        ② 父图 workflow_final 的 answer 携带子图输出（CID 聚合链路完整）。
        误判恢复时（sub_checkpoint_exists 恒 True）子图输入被替换为
        InteractiveInput(raw_inputs="")，子图 start 节点 AttributeError，
        ①② 均不成立。
        """
        _patch_child_ir_loading(monkeypatch)
        wf = await (await IRConverter.async_ir_to_workflow(_cid_parent_ir())).instantiate()

        chunks = await _drive(wf, create_workflow_session(session_id="cid-fresh"), "hello-cid")

        assert f"用户输入：hello-cid" in _sub_workflow_echo_answers(chunks), (
            "子工作流未回显本路 query——fresh 执行被误判为恢复、子图输入丢失"
        )
        assert _final_payload(chunks).get("answer") == "用户输入：hello-cid", (
            "父图终结帧未携带子工作流输出——CID 聚合链路损坏"
        )

    @pytest.mark.asyncio
    async def test_repeated_fresh_execution_no_residual(self, monkeypatch):
        """同实例两轮顺序 fresh 执行：第二轮子图重新执行且输入正确（无残留）。"""
        _patch_child_ir_loading(monkeypatch)
        wf = await (await IRConverter.async_ir_to_workflow(_cid_parent_ir())).instantiate()

        for i in range(2):
            chunks = await _drive(
                wf, create_workflow_session(session_id=f"cid-rep-{i}"), f"rep-{i}"
            )
            assert f"用户输入：rep-{i}" in _sub_workflow_echo_answers(chunks), (
                f"第 {i} 轮子工作流未回显本轮 query"
            )


class TestCIDConcurrentExecution:
    """CID 集成级并发（issue 第 2 项——LLM 打桩后的并发分支路由 + 子工作流窗口）。

    同一 CID 实例多路并发 fresh：各路子图回显各自 query。串扰面在
    IntentDetection 结果、分支选择、子工作流执行窗口三层。
    """

    @pytest.mark.asyncio
    async def test_concurrent_fresh_executions_isolated(self, monkeypatch):
        _patch_child_ir_loading(monkeypatch)
        wf = await (await IRConverter.async_ir_to_workflow(_cid_parent_ir())).instantiate()

        queries = [f"cid-{i}" for i in range(3)]
        results = await asyncio.gather(*[
            _drive(wf, create_workflow_session(session_id=f"cid-conc-{i}"), q)
            for i, q in enumerate(queries)
        ])

        for i, (query, chunks) in enumerate(zip(queries, results)):
            assert f"用户输入：{query}" in _sub_workflow_echo_answers(chunks), (
                f"执行 {i} 子工作流未回显本路 query——并发串扰或输入丢失"
            )
            assert _final_payload(chunks).get("answer") == f"用户输入：{query}", (
                f"执行 {i} 终结帧未携带本路子工作流输出——并发串扰"
            )
