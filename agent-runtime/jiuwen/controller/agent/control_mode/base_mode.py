#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import abc
import asyncio
import threading
from asyncio import Queue
from typing import Dict, AsyncGenerator

from jiuwen.common.log.base import logger
from jiuwen.controller.common.config import ControlModeConfig, InvokeRequest
from jiuwen.controller.common.enum import RetCode
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType, MessageSubType
from jiuwen.controller.common.task import TaskExecution
from jiuwen.controller.task_dispatcher.task_dispatcher import TaskDispatcher
from jiuwen.controller.task_executor.task_executor import TaskExecutor
from jiuwen.controller.task_planner.planner_factory import PlannerFactory
from jiuwen.controller.utils.utils import MessageConverter

CODE = "ret_code"
RESULT = "result"
SIGNAL = "control_signal"
REFLECTION = "reflection"


class BaseMode:
    def __init__(self, **kwargs):
        """初始化控制器"""
        # 使用配置类初始化
        config = ControlModeConfig(**kwargs)

        if config.task_id is None:
            import secrets

            config.task_id = secrets.token_hex(16)
        self.config = config
        self.workflows = config.workflows
        self.plugins = config.plugins
        self.context_manager = config.context_manager
        self.model = config.model
        self.plan_config = config.plan_config
        self.task_id = config.task_id
        self.terminate = False
        self.task_end = False
        # 初始化核心组件
        self._init_components(config)

        # 最大任务循环次数，防止无限循环
        self.max_task_iterations = self.plan_config.max_iterations

    @staticmethod
    def should_pending(message: Message) -> bool:
        """判断消息是否应该直接输出给用户

        Args:
            message: 消息对象

        Returns:
            bool: 是否应该输出给用户
        """
        if message.message_type == MessageType.WORKFLOW_INTERRUPT:
            return True

        return False

    @staticmethod
    def generate_last_message(last_message, stream_results, termination_signal):
        """生成最后结果"""
        # 如果没有获取到有效的响应消息，中断循环
        if not last_message:
            if stream_results:
                # 如果有中间结果但没有最终消息，使用最后一个结果
                last_item = stream_results[-1]
                if isinstance(last_item, Message):
                    last_message = last_item
                else:
                    yield {
                        "ret_code": RetCode.FAILED,
                        "result": "任务执行未返回有效响应",
                    }
                    termination_signal = True
            else:
                yield {"ret_code": RetCode.FAILED, "result": "任务执行未返回任何结果"}
                termination_signal = True
        return

    @staticmethod
    def should_output_to_user(message: Message) -> bool:
        """判断消息是否应该直接输出给用户

        Args:
            message: 消息对象

        Returns:
            bool: 是否应该输出给用户
        """
        # 完成消息直接输出给用户
        if message.message_type == MessageType.WORKFLOW_COMPLETION:
            return True

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

    @staticmethod
    def _get_final_result(input_data, report_message):
        """处理最终返回"""
        if input_data == RetCode.SUCCESS:
            return_dict = {CODE: input_data, RESULT: report_message}
        else:
            return_dict = {CODE: RetCode.FAILED, RESULT: input_data}
        return return_dict

    @abc.abstractmethod
    async def stream(self, **kwargs) -> AsyncGenerator:
        """agent控制模式的stream方法"""
        pass

    @abc.abstractmethod
    def invoke(self, **kwargs):
        """agent控制模式的invoke方法"""
        try:
            # 创建请求对象
            request = InvokeRequest(**kwargs)
            # 创建初始用户输入消息
            runtime_data = {
                "task_id": self.task_id,
                "prompt_info": request.prompt_info,
                "plugins": request.plugins,
                "workflows": request.workflows,
                "contexts": request.contexts,
                "runtime_context": request.runtime_context,
            }
            message = MessageConverter.create_user_input_message(
                request.query, runtime_data
            )
            # 运行任务驱动循环
            final_message = self._run_task_loop(message, request.trace_handlers)
            # 处理最终结果
            return self.process_final_message(final_message)
        except Exception:
            import traceback

            error_msg = f"控制器执行失败，{traceback.format_exc()}"
            logger.error(error_msg, simple_log="控制器执行失败")
            return RetCode.FAILED, {
                "result": error_msg,
                "error": "controller execution failed",
            }

    def stream_task_execute(
        self, last_message, stream_results, task_execution, termination_signal
    ):
        """任务执行流式方法"""
        queue: Queue = Queue()
        sentinel = object()

        def runner():
            async def consume():
                try:
                    async for chunk in self.task_executor.stream_execute(
                        task_execution
                    ):
                        stream_results.append(chunk)
                        queue.put(chunk)
                finally:
                    queue.put(sentinel)

            asyncio.run(consume())

        threading.Thread(target=runner, daemon=True).start()
        while True:
            chunk = queue.get()
            if chunk is sentinel:
                break
            if isinstance(chunk, Message):
                # 保存最后一个消息用于下一轮循环
                last_message = chunk
                logger.info(
                    f"Stream task loop completed with final message: {type(last_message)}"
                )
                # 检查是否需要直接输出给用户
                if self.should_output_to_user(chunk):
                    termination_signal = True
                    break
            else:
                # 非消息类型直接输出
                yield chunk
        return

    async def process_task_execution_streaming_message(
        self, task_execution: TaskExecution
    ):
        """处理任务执行的流式输出，更新task_execution的状态属性

        Args:
            task_execution: 任务执行对象，执行后会更新其last_message属性
        """
        # 获取任务的ID用于后续可能的删除操作
        task_execution_id = task_execution.task.id

        # 使用流式执行方法处理任务
        async for message in self.task_executor.stream_execute(task_execution):
            if isinstance(message, Message):
                # 处理工作流或插件完成消息
                if message.message_type in [
                    MessageType.WORKFLOW_COMPLETION,
                    MessageType.PLUGIN_COMPLETION,
                ]:
                    logger.info(
                        f"Received completion message: {message.message_type}, "
                        f"removing task with ID {task_execution_id}"
                    )
                    # 使用ID从任务队列中删除对应任务
                    self.task_planner.task_queue.mark_task_completed(task_execution_id)
                # 保存最后一个消息用于下一轮循环
                task_execution.last_message = message

                if self.should_output_to_user(message):
                    self.terminate = True
                if self.should_pending(message):
                    self.task_planner.task_queue.mark_task_pending(task_execution_id)
            else:
                # 非消息类型直接输出
                yield message

    def get_interrupted_workflow_state(self) -> Dict:
        """获取中断状态"""
        return self.context_manager.get_interrupted_workflow_states()

    def get_task_end(self) -> bool:
        """获取任务状态"""
        return self.task_end

    def _run_task_loop(self, initial_message: Message, trace_handlers=None) -> Message:
        """运行任务驱动循环， 直到得到最终结果"""
        current_message = initial_message
        iterations = 0

        while iterations < self.max_task_iterations:
            iterations += 1
            logger.debug(
                f"Task iteration {iterations}: Processing message type {current_message.message_type}"
            )

            # 1. 任务识别 - 尝试从当前消息生成任务
            task_or_message = self.task_planner.plan_task(current_message)

            # 如果返回的是消息而非任务，说明这是最终输出
            if isinstance(task_or_message, Message):
                logger.debug(
                    f"Task loop completed with final message type: {task_or_message.message_type}"
                )
                return task_or_message

            # 2. 任务分发
            task_execution = self.task_dispatcher.dispatch(task_or_message)

            # 3. 任务执行
            response_message = self.task_executor.execute(task_execution)

            # 4. 将执行结果作为下一轮循环的输入
            current_message = response_message

        # 如果达到最大迭代次数，返回超时错误
        return Message(
            message_type=MessageType.WORKFLOW_INTERRUPT,
            content="任务处理超出最大迭代次数，可能存在循环依赖",
            runtime_data={"success": False, "error": "max_iterations_exceeded"},
        )

    def _init_components(self, config: ControlModeConfig):
        """初始化控制器组件"""
        self.task_planner = PlannerFactory.create_planner(
            config=config,
            context_manager=self.context_manager,
        )

        self.task_dispatcher = TaskDispatcher(context_manager=self.context_manager)
        self.task_executor = TaskExecutor(
            context_manager=self.context_manager,
            workflows=config.workflows,
            llm=config.model,
        )

    def _process_stream_message(self, item) -> dict:
        if isinstance(item, dict):
            if item.get("function_call") is not None:
                return_dict = dict(
                    ret_code=RetCode.FUNC_CALL_GEN, function_call_generation=item
                )
            elif item.get("result") is not None:
                return_dict = dict(ret_code=RetCode.API_EXEC_RESULT, api_result=item)
            elif item.get("error_msg") is not None:
                return_dict = dict(ret_code=RetCode.API_EXCEPTION, exception=item)
            elif item.get("content_opt_result") is not None:
                return_dict = dict(
                    ret_code=RetCode.CONT_OPT_RESULT, content_optimization=item
                )
            elif item.get(SIGNAL) is not None:
                return_dict = dict(
                    ret_code=RetCode.UX_SIGNAL, control_signal=item.get(SIGNAL)
                )
            elif item.get("role", "") == "assistant":
                if item.get("think", ""):
                    return_dict = dict(
                        ret_code=RetCode.STREAM_THINK_LLM,
                        stream_output_char=item.get("think", ""),
                    )
                else:
                    return_dict = dict(
                        ret_code=RetCode.STREAM_OUTPUT_LLM,
                        stream_output_char=item.get("content", ""),
                    )
            elif item.get(REFLECTION) is not None:
                return_dict = dict(
                    ret_code=RetCode.STREAM_REFLECTION, reflection=item.get(REFLECTION)
                )
            elif item.get("intermediate_message") is not None:
                return_dict = dict(
                    ret_code=RetCode.INTERMEDIATE_MESSAGE,
                    intermediate_message=item.get("intermediate_message"),
                )
            else:
                return_dict = self._get_final_result(
                    item, self.context_manager.get_result_message()
                )
        else:
            return_dict = self._get_final_result(
                item, self.context_manager.get_result_message()
            )
        return return_dict
