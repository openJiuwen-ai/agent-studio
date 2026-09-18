# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""后台任务工具：把非关键持久化移出用户可感知的关键路径。

流式响应的终态事件（done/end）此前串行等待会话历史落库、agent 会话状态
checkpoint 等全量 Redis 读写，导致「内容输出完毕 → finish」出现随会话历史
增长的尾延迟。本工具提供 fire-and-forget 执行：

- ``asyncio.create_task`` 后保持强引用，防止任务在完成前被 GC
  （asyncio 官方文档要求调用方持有 Task 引用）；
- 独立 Task 不随请求生成器的取消而取消（未 await 即无取消传播，
  客户端断开不影响后台落库），因此无需 ``asyncio.shield``；
- 任务异常兜底记录（调用方协程通常自带 try/except，此处仅防御意外逃逸）；
- 无运行中事件循环时（如解释器关闭期间的生成器收尾）放弃后台执行并
  关闭协程对象，避免 "coroutine was never awaited" 告警。
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, Optional

from openjiuwen.core.common.logging import workflow_logger

# 强引用集合：防止 create_task 返回的 Task 在完成前被垃圾回收。
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def run_in_background(
    coro: Coroutine[Any, Any, Any], name: Optional[str] = None
) -> Optional[asyncio.Task]:
    """后台执行协程并立即返回，不阻塞调用方关键路径。

    Args:
        coro: 待执行的协程对象（通常为自带异常兜底的持久化操作）。
        name: 任务名（仅用于日志定位）。

    Returns:
        已调度的 Task；无运行中事件循环时返回 None（协程已被关闭）。
    """
    try:
        task = asyncio.create_task(coro, name=name)
    except RuntimeError:
        coro.close()
        workflow_logger.warning(
            f"Background task {name or '<unnamed>'} skipped: no running event loop"
        )
        return None
    _BACKGROUND_TASKS.add(task)

    def _on_done(done: asyncio.Task) -> None:
        _BACKGROUND_TASKS.discard(done)
        if not done.cancelled() and done.exception() is not None:
            workflow_logger.error(
                f"Background task {done.get_name()} failed: {done.exception()}",
                exc_info=done.exception(),
            )

    task.add_done_callback(_on_done)
    return task
