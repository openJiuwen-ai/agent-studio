# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""执行期 session 的 ContextVar 通道（静态图复用配套，spec §4）。

背景：Workflow 实例缓存复用后，组件实例/图结构跨执行共享，执行期状态
（session、context、流式末帧输出）不能再落在可复用对象的实例属性上。

三个通道，按"谁写入、谁读取"划分：

1. ``_workflow_session``：Patch B 在 ``CompiledGraph._invoke`` 入口 set、
   finally reset，值为传入 ``CompiledGraph._invoke`` 的 session——主/
   子工作流路径为 WorkflowSession / SubWorkflowSession，循环体路径
   （AdvancedLoopComponent.on_invoke 以 NodeSession 调 compile/_invoke，
   loop_comp.py:444-464）为 NodeSession；与各路径现状 set_session 的值
   一致。子工作流嵌套经 token 栈式恢复（子执行期间组件解析到子
   session）。供 Patch C 的路由第二优先级解析。
2. ``_component_exec``：(session, context) 二元组。分支路由属主组件
   （IntentDetection/_RoutedIntentDetection）在 invoke 入口 set 且**不
   reset**——路由 dispatch 发生在 invoke 返回之后的同一 NodeTask 里
   （task.py 的 NodeTask.run：先跑节点函数再 dispatch），值必须存活到
   dispatch；其他组件（LLMChain 等）set 后在 finally reset，避免本节点
   的路由误解析到组件级 session（与现状 add_conditional_connection 的
   ProxySession 语义对齐）。NodeTask 每节点独立 context
   （asyncio.create_task 拷贝），天然跨执行隔离。

   值类型契约：引擎 ``WorkflowComponent.on_invoke`` 传给 invoke 的是
   ``Session(node_session, False)`` 包装器（component.py:95-99，无
   state()、无 __getattr__ 委托）——通道按**组件面包装器**存储（与旧
   ``self._session = session`` 同物；组件自身读点 trace /
   get_global_state / interact 等只有包装器提供，NodeSession 无这些方法；
   与 LLMChain 的通道存包装器契约一致）。该通道的 Patch C 消费方
   （BranchRouter 分支条件 → ``AtomicNode._validate_session_and_state``）
   则要求 ``isinstance(session, BaseSession)``——由
   ``resolve_routing_session`` **读取端解包**满足（``getattr(session,
   "_inner", session)``，与旧 ``BranchRouter.set_session`` 解包语义一致；
   NodeSession 自身无 ``_inner``，不会过度解包）。写入/读取两端契约分离，
   写入端不得解包。

   前提与已知限制：
   - **前提（per-node 同 task）**：值仅在"节点函数与 dispatch 同 task"时
     可达。vertex.py 有两条同 task 直 await 分支——``max_retries < 0``
     早返回（:243-244）与 ``timeout < 0``（默认 -1.0，:248-249）；其余
     （``max_retries >= 0`` 且 ``timeout >= 0``）经 ``asyncio.wait_for``
     新建子 task（:250-253），invoke 内的 set 留在子 task 上下文、dispatch
     读不到 → 回退 workflow 级解析（粒度降级，非严格等价；条件求值安全）。
   - **作用域（嵌套隔离）**：``TaskExecutorPool.submit`` 以 ``create_task``
     从**引擎 task** 派生节点 task——组件级值只在属主节点自己的 task 上下文
     及其子协程内，**不进入嵌套子执行**（子工作流/循环的承载节点 task 继承
     自引擎 task，引擎 task 从不携带组件级值）。其生命周期为整个属主
     NodeTask（invoke 期间即被组件自身读取），不限于 dispatch 窗口。
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

    组件级值解包到 NodeSession 后返回：分支条件求值（Condition.__call__ →
    AtomicNode._validate_session_and_state）要求 ``isinstance(BaseSession)``，
    而引擎 on_invoke 传入的是 Session 包装器（写入端已解包，此处兜底保证
    未来任何写入方存包装器也安全；NodeSession 自身无 ``_inner``，不会过度
    解包）。
    """
    session, _ = _component_exec.get()
    if session is not None:
        return getattr(session, "_inner", session)
    workflow_session = _workflow_session.get()
    if workflow_session is not None:
        return workflow_session
    return fallback
