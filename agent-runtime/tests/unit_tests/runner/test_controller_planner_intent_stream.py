# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access  # 白盒单测:直接验证 _build_intent_stream_data 构造逻辑
"""intent SSE 事件构造与 stream() 轮内状态生命周期覆盖。

覆盖评审要求:
1. WORKFLOW 路径透传 user_fields(含短路:不回查 context_manager)
2. LLM fallback 构造(有 category+wf_ctx / 无 category / 无 detected_intent)
3. 空 user_fields 时落到 LLM 路径(不残留为透传 data)
4. adapter 契约:StreamCode.INTENT_MSG.value(1208) ↔ ConversationEvent.INTENT_MSG("intent")
5. stream() 每轮重置 _intent_workflow_user_fields(不残留上一轮)
6. stream() 识别异常路径不下发 intent 事件
7. stream() 即便 invoke 未重填 user_fields,stale 也不透传(落到 LLM 路径)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.task_planner.planners.controller_planner import ControllerPlanner
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.serve.controllers.execution.enum import ConversationEvent


def _planner(
    user_fields=None,
    latest_intent=None,
    wf_ctx=None,
    func2cat=None,
    id2func=None,
    task_id="task-1",
):
    """构造仅装 _build_intent_stream_data 依赖的 ControllerPlanner stub。

    Args:
        user_fields: idm._intent_workflow_user_fields(workflow 路径输出);None → 视作 {} (falsy)
        latest_intent: context_manager.get_latest_intent() 返回值
        wf_ctx: context_manager.get_workflow_context_by_name_and_type() 返回值
        func2cat: idm.intent_function_2_category_map
        id2func: idm.intent_id_to_function_map
    """
    p = ControllerPlanner.__new__(ControllerPlanner)
    p.task_id = task_id
    p.intention_detect_module = SimpleNamespace(
        _intent_workflow_user_fields=user_fields if user_fields is not None else {},
        intent_function_2_category_map=dict(func2cat or {}),
        intent_id_to_function_map=dict(id2func or {}),
    )
    cm = MagicMock()
    cm.get_latest_intent.return_value = latest_intent
    cm.get_workflow_context_by_name_and_type.return_value = wf_ctx
    p.context_manager = cm
    return p


# ---------------------------------------------------------------------------
# 路径1:WORKFLOW 透传 user_fields
# ---------------------------------------------------------------------------

def test_workflow_path_passes_through_user_fields():
    """有非空 user_fields → StreamData.data 直接透传该字典,code=INTENT_MSG。"""
    user_fields = {"intent_id": "5", "res": "wf_x", "predMain": "售后", "extra": 1}
    p = _planner(user_fields=user_fields, latest_intent="wf_x")
    sd = p._build_intent_stream_data()
    assert isinstance(sd, StreamData)
    assert sd.code == StreamCode.INTENT_MSG.value == 1208
    assert sd.msg == "intent"
    assert sd.data is user_fields  # 透传同一对象,不拷贝
    assert sd.execution_id == "task-1"


def test_workflow_path_short_circuits_without_querying_context():
    """有 user_fields 时不应回查 context_manager(不走 LLM 反查路径)。"""
    p = _planner(user_fields={"intent_id": "5"}, latest_intent="wf_x")
    p._build_intent_stream_data()
    p.context_manager.get_latest_intent.assert_not_called()
    p.context_manager.get_workflow_context_by_name_and_type.assert_not_called()


# ---------------------------------------------------------------------------
# 路径2:LLM fallback 构造
# ---------------------------------------------------------------------------

def test_llm_fallback_builds_full_payload_with_category_and_ctx():
    """空 user_fields + 有 detected_intent:category 命中 + wf_ctx 命中 → 完整 payload。"""
    p = _planner(
        user_fields={},
        latest_intent="wf_x",
        wf_ctx=SimpleNamespace(intent_name="售后流程", config_name="cfg1"),
        func2cat={"wf_x": "分类0"},
        id2func={"5": "wf_x"},
    )
    sd = p._build_intent_stream_data()
    assert sd.code == 1208
    data = sd.data
    assert data["intent_id"] == "5"          # 反查 intent_id_to_function_map
    assert data["res"] == "售后流程"          # pred_main 优先
    assert data["predMain"] == "售后流程"     # wf_ctx.intent_name
    assert data["message"] == "分类0:wf_x"    # f"{category}:{detected_intent}"
    assert data["abrFlag"] == ""
    assert data["rag_msg"] == ""
    assert data["intentResponse"]["responseData"][0]["answer"] == "wf_x"
    assert data["intentResponse"]["responseData"][0]["pageData"] == {"status": "", "type": ""}


def test_llm_fallback_without_category_mapping_keeps_res_as_detected():
    """无 category 映射 → intent_id 为空,res 回退为 detected_intent。"""
    p = _planner(
        user_fields=None,  # None 同样 falsy,落到 LLM 路径
        latest_intent="unknown_intent",
        wf_ctx=None,
        func2cat={},
        id2func={"5": "wf_x"},  # 无 category 时不进入反查循环
    )
    sd = p._build_intent_stream_data()
    data = sd.data
    assert data["intent_id"] == ""            # 无 category 不反查 intent_id
    assert data["res"] == "unknown_intent"    # pred_main 为空时回退 detected_intent
    assert data["predMain"] == ""             # 无 wf_ctx
    assert data["message"] == ""              # 无 category 不拼 message
    assert data["intentResponse"]["responseData"][0]["answer"] == "unknown_intent"


def test_llm_fallback_without_detected_intent_emits_empty_payload():
    """空 user_fields + 无 detected_intent → 全空 payload(不抛错)。"""
    p = _planner(user_fields={}, latest_intent=None, wf_ctx=None)
    sd = p._build_intent_stream_data()
    data = sd.data
    assert data["intent_id"] == ""
    assert data["res"] == ""
    assert data["predMain"] == ""
    assert data["message"] == ""
    assert data["abrFlag"] == ""
    assert data["rag_msg"] == ""
    assert data["intentResponse"]["responseData"][0]["answer"] == ""


# ---------------------------------------------------------------------------
# 识别失败/空输出不残留:空 user_fields 必须落到 LLM 路径
# ---------------------------------------------------------------------------

def test_empty_user_fields_does_not_leak_as_passthrough():
    """空 user_fields 必须落到 LLM 路径(构造 intentResponse 结构),
    而不是把空 dict 当作 WORKFLOW 透传 data。"""
    p = _planner(
        user_fields={},
        latest_intent="wf_x",
        wf_ctx=None,
        func2cat={},
        id2func={},
    )
    sd = p._build_intent_stream_data()
    # LLM 路径 data 含 intentResponse 键;WORKFLOW 透传 data 不会含此键
    assert "intentResponse" in sd.data
    assert sd.data["intentResponse"]["responseData"][0]["answer"] == "wf_x"
    # 透传路径会以原 dict 作为 data;此处 data 不是空 dict
    assert sd.data != {}


# ---------------------------------------------------------------------------
# adapter 契约:StreamCode.INTENT_MSG ↔ ConversationEvent.INTENT_MSG
# ---------------------------------------------------------------------------

def test_intent_stream_code_and_event_contract():
    """StreamData.code 经 item_code_to_conversation_event_type 映射为 ConversationEvent.INTENT_MSG。

    utils.item_code_to_conversation_event_type 是模块级字典(重导入成本高),
    这里断言它依赖的两个枚举契约值不变;一旦值漂移,utils 中的映射行会 KeyError,
    从而在更上层的集成测试暴露。
    """
    # planner 产出的 StreamData.code 即 adapter 字典的 key
    p = _planner(user_fields={"intent_id": "5"}, latest_intent=None)
    sd = p._build_intent_stream_data()
    assert sd.code == StreamCode.INTENT_MSG.value == 1208
    # adapter 字典期望映射到的 event
    assert ConversationEvent.INTENT_MSG.value == "intent"


# ---------------------------------------------------------------------------
# stream() 轮内状态生命周期:每轮重置 / 异常不下发 / stale 不透传
# ---------------------------------------------------------------------------

def _stream_planner(latest_intent=None, wf_ctx=None, func2cat=None, id2func=None):
    """构造可驱动 stream() 主分支(L194-200)的 ControllerPlanner stub。

    start_workflow=False 跳过 L171 等待块;rule_module.apply_rules 返回 None 跳过规则短路。
    _get_next_workflow 由调用方挂载(控制 _intent_detected_this_turn / 抛异常)。
    """
    p = ControllerPlanner.__new__(ControllerPlanner)
    p.task_id = "task-stream"
    p.plan_config = SimpleNamespace(start_workflow=False)
    p.last_message = None
    p._process_user_input = MagicMock()  # 跳过用户输入预处理
    p.rule_module = MagicMock()
    p.rule_module.apply_rules.return_value = None  # 不走规则短路
    p.intention_detect_module = SimpleNamespace(
        _intent_detected_this_turn=False,
        _intent_workflow_user_fields={},
        intent_function_2_category_map=dict(func2cat or {}),
        intent_id_to_function_map=dict(id2func or {}),
    )
    cm = MagicMock()
    cm.get_latest_intent.return_value = latest_intent
    cm.get_workflow_context_by_name_and_type.return_value = wf_ctx
    cm.is_task_end.return_value = False
    p.context_manager = cm
    return p


def _user_msg():
    """最小 USER_INPUT 消息(stream() 仅读 message_type/content)。"""
    return SimpleNamespace(message_type=MessageType.USER_INPUT, content="hi")


@pytest.mark.asyncio
async def test_stream_resets_intent_workflow_user_fields_each_turn():
    """stream() 主分支每轮入口清空 _intent_workflow_user_fields(不残留上一轮)。"""
    p = _stream_planner(latest_intent="wf_x")
    # 模拟上一轮残留
    p.intention_detect_module._intent_workflow_user_fields = {"intent_id": "stale"}

    async def _noop_next_workflow(_message):
        # invoke 未把 _intent_detected_this_turn 置 True(如指定意图/LATEST 分支)
        return None

    p._get_next_workflow = _noop_next_workflow

    yielded = [item async for item in p.stream(_user_msg())]

    # 无 intent 事件下发(本轮未识别)
    assert yielded == []
    # 关键:字段已被 L196 清空,不再残留上一轮值
    assert p.intention_detect_module._intent_workflow_user_fields == {}


@pytest.mark.asyncio
async def test_stream_does_not_yield_intent_event_when_detection_raises():
    """识别异常(经 _get_intent_based_workflow re-raise 为 JiuWenBaseException)时,
    stream() 不下发 intent 事件;且字段已在抛出前被 L196 清空。"""
    p = _stream_planner(latest_intent="wf_x")
    p.intention_detect_module._intent_workflow_user_fields = {"intent_id": "stale"}

    async def _raising_next_workflow(_message):
        # 模拟 invoke 内 L396 置 True 后识别抛异常
        p.intention_detect_module._intent_detected_this_turn = True
        raise JiuWenBaseException(1000, "intent detection boom")

    p._get_next_workflow = _raising_next_workflow

    yielded = []
    with pytest.raises(JiuWenBaseException):
        async for item in p.stream(_user_msg()):
            yielded.append(item)

    # 异常前未下发任何 intent 事件
    assert yielded == []
    # 字段已在 L196 重置(抛出前完成)
    assert p.intention_detect_module._intent_workflow_user_fields == {}


@pytest.mark.asyncio
async def test_stream_does_not_emit_stale_when_invoke_leaves_user_fields_empty():
    """评审最小复现的反例:即便 invoke 走非 WORKFLOW 路径未重填 user_fields,
    L196 已先行清空 → _build_intent_stream_data() 落到 LLM 路径,用 get_latest_intent() 的 "current",
    不透传上一轮 "previous"。

    无 L196 重置时此用例会失败:data 会等于 {"intent_id": "previous"}(透传)。
    """
    p = _stream_planner(
        latest_intent="current",
        wf_ctx=None,
        func2cat={},
        id2func={},
    )
    # 上一轮残留
    p.intention_detect_module._intent_workflow_user_fields = {"intent_id": "previous"}

    async def _llm_path_next_workflow(_message):
        # invoke 跑了(置 True),但走非 WORKFLOW 路径,未碰 _intent_workflow_user_fields
        p.intention_detect_module._intent_detected_this_turn = True
        return None

    p._get_next_workflow = _llm_path_next_workflow

    yielded = [item async for item in p.stream(_user_msg())]

    # 下发了 1 个 intent 事件
    assert len(yielded) == 1
    sd = yielded[0]
    assert isinstance(sd, StreamData)
    # 不透传上一轮 stale
    assert sd.data != {"intent_id": "previous"}
    # 落到 LLM 路径:含 intentResponse,answer 为本轮 "current"
    assert "intentResponse" in sd.data
    assert sd.data["intentResponse"]["responseData"][0]["answer"] == "current"
    # 字段已被 L196 清空
    assert p.intention_detect_module._intent_workflow_user_fields == {}
