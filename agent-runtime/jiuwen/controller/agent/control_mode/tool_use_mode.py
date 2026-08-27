#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import logging
from typing import AsyncGenerator

from jiuwen.common.log.base import logger
from jiuwen.controller.agent.control_mode.base_mode import BaseMode
from jiuwen.controller.common.config import StreamRequest
from jiuwen.controller.common.enum import PlanAndExecuteCode, RetCode
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.task import Task
from jiuwen.controller.utils.utils import MessageConverter


class ToolUseMode(BaseMode):
    def __init__(self, **kwargs):
        """初始化控制器"""
        # 使用配置类初始化
        super(ToolUseMode, self).__init__(**kwargs)

        # 初始化核心组件
        self.terminate = None
        self._init_components(self.config)

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
        return last_message, termination_signal

    async def stream(self, **kwargs) -> AsyncGenerator:
        """流式调用控制器处理用户查询"""
        try:
            # 创建流式请求对象
            request = StreamRequest(**kwargs)

            # 创建初始用户输入消息
            runtime_data = {
                "task_id": self.task_id,
                "contexts": request.contexts,
                "runtime_context": request.runtime_context,
                "multimodal_image": request.multimodal_image,
            }
            self.task_planner.update_plugins(request.plugins)
            self.task_planner.update_mcps(request.mcps)

            message = MessageConverter.create_user_input_message(
                request.query, runtime_data
            )

            # 运行流式任务循环 - 使用更合适的方法名
            yield_result = self._stream_task_loop(message)
            async for item in yield_result:
                yield self._process_stream_message(item)

        except Exception as e:
            import traceback

            error_msg = f"控制器流式执行失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg, simple_log=f"控制器流式执行失败 : {type(e)}")
            yield {"ret_code": RetCode.FAILED, "result": error_msg, "error": str(e)}

    async def _stream_task_loop(self, initial_message: Message) -> AsyncGenerator:
        """执行任务驱动循环的流式版本，直到得到最终结果

        Args:
            initial_message: 初始消息

        Returns:
            AsyncGenerator: 生成流式结果
        """
        current_message = initial_message
        iterations = 0
        runtime_data = initial_message.runtime_data

        while iterations < self.max_task_iterations:
            # 与 base_mode._run_task_loop 保持一致，迭代开始信息为 DEBUG
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Stream task iteration %s: Processing message type %s",
                    iterations,
                    current_message.message_type,
                )
            # 1. 任务识别 - 使用流式任务规划
            final_task_or_message = None

            if not current_message.runtime_data:
                current_message.runtime_data = runtime_data

            # 处理规划器的流式输出
            async for result in self.task_planner.stream_plan_task(current_message):
                # 如果是中间结果（非Task或Message），转换后输出
                if isinstance(result, PlanAndExecuteCode):
                    if result == PlanAndExecuteCode.PLANNING:
                        iterations += 1
                    if result == PlanAndExecuteCode.SUCCESS:
                        yield RetCode.SUCCESS
                        return
                elif isinstance(result, Message):
                    final_task_or_message = result
                    yield result
                elif isinstance(result, Task):
                    final_task_or_message = result
                else:
                    yield result

            # 2. 任务分发
            task_execution = self.task_dispatcher.dispatch(final_task_or_message)

            # 3. 使用流式方法执行任务并处理结果
            async for item in self.process_task_execution_streaming_message(
                task_execution
            ):
                yield item

            # 使用最后一个消息作为下一轮循环的输入
            # 完整 last_message repr 内容较大，降级为 DEBUG
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Stream task loop continue with current message: %s",
                    task_execution.last_message,
                    simple_log="Stream task loop continue with current message",
                )
            current_message = task_execution.last_message

        # 如果达到最大迭代次数，返回超时错误
        yield RetCode.FAILED
