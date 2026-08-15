# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for FastRedisCheckpointer."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.fast_redis_checkpointer import (
    FastRedisCheckpointer,
    NsIndexingGraphStore,
)


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
    delegate.graph_store = MagicMock(return_value=MagicMock())
    # workflow_storage mock — set via setattr to avoid protected-access lint
    workflow_storage_mock = MagicMock()
    workflow_storage_mock.clear = AsyncMock()
    setattr(delegate, "_workflow_storage", workflow_storage_mock)
    # graph_state mock — used as fallback for prefix delete
    graph_state_mock = MagicMock()
    graph_state_mock.delete = AsyncMock()
    setattr(delegate, "_graph_state", graph_state_mock)
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
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
        mock_session = self._make_session()

        result = {}  # No TASK_STATUS_INTERRUPT → normal completion
        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Redis.delete called with precise GraphStore keys
        expected_type_key = "sess-1:workflow-graph:wf-1:checkpoint_data_type"
        expected_value_key = "sess-1:workflow-graph:wf-1:checkpoint_data_value"
        mock_redis.delete.assert_any_call(expected_type_key, expected_value_key)

        # SREM ns from NS index SET (not DELETE the whole key)
        mock_redis.srem.assert_any_call("agentBuilder:graph_ns:sess-1", "wf-1")
        # SREM workflow_id from sentinel SET (Redis auto-deletes empty SET)
        mock_redis.srem.assert_any_call(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )

        # No manual DELETE of the sentinel key or NS index key
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list if c[0]]
        assert "agentBuilder:session_exists:sess-1" not in delete_calls
        assert "agentBuilder:graph_ns:sess-1" not in delete_calls

        # workflow_storage.clear delegated
        getattr(mock_delegate, "_workflow_storage").clear.assert_awaited_once_with("wf-1", "sess-1")

    @pytest.mark.asyncio
    async def test_normal_completion_set_not_empty_keeps_key(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: SREM only removes own workflow_id, never DELETEs the SET."""
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
        mock_session = self._make_session()

        result = {}
        await checkpointer.post_workflow_execute(mock_session, result, None)

        # SREM called for own workflow_id on sentinel SET and ns on NS index SET
        mock_redis.srem.assert_any_call(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )
        mock_redis.srem.assert_any_call(
            "agentBuilder:graph_ns:sess-1", "wf-1"
        )
        # No manual DELETE of the sentinel key or NS index key
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list if c[0]]
        assert "agentBuilder:session_exists:sess-1" not in delete_calls
        assert "agentBuilder:graph_ns:sess-1" not in delete_calls

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
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
        mock_session = self._make_session()
        test_exception = RuntimeError("boom")

        await checkpointer.post_workflow_execute(mock_session, None, test_exception)

        # Delegate.post_workflow_execute should NOT be called (we clear ourselves)
        mock_delegate.post_workflow_execute.assert_not_called()

        # Redis.delete called with precise GraphStore keys (same as normal completion)
        expected_type_key = "sess-1:workflow-graph:wf-1:checkpoint_data_type"
        expected_value_key = "sess-1:workflow-graph:wf-1:checkpoint_data_value"
        mock_redis.delete.assert_any_call(expected_type_key, expected_value_key)

        # SREM workflow_id from sentinel SET and ns from NS index SET
        mock_redis.srem.assert_any_call(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )
        mock_redis.srem.assert_any_call(
            "agentBuilder:graph_ns:sess-1", "wf-1"
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
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
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

        # SREM workflow_id from sentinel SET and ns from NS index SET
        mock_redis.srem.assert_any_call(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )
        mock_redis.srem.assert_any_call(
            "agentBuilder:graph_ns:sess-1", "wf-1"
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
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
        mock_session = self._make_session()
        test_exception = RuntimeError("workflow failed")

        # Decorator returns normally (does not raise); _invoke re-raises separately
        await checkpointer.post_workflow_execute(mock_session, None, test_exception)

        # Delegate.post_workflow_execute NOT called (no checkpoint save)
        mock_delegate.post_workflow_execute.assert_not_called()

        # Checkpoint cleared: GraphStore keys deleted + workflow_id SREM'd from sentinel SET + ns SREM'd from NS index
        mock_redis.delete.assert_called()
        mock_redis.srem.assert_any_call(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )
        mock_redis.srem.assert_any_call(
            "agentBuilder:graph_ns:sess-1", "wf-1"
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
    async def test_precise_delete_failure_falls_back_to_prefix_delete(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Precise batch_delete failure → fallback to prefix GraphStore delete."""
        mock_redis.delete = AsyncMock(side_effect=Exception("Redis delete error"))
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
        mock_session = self._make_session()
        result = {}  # Normal completion

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Fallback to delegate's _graph_state.delete (prefix delete)
        getattr(mock_delegate, "_graph_state").delete.assert_awaited_once_with("sess-1", "wf-1")
        # Delegate.post_workflow_execute NOT called (prefix delete succeeded)
        mock_delegate.post_workflow_execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_precise_delete_failure_and_prefix_failure_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Both precise and prefix delete fail → fallback to delegate post_workflow_execute."""
        mock_redis.delete = AsyncMock(side_effect=Exception("Redis delete error"))
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
        getattr(mock_delegate, "_graph_state").delete = AsyncMock(
            side_effect=Exception("prefix delete also failed")
        )
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Delegate.post_workflow_execute called as final fallback
        mock_delegate.post_workflow_execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_workflow_storage_clear_failure_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """workflow_storage.clear() failure → fallback to delegate."""
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
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
        mock_redis.smembers = AsyncMock(return_value={b"wf-1"})
        # Remove _workflow_storage from delegate to simulate missing attribute
        delattr(mock_delegate, "_workflow_storage")
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Fallback to delegate's post_workflow_execute
        mock_delegate.post_workflow_execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sub_workflow_completion_preserves_main_checkpoint(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Sub-workflow normal completion does NOT delete main workflow's checkpoint.

        This is the core regression test: when a sub-workflow completes normally,
        _clear_checkpoint_and_sentinel must only delete GraphStore keys whose ns
        matches the sub-workflow's workflow_id, preserving the main workflow's
        interrupt checkpoint for resume.

        The NS index SET contains both main and sub NS, but only sub-wf matches
        the workflow_id filter. Main-wf's keys must NOT be deleted.
        """
        mock_redis.delete = AsyncMock(return_value=2)
        mock_redis.srem = AsyncMock(return_value=1)
        # NS index contains both main-wf and sub-wf
        mock_redis.smembers = AsyncMock(return_value={b"main-wf", b"sub-wf"})
        # Sub-workflow completes normally
        sub_session = self._make_session(session_id="sess-1", workflow_id="sub-wf")
        result = {}

        await checkpointer.post_workflow_execute(sub_session, result, None)

        # SREM only sub-wf from sentinel SET, NOT main-wf
        mock_redis.srem.assert_any_call(
            "agentBuilder:session_exists:sess-1", "sub-wf"
        )
        # SREM only sub-wf from NS index SET, NOT main-wf
        mock_redis.srem.assert_any_call(
            "agentBuilder:graph_ns:sess-1", "sub-wf"
        )
        # main-wf must NOT be SREM'd from either SET
        srem_args = [c.args for c in mock_redis.srem.call_args_list]
        for args in srem_args:
            assert "main-wf" not in args, \
                f"main-wf should not be SREM'd, but got call: {args}"

        # GraphStore keys for sub-wf were deleted
        expected_type_key = "sess-1:workflow-graph:sub-wf:checkpoint_data_type"
        expected_value_key = "sess-1:workflow-graph:sub-wf:checkpoint_data_value"
        mock_redis.delete.assert_any_call(expected_type_key, expected_value_key)

        # GraphStore keys for main-wf must NOT be deleted
        main_type_key = "sess-1:workflow-graph:main-wf:checkpoint_data_type"
        main_value_key = "sess-1:workflow-graph:main-wf:checkpoint_data_value"
        delete_calls = [c.args for c in mock_redis.delete.call_args_list]
        for args in delete_calls:
            assert main_type_key not in args, \
                f"main-wf type key should not be deleted, but got: {args}"
            assert main_value_key not in args, \
                f"main-wf value key should not be deleted, but got: {args}"

    @pytest.mark.asyncio
    async def test_main_workflow_deletes_sub_ns_with_pipe_separator(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Main workflow completion deletes its own NS + sub-NS (pipe separator).

        Sub-workflow NS format is {main}|{exe}|{sub}. The prefix filter
        ns.startswith(workflow_id) must match both main NS and sub-NS.
        """
        mock_redis.delete = AsyncMock(return_value=4)
        mock_redis.srem = AsyncMock(return_value=1)
        main_wf = "663621b9-f3b7-4c01-b278-960f860178f2"
        sub_ns = f"{main_wf}|exe-123|sub-wf-456"
        mock_redis.smembers = AsyncMock(return_value={main_wf.encode(), sub_ns.encode()})

        main_session = self._make_session(session_id="sess-1", workflow_id=main_wf)
        result = {}

        await checkpointer.post_workflow_execute(main_session, result, None)

        # Both main NS and sub-NS keys should be deleted
        main_type = f"sess-1:workflow-graph:{main_wf}:checkpoint_data_type"
        sub_type = f"sess-1:workflow-graph:{sub_ns}:checkpoint_data_type"
        delete_args = [args for c in mock_redis.delete.call_args_list for args in c.args]
        assert main_type in delete_args
        assert sub_type in delete_args

        # Both NS SREM'd from index
        srem_index_calls = [
            c.args for c in mock_redis.srem.call_args_list
            if c.args[0] == "agentBuilder:graph_ns:sess-1"
        ]
        srem_members = set()
        for call_args in srem_index_calls:
            srem_members.update(call_args[1:])
        assert main_wf in srem_members
        assert sub_ns in srem_members


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
        assert isinstance(result, NsIndexingGraphStore)
        assert getattr(result, "_saver") is mock_delegate.graph_store.return_value
        mock_delegate.graph_store.assert_called_once()


class TestNsIndexFallback:
    """Tests for NS index empty / fallback behavior."""

    @staticmethod
    def _make_session(session_id="sess-1", workflow_id="wf-1"):
        mock = MagicMock()
        mock.session_id = MagicMock(return_value=session_id)
        mock.workflow_id = MagicMock(return_value=workflow_id)
        return mock

    @pytest.mark.asyncio
    async def test_empty_ns_index_falls_back_to_prefix_delete(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """NS index SET empty (old data) → fallback to prefix delete via _graph_state."""
        mock_redis.delete = AsyncMock(return_value=0)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(return_value=set())  # empty index
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Fallback to delegate's _graph_state.delete (prefix delete)
        getattr(mock_delegate, "_graph_state").delete.assert_awaited_once_with(
            "sess-1", "wf-1"
        )
        # Delegate.post_workflow_execute NOT called
        mock_delegate.post_workflow_execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_smembers_failure_falls_back_to_prefix_delete(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """SMEMBERS failure → fallback to prefix delete."""
        mock_redis.delete = AsyncMock(return_value=0)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(side_effect=Exception("Redis down"))
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Fallback to delegate's _graph_state.delete (prefix delete)
        getattr(mock_delegate, "_graph_state").delete.assert_awaited_once_with(
            "sess-1", "wf-1"
        )

    @pytest.mark.asyncio
    async def test_empty_ns_index_and_no_graph_state_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """NS index empty + no _graph_state → fallback to delegate post_workflow_execute."""
        mock_redis.delete = AsyncMock(return_value=0)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(return_value=set())
        delattr(mock_delegate, "_graph_state")
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        mock_delegate.post_workflow_execute.assert_awaited_once()


class TestNsIndexingGraphStoreSave:
    """Tests for NsIndexingGraphStore.save recording ns to index SET."""

    @pytest.mark.asyncio
    async def test_save_records_ns_to_index_set(self, mock_delegate, mock_redis):
        """NsIndexingGraphStore.save SADDs ns to per-session index SET."""
        mock_redis.sadd = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        delegate_saver = MagicMock()
        delegate_saver.save = AsyncMock()

        store = NsIndexingGraphStore(
            delegate_saver=delegate_saver,
            redis_client=mock_redis,
            ttl_seconds=86400,
        )
        await store.save("sess-1", "wf-1", MagicMock())

        # Delegate save called
        delegate_saver.save.assert_awaited_once()
        # SADD ns to index SET
        mock_redis.sadd.assert_awaited_once_with("agentBuilder:graph_ns:sess-1", "wf-1")
        # TTL set on index key
        mock_redis.expire.assert_awaited_once_with(
            "agentBuilder:graph_ns:sess-1", 86400
        )

    @pytest.mark.asyncio
    async def test_save_empty_ns_does_not_sadd(self, mock_delegate, mock_redis):
        """NsIndexingGraphStore.save with empty ns → no SADD."""
        mock_redis.sadd = AsyncMock()
        delegate_saver = MagicMock()
        delegate_saver.save = AsyncMock()

        store = NsIndexingGraphStore(
            delegate_saver=delegate_saver,
            redis_client=mock_redis,
            ttl_seconds=86400,
        )
        await store.save("sess-1", "", MagicMock())

        delegate_saver.save.assert_awaited_once()
        mock_redis.sadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_sadd_failure_does_not_block_save(self, mock_delegate, mock_redis):
        """NsIndexingGraphStore.save: SADD failure does not raise."""
        mock_redis.sadd = AsyncMock(side_effect=Exception("Redis write error"))
        mock_redis.expire = AsyncMock()
        delegate_saver = MagicMock()
        delegate_saver.save = AsyncMock()

        store = NsIndexingGraphStore(
            delegate_saver=delegate_saver,
            redis_client=mock_redis,
            ttl_seconds=86400,
        )
        # Should NOT raise
        await store.save("sess-1", "wf-1", MagicMock())

        # Delegate save still called
        delegate_saver.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_and_delete_delegate(self, mock_delegate, mock_redis):
        """NsIndexingGraphStore.get/delete delegate to wrapped saver."""
        delegate_saver = MagicMock()
        delegate_saver.get = AsyncMock(return_value="state")
        delegate_saver.delete = AsyncMock()

        store = NsIndexingGraphStore(
            delegate_saver=delegate_saver,
            redis_client=mock_redis,
            ttl_seconds=86400,
        )
        result = await store.get("sess-1", "wf-1")
        assert result == "state"
        delegate_saver.get.assert_awaited_once_with("sess-1", "wf-1")

        await store.delete("sess-1", "wf-1")
        delegate_saver.delete.assert_awaited_once_with("sess-1", "wf-1")


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
