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

   **为何仍接管整体实现**：openjiuwen 的 reentrant-compile 修复
   (fix/0.1.17.post2-compile-reentrant) 已把 on_invoke 里的
   ``self._node_id`` / ``self._node_session`` 换成局部变量（并发隔离），
   但 io_state 仍是引擎原版语义——取 ``_io_state.get_state()`` 后
   ``set_outputs`` 整棵子树回写，未按 parent_id scope 收窄，也没有
   ``LOOP_STATE_DIRECT_COMMIT_ENABLED`` 的直提交路径。本 patch 以上游新版
   on_invoke 为底，仅替换 io_state 处理段；执行期 session 的 ContextVar 通道
   （``_LOOP_EXEC_SESSION``）由引擎自持，本 patch 原样沿用（不接管该段）。

两个 patch 作用对象不同 (LoopGroup 在外层, AdvancedLoopComponent 在内层),
各自独立的 _PATCH_APPLIED_* flag, 可按需 apply。

Applied once at import from ir_converter / sub_workflow.
"""

from __future__ import annotations

import os
from typing import Iterable

from openjiuwen.core.common.constants.constant import LOOP_ID
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session import BaseSession, NodeSession
from openjiuwen.core.session.utils import get_value_by_nested_path

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


def _advanced_loop_on_invoke_prelude(self, session: BaseSession) -> tuple:
    """io_state 清理段（引擎原版逻辑的 runtime 变体）。返回 (node_id, io_key)。

    与引擎原版的差异：按 parent_id scope 收窄取值（get_value_by_nested_path），
    并在 ``LOOP_STATE_DIRECT_COMMIT_ENABLED`` 下走 update_by_id_and_commit
    直提交路径（staged 写不跨 session 对象切换保留）。
    """
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

    return node_id, node_session, io_key, io_state


async def _patched_advanced_loop_on_invoke(
    self, inputs: Input, session: BaseSession, **kwargs
) -> Output:
    """以上游新版 on_invoke 为底，io_state 段换成 runtime scope 变体。

    上游新版已把 node_id / node_session 局部化（并发下不被其他执行覆写），
    本 patch 保留该点；执行期 session 的 ContextVar 通道沿用引擎自持的
    ``_LOOP_EXEC_SESSION``（set/reset 原样保留）。
    """
    loop_session = session
    node_id, node_session, io_key, io_state = _advanced_loop_on_invoke_prelude(
        self, loop_session
    )

    if loop_session.tracer() is not None:
        loop_session.tracer().register_workflow_span_manager(loop_session.executable_id())
    # 执行期 session 上通道：本次循环执行的 break/轮次计数解析到本会话
    # （并发执行各自任务上下文内可见；finally 复位防泄漏到同任务后续代码）
    from openjiuwen.core.workflow.components.flow.loop import (  # pylint: disable=import-outside-toplevel
        loop_comp as engine_loop_comp,
    )

    # 补丁的接管点即该引擎私有 ContextVar，无公开等价入口
    exec_session_channel = engine_loop_comp._LOOP_EXEC_SESSION  # pylint: disable=protected-access
    token = exec_session_channel.set(node_session)
    try:
        # 上游内部图对象无公开访问入口，本补丁须沿用其既有编译路径
        compiled = self._graph.compile(loop_session, **kwargs)  # pylint: disable=protected-access
        await compiled.invoke(inputs, loop_session)
    finally:
        exec_session_channel.reset(token)
    result = node_session.state().get_outputs(node_id)
    if _LOOP_STATE_DIRECT_COMMIT_ENABLED:
        io_state.update_by_id_and_commit(io_key, {io_key: None})
    else:
        io_state.update_by_id(io_key, {io_key: None})
    return result


def apply_loop_state_cleanup_patch() -> bool:
    """Patch AdvancedLoopComponent.on_invoke to reset per-round io_state."""
    global _PATCH_STATE_APPLIED, _orig_advanced_loop_on_invoke
    if _PATCH_STATE_APPLIED:
        return False

    from openjiuwen.core.workflow.components.flow.loop import loop_comp

    _orig_advanced_loop_on_invoke = loop_comp.AdvancedLoopComponent.on_invoke
    loop_comp.AdvancedLoopComponent.on_invoke = _patched_advanced_loop_on_invoke

    _PATCH_STATE_APPLIED = True
    return True
