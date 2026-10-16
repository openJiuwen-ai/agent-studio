# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""workflow_loader 接入实例缓存单测（controller/agent-group 路径静态图复用）。

controller 路径的工作流加载入口是 ``ensure_openjiuwen_workflow_registered``：
它每请求 remove-and-reregister 一个 LazyWorkflow 壳。修复前壳是每请求新建的，
壳内 ``_workflow`` 缓存随壳一起丢弃，跨请求命中率恒为 0——每次请求都会完整
执行 ``build_openjiuwen_workflow_from_ir``。修复后改走
``aget_or_create_workflow_instance``，同一已发布 IR 复用同一壳。
"""
from unittest.mock import MagicMock

import pytest

from jiuwen.extension.wrapper.workflow_loader import (
    ensure_openjiuwen_workflow_registered,
)
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.runner import Runner


IR_PATH = "workflow/ir/wf-cache/pub_1770000000000.json"


def _published_ir() -> dict:
    """每次返回新 dict：模拟每请求从存储重新加载 IR。"""
    return {
        "workflowId": "wf-cache-test",
        "workflowName": "cache-test",
        "ir_path": IR_PATH,
        "is_published": True,
        "components": [],
    }


class _FakeShell:
    """LazyWorkflow 占位：只提供 add_workflow 读取的 card 属性。"""

    def __init__(self) -> None:
        self.card = MagicMock()


class _OkStub:
    """无 is_ok 属性的返回值：绕过 workflow_loader 的结果检查。"""


@pytest.fixture(autouse=True)
def _clean_cache():
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


@pytest.fixture(autouse=True)
def _stub_resource_mgr(monkeypatch):
    """隔离 openjiuwen 资源注册表——本测试只关心壳复用与构建次数。"""
    monkeypatch.setattr(
        Runner.resource_mgr, "remove_workflow", lambda *a, **kw: _OkStub()
    )
    monkeypatch.setattr(Runner.resource_mgr, "add_workflow", lambda *a, **kw: _OkStub())


@pytest.fixture
def builds(monkeypatch):
    """记录 IR -> Workflow 转换次数。

    ``ir_to_workflow`` 与 ``async_ir_to_workflow`` 是同一转换的两个入口，
    测试不预设走哪个，统一计数——断言的是"转换发生了几次"这一行为。
    """
    recorded = []

    async def fake_convert(ir_data, **kwargs):
        shell = _FakeShell()
        recorded.append(shell)
        return shell

    monkeypatch.setattr(IRConverter, "ir_to_workflow", fake_convert)
    monkeypatch.setattr(IRConverter, "async_ir_to_workflow", fake_convert)
    return recorded


class TestControllerPathInstanceCache:
    @pytest.mark.asyncio
    async def test_published_ir_reuses_shell_across_calls(self, builds):
        first = await ensure_openjiuwen_workflow_registered(
            _published_ir(), workflow_id="wf-cache-test", agent_id="agent-1"
        )
        second = await ensure_openjiuwen_workflow_registered(
            _published_ir(), workflow_id="wf-cache-test", agent_id="agent-1"
        )

        assert first is second, "同一已发布 IR 的两次加载应复用同一 LazyWorkflow 壳"
        assert len(builds) == 1, "第二次加载应命中实例缓存，不再新建壳"

    @pytest.mark.asyncio
    async def test_unpublished_ir_builds_every_call(self, builds):
        """未发布 IR 不缓存（跟随 IR 缓存惯例），每次新建壳。"""
        ir = _published_ir()
        ir["is_published"] = False

        first = await ensure_openjiuwen_workflow_registered(
            ir, workflow_id="wf-cache-test", agent_id="agent-1"
        )
        second = await ensure_openjiuwen_workflow_registered(
            ir, workflow_id="wf-cache-test", agent_id="agent-1"
        )

        assert first is not second
        assert len(builds) == 2

    @pytest.mark.asyncio
    async def test_downgraded_patch_builds_every_call(self, builds, monkeypatch):
        """static_graph_patch 降级时强制直建——跨请求复用静态图不再安全。"""
        monkeypatch.setattr(wic, "STATIC_GRAPH_DOWNGRADED", True)

        first = await ensure_openjiuwen_workflow_registered(
            _published_ir(), workflow_id="wf-cache-test", agent_id="agent-1"
        )
        second = await ensure_openjiuwen_workflow_registered(
            _published_ir(), workflow_id="wf-cache-test", agent_id="agent-1"
        )

        assert first is not second
        assert len(builds) == 2
