# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for FastRedisCheckpointer."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.fast_redis_checkpointer import FastRedisCheckpointer


def _make_mock_delegate():
    """Create a mock RedisCheckpointer with all abstract methods."""
    delegate = MagicMock()
    delegate.pre_workflow_execute = AsyncMock()
    delegate.post_workflow_execute = AsyncMock()
    delegate.pre_agent_execute = AsyncMock()
    delegate.pre_agent_team_execute = AsyncMock()
    delegate.interrupt_agent_execute = AsyncMock()
    delegate.post_agent_execute = AsyncMock()
    delegate.post_agent_team_execute = AsyncMock()
    delegate.session_exists = AsyncMock()
    delegate.release = AsyncMock()
    delegate.graph_store = MagicMock()
    # workflow_storage mock — set via setattr to avoid protected-access lint
    workflow_storage_mock = MagicMock()
    workflow_storage_mock.clear = AsyncMock()
    setattr(delegate, "_workflow_storage", workflow_storage_mock)
    return delegate


@pytest.fixture
def mock_delegate():
    return _make_mock_delegate()


@pytest.fixture
def mock_redis():
    """Create a mock redis.asyncio.Redis client."""
    return MagicMock()


@pytest.fixture
def checkpointer(mock_delegate, mock_redis):
    return FastRedisCheckpointer(
        delegate=mock_delegate,
        redis_client=mock_redis,
        ttl_seconds=86400,
    )


class TestSessionExists:
    @pytest.mark.asyncio
    async def test_session_exists_no_sentinel(self, checkpointer, mock_redis):
        """New session: sentinel SET empty → returns False."""
        mock_redis.scard = AsyncMock(return_value=0)
        result = await checkpointer.session_exists("test-session-123")
        assert result is False
        mock_redis.scard.assert_awaited_once_with(
            "agentBuilder:session_exists:test-session-123"
        )

    @pytest.mark.asyncio
    async def test_session_exists_with_sentinel(self, checkpointer, mock_redis):
        """Existing session: sentinel SET has members → returns True."""
        mock_redis.scard = AsyncMock(return_value=1)
        result = await checkpointer.session_exists("test-session-123")
        assert result is True
        mock_redis.scard.assert_awaited_once_with(
            "agentBuilder:session_exists:test-session-123"
        )

    @pytest.mark.asyncio
    async def test_session_exists_multiple_workflows(self, checkpointer, mock_redis):
        """Session with multiple workflow sentinels (nested workflow) → returns True."""
        mock_redis.scard = AsyncMock(return_value=2)
        result = await checkpointer.session_exists("test-session-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_session_exists_redis_error_returns_false(
        self, checkpointer, mock_redis
    ):
        """Redis error on SCARD → return False (safe default)."""
        mock_redis.scard = AsyncMock(side_effect=Exception("Redis down"))
        result = await checkpointer.session_exists("test-session-123")
        assert result is False


class TestPreWorkflowExecute:
    @pytest.mark.asyncio
    async def test_pre_workflow_writes_sentinel(self, checkpointer, mock_delegate, mock_redis):
        """pre_workflow_execute delegates + SADD workflow_id to sentinel SET."""
        mock_redis.sadd = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_session = MagicMock()
        mock_session.session_id = MagicMock(return_value="sess-1")
        mock_session.workflow_id = MagicMock(return_value="wf-1")

        await checkpointer.pre_workflow_execute(mock_session, MagicMock())

        # Delegate was called
        mock_delegate.pre_workflow_execute.assert_awaited_once()
        # SADD workflow_id to sentinel SET
        mock_redis.sadd.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )
        # TTL set on the SET key
        mock_redis.expire.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", 86400
        )

    @pytest.mark.asyncio
    async def test_pre_workflow_sentinel_write_failure_no_raise(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Sentinel write failure does NOT raise — logs warning."""
        mock_redis.sadd = AsyncMock(side_effect=Exception("Redis write error"))
        mock_session = MagicMock()
        mock_session.session_id = MagicMock(return_value="sess-1")
        mock_session.workflow_id = MagicMock(return_value="wf-1")

        # Should NOT raise
        await checkpointer.pre_workflow_execute(mock_session, MagicMock())

        # Delegate was still called
        mock_delegate.pre_workflow_execute.assert_awaited_once()


class TestPostWorkflowExecute:
    @staticmethod
    def _make_session(session_id="sess-1", workflow_id="wf-1"):
        mock = MagicMock()
        mock.session_id = MagicMock(return_value=session_id)
        mock.workflow_id = MagicMock(return_value=workflow_id)
        return mock

    @pytest.mark.asyncio
    async def test_normal_completion_deletes_sentinel_and_graph_keys(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: precise GraphStore delete + SREM from sentinel SET + workflow_storage.clear."""
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        result = {}  # No TASK_STATUS_INTERRUPT → normal completion
        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Redis.delete called with precise GraphStore keys
        expected_type_key = "sess-1:workflow-graph:wf-1:checkpoint_data_type"
        expected_value_key = "sess-1:workflow-graph:wf-1:checkpoint_data_value"
        mock_redis.delete.assert_any_call(expected_type_key, expected_value_key)

        # SREM workflow_id from sentinel SET (Redis auto-deletes empty SET)
        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )

        # No manual DELETE of the sentinel key — Redis handles empty-set cleanup
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list]
        assert "agentBuilder:session_exists:sess-1" not in delete_calls

        # workflow_storage.clear delegated
        getattr(mock_delegate, "_workflow_storage").clear.assert_awaited_once_with("wf-1", "sess-1")

    @pytest.mark.asyncio
    async def test_normal_completion_set_not_empty_keeps_key(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: SREM only removes own workflow_id, never DELETEs the SET."""
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        result = {}
        await checkpointer.post_workflow_execute(mock_session, result, None)

        # SREM called for own workflow_id only
        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )
        # No manual DELETE of the sentinel key — Redis auto-handles empty-set cleanup
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list]
        assert "agentBuilder:session_exists:sess-1" not in delete_calls

    @pytest.mark.asyncio
    async def test_exception_path_clears_checkpoint(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Non-WorkflowAbortException path: clear checkpoint + SREM (terminal state).

        Any execution exception (plugin config error, runtime error, etc.) is treated
        as a terminal state, not an interrupt. The checkpoint is cleared and the
        workflow_id is SREM'd from the sentinel SET so the next run with the same
        conversation_id starts fresh instead of erroneously resuming from the failed
        node. True interrupts go through the exception=None branch and are unaffected.
        """
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()
        test_exception = RuntimeError("boom")

        await checkpointer.post_workflow_execute(mock_session, None, test_exception)

        # Delegate.post_workflow_execute should NOT be called (we clear ourselves)
        mock_delegate.post_workflow_execute.assert_not_called()

        # Redis.delete called with precise GraphStore keys (same as normal completion)
        expected_type_key = "sess-1:workflow-graph:wf-1:checkpoint_data_type"
        expected_value_key = "sess-1:workflow-graph:wf-1:checkpoint_data_value"
        mock_redis.delete.assert_any_call(expected_type_key, expected_value_key)

        # SREM workflow_id from sentinel SET
        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )

        # workflow_storage.clear delegated
        getattr(mock_delegate, "_workflow_storage").clear.assert_awaited_once_with("wf-1", "sess-1")

    @pytest.mark.asyncio
    async def test_workflow_abort_exception_clears_checkpoint(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """WorkflowAbortException (异常结束节点) clears checkpoint like normal completion."""
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        from jiuwen.extension.workflow_node.utils import WorkflowAbortException
        abort_exc = WorkflowAbortException(
            data={"error_code": "10025"},
            node_id="node_1782702227731",
            node_name="异常",
            node_type="jiuwen.exception",
        )

        await checkpointer.post_workflow_execute(mock_session, None, abort_exc)

        # Delegate.post_workflow_execute should NOT be called (we handle it ourselves)
        mock_delegate.post_workflow_execute.assert_not_called()

        # Redis.delete called with precise GraphStore keys (same as normal completion)
        expected_type_key = "sess-1:workflow-graph:wf-1:checkpoint_data_type"
        expected_value_key = "sess-1:workflow-graph:wf-1:checkpoint_data_value"
        mock_redis.delete.assert_any_call(expected_type_key, expected_value_key)

        # SREM workflow_id from sentinel SET
        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )

        # workflow_storage.clear delegated
        getattr(mock_delegate, "_workflow_storage").clear.assert_awaited_once_with("wf-1", "sess-1")

    @pytest.mark.asyncio
    async def test_exception_path_clears_without_raising(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Exception path: decorator clears checkpoint and returns normally.

        Exception propagation is NOT the decorator's responsibility — it is handled
        by CompiledGraph._invoke (patched version, see workflow_sub_stream_patch.py),
        which re-raises the exception after post_workflow_execute returns. Therefore
        the decorator must NOT call delegate.post_workflow_execute (which would save
        the checkpoint) and must NOT raise itself; it just clears and returns.
        """
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()
        test_exception = RuntimeError("workflow failed")

        # Decorator returns normally (does not raise); _invoke re-raises separately
        await checkpointer.post_workflow_execute(mock_session, None, test_exception)

        # Delegate.post_workflow_execute NOT called (no checkpoint save)
        mock_delegate.post_workflow_execute.assert_not_called()

        # Checkpoint cleared: GraphStore keys deleted + workflow_id SREM'd from sentinel SET
        mock_redis.delete.assert_called()
        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )

    @pytest.mark.asyncio
    async def test_interrupt_path_keeps_sentinel(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Interrupt path: delegate saves checkpoint, sentinel kept."""
        mock_session = self._make_session()
        # Simulate TASK_STATUS_INTERRUPT present in result
        # TASK_STATUS_INTERRUPT = "__interrupt__" (from openjiuwen.core.graph.pregel)
        result = {"__interrupt__": True}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Delegate was called (saves checkpoint)
        mock_delegate.post_workflow_execute.assert_awaited_once()
        # No Redis delete or SREM calls
        mock_redis.delete.assert_not_called()
        mock_redis.srem.assert_not_called()

    @pytest.mark.asyncio
    async def test_precise_delete_failure_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Precise GraphStore delete failure → fallback to delegate (scan_iter)."""
        mock_redis.delete = AsyncMock(side_effect=Exception("Redis delete error"))
        mock_session = self._make_session()
        result = {}  # Normal completion

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Delegate.post_workflow_execute called as fallback (includes scan_iter)
        mock_delegate.post_workflow_execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_workflow_storage_clear_failure_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """workflow_storage.clear() failure → fallback to delegate."""
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        getattr(mock_delegate, "_workflow_storage").clear = AsyncMock(
            side_effect=Exception("Redis error in clear")
        )
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Fallback to delegate's post_workflow_execute
        mock_delegate.post_workflow_execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_workflow_storage_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """If delegate has no _workflow_storage attribute → fallback to delegate."""
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        # Remove _workflow_storage from delegate to simulate missing attribute
        delattr(mock_delegate, "_workflow_storage")
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Fallback to delegate's post_workflow_execute
        mock_delegate.post_workflow_execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sub_workflow_completion_preserves_main_sentinel(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Sub-workflow normal completion only SREMs its own workflow_id, not the main workflow's.

        This is the core regression test for the nested workflow interrupt detection bug:
        when a sub-workflow completes normally, its _clear_checkpoint_and_sentinel call
        must only SREM the sub-workflow's ID from the sentinel SET, keeping the main
        workflow's ID intact.
        """
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        # Sub-workflow completes normally
        sub_session = self._make_session(session_id="sess-1", workflow_id="sub-wf")
        result = {}  # Normal completion

        await checkpointer.post_workflow_execute(sub_session, result, None)

        # SREM only removed sub-wf, not main-wf
        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "sub-wf"
        )
        # No manual DELETE of the sentinel key — Redis auto-handles cleanup
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list]
        assert "agentBuilder:session_exists:sess-1" not in delete_calls

        # GraphStore keys for sub-wf were deleted
        expected_type_key = "sess-1:workflow-graph:sub-wf:checkpoint_data_type"
        expected_value_key = "sess-1:workflow-graph:sub-wf:checkpoint_data_value"
        mock_redis.delete.assert_any_call(expected_type_key, expected_value_key)


class TestDelegatePassthrough:
    @pytest.mark.asyncio
    async def test_pre_agent_execute(self, checkpointer, mock_delegate):
        mock_session = MagicMock()
        await checkpointer.pre_agent_execute(mock_session, "inputs")
        mock_delegate.pre_agent_execute.assert_awaited_once_with(mock_session, "inputs")

    @pytest.mark.asyncio
    async def test_pre_agent_team_execute(self, checkpointer, mock_delegate):
        mock_session = MagicMock()
        await checkpointer.pre_agent_team_execute(mock_session, "inputs")
        mock_delegate.pre_agent_team_execute.assert_awaited_once_with(mock_session, "inputs")

    @pytest.mark.asyncio
    async def test_interrupt_agent_execute(self, checkpointer, mock_delegate):
        mock_session = MagicMock()
        await checkpointer.interrupt_agent_execute(mock_session)
        mock_delegate.interrupt_agent_execute.assert_awaited_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_post_agent_execute(self, checkpointer, mock_delegate):
        mock_session = MagicMock()
        await checkpointer.post_agent_execute(mock_session)
        mock_delegate.post_agent_execute.assert_awaited_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_post_agent_team_execute(self, checkpointer, mock_delegate):
        mock_session = MagicMock()
        await checkpointer.post_agent_team_execute(mock_session)
        mock_delegate.post_agent_team_execute.assert_awaited_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_release_delegates_without_deleting_sentinel(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """release() delegates but does NOT delete sentinel SET.

        Sentinel is intentionally preserved to avoid accidental loss of
        interrupt state. It expires via TTL instead.
        """
        await checkpointer.release("sess-1")
        mock_delegate.release.assert_awaited_once_with("sess-1", None)
        # Sentinel SET NOT deleted — relies on TTL for cleanup
        mock_redis.delete.assert_not_called()
        mock_redis.srem.assert_not_called()

    @pytest.mark.asyncio
    async def test_release_with_agent_id(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Agent-specific release delegates correctly."""
        await checkpointer.release("sess-1", agent_id="agent-1")
        mock_delegate.release.assert_awaited_once_with("sess-1", "agent-1")
        mock_redis.delete.assert_not_called()

    @staticmethod
    def test_graph_store(checkpointer, mock_delegate):
        mock_delegate.graph_store.return_value = "mock_graph_store"
        result = checkpointer.graph_store()
        assert result == "mock_graph_store"
        mock_delegate.graph_store.assert_called_once()


class TestFeatureToggle:
    @staticmethod
    def test_toggle_default_is_enabled():
        """FAST_CHECKPOINTER_ENABLED defaults to True."""
        from agent_runtime.common.config import CheckpointerSettings
        settings = CheckpointerSettings()
        assert settings.fast_checkpointer_enabled is True

    @staticmethod
    def test_toggle_can_be_disabled():
        """FAST_CHECKPOINTER_ENABLED can be set to False."""
        from agent_runtime.common.config import CheckpointerSettings
        original = os.environ.get("FAST_CHECKPOINTER_ENABLED")
        try:
            os.environ["FAST_CHECKPOINTER_ENABLED"] = "false"
            settings = CheckpointerSettings()
            assert settings.fast_checkpointer_enabled is False
        finally:
            if original is not None:
                os.environ["FAST_CHECKPOINTER_ENABLED"] = original
            else:
                os.environ.pop("FAST_CHECKPOINTER_ENABLED", None)

    @pytest.mark.asyncio
    async def test_toggle_enabled_creates_fast_checkpointer(
        self, mock_delegate, mock_redis
    ):
        """When fast_checkpointer_enabled=True, FastRedisCheckpointer wraps delegate."""
        fast = FastRedisCheckpointer(
            delegate=mock_delegate,
            redis_client=mock_redis,
            ttl_seconds=86400,
        )
        assert isinstance(fast, FastRedisCheckpointer)
        # session_exists uses sentinel SET (SCARD), not delegate
        mock_redis.scard = AsyncMock(return_value=1)
        result = await fast.session_exists("sess-1")
        assert result is True
        mock_delegate.session_exists.assert_not_called()
