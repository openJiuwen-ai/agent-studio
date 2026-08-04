# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access  # 白盒单测:直接验证 _process_child_agents / _resolve_route_key / _get_handle_handoff_agent_intent 等内部方法
"""C-09 A.1:agent handoff 按 child.id 路由(允许同名子成员);所有识别入口统一返回 category。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.controller.common.config import AgentMetaData
from jiuwen.controller.task_planner.planners.controller_planner import ControllerPlanner
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    DEFAULT_INTENT,
    IntentionDetectModule,
)


def _child(cid, name, desc):
    return AgentMetaData(id=cid, name=name, description=desc)


def _msg(tid="t1"):
    return MagicMock(task_id=tid)


def _detector(children=(), maps=None):
    """只装 _resolve_route_key / _process_child_agents 需要的属性的 stub。"""
    m = IntentionDetectModule.__new__(IntentionDetectModule)
    m.plan_config = SimpleNamespace(child_agents_metadata=list(children))
    m.category_2_agent_name_map = {}
    m.agent_name_2_category_map = {}
    m.category_2_child_id_map = {}
    m.intent_id_to_child_category_map = {}
    m.intent_id_to_function_map = {}
    if maps:
        for key, val in maps.items():
            setattr(m, key, dict(val))
    return m


# ---------------------------------------------------------------------------
# _process_child_agents:建 category_2_child_id_map + intent_id_to_child_category_map
# ---------------------------------------------------------------------------

def test_process_child_agents_builds_category_and_intent_id_maps_for_dup_names():
    """两个 name=service 不同 id → category→id 与 intent_id→category 两条,键不同、id 唯一。"""
    children = [_child("a", "service", "售后"), _child("b", "service", "技术")]
    det = _detector(children)
    intents = []
    det._process_child_agents(intents, 0)
    assert det.category_2_child_id_map == {"分类0": "a", "分类1": "b"}
    assert det.intent_id_to_child_category_map == {"0": "分类0", "1": "分类1"}
    # intent_id_to_function_map 仍存 name(候选标签/LLM 输入不变)
    assert det.intent_id_to_function_map == {"0": "service", "1": "service"}
    assert len(intents) == 2


def test_process_child_agents_skips_child_without_name_or_desc():
    """缺 name 或 description 的 child 不进意图/映射(既有 guard,不变)。"""
    det = _detector([_child("a", None, "d"), _child("b", "n", "")])
    intents = []
    det._process_child_agents(intents, 0)
    assert intents == []
    assert det.category_2_child_id_map == {}
    assert det.intent_id_to_child_category_map == {}


# ---------------------------------------------------------------------------
# _resolve_route_key:AGENT→category,workflow/global→name,unknown→None
# ---------------------------------------------------------------------------

def test_resolve_route_key_agent_returns_category():
    """AGENT intent_id → category(优先 child_category_map),不再返回 name。"""
    det = _detector(maps={
        "intent_id_to_child_category_map": {"2": "分类2"},
        "intent_id_to_function_map": {"2": "service"},
    })
    assert det._resolve_route_key("2") == "分类2"


def test_resolve_route_key_workflow_returns_name():
    """workflow intent_id(不在 child_category_map)→ workflow_name。"""
    det = _detector(maps={
        "intent_id_to_child_category_map": {},
        "intent_id_to_function_map": {"5": "wf_x"},
    })
    assert det._resolve_route_key("5") == "wf_x"


def test_resolve_route_key_global_returns_name():
    """global intent_id → global_name。"""
    det = _detector(maps={
        "intent_id_to_child_category_map": {},
        "intent_id_to_function_map": {"9": "global_y"},
    })
    assert det._resolve_route_key("9") == "global_y"


def test_resolve_route_key_unknown_returns_none():
    det = _detector(maps={
        "intent_id_to_child_category_map": {},
        "intent_id_to_function_map": {},
    })
    assert det._resolve_route_key("99") is None


def test_resolve_route_key_coerces_non_str():
    """非 str intent_id(int)→ str 后查 map。"""
    det = _detector(maps={
        "intent_id_to_child_category_map": {"2": "分类2"},
        "intent_id_to_function_map": {},
    })
    assert det._resolve_route_key(2) == "分类2"


# ---------------------------------------------------------------------------
# _map_intent_id_to_function:AGENT→category,workflow→name,unknown→default
# ---------------------------------------------------------------------------

def test_map_intent_id_to_function_agent_returns_category():
    det = _detector(maps={
        "intent_id_to_child_category_map": {"2": "分类2"},
        "intent_id_to_function_map": {"2": "service"},
    })
    assert det._map_intent_id_to_function("2", "t") == "分类2"


def test_map_intent_id_to_function_workflow_returns_name():
    det = _detector(maps={
        "intent_id_to_child_category_map": {},
        "intent_id_to_function_map": {"5": "wf_x"},
    })
    assert det._map_intent_id_to_function("5", "t") == "wf_x"


def test_map_intent_id_to_function_unknown_returns_default():
    det = _detector(maps={
        "intent_id_to_child_category_map": {},
        "intent_id_to_function_map": {},
    })
    assert det._map_intent_id_to_function("99", "t") == DEFAULT_INTENT


# ---------------------------------------------------------------------------
# _get_handle_handoff_agent_intent:按 child.id 路由(不再 name first-match)
# ---------------------------------------------------------------------------

def _handoff_passthrough(child, _tid):
    return child


def _planner(children, cat2id, detector=None):
    p = ControllerPlanner.__new__(ControllerPlanner)
    p.intention_detect_module = detector or SimpleNamespace(category_2_child_id_map=dict(cat2id))
    p.plan_config = SimpleNamespace(child_agents_metadata=list(children))
    rule = MagicMock()
    rule.create_handoff_child_agent_task.side_effect = _handoff_passthrough
    p.rule_module = rule
    return p


def test_handoff_dup_name_routes_by_id_to_correct_child():
    """两个 name=service 不同 id → 按 category 路由到对的 child,不再 first-match。"""
    child_a = _child("a", "service", "售后")
    child_b = _child("b", "service", "技术")
    p = _planner([child_a, child_b], {"分类0": "a", "分类1": "b"})
    assert p._get_handle_handoff_agent_intent("分类1", _msg()) is child_b
    assert p._get_handle_handoff_agent_intent("分类0", _msg()) is child_a


def test_handoff_does_not_use_name_first_match():
    """detected 是 category;传 child name 不命中(category-keyed,非 name-keyed)。"""
    child_a = _child("a", "service", "d1")
    child_b = _child("b", "service", "d2")
    p = _planner([child_a, child_b], {"分类1": "b"})
    assert p._get_handle_handoff_agent_intent("service", _msg()) is None
    assert p._get_handle_handoff_agent_intent("分类1", _msg()) is child_b


def test_handoff_unknown_category_returns_none():
    p = _planner([_child("a", "service", "d")], {"分类0": "a"})
    assert p._get_handle_handoff_agent_intent("分类9", _msg()) is None


def test_handoff_empty_children_returns_none():
    p = _planner([], {"分类0": "a"})
    assert p._get_handle_handoff_agent_intent("分类0", _msg()) is None


# ---------------------------------------------------------------------------
# 端到端(非 LLM 识别路径):resolve_route_key(agent) → category → dispatch → handoff 对的 child
# ---------------------------------------------------------------------------

def test_end_to_end_non_llm_path_routes_dup_child_b():
    """验证非 LLM route key 能按 category handoff 到同名 child_b(不再 first-match)。"""
    child_a = _child("a", "service", "售后")
    child_b = _child("b", "service", "技术")
    det = _detector([child_a, child_b])
    det._process_child_agents([], 0)
    p = _planner([child_a, child_b], det.category_2_child_id_map, detector=det)

    route_key = det._resolve_route_key("1")  # 非 LLM 识别选中 child_b(intent_id=1)
    assert route_key == "分类1"
    assert route_key in p.intention_detect_module.category_2_child_id_map
    assert p._get_handle_handoff_agent_intent(route_key, _msg()) is child_b


# ---------------------------------------------------------------------------
# multi-layer:effective intent name 重复 → 回退细粒度 LLM(不约束内容)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_layer_dup_effective_intent_name_falls_back_to_llm():
    """effective intent name 重复 → multi-layer name-keyed 字典会塌,回退细粒度 LLM,不走 matcher(不约束内容,用户设相同意图名也正确路由)。"""
    det = _detector()
    det._build_intent_mappings_and_list = MagicMock(return_value=[
        {"name": "service", "description": "售后"},
        {"name": "service", "description": "技术"},
    ])
    det._detect_intent_with_llm = AsyncMock(return_value="分类3")
    det._prepare_multi_layer_id_input = MagicMock()  # 重名时不应被调

    result = await det._detect_with_multi_layer_intent_detection("t", [], False)

    assert result == "分类3"
    det._detect_intent_with_llm.assert_awaited_once()
    det._prepare_multi_layer_id_input.assert_not_called()


@pytest.mark.asyncio
async def test_multi_layer_unique_effective_intent_name_does_not_fall_back():
    """effective intent name 唯一 → 不回退,走原 multi-layer(不误触发 fallback)。"""
    det = _detector()
    det._build_intent_mappings_and_list = MagicMock(return_value=[
        {"name": "售后", "description": "a"},
        {"name": "技术", "description": "b"},
    ])
    det._detect_intent_with_llm = AsyncMock(return_value="SHOULD_NOT_BE_USED")
    det._prepare_multi_layer_id_input = MagicMock(return_value=MagicMock())
    det._resolve_route_key = MagicMock(return_value="分类3")
    det.multi_layer_id_cfg = MagicMock()
    match_result = MagicMock(is_matched=True, intent_id="3")

    with patch(
        "jiuwen.controller.task_planner.planning_modules."
        "intention_detect_module.IntentDetection"
    ) as mock_id_cls:
        mock_id_cls.return_value.invoke = AsyncMock(return_value=match_result)
        result = await det._detect_with_multi_layer_intent_detection("t", [], False)

    assert result == "分类3"
    det._detect_intent_with_llm.assert_not_awaited()
    det._prepare_multi_layer_id_input.assert_called_once()
