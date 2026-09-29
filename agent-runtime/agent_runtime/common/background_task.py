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

后台化打破了「finish 到达时数据已落库」的旧不变量：下一轮请求可能在
上一轮落库完成前读取同一会话数据（Redis 整段读改写），产生脏读或后写
覆盖先写的丢消息。为此提供两层顺序性保护，恢复单会话顺序性：

- 进程内：per-key 在飞任务注册表（``_TRACKED_TASKS``），下一轮请求入口
  经 ``await_pending()`` 有界等待；
- 跨进程（平台显式支持多 worker / nginx 多实例 / k8s 多副本拓扑）：
  Redis 在飞计数器。INCR 在调度时同步完成——严格先于 finish 事件发出，
  下一轮不可能先于标记出现；DECR 在任务 finally 中执行。读侧在进程内
  join 后有界轮询计数器。进程崩溃时计数由 TTL 回收；读侧以自身超时
  封顶，永不无限阻塞。

``backgrounding_enabled()`` 为平台级回退开关（环境变量
``PERSIST_BACKGROUND_ENABLE``，默认开启）：关闭时调用方回到同步落库，
行为与后台化之前完全一致。
"""

import asyncio
import os
from collections.abc import Coroutine
from typing import Any, Optional

from openjiuwen.core.common.logging import workflow_logger

# 强引用集合：防止 create_task 返回的 Task 在完成前被垃圾回收。
_BACKGROUND_TASKS: set[asyncio.Task] = set()

# 按 key（如 conversation_id）的在飞任务注册表：供同进程下一轮请求入口 join。
_TRACKED_TASKS: dict[str, set[asyncio.Task]] = {}

# 跨进程在飞计数 key 前缀与 TTL。TTL 仅用于进程崩溃后的计数回收，
# 远大于正常落库耗时；DECR 越过 0 为负无害（读侧判 <= 0 即视为无在飞）。
INFLIGHT_KEY_PREFIX = "agentBuilder:conv-inflight:"
INFLIGHT_TTL_SECONDS = 60

# join 兜底超时：后台落库正常为百毫秒级，5s 覆盖极端慢 Redis；
# 超时后记 error 放行（退化为偶发脏读）而非无限阻塞下一轮。
JOIN_TIMEOUT_SECONDS = 5.0

# 跨进程在飞计数的轮询间隔。
POLL_INTERVAL_SECONDS = 0.05


def _get_redis():
    """惰性获取 Redis 客户端；未初始化或导入失败返回 None（跨进程 join 降级）."""
    try:
        from common_utils.redis_manager import RedisClientManager

        mgr = RedisClientManager.get_instance()
        if mgr.is_initialized:
            return mgr.get_client()
    except Exception as e:
        workflow_logger.warning(
            f"background_task: Redis client unavailable, "
            f"cross-process join degraded to in-process only: {e}"
        )
    return None


def backgrounding_enabled() -> bool:
    """平台级回退开关：PERSIST_BACKGROUND_ENABLE=false 时回到同步落库."""
    return os.getenv("PERSIST_BACKGROUND_ENABLE", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )


def run_in_background(
    coro: Coroutine[Any, Any, Any],
    name: Optional[str] = None,
    track_key: Optional[str] = None,
) -> Optional[asyncio.Task]:
    """后台执行协程并立即返回，不阻塞调用方关键路径。

    Args:
        coro: 待执行的协程对象（通常为自带异常兜底的持久化操作）。
        name: 任务名（仅用于日志定位）。
        track_key: 非空时登记到该 key 的在飞集合，供 await_pending join。

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
    if track_key:
        _TRACKED_TASKS.setdefault(track_key, set()).add(task)

    def _on_done(done: asyncio.Task) -> None:
        _BACKGROUND_TASKS.discard(done)
        pending = _TRACKED_TASKS.get(track_key) if track_key else None
        if pending is not None:
            pending.discard(done)
            if not pending:
                _TRACKED_TASKS.pop(track_key, None)
        if not done.cancelled() and done.exception() is not None:
            workflow_logger.error(
                f"Background task {done.get_name()} failed: {done.exception()}",
                exc_info=done.exception(),
            )

    task.add_done_callback(_on_done)
    return task


async def _incr_inflight(track_key: str) -> None:
    """跨进程在飞计数 +1 并刷新 TTL；Redis 不可用时静默降级（仅进程内保护）。"""
    redis = _get_redis()
    if redis is None:
        return
    key = f"{INFLIGHT_KEY_PREFIX}{track_key}"
    try:
        await redis.incr(key)
        await redis.expire(key, INFLIGHT_TTL_SECONDS)
    except Exception as e:
        workflow_logger.warning(
            f"inflight INCR failed, key={key}, cross-process join degraded: {e}"
        )


async def _decr_inflight(track_key: str) -> None:
    """跨进程在飞计数 -1 并补 TTL（防 DECR 越过 0 后残留无 TTL 的负值 key）。"""
    redis = _get_redis()
    if redis is None:
        return
    key = f"{INFLIGHT_KEY_PREFIX}{track_key}"
    try:
        await redis.decr(key)
        await redis.expire(key, INFLIGHT_TTL_SECONDS)
    except Exception as e:
        workflow_logger.warning(f"inflight DECR failed, key={key}: {e}")


async def run_in_background_tracked(
    coro: Coroutine[Any, Any, Any],
    name: Optional[str] = None,
    track_key: Optional[str] = None,
) -> Optional[asyncio.Task]:
    """带跨进程在飞计数的后台执行：先 INCR（返回前完成，严格先于 finish
    事件发出），再 fire-and-forget；任务 finally 中 DECR。

    track_key 为空或 Redis 不可用时退化为 run_in_background（仅进程内保护）。
    """
    if not track_key:
        return run_in_background(coro, name=name)
    await _incr_inflight(track_key)

    async def _tracked() -> Any:
        try:
            return await coro
        finally:
            # 任务被取消时（如事件循环收尾）finally 中的 await 可能立即抛
            # CancelledError 导致 DECR 丢失，由 key TTL 兜底回收。
            await _decr_inflight(track_key)

    task = run_in_background(_tracked(), name=name, track_key=track_key)
    if task is None:
        # 理论上不可达（能 await INCR 即有运行中事件循环）：包装协程已被
        # 关闭，内层协程也需显式关闭避免 never-awaited 告警；计数由 TTL 回收。
        coro.close()
    return task


async def await_pending(
    track_key: str, timeout: float = JOIN_TIMEOUT_SECONDS
) -> None:
    """有界等待 track_key 名下在飞后台落库完成（下一轮请求入口调用）。

    两层等待：先进程内注册表 join（快路径，零 Redis 开销），再轮询跨进程
    在飞计数（多 worker / 多实例拓扑下其他进程的后台任务）。

    快照语义：join 调用时刻的在飞集合；等待期间新加入的任务由下一轮 join。
    必须用 ``asyncio.wait`` 而非 ``wait_for(gather(...))``：后者的超时与
    调用方取消都会传播取消到子任务，把在飞的后台落库杀死——恰在慢 Redis
    （超时触发）或下一轮客户端断连（调用方取消）时丢消息。``asyncio.wait``
    超时或自身被取消都不动子任务；子任务异常也不会从 wait 抛出（已由
    done_callback 记录）。
    """
    if not track_key:
        return
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    pending = [t for t in _TRACKED_TASKS.get(track_key, ()) if not t.done()]
    if pending:
        _, still_pending = await asyncio.wait(
            pending, timeout=max(0.0, deadline - loop.time())
        )
        if still_pending:
            workflow_logger.error(
                f"await_pending in-process timeout after {timeout}s, "
                f"key={track_key}, proceed with {len(still_pending)} "
                f"in-flight background tasks"
            )
            return

    redis = _get_redis()
    if redis is None:
        return
    key = f"{INFLIGHT_KEY_PREFIX}{track_key}"
    while True:
        try:
            raw = await redis.get(key)
        except Exception as e:
            workflow_logger.warning(
                f"inflight GET failed, key={key}, "
                f"cross-process join degraded to in-process only: {e}"
            )
            return
        try:
            inflight = int(raw) if raw is not None else 0
        except (TypeError, ValueError):
            workflow_logger.warning(
                f"inflight counter corrupted, key={key}, value={raw!r}, "
                f"treated as no in-flight task"
            )
            return
        if inflight <= 0:
            return
        # do-while：至少完成一次轮询再判超时，避免进程内 join 恰好用尽
        # 预算时未查远端就误报 cross-process timeout
        if loop.time() >= deadline:
            break
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    workflow_logger.error(
        f"await_pending cross-process timeout after {timeout}s, key={track_key}, "
        f"proceed with remote in-flight background tasks"
    )
