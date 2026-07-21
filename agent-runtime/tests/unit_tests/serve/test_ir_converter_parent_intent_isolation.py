# coding: utf-8
"""R-04: 父级 per-reference intent 覆盖不污染共享 IR memory cache。

回归对象:[ir_converter.py] `_recursive_create` 原地把父级 intent 覆盖写到
`async_ir_load` 返回的共享缓存子 IR 对象上 → 跨父级污染。修复方式:覆盖只应用到
per-config `current_metadata`(经 `_resolve_intent_fields`),不碰缓存对象。

覆盖:
1. ``_resolve_intent_fields`` 覆盖语义参数化(免 mock):证明 ``override.get(...) or IR``
   等价于旧实现的 ``if child_intent.get(name/description): 覆盖``(非空才覆盖)。
2. 转换器隔离:同一 shared IR 喂父A/父B,转换后 shared IR 与深拷贝快照相等(缓存不变),
   且各父级 ``AgentConfig.metadata.intent_*`` 按各自 child-ref 正确覆盖/回退(确定性预期)。
3. 跨父级不串线 + 顺序无关。

注:`_recursive_create` 是 `create_all_agents_config_list` 内的闭包,intent 写点之后紧接
`get_task_model` / `create_agent_config` 等 LLM 构建代码;故缓存不变性测试 mock 掉
`async_ir_load`(返回同一 shared dict)与下游构建器,聚焦 intent 解析 + 缓存不变。
覆盖语义本身测纯函数 `_resolve_intent_fields`,无需 mock。
"""

from __future__ import annotations

import copy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.controller.common.config import AgentConfig
from jiuwen.serve.controllers.execution.ir_converter import (
    IRConverter,
    _resolve_intent_fields,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# 共享子 IR:预置非空原始 intent_*(用于验证"非空才覆盖 / 空则回退原值")。
_SHARED_IR = {
    "agentId": "shared-0b57bc7a",
    "agentName": "R04_SHARED",
    "description": "shared-original",
    "intent_name": "shared_original_name",
    "intent_description": "shared_original_desc",
    "ir_path": "workflow/ir/shared/shared",
    "is_published": True,
    "configs": {"mode": "Controller", "agents": [], "sysPromptTemplate": "", "modelConfig": {}},
}


def _root_ir(parent_id: str, child_intent):
    """构造引用 shared 子的父 controller root IR。child_intent=None 表示不带 intent 字段。"""
    child_ref = {
        "id": "shared-0b57bc7a",
        "name": "R04_SHARED",
        "mode": "Controller",
        "node_id": "node_child_1",
        "ir_path": "workflow/ir/shared/shared",
    }
    if child_intent is not None:
        child_ref["intent"] = child_intent
    return {
        "agentId": parent_id,
        "agentName": parent_id,
        "description": "",
        "ir_path": f"workflow/ir/{parent_id}/{parent_id}",
        "is_published": True,
        "configs": {
            "mode": "Controller",
            "agents": [child_ref],
            "sysPromptTemplate": "",
            "modelConfig": {},
        },
    }


# mock 目标(ir_converter 模块内引用名)
_MOD = "jiuwen.serve.controllers.execution.ir_converter"


def _patches(shared_ir):
    """返回 mock 上下文管理器元组:async_ir_load 返回 shared_ir;校验/下游构建器旁路。"""
    async_ir_load = patch(f"{_MOD}.async_ir_load", new=AsyncMock(return_value=shared_ir))
    agent_ir_validator = patch(f"{_MOD}.AgentIrValidator", new=MagicMock())
    # get_task_model 同步返回 (task_model_stub, None) → model_configs 为 None → llm 跳过
    agent_ir_utils_mock = MagicMock()
    agent_ir_utils_mock.return_value.get_task_model.return_value = (MagicMock(), None)
    agent_ir_utils = patch(f"{_MOD}.AgentIrUtils", new=agent_ir_utils_mock)
    create_agent_config = patch(
        f"{_MOD}.IRConverter.create_agent_config",
        # side_effect 每次返回新实例,避免子/根 config 共用同一对象导致 metadata 互相覆盖
        new=AsyncMock(side_effect=lambda *a, **kw: AgentConfig()),
    )
    return async_ir_load, agent_ir_validator, agent_ir_utils, create_agent_config


async def _build(parent_id: str, child_intent, shared_ir):
    """跑 create_all_agents_config_list,mock 下游;返回 (all_configs, shared_ir)。"""
    root = _root_ir(parent_id, child_intent)
    p1, p2, p3, p4 = _patches(shared_ir)
    with p1, p2, p3, p4:
        configs, _info = await IRConverter.create_all_agents_config_list(root, "conv-test")
    return configs, shared_ir


def _child_metadata(configs):
    """all_configs[0] 是递归最先 append 的子(shared)config。"""
    return configs[0].metadata


# ---------------------------------------------------------------------------
# 1. 覆盖语义参数化(纯函数,免 mock)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "parent_intent, exp_name, exp_desc",
    [
        (None, "shared_original_name", "shared_original_desc"),
        ("not-a-dict", "shared_original_name", "shared_original_desc"),
        ({}, "shared_original_name", "shared_original_desc"),
        ({"name": "", "description": ""}, "shared_original_name", "shared_original_desc"),
        ({"name": "from_parent"}, "from_parent", "shared_original_desc"),
        ({"description": "desc_from_parent"}, "shared_original_name", "desc_from_parent"),
        ({"name": "n", "description": "d"}, "n", "d"),
    ],
)
def test_resolve_intent_fields_semantics(parent_intent, exp_name, exp_desc):
    name, desc = _resolve_intent_fields(_SHARED_IR, parent_intent)
    assert (name, desc) == (exp_name, exp_desc)


# ---------------------------------------------------------------------------
# 2. 转换器隔离:缓存不变 + 各父级 metadata 确定性
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_converter_does_not_mutate_shared_ir():
    """父A 带 intent 覆盖,转换后 shared IR 必须与快照完全相等(改前此处必失败)。"""
    shared = copy.deepcopy(_SHARED_IR)
    snapshot = copy.deepcopy(shared)
    await _build(
        "PARENT_A",
        {"name": "intent_from_A", "description": "A注入"},
        shared,
    )
    assert shared == snapshot


@pytest.mark.asyncio
async def test_parent_a_overrides_child_metadata():
    """A 的 child-ref 带 intent → shared 子的 metadata 用 A 的覆盖值。"""
    shared = copy.deepcopy(_SHARED_IR)
    configs, _ = await _build(
        "PARENT_A",
        {"name": "intent_from_A", "description": "A注入"},
        shared,
    )
    meta = _child_metadata(configs)
    assert meta.intent_name == "intent_from_A"
    assert meta.intent_description == "A注入"


@pytest.mark.asyncio
async def test_parent_b_real_form_falls_back_description():
    """真实编译形态(B child-ref 的 name 非空、description 为空):B 用自己 name,description 回退 shared 原值。"""
    shared = copy.deepcopy(_SHARED_IR)
    configs, _ = await _build(
        "PARENT_B",
        {"name": "B节点名", "description": ""},
        shared,
    )
    meta = _child_metadata(configs)
    assert meta.intent_name == "B节点名"
    assert meta.intent_description == "shared_original_desc"


@pytest.mark.asyncio
async def test_parent_no_intent_field_falls_back_both():
    """兼容形态:B child-ref 完全无 intent 字段 → name/desc 均回退 shared 原值。"""
    shared = copy.deepcopy(_SHARED_IR)
    configs, _ = await _build("PARENT_B", None, shared)
    meta = _child_metadata(configs)
    assert meta.intent_name == "shared_original_name"
    assert meta.intent_description == "shared_original_desc"


# ---------------------------------------------------------------------------
# 3. 跨父级不串线 + 顺序无关(同一 shared 对象模拟 memory cache 共享)
# ---------------------------------------------------------------------------


async def _run_both(order, shared):
    """按 order(如 ['A','B'])在同一个 shared 对象上顺序跑两父,返回 (meta_a, meta_b)。"""
    meta = {}
    for who in order:
        if who == "A":
            cfgs, _ = await _build(
                "PARENT_A", {"name": "intent_from_A", "description": "A注入"}, shared
            )
            meta["A"] = _child_metadata(cfgs)
        else:
            cfgs, _ = await _build(
                "PARENT_B", {"name": "B节点名", "description": ""}, shared
            )
            meta["B"] = _child_metadata(cfgs)
    return meta["A"], meta["B"], shared


@pytest.mark.asyncio
async def test_no_cross_parent_pollution_a_then_b():
    """A 先跑(会写缓存对象——改前),B 后跑读同一 shared:B 不应继承 A 的 description。"""
    shared = copy.deepcopy(_SHARED_IR)
    snapshot = copy.deepcopy(shared)
    meta_a, meta_b, shared = await _run_both(["A", "B"], shared)
    # B 用自己的 name + shared 原始 description(不是 A 的 "A注入")
    assert meta_b.intent_name == "B节点名"
    assert meta_b.intent_description == "shared_original_desc"
    assert meta_b.intent_description != meta_a.intent_description
    # shared 全程未被污染
    assert shared == snapshot


@pytest.mark.asyncio
async def test_order_independence():
    """A→B 与 B→A:shared 始终干净;各自 metadata 只由自己 child-ref + shared 原值决定。"""
    for order in (["A", "B"], ["B", "A"]):
        shared = copy.deepcopy(_SHARED_IR)
        snapshot = copy.deepcopy(shared)
        meta_a, meta_b, shared = await _run_both(order, shared)
        assert meta_a.intent_name == "intent_from_A"
        assert meta_a.intent_description == "A注入"
        assert meta_b.intent_name == "B节点名"
        assert meta_b.intent_description == "shared_original_desc"
        assert shared == snapshot
