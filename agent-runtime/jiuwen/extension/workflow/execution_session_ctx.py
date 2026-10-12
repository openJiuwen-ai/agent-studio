# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""执行期 session 的 ContextVar 通道（静态图复用配套，spec §4）。

背景：Workflow 实例缓存复用后，组件实例/图结构跨执行共享，执行期状态
（session、context、流式末帧输出）不能再落在可复用对象的实例属性上。

三个通道，按"谁写入、谁读取"划分：

1. ``_workflow_session``：Patch B 在 ``CompiledGraph._invoke`` 入口 set、
   finally reset，值为本次执行的 workflow 级 session（WorkflowSession /
   SubWorkflowSession）。子工作流嵌套经 token 栈式恢复（子执行期间组件
   解析到子 session）。供 Patch C 的路由第二优先级解析。
2. ``_component_exec``：(session, context) 二元组。分支路由属主组件
   （IntentDetection/_RoutedIntentDetection）在 invoke 入口 set 且**不
   reset**——路由 dispatch 发生在 invoke 返回之后的同一 NodeTask 里
   （task.py 的 NodeTask.run：先跑节点函数再 dispatch），值必须存活到
   dispatch；其他组件（LLMChain 等）set 后在 finally reset，避免本节点
   的路由误解析到组件级 session（与现状 add_conditional_connection 的
   ProxySession 语义对齐）。NodeTask 每节点独立 context
   （asyncio.create_task 拷贝），天然跨执行隔离。
3. ``_stream_final_output``：流式组件的末帧输出。**不 reset**——引擎
   Vertex._post_stream 在 generator 耗尽后读取（vertex.py:624-628），
   reset 会丢值。同样依赖 NodeTask 的 context 隔离。
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Optional, Tuple

_workflow_session: ContextVar[Optional[Any]] = ContextVar(
    "jiuwen_workflow_session", default=None
)
_component_exec: ContextVar[Tuple[Optional[Any], Optional[Any]]] = ContextVar(
    "jiuwen_component_exec", default=(None, None)
)
_stream_final_output: ContextVar[Optional[dict]] = ContextVar(
    "jiuwen_stream_final_output", default=None
)


def set_workflow_session(session: Any) -> Token:
    return _workflow_session.set(session)


def reset_workflow_session(token: Token) -> None:
    _workflow_session.reset(token)


def current_workflow_session() -> Optional[Any]:
    return _workflow_session.get()


def set_component_exec(session: Any, context: Any) -> Token:
    return _component_exec.set((session, context))


def reset_component_exec(token: Token) -> None:
    _component_exec.reset(token)


def current_component_exec() -> Tuple[Optional[Any], Optional[Any]]:
    return _component_exec.get()


def set_stream_final_output(value: Optional[dict]) -> None:
    _stream_final_output.set(value)


def get_stream_final_output() -> Optional[dict]:
    return _stream_final_output.get()


def resolve_routing_session(fallback: Any = None) -> Any:
    """路由 session 解析链（Patch C）：组件级 → workflow 级 → 调用方回退。

    与现状语义对齐：
    - add_conditional_connection 注册的路由 → ProxySession（workflow 级），
      对应 workflow 级分支；
    - IntentDetection/_RoutedIntentDetection 每次执行 set_session(组件
      NodeSession) → 对应组件级分支（需存活到同 task 内的 dispatch）。
    """
    session, _ = _component_exec.get()
    if session is not None:
        return session
    workflow_session = _workflow_session.get()
    if workflow_session is not None:
        return workflow_session
    return fallback
