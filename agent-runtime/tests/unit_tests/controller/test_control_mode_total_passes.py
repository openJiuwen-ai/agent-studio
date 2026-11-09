# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""ControllerMode._stream_task_loop 总趟数硬上限回归测试。

实测暴露：iterations 仅在分发到"GENERAL 型且名字未重复"的工作流时自增
（分发后置位）；插件/MCP/消息趟与同名工作流重复趟均不计数——此类任务
持续产出时 while iterations < max_task_iterations 恒真、无界自旋。本测试
钉住：总趟数单调计数触顶即断（落既有触顶终局路径），GENERAL 工作流
计数语义不受影响。
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from jiuwen.controller.agent.control_mode import control_mode as cmode
from jiuwen.controller.agent.control_mode.control_mode import ControllerMode
from jiuwen.controller.common.enum import WorkflowType
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.common.task import Task
from jiuwen.controller.common.task_type import TaskType

_END_SENTINEL = "END-WORKFLOW-SENTINEL"


def _stub_is_start_workflow_executed():
    """启动标记桩：未执行（首趟产出 CONTROLLER_START 流）。"""
    return False


def _make_message():
    """构造循环用最小消息（含 runtime_context 供 conversation_id 写入）。"""
    return Message(
        MessageType.USER_INPUT,
        "query",
        runtime_data={"runtime_context": SimpleNamespace(conversation_id="conv-1")},
    )


def _make_plugin_task():
    """插件任务：无 workflow_context，分发后不推进 iterations（病态趟型）。"""
    return Task(task_type=TaskType.PLUGIN_START)


def _make_general_task_factory():
    """GENERAL 工作流任务工厂：名字逐趟唯一，分发后正常推进 iterations。"""
    counter = [0]

    def factory():
        counter[0] += 1
        task = _make_plugin_task()
        task.workflow_context = SimpleNamespace(
            type=WorkflowType.GENERAL, workflow_name=f"wf-{counter[0]}"
        )
        return task

    return factory


class _FakePlanner:
    """规划器桩：记录调用数，每趟调用工厂产出任务。"""

    def __init__(self, make_task):
        self.calls = 0
        self._make_task = make_task

    async def stream_plan_task(self, message):
        self.calls += 1
        yield self._make_task()


class _FakeDispatcher:
    """分发器桩：原样包装任务，以新消息收尾驱动下一趟。"""

    @staticmethod
    def dispatch(final_task_or_message):
        return SimpleNamespace(task=final_task_or_message, last_message=_make_message())


async def _stub_process_streaming(task_execution):
    """任务执行流桩：回放 last_message 一个流项。"""
    yield task_execution.last_message


async def _stub_end_workflow(current_message):
    """触顶终局桩：产出哨兵，证明断路落入既有触顶终局路径。"""
    yield _END_SENTINEL


def _make_mode(make_task, max_task_iterations=10):
    """构造最小 ControllerMode，仅装配 _stream_task_loop 触碰的成员。"""
    with patch.object(ControllerMode, "__init__", return_value=None):
        mode = ControllerMode()
    mode.task_id = "task-ctrl-passes"
    mode.max_task_iterations = max_task_iterations
    mode.terminate = False
    mode.task_end = False
    mode.context_manager = SimpleNamespace(
        controller_context=SimpleNamespace(
            global_iteration_count=0, processed_workflow_names=set()
        ),
        is_start_workflow_executed=_stub_is_start_workflow_executed,
    )
    mode.task_planner = _FakePlanner(make_task)
    mode.task_dispatcher = _FakeDispatcher()
    mode.process_task_execution_streaming_message = _stub_process_streaming
    mode._execute_end_workflow_and_return_max_iterations_error = _stub_end_workflow
    return mode


async def _drain(gen):
    return [item async for item in gen]


@pytest.mark.asyncio
async def test_plugin_passes_capped():
    """插件任务无 workflow_context（iterations 恒 0）：总趟数触顶即断。"""
    mode = _make_mode(_make_plugin_task, max_task_iterations=10)

    with patch.object(cmode, "_MAX_TASK_TOTAL_PASSES", 3):
        drained = await _drain(mode._stream_task_loop(_make_message()))

    assert _END_SENTINEL in drained  # 断路落入既有触顶终局路径
    assert mode.task_planner.calls == 3  # 上限 3 趟后断，而非 10 趟预算


@pytest.mark.asyncio
async def test_general_workflow_budget_semantics_unchanged():
    """正常路径：GENERAL 工作流逐趟计数仍按 max_task_iterations 预算退出。"""
    mode = _make_mode(_make_general_task_factory(), max_task_iterations=2)

    drained = await _drain(mode._stream_task_loop(_make_message()))

    assert _END_SENTINEL in drained
    assert mode.task_planner.calls == 2  # 预算 2 趟用尽退出，总趟上限未介入
    assert mode.context_manager.controller_context.global_iteration_count == 2


@pytest.mark.asyncio
async def test_cap_dominates_when_smaller_than_budget():
    """两计数并存：上限小于预算时按总趟数断，GENERAL 计数保持推进。"""
    mode = _make_mode(_make_general_task_factory(), max_task_iterations=10)

    with patch.object(cmode, "_MAX_TASK_TOTAL_PASSES", 2):
        drained = await _drain(mode._stream_task_loop(_make_message()))

    assert _END_SENTINEL in drained
    assert mode.task_planner.calls == 2  # 总趟上限 2 先于预算 10 触发
    assert mode.context_manager.controller_context.global_iteration_count == 2
