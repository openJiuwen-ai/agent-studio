# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""Unit tests for FastRedisCheckpointer.

Tests cover:
- session_exists: O(1) sentinel SET check (SCARD)
- pre_workflow_execute: delegate + SADD to sentinel SET
- post_workflow_execute: normal completion / interrupt / exception paths
- _clear_checkpoint_and_sentinel: prefix GraphStore delete + bare session key
  delete + SREM sentinel + workflow_storage.clear
- delegate passthrough methods
- feature toggle
"""

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

    # _graph_state mock — GraphStore with prefix-based delete
    graph_state_mock = MagicMock()
    graph_state_mock.delete = AsyncMock()
    setattr(delegate, "_graph_state", graph_state_mock)

    # workflow_storage mock
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

        mock_delegate.pre_workflow_execute.assert_awaited_once()
        mock_redis.sadd.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )
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

        await checkpointer.pre_workflow_execute(mock_session, MagicMock())
        mock_delegate.pre_workflow_execute.assert_awaited_once()


class TestPostWorkflowExecute:
    @staticmethod
    def _make_session(session_id="sess-1", workflow_id="wf-1"):
        mock = MagicMock()
        mock.session_id = MagicMock(return_value=session_id)
        mock.workflow_id = MagicMock(return_value=workflow_id)
        return mock

    @staticmethod
    def _get_graph_state(mock_delegate):
        return getattr(mock_delegate, "_graph_state")

    # ── Normal completion path ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_normal_completion_precise_delete_graph_state(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: precisely deletes recorded graph keys — no full-keyspace scan_iter."""
        mock_redis.smembers = AsyncMock(return_value={b"k1", b"k2"})
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        result = {}  # No TASK_STATUS_INTERRUPT → normal completion
        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Recorded graph keys deleted precisely (no GraphStore.delete / delete_by_prefix scan_iter)
        key_delete_calls = [
            c[0] for c in mock_redis.delete.call_args_list if len(c[0]) == 2
        ]
        assert key_delete_calls, "expected a 2-key precise delete call"
        assert set(key_delete_calls[0]) == {"k1", "k2"}
        # graph_keys tracking SET itself deleted
        mock_redis.delete.assert_any_call("agentBuilder:graph_keys:sess-1")
        # GraphStore.delete (full-keyspace scan) NOT called
        gs = self._get_graph_state(mock_delegate)
        gs.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_normal_completion_deletes_bare_session_key(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: bare session key (session_id) deleted to clear comp_state."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        result = {}
        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Bare session key deleted via self._redis.delete(session_id)
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list if c[0]]
        assert "sess-1" in delete_calls

    @pytest.mark.asyncio
    async def test_normal_completion_srem_sentinel(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: SREM workflow_id from sentinel SET."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        result = {}
        await checkpointer.post_workflow_execute(mock_session, result, None)

        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )

    @pytest.mark.asyncio
    async def test_normal_completion_workflow_storage_clear(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: workflow_storage.clear delegated."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        result = {}
        await checkpointer.post_workflow_execute(mock_session, result, None)

        getattr(mock_delegate, "_workflow_storage").clear.assert_awaited_once_with("wf-1", "sess-1")

    @pytest.mark.asyncio
    async def test_normal_completion_no_delegate_post_workflow(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Normal completion: delegate.post_workflow_execute NOT called (we handle cleanup)."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()

        result = {}
        await checkpointer.post_workflow_execute(mock_session, result, None)

        mock_delegate.post_workflow_execute.assert_not_called()

    # ── Exception path ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_exception_path_precise_delete_and_bare_key(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Exception path: same cleanup as normal completion (precise delete + bare key delete)."""
        mock_redis.smembers = AsyncMock(return_value={b"ek1"})
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()
        test_exception = RuntimeError("boom")

        await checkpointer.post_workflow_execute(mock_session, None, test_exception)

        # Delegate NOT called
        mock_delegate.post_workflow_execute.assert_not_called()

        # Precise delete of recorded graph key (no GraphStore.delete / scan_iter)
        mock_redis.delete.assert_any_call("ek1")
        gs = self._get_graph_state(mock_delegate)
        gs.delete.assert_not_called()

        # Bare session key deleted
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list if c[0]]
        assert "sess-1" in delete_calls

        # SREM
        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "wf-1"
        )

    @pytest.mark.asyncio
    async def test_workflow_abort_exception_clears_checkpoint(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """WorkflowAbortException clears checkpoint like normal completion."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
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

        mock_delegate.post_workflow_execute.assert_not_called()
        gs = self._get_graph_state(mock_delegate)
        gs.delete.assert_not_called()

    # ── Interrupt path ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_interrupt_path_keeps_sentinel(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Interrupt path: delegate saves checkpoint, no cleanup."""
        mock_session = self._make_session()
        result = {"__interrupt__": True}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        mock_delegate.post_workflow_execute.assert_awaited_once()
        mock_redis.delete.assert_not_called()
        mock_redis.srem.assert_not_called()
        gs = self._get_graph_state(mock_delegate)
        gs.delete.assert_not_called()

    # ── Fallback paths ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_graph_key_tracking_failure_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Tracking SET smembers/delete failure → fallback to delegate post_workflow_execute."""
        mock_redis.smembers = AsyncMock(side_effect=Exception("Redis smembers error"))
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Delegate called as fallback (precise delete failed)
        mock_delegate.post_workflow_execute.assert_awaited_once()
        # SREM/delete NOT reached (we returned early)
        mock_redis.srem.assert_not_called()

    @pytest.mark.asyncio
    async def test_workflow_storage_clear_failure_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """workflow_storage.clear() failure → fallback to delegate."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        getattr(mock_delegate, "_workflow_storage").clear = AsyncMock(
            side_effect=Exception("Redis error in clear")
        )
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)
        mock_delegate.post_workflow_execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_workflow_storage_falls_back_to_delegate(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """If delegate has no _workflow_storage → fallback to delegate."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        delattr(mock_delegate, "_workflow_storage")
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)
        mock_delegate.post_workflow_execute.assert_awaited_once()

    # ── Sub-workflow completion ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_sub_workflow_completion_preserves_main_sentinel(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Sub-workflow normal completion only SREMs its own workflow_id."""
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        sub_session = self._make_session(session_id="sess-1", workflow_id="sub-wf")
        result = {}

        await checkpointer.post_workflow_execute(sub_session, result, None)

        mock_redis.srem.assert_awaited_once_with(
            "agentBuilder:session_exists:sess-1", "sub-wf"
        )
        # Bare session key deleted (session_id level, not workflow_id level)
        delete_calls = [c[0][0] for c in mock_redis.delete.call_args_list if c[0]]
        assert "sess-1" in delete_calls
        assert "agentBuilder:session_exists:sess-1" not in delete_calls

    @pytest.mark.asyncio
    async def test_bare_key_delete_failure_does_not_block_sentinel(
        self, checkpointer, mock_delegate, mock_redis
    ):
        """Bare session key delete failure does NOT block SREM or workflow_storage.clear."""
        mock_redis.smembers = AsyncMock(return_value=set())

        def fake_delete(*args):
            if len(args) == 1 and args[0] == "sess-1":
                raise Exception("bare key delete error")
            return 1

        mock_redis.delete = AsyncMock(side_effect=fake_delete)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_session = self._make_session()
        result = {}

        await checkpointer.post_workflow_execute(mock_session, result, None)

        # Precise graph key delete still called (tracking SET + fallback main keys)
        gs = self._get_graph_state(mock_delegate)
        gs.delete.assert_not_called()
        # SREM still called (not blocked by bare key failure)
        mock_redis.srem.assert_awaited_once()
        # workflow_storage.clear still called
        getattr(mock_delegate, "_workflow_storage").clear.assert_awaited_once()


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
        """release() delegates but does NOT delete sentinel SET."""
        await checkpointer.release("sess-1")
        mock_delegate.release.assert_awaited_once_with("sess-1", None)
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
    def test_graph_store_returns_tracking_wrapper(checkpointer, mock_delegate):
        """graph_store() returns a _TrackingGraphStore wrapping the delegate graph store."""
        from agent_runtime.runner.fast_redis_checkpointer import _TrackingGraphStore
        mock_delegate.graph_store.return_value = "delegate_graph_store"
        result = checkpointer.graph_store()
        assert isinstance(result, _TrackingGraphStore)
        assert result._delegate == "delegate_graph_store"
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
        mock_redis.scard = AsyncMock(return_value=1)
        result = await fast.session_exists("sess-1")
        assert result is True
        mock_delegate.session_exists.assert_not_called()
