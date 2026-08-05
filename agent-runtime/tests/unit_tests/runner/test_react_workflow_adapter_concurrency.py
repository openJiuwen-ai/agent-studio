# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for R-02 fix: ReactWorkflowAdapter per-call workflow instance isolation.

R-02 根因:同一 adapter 持有共享 workflow 实例,并发 invoke() 在共享实例的
compile()/stream() 上竞写,导致输出串线(发 A 回 B / 残缺)。
修复后 adapter 只存只读 ir_data,invoke() 每次自建 LazyWorkflow,各请求独立
_session/_graph。

本测试用 fake workflow 验证:并发调用同一 adapter 时,(1) 每次都构建新的 workflow
实例,(2) 各请求输出与各自输入一一对应、不串线。
"""

import asyncio
import sys
import types
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest


class _FakeIRConverter:
    """测试替身，避免加载 IRConverter 的可选检索/数据库依赖。"""

    @staticmethod
    async def async_ir_to_workflow(_ir_data):
        raise NotImplementedError


@pytest.fixture
def ir_converter_cls():
    module_name = "jiuwen.serve.controllers.execution.ir_converter"
    converter_module = types.ModuleType(module_name)
    converter_module.IRConverter = _FakeIRConverter
    with patch.dict(sys.modules, {module_name: converter_module}):
        yield _FakeIRConverter


@dataclass
class _Chunk:
    """模拟 stream chunk — adapter.invoke 只读 type/payload。"""
    type: str
    payload: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)


class _FakeWorkflow:
    """记录被 stream 时的 inputs,并把 query 回显成 workflow_final answer。"""

    def __init__(self):
        self.received_inputs: dict | None = None

    async def stream(self, *, inputs, session, stream_modes):
        # 拷贝一份,避免与调用方共享引用
        self.received_inputs = dict(inputs)
        query = inputs.get("query", "")
        yield _Chunk(type="workflow_final", payload={"answer": f"OK:{query}"})


class _FakeWorkflowMaybeFail:
    """query=='FAIL' 时在 stream 中抛错,否则回显。用于异常隔离测试。"""

    async def stream(self, *, inputs, session, stream_modes):
        query = inputs.get("query", "")
        if query == "FAIL":
            raise RuntimeError("simulated workflow stream failure")
        yield _Chunk(type="workflow_final", payload={"answer": f"OK:{query}"})


class TestReactWorkflowAdapterConcurrency:
    """R-02: 同一 adapter 的并发 invoke() 必须使用各自独立的 workflow 实例。"""

    @pytest.mark.asyncio
    async def test_concurrent_invokes_build_separate_instances_and_do_not_cross(
        self, ir_converter_cls
    ):
        """并发两调用各自构建独立 workflow 实例,输出不串线。"""
        from agent_runtime.runner.react_workflow_adapter import ReactWorkflowAdapter

        created: list = []
        entered = 0
        gate = asyncio.Event()

        async def fake_async_ir_to_workflow(ir_data, **kwargs):
            # 强制两调用同时进入构建窗口(gate 在第二个到达时打开),
            # 模拟 R02 复现里 B 卡进 A 窗口的并发场景。
            nonlocal entered
            entered += 1
            wf = _FakeWorkflow()
            created.append(wf)
            if entered >= 2:
                gate.set()
            await gate.wait()
            return wf

        with pytest.warns(DeprecationWarning, match="native WorkflowCard"):
            adapter = ReactWorkflowAdapter(
                ir_data={"workflowId": "w-r02"},
                card_id="card-r02",
                workflow_name="R02_ROOT_WORKFLOW",
                workflow_desc="R02 echo workflow",
                input_params={},
                user_fields_keys=[],
            )

        with patch("openjiuwen.core.workflow.create_workflow_session",
                   return_value=MagicMock()), \
             patch.object(ir_converter_cls, "async_ir_to_workflow", fake_async_ir_to_workflow):
            results = await asyncio.gather(
                adapter.invoke({"query": "R02_SESSION_A"}),
                adapter.invoke({"query": "R02_SESSION_B"}),
            )

        # (1) 并发两调用各构建了一个 workflow 实例,不复用共享实例
        assert len(created) == 2
        assert created[0] is not created[1]

        # (2) 输出与各自输入一一对应,不串线(发 A 不回 B)
        assert results[0] == {"answer": "OK:R02_SESSION_A"}
        assert results[1] == {"answer": "OK:R02_SESSION_B"}

        # (3) 各实例只收到自己的 query,未被另一并发请求覆盖
        queries_seen = {wf.received_inputs.get("query") for wf in created}
        assert queries_seen == {"R02_SESSION_A", "R02_SESSION_B"}

    @pytest.mark.asyncio
    async def test_invoke_uses_ir_data_not_shared_instance(self, ir_converter_cls):
        """invoke 每次都调 async_ir_to_workflow(self._ir_data),不持有共享实例。"""
        from agent_runtime.runner.react_workflow_adapter import ReactWorkflowAdapter

        async def fake_async_ir_to_workflow(ir_data, **kwargs):
            assert ir_data == {"workflowId": "w-r02"}  # 传的是只读 ir_data
            wf = _FakeWorkflow()
            return wf

        with pytest.warns(DeprecationWarning, match="native WorkflowCard"):
            adapter = ReactWorkflowAdapter(
                ir_data={"workflowId": "w-r02"},
                card_id="card-r02",
                workflow_name="wf",
                workflow_desc="d",
                input_params={},
                user_fields_keys=[],
            )

        # adapter 实例上不应残留任何共享 workflow 实例属性
        assert not hasattr(adapter, "_workflow_instance")

        with patch("openjiuwen.core.workflow.create_workflow_session",
                   return_value=MagicMock()), \
             patch.object(ir_converter_cls, "async_ir_to_workflow", fake_async_ir_to_workflow):
            result = await adapter.invoke({"query": "X"})

        assert result == {"answer": "OK:X"}

    @pytest.mark.asyncio
    async def test_failure_in_one_call_does_not_pollute_the_other(self, ir_converter_cls):
        """§9.3 异常隔离:一个调用 stream 抛错,不影响另一并发调用(独立实例+session)。"""
        from agent_runtime.runner.react_workflow_adapter import ReactWorkflowAdapter

        async def fake_async_ir_to_workflow(ir_data, **kwargs):
            return _FakeWorkflowMaybeFail()

        with pytest.warns(DeprecationWarning, match="native WorkflowCard"):
            adapter = ReactWorkflowAdapter(
                ir_data={"workflowId": "w-r02"},
                card_id="card-r02",
                workflow_name="wf",
                workflow_desc="d",
                input_params={},
                user_fields_keys=[],
            )

        with patch("openjiuwen.core.workflow.create_workflow_session",
                   return_value=MagicMock()), \
             patch.object(ir_converter_cls, "async_ir_to_workflow", fake_async_ir_to_workflow):
            results = await asyncio.gather(
                adapter.invoke({"query": "FAIL"}),
                adapter.invoke({"query": "OK"}),
                return_exceptions=True,
            )

        # 失败调用抛错,成功调用不受污染、正常返回自己的答案
        assert isinstance(results[0], Exception)
        assert results[1] == {"answer": "OK:OK"}
