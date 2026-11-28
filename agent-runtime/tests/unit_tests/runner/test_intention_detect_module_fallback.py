# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""WORKFLOW→LLM 细粒度回退时 _intent_workflow_user_fields 清空覆盖。

评审警告（PR #2735）：WORKFLOW 粗粒度识别输出非空 user_fields 但未解析出有效
intent_function 时，后续 LLM 细粒度回退会更新实际路由结果，却不会清空
_intent_workflow_user_fields；controller_planner._build_intent_stream_data()
只看 user_fields 非空就透传工作流原始结果，导致 SSE intent 事件与控制器实际
路由使用 LLM 结果不一致。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.controller.common.enum import IntentIdentificationMethod
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
)


def _idm() -> IntentionDetectModule:
    """构造绕过 __init__ 的 IntentionDetectModule stub，仅装回退路径依赖。"""
    idm = IntentionDetectModule.__new__(IntentionDetectModule)
    idm.llm = MagicMock()  # 非 None，确保进入 LLM 回退分支
    idm.context_manager = MagicMock()
    idm.context_manager.get_latest_user_content.return_value = "query"
    idm.plan_config = SimpleNamespace(
        intent_identification=SimpleNamespace(
            method=IntentIdentificationMethod.WORKFLOW,
            id="intent_wf",
        ),
        chat_history_max_turn=3,
    )
    idm._intent_workflow_user_fields = {}
    idm._intent_detected_this_turn = False
    idm.intent_id_to_function_map = {}
    idm.intent_function_2_category_map = {}
    return idm


@pytest.mark.asyncio
async def test_workflow_to_llm_fallback_clears_intent_workflow_user_fields():
    """WORKFLOW 返回非空 user_fields + 无效 intent_function → LLM 回退后字段必须清空。

    回退前 _intent_workflow_user_fields 为工作流原始输出（intent_id=None），
    若不清空，_build_intent_stream_data 会透传该 stale 结果，与实际 LLM 路由不一致。
    """
    idm = _idm()

    # WORKFLOW 粗粒度识别：输出非空 user_fields，但 intent_function 为 None
    stale_user_fields = {"intent_id": None, "candidate_intents": []}
    idm._detect_intent_with_workflow_method = AsyncMock(
        return_value=(None, [], stale_user_fields)
    )
    # 候选意图过滤为空 → 走默认 LLM 回退分支
    idm._filter_valid_candidate_intents = MagicMock(return_value=[])
    # LLM 细粒度回退返回有效意图
    idm._detect_intent_with_llm = AsyncMock(return_value="llm_intent")

    result = await idm._detect_intent_with_coarse_grained_method(
        active_workflows=[], task_id="task-1"
    )

    # 实际路由使用 LLM 结果
    assert result == "llm_intent"
    # 关键：回退后 user_fields 已清空，不残留工作流原始结果
    assert idm._intent_workflow_user_fields == {}
    # LLM 回退确实被调用
    idm._detect_intent_with_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_workflow_adopted_keeps_intent_workflow_user_fields():
    """WORKFLOW 返回有效 intent_function（无需 LLM 回退）→ 保留 user_fields 供 SSE 透传。"""
    idm = _idm()

    user_fields = {"intent_id": "5", "predMain": "售后"}
    idm._detect_intent_with_workflow_method = AsyncMock(
        return_value=("wf_x", None, user_fields)
    )
    # 不应进入回退，兜底 mock 防止误调用
    idm._detect_intent_with_llm = AsyncMock(return_value="should_not_used")

    result = await idm._detect_intent_with_coarse_grained_method(
        active_workflows=[], task_id="task-1"
    )

    # WORKFLOW 结果被采用
    assert result == "wf_x"
    # user_fields 保留（供 SSE 透传）
    assert idm._intent_workflow_user_fields is user_fields
    # 未触发 LLM 回退
    idm._detect_intent_with_llm.assert_not_awaited()
