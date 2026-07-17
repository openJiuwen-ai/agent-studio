# coding=utf-8
"""
LLM Bridge: sync/async 桥接工具

提供 _run_async 和 _collect_async_gen 工具函数，
用于在同步调用上下文中使用 agent-core 的异步 Model API。

agent-core 的 Model 是纯异步的（invoke/stream），
这些工具函数将异步调用桥接到同步调用者。

Flask 同步路由（/flask/v1/prompt/... 经 WSGIMiddleware 在 WSGI 线程跑）调模型时，
_run_async 把协程调度到主 FastAPI loop（run_coroutine_threadsafe）而非新建 loop，
使主 loop 上的 async 单例资源（如 S3StorageProvider 的 aioboto3 client）被同 loop
使用，避免 "Future attached to a different loop"。
"""

import asyncio
import concurrent.futures


# 主 FastAPI event loop，由 server_fastapi lifespan 注入（set_main_loop）。
_main_loop = None


def set_main_loop(loop) -> None:
    """注入主 FastAPI event loop（lifespan 启动时调用）。"""
    global _main_loop
    _main_loop = loop


def _run_async(coro):
    """Run an async coroutine from a sync context.

    优先调度到主 FastAPI loop（run_coroutine_threadsafe）—— Flask 同步路由经此桥接时，
    主 loop 上的 async 单例（S3StorageProvider 等）能被同 loop 使用，避免跨 loop。
    主 loop 在协程的 await 点交错处理其它请求，不会死锁。
    兜底：无主 loop 或未运行（未启动 / 单元测试），按原逻辑新建 loop。
    """
    if _main_loop is not None and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        return future.result()

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
