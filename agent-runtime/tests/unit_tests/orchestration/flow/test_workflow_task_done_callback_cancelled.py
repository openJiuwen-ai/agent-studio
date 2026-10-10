# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for Workflow._task_done_callback 对已取消任务的处理。

背景 bug：Python 语义中对已取消的 Task 调用 ``task.exception()`` 会抛
``CancelledError``（而不是返回它）。原回调第一行就是 ``task.exception()``，
任务被取消时回调本身异常中断：``_cur_tasks.remove(task)`` 与后续错误处理全部
跳过，被取消的任务永久残留在 ``_cur_tasks``（泄漏），且 asyncio 记录
"Exception in callback" 噪音日志。触发场景：``async_clean_up``（取消在飞任务）
或 ``__del__`` 的取消路径必然走到本回调。
"""

import asyncio

import pytest

from jiuwen.orchestration.flow.workflow import Workflow


def _make_bare_workflow():
    """绕过重量级 __init__，仅装配回调依赖的字段。"""
    wf = Workflow.__new__(Workflow)
    setattr(wf, "_cur_tasks", set())
    wf.chat_manager = None
    return wf


def _cur_tasks(wf):
    return getattr(wf, "_cur_tasks")


def _call_task_done_callback(wf, task):
    return getattr(wf, "_task_done_callback")(task)


@pytest.mark.asyncio
async def test_cancelled_task_is_removed_without_raising():
    async def forever():
        await asyncio.sleep(3600)

    loop = asyncio.get_running_loop()
    task = loop.create_task(forever())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()

    wf = _make_bare_workflow()
    _cur_tasks(wf).add(task)

    _call_task_done_callback(wf, task)  # 修复前：此处抛 CancelledError

    assert task not in _cur_tasks(wf)


@pytest.mark.asyncio
async def test_failed_task_still_logged_and_removed():
    async def boom():
        raise RuntimeError("node failed")

    loop = asyncio.get_running_loop()
    task = loop.create_task(boom())
    await asyncio.sleep(0)

    wf = _make_bare_workflow()
    _cur_tasks(wf).add(task)
    _call_task_done_callback(wf, task)

    assert task not in _cur_tasks(wf)


@pytest.mark.asyncio
async def test_completed_task_removed():
    async def ok():
        return 1

    loop = asyncio.get_running_loop()
    task = loop.create_task(ok())
    await task

    wf = _make_bare_workflow()
    _cur_tasks(wf).add(task)
    _call_task_done_callback(wf, task)

    assert task not in _cur_tasks(wf)
