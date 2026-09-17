#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any, Dict

from jiuwen.common.log.base import logger
from jiuwen.controller.common.enum import WorkflowType
from jiuwen.controller.common.task import Task, TaskState
from jiuwen.controller.common.task_type import TaskType, TaskSubType
from jiuwen.controller.context_manager.workflow_context import WorkflowStatus


class TaskStatus(Enum):
    """任务状态枚举类"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class TaskQueueState:
    """任务队列状态类，用于TaskQueue的序列化与反序列化"""

    pending_tasks: List[TaskState]
    running_tasks: List[TaskState]
    completed_tasks: List[TaskState]
    failed_tasks: List[TaskState]
    task_maps: Dict[str, TaskState]
    status_maps: Dict[str, str]  # 存储TaskStatus枚举的字符串值


class TaskQueue:
    """任务队列，管理待处理、运行中和已完成的任务"""

    def __init__(self, context_manager=None):
        """初始化任务队列

        Args:
            state: 任务队列状态对象，用于恢复
            context_manager: 上下文管理器，用于获取完整的WorkflowContext
        """
        self.pending_tasks: List[Task] = []
        self.running_tasks: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.failed_tasks: List[Task] = []

        # 任务映射字典，用于快速查找和状态判断
        self._task_maps: Dict[str, Task] = {}
        self._status_maps: Dict[str, TaskStatus] = {}

        # 存储上下文管理器引用
        self.context_manager = context_manager

    def add_task(self, task: Task):
        """添加任务到队列

        Args:
            task: 要添加的任务
        """
        # 检查是否有相同workflow_id的任务存在
        if task.workflow_context and task.workflow_context.workflow_id:
            workflow_id = task.workflow_context.workflow_id
            # 遍历所有已存在的任务，查找相同workflow_id的未完成任务
            for existing_task in self._task_maps.values():
                if (
                    existing_task.workflow_context
                    and existing_task.workflow_context.workflow_id == workflow_id
                ):
                    existing_status = self._status_maps.get(existing_task.id)

                    # 只要不是已完成状态，就将任务移到pending队列末尾
                    if existing_status != TaskStatus.COMPLETED:
                        # 从当前队列中移除任务
                        if existing_status == TaskStatus.PENDING:
                            self.pending_tasks.remove(existing_task)
                        elif existing_status == TaskStatus.RUNNING:
                            self.running_tasks.remove(existing_task)
                        elif existing_status == TaskStatus.FAILED:
                            self.failed_tasks.remove(existing_task)

                        # 中断恢复/重试场景（RUNNING/FAILED）：用户回复以新任务
                        # input_data 到达，旧任务的 input_data 还是上轮 query，
                        # 必须更新输入，否则恢复轮 InteractiveInput 永远拿不到
                        # 当轮回复（缺陷②）。PENDING 场景保留原始输入，避免
                        # 同一 workflow 连续入队时最新输入静默覆盖最早的待处理输入。
                        if existing_status in (TaskStatus.RUNNING, TaskStatus.FAILED):
                            existing_task.input_data = task.input_data

                        # 移到pending队列末尾并更新状态
                        self.pending_tasks.append(existing_task)
                        self._status_maps[existing_task.id] = TaskStatus.PENDING
                        logger.info(
                            f"Moved existing task with workflow_id {workflow_id} to end of pending queue"
                        )
                        return
        self.pending_tasks.append(task)
        self._task_maps[task.id] = task
        self._status_maps[task.id] = TaskStatus.PENDING

    def get_latest_intent(self):
        """获取中断列表中"""
        if self.pending_tasks:
            pending_task = self.pending_tasks[-1]
            if pending_task.is_workflow_task():
                return pending_task.workflow_context.workflow_name
        return None

    def get_next_task(self) -> Optional[Task]:
        """获取下一个待处理任务，采用先进后出（LIFO）的栈顺序

        Returns:
            下一个待处理任务，如果队列为空则返回None
        """
        if not self.pending_tasks:
            return None

        # 修改为从末尾取任务（先进后出）
        task = self.pending_tasks.pop()  # 从列表末尾取出最后添加的任务
        self.running_tasks.append(task)
        self._status_maps[task.id] = TaskStatus.RUNNING
        return task

    def is_pending_task_empty(self):
        """
        查询pending任务队列是否为空

        Returns:
            pending任务队列是否为空
        """
        return len(self.pending_tasks) == 0

    def remove_current_task(self):
        """从运行中任务列表中移除当前任务（最先开始执行的任务）并标记为完成

        如果运行中没有任务，则不执行任何操作
        如果有多个运行中任务，默认移除第一个（最早添加的）任务

        Returns:
            bool: 是否成功移除任务
        """
        if self.running_tasks:
            completed_task = self.running_tasks.pop(0)
            self.completed_tasks.append(completed_task)
            self._status_maps[completed_task.id] = TaskStatus.COMPLETED
            return True
        return False

    def mark_task_failed(self, task_id: str, error=None) -> bool:
        """将任务标记为失败

        Args:
            task_id: 任务ID
            error: 错误信息

        Returns:
            bool: 是否成功标记任务
        """
        if task_id not in self._task_maps:
            return False

        status = self._status_maps.get(task_id)
        if status == TaskStatus.RUNNING:
            for i, task in enumerate(self.running_tasks):
                if task.id == task_id:
                    failed_task = self.running_tasks.pop(i)
                    if error:
                        failed_task.result = error
                    self.failed_tasks.append(failed_task)
                    self._status_maps[task_id] = TaskStatus.FAILED
                    return True
        elif status == TaskStatus.PENDING:
            for i, task in enumerate(self.pending_tasks):
                if task.id == task_id:
                    failed_task = self.pending_tasks.pop(i)
                    if error:
                        failed_task.result = error
                    self.failed_tasks.append(failed_task)
                    self._status_maps[task_id] = TaskStatus.FAILED
                    return True
        elif status == TaskStatus.COMPLETED:
            # 将已完成的任务标记为失败
            for i, task in enumerate(self.completed_tasks):
                if task.id == task_id:
                    failed_task = self.completed_tasks.pop(i)
                    if error:
                        failed_task.result = error
                    self.failed_tasks.append(failed_task)
                    self._status_maps[task_id] = TaskStatus.FAILED
                    return True

        return False

    def mark_task_completed(self, task_id: str) -> bool:
        """将任务标记为成功完成

        替代remove_task_by_id方法，可以将任何状态的任务标记为已完成

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功标记任务
        """
        if task_id not in self._task_maps:
            return False

        status = self._status_maps.get(task_id)
        if status == TaskStatus.COMPLETED:
            # 已经是完成状态，无需操作
            return True

        # 从当前状态队列中移除任务
        task = None
        if status == TaskStatus.RUNNING:
            for i, t in enumerate(self.running_tasks):
                if t.id == task_id:
                    task = self.running_tasks.pop(i)
                    break
        elif status == TaskStatus.PENDING:
            for i, t in enumerate(self.pending_tasks):
                if t.id == task_id:
                    task = self.pending_tasks.pop(i)
                    break
        elif status == TaskStatus.FAILED:
            for i, t in enumerate(self.failed_tasks):
                if t.id == task_id:
                    task = self.failed_tasks.pop(i)
                    break

        if task:
            self.completed_tasks.append(task)
            self._status_maps[task_id] = TaskStatus.COMPLETED
            return True

        return False

    def mark_task_pending(self, task_id: str) -> bool:
        """将任务设置为待处理状态

        可以将完成或失败的任务重新设置为待处理状态

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功设置任务状态
        """
        if task_id not in self._task_maps:
            return False

        status = self._status_maps.get(task_id)
        if status == TaskStatus.PENDING:
            # 已经是待处理状态，无需操作
            return True

        # 从当前状态队列中移除任务
        task = None
        if status == TaskStatus.RUNNING:
            for i, t in enumerate(self.running_tasks):
                if t.id == task_id:
                    task = self.running_tasks.pop(i)
                    break
        elif status == TaskStatus.COMPLETED:
            for i, t in enumerate(self.completed_tasks):
                if t.id == task_id:
                    task = self.completed_tasks.pop(i)
                    break
        elif status == TaskStatus.FAILED:
            for i, t in enumerate(self.failed_tasks):
                if t.id == task_id:
                    task = self.failed_tasks.pop(i)
                    break

        if task:
            self.pending_tasks.append(task)
            self._status_maps[task_id] = TaskStatus.PENDING
            return True

        return False

    def mark_all_tasks_completed(self) -> int:
        """将所有任务标记为已完成状态

        将所有待处理、运行中和失败的任务都标记为已完成状态

        Returns:
            int: 成功标记为已完成的任务数量
        """
        marked_count = 0

        # 处理待处理任务
        pending_tasks_copy = self.pending_tasks.copy()
        for task in pending_tasks_copy:
            self.pending_tasks.remove(task)
            self.completed_tasks.append(task)
            self._status_maps[task.id] = TaskStatus.COMPLETED
            marked_count += 1

        # 处理运行中任务
        running_tasks_copy = self.running_tasks.copy()
        for task in running_tasks_copy:
            self.running_tasks.remove(task)
            self.completed_tasks.append(task)
            self._status_maps[task.id] = TaskStatus.COMPLETED
            marked_count += 1

        # 处理失败任务
        failed_tasks_copy = self.failed_tasks.copy()
        for task in failed_tasks_copy:
            self.failed_tasks.remove(task)
            self.completed_tasks.append(task)
            self._status_maps[task.id] = TaskStatus.COMPLETED
            marked_count += 1

        logger.info(f"Marked {marked_count} tasks as completed")
        return marked_count

    def get_task_status(self, task_id: str) -> TaskStatus:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态: TaskStatus 枚举值
        """
        return self._status_maps.get(task_id, TaskStatus.UNKNOWN)

    def get_task_result(self, task_id: str) -> Any:
        """获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            任务结果
        """
        if task_id in self._task_maps:
            return self._task_maps[task_id].result
        return None

    def clear_all_tasks(self) -> int:
        """清理所有任务

        Returns:
            int: 清理的任务总数
        """
        # 记录清理前的任务总数
        cleared_count = len(self._task_maps)

        # 清空所有任务列表
        self.pending_tasks.clear()
        self.running_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()

        # 清空映射字典
        self._task_maps.clear()
        self._status_maps.clear()

        return cleared_count

    def get_state(self) -> TaskQueueState:
        """获取当前任务队列的状态对象

        Returns:
            TaskQueueState: 任务队列状态对象
        """
        # 将每个任务列表中的Task对象转换为TaskState
        pending_tasks_states = [task.get_state() for task in self.pending_tasks]
        running_tasks_states = [task.get_state() for task in self.running_tasks]
        completed_tasks_states = [task.get_state() for task in self.completed_tasks]
        failed_tasks_states = [task.get_state() for task in self.failed_tasks]

        # 将任务映射字典中的Task对象转换为TaskState
        task_maps_states = {
            task_id: task.get_state() for task_id, task in self._task_maps.items()
        }

        # 将状态映射中的枚举值转换为字符串
        status_maps_str = {k: v.value for k, v in self._status_maps.items()}

        # 创建并返回TaskQueueState对象
        return TaskQueueState(
            pending_tasks=pending_tasks_states,
            running_tasks=running_tasks_states,
            completed_tasks=completed_tasks_states,
            failed_tasks=failed_tasks_states,
            task_maps=task_maps_states,
            status_maps=status_maps_str,
        )

    def load_state(self, state: TaskQueueState):
        """从状态对象恢复任务队列实例

        Args:
            state: 任务队列状态对象
        """
        # 恢复各个任务列表
        self._restore_task_list("pending_tasks", state.pending_tasks)
        self._restore_task_list("running_tasks", state.running_tasks)
        self._restore_task_list("completed_tasks", state.completed_tasks)
        self._restore_task_list("failed_tasks", state.failed_tasks)

        # 恢复任务映射字典
        self._task_maps = {}
        for task_id, task_state in state.task_maps.items():
            # 查找是否在上面的列表中已经创建了该任务
            existing_task = None
            for task_list in [
                self.pending_tasks,
                self.running_tasks,
                self.completed_tasks,
                self.failed_tasks,
            ]:
                for task in task_list:
                    if task.id == task_id:
                        existing_task = task
                        break
                if existing_task:
                    break

            if existing_task:
                # 如果已经存在，使用已创建的对象
                self._task_maps[task_id] = existing_task
            else:
                # 否则创建新对象
                task = self._create_task_from_state(task_state)
                self._task_maps[task_id] = task

        # 恢复状态映射
        self._status_maps = {k: TaskStatus(v) for k, v in state.status_maps.items()}

    def _restore_task_list(self, list_name: str, task_states: List[TaskState]):
        """恢复特定任务列表

        Args:
            list_name: 任务列表名称
            task_states: 任务状态对象列表
        """
        task_list = []
        for task_state in task_states:
            task = self._create_task_from_state(task_state)
            task_list.append(task)

        setattr(self, list_name, task_list)

    def _create_task_from_state(self, task_state: TaskState) -> Task:
        """从TaskState创建Task对象，假设一定能找到对应的WorkflowContext

        Args:
            task_state: 任务状态对象

        Returns:
            Task: 创建的任务对象
        """
        # 处理workflow_context
        workflow_context = None
        if task_state.workflow_context and self.context_manager:
            # 从ContextManager获取完整的WorkflowContext
            workflow_id = task_state.workflow_context.workflow_id
            workflow_type = task_state.workflow_context.type
            workflow_context = self.context_manager.get_workflow_context_by_id(
                workflow_id, WorkflowType(workflow_type)
            )

            # 如果找到对应的WorkflowContext，但状态不同，更新其状态
            if workflow_context and task_state.workflow_context.status:
                # 确保状态是枚举对象
                status_value = task_state.workflow_context.status
                if isinstance(status_value, str):
                    try:
                        status_enum = WorkflowStatus(status_value)
                        # 只有当状态需要变化时才更新
                        if workflow_context.status != status_enum:
                            workflow_context.status = status_enum
                    except ValueError:
                        # 无效的状态值，保持原状态
                        pass

            # 如果没有找到对应的WorkflowContext，记录警告
            if not workflow_context:
                # 在实际代码中，您可能希望使用日志而非print
                logger.info(
                    f"Warning: WorkflowContext with ID {workflow_id} not found in ContextManager. "
                    f"Task {task_state.id} will have no workflow context."
                )

        # 创建Task对象
        task = Task(
            task_type=TaskType(task_state.task_type),
            input_data=task_state.input_data,
            workflow_context=workflow_context,  # 可能为None，如果未找到
            id=task_state.id,
            status=task_state.status,
            created_at=task_state.created_at,
            result=task_state.result,
            error=task_state.error,
            sub_task_type=TaskSubType(task_state.sub_task_type),
            is_restored=True,  # 标记为已恢复
        )

        return task
