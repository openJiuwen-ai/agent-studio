#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from abc import abstractmethod
from typing import Any, Union, Optional, AsyncGenerator

from jiuwen.common.log.base import logger
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.common.task import Task
from jiuwen.controller.common.task_type import TaskType, TaskSubType


class TaskPlanner:
    """任务规划模块，根据消息、规则和上下文规划下一步任务"""

    def __init__(
        self,
        plan_config,
        llm,
        plugins,
        workflows,
        context_manager,
        task_id,
        agent_state=None,
        mcps=None,
    ):
        """初始化任务规划器

        Args:
            context_manager: 上下文管理器
            workflows: 工作流列表
            plugins: 插件列表
            llm: 模型
            plan_config: 规划配置
            task_id: 任务ID
        """
        self.context_manager = context_manager
        self.workflows = workflows
        self.plugins = plugins
        self.model = llm
        self.plan_config = plan_config
        self.task_id = task_id
        self.mcps = mcps

    @staticmethod
    def is_final_output(message: Message) -> bool:
        """判断消息是否为最终输出

        Args:
            message: 当前消息

        Returns:
            bool: 是否为最终输出
        """
        # 工作流完成消息通常是最终输出
        if message.is_workflow_completion:
            return True

        # 插件参数缺失和插件调用确认消息, 需要调用原子能力处理
        if message.is_plugin_param_miss or message.is_plugin_call_confirm:
            return False

        # 其他情况不是最终输出
        return False

    @staticmethod
    def create_task_for_message(message: Message) -> Optional[Task]:
        """根据消息类型创建对应的任务

        Args:
            message: 当前消息

        Returns:
            创建的任务，如果无法创建特定任务则返回None
        """
        # 根据消息类型创建不同任务
        if message.is_plugin_param_miss:
            # 创建一个获取插件参数的任务
            return Task(
                task_type=TaskType.WORKFLOW_INTERRUPT,
                sub_task_type=TaskSubType.ASK_USER_FOR_PARAM,
                input_data={
                    "plugin_name": message.runtime_data.get("plugin_name"),
                    "param_name": message.runtime_data.get("param_name"),
                    "param_desc": message.runtime_data.get("param_desc"),
                    "original_message": message,
                },
            )
        if message.is_plugin_call_confirm:
            # 创建一个调用插件的任务
            return Task(
                task_type=TaskType.WORKFLOW_INTERRUPT,
                sub_task_type=TaskSubType.ASK_USER_FOR_CONFIRM,
                input_data={
                    "plugin_name": message.runtime_data.get("plugin_name"),
                    "function_name": message.runtime_data.get("function_name"),
                    "arguments": message.runtime_data.get("arguments"),
                    "original_message": message,
                },
            )

        # 默认情况，无法创建特定任务
        return None

    @abstractmethod
    def plan(self, message: Message) -> Union[Message, Task, None]:
        """规划任务的抽象方法，子类必须实现

        Args:
            message: 输入消息

        Returns:
            规划结果，可能是消息、任务或None
        """
        pass

    @abstractmethod
    async def stream(self, message: Message) -> AsyncGenerator[Any, None]:
        """流式规划任务的抽象方法，子类必须实现

        Args:
            message: 输入消息

        Yields:
            流式输出内容
        """
        pass

    def plan_task(self, message: Message) -> Union[Message, Task]:
        """非流式规划任务并处理结果

        这是一个公共方法，封装了规划和结果处理逻辑。

        Args:
            message: 输入消息

        Returns:
            处理后的任务或消息
        """
        logger.debug(f"Planning task for message type {message.message_type}")

        # 调用子类实现的plan方法
        result = self.plan(message)

        # 处理规划结果
        return self._process_plan_result(message, result)

    async def stream_plan_task(self, message: Message) -> AsyncGenerator[Any, None]:
        """流式规划任务并处理结果

        这是一个公共方法，封装了流式规划和结果处理逻辑。

        Args:
            message: 输入消息

        Yields:
            流式输出内容，包括中间结果和最终的任务或消息
        """
        logger.debug(
            f"task_id: {self.task_id}| Stream planning task "
            f"for message type {message.message_type if message else 'UNKNOWN'}"
        )

        # 调用子类实现的stream方法，并处理流式输出
        detected_task_list = list()

        # 处理流式输出
        async for chunk in self.stream(message):
            if isinstance(chunk, Task):
                detected_task_list.append(chunk)
                logger.debug(
                    "Detected Task object in stream: %s", chunk.task_type
                )
                # 找到任务后仍然继续处理流，但不传递任务对象
            else:
                # 传递非任务类型的流式输出
                yield chunk

        # 如果在流中检测到任务，处理该任务
        for detected_task in detected_task_list:
            if detected_task:
                logger.debug(
                    f"task_id: {self.task_id}| Processing detected Task from stream: "
                    f"{detected_task.task_type}"
                )

                # 将任务添加到队列
                self.task_queue.add_task(detected_task)

        logger.debug(
            "task_id: %s| Before execute task in task queue, "
            "length of task queue = %s",
            self.task_id, len(self.task_queue.pending_tasks),
        )
        end_workflow_context = self.context_manager.get_end_workflow_contexts()
        while not self.task_queue.is_pending_task_empty():
            # 获取队列中的下一个任务, 如果沒有新任务产生，则继续恢复上一个任务的执行
            next_task = self.task_queue.get_next_task()
            if next_task:
                # 检查工作流任务是否需要提前结束
                is_workflow_task = next_task.is_workflow_task()
                task_should_end = self.context_manager.is_task_end()
                workflow_name_mismatch = (
                    not end_workflow_context
                    or not is_workflow_task  # 添加这个条件
                    or next_task.workflow_context.workflow_name
                    != end_workflow_context.workflow_name
                )
                if is_workflow_task and task_should_end and workflow_name_mismatch:
                    workflow_name = next_task.workflow_context.workflow_name
                    logger.info(
                        f"task_id: {self.task_id}| Task end after execute end workflow context: "
                        f"{workflow_name}"
                    )
                    yield next_task
                    return

                if next_task.is_restored and next_task.is_workflow_task():
                    self.context_manager.add_intent_to_latest_user_message(
                        next_task.workflow_context.workflow_name
                    )
                    next_task.input_data[WorkflowConstants.QUERY] = (
                        self.context_manager.get_latest_user_content()
                    )
                    next_task.input_data[WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY] = (
                        self.context_manager.get_global_variables(
                            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY
                        )
                    )
                logger.debug(
                    "task_id: %s| get next task from queue: %s",
                    self.task_id, next_task.task_type,
                )
                yield next_task
                if (
                    self.context_manager.agent_config.plan_config.plan_mode
                    == "Controller"
                ):
                    logger.debug(
                        "task_id: %s| For Controller mode, execute ONE task in task queue "
                        "each time!",
                        self.task_id,
                    )
                    break

    def _process_plan_result(
        self, message: Message, result: Any
    ) -> Union[Message, Task]:
        """处理规划结果

        Args:
            message: 输入消息
            result: 规划结果

        Returns:
            处理后的任务或消息
        """
        # 3. 检查结果类型
        if isinstance(result, Message):
            # 如果结果是消息，检查是否是最终输出消息
            if self.is_final_output(result):
                logger.debug(f"Message is final output: {result.message_type}")
                return result

            # 如果不是最终输出消息，创建任务来处理该消息
            task = self.create_task_for_message(result)
            if task:
                logger.debug(f"Created task for message: {task.task_type}")
                self.task_queue.add_task(task)
            else:
                # 如果无法为消息创建任务，直接返回消息
                logger.debug(f"No task created for message: {result.message_type}")
                return result

        elif isinstance(result, Task):
            # 如果结果是任务，直接添加到队列
            task = result
            logger.debug(f"Adding task to queue: {task.task_type}")
            self.task_queue.add_task(task)

        # 4. 获取队列中的下一个任务
        next_task = self.task_queue.get_next_task()
        if next_task:
            logger.debug(f"Returning next task from queue: {next_task.task_type}")
            return next_task

        # 5. 如果队列为空，返回默认消息
        logger.warning("Task queue is empty, returning default message")
        return Message(
            message_type=MessageType.WORKFLOW_COMPLETION,
            content="无法确定下一步操作",
            runtime_data={"success": False, "reason": "empty_task_queue"},
        )
