# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for agent_runtime.common.background_task — fire-and-forget 后台任务工具。"""

import asyncio
from unittest.mock import patch

import pytest

from agent_runtime.common import background_task
from agent_runtime.common.background_task import run_in_background


class TestRunInBackground:
    """run_in_background 行为测试。"""

    @staticmethod
    @pytest.mark.asyncio
    async def test_executes_coroutine_and_discards_reference():
        """后台执行协程；完成后从强引用集合移除。"""
        done = asyncio.Event()

        async def work():
            done.set()

        task = run_in_background(work(), name="t-exec")
        assert isinstance(task, asyncio.Task)
        assert task in background_task._BACKGROUND_TASKS

        for _ in range(100):
            if done.is_set():
                break
            await asyncio.sleep(0.01)
        assert done.is_set()

        await task
        # done_callback 经 call_soon 调度，让出一次控制权后引用应被移除
        for _ in range(10):
            if task not in background_task._BACKGROUND_TASKS:
                break
            await asyncio.sleep(0)
        assert task not in background_task._BACKGROUND_TASKS

    @staticmethod
    def test_returns_none_without_running_loop():
        """无运行中事件循环时放弃执行、关闭协程并返回 None。"""

        async def work():
            pass

        coro = work()
        result = run_in_background(coro, name="t-noloop")
        assert result is None
        # 协程已被 close，避免 "coroutine was never awaited" 告警
        assert coro.cr_frame is None

    @staticmethod
    @pytest.mark.asyncio
    async def test_logs_unexpected_exception():
        """协程异常逃逸时兜底记录 error 日志。"""

        async def boom():
            raise RuntimeError("boom")

        task = run_in_background(boom(), name="t-boom")
        with patch.object(background_task.workflow_logger, "error") as mock_error:
            with pytest.raises(RuntimeError):
                await task
            # done_callback 经 call_soon 调度，让出控制权触发
            for _ in range(10):
                if mock_error.called:
                    break
                await asyncio.sleep(0)
        assert mock_error.called

    @staticmethod
    @pytest.mark.asyncio
    async def test_survives_caller_cancellation():
        """后台任务不随调用方协程取消而取消（fire-and-forget 语义）。"""
        finished = asyncio.Event()

        async def work():
            await asyncio.sleep(0.05)
            finished.set()

        async def caller():
            run_in_background(work(), name="t-cancel")
            await asyncio.sleep(3600)

        caller_task = asyncio.create_task(caller())
        await asyncio.sleep(0)  # 让 caller 启动并创建后台任务
        caller_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller_task

        # 调用方已取消，后台任务仍应完成
        for _ in range(200):
            if finished.is_set():
                break
            await asyncio.sleep(0.01)
        assert finished.is_set()
