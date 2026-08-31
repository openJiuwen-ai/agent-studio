#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import logging
import traceback
from typing import AsyncGenerator

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.controller.agent.control_mode.base_mode import BaseMode, RESULT, CODE
from jiuwen.controller.common.config import StreamRequest
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import (
    ActionAfterCompletionType,
    WorkflowType,
    HandoffType,
    RetCode,
)
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType, MessageSubType
from jiuwen.controller.common.task import Task, TaskExecution
from jiuwen.controller.common.task_type import TaskType, TaskSubType
from jiuwen.controller.task_executor import WorkflowHandler
from jiuwen.controller.utils.utils import MessageConverter
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode


class ControllerMode(BaseMode):
    def __init__(self, **kwargs):
        """初始化控制器"""
        # 使用配置类初始化
        super(ControllerMode, self).__init__(**kwargs)
        self.terminate = False
        # controller模式初始化时添加默认全局环境变量
        self.init_global_variables()

    def __call__(self, **kwargs):
        """
        调用控制器处理用户查询的兼容性方法，实际调用invoke方法

        注意：推荐直接使用invoke方法，此方法仅为保持兼容性
        """
        return self.invoke(**kwargs)

    @staticmethod
    def get_final_result(input_data, report_message):
        """获取最终结果"""
        if input_data == RetCode.SUCCESS:
            return_dict = {CODE: input_data, RESULT: report_message}
        else:
            return_dict = {CODE: RetCode.FAILED, RESULT: input_data}
        return return_dict

    @staticmethod
    def should_output_to_user(message: Message) -> bool:
        """判断消息是否应该直接输出给用户

        Args:
            message: 消息对象

        Returns:
            bool: 是否应该输出给用户
        """
        # 中断消息且是特定子类型，输出给用户
        if message.message_type == MessageType.WORKFLOW_INTERRUPT:
            sub_type = message.sub_type
            if sub_type in [
                MessageSubType.PLUGIN_CALL_CONFIRM,
                MessageSubType.PLUGIN_PARAM_MISS,
                MessageSubType.QUESTIONER_ASK,
            ]:
                return True

        return False

    def init_global_variables(self):
        """初始化全局变量"""
        config_global_variables = self.plan_config.global_variables
        if (
            config_global_variables is None
            or not isinstance(config_global_variables, list)
            or len(config_global_variables) == 0
        ):
            logger.info(
                f"task_id: {self.task_id}| No need init context global_variables. cause: "
                f"global_variables={config_global_variables}"
            )
            return
        # 已存在global_variables则不更新
        if self.context_manager.get_global_variables(
            WorkflowConstants.CONTROLLER_GLOBAL_VARIABLES_KEY
        ):
            return
        global_variables = dict()
        for variable_item in config_global_variables:
            if variable_item.get("name", ""):
                global_variables[variable_item.get("name", "")] = variable_item.get(
                    "default"
                )
        self.context_manager.set_global_variables(
            WorkflowConstants.CONTROLLER_GLOBAL_VARIABLES_KEY, global_variables
        )
        logger.info(
            f"task_id: {self.task_id}| Set global_variables to context successfully. data={global_variables}"
        )

    def update_input_global_variables(self, global_variables):
        """从input中更新全局变量"""
        controller_global_variables = self.context_manager.get_global_variables(
            "controller_global_variables"
        )
        if controller_global_variables is None or not global_variables:
            return
        is_updated = False
        for key, value in global_variables.items():
            if key and key in controller_global_variables:
                controller_global_variables.update({key: value})
                is_updated = True
        if is_updated:
            self.context_manager.set_global_variables(
                "controller_global_variables", controller_global_variables
            )
            logger.info(
                f"task_id: {self.task_id}| controller global variables updated from input: "
                f"{type(controller_global_variables)}"
            )

    def invoke(self, **kwargs):
        """同步调用控制器处理用户查询，实现任务驱动循环"""
        pass

    async def stream(self, **kwargs) -> AsyncGenerator:
        """流式调用控制器处理用户查询"""
        try:
            # 创建流式请求对象
            request = StreamRequest(**kwargs)

            # 创建初始用户输入消息
            runtime_data = {
                "task_id": self.task_id,
                "prompt_info": request.prompt_info,
                "plugins": request.plugins,
                "workflows": request.workflows,
                "contexts": request.contexts,
                "runtime_context": request.runtime_context,
                "multimodal_image": request.multimodal_image,
                "trace_handlers": request.trace_handlers,
                "session": request.session,
            }

            message = MessageConverter.create_user_input_message(
                request.query, runtime_data
            )

            # 运行流式任务循环 - 使用更合适的方法名
            async for item in self._stream_task_loop(message):
                yield item

        except Exception as e:
            error_msg = f"task_id: {self.task_id}| 控制器流式执行失败: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            if isinstance(e, JiuWenBaseException):
                yield StreamData(
                    code=StreamCode.ERROR.value,
                    msg=StreamDataMsg.FAIL.value,
                    data=dict(
                        code=e.error_code,
                        message=e.message,
                        node_name="控制器",
                    ),
                    execution_id=self.task_id,
                )
            else:
                yield StreamData(
                    code=StreamCode.ERROR.value,
                    msg=StreamDataMsg.FAIL.value,
                    data=dict(
                        message=error_msg,
                        node_name="控制器",
                    ),
                    execution_id=self.task_id,
                )
            self.task_end = True

    async def process_task_execution_streaming_message(
        self, task_execution: TaskExecution
    ):
        """处理任务执行的流式输出，更新task_execution的状态属性

        Args:
            task_execution: 任务执行对象，执行后会更新其last_message属性
        """
        # 获取任务的ID用于后续可能的删除操作
        task_execution_id = task_execution.task.id
        query = task_execution.task.input_data.get("query", "")

        # 使用流式执行方法处理任务
        async for message in self.task_executor.stream_execute(task_execution):
            if isinstance(message, Message):
                # 保存最后一个消息用于下一轮循环
                task_execution.last_message = message
                for result in self.handle_controller_message(
                    message, task_execution_id, query
                ):
                    yield result
            else:
                # 非消息类型直接输出
                yield message

    def handle_controller_message(self, message, task_execution_id, query):
        """处理控制器消息并确定后续行为"""
        if message.is_workflow_completion:
            yield from self._handle_workflow_completion(
                message, task_execution_id, query
            )
        elif message.is_workflow_interrupt:
            yield from self._handle_workflow_interrupt(message, task_execution_id)
        elif message.is_workflow_message:
            yield from self._handle_workflow_message(message, task_execution_id)

    def _handle_workflow_completion(self, message, task_execution_id, query):
        """处理工作流完成消息"""
        # 获取工作流信息
        workflow_name = message.content.get("workflow_name")
        workflow_type = message.content.get("workflow_type")
        workflow_context = self.context_manager.get_workflow_context_by_name_and_type(
            workflow_name, workflow_type
        )

        # 在context manager里删除
        processed_workflow_names = (
            self.context_manager.controller_context.processed_workflow_names
        )
        if (
            workflow_type == WorkflowType.GENERAL
            and workflow_name in processed_workflow_names
        ):
            processed_workflow_names.remove(workflow_name)

        # 标记任务完成
        logger.info(
            f"task_id: {self.task_id}| Received completion message: {message.message_type}, "
            f"removing task with ID {task_execution_id}"
        )
        self.task_planner.task_queue.mark_task_completed(task_execution_id)

        # 处理完成后的动作
        if (
            workflow_context.action_after_completion
            == ActionAfterCompletionType.WAITING_USER_INPUT
        ):
            logger.info(
                f"task_id: {self.task_id}| Received completion message: {message.message_type} "
                f"with ID {task_execution_id}, waiting user input"
            )
            self.terminate = True
        elif (
            workflow_context.action_after_completion
            == ActionAfterCompletionType.TERMINATE
        ):
            logger.info(
                f"task_id: {self.task_id}| mark all tasks completed except end workflow"
            )
            self._terminate_all_workflows()
            # 发送task_terminated事件
            task_terminated_data = WorkflowHandler.create_workflow_jump_debug_data(
                query,
                workflow_context.workflow_name,
                workflow_context.current_node_info,
            )
            yield StreamData(
                code=StreamCode.TASK_TERMINATED_MESSAGE.value,
                msg="task_terminated_message",
                data=task_terminated_data,
                execution_id=self.task_id,
            )

        # 检查特殊工作流
        self._check_special_workflow_completion(workflow_name, task_execution_id)
        return []

    def _handle_workflow_interrupt(self, message, task_execution_id):
        """处理工作流中断消息"""
        logger.info(
            f"task_id: {self.task_id}| Received interrupt message: {message.message_type}, "
            f"pending task with ID {task_execution_id}"
        )
        self.task_planner.task_queue.mark_task_pending(task_execution_id)

        # 检查是否需要用户交互
        user_interaction_types = [
            MessageSubType.PLUGIN_CALL_CONFIRM,
            MessageSubType.PLUGIN_PARAM_MISS,
            MessageSubType.QUESTIONER_ASK,
            MessageSubType.CONTROLLER_ASK,
        ]

        if message.sub_type in user_interaction_types:
            self.terminate = True
            if message.sub_type == MessageSubType.CONTROLLER_ASK:
                yield from self._yield_question_stream(message.content["question"])

    def _handle_workflow_message(self, message, task_execution_id):
        """处理工作流普通消息"""
        yield from self._yield_message_stream(message.content["message"])

        logger.info(
            f"task_id: {self.task_id}| Received workflow message: {message.message_type}"
        )
        if message.content.get("action") == ActionAfterCompletionType.CONTINUE:
            logger.info(
                f"task_id: {self.task_id} | Global text intent processing completed. "
                f"Action: '{ActionAfterCompletionType.CONTINUE.value}', returning."
            )
        elif message.content.get("terminate"):
            self._terminate_all_workflows()
        else:
            self.terminate = True

    def _check_special_workflow_completion(self, workflow_name, task_execution_id):
        """检查特殊工作流完成情况"""
        end_workflow_context = self.context_manager.get_end_workflow_contexts()
        # 检查结束工作流
        if self.context_manager.is_end_workflow_completed() or (
            end_workflow_context and workflow_name == end_workflow_context.workflow_name
        ):
            logger.info(
                f"task_id: {self.task_id}| terminate task with end workflow {task_execution_id} completed"
            )
            self.task_end = True
            self.context_manager.mark_end_workflow_completed()

    def _yield_question_stream(self, question):
        """生成问题流数据"""
        data = {
            "answer": question,
            "node_type": "jiuwen.questioner",
            "node_id": "controller_ask",
            "node_name": "控制器",
        }
        yield StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg="",
            data=data,
            execution_id=self.task_id,
        )
        yield StreamData(
            code=StreamCode.MESSAGE_END.value,
            msg="",
            data=data,
            execution_id=self.task_id,
        )

    def _yield_message_stream(self, message):
        """生成消息流数据"""
        data = {
            "answer": message,
            "node_type": "jiuwen.message",
            "node_id": "global_intent",
            "node_name": "控制器",
        }
        yield StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg="",
            data=data,
            execution_id=self.task_id,
        )
        yield StreamData(
            code=StreamCode.MESSAGE_END.value,
            msg="",
            data=data,
            execution_id=self.task_id,
        )

    def _terminate_all_workflows(self):
        """终止所有工作流"""
        self.context_manager.mark_all_workflow_completed()
        self.task_planner.task_queue.mark_all_tasks_completed()
        self.context_manager.mark_task_end()

    async def _stream_task_loop(self, initial_message: Message) -> AsyncGenerator:
        """执行任务驱动循环的流式版本，直到得到最终结果

        Args:
            initial_message: 初始消息

        Returns:
            AsyncGenerator: 生成流式结果
        """
        current_message = initial_message
        iterations = self.context_manager.controller_context.global_iteration_count
        processed_workflow_names = (
            self.context_manager.controller_context.processed_workflow_names
        )  # 跟踪已处理的工作流名称
        if not self.context_manager.is_start_workflow_executed():
            yield StreamData(
                code=StreamCode.CONTROLLER_START_MESSAGE.value,
                msg="task start",
                data={},
                execution_id=self.task_id,
            )
        while iterations < self.max_task_iterations:
            if logger.isEnabledFor(logging.INFO):
                logger.info(
                    f"task_id: {self.task_id}|Stream task iteration {iterations}: "
                    f"Processing message type {current_message.message_type}"
                )

            # 1. 任务识别 - 使用流式任务规划
            task_planner_results = []
            final_task_or_message = None

            # 处理规划器的流式输出
            async for result in self.task_planner.stream_plan_task(current_message):
                # 收集所有规划结果
                task_planner_results.append(result)

                # 如果是中间结果（非Task或Message），转换后输出
                if not isinstance(result, (Task, Message)):
                    yield result
                else:
                    # 记录最终的任务或消息
                    final_task_or_message = result

            # 如果返回的是消息而非任务，说明这是最终输出
            if not isinstance(final_task_or_message, Task):
                # 完整 message repr 内容较大，降级为 DEBUG
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "task_id: %s| Stream task loop completed with final message: %s",
                        self.task_id,
                        final_task_or_message,
                    )
                if final_task_or_message is None and self.context_manager.is_task_end():
                    self.task_end = True
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(f"task_id: {self.task_id}| Stream task end")
                    yield self._create_task_end_message()
                    return
                yield self._create_intermediate_message()
                return

            # 检查是否为 AGENT_HANDOFF 类型的任务
            if final_task_or_message.task_type == TaskType.AGENT_HANDOFF:
                if logger.isEnabledFor(logging.INFO):
                    logger.info(
                        f"task_id: {self.task_id}| Detected AGENT_HANDOFF task: {final_task_or_message.id}"
                    )
                # 根据子任务类型生成相应的 handoff 流数据
                async for result in self._handle_handoff_task(final_task_or_message):
                    yield result
                # 对于 handoff 任务，直接返回，不进行后续处理
                return

            # 2. 任务分发
            task_execution = self.task_dispatcher.dispatch(final_task_or_message)
            # 迭代计数逻辑优化
            if task_execution.task.workflow_context:
                workflow_type = task_execution.task.workflow_context.type
                workflow_name = task_execution.task.workflow_context.workflow_name

                # 只在业务工作流类型下计数，且避免重复工作流名称的重复计数
                if (
                    workflow_type == WorkflowType.GENERAL
                    and workflow_name not in processed_workflow_names
                ):
                    iterations += 1
                    self.context_manager.controller_context.global_iteration_count += 1
                    processed_workflow_names.add(workflow_name)
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(
                            f"task_id: {self.task_id}| "
                            f"Incrementing iteration count to {iterations} for workflow: {workflow_name}"
                        )
            task_execution.task.input_data["conversation_id"] = (
                initial_message.runtime_data.get("runtime_context").conversation_id
            )
            # 3. 使用流式方法执行任务并处理结果
            async for message in self.process_task_execution_streaming_message(
                task_execution
            ):
                yield message

            # 检查执行后的状态
            if self.terminate:
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"task_id: {self.task_id}| Stream task loop terminate")
                yield self._create_intermediate_message()
                yield self._create_interrupt_message()
                return
            if self.task_end:
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"task_id: {self.task_id}| Stream task end")
                yield self._create_task_end_message()
                return
            # 使用最后一个消息作为下一轮循环的输入
            # 完整 last_message repr 内容较大，降级为 DEBUG
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "task_id: %s| Stream task loop continue with current message: %s",
                    self.task_id,
                    task_execution.last_message,
                )
            current_message = task_execution.last_message
            if not current_message:
                if logger.isEnabledFor(logging.INFO):
                    logger.info(
                        f"task_id: {self.task_id}| Stream task loop terminate, current_message is None"
                    )
                yield self._create_intermediate_message()
                yield self._create_interrupt_message()
                return
        # 达到最大迭代次数，执行结束工作流
        logger.warning(
            f"task_id: {self.task_id}| Reached max iterations ({self.max_task_iterations}), "
            f"executing end workflow"
        )
        async for message in self._execute_end_workflow_and_return_max_iterations_error(
            current_message
        ):
            yield message

    async def _handle_handoff_task(self, final_task_or_message):
        if final_task_or_message.sub_task_type == TaskSubType.HANDOFF_TO_CHILD:
            yield self._create_handoff_to_child_stream_data(final_task_or_message)
        else:
            yield self._create_handoff_to_father_stream_data(final_task_or_message)

    async def _execute_end_workflow_and_return_max_iterations_error(
        self, current_message: Message
    ) -> AsyncGenerator:
        """执行结束工作流并返回最大迭代次数错误

        Args:
            current_message: 当前消息

        Returns:
            AsyncGenerator: 生成结束工作流的流式结果和错误信息
        """
        # 获取结束工作流上下文
        end_workflow_context = self.context_manager.get_end_workflow_contexts()
        final_message_content = None

        if end_workflow_context:
            try:
                # 创建结束工作流任务
                end_task = self.task_planner.rule_module.create_workflow_start_task(
                    current_message, end_workflow_context.workflow_id, WorkflowType.END
                )

                # 分发并执行结束工作流任务
                end_task_execution = self.task_dispatcher.dispatch(end_task)
                async for result in self.process_task_execution_streaming_message(
                    end_task_execution
                ):
                    yield result

                # 获取结束工作流的最终消息
                final_message = end_task_execution.last_message
                if hasattr(final_message, "content"):
                    final_message_content = final_message.content
                else:
                    final_message_content = str(final_message)

                logger.info(
                    f"task_id: {self.task_id}| End workflow executed with final message: "
                    f"{type(final_message_content)}"
                )
            except Exception as e:
                logger.error(
                    f"task_id: {self.task_id}| Error executing end workflow: {str(e)}"
                )
        else:
            logger.warning(f"task_id: {self.task_id}| No end workflow context found")

        # 构建并返回错误信息
        error_data = dict(answer="任务处理超出最大迭代次数，可能存在循环依赖")
        if final_message_content:
            error_data["final_message"] = final_message_content
        yield StreamData(
            code=StreamCode.ERROR.value,
            msg=StreamDataMsg.FAIL.value,
            data=dict(
                code=StatusCode.WORKFLOW_REACH_MAX_ITERATION.code,
                message="任务处理超出最大迭代次数，可能存在循环依赖",
                node_name="控制器",
            ),
            execution_id=self.task_id,
        )
        yield StreamData(
            code=StreamCode.CONTROLLER_FINISH_MESSAGE.value,
            msg="task end",
            data=error_data,
            execution_id=self.task_id,
        )
        self.task_end = True

    def _create_task_end_message(self):
        return StreamData(
            code=StreamCode.CONTROLLER_FINISH_MESSAGE.value,
            msg="task end",
            data={},
            execution_id=self.task_id,
        )

    def _create_intermediate_message(self):
        msgs = self.context_manager.engine.get_messages()
        logger.info(
            f"task_id: {self.task_id}| Intermediate message count: {len(msgs)} "
            f"contents: {[(m.content or '')[:50] for m in msgs]}",
            simple_log=f"task_id: {self.task_id}| Intermediate message count: {len(msgs)}",
        )
        return StreamData(
            code=StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value,
            msg="intermediate message",
            data=dict(answer=msgs),
            execution_id=self.task_id,
        )

    def _create_handoff_stream_data(
        self, task: Task, handoff_type: HandoffType
    ) -> StreamData:
        """为智能体切换任务创建 handoff 流数据消息

        Args:
            task: 智能体切换类型的任务
            handoff_type: 切换类型（TO_CHILD 或 TO_FATHER）

        Returns:
            StreamData: handoff 流数据消息
        """
        input_data = task.input_data

        # 根据切换类型确定目标智能体字段名
        if handoff_type == HandoffType.AGENT_HANDOFF_TO_CHILD:
            agent_prefix = "child"
            msg = "agent_handoff_to_child"
        else:  # AGENT_HANDOFF_TO_FATHER
            agent_prefix = "father"
            msg = "agent_handoff_to_father"

        # 提取目标智能体信息
        agent_id = input_data.get(f"{agent_prefix}_agent_id", "")
        agent_name = input_data.get(f"{agent_prefix}_agent_name", "")
        agent_description = input_data.get(f"{agent_prefix}_agent_description", "")
        query = input_data.get("query", "")

        # 构建 handoff 数据
        handoff_data = {
            "type": handoff_type.value,
            "target_agent": {
                "id": agent_id,
                "name": agent_name,
                "description": agent_description,
            },
            "query": query,
            "task_id": task.id,
            "input_data": input_data,
        }

        logger.info(
            f"task_id: {self.task_id}| Creating {msg} stream data for agent: {agent_name}"
        )

        return StreamData(
            code=StreamCode.CONTROLLER_AGENT_HANDOFF_MESSAGE.value,
            msg=msg,
            data=handoff_data,
            execution_id=self.task_id,
        )

    def _create_handoff_to_child_stream_data(self, task: Task) -> StreamData:
        """为 AGENT_HANDOFF_TO_CHILD 任务创建 handoff 流数据消息"""
        return self._create_handoff_stream_data(
            task, HandoffType.AGENT_HANDOFF_TO_CHILD
        )

    def _create_handoff_to_father_stream_data(self, task: Task) -> StreamData:
        """为 AGENT_HANDOFF_TO_FATHER 任务创建 handoff 流数据消息"""
        return self._create_handoff_stream_data(
            task, HandoffType.AGENT_HANDOFF_TO_FATHER
        )

    def _create_interrupt_message(self):
        """创建中断消息的流数据

        Returns:
            StreamData: 中断消息的流数据
        """
        interrupt_data = {
            "type": "controller_agent_interrupt",
            "reason": "任务被中断",
            "task_id": self.task_id,
            "message": "控制器任务执行被中断",
        }

        logger.info(f"task_id: {self.task_id}| Creating interrupt stream data")

        return StreamData(
            code=StreamCode.CONTROLLER_AGENT_INTERRUPT_MESSAGE.value,
            msg="controller_agent_interrupt",
            data=interrupt_data,
            execution_id=self.task_id,
        )
