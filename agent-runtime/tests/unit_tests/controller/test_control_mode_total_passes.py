# coding: utf-8
# pylint: disable=protected-access
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""ControllerMode._stream_task_loop 连续不推进趟硬上限回归测试。

实测暴露：iterations 仅在分发到"GENERAL 型且名字未重复"的工作流时自增
（分发后置位）；插件/MCP/消息趟与同名工作流重复趟均不计数——此类任务
持续产出时 while iterations < max_task_iterations 恒真、无界自旋。守卫仅
统计"连续不推进 iterations"的趟（任一推进趟清零），触顶即断落既有触顶
终局路径；因此不覆盖任何 plan_config.max_iterations 配置预算——正常
推进任务始终按预算退出。
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


def _make_alternating_task_factory():
    """交替任务工厂：推进趟/不推进趟轮换，永不连续不推进。"""

    counter = [0]

    def factory():
        counter[0] += 1
        task = _make_plugin_task()
        if counter[0] % 2:
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
    """插件任务无 workflow_context（iterations 恒 0）：连续不推进趟触顶即断。"""
    mode = _make_mode(_make_plugin_task, max_task_iterations=10)

    with patch.object(cmode, "_MAX_IDLE_TASK_PASSES", 3):
        drained = await _drain(mode._stream_task_loop(_make_message()))

    assert _END_SENTINEL in drained  # 断路落入既有触顶终局路径
    assert mode.task_planner.calls == 3  # 连续 3 趟不推进后断，而非 10 趟预算


@pytest.mark.asyncio
async def test_general_workflow_budget_semantics_unchanged():
    """正常路径：GENERAL 工作流逐趟计数仍按 max_task_iterations 预算退出。"""
    mode = _make_mode(_make_general_task_factory(), max_task_iterations=2)

    drained = await _drain(mode._stream_task_loop(_make_message()))

    assert _END_SENTINEL in drained
    assert mode.task_planner.calls == 2  # 预算 2 趟用尽退出，守卫未介入
    assert mode.context_manager.controller_context.global_iteration_count == 2


@pytest.mark.asyncio
async def test_cap_never_cuts_productive_loops():
    """检视场景钉住：每趟都推进时，上限远小于预算也不截断。"""
    mode = _make_mode(_make_general_task_factory(), max_task_iterations=10)

    with patch.object(cmode, "_MAX_IDLE_TASK_PASSES", 2):
        drained = await _drain(mode._stream_task_loop(_make_message()))

    assert _END_SENTINEL in drained
    assert mode.task_planner.calls == 10  # 跑满预算 10 趟退出，上限未介入
    assert mode.context_manager.controller_context.global_iteration_count == 10


@pytest.mark.asyncio
async def test_idle_counter_reset_by_progress():
    """推进趟清零计数：间歇性不推进不会误触上限，按预算退出。"""
    mode = _make_mode(_make_alternating_task_factory(), max_task_iterations=6)

    with patch.object(cmode, "_MAX_IDLE_TASK_PASSES", 2):
        drained = await _drain(mode._stream_task_loop(_make_message()))

    assert _END_SENTINEL in drained
    # 预算按 iterations 计：推进 6 次需 11 趟（推进/不推进交替），守卫未介入
    assert mode.task_planner.calls == 11
    assert mode.context_manager.controller_context.global_iteration_count == 6
