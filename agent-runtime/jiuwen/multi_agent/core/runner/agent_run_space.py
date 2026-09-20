#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""AgentRunSpace运行空间管理器"""

import asyncio
from typing import Callable

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import format_exception_reason
from jiuwen.multi_agent.core.enums import ProcessStatus
import logging


class AgentRunSpace:
    """Agent run space manager, responsible for managing asynchronous execution of StandaloneRunner"""

    def __init__(self, runner: "StandaloneRunner") -> None:
        self._runner = runner
        self._stopped = asyncio.Event()
        self._run_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the run space"""
        self._stopped.set()
        logger.debug("AgentRunSpace set stop")
        try:
            await self._runner.message_queue.shutdown()
            logger.debug("Stop runner message_queue success")
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.MULTI_AGENT_RUN_SPACE_SHUTDOWN_QUEUE_ERROR.code,
                message=f"Failed to shutdown message queue: {type(e)}",
            ) from e

        if not self._run_task.done():
            try:
                logger.debug("Start to stop run_task")
                await self._run_task
                logger.debug("Stop run_task success")
            except Exception as e:
                raise JiuWenBaseException(
                    error_code=StatusCode.MULTI_AGENT_RUN_SPACE_STOP_TASK_ERROR.code,
                    message=f"Failed to stop run task: {type(e)}",
                ) from e

    async def stop_when_idle(self) -> None:
        """Stop when message queue is idle"""
        try:
            await self._runner.message_queue.join()
            await self.stop()
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.MULTI_AGENT_RUN_SPACE_STOP_IDLE_ERROR.code,
                message="Failed to stop when idle",
            ) from e

    async def stop_when(
        self, condition: Callable[[], bool], check_period: float = 1.0
    ) -> None:
        """Stop when condition is met"""

        async def check_condition() -> None:
            try:
                while not condition():
                    await asyncio.sleep(check_period)
                await self.stop()
            except Exception as e:
                raise JiuWenBaseException(
                    error_code=StatusCode.MULTI_AGENT_RUN_SPACE_CHECK_CONDITION_ERROR.code,
                    message=f"Failed to stop when idle: {format_exception_reason(e)}",
                ) from e

        try:
            await asyncio.create_task(check_condition())
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.MULTI_AGENT_RUN_SPACE_EXECUTE_STOP_WHEN_ERROR.code,
                message=f"Failed to execute stop_when: {type(e)}",
            ) from e

    def get_state(self):
        """Get state"""
        pass

    def load_state(self, state) -> None:
        """Load state"""
        pass

    async def _run(self) -> None:
        """Main run loop"""
        while not self._stopped.is_set():
            try:
                # Process next message
                result = await self._runner.process_next()
                if result.status == ProcessStatus.NO_MESSAGES:
                    # 通过接受关闭信号回到while循环判断stopped标志退出循环
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"received shutdown sentinel from receive_que. runner is stopped: {self._stopped.is_set()}"
                        )
                elif result.status == ProcessStatus.ERROR:
                    logger.error(
                        f"Error processing message: {result.error_message}",
                        simple_log="Error processing message.",
                    )

            except JiuWenBaseException as e:
                logger.error(
                    f"JiuWen error in AgentRunSpace: [{e.error_code}] {e.message}",
                    exc_info=True,
                    simple_log="JiuWen error in AgentRunSpace.",
                )

            except Exception as e:
                logger.error(
                    f"AgentRunSpace execution error: {e}",
                    exc_info=True,
                    simple_log="AgentRunSpace execution error.",
                )
                jiuwen_exception = JiuWenBaseException(
                    error_code=StatusCode.MULTI_AGENT_RUN_SPACE_EXECUTION_ERROR.code,
                    message=f"AgentRunSpace execution error: {str(e)}",
                )
                logger.error(
                    f"Converted to JiuWen exception: [{jiuwen_exception.error_code}] {jiuwen_exception.message}",
                    simple_log="Converted to JiuWen exception.",
                )
