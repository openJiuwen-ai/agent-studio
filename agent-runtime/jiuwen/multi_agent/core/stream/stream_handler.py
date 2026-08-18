#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import asyncio
import os
from typing import Any, AsyncGenerator

from jiuwen.common.configs.env_constants import STREAM_FRAME_TIMEOUT_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger

DEFAULT_STREAM_FRAME_TIMEOUT = 300
STREAM_END_FRAME = "end_of_stream_frame"


class StreamHandler:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._running = True
        self.timeout = int(
            os.getenv(STREAM_FRAME_TIMEOUT_KEY, DEFAULT_STREAM_FRAME_TIMEOUT)
        )

    def is_running(self) -> bool:
        """获取running状态"""
        return self._running

    async def on_stream(self, message: Any) -> None:
        """
        将流式数据放到队列中，等待流出
        """
        if not self._running:
            logger.warning(
                "StreamHandler is not running, message not put into the queue"
            )
            return
        await self._queue.put(message)

    async def stream_output(self) -> AsyncGenerator:
        """
        从队列中取出流式数据，并通过生成器逐个流出
        """
        while self._running:
            try:
                msg = await asyncio.wait_for(self._queue.get(), self.timeout)
                self._queue.task_done()
                if msg == STREAM_END_FRAME:
                    await self.stop()
                    break
                yield msg
            except asyncio.TimeoutError as e:
                logger.error("StreamHandler get stream data time out")
                raise JiuWenBaseException(
                    StatusCode.EXECUTOR_STREAM_DATA_ERROR.code,
                    "StreamHandler get stream data time out",
                ) from e
            except asyncio.CancelledError:
                logger.warning("StreamHandler is cancelled, stop the stream data queue")
                await self.stop()
                break
            except Exception as e:
                logger.error(
                    f"Error stream output: {e}, stop the stream data queue",
                    simple_log="Error stream output",
                )
                await self.stop()
                break

    async def stop(self) -> None:
        """
        停止处理流式数据
        """
        if not self._running:
            logger.warning("StreamHandler is not running, no need to stop")
            return

        self._running = False
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        await self._queue.join()
