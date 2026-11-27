# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""PlanExecuteMode._execute_single_step 循环守卫测试。

多智能体调单智能体规划模式实测暴露的 step 级死循环形态，逐一钉死：
1. 空响应被跳过（无工具调用、step 永不完成）→ 触顶强制终局，不再无界自旋；
2. 工具未找到（幻觉名每轮变化）→ 不算有效工具交接，不得触发切换重置；
3. 同错误熔断→重试→再熔断的循环由总轮数硬上限兜底，且 last_tool_name 保留；
4. 已解析工具的合法切换仍重置预算，切换风暴由总轮数硬上限兜底；
5. 触顶追加轮后仍未完成 → 终局退出（原等值判断 6、7、8…永不再命中）；
6. 正常完成路径不受影响（首轮 (step_done, content) 即退出，无强制终局）。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from jiuwen.controller.agent.control_mode import plan_execute_mode as pem


def _stub_build_step_hint(iteration, ctx):
    """step 提示桩：提示内容不参与断言。"""
    return "hint"


def _stub_log_step_iteration(*args, **kwargs):
    """迭代日志桩：静默，避免日志副作用。"""
    return None


def _make_mode():
    """构造最小 PlanExecuteMode，绕过复杂初始化（同既有测试范式）。"""
    with patch.object(pem.PlanExecuteMode, "__init__", return_value=None):
        mode = pem.PlanExecuteMode()
    mode.task_id = "task-loop"
    mode.terminate = False
    mode._tool_failure_count = {}
    mode.context_manager = MagicMock()
    mode._build_step_hint = _stub_build_step_hint
    mode._log_step_iteration = _stub_log_step_iteration
    return mode


def _make_step():
    return SimpleNamespace(step_idx=1, interrupted_workflow_name=None)


def _wire_llm(mode, results):
    """_call_llm_with_hint 循环返回 results 中的元素并记录调用次数。"""
    calls = []

    async def fake_call(hint, tools):
        calls.append(hint)
        return results[(len(calls) - 1) % len(results)]

    mode._call_llm_with_hint = fake_call
    return calls


def _wire_process(mode, items_by_call):
    """_process_llm_result 按调用次序 yield 预置条目（元组=完成信号）。

    按调用计数循环（step_iteration 会被切换/熔断重置，不能作索引），
    覆盖"永远不完成"形态。
    """
    seq = list(items_by_call)
    state = {"n": 0}

    async def fake_process(llm_result, step, step_iteration, plan):
        if seq:
            for item in seq[state["n"] % len(seq)]:
                yield item
            state["n"] += 1

    mode._process_llm_result = fake_process


async def _drain(gen):
    return [item async for item in gen]


def _tool_call_result(name):
    return {"has_tool_calls": True, "tool_calls": [{"name": name}]}


def _no_tool_result():
    return {"has_tool_calls": False, "tool_calls": []}


def _notices(mode):
    """收集写入 context 的强制终局通知（tool_call_id, 工具名）。"""
    return [
        (c.kwargs.get("tool_call_id"), c.kwargs.get("name"))
        for c in mode.context_manager.add_function_message.call_args_list
    ]


@pytest.mark.asyncio
async def test_empty_response_spin_terminates():
    """空响应轮（无工具调用、无内容、step 不完成）必须在触顶后终局。"""
    mode = _make_mode()
    calls = _wire_llm(mode, [_no_tool_result()])
    _wire_process(mode, [[]])  # 空响应被跳过：不产出任何条目

    await _drain(mode._execute_single_step(_make_step(), {"filtered_tools": [], "plan": {}}))

    assert len(calls) == 5  # max_iterations=5 轮后强制结束，不再自旋
    assert ("step_max_iterations", "unknown") in _notices(mode)


@pytest.mark.asyncio
async def test_unresolved_tool_churn_does_not_reset_budget():
    """幻觉工具名每轮变化不得触发切换重置——未解析的调用不是有效交接。"""
    mode = _make_mode()
    names = ["ghost_a", "ghost_b"]
    calls = _wire_llm(mode, [_tool_call_result(n) for n in names])
    # 每轮都 yield tool_not_found 事件（_execute_tool_call 兜底分支唯一站点）
    _wire_process(mode, [[SimpleNamespace(msg="tool_not_found")]])

    await _drain(mode._execute_single_step(_make_step(), {"filtered_tools": [], "plan": {}}))

    # 5 轮触顶 + 1 轮追加处理，随后终局；预算从未被切换重置
    assert len(calls) == 6
    assert ("step_max_iterations", "unknown") in _notices(mode)


@pytest.mark.asyncio
async def test_detector_cycle_bounded_by_total_rounds():
    """同错误 3 次熔断→重试→再熔断的循环由总轮数硬上限兜底，且名字保留。"""
    mode = _make_mode()
    calls = _wire_llm(mode, [_tool_call_result("t1")])
    # 每轮报同一错误且 step 不完成；熔断器每 3 轮动作一次并重置计数
    _wire_process(mode, [[(False, "ValueError: boom")]])

    await _drain(mode._execute_single_step(_make_step(), {"filtered_tools": [], "plan": {}}))

    # 熔断重置使 step_iteration 永远到不了 5，只能靠 _MAX_STEP_TOTAL_ROUNDS 收口
    assert len(calls) == pem._MAX_STEP_TOTAL_ROUNDS
    assert ("step_total_rounds_limit", "t1") in _notices(mode)  # last_tool_name 未被熔断清空


@pytest.mark.asyncio
async def test_resolved_switch_churn_bounded_by_total_rounds():
    """已解析工具的合法切换仍重置预算；切换风暴由总轮数上限兜底。"""
    mode = _make_mode()
    calls = _wire_llm(mode, [_tool_call_result("t1"), _tool_call_result("t2")])
    # 交替报不同错误签名，绕开同错误熔断
    _wire_process(mode, [[(False, "ValueError: a")], [(False, "TypeError: b")]])

    await _drain(mode._execute_single_step(_make_step(), {"filtered_tools": [], "plan": {}}))

    assert len(calls) == pem._MAX_STEP_TOTAL_ROUNDS
    # 第 101 轮在循环顶收口，last_tool_name 停在第 100 轮（偶数轮）的 t2
    assert ("step_total_rounds_limit", "t2") in _notices(mode)


@pytest.mark.asyncio
async def test_extra_iteration_then_terminal():
    """触顶追加轮后仍未完成必须终局（原等值判断追加后永不再命中）。"""
    mode = _make_mode()
    calls = _wire_llm(mode, [_tool_call_result("t1")])
    # 有工具调用但 step 始终不完成、无错误内容
    _wire_process(mode, [[SimpleNamespace(msg="progress")]])

    await _drain(mode._execute_single_step(_make_step(), {"filtered_tools": [], "plan": {}}))

    # 首轮 None→t1 合法切换重置一次预算：6 轮触顶 + 1 轮追加处理 = 7 次调用
    assert len(calls) == 7
    assert ("step_max_iterations", "t1") in _notices(mode)


@pytest.mark.asyncio
async def test_step_completes_normally_without_notices():
    """首轮即完成：无强制终局通知，不额外消耗 LLM 轮次。"""
    mode = _make_mode()
    calls = _wire_llm(mode, [_tool_call_result("t1")])
    _wire_process(mode, [[(True, "final answer")]])

    out = await _drain(mode._execute_single_step(_make_step(), {"filtered_tools": [], "plan": {}}))

    assert len(calls) == 1
    assert _notices(mode) == []
    assert out == []
