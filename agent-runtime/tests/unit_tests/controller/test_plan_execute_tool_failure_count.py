# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""PlanExecuteMode._handle_tool_calls 失败计数的虚假失败回归测试。

实测暴露：返回体 answer 缺 error_code 键（或显式 null）时，
answer.get("error_code") 得 None，is_failed = (None != 0) 恒真——
业务成功的工具被逐轮计为失败，且 _tool_failure_count 为实例级、
跨 step 不清，累计到阈值（>=3）后被熔断器拉黑。本测试钉住：
缺键/显式 null 均按无错处理（计数清零），真失败仍正常累计。
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from jiuwen.controller.agent.control_mode import plan_execute_mode as pem
from jiuwen.orchestration.flow.stream.base import StreamData


def _stub_is_step_completed_by_llm(content, step):
    """完成判定桩：走"继续下一轮迭代"分支，聚焦计数断言。"""
    return False


def _stub_is_asking_user_input(content):
    """提问判定桩：不触发用户提问出口。"""
    return False


def _stub_inject_query(tool_calls):
    """query 注入桩：无操作。"""


def _make_mode():
    """构造最小 PlanExecuteMode，仅装配 _handle_tool_calls 触碰的成员。"""
    with patch.object(pem.PlanExecuteMode, "__init__", return_value=None):
        mode = pem.PlanExecuteMode()
    mode.task_id = "task-failcnt"
    mode.terminate = False
    mode._interrupted_by_workflow = False
    mode._tool_failure_count = {}
    mode._is_step_completed_by_llm = _stub_is_step_completed_by_llm
    mode._is_asking_user_input = _stub_is_asking_user_input
    mode._inject_query_to_workflow_calls = _stub_inject_query
    return mode


def _wire_execute(mode, answers):
    """_execute_tool_call 依次 yield 携带指定 answer 的 StreamData。"""

    async def fake_execute(tool_call, plan, step):
        for answer in answers:
            yield StreamData(
                code=0, msg="api_exec_data", data={"answer": answer}, execution_id="e1"
            )

    mode._execute_tool_call = fake_execute


def _llm_result():
    return {
        "tool_calls": [
            {"name": "doc_gen", "arguments": {}, "tool_call_id": "tc1"}
        ],
        "content": "",
    }


async def _drain(gen):
    return [item async for item in gen]


@pytest.mark.asyncio
async def test_missing_error_code_not_counted_as_failure():
    """answer 缺 error_code 键：按无错处理，不得累计失败。"""
    mode = _make_mode()
    mode._tool_failure_count["doc_gen"] = 2  # 预置历史计数，验证成功后清零
    _wire_execute(mode, [{"result": {"output": "ok"}}])

    await _drain(
        mode._handle_tool_calls(_llm_result(), SimpleNamespace(step_idx=1, description="d"), {})
    )

    assert mode._tool_failure_count["doc_gen"] == 0
    assert mode._current_step_tool_errors == []


@pytest.mark.asyncio
async def test_null_error_code_not_counted_as_failure():
    """error_code 显式 null：同样按无错处理。"""
    mode = _make_mode()
    _wire_execute(mode, [{"error_code": None, "result": {"output": "ok"}}])

    await _drain(
        mode._handle_tool_calls(_llm_result(), SimpleNamespace(step_idx=1, description="d"), {})
    )

    assert mode._tool_failure_count["doc_gen"] == 0


@pytest.mark.asyncio
async def test_real_failure_still_counted():
    """error_code 非 0：真失败仍正常累计（修复不得误伤熔断）。"""
    mode = _make_mode()
    _wire_execute(mode, [{"error_code": 1, "result": {"stderr": "boom"}}])

    await _drain(
        mode._handle_tool_calls(_llm_result(), SimpleNamespace(step_idx=1, description="d"), {})
    )

    assert mode._tool_failure_count["doc_gen"] == 1
    assert [e["tool"] for e in mode._current_step_tool_errors] == ["doc_gen"]
