# coding=utf-8
"""
LLM Bridge: sync/async 桥接工具

提供 _run_async 和 _collect_async_gen 工具函数，
用于在同步调用上下文中使用 agent-core 的异步 Model API。

agent-core 的 Model 是纯异步的（invoke/stream），
这些工具函数将异步调用桥接到同步调用者。
"""

import asyncio
import concurrent.futures


def _run_async(coro):
    """Run an async coroutine from a sync context.

    Handles both cases: no running event loop (direct asyncio.run)
    and an already-running loop (offload to a thread pool).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def _collect_async_gen(async_gen):
    """Collect all items from an async generator into a list (sync)."""
    async def _collect():
        return [item async for item in async_gen]
    return _run_async(_collect())
