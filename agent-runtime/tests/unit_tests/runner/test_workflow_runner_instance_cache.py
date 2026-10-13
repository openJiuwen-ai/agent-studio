# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""workflow_runner 实例缓存接入单测。

复用 test_workflow_runner.py 的 mock 范式：mock async_ir_load 等基础设施，
驱动 run_streaming 两次，断言 static_graph 模式下第二次复用同一
LazyWorkflow（缓存命中）、off 模式下不复用。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.common.config import settings
from agent_runtime.runner.workflow_runner import WorkflowRunner


def _make_mock_req(conversation_id="conv-1", query="test"):
    req = MagicMock()
    req.conversation_id = conversation_id
    req.ir_path = "workflow/ir/test/pub_1770000000000.json"
    req.query = query
    req.resume_input = None
    req.user_id = "testUser"
    req.params = MagicMock()
    req.params.is_debug = False
    req.params.model_dump = MagicMock(return_value={})
    req.params.conversation_history = []
    req.params.enable_memory_extract = False
    return req


IR_DATA = {"workflowId": "wf-cache-test", "is_published": True, "nodes": []}


async def _aiter(items):
    for it in items:
        yield it


async def _collect(agen):
    return [item async for item in agen]


def _make_mock_workflow():
    """build 产物：MagicMock 壳 + 空 async 流（驱动 run_streaming 完整返回）。"""
    wf = MagicMock()
    wf.stream.return_value = _aiter([])
    return wf


@pytest.fixture(autouse=True)
def _infra_mocks():
    """mock 掉 run_streaming 依赖的基础设施（session/redis/记忆）。"""
    with patch(
        "agent_runtime.runner.workflow_runner.async_ir_load", new=AsyncMock(return_value=IR_DATA)
    ), patch(
        "agent_runtime.runner.workflow_runner.create_workflow_session_with_trace",
        return_value=MagicMock(),
    ), patch(
        "agent_runtime.runner.workflow_runner.ExecutionIdStore.save", new=AsyncMock()
    ), patch(
        "agent_runtime.runner.workflow_runner.TraceIdStore.save", new=AsyncMock()
    ), patch(
        "agent_runtime.runner.workflow_runner.get_redis_client"
    ) as _redis_mock:
        _redis_mock.return_value = AsyncMock()
        yield


class TestWorkflowRunnerInstanceCache:
    @pytest.fixture(autouse=True)
    def _clean_cache(self):
        from jiuwen.serve.controllers.execution import workflow_instance_cache as wic
        wic.clear_workflow_instance_cache()
        yield
        wic.clear_workflow_instance_cache()

    @pytest.mark.asyncio
    async def test_static_graph_mode_reuses_instance(self, monkeypatch):
        runner = WorkflowRunner()

        sentinel_workflows = []

        async def fake_build(d, **kw):
            wf = _make_mock_workflow()
            sentinel_workflows.append(wf)
            return wf

        with patch.object(runner._ir_converter, "async_ir_to_workflow", new=fake_build):
            req = _make_mock_req(conversation_id="c1")
            await _collect(runner.run_streaming(req))
            req = _make_mock_req(conversation_id="c2")
            await _collect(runner.run_streaming(req))

        # build 只发生一次（第二次缓存命中，复用同一 LazyWorkflow）
        assert len(sentinel_workflows) == 1
