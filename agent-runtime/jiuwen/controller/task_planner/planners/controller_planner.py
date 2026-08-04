#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from dataclasses import dataclass, field
from datetime import datetime
from typing import Union, Any, AsyncGenerator

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import WorkflowType
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.common.task import Task
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
)
from jiuwen.controller.task_planner.planning_modules.task_understanding_module import (
    TaskUnderstandingModule,
)
from jiuwen.controller.task_planner.rule_modules.rule_module import RuleModule
from jiuwen.controller.task_planner.task_planner import TaskPlanner
from jiuwen.controller.task_planner.task_queue import TaskQueue


@dataclass
class ControllerState:
    """控制器状态类，用于存储ControllerPlanner的状态"""

    current_workflow_index: int = 0
    start_workflow_executed: bool = False
    start_workflow_completed: bool = False
    end_workflow_executed: bool = False
    end_workflow_completed: bool = False
    global_iteration_count: int = 0
    processed_workflow_names: set = field(default_factory=set)
    task_end: bool = False
    task_id: str = field(default_factory=str)
    created_at: datetime = field(default_factory=datetime.now)


class ControllerPlanner(TaskPlanner):
    """控制器规划器，基于规则或动态选择进行任务规划"""

    def __init__(self, plan_config, llm, plugins, workflows, context_manager, task_id):
        """初始化控制器规划器

        Args:
            plan_config: 规划配置，包含控制器相关配置
            llm: 语言模型实例
            plugins: 可用插件列表
            workflows: 工作流列表
            context_manager: 上下文管理器
            task_id: 任务ID
        """
        super().__init__(plan_config, llm, plugins, workflows, context_manager, task_id)
        self.last_message = None
        self.task_queue = TaskQueue(self.context_manager)
        # 设置任务ID
        self.task_id = task_id
        # 从控制器上下文初始化工作流索引
        self.current_workflow_index = self.context_manager.get_workflow_index()

        # 初始化规则库
        self.rule_module = RuleModule(
            controller_config=plan_config, context_manager=context_manager
        )
        self.intention_detect_module = IntentionDetectModule(
            plan_config, llm, context_manager
        )
        self.task_understanding_module = (
            TaskUnderstandingModule(llm, context_manager)
            if self._has_pe_agent()
            else None
        )

    def get_state(self) -> ControllerState:
        """获取当前控制器状态（用于向后兼容）

        Returns:
            ControllerState: 控制器状态对象
        """
        controller_state = self.context_manager.get_controller_state(self.task_id)
        logger.info(
            f"get controller state for {self.task_id}, create at {controller_state.created_at}"
        )
        return controller_state

    def load_state(self, state):
        """加载当前ControllerPlanner的状态

        Args:
            state:

        Returns:

        """
        self.task_queue.load_state(state.task_queue_state)

    def is_start_workflow_executed(self):
        """判断start_workflow是否已执行

        Returns:
            bool: 是否已执行
        """
        return self.context_manager.is_start_workflow_executed()

    def is_start_workflow_completed(self):
        """判断start_workflow是否已完成

        Returns:
            bool: 是否已完成
        """
        return self.context_manager.is_start_workflow_completed()

    def plan(self, message: Message) -> Union[Message, Task, None]:
        """基于规则和工作流序列规划任务

        应用规则库规则（包括开始工作流和全局意图），
        在start_workflow完成后按顺序执行工作流。

        Args:
            message: 输入消息

        Returns:
            规划结果，可能是消息、任务或None
        """
        pass

    async def stream(self, message: Message) -> AsyncGenerator[Any, None]:
        """流式规划任务，按workflow_sequence顺序执行工作流

        Args:
            message: 输入消息

        Yields:
            流式输出内容
        """
        logger.info(
            f"task_id: {self.task_id}| Task Planner received message type: {message.message_type} "
            f"content: {message.content}",
            simple_log=f"task_id: {self.task_id}| Task Planner received message type: {message.message_type}",
        )
        self.last_message = message
        # 处理用户输入，获取工作流序列
        self._process_user_input(message)

        # 应用规则（包括开始工作流和全局意图规则）
        rule_result = self.rule_module.apply_rules(message)
        if rule_result:
            logger.info(
                f"task_id: {self.task_id} | Rule applied in stream, result_type={type(rule_result).__name__}, "
                f"result={rule_result}",
                simple_log=(
                    f"task_id: {self.task_id} | Rule applied in stream, "
                    f"result_type={type(rule_result).__name__}"
                ),
            )
            yield rule_result
            return

        # 如果start_workflow尚未完成，等待
        if (
            self.plan_config.start_workflow
            and not self.is_start_workflow_completed()
            and not self.context_manager.is_task_end()
        ):
            logger.info(
                f"task_id: {self.task_id}| Waiting for start workflow to complete or user input"
            )
            if message.message_type == MessageType.USER_INPUT:
                intent_workflow_task = await self._get_intent_based_workflow(
                    [], self.last_message, True
                )
                if intent_workflow_task:
                    yield intent_workflow_task
                return
            return

        # 执行下一个工作流
        task = await self._get_next_workflow(message)
        if task:
            yield task
            return

    def reset(self):
        """重置规划器状态"""
        # 重置控制器上下文
        self.context_manager.reset_controller_context()

        # 清除任务队列
        self.task_queue.clear_all_tasks()

    def _process_user_input(self, message):
        """处理用户输入，提取并验证工作流序列"""
        if message.message_type != MessageType.USER_INPUT:
            return

        runtime_context = message.runtime_data.get("runtime_context", {})
        conversation_id = runtime_context.conversation_id
        workflow_req_params = runtime_context.agent_workflow_context.get(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
        )

        # 获取工作流序列和活动工作流
        workflow_sequence = workflow_req_params.get(
            WorkflowConstants.SEQUENCE_WORKFLOWS_KEY
        )
        active_workflows = workflow_req_params.get(
            WorkflowConstants.ACTIVE_WORKFLOWS_KEY
        )
        intent = workflow_req_params.get(WorkflowConstants.INTENT)
        enable_history = workflow_req_params.get("enable_history", True)
        self.context_manager.add_user_message(
            message.content, enable_history=enable_history
        )

        logger.info(f"Saved intent param: {intent}", simple_log="Saved intent param")
        self.context_manager.set_global_variables(WorkflowConstants.INTENT, intent)
        self.context_manager.set_global_variables(
            WorkflowConstants.CONVERSATION_ID, conversation_id
        )

        # 设置全局意图配置
        workflow_req_params["global_intents"] = self.plan_config.global_intents
        logger.info(
            f"task_id: {self.task_id}| global_intents: {self.plan_config.global_intents}",
            simple_log="task_id: {self.task_id}| global_intents",
        )
        self.context_manager.set_global_variables(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, workflow_req_params
        )

        # 清除之前可能存在的工作流执行状态
        self.context_manager.set_global_variables(
            WorkflowConstants.VALID_WORKFLOW_SEQUENCE_KEY, None
        )
        self.context_manager.set_global_variables(
            WorkflowConstants.ACTIVE_WORKFLOWS_KEY, None
        )

        # 处理指定工作流序列模式（优先级高于active_workflows）
        if workflow_sequence:
            # 验证工作流序列
            valid_sequence = []
            for workflow_id in workflow_sequence:
                workflow_context = self.context_manager.get_workflow_context_by_id(
                    workflow_id, WorkflowType.GENERAL
                )
                if workflow_context:
                    valid_sequence.append(workflow_id)
                else:
                    logger.warning(
                        f"task_id: {self.task_id}| Workflow ID {workflow_id} not found in context"
                    )

            if valid_sequence:
                # 保存有效序列
                self.context_manager.set_global_variables(
                    WorkflowConstants.VALID_WORKFLOW_SEQUENCE_KEY, valid_sequence
                )
                logger.info(
                    f"task_id: {self.task_id}| Saved valid workflow sequence: {valid_sequence}"
                )
                # 当有valid_sequence时，确保active_workflows不生效
                self.context_manager.set_global_variables(
                    WorkflowConstants.ACTIVE_WORKFLOWS_KEY, None
                )
            else:
                logger.warning(
                    f"task_id: {self.task_id}| No valid workflows found in the provided sequence"
                )

        # 仅当workflow_sequence为空或无效时，才处理active_workflows
        if active_workflows:
            # 验证活动工作流
            valid_active_workflows = []
            for workflow_id in active_workflows:
                workflow_context = self.context_manager.get_workflow_context_by_id(
                    workflow_id, WorkflowType.GENERAL
                )
                if workflow_context:
                    valid_active_workflows.append(workflow_id)
                else:
                    logger.warning(
                        f"task_id: {self.task_id}| Active workflow ID {workflow_id} not found in context"
                    )

            if valid_active_workflows:
                # 保存有效的活动工作流
                self.context_manager.set_global_variables(
                    WorkflowConstants.ACTIVE_WORKFLOWS_KEY, valid_active_workflows
                )
                logger.info(f"Saved active workflows: {valid_active_workflows}")
            else:
                logger.warning("No valid workflows found in the active workflows list")

    async def _get_next_workflow(self, message):
        """Process the next workflow to be executed based on sequence or intent detection"""
        controller_context = self.context_manager.controller_context
        valid_sequence = self.context_manager.get_global_variables(
            WorkflowConstants.VALID_WORKFLOW_SEQUENCE_KEY
        )
        active_workflows = self.context_manager.get_global_variables(
            WorkflowConstants.ACTIVE_WORKFLOWS_KEY
        )
        force_default_workflow = self._check_force_default_workflow(message)

        # 首先检查是否需要执行第一个序列工作流
        first_workflow_task = self._get_first_sequence_workflow(
            valid_sequence, controller_context, message
        )
        if first_workflow_task:
            return first_workflow_task

        # 处理用户输入的意图识别
        intent_result = await self._handle_user_input_intent(
            message, active_workflows, force_default_workflow
        )
        if intent_result is not None:
            return intent_result

        # 当意图识别没有返回工作流时，优先执行默认工作流
        default_result = self._try_default_workflow_for_user_input(message)
        if default_result is not None:
            return default_result

        # 处理工作流完成消息且中断栈不为空的情况
        if self._should_wait_for_interrupt_workflow(message):
            return None

        # 中断工作流栈为空时的统一处理逻辑
        if self.task_queue.is_pending_task_empty():
            return self._get_sequential_workflows(
                valid_sequence, controller_context, message
            )

        return None

    def _check_force_default_workflow(self, message) -> bool:
        """检查是否强制使用默认工作流"""
        if not hasattr(message, "runtime_data") or not isinstance(
            message.runtime_data, dict
        ):
            return False
        runtime_context = message.runtime_data.get("runtime_context", {})
        if not hasattr(runtime_context, "agent_workflow_context"):
            return False
        if not isinstance(runtime_context.agent_workflow_context, dict):
            return False
        return runtime_context.agent_workflow_context.get(
            "force_default_workflow", False
        )

    async def _handle_user_input_intent(
        self, message, active_workflows, force_default_workflow
    ):
        """处理用户输入的意图识别逻辑"""
        is_user_input_or_start_completion = (
            message.message_type == MessageType.USER_INPUT
            or self._is_start_workflow_completion_message(message)
        )
        if not is_user_input_or_start_completion or force_default_workflow:
            return None

        specified_intent = self.context_manager.get_global_variables(
            WorkflowConstants.INTENT, None
        )
        # 任务理解：仅在没有指定意图，用户输入且存在 PE Agent 时判断
        if not specified_intent:
            pe_task = await self._try_route_to_pe_agent(message)
            if pe_task:
                return pe_task

        intent_workflow_task = await self._try_get_intent_workflow(active_workflows)
        if intent_workflow_task:
            return intent_workflow_task

        default_workflow_task = self._get_default_workflow(message)
        if default_workflow_task:
            logger.info(
                f"task_id: {self.task_id}| Default workflow selected: {default_workflow_task.workflow_id}"
            )
            return default_workflow_task

        if self.plan_config.parent_agent_metadata:
            logger.warning(f"task_id: {self.task_id}| Handoff to father agent")
            return self.rule_module.create_handoff_father_agent_task(self.task_id)

        return None

    async def _try_route_to_pe_agent(self, message):
        """尝试路由到 PE Agent"""
        if (
            message.message_type != MessageType.USER_INPUT
            or not self.task_understanding_module
        ):
            return None
        is_complex = await self._should_route_to_pe_agent(message)
        if not is_complex:
            return None
        pe_agent = self._get_pe_agent()
        if not pe_agent:
            return None
        logger.info(
            f"task_id: {self.task_id}| Routing to PE Agent due to complex task",
            simple_log=f"task_id: {self.task_id}| Routing to PE Agent",
        )
        return self.rule_module.create_handoff_child_agent_task(pe_agent, self.task_id)

    def _try_default_workflow_for_user_input(self, message):
        """尝试为用户输入获取默认工作流"""
        if message.message_type != MessageType.USER_INPUT:
            return None
        default_workflow_task = self._get_default_workflow(message)
        if not default_workflow_task:
            return None
        logger.info(
            f"task_id: {self.task_id}| Default workflow selected: {default_workflow_task.workflow_id}"
        )
        return default_workflow_task

    def _should_wait_for_interrupt_workflow(self, message) -> bool:
        """检查是否需要等待中断工作流执行"""
        if message.message_type != MessageType.WORKFLOW_COMPLETION:
            return False
        if self.task_queue.is_pending_task_empty():
            return False
        logger.info(
            "Interrupt workflow stack is not empty, waiting for interrupt workflow execution"
        )
        return True

    async def _try_get_intent_workflow(self, active_workflows):
        """尝试基于意图获取工作流"""
        use_intent = not self.context_manager.is_end_workflow_completed()
        not_end = not self.context_manager.is_task_end()

        if use_intent and not_end:
            return await self._get_intent_based_workflow(
                active_workflows, self.last_message
            )
        return None

    def _get_sequential_workflows(self, valid_sequence, controller_context, message):
        """按顺序执行工作流：序列工作流 -> 结束工作流"""
        # 按顺序尝试执行工作流
        workflows_to_try = [
            lambda: self._get_next_sequence_workflow(
                valid_sequence, controller_context, message
            ),
            lambda: self._get_end_workflow(
                valid_sequence, None, controller_context, message
            ),
        ]
        for get_workflow in workflows_to_try:
            workflow_task = get_workflow()
            if workflow_task:
                return workflow_task

        # 没有工作流可执行，标记任务结束
        self.context_manager.mark_task_end()
        return None

    def _get_first_sequence_workflow(self, valid_sequence, controller_context, message):
        """如果配置了默认顺序，则执行默认顺序中第一个工作流

        Args:
            valid_sequence: 有效的工作流序列
            controller_context: 控制器上下文
            message: 消息对象

        Returns:
            Task or None: 第一个工作流任务或None
        """
        # 检查是否有有效的工作流序列
        if not valid_sequence:
            return None

        # 检查当前工作流索引是否为0（表示还没开始执行任何工作流）
        if controller_context.current_workflow_index != 0:
            return None

        # 获取第一个工作流ID
        first_workflow_id = valid_sequence[0]

        # 检查第一个工作流是否已经在运行或已完成
        if self.context_manager.is_general_workflow_running(
            first_workflow_id
        ) or self.context_manager.is_general_workflow_completed(first_workflow_id):
            return None

        # 创建并返回第一个工作流的开始任务
        logger.info(f"Executing first workflow in sequence: {first_workflow_id}")
        return self.rule_module.create_workflow_start_task(
            message, first_workflow_id, WorkflowType.GENERAL
        )

    def _get_next_sequence_workflow(self, valid_sequence, controller_context, message):
        """从有效序列中获取下一个工作流"""
        if not valid_sequence or not hasattr(
            controller_context, "current_workflow_index"
        ):
            return None

        logger.info(
            f"current_workflow_index：{controller_context.current_workflow_index}"
        )
        # 检查是否已经完成所有工作流
        if controller_context.current_workflow_index >= len(valid_sequence):
            return None

        # 获取当前工作流ID
        current_workflow_id = valid_sequence[controller_context.current_workflow_index]

        # 检查当前索引不是0且前一个工作流是否已完成
        if controller_context.current_workflow_index > 0:
            previous_workflow_id = valid_sequence[
                controller_context.current_workflow_index - 1
            ]
            if not self.context_manager.is_general_workflow_completed(
                previous_workflow_id
            ):
                logger.info(
                    f"Waiting for previous workflow {previous_workflow_id} to complete "
                    f"before executing {current_workflow_id}"
                )
                return None

        # 检查当前工作流是否正在运行
        if self.context_manager.is_general_workflow_running(current_workflow_id):
            # 工作流正在运行，检查是否已完成
            if self.context_manager.is_general_workflow_completed(current_workflow_id):
                # 当前工作流已完成，增加索引准备执行下一个
                logger.info(
                    f"Workflow {current_workflow_id} completed, advancing to next workflow"
                )
                controller_context.current_workflow_index += 1

                # 递归调用以获取下一个工作流
                return self._get_next_sequence_workflow(
                    valid_sequence, controller_context, message
                )

            # 当前工作流正在执行但未完成，等待
            logger.info(
                f"Workflow {current_workflow_id} is still executing, waiting for completion"
            )
            return None

        # 当前工作流未开始执行或不在运行状态，创建工作流开始任务
        logger.info(
            f"Sequence mode - "
            f"Executing "
            f"workflow {controller_context.current_workflow_index}/{len(valid_sequence) - 1}: {current_workflow_id}"
        )

        return self.rule_module.create_workflow_start_task(
            message, current_workflow_id, WorkflowType.GENERAL
        )

    def _get_default_workflow(self, message):
        """Select default workflow based on intent detection from active workflows"""
        logger.info("Using default workflow")
        default_workflow_context = self.context_manager.get_default_workflow_contexts()
        if default_workflow_context:
            detected_workflow_id = default_workflow_context.workflow_id
            if detected_workflow_id:
                logger.info(
                    f"Intent-based mode - Using Default workflow ID: {detected_workflow_id}"
                )
                return self.rule_module.create_workflow_start_task(
                    message, detected_workflow_id, WorkflowType.DEFAULT
                )
        logger.info("No default workflow found in the provided sequence")
        return None

    async def _get_intent_based_workflow(
        self, active_workflows, message, global_only=False
    ):
        """Select workflow based on intent detection from active workflows"""
        logger.info("Using intent detection module to select workflow")
        try:
            # Perform intent detection
            latest_intent = self.task_queue.get_latest_intent()
            await self.intention_detect_module.invoke(
                active_workflows,
                task_id=self.task_id,
                global_only=global_only,
                latest_intent=latest_intent,
                message=message,
            )

            # Get detection result
            detected_intent_name = self.context_manager.get_latest_intent()
            logger.info(f"Intent detection result: {detected_intent_name}")

            # 首先检查是否为全局意图
            if (
                detected_intent_name
                in self.intention_detect_module.global_intent_2_category_map
            ):
                logger.info(f"Detected global intent: {detected_intent_name}")
                # 处理全局意图逻辑
                return self._get_handle_global_intent_workflow(
                    detected_intent_name, message
                )

            if (
                detected_intent_name
                in self.intention_detect_module.category_2_child_id_map
            ):
                logger.info(f"Detected agent handoff: {detected_intent_name}")
                return self._get_handle_handoff_agent_intent(
                    detected_intent_name, message
                )

            # 如果不是全局意图，则按原有逻辑处理工作流意图
            workflow_context = (
                self.context_manager.get_workflow_context_by_name_and_type(
                    detected_intent_name
                )
            )
            if workflow_context:
                detected_workflow_id = workflow_context.workflow_id
                if detected_workflow_id:
                    logger.info(
                        f"Intent-based mode - Selected workflow ID: {detected_workflow_id}"
                    )
                    return self.rule_module.create_workflow_start_task(
                        message, detected_workflow_id, WorkflowType.GENERAL
                    )
            else:
                logger.warning(f"No workflow found for intent {detected_intent_name}")
        except Exception as e:
            import traceback

            logger.error(
                f"Error during intent detection: {str(traceback.format_exc())}",
                simple_log="Error during intent detection",
            )
            raise JiuWenBaseException(
                error_code=StatusCode.CONTROLLER_INTENT_DETECTION_ERROR.code,
                message=str(e),
            ) from e
        return None

    def _get_handle_global_intent_workflow(self, global_intent_name, message):
        """处理全局意图

        Args:
            global_intent_name: 全局意图名称
            message: 消息对象

        Returns:
            处理结果，可能是任务或None
        """
        logger.info(f"Processing global intent: {global_intent_name}")

        # 从配置中找到对应的全局意图配置
        if self.plan_config.global_intents:
            for global_intent in self.plan_config.global_intents:
                if global_intent.name == global_intent_name:
                    logger.info(
                        f"Found global intent config: {global_intent}",
                        simple_log="Found global intent config",
                    )

                    # 根据handler_type处理不同类型的全局意图
                    if global_intent.handler_type:
                        task_id = getattr(message, "task_id", "task")
                        return self.rule_module.create_global_intent_task(
                            global_intent, task_id
                        )
                    break

        logger.warning(f"Global intent {global_intent_name} not found in configuration")
        return None

    def _get_end_workflow(
        self, valid_sequence, intent_workflow_task, controller_context, message
    ):
        """Try to execute end workflow if conditions are met"""
        if not self._should_execute_end_workflow(
            valid_sequence, intent_workflow_task, controller_context
        ):
            return None

        logger.info("Executing end workflow")
        end_workflow_context = self.context_manager.get_end_workflow_contexts()
        return self.rule_module.create_workflow_start_task(
            message, end_workflow_context.workflow_id, WorkflowType.END
        )

    def _should_execute_end_workflow(
        self, workflow_sequence, intent_workflow_task, controller_context
    ) -> bool:
        """
        判断是否应执行结束工作流

        Args:
            workflow_sequence: 工作流序列
            controller_context: 控制器上下文

        Returns:
            bool: 是否应执行结束工作流
        """
        # 仅当配置了结束工作流时才考虑执行
        if not self.plan_config.end_workflow:
            return False

        if (
            self.context_manager.is_end_workflow_executed()
            or self.context_manager.is_end_workflow_completed()
        ):
            logger.info("End workflow executed or completed")
            return False

        # 对于序列模式，当所有工作流都已完成时执行结束工作流
        if workflow_sequence:
            # 检查索引是否已到达序列末尾
            if controller_context.current_workflow_index >= len(workflow_sequence):
                return True

            # 检查所有工作流是否都已完成
            for workflow_id in workflow_sequence:
                if not self.context_manager.is_general_workflow_completed(workflow_id):
                    logger.info(
                        f"Waiting for workflow {workflow_id} to complete before executing end workflow"
                    )
                    return False

            # 所有工作流都已完成
            logger.info(
                "All workflows in sequence have completed, can execute end workflow"
            )
            self.context_manager.mark_end_workflow_executed()
            return True
        # 对于基于意图的模式，如果没选到工作流，则自动执行结束工作流
        if not intent_workflow_task:
            logger.info(
                "No intent detected for workflow and pending task, execute end workflow"
            )
            return True
        return False

    def _is_start_workflow_completion_message(self, message) -> bool:
        if message.message_type == MessageType.WORKFLOW_COMPLETION:
            return message.content.get("workflow_type") == WorkflowType.START
        return False

    def _get_handle_handoff_agent_intent(self, detected_intent_class, message):
        """处理agent handoff意图(A.1:按 child.id 路由,不经 name first-match)

        Args:
            detected_intent_class: 检测到的agent handoff意图 category(分类N,每 child 唯一)
            message: 消息对象

        Returns:
            处理结果，可能是任务或None
        """
        logger.info(f"Processing agent handoff intent: {detected_intent_class}")

        # A.1(C-09): category → child.id(唯一),按 id 定位 child,允许同名子成员
        child_id = self.intention_detect_module.category_2_child_id_map.get(
            detected_intent_class
        )
        if child_id and self.plan_config.child_agents_metadata:
            for child_agent in self.plan_config.child_agents_metadata:
                if child_agent.id == child_id:
                    logger.info(f"Found child agent config: {child_agent}")

                    # 创建agent handoff任务
                    task_id = getattr(message, "task_id", "task")
                    return self.rule_module.create_handoff_child_agent_task(
                        child_agent, task_id
                    )

        logger.warning(
            f"Child agent for intent class {detected_intent_class} not found in configuration"
        )
        return None

    def _has_pe_agent(self) -> bool:
        """检查是否配置了 PlanExecute 模式的子 Agent"""
        child_agents = self.plan_config.child_agents_metadata
        if not child_agents or not isinstance(child_agents, list):
            return False
        return any(agent.mode == "PlanExecute" for agent in child_agents)

    def _get_pe_agent(self) -> "AgentMetaData | None":
        """获取 PlanExecute 模式的子 Agent

        Returns:
            AgentMetaData | None: PlanExecute 模式的子 Agent，如果没有则返回 None
        """
        child_agents = self.plan_config.child_agents_metadata
        if not child_agents or not isinstance(child_agents, list):
            return None
        for agent in child_agents:
            if agent.mode == "PlanExecute":
                return agent
        return None

    async def _should_route_to_pe_agent(self, message: Message) -> bool:
        """判断是否应该路由到 PE Agent"""
        query = message.content
        chat_history = self.context_manager.get_latest_k_chat_history(
            self.plan_config.chat_history_max_turn
        )
        available_intents = self._get_available_intent_names()
        result = await self.task_understanding_module.invoke(
            query=query,
            chat_history=chat_history,
            available_intents=available_intents,
            task_id=self.task_id,
        )
        return result.is_complex

    def _get_available_intent_names(self) -> list:
        """获取可用意图描述列表

        返回格式与意图识别模块一致，包含能力名称和描述
        """
        intent_descriptions = []
        self._collect_global_intent_descriptions(intent_descriptions)
        self._collect_workflow_intent_descriptions(intent_descriptions)
        self._collect_child_agent_intent_descriptions(intent_descriptions)
        return self._deduplicate_intent_descriptions(intent_descriptions)

    def _collect_global_intent_descriptions(self, intent_descriptions: list):
        """收集全局意图描述"""
        if not self.plan_config.global_intents:
            return
        for intent in self.plan_config.global_intents:
            if intent.name and intent.name != "其他":
                desc = intent.description or intent.name
                intent_descriptions.append(f"{intent.name}: {desc}")

    def _collect_workflow_intent_descriptions(self, intent_descriptions: list):
        """收集工作流意图描述"""
        for workflow_context in self.context_manager.get_normal_workflow_contexts():
            name = (
                workflow_context.intent_name
                or workflow_context.config_name
                or workflow_context.workflow_name
            )
            desc = self._get_workflow_description(workflow_context)
            if desc:
                intent_descriptions.append(f"{name}: {desc}")
            else:
                intent_descriptions.append(name)

    def _get_workflow_description(self, workflow_context) -> str:
        """获取工作流描述，优先使用 intent_description"""
        if (
            hasattr(workflow_context, "intent_description")
            and workflow_context.intent_description
        ):
            return workflow_context.intent_description
        return workflow_context.description

    def _collect_child_agent_intent_descriptions(self, intent_descriptions: list):
        """收集子 Agent 意图描述"""
        child_agents = self.plan_config.child_agents_metadata
        if not child_agents or not isinstance(child_agents, list):
            return
        for agent in child_agents:
            intent_desc = self._format_agent_intent_description(agent)
            if intent_desc:
                intent_descriptions.append(intent_desc)

    def _format_agent_intent_description(self, agent) -> str:
        """格式化 Agent 意图描述"""
        name = agent.intent_name or agent.name
        if not name:
            return ""
        desc = (
            agent.intent_description
            if hasattr(agent, "intent_description") and agent.intent_description
            else agent.description
        )
        if desc:
            return f"{name}: {desc}"
        return name

    def _deduplicate_intent_descriptions(self, intent_descriptions: list) -> list:
        """去重意图描述列表，保持顺序"""
        seen = set()
        deduped = []
        for item in intent_descriptions:
            if item and item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped
