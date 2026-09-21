# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access  # 单元测试需直接验证 _task_maps/_status_maps 内部状态
"""TaskQueue.add_task 去重合并 input_data 的单元测试。

覆盖缺陷②修复：同 workflow_id 的未完成任务去重时，
仅在 RUNNING/FAILED 场景下合并新任务的 input_data 到旧任务，
PENDING 场景保留原始输入（避免连续入队时覆盖最早的待处理输入）。
"""
from unittest.mock import MagicMock

from jiuwen.controller.common.task import Task
from jiuwen.controller.common.task_type import TaskType, TaskSubType
from jiuwen.controller.task_planner.task_queue import TaskQueue, TaskStatus


def _make_workflow_context(workflow_id: str):
    """创建最小可用的 WorkflowContext mock。"""
    ctx = MagicMock()
    ctx.workflow_id = workflow_id
    ctx.workflow_name = f"wf_{workflow_id}"
    ctx.type = MagicMock()
    ctx.status = MagicMock()
    return ctx


def _make_task(workflow_id: str, input_data: dict, task_id: str = None) -> Task:
    """创建工作流任务。"""
    return Task(
        task_type=TaskType.WORKFLOW_START,
        input_data=input_data,
        workflow_context=_make_workflow_context(workflow_id),
        id=task_id or Task.generate_id(),
        sub_task_type=TaskSubType.STARTED_FROM_CONTROLLER,
    )


class TestTaskQueueDedupMergeInputData:
    """去重时 input_data 合并策略：RUNNING/FAILED 合并，PENDING 保留原始。"""

    @staticmethod
    def test_running_task_dedup_merges_query():
        """RUNNING 状态去重时仅更新 query 字段，保留 workflow_req_params 等其他字段。"""
        queue = TaskQueue()

        old_task = _make_task("wf-001", {
            "query": "查询电费账单",
            "workflow_req_params": {"key": "value"},
        })
        queue.add_task(old_task)
        # 模拟任务被取出执行（状态变为 RUNNING）
        queue.get_next_task()
        assert queue._status_maps[old_task.id] == TaskStatus.RUNNING

        # 用户回复后，controller 创建新任务
        new_task = _make_task("wf-001", {"query": "户号100023"})
        queue.add_task(new_task)

        # 旧任务被移回 pending，query 已更新，其他字段保留
        assert len(queue.pending_tasks) == 1
        assert queue.pending_tasks[0].id == old_task.id
        assert queue.pending_tasks[0].input_data["query"] == "户号100023"
        assert queue.pending_tasks[0].input_data["workflow_req_params"] == {"key": "value"}
        assert queue._status_maps[old_task.id] == TaskStatus.PENDING

    @staticmethod
    def test_failed_task_dedup_merges_all_fields():
        """FAILED 状态任务去重时，合并所有字段（重试可能携带更新后的参数）。"""
        queue = TaskQueue()

        old_task = _make_task("wf-002", {
            "query": "失败的旧输入",
            "extra_field": "preserved",
            "workflow_req_params": {"old": "value"},
        })
        queue.add_task(old_task)
        queue.get_next_task()
        queue.mark_task_failed(old_task.id)
        assert queue._status_maps[old_task.id] == TaskStatus.FAILED

        new_task = _make_task("wf-002", {
            "query": "重试的新输入",
            "workflow_req_params": {"new": "value"},
        })
        queue.add_task(new_task)

        assert queue.pending_tasks[0].id == old_task.id
        # query 和 workflow_req_params 被新值覆盖
        assert queue.pending_tasks[0].input_data["query"] == "重试的新输入"
        assert queue.pending_tasks[0].input_data["workflow_req_params"] == {"new": "value"}
        # 旧任务中未被新任务覆盖的字段保留
        assert queue.pending_tasks[0].input_data["extra_field"] == "preserved"

    @staticmethod
    def test_pending_task_preserves_original_input():
        """PENDING 状态任务去重时，应保留原始 input_data（连续入队不覆盖）。"""
        queue = TaskQueue()

        old_task = _make_task("wf-003", {"query": "最早的待处理输入"})
        queue.add_task(old_task)
        assert queue._status_maps[old_task.id] == TaskStatus.PENDING

        new_task = _make_task("wf-003", {"query": "最新输入"})
        queue.add_task(new_task)

        # PENDING 场景保留原始输入，不覆盖
        assert len(queue.pending_tasks) == 1
        assert queue.pending_tasks[0].id == old_task.id
        assert queue.pending_tasks[0].input_data == {"query": "最早的待处理输入"}

    @staticmethod
    def test_dedup_preserves_old_task_object():
        """去重应保留旧任务对象（同一引用），确保 _task_maps 等引用不断裂。"""
        queue = TaskQueue()

        old_task = _make_task("wf-004", {"query": "旧输入"})
        queue.add_task(old_task)
        queue.get_next_task()  # 变为 RUNNING
        old_task_id = old_task.id

        new_task = _make_task("wf-004", {"query": "新输入"})
        queue.add_task(new_task)

        # _task_maps 中仍是旧任务 ID
        assert old_task_id in queue._task_maps
        # 新任务 ID 不在 _task_maps 中（被丢弃）
        assert new_task.id not in queue._task_maps
        # pending 中的任务是旧任务对象
        assert queue.pending_tasks[0] is old_task

    @staticmethod
    def test_completed_task_not_merged():
        """已完成任务不应触发去重合并，新任务应正常入队。"""
        queue = TaskQueue()

        old_task = _make_task("wf-005", {"query": "已完成的任务"})
        queue.add_task(old_task)
        queue._status_maps[old_task.id] = TaskStatus.COMPLETED
        queue.completed_tasks.append(old_task)
        queue.pending_tasks.remove(old_task)

        new_task = _make_task("wf-005", {"query": "新任务"})
        queue.add_task(new_task)

        # 新任务正常入队（不与已完成任务去重）
        assert len(queue.pending_tasks) == 1
        assert queue.pending_tasks[0].id == new_task.id
        assert queue.pending_tasks[0].input_data == {"query": "新任务"}

    @staticmethod
    def test_different_workflow_id_no_dedup():
        """不同 workflow_id 的任务不应触发去重。"""
        queue = TaskQueue()

        task_a = _make_task("wf-A", {"query": "任务A"})
        task_b = _make_task("wf-B", {"query": "任务B"})
        queue.add_task(task_a)
        queue.add_task(task_b)

        assert len(queue.pending_tasks) == 2
        assert queue.pending_tasks[0].input_data == {"query": "任务A"}
        assert queue.pending_tasks[1].input_data == {"query": "任务B"}

    @staticmethod
    def test_no_existing_task_normal_enqueue():
        """无同 workflow_id 任务时正常入队，不触发去重逻辑。"""
        queue = TaskQueue()

        task = _make_task("wf-new", {"query": "首次任务"})
        queue.add_task(task)

        assert len(queue.pending_tasks) == 1
        assert queue.pending_tasks[0] is task
        assert task.id in queue._task_maps
        assert queue._status_maps[task.id] == TaskStatus.PENDING
