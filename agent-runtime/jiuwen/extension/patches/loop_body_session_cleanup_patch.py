# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
Loop body session cleanup (jiuwen-side patch, no openjiuwen core edits).

包含两个独立的 patch：

1. LoopGroup body round cleanup (PR !1163):
   loop-body components share io_state across rounds. Nodes skipped on the
   current branch/path can still leave outputs in session; downstream aggregate reads
   stale values via get_inputs().
   在每次 LoopGroup body run 之前，清掉注册的 body components 的 session 数据
   (不是整个 scope root，所以 state_store 这类虚拟键能保留)，并重置 body
   node ids 在 executed_nodes / finished_stream_nodes 中的标记。

   Sub-workflow interrupt/resume cleanup stays in workflow_sub_stream_patch.py.

2. AdvancedLoopComponent per-round io_state cleanup:
   AdvancedLoopComponent.on_invoke 进入新一轮时需清掉本节点上一轮残留
   io_state，否则循环上一轮的输出会污染下一轮 get_inputs / aggregate。
   core 侧 on_invoke 已含此逻辑，但 runtime 侧需要按 parent_id scope 取值
   并复用 get_value_by_nested_path 做路径解析，由本 patch 接管 on_invoke
   整体实现。

两个 patch 作用对象不同 (LoopGroup 在外层, AdvancedLoopComponent 在内层),
各自独立的 _PATCH_APPLIED_* flag, 可按需 apply。

Applied once at import from ir_converter / sub_workflow.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any, Iterable, Optional

from openjiuwen.core.common.constants.constant import FINISH_INDEX, LOOP_ID
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import BaseError, build_error
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session import BaseSession, NodeSession
from openjiuwen.core.session.utils import get_value_by_nested_path

# 循环组件执行期状态键（与 openjiuwen loop_comp 的 BROKEN 常量一致）
_BROKEN_KEY = "_broken"

# --- LoopGroup body round cleanup ---
_PATCH_APPLIED = False
_orig_loop_group_on_invoke = None


def _loop_comp_workflow_session(session: BaseSession) -> BaseSession:
    """Session that owns workflow_state (executed_nodes) for the loop component vertex."""
    if hasattr(session, "node_id") and session.node_id() == "body" and session.parent() is not None:
        return session.parent()
    return session


def clear_loop_body_round_marks(session: BaseSession, body_node_ids: Iterable[str]) -> None:
    """Drop loop-body component ids from executed_nodes / finished_stream_nodes."""
    body_set = {node_id for node_id in body_node_ids if node_id}
    if not body_set:
        return
    workflow_state = _loop_comp_workflow_session(session).state()
    updates: dict[str, list[str]] = {}
    executed_nodes = workflow_state.get_workflow_state("executed_nodes") or []
    if executed_nodes:
        updates["executed_nodes"] = [nid for nid in executed_nodes if nid not in body_set]
    finished_stream_nodes = workflow_state.get_workflow_state("finished_stream_nodes") or []
    if finished_stream_nodes:
        updates["finished_stream_nodes"] = [nid for nid in finished_stream_nodes if nid not in body_set]
    if updates:
        workflow_state.update_and_commit_workflow_state(updates)


def clear_loop_body_component_io_state(
    session: BaseSession,
    scope_id: str,
    body_node_ids: Iterable[str],
) -> None:
    """Remove io_state outputs for registered loop-body graph components only.

    Keys are nested paths like ``loop_node.branch_a`` under the shared io_state root.
    Does not wipe the whole ``loop_node`` scope so virtual keys (e.g. state_store) persist.
    """
    if not scope_id:
        return
    io_state = getattr(_loop_comp_workflow_session(session).state(), "_io_state", None)
    if io_state is None:
        return
    cleared = False
    for node_id in body_node_ids:
        if not node_id:
            continue
        nested_key = f"{scope_id}.{node_id}"
        io_state.update_by_id(nested_key, {nested_key: None})
        cleared = True
    if cleared:
        io_state.commit()


def clear_loop_body_session_for_round(
    session: BaseSession,
    scope_id: str,
    body_node_ids: Iterable[str],
) -> None:
    """Boundary cleanup before each loop body iteration."""
    clear_loop_body_round_marks(session, body_node_ids)
    clear_loop_body_component_io_state(session, scope_id, body_node_ids)


def _loop_body_io_scope_id(session: BaseSession) -> str:
    """parent_id used by loop-body NodeSession state."""
    loop_compile_session = session.parent() if hasattr(session, "parent") else None
    if loop_compile_session is None:
        return ""
    return loop_compile_session.executable_id()


async def _patched_loop_group_on_invoke(
    self, inputs: Input, session: BaseSession, **kwargs
) -> Output:
    body_node_ids = getattr(self, "_node_ids", None)
    if body_node_ids:
        scope_id = _loop_body_io_scope_id(session)
        clear_loop_body_session_for_round(session, scope_id, body_node_ids)
    return await _orig_loop_group_on_invoke(self, inputs, session, **kwargs)


def apply_loop_body_session_cleanup_patch() -> bool:
    """Patch LoopGroup to clear body session data at each round boundary."""
    global _PATCH_APPLIED, _orig_loop_group_on_invoke
    if _PATCH_APPLIED:
        return False

    from openjiuwen.core.workflow.components.flow.loop.loop_comp import LoopGroup

    _orig_loop_group_on_invoke = LoopGroup.on_invoke
    LoopGroup.on_invoke = _patched_loop_group_on_invoke

    _PATCH_APPLIED = True
    return True


# --- AdvancedLoopComponent per-round io_state cleanup ---
_PATCH_STATE_APPLIED = False
_orig_advanced_loop_on_invoke = None
_LOOP_STATE_DIRECT_COMMIT_ENABLED = (
    os.getenv("LOOP_STATE_DIRECT_COMMIT_ENABLED", "true").strip().lower() == "true"
)
_NODE_ID_ATTR = "_node_id"
_NODE_SESSION_ATTR = "_node_session"
_IO_STATE_ATTR = "_io_state"


# --- AdvancedLoopComponent 执行期状态会话化（静态图复用并发隔离）---
# 静态图复用后同一 AdvancedLoopComponent 实例被并发执行共享，而引擎把循环
# 执行期状态放在实例字段上：
#   - ``self._node_session``：break_loop/is_broken/路由 __call__ 经它读写
#     ``_broken`` 退出标志；``_condition_invoke`` 经它读写 INDEX；
#   - ``self._post_body._finish_index``：轮次完成计数。
# 并发会话互相覆盖：A 的 break 写进「最后进入循环的会话」的 session、B 的
# is_broken 恒读 False → 循环不退出 → 循环体重跑 → 体内子工作流二次执行
# （中断恢复场景下 QA 节点以 END 状态重入并重复提问，10 并发复现）。
# 修复：执行期 session 经 ContextVar 通道按任务解析（on_invoke 设置/复位），
# ``_broken`` / ``finish_index`` 一律读写该 session 的 state，不再落共享实例；
# 无执行期上下文（引擎不派生任务等）时回退实例字段，保持旧行为。
_LOOP_EXEC_SESSION: ContextVar[Optional[BaseSession]] = ContextVar(
    "jiuwen_loop_exec_session", default=None
)
_PATCH_EXEC_STATE_APPLIED = False


def _resolve_loop_session(component: Any) -> Optional[BaseSession]:
    """按执行期上下文解析循环组件当前执行的 session（无上下文回退实例字段）。"""
    session = _LOOP_EXEC_SESSION.get()
    if session is not None:
        return session
    return getattr(component, _NODE_SESSION_ATTR, None)


async def _patched_advanced_loop_on_invoke(
    self, inputs: Input, session: BaseSession, **kwargs
) -> Output:
    loop_session = session
    loop_state = loop_session.state()
    node_id = loop_session.node_id()
    parent_id = session.parent_id()
    io_key = f"{parent_id}.{node_id}" if parent_id else node_id
    setattr(self, _NODE_ID_ATTR, node_id)
    node_session = NodeSession(loop_session, node_id)
    setattr(self, _NODE_SESSION_ATTR, node_session)
    io_state = getattr(loop_state, _IO_STATE_ATTR)
    if _LOOP_STATE_DIRECT_COMMIT_ENABLED:
        io_state.update_by_id_and_commit(
            io_key,
            {io_key: {LOOP_ID: node_id}},
        )
    else:
        loop_state.set_outputs({LOOP_ID: node_id})

    raw_io = (
        io_state.get_state(copied=False)
        if _LOOP_STATE_DIRECT_COMMIT_ENABLED
        else io_state.get_state()
    )
    if parent_id:
        scoped = get_value_by_nested_path(parent_id, raw_io)
        state = dict(scoped) if isinstance(scoped, dict) else {}
    else:
        state = dict(raw_io)
    if state and node_id in state:
        del state[node_id]
    if _LOOP_STATE_DIRECT_COMMIT_ENABLED:
        io_state.update_by_id_and_commit(
            io_key,
            {io_key: state},
        )
    else:
        loop_state.set_outputs(state)
        loop_state.commit()

    if loop_session.tracer() is not None:
        loop_session.tracer().register_workflow_span_manager(loop_session.executable_id())
    # 执行期 session 上通道：本次循环执行的 break/轮次计数解析到本会话
    # （并发执行各自任务上下文内可见；finally 复位防泄漏到同任务后续代码）
    token = _LOOP_EXEC_SESSION.set(node_session)
    try:
        compiled = self._graph.compile(loop_session, **kwargs)
        await compiled.invoke(inputs, loop_session)
    finally:
        _LOOP_EXEC_SESSION.reset(token)
    result = node_session.state().get_outputs(node_id)
    if _LOOP_STATE_DIRECT_COMMIT_ENABLED:
        io_state.update_by_id_and_commit(io_key, {io_key: None})
    else:
        io_state.update_by_id(io_key, {io_key: None})
    return result


def _patched_advanced_loop_is_broken(self) -> bool:
    """退出标志按执行期 session 读取（不再读共享实例上的 session）。"""
    session = _resolve_loop_session(self)
    if session is None:
        return False
    value = session.state().get(_BROKEN_KEY)
    return value if isinstance(value, bool) else False


def _patched_advanced_loop_break(self) -> None:
    """退出标志写入执行期 session 并提交（未提交的 staged 写会随 session
    对象切换丢失，并发下 break 标志须落盘）。"""
    session = _resolve_loop_session(self)
    if session is None:
        return
    session.state().update({_BROKEN_KEY: True})
    session.state().commit()


def _patched_advanced_loop_call(self, *args, **kwargs) -> list[str]:
    """条件路由：用执行期 session 驱动条件判定（原实现取共享实例字段）。"""
    return self.atomic_invoke(session=_resolve_loop_session(self))


def _patched_advanced_loop_atomic_invoke(self, **kwargs) -> Any:
    """条件判定入口：尊重调用方传入的 session（原实现强制 self._node_session）。"""
    session = kwargs.get("session") or _resolve_loop_session(self)
    try:
        return self._condition_invoke(session=session)
    except Exception as e:
        if isinstance(e, BaseError):
            raise
        raise build_error(
            StatusCode.COMPONENT_LOOP_CONDITION_EXECUTION_ERROR,
            reason=str(e),
            comp=self._node_id,
            cause=e,
        ) from e


async def _patched_post_body_on_invoke(
    self, inputs: Input, session: BaseSession, **kwargs
) -> Output:
    """轮次计数写执行期 session（原实现读共享实例字段再自增，跨会话串值）。"""
    loop_session = _LOOP_EXEC_SESSION.get()
    state = loop_session.state() if loop_session is not None else session.state()
    finish_index = state.get(FINISH_INDEX)
    if not isinstance(finish_index, int):
        finish_index = -1
    finish_index += 1
    state.update({FINISH_INDEX: finish_index})
    state.commit()
    return None


def _patched_post_body_get_finish_index(self) -> int:
    loop_session = _LOOP_EXEC_SESSION.get()
    if loop_session is None:
        return self._finish_index
    value = loop_session.state().get(FINISH_INDEX)
    return value if isinstance(value, int) else -1


def _patched_post_body_set_finish_index(self, finish_index: int) -> None:
    loop_session = _LOOP_EXEC_SESSION.get()
    if loop_session is None:
        self._finish_index = finish_index
        return
    loop_session.state().update({FINISH_INDEX: finish_index})
    loop_session.state().commit()


def apply_loop_exec_state_isolation_patch() -> bool:
    """Patch AdvancedLoopComponent/PostLoopBody 执行期状态为按会话解析。"""
    global _PATCH_EXEC_STATE_APPLIED
    if _PATCH_EXEC_STATE_APPLIED:
        return False

    from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
        AdvancedLoopComponent,
        PostLoopBody,
    )

    AdvancedLoopComponent.is_broken = _patched_advanced_loop_is_broken
    AdvancedLoopComponent.break_loop = _patched_advanced_loop_break
    AdvancedLoopComponent.__call__ = _patched_advanced_loop_call
    AdvancedLoopComponent._atomic_invoke = _patched_advanced_loop_atomic_invoke
    PostLoopBody.on_invoke = _patched_post_body_on_invoke
    PostLoopBody.get_finish_index = _patched_post_body_get_finish_index
    PostLoopBody.set_finish_index = _patched_post_body_set_finish_index

    _PATCH_EXEC_STATE_APPLIED = True
    return True


def apply_loop_state_cleanup_patch() -> bool:
    """Patch AdvancedLoopComponent.on_invoke to reset per-round io_state."""
    global _PATCH_STATE_APPLIED, _orig_advanced_loop_on_invoke
    if _PATCH_STATE_APPLIED:
        return False

    from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
        AdvancedLoopComponent,
    )

    _orig_advanced_loop_on_invoke = AdvancedLoopComponent.on_invoke
    AdvancedLoopComponent.on_invoke = _patched_advanced_loop_on_invoke

    _PATCH_STATE_APPLIED = True
    return True
