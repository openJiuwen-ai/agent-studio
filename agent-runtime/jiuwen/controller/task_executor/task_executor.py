#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import time
from typing import Any, Optional, AsyncGenerator

from jiuwen.common.log.base import logger
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.common.task import TaskExecution, Task


class TaskExecutor:
    """任务执行器基类，提供任务执行功能"""

    def __init__(self, workflows, llm=None, context_manager=None):
        """初始化任务执行器

        Args:
            workflows: 工作流列表
            context_manager: 上下文管理器
        """
        self.llm = llm
        self.context_manager = context_manager
        self.workflows = workflows

    @staticmethod
    def _create_error_message(task: Task, error_msg: str) -> Message:
        """创建错误消息

        Args:
            task: 任务对象
            error_msg: 错误信息

        Returns:
            Message: 错误消息对象
        """
        return Message(
            message_type=MessageType.WORKFLOW_INTERRUPT,
            content=f"任务执行失败: {error_msg}",
            runtime_data={
                "success": False,
                "error": error_msg,
                "task_id": task.id,
                "workflow_id": task.workflow_id,
            },
        )

    async def execute(self, task_execution: TaskExecution) -> Any:
        """非流式执行任务

        Args:
            task_execution: 任务执行对象，包含任务和处理函数

        Returns:
            Any: 任务执行结果
        """
        task = task_execution.task
        handler = task_execution.handler

        # 检查前置条件
        validation_result = self._validate_execution(task, handler)
        if validation_result:
            return validation_result

        # 记录开始执行
        logger.debug(f"Executing task: {task.id}, type: {task.task_type}")
        start_time = time.time()

        try:
            # 检查处理函数是否支持流式处理
            if hasattr(handler, "astream_handle") and callable(handler.astream_handle):
                # 如果支持流式处理但调用的是非流式接口，收集流式结果并返回最后一个
                logger.debug(
                    "Handler supports streaming, but execute() was called. Collecting results."
                )
                return self._collect_stream_results(task, handler)

            # 调用处理函数执行任务
            context = {}  # 如果有上下文管理，这里可以从context_manager获取
            result = handler(task, context, workflows=self.workflows)
            # 记录执行完成
            execution_time = time.time() - start_time
            logger.debug(
                f"Task executed successfully: {task.id}, execution time: {execution_time:.2f}s"
            )
            return result
        except Exception as e:
            # 处理执行异常
            error_msg = f"Task execution failed: {e}"
            # 记录错误
            logger.error(f"{error_msg}", simple_log=f"Task execution failed: {type(e)}")
            return None

    async def stream_execute(self, task_execution: TaskExecution) -> AsyncGenerator:
        """流式执行任务

        Args:
            task_execution: 任务执行对象，包含任务和处理函数

        Yields:
            流式执行结果
        """
        task = task_execution.task
        handler = task_execution.handler

        # 检查前置条件
        validation_result = self._validate_execution(task, handler)
        if validation_result:
            yield validation_result
            return

        # 记录开始执行
        logger.debug(
            "Stream executing task: %s, type: %s", task.id, task.task_type
        )
        start_time = time.time()

        try:
            # 检查处理函数是否支持流式处理
            async for chunk in handler.astream_handle(
                task, workflows=self.workflows, llm=self.llm
            ):
                yield chunk

            # 记录执行完成
            execution_time = time.time() - start_time
            logger.debug(
                "Task stream executed successfully: %s, execution time: %.2fs",
                task.id, execution_time,
            )

        except Exception as e:
            # 处理执行异常
            import traceback

            error_msg = (
                f"Task stream execution failed: {str(e)}\n{traceback.format_exc()}"
            )
            # 记录错误
            logger.error(f"{error_msg}", simple_log="stream_execute error")
            raise

    def _validate_execution(self, task: Task, handler: Any) -> Optional[Message]:
        """验证任务执行的前置条件

        Args:
            task: 任务对象
            handler: 处理函数

        Returns:
            Optional[Message]: 如果验证失败，返回错误消息；如果验证通过，返回None
        """
        # 检查处理函数是否存在
        if not handler:
            error_msg = f"No handler available for task: {task.id}"
            logger.error(error_msg)
            return self._create_error_message(task, error_msg)

        return None

    async def _collect_stream_results(self, task: Task, handler: Any) -> Any:
        """收集流式处理结果

        Args:
            task: 任务对象
            handler: 处理函数

        Returns:
            最后一个结果或合并后的结果
        """
        context = {}  # 如果有上下文管理，这里可以从context_manager获取
        results = []

        try:
            # 收集所有流式结果
            async for chunk in handler.astream_handle(
                task, context, workflows=self.workflows
            ):
                results.append(chunk)

            # 如果没有结果，返回空消息
            if not results:
                return Message(
                    message_type=MessageType.SYSTEM,
                    content="任务执行未返回任何结果",
                    runtime_data={"success": True, "task_id": task.id},
                )

            # 返回最后一个结果
            return results[-1]
        except Exception as e:
            # 处理执行异常
            error_msg = f"Task execution failed: {e}"
            # 记录错误
            logger.error(f"{error_msg}", simple_log=f"Task execution failed: {type(e)}")
            return None
