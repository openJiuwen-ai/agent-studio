# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""studio 侧执行期状态通道（静态图复用配套，spec §4）。

背景：Workflow 实例缓存复用后，组件实例/图结构跨执行共享，执行期状态
（session、context、流式末帧输出）不能再落在可复用对象的实例属性上。

**执行期 session/context 通道已归上游**：openjiuwen 自
`fix/0.1.17.post2-compile-reentrant` 起自带
``openjiuwen.core.session.execution_session_ctx``（``_workflow_session`` +
``_component_exec`` 三元组 + ``resolve_routing_session``），引擎的
``BranchRouter.__call__`` / ``BaseWorkflow.new_router`` 都经它解析。studio 侧
一律直接使用该模块——本模块不再重复定义，避免出现"写了但引擎读不到"的第二
通道（本文件旧版正是如此，Patch C 被上游取代后即成死代码）。

本模块只保留两个**上游没有**的 studio 专用通道：

1. ``_stream_final_output``：流式组件的末帧输出。**不 reset**——引擎
   ``Vertex._post_stream`` 在 generator 耗尽后读取（vertex.py:624-628），
   reset 会丢值。依赖 NodeTask 的 context 隔离（``asyncio.create_task``
   拷贝上下文），跨执行天然隔离。
2. ``_component_state``：组件执行期状态对象（如 FlowQA 的 QAState）。组件在
   invoke 入口 set、finally reset（token 栈式）；逃逸面方法
   （``get_state`` / ``get_node_status`` / ``should_interrupt``）经通道读取，
   invoke 外回退默认值。同样依赖 NodeTask 的 context 隔离
   （PR #1 评审修复轮，Critical-1）。
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Optional

_stream_final_output: ContextVar[Optional[dict]] = ContextVar(
    "jiuwen_stream_final_output", default=None
)
_component_state: ContextVar[Optional[Any]] = ContextVar(
    "jiuwen_component_state", default=None
)


def set_stream_final_output(value: Optional[dict]) -> None:
    _stream_final_output.set(value)


def get_stream_final_output() -> Optional[dict]:
    return _stream_final_output.get()


def set_component_state(state: Any) -> Token:
    """组件执行期状态对象通道（spec §4 通道，PR #1 评审修复轮）。

    存放组件自身的执行期状态对象（如 ``FlowQA`` 的 ``QAState``）。组件在
    invoke 入口 set、finally reset（token 栈式）；逃逸面方法（``get_state`` /
    ``get_node_status`` / ``should_interrupt``）经 ``current_component_state``
    读取——实例跨执行复用后这些值不能落共享实例字段（并发执行互踩）。
    invoke 外（无执行期上下文）读取方自行回退默认值。
    """
    return _component_state.set(state)


def reset_component_state(token: Token) -> None:
    _component_state.reset(token)


def current_component_state() -> Optional[Any]:
    return _component_state.get()
