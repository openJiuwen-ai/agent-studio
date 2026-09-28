# coding: utf-8
"""构建期子 IR 并发预取(async_ir_load_batch)的单元测试。

改造背景:ir_converter/utils 中多处"for 循环内逐个 await async_ir_load"
的串行 IO 往返,是多智能体/多工作流构建期(尤其冷启动回源 OBS)的主要
耗时。改造方式:各调用点先并发预取(async_ir_load_batch:去重 + 信号量
限流 + 异常策略),预取完成后转换/递归仍按原顺序串行执行。

覆盖:
1. helper 语义:按位对齐、去重共享引用、空列表、快速失败、
   return_exceptions 占位、并发上限(真并发 + 限流生效 + 默认值来自
   settings + <1 非法值双层拒绝)、失败占位共享引用。
2. 站点行为:process_workflows / process_global_intents 的对齐与过滤、
   extract_node_defs 的吞错语义、create_all_agents_config_list 的
   子 Agent 顺序、create_all_memory_config_list 的合并预取与递归顺序。
3. 语义不变量:子项顺序与串行版一致;失败语义(快速失败 vs 吞错继续)
   与串行版一致;批量返回共享引用(调用方不可原地修改纪律的前提);
   请求级缓存跨 batch 去重(async_ir_load 的 at-most-once 语义)。
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from pydantic import ValidationError

from agent_runtime.common.config import CacheSettings, settings
from agent_runtime.context.request_context import RequestContext, _request_ctx
from jiuwen.controller.common.config import AgentConfig
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load_batch
from jiuwen.serve.controllers.execution.utils import AgentIrUtils

_OPEN = "jiuwen.serve.controllers.execution.open_utils"
_CONV = "jiuwen.serve.controllers.execution.ir_converter"
_UTILS = "jiuwen.serve.controllers.execution.utils"


# ---------------------------------------------------------------------------
# 1. helper 语义
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_order_alignment():
    """不同路径:结果与输入按位对齐(以对象身份断言)。"""
    irs = {"p1": {"id": 1}, "p2": {"id": 2}, "p3": {"id": 3}}

    async def fake_load(path):
        return irs.get(path)

    with patch(f"{_OPEN}.async_ir_load", new=fake_load):
        results = await async_ir_load_batch(["p1", "p2", "p3"])

    assert len(results) == 3
    assert all(r is irs[p] for r, p in zip(results, ["p1", "p2", "p3"]))


@pytest.mark.asyncio
async def test_batch_dedup_shares_reference():
    """重复路径只加载一次,结果中共享同一对象(对齐缓存共享引用行为)。"""
    shared = {"id": "shared"}
    load_calls = []

    async def fake_load(path):
        load_calls.append(path)
        return shared

    with patch(f"{_OPEN}.async_ir_load", new=fake_load):
        results = await async_ir_load_batch(["a", "b", "a", "b"])

    assert load_calls == ["a", "b"]
    assert len(results) == 4
    assert results[0] is results[2] is shared
    assert results[1] is results[3] is shared


@pytest.mark.asyncio
async def test_batch_duplicate_failed_path_shares_placeholder():
    """return_exceptions=True + 重复失败路径:占位异常对象共享,只加载一次。

    去重发生在加载层,失败结果同样按 path 回填到所有重复位置——
    results[0] is results[2](同一异常实例),与成功路径的共享引用
    行为对称。
    """
    load_calls = []

    async def fake_load(path):
        load_calls.append(path)
        if path == "bad":
            raise ValueError("boom")
        return {"path": path}

    with patch(f"{_OPEN}.async_ir_load", new=fake_load):
        results = await async_ir_load_batch(
            ["bad", "ok", "bad"], return_exceptions=True
        )

    assert load_calls == ["bad", "ok"]
    assert isinstance(results[0], ValueError)
    assert results[0] is results[2]
    assert results[1] == {"path": "ok"}


@pytest.mark.asyncio
async def test_batch_unhashable_path_falls_back_to_no_dedup():
    """畸形不可哈希 path:去重退化为逐个加载,失败语义与串行版一致。"""
    calls = []

    async def fake_load(path):
        calls.append(path)
        return {"echo": path}

    bad = {"not": "hashable"}
    with patch(f"{_OPEN}.async_ir_load", new=fake_load):
        results = await async_ir_load_batch(["ok", bad, "ok", bad])

    # 退化后不去重:4 次逐个加载(串行版同样会对每个畸形 path 走加载)
    assert calls == ["ok", bad, "ok", bad]
    assert [r["echo"] for r in results] == ["ok", bad, "ok", bad]


@pytest.mark.asyncio
async def test_batch_empty_paths_returns_empty():
    """空列表:不发起任何加载,直接返回空。"""

    async def fail_load(path):
        raise AssertionError("should not be called")

    with patch(f"{_OPEN}.async_ir_load", new=fail_load):
        assert await async_ir_load_batch([]) == []


@pytest.mark.asyncio
async def test_batch_fail_fast_raises():
    """默认 return_exceptions=False:首个异常直接抛出(对齐串行首错即断)。"""

    async def fake_load(path):
        if path == "bad":
            raise ValueError("load failed")
        return {"path": path}

    with patch(f"{_OPEN}.async_ir_load", new=fake_load):
        with pytest.raises(ValueError, match="load failed"):
            await async_ir_load_batch(["good", "bad", "good2"])


@pytest.mark.asyncio
async def test_batch_return_exceptions_placeholder():
    """return_exceptions=True:失败项以异常对象占位,其余正常返回。"""
    ok1, ok3 = {"id": 1}, {"id": 3}

    async def fake_load(path):
        if path == "bad":
            raise ValueError("boom")
        return ok1 if path == "p1" else ok3

    with patch(f"{_OPEN}.async_ir_load", new=fake_load):
        results = await async_ir_load_batch(
            ["p1", "bad", "p3"], return_exceptions=True
        )

    assert results[0] is ok1
    assert isinstance(results[1], ValueError)
    assert results[2] is ok3


@pytest.mark.asyncio
async def test_batch_respects_max_concurrency():
    """信号量限流生效,且加载之间真实并发(串行时 max_active 恒为 1)。"""
    state = {"active": 0, "max_active": 0}

    async def fake_load(path):
        state["active"] += 1
        state["max_active"] = max(state["max_active"], state["active"])
        await asyncio.sleep(0.01)
        state["active"] -= 1
        return {"path": path}

    with patch(f"{_OPEN}.async_ir_load", new=fake_load):
        results = await async_ir_load_batch(
            [f"p{i}" for i in range(5)], max_concurrency=2
        )

    assert len(results) == 5
    assert state["max_active"] == 2


@pytest.mark.asyncio
async def test_batch_default_concurrency_from_settings():
    """不显式传 max_concurrency 时,上限取 settings.cache.ir_load_max_concurrency。

    env IR_LOAD_MAX_CONCURRENCY,默认 5。
    """
    state = {"active": 0, "max_active": 0}

    async def fake_load(path):
        state["active"] += 1
        state["max_active"] = max(state["max_active"], state["active"])
        await asyncio.sleep(0.01)
        state["active"] -= 1
        return {"path": path}

    with patch.object(settings.cache, "ir_load_max_concurrency", 2), patch(
        f"{_OPEN}.async_ir_load", new=fake_load
    ):
        results = await async_ir_load_batch([f"p{i}" for i in range(6)])

    assert len(results) == 6
    assert state["max_active"] == 2


@pytest.mark.asyncio
async def test_batch_rejects_non_positive_concurrency():
    """函数层 fail-fast:0 会使信号量 acquire 永久阻塞(挂起无报错),必须显式拒绝。"""
    for bad in (0, -1):
        with pytest.raises(ValueError, match="max_concurrency"):
            await async_ir_load_batch(["p1"], max_concurrency=bad)


def test_settings_reject_non_positive_ir_load_concurrency():
    """配置层 ge=1:env 误配 0/负数在启动期即 ValidationError,不带病上线。"""
    for bad in ("0", "-1"):
        with pytest.raises(ValidationError):
            CacheSettings(IR_LOAD_MAX_CONCURRENCY=bad)


@pytest.mark.asyncio
async def test_request_level_cache_dedup_across_batches():
    """请求级缓存跨 batch 去重:同一 path 在两次 batch 中只实际加载一次。

    async_ir_load 的 at-most-once-per-request 语义(ir_load_cache +
    asyncio.shield)在并发化后保持不变——batch 只是并发发起 async_ir_load,
    去重仍由请求级缓存兜底。
    """
    ir_p1, ir_p2 = {"id": "p1"}, {"id": "p2"}
    uncached = AsyncMock(side_effect=lambda path: {"p1": ir_p1, "p2": ir_p2}[path])

    token = _request_ctx.set(RequestContext(ir_load_cache={}))
    try:
        with patch(f"{_OPEN}._async_ir_load_uncached", new=uncached):
            first = await async_ir_load_batch(["p1", "p2"])
            second = await async_ir_load_batch(["p2", "p1"])
    finally:
        _request_ctx.reset(token)

    assert uncached.await_count == 2
    assert first[0] is ir_p1 and first[1] is ir_p2
    assert second[0] is ir_p2 and second[1] is ir_p1


# ---------------------------------------------------------------------------
# 2. 站点行为
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_workflows_alignment():
    """挂载工作流:批量预取按位对齐,Start/Normal 分类逻辑不变。"""
    ir_start, ir_normal = {"wf": "start"}, {"wf": "normal"}
    batch = AsyncMock(return_value=[ir_start, ir_normal])
    ir_data = {
        "configs": {
            "workflows": [
                {"ir_path": "wf/a", "workflow_type": "Start", "name": "wa"},
                {"ir_path": "wf/b", "workflow_type": "Normal", "name": "wb"},
            ]
        }
    }

    with patch(f"{_UTILS}.async_ir_load_batch", new=batch):
        configs = await AgentIrUtils.process_workflows(ir_data)

    batch.assert_awaited_once_with(["wf/a", "wf/b"])
    assert configs["start"].workflow_ir is ir_start
    assert configs["start"].config_name == "wa"
    assert [c.workflow_ir for c in configs["normal"]] == [ir_normal]
    assert configs["normal"][0].config_name == "wb"


@pytest.mark.asyncio
async def test_process_global_intents_filters_and_aligns():
    """全局意图:仅 Workflow 类型 handler 参与预取,Text 类型不占位。"""
    ir_g1, ir_g2 = {"wf": "g1"}, {"wf": "g2"}
    batch = AsyncMock(return_value=[ir_g1, ir_g2])
    ir_data = {
        "configs": {
            "global_intents": [
                {
                    "handler_type": "Workflow",
                    "handler": {"ir_path": "wf/g1", "name": "g1"},
                },
                {
                    "handler_type": "Text",
                    "handler": {"name": "text-handler"},
                },
                {
                    "handler_type": "Workflow",
                    "handler": {"ir_path": "wf/g2", "name": "g2"},
                },
            ]
        }
    }

    with patch(f"{_UTILS}.async_ir_load_batch", new=batch):
        result = await AgentIrUtils.process_global_intents(ir_data)

    batch.assert_awaited_once_with(["wf/g1", "wf/g2"])
    assert len(result) == 2
    assert result[0].workflow_ir is ir_g1
    assert result[0].config_name == "g1"
    assert result[1].workflow_ir is ir_g2


@pytest.mark.asyncio
async def test_extract_node_defs_swallow_load_failure():
    """子工作流定义提取:单个子 IR 加载失败被吞掉,其余与父定义不受影响。

    注:子 IR 无嵌套子流时,递归会以空列表再次调用批量接口(mock 用
    side_effect 按 paths 返回,空列表返回空,不影响断言)。
    """
    ir_child = {
        "workflowId": "wf-child",
        "components": [
            {"id": "node_c1", "name": "子节点", "type": "jiuwen.message"}
        ],
    }
    children_by_path = {
        "wf/child1": ir_child,
        "wf/child2": ValueError("child2 load failed"),
    }

    async def fake_batch(paths, **kwargs):
        return [children_by_path.get(p) for p in paths]

    batch = AsyncMock(side_effect=fake_batch)
    ir_parent = {
        "workflowId": "wf-parent",
        "components": [
            {"id": "node_p1", "name": "父节点", "type": "jiuwen.message"},
            {
                "id": "node_sub1",
                "name": "子流1",
                "type": "jiuwen.subWorkflow",
                "configs": {"reference": {"path": "wf/child1"}},
            },
            {
                "id": "node_sub2",
                "name": "子流2",
                "type": "jiuwen.subWorkflow",
                "configs": {"reference": {"path": "wf/child2"}},
            },
        ],
    }

    with patch(f"{_CONV}.async_ir_load_batch", new=batch):
        result = await IRConverter.extract_node_defs(ir_parent)

    non_empty_calls = [c for c in batch.await_args_list if c.args[0]]
    assert len(non_empty_calls) == 1
    assert non_empty_calls[0] == call(
        ["wf/child1", "wf/child2"], return_exceptions=True
    )
    # 成功子流的内部节点进入结果
    assert "wf-child" in result
    assert "node_c1" in result["wf-child"]
    # 失败子流被跳过,父流定义完整
    assert "wf-parent" in result
    assert "node_p1" in result["wf-parent"]


@pytest.mark.asyncio
async def test_extract_node_defs_children_order():
    """子工作流定义提取:多个子流全部合并,父流 key 最后写入(与串行版一致)。"""
    ir_child1 = {"workflowId": "wf-c1", "components": [{"id": "n1", "type": "t"}]}
    ir_child2 = {"workflowId": "wf-c2", "components": [{"id": "n2", "type": "t"}]}
    children_by_path = {"wf/c1": ir_child1, "wf/c2": ir_child2}

    async def fake_batch(paths, **kwargs):
        return [children_by_path.get(p) for p in paths]

    batch = AsyncMock(side_effect=fake_batch)
    ir_parent = {
        "workflowId": "wf-parent",
        "components": [
            {
                "id": "sub1",
                "type": "jiuwen.subWorkflow",
                "configs": {"reference": {"path": "wf/c1"}},
            },
            {
                "id": "sub2",
                "type": "jiuwen.subWorkflow",
                "configs": {"reference": {"path": "wf/c2"}},
            },
        ],
    }

    with patch(f"{_CONV}.async_ir_load_batch", new=batch):
        result = await IRConverter.extract_node_defs(ir_parent)

    assert list(result) == ["wf-c1", "wf-c2", "wf-parent"]


@pytest.mark.asyncio
async def test_create_all_agents_children_order():
    """多智能体:子 Agent 按原顺序递归,批量预取路径与子项顺序一致。"""
    ir_c1 = {
        "agentId": "c1",
        "agentName": "child-1",
        "ir_path": "ir/c1",
        "is_published": True,
        "configs": {"mode": "Controller"},
    }
    ir_c2 = {
        "agentId": "c2",
        "agentName": "child-2",
        "ir_path": "ir/c2",
        "is_published": True,
        "configs": {"mode": "Controller"},
    }
    root = {
        "agentId": "root",
        "agentName": "root",
        "ir_path": "ir/root",
        "is_published": True,
        "configs": {
            "mode": "Controller",
            "agents": [
                {"id": "c1", "ir_path": "ir/c1", "mode": "Controller"},
                {"id": "c2", "ir_path": "ir/c2", "mode": "Controller"},
            ],
        },
    }
    irs_by_path = {"ir/c1": ir_c1, "ir/c2": ir_c2}

    async def fake_batch(paths, **kwargs):
        return [irs_by_path.get(p) for p in paths]

    batch = AsyncMock(side_effect=fake_batch)
    agent_ir_utils_mock = MagicMock()
    agent_ir_utils_mock.return_value.get_task_model.return_value = (MagicMock(), None)

    with patch(f"{_CONV}.async_ir_load_batch", new=batch), patch(
        f"{_CONV}.AgentIrValidator", new=MagicMock()
    ), patch(f"{_CONV}.AgentIrUtils", new=agent_ir_utils_mock), patch(
        f"{_CONV}.IRConverter.create_agent_config",
        new=AsyncMock(side_effect=lambda *a, **kw: AgentConfig()),
    ):
        configs, _info = await IRConverter.create_all_agents_config_list(
            root, "conv-test"
        )

    # 预取路径与子项声明顺序一致(先 c1 后 c2);无子项的子 Agent 递归会
    # 以空列表再调一次批量接口,不参与断言
    non_empty_calls = [c for c in batch.await_args_list if c.args[0]]
    assert len(non_empty_calls) == 1
    assert non_empty_calls[0] == call(["ir/c1", "ir/c2"])
    # 转换顺序与串行版一致:子 config 先于根 config 追加
    assert [c.metadata.ir_path for c in configs] == ["ir/c1", "ir/c2", "ir/root"]


@pytest.mark.asyncio
async def test_memory_config_multiagents_merged_batch():
    """记忆配置收集:MultiAgents 的 agents+workflows 合并为一次预取。

    递归顺序保持"根 → agents → workflows"。
    """
    ir_a1 = {
        "agentId": "a1",
        "agentVersion": "0.6.0",
        "configs": {"memory": {"marker": "a1"}},
    }
    ir_a2 = {
        "agentId": "a2",
        "agentVersion": "0.6.0",
        "configs": {"memory": {"marker": "a2"}},
    }
    ir_w1 = {
        "workflowId": "w1",
        "workflowVersion": "0.6.0",
        "configs": {"memory": {"marker": "w1"}},
    }
    root = {
        "agentId": "root-ma",
        "agentName": "root",
        "agentVersion": "0.6.0",
        "configs": {
            "agents": [
                {"id": "a1", "ir_path": "ir/a1"},
                {"id": "a2", "ir_path": "ir/a2"},
            ],
            "workflows": [{"ir_path": "ir/w1"}],
            "memory": {"marker": "root"},
        },
    }
    batch = AsyncMock(return_value=[ir_a1, ir_a2, ir_w1])
    # 记录 from_config_dict 的调用顺序(每个节点带 memory 时调用一次)
    visit_order = []

    def fake_from_config_dict(cfg):
        visit_order.append(cfg["marker"])
        return MagicMock()

    memory_ir_config = MagicMock()
    memory_ir_config.from_config_dict.side_effect = fake_from_config_dict

    with patch(f"{_CONV}.async_ir_load_batch", new=batch), patch(
        f"{_CONV}.MemoryIrConfig", new=memory_ir_config
    ):
        all_configs = await IRConverter.create_all_memory_config_list(root)

    # 合并预取:agents 在前、workflows 在后,一次批量调用
    batch.assert_awaited_once_with(["ir/a1", "ir/a2", "ir/w1"])
    # 递归顺序:根 → a1 → a2 → w1(与串行版一致)
    assert visit_order == ["root", "a1", "a2", "w1"]
    assert len(all_configs) == 4


@pytest.mark.asyncio
async def test_memory_config_workflow_branch_only_subworkflow_loaded():
    """Workflow 分支:仅 SubWorkflow(workflowComposite)组件触发预取,普通组件不加载。

    注:该分支的组件类型过滤用 NodeType.SUB_WORKFLOW.value
    ("jiuwen.workflowComposite"),与 extract_node_defs 同时认
    "jiuwen.subWorkflow" 不同——测试数据须用前者,保持与原实现一致。
    """
    ir_child = {
        "workflowId": "wf-child",
        "workflowVersion": "0.6.0",
        "configs": {},
    }
    root = {
        "workflowId": "wf-root",
        "workflowVersion": "0.6.0",
        "components": [
            {"id": "n1", "type": "jiuwen.message"},
            {
                "id": "n2",
                "type": "jiuwen.workflowComposite",
                "configs": {"reference": {"path": "wf/child"}},
            },
            {
                "id": "n3",
                "type": "jiuwen.workflowComposite",
                "configs": {"reference": {}},
            },
        ],
        "configs": {},
    }
    batch = AsyncMock(return_value=[ir_child])

    with patch(f"{_CONV}.async_ir_load_batch", new=batch):
        all_configs = await IRConverter.create_all_memory_config_list(root)

    # n3 无 path 不加载;n1 非 SubWorkflow 不加载
    batch.assert_awaited_once_with(["wf/child"])
    assert all_configs == []
