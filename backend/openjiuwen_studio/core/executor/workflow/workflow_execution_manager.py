#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import asyncio
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass
from builtins import id as builtinid
from openjiuwen.core.common.logging import logger
from openjiuwen.core.workflow import Session


@dataclass
class WorkflowExecutionRegistration:
    """工作流执行注册信息"""
    conversation_id: str
    workflow_id: str
    workflow_version: str
    space_id: str
    session: Optional[Session] = None
    task: Optional[asyncio.Task] = None


@dataclass
class WorkflowExecutionInfo(WorkflowExecutionRegistration):
    """工作流执行信息"""
    thread_id: Optional[int] = None


class WorkflowExecutionManager:
    """工作流执行管理器，用于跟踪和管理正在执行的工作流"""

    def __init__(self):
        # 使用 conversation_id 作为key
        self._executions: Dict[str, WorkflowExecutionInfo] = {}
        self._lock = threading.Lock()
        self._cancelled_flags: Dict[str, bool] = {}

    def register_execution(self, registration: WorkflowExecutionRegistration) -> None:
        """注册一个执行任务"""
        with self._lock:
            thread_id = threading.get_ident()
            self._executions[registration.conversation_id] = WorkflowExecutionInfo(
                conversation_id=registration.conversation_id,
                workflow_id=registration.workflow_id,
                workflow_version=registration.workflow_version,
                space_id=registration.space_id,
                session=registration.session,
                task=registration.task,
                thread_id=thread_id
            )
            # 初始化取消标志
            self._cancelled_flags[registration.conversation_id] = False
            logger.info(
                f"Registered workflow execution: conversation_id={registration.conversation_id}, "
                f"thread_id={thread_id}")

    def unregister_execution(self, conversation_id: str) -> None:
        """取消注册执行任务"""
        with self._lock:
            if conversation_id in self._executions:
                info = self._executions.pop(conversation_id)
                self._cancelled_flags.pop(conversation_id, None)
                logger.info(
                    f"Unregistered workflow execution: conversation_id={info.conversation_id}, "
                    f"thread_id={info.thread_id}"
                )

    def is_cancelled(self, conversation_id: str) -> bool:
        """检查指定conversation_id是否已被取消"""
        with self._lock:
            return self._cancelled_flags.get(conversation_id, False)

    def get_execution(self, conversation_id: str) -> Optional[WorkflowExecutionInfo]:
        """获取执行信息"""
        with self._lock:
            return self._executions.get(conversation_id)

    def is_executing(self, conversation_id: str) -> bool:
        """
        检查指定 conversation_id 的工作流是否正在执行

        Args:
            conversation_id: 对话ID

        Returns:
            bool: 如果正在执行返回 True，否则返回 False
        """
        with self._lock:
            execution_info = self._executions.get(conversation_id)
            if not execution_info:
                return False

            # 检查任务是否已完成或取消
            if execution_info.task:
                return not execution_info.task.done()

            # 如果没有任务信息，但存在于注册表中，则视为正在执行
            return True

    async def cancel_execution(
            self,
            conversation_id: str
    ) -> bool:
        """
        取消正在执行的工作流

        Args:
            conversation_id: 对话ID

        Returns:
            bool: 是否成功取消
        """
        execution_info = self.get_execution(conversation_id)
        if not execution_info:
            logger.warning(f"Execution not found for conversation_id: {conversation_id}")
            return False

        try:
            # 1. 设置取消标志（优先执行，让流式输出能快速响应）
            with self._lock:
                self._cancelled_flags[conversation_id] = True
            logger.info(f"Set cancelled flag for conversation_id: {conversation_id}")

            # 2. 取消异步任务
            if execution_info.session and execution_info.task and not execution_info.task.done():
                execution_info.task.cancel()
                logger.info(
                    f"Workflow task cancelled by user for conversation_id: {conversation_id} "
                    f"task_id: {builtinid(execution_info.task)}")
                try:
                    await execution_info.task
                except asyncio.CancelledError:
                    logger.info(f"Cancelled async task for conversation_id: {conversation_id}")
                except Exception as e:
                    logger.error(f"Error cancelling task: {e}", exc_info=True)

            # 3. 从注册表中移除
            self.unregister_execution(conversation_id)

            logger.info(
                f"Successfully cancelled execution: conversation_id={conversation_id}."
            )
            return True

        except Exception as e:
            logger.error(
                f"Error cancelling execution for conversation_id={conversation_id}: {e}",
                exc_info=True
            )
            return False

    def list_executions(self) -> Dict[str, WorkflowExecutionInfo]:
        """列出所有正在执行的会话"""
        with self._lock:
            return self._executions.copy()


# 全局执行管理器实例
workflow_execution_manager = WorkflowExecutionManager()
