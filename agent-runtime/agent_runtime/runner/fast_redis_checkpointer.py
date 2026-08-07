# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
FastRedisCheckpointer — decorator that replaces O(N) scan_iter operations
in RedisCheckpointer with O(1) alternatives.

Eliminates two full-keyspace Redis scans per workflow request:
1. session_exists() → sentinel SET SCARD (O(1))
2. post_workflow_execute() → precise key deletion (O(K) instead of scan_iter)
"""

from typing import Optional

from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.session.checkpointer import Checkpointer
from openjiuwen.core.session.checkpointer.base import (
    WORKFLOW_NAMESPACE_GRAPH,
    build_key_with_namespace,
)
from redis.asyncio import Redis


# GraphStore key suffixes — mirrors GraphStore._DATA_TYPE / _DATA_VALUE
# in openjiuwen/extensions/checkpointer/redis/storage.py
_GRAPH_DATA_TYPE = "checkpoint_data_type"
_GRAPH_DATA_VALUE = "checkpoint_data_value"

# Sentinel SET key — one per session, members are workflow_ids with active checkpoints.
# Format: agentBuilder:session_exists:{session_id}
# Members: {workflow_id} for each workflow that has a sentinel
#
# Using a SET instead of individual string keys per workflow keeps
# session_exists() at O(1) (SCARD) and allows per-workflow add/remove
# (SADD/SREM) without scan_iter.
_SENTINEL_PREFIX = "agentBuilder:session_exists:"


def _sentinel_key(session_id: str) -> str:
    return f"{_SENTINEL_PREFIX}{session_id}"


class FastRedisCheckpointer(Checkpointer):
    """Decorator around RedisCheckpointer that replaces scan_iter with O(1) operations.

    Overrides:
      - session_exists: O(1) sentinel SET check (SCARD)
      - pre_workflow_execute: delegate + SADD workflow_id to sentinel SET
      - post_workflow_execute: precise GraphStore key delete + SREM from sentinel SET

    All other methods delegate to the original RedisCheckpointer unchanged.
    """

    def __init__(
        self,
        delegate: Checkpointer,
        redis_client: Redis,
        ttl_seconds: int = 86400,  # 24h — sentinel key 过期时间，兜底清理
    ):
        self._delegate = delegate
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    # ── Overridden methods ──────────────────────────────────────

    async def session_exists(self, session_id: str) -> bool:
        """O(1) sentinel SET check — SCARD returns member count.

        Returns False if Redis is unreachable (safe default: treat as new session).
        """
        try:
            count = await self._redis.scard(_sentinel_key(session_id))
            return count > 0
        except Exception as e:
            workflow_logger.warning(
                f"FastRedisCheckpointer: sentinel SCARD failed for session "
                f"{session_id}, returning False: {e}"
            )
            return False

    async def pre_workflow_execute(self, session, inputs):
        """Delegate + SADD workflow_id to sentinel SET (idempotent).

        Sentinel is written AFTER delegate succeeds. If delegate raises (e.g.,
        CHECKPOINTER_PRE_WORKFLOW_EXECUTION_ERROR), the sentinel is NOT written,
        which is correct — the session never started, so session_exists() should
        return False.
        """
        await self._delegate.pre_workflow_execute(session, inputs)
        session_id = session.session_id()
        workflow_id = session.workflow_id()
        try:
            key = _sentinel_key(session_id)
            await self._redis.sadd(key, workflow_id)
            await self._redis.expire(key, self._ttl_seconds)
        except Exception as e:
            workflow_logger.warning(
                f"FastRedisCheckpointer: sentinel SADD failed for session "
                f"{session_id}, workflow {workflow_id}: {e}"
            )

    async def post_workflow_execute(self, session, result, exception):
        """Replace GraphStore.delete() scan_iter with precise key deletion.

        On normal completion:
          1. Construct exact GraphStore keys and batch_delete them (O(2))
          2. SREM workflow_id from sentinel SET
          3. Delegate workflow_storage.clear()
        On any execution exception (WorkflowAbortException / plugin config error /
        runtime error):
          Treated as a terminal state, not an interrupt. Clear checkpoint + SREM
          sentinel so the next run with the same conversation_id starts fresh
          instead of erroneously resuming from the failed node. Exception
          propagation is NOT done here — it is handled by CompiledGraph._invoke
          (patched version), which re-raises after this method returns.
        On true interrupt (TASK_STATUS_INTERRUPT in result, exception is None):
          delegate saves checkpoint for resume.
        """
        session_id = session.session_id()
        workflow_id = session.workflow_id()

        if exception is not None:
            # 任何执行异常都视为终态，清除 checkpoint + 哨兵 SET 中的 workflow_id，
            # 避免下次同 conversationId 运行被误判为中断恢复而重跑失败节点。真正的中断
            # 由 TASK_STATUS_INTERRUPT 在 exception=None 分支处理，不受影响。
            #
            # 异常的向上传播由 CompiledGraph._invoke（patched 版本，见
            # workflow_sub_stream_patch.py）在调用本方法后自行 re-raise 负责，因此这里
            # 只需清理、无需 re-raise，也不调用 delegate.post_workflow_execute（它会在
            # 异常时保存 checkpoint 并 re-raise，正是被修复的旧行为）。
            from jiuwen.extension.workflow_node.utils import WorkflowAbortException
            if isinstance(exception, WorkflowAbortException):
                workflow_logger.info(
                    f"FastRedisCheckpointer: WorkflowAbortException detected, "
                    f"clearing checkpoint for session {session_id}, "
                    f"workflow {workflow_id}"
                )
            else:
                workflow_logger.info(
                    f"FastRedisCheckpointer: execution exception "
                    f"{type(exception).__name__} treated as terminal, clearing "
                    f"checkpoint for session {session_id}, workflow {workflow_id} "
                    f"(true interrupts go through the exception=None branch)"
                )
            await self._clear_checkpoint_and_sentinel(session_id, workflow_id, session)
            return

        from openjiuwen.core.graph.pregel import TASK_STATUS_INTERRUPT

        if result.get(TASK_STATUS_INTERRUPT) is None:
            # Normal completion — clear checkpoint
            await self._clear_checkpoint_and_sentinel(session_id, workflow_id, session)
        else:
            # Interrupt — delegate saves checkpoint
            await self._delegate.post_workflow_execute(session, result, exception)

    # ── Internal helpers ────────────────────────────────────────

    async def _clear_checkpoint_and_sentinel(
        self, session_id: str, workflow_id: str, session
    ):
        """Clear GraphStore keys, remove workflow_id from sentinel SET, and workflow storage.

        Used for both normal completion and WorkflowAbortException (异常结束节点),
        which should both result in a clean slate for the next run.

        Only removes the given workflow_id from the sentinel SET — other workflows
        in the same session (e.g., the main workflow when a sub-workflow completes)
        remain as SET members so session_exists() stays correct.
        """
        # Step 1: Prefix-based GraphStore key deletion.
        # 精确删只清主工作流 NS 的 key，但 sub-workflow（loop body 等）的 NS 是
        # workflow_id:node_xxx:1，其 GraphStore key 也以 workflow_id 开头，精确删
        # 漏掉这些 key → 下次同 conversationId 跑时 _is_resume=True，pregel 走
        # resume 路径跳过 condition，破坏 loop 变量绑定（QA 读到空 city）。
        # 改用 prefix 删，确保主工作流及其所有 sub-NS 的 graph state 都被清掉。
        # 用 delegate 的 _graph_state.delete（GraphStore 内部走 RedisStore.delete_by_prefix），
        # 因为 self._redis 是裸 redis.asyncio.Redis，没有 delete_by_prefix 方法。
        # NOTE: Uses getattr to avoid protected-access lint warning.
        graph_state = getattr(self._delegate, "_graph_state", None)
        if graph_state is not None:
            try:
                await graph_state.delete(session_id, workflow_id)
                workflow_logger.info(
                    f"FastRedisCheckpointer: prefix GraphStore delete for "
                    f"session {session_id}, workflow {workflow_id}"
                )
            except Exception as e:
                workflow_logger.warning(
                    f"FastRedisCheckpointer: prefix GraphStore delete failed, "
                    f"falling back to delegate post_workflow_execute: {e}"
                )
                await self._delegate.post_workflow_execute(session, {}, None)
                return
        else:
            workflow_logger.warning(
                f"FastRedisCheckpointer: delegate has no _graph_state, "
                f"falling back to delegate post_workflow_execute for session "
                f"{session_id}, workflow {workflow_id}"
            )
            await self._delegate.post_workflow_execute(session, {}, None)
            return

        # Step 1.5: Delete bare session key (clears comp_state with QA
        #            QUESTIONER_STATE_KEY + comp_state_updates, ensuring next
        #            round starts fresh).
        # bare session key（session_id 无 namespace）由 AsyncStateManager 管理，
        # 包含 comp_state（框架快照，含 QA 的 USER_INTERACT 残留）和
        # comp_state_updates（update_state 追加的增量）。不清掉会导致下一轮
        # QA 的 _load_state_from_session 从 comp_state 读到旧的 USER_INTERACT，
        # 走恢复路径而非新开始路径，不生成问题文本。
        # conversationHistory 不受影响——下一轮 Start 节点从 inputs（请求传入）重建。
        try:
            await self._redis.delete(session_id)
            workflow_logger.info(
                f"FastRedisCheckpointer: deleted bare session key for "
                f"session {session_id}"
            )
        except Exception as e:
            workflow_logger.warning(
                f"FastRedisCheckpointer: bare session key delete failed: {e}"
            )

        # Remove this workflow_id from the sentinel SET (not the whole SET)
        # Redis auto-deletes the key when the last member is removed, so no
        # A standalone SREM is enough and avoids redundant SCARD/DELETE operations.
        try:
            key = _sentinel_key(session_id)
            await self._redis.srem(key, workflow_id)
        except Exception as e:
            workflow_logger.warning(
                f"FastRedisCheckpointer: sentinel SREM failed for session "
                f"{session_id}, workflow {workflow_id}: {e}"
            )

        # Delegate workflow_storage.clear() (this is O(K), not scan_iter)
        # NOTE: Uses getattr to avoid protected-access lint warning.
        # The delegate (RedisCheckpointer) has a _workflow_storage attribute
        # with a clear() method. If it's not accessible or fails, fall back
        # to the full delegate post_workflow_execute (includes scan_iter).
        workflow_storage = getattr(self._delegate, "_workflow_storage", None)
        if workflow_storage is not None and hasattr(workflow_storage, "clear"):
            try:
                await workflow_storage.clear(workflow_id, session_id)
            except Exception as e:
                workflow_logger.warning(
                    f"FastRedisCheckpointer: workflow_storage.clear() failed, "
                    f"falling back to full delegate post_workflow_execute for session "
                    f"{session_id}, workflow {workflow_id}: {e}"
                )
                await self._delegate.post_workflow_execute(session, {}, None)
        else:
            workflow_logger.warning(
                f"FastRedisCheckpointer: workflow_storage not accessible on delegate, "
                f"falling back to full delegate post_workflow_execute for session "
                f"{session_id}, workflow {workflow_id}"
            )
            await self._delegate.post_workflow_execute(session, {}, None)

    # ── Delegate pass-through methods ───────────────────────────

    async def pre_agent_execute(self, session, inputs):
        await self._delegate.pre_agent_execute(session, inputs)

    async def pre_agent_team_execute(self, session, inputs):
        await self._delegate.pre_agent_team_execute(session, inputs)

    async def interrupt_agent_execute(self, session):
        await self._delegate.interrupt_agent_execute(session)

    async def post_agent_execute(self, session):
        await self._delegate.post_agent_execute(session)

    async def post_agent_team_execute(self, session):
        await self._delegate.post_agent_team_execute(session)

    async def release(self, session_id: str, agent_id: Optional[str] = None):
        """Delegate release. Sentinel SET is NOT deleted — it will expire via TTL.

        Intentionally keeping the sentinel key after release avoids accidental
        deletion that could cause loss of interrupt state if release is called
        prematurely. The sentinel TTL (default 24h, configurable via
        FAST_CHECKPOINTER_SENTINEL_TTL_SECONDS) ensures eventual cleanup.
        """
        await self._delegate.release(session_id, agent_id)

    def graph_store(self):
        return self._delegate.graph_store()
