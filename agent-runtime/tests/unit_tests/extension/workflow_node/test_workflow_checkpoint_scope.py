import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from openjiuwen.core.common.constants.constant import INTERACTIVE_INPUT
from openjiuwen.core.graph.pregel import TASK_STATUS_INTERRUPT
from openjiuwen.core.session import InteractiveInput, NodeSession, SubWorkflowSession
from openjiuwen.extensions.checkpointer.redis.storage import WorkflowStorage

from agent_runtime.runner.fast_redis_checkpointer import FastRedisCheckpointer
from jiuwen.extension.patches.workflow_sub_stream_patch import (
    _CheckpointScopedSessionView,
    _checkpoint_scope_id,
    _checkpoint_session,
    _patched_compiled_invoke,
)


def _sub_workflow_session(
    *,
    main_workflow_id="transfer",
    executable_id="node_transfer_child",
    workflow_id="shared-child",
    session_id="session-1",
):
    parent = Mock()
    parent.session_id.return_value = session_id
    parent.config.return_value = object()
    parent.workflow_id.return_value = main_workflow_id
    parent.main_workflow_id.return_value = main_workflow_id
    parent.workflow_nesting_depth.return_value = 0
    parent.state.return_value.create_node_state.return_value = Mock()

    node_session = NodeSession(parent, executable_id)
    session = SubWorkflowSession(node_session, workflow_id)
    session.state().get_workflow_state.return_value = []
    return session


class _StateTrackingCheckpointer:
    def __init__(self):
        self.interrupted_keys = set()
        self.pre_sessions = []
        self.post_sessions = []

    async def pre_workflow_execute(self, session, inputs):
        key = (session.session_id(), session.workflow_id())
        if key in self.interrupted_keys and not isinstance(inputs, InteractiveInput):
            raise RuntimeError(
                f"fresh input collided with interrupted checkpoint: {key}"
            )
        if key not in self.interrupted_keys and isinstance(inputs, InteractiveInput):
            raise RuntimeError(f"no interrupted checkpoint to resume: {key}")
        self.pre_sessions.append(session)

    async def post_workflow_execute(self, session, result, exception):
        key = (session.session_id(), session.workflow_id())
        if exception is None and result.get(TASK_STATUS_INTERRUPT) is not None:
            self.interrupted_keys.add(key)
        else:
            self.interrupted_keys.discard(key)
        self.post_sessions.append(session)


class _FakeCompiledGraph:
    def __init__(self, results, checkpointer=None):
        self._checkpointer = checkpointer or _StateTrackingCheckpointer()
        self._pregel = Mock()
        self._pregel.run = AsyncMock(side_effect=results)

    @property
    def checkpointer(self):
        return self._checkpointer

    @property
    def pregel(self):
        return self._pregel


def test_shared_child_has_deterministic_parent_specific_checkpoint_scopes():
    transfer = _sub_workflow_session()
    collection = _sub_workflow_session(
        main_workflow_id="collection",
        executable_id="node_collection_child",
    )

    assert (
        _checkpoint_scope_id(transfer)
        == "transfer|node_transfer_child|shared-child"
    )
    assert (
        _checkpoint_scope_id(collection)
        == "collection|node_collection_child|shared-child"
    )


def test_executable_nodes_in_one_parent_have_different_checkpoint_scopes():
    first = _sub_workflow_session(executable_id="node_first_child")
    second = _sub_workflow_session(executable_id="node_second_child")

    assert _checkpoint_scope_id(first) != _checkpoint_scope_id(second)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("main_workflow_id", ""),
        ("executable_id", ""),
        ("workflow_id", ""),
        ("main_workflow_id", "transfer|collection"),
        ("executable_id", "node|child"),
        ("workflow_id", "shared|child"),
    ],
)
def test_invalid_subworkflow_identity_raises_checkpoint_scope_error(field, value):
    values = {
        "main_workflow_id": "transfer",
        "executable_id": "node_transfer_child",
        "workflow_id": "shared-child",
    }
    values[field] = value
    session = _sub_workflow_session(**values)

    with pytest.raises(ValueError, match="checkpoint scope"):
        _checkpoint_scope_id(session)


def test_invalid_subworkflow_identity_logs_all_scope_metadata():
    session = _sub_workflow_session(executable_id="")

    with patch(
        "jiuwen.extension.patches.workflow_sub_stream_patch.workflow_logger.error"
    ) as error:
        with pytest.raises(ValueError, match="checkpoint scope"):
            _checkpoint_scope_id(session)

    error.assert_called_once_with(
        "Invalid subworkflow checkpoint scope: session_id=session-1, "
        "main_workflow_id=transfer, executable_id=, "
        "sub_workflow_id=shared-child"
    )


def test_scoped_session_view_overrides_only_workflow_id():
    session = _sub_workflow_session()
    session.custom_attribute = object()
    view = _CheckpointScopedSessionView(session, "parent|node|child")

    assert view.workflow_id() == "parent|node|child"
    assert view.session_id() == session.session_id()
    assert view.state() is session.state()
    assert view.config() is session.config()
    assert view.custom_attribute is session.custom_attribute


def test_checkpoint_session_wraps_subworkflow_with_resolved_scope():
    session = _sub_workflow_session()

    checkpoint_session, checkpoint_scope = _checkpoint_session(session)

    assert isinstance(checkpoint_session, _CheckpointScopedSessionView)
    assert checkpoint_session.workflow_id() == checkpoint_scope
    assert checkpoint_scope == "transfer|node_transfer_child|shared-child"


def test_top_level_checkpoint_session_is_not_wrapped():
    session = Mock()
    session.workflow_id.return_value = "top-level"
    session.session_id.return_value = "session-1"

    checkpoint_session, checkpoint_scope = _checkpoint_session(session)

    assert checkpoint_session is session
    assert checkpoint_scope == "top-level"
    assert checkpoint_session.workflow_id() == "top-level"


def test_top_level_checkpoint_id_with_separator_remains_unchanged():
    session = Mock()
    session.workflow_id.return_value = "top|level"
    session.session_id.return_value = "session-1"

    checkpoint_session, checkpoint_scope = _checkpoint_session(session)

    assert checkpoint_session is session
    assert checkpoint_scope == "top|level"


def test_scoped_session_preserves_native_node_targeted_interactive_path():
    session = _sub_workflow_session()
    node_state = Mock()
    node_state.get.return_value = None
    session.state().create_node_state.return_value = node_state
    checkpoint_session, checkpoint_scope = _checkpoint_session(session)
    inputs = InteractiveInput()
    inputs.update("qa-node", "approved")
    storage = object.__new__(WorkflowStorage)

    process_interactive_inputs = getattr(storage, "_process_interactive_inputs")
    process_interactive_inputs(checkpoint_session, inputs)

    assert checkpoint_scope == "transfer|node_transfer_child|shared-child"
    session.state().create_node_state.assert_called_once_with(
        "node_transfer_child.qa-node", "node_transfer_child"
    )
    assert isinstance(checkpoint_session, NodeSession)
    assert isinstance(checkpoint_session, SubWorkflowSession)
    node_state.update.assert_called_once_with({INTERACTIVE_INPUT: ["approved"]})
    session.state().commit.assert_called_once_with()


@pytest.mark.asyncio
async def test_shared_child_interrupts_resume_independently_by_parent_scope():
    transfer = _sub_workflow_session(session_id="conversation-1")
    collection = _sub_workflow_session(
        main_workflow_id="collection",
        executable_id="node_collection_child",
        session_id="conversation-1",
    )
    compiled = _FakeCompiledGraph(
        [
            {TASK_STATUS_INTERRUPT: True},
            {TASK_STATUS_INTERRUPT: True},
            {},
            {},
        ]
    )

    await _patched_compiled_invoke(compiled, {"amount": 10}, transfer)
    await _patched_compiled_invoke(compiled, {"source": "salary"}, collection)

    transfer_key = (
        "conversation-1",
        "transfer|node_transfer_child|shared-child",
    )
    collection_key = (
        "conversation-1",
        "collection|node_collection_child|shared-child",
    )
    assert compiled.checkpointer.interrupted_keys == {transfer_key, collection_key}

    await _patched_compiled_invoke(
        compiled, InteractiveInput({"answer": "collection"}), collection
    )
    assert compiled.checkpointer.interrupted_keys == {transfer_key}

    await _patched_compiled_invoke(
        compiled, InteractiveInput({"answer": "transfer"}), transfer
    )
    assert compiled.checkpointer.interrupted_keys == set()

    namespaces = [
        invocation.kwargs["config"]["ns"]
        for invocation in compiled.pregel.run.await_args_list
    ]
    assert namespaces == [
        transfer_key[1],
        collection_key[1],
        collection_key[1],
        transfer_key[1],
    ]


@pytest.mark.asyncio
async def test_fast_redis_uses_parent_scoped_child_sentinel_and_delegate_session():
    delegate = MagicMock()
    delegate.pre_workflow_execute = AsyncMock()
    delegate.post_workflow_execute = AsyncMock()
    redis = MagicMock()
    redis.sadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    checkpointer = FastRedisCheckpointer(delegate, redis, ttl_seconds=86400)
    compiled = _FakeCompiledGraph(
        [{TASK_STATUS_INTERRUPT: True}], checkpointer=checkpointer
    )
    transfer = _sub_workflow_session(session_id="conversation-1")

    await _patched_compiled_invoke(compiled, {"amount": 10}, transfer)

    checkpoint_scope = "transfer|node_transfer_child|shared-child"
    redis.sadd.assert_awaited_once_with(
        "agentBuilder:session_exists:conversation-1", checkpoint_scope
    )
    delegate_pre_session = delegate.pre_workflow_execute.await_args.args[0]
    assert delegate_pre_session.workflow_id() == checkpoint_scope
    delegate_post_session = delegate.post_workflow_execute.await_args.args[0]
    assert delegate_post_session.workflow_id() == checkpoint_scope
    delegate.post_workflow_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancelled_child_cleanup_uses_parent_scoped_session():
    transfer = _sub_workflow_session(session_id="conversation-1")
    compiled = _FakeCompiledGraph([asyncio.CancelledError()])

    with pytest.raises(asyncio.CancelledError):
        await _patched_compiled_invoke(compiled, {"amount": 10}, transfer)

    assert len(compiled.checkpointer.post_sessions) == 1
    assert (
        compiled.checkpointer.post_sessions[0].workflow_id()
        == "transfer|node_transfer_child|shared-child"
    )
