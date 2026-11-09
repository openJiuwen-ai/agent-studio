# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""ToolUseMode._stream_task_loop 总趟数硬上限回归测试。

实测暴露：iterations 仅在规划器发 PLANNING 码时自增，队列回补、工具等待
等趟型不计数——病态场景（工具长期 pending/任务反复重入队列，状态机不回
PLANNING）下 while iterations < max_task_iterations 恒真、无界自旋。本测试
钉住：总趟数单调计数触顶即断（落 RetCode.FAILED），PLANNING 预算语义与
SUCCESS 即退不受影响。
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from jiuwen.controller.agent.control_mode import tool_use_mode as tum
from jiuwen.controller.agent.control_mode.tool_use_mode import ToolUseMode
from jiuwen.controller.common.enum import PlanAndExecuteCode, RetCode
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType


def _make_message():
    """构造循环用最小消息（USER_INPUT，带非空 runtime_data）。"""
    return Message(MessageType.USER_INPUT, "query", runtime_data={"task_id": "t"})


class _FakePlanner:
    """规划器桩：记录调用数，每趟按固定脚本产出结果。"""

    def __init__(self, script):
        self.calls = 0
        self._script = script

    async def stream_plan_task(self, message):
        self.calls += 1
        for item in self._script:
            yield item


class _FakeDispatcher:
    """分发器桩：返回以新消息收尾的执行结果，驱动下一趟。"""

    @staticmethod
    def dispatch(final_task_or_message):
        return SimpleNamespace(last_message=_make_message())


async def _stub_process_streaming(task_execution):
    """任务执行流桩：回放 last_message 一个流项。"""
    yield task_execution.last_message


def _make_mode(script, max_task_iterations=10):
    """构造最小 ToolUseMode，仅装配 _stream_task_loop 触碰的成员。"""
    with patch.object(ToolUseMode, "__init__", return_value=None):
        mode = ToolUseMode()
    mode.max_task_iterations = max_task_iterations
    mode.task_planner = _FakePlanner(script)
    mode.task_dispatcher = _FakeDispatcher()
    mode.process_task_execution_streaming_message = _stub_process_streaming
    return mode


async def _drain(gen):
    return [item async for item in gen]


@pytest.mark.asyncio
async def test_non_planning_passes_capped():
    """规划器从不发 PLANNING 码（iterations 恒 0）：总趟数触顶即断。"""
    mode = _make_mode([_make_message()], max_task_iterations=10)

    with patch.object(tum, "_MAX_TASK_TOTAL_PASSES", 3):
        drained = await _drain(mode._stream_task_loop(_make_message()))

    assert drained[-1] == RetCode.FAILED
    assert mode.task_planner.calls == 3  # 上限 3 趟后断，而非 10 趟预算


@pytest.mark.asyncio
async def test_planning_budget_semantics_unchanged():
    """正常路径：PLANNING 计数仍按 max_task_iterations 预算退出。"""
    mode = _make_mode(
        [PlanAndExecuteCode.PLANNING, _make_message()], max_task_iterations=2
    )

    drained = await _drain(mode._stream_task_loop(_make_message()))

    assert drained[-1] == RetCode.FAILED
    assert mode.task_planner.calls == 2  # 预算 2 趟用尽退出，总趟上限未介入


@pytest.mark.asyncio
async def test_success_exits_immediately():
    """规划器发 SUCCESS：立即成功返回，不进入任何预算/上限判定。"""
    mode = _make_mode([PlanAndExecuteCode.SUCCESS], max_task_iterations=10)

    drained = await _drain(mode._stream_task_loop(_make_message()))

    assert drained == [RetCode.SUCCESS]
    assert mode.task_planner.calls == 1


@pytest.mark.asyncio
async def test_cap_dominates_when_smaller_than_budget():
    """两计数并存：上限小于预算时按总趟数断，PLANNING 计数保持单调。"""
    mode = _make_mode(
        [PlanAndExecuteCode.PLANNING, _make_message()], max_task_iterations=10
    )

    with patch.object(tum, "_MAX_TASK_TOTAL_PASSES", 2):
        drained = await _drain(mode._stream_task_loop(_make_message()))

    assert drained[-1] == RetCode.FAILED
    assert mode.task_planner.calls == 2  # 总趟上限 2 先于预算 10 触发
