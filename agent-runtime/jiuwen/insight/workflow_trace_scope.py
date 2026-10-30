#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
workflow LLM 节点遥测的作用域载体。

controller 链上的 TraceManager 无法经工作流运行时上下文透传（组件
init 的 runtime_context 形参在 openjiuwen 路径是死代码，且每次 astream
都会被重置；数据面 params/envs 会进序列化）。本模块用 ContextVar 做进程
内协程作用域：task_executor 在工作流 astream 消费点进入作用域，engine
为组件执行创建的 asyncio 任务在创建时拷贝当前 context，组件内（如
llm_chain）即可取到并派生自己的遥测 manager。ContextVar 不经过任何
序列化面，运行时上下文 / checkpoint / IR 均不受影响。
"""

import inspect
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Optional

if TYPE_CHECKING:
    from jiuwen.insight.manager import TraceManager

# default=None：独立工作流（无 agent 链）或任务未携带 trace_handlers 时，
# current_workflow_trace_manager() 返回 None，消费方跳过遥测，行为不变
_WORKFLOW_TRACE_MANAGER: ContextVar[Optional["TraceManager"]] = ContextVar(
    "workflow_trace_manager", default=None
)


def current_workflow_trace_manager() -> Optional["TraceManager"]:
    """当前协程上下文中的工作流级 TraceManager；未绑定返回 None。"""
    return _WORKFLOW_TRACE_MANAGER.get()


@contextmanager
def workflow_trace_scope(trace_manager: Optional["TraceManager"]):
    """把工作流级 TraceManager 绑定到当前协程上下文（None 容忍，空操作）。

    Args:
        trace_manager: controller 链上的 TraceManager（通常为 agent 根
            manager 的 child），或 handler 列表——消费方统一经
            TraceManager.generate_manager 归一；None 时本作用域为空操作。

    Yields:
        绑定的对象（便于调用方判空）；退出时恢复先前的绑定值，支持嵌套
        （子工作流在自身作用域内执行，退出后不影响外层）。
    """
    if trace_manager is None:
        yield None
        return
    token = _WORKFLOW_TRACE_MANAGER.set(trace_manager)
    try:
        yield trace_manager
    finally:
        _WORKFLOW_TRACE_MANAGER.reset(token)


async def scoped_astream(
    source: Callable[[], Any], trace_manager: Optional["TraceManager"]
) -> AsyncIterator[Any]:
    """把作用域绑定收敛到内层异步流步进期间的消费包装（检视意见）。

    `with workflow_trace_scope(...)` 直接包住含 yield 的 async for 时，
    生成器在 yield 处挂起而 with 块未退出，ContextVar 绑定会滞留在
    消费方 Task 的上下文里——上层消费者在两次 yield 之间 create_task
    的兄弟任务拷贝当前 context、继承该作用域，可能把不相关的 LLM
    节点遥测错误归属到同一条 controller 链 span。本包装只在建立与
    步进内层流期间绑定，向上 yield 前解绑，跨 yield 零残留；对内层
    语义不变——内层执行体及期间创建的组件任务照常取到绑定。

    Args:
        source: 零参可调用，返回内层异步迭代器（返回值可 awaitable，
            如 `lambda: workflow.astream(q, **kwargs)`；或直接返回
            async generator 的调用）。
        trace_manager: 同 workflow_trace_scope，None 容忍（照常透传）。
    """
    with workflow_trace_scope(trace_manager):
        it = source()
        if inspect.isawaitable(it):
            it = await it
    try:
        while True:
            with workflow_trace_scope(trace_manager):
                try:
                    item = await it.__anext__()
                except StopAsyncIteration:
                    return
            yield item
    finally:
        aclose = getattr(it, "aclose", None)
        if aclose is not None:
            with workflow_trace_scope(trace_manager):
                try:
                    await aclose()
                except Exception:
                    pass
