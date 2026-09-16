"""Regression tests for the agent-runtime hot-path optimizations."""

import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from agent_runtime.context.request_context import RequestContext, _request_ctx
from openjiuwen.core.common.constants.constant import LOOP_ID

import jiuwen.extension.patches.loop_body_session_cleanup_patch as loop_patch
from jiuwen.serve.controllers.execution import ir_converter, open_utils


class _LoopGroupWorkflow:
    """Small stand-in used to exercise the LoopGroup registration branch."""

    def __init__(self):
        self.add_workflow_comp = MagicMock()


class _Workflow:
    """Small stand-in used to exercise the regular Workflow branch."""

    def __init__(self):
        self.add_workflow_comp = MagicMock()


@pytest.mark.parametrize("is_loop_group", [False, True])
def test_component_registration_forwards_name_without_signature_reflection(
    is_loop_group,
):
    """Registration forwards names without reflecting on every component."""
    workflow = _LoopGroupWorkflow() if is_loop_group else _Workflow()
    component = object()
    support_flag = (
        "_LOOP_GROUP_ADD_COMP_SUPPORTS_NAME"
        if is_loop_group
        else "_WORKFLOW_ADD_COMP_SUPPORTS_NAME"
    )

    with (
        patch.object(ir_converter, "LoopGroup", _LoopGroupWorkflow),
        patch.object(ir_converter, support_flag, True),
        patch.object(
            ir_converter.inspect,
            "signature",
            side_effect=AssertionError("registration must not reflect the method"),
        ) as signature,
    ):
        ir_converter._add_workflow_comp_with_exception(
            workflow,
            "node-id",
            component,
            timeout=30,
            max_retries=2,
            exception_config=None,
            node_name="显示名称",
        )

    signature.assert_not_called()
    assert workflow.add_workflow_comp.call_args.args[:2] == ("node-id", component)
    assert workflow.add_workflow_comp.call_args.kwargs["name"] == "显示名称"


def test_openjiuwen_direct_commit_does_not_alias_mutable_payload():
    """Direct commit must isolate mutable payloads when the API is available."""
    try:
        from openjiuwen.core.session.state.base import InMemoryCommitState
    except ImportError:
        pytest.skip("openjiuwen core does not expose InMemoryCommitState")

    state = InMemoryCommitState()
    commit = getattr(state, "update_by_id_and_commit", None)
    if commit is None:
        pytest.skip("openjiuwen core does not expose direct commit API")

    payload = {"loop-node": {"items": []}}
    commit("loop-node", payload)

    payload["loop-node"]["items"].append("mutated-after-commit")

    assert state.get_state()["loop-node"]["items"] == []


def test_loop_state_direct_commit_defaults_to_enabled(monkeypatch):
    """Direct commit is enabled when the rollout variable is not set."""
    monkeypatch.delenv("LOOP_STATE_DIRECT_COMMIT_ENABLED", raising=False)
    importlib.reload(loop_patch)

    assert loop_patch._LOOP_STATE_DIRECT_COMMIT_ENABLED is True


@pytest.mark.asyncio
@pytest.mark.parametrize("source, source_label", [("redis", "Redis"), ("obs", "OBS")])
async def test_async_cache_hit_uses_debug_and_keeps_performance_metric(
    source, source_label
):
    """Normal external cache hits are quiet at INFO but retain source metrics."""
    cached_ir = {"components": {"node": {"type": "jiuwen.message"}}}
    cache = MagicMock()
    cache.aget_with_source = AsyncMock(return_value=(cached_ir, source))
    cache.memory_cache.currsize = 3
    cache.memory_cache.maxsize = 10
    performance_log = MagicMock()

    with (
        patch.object(open_utils, "cache_ir_queue", cache),
        patch.object(open_utils, "logger") as runtime_logger,
        patch.object(open_utils, "_log_ir_content"),
        patch(
            "openjiuwen.core.common.logging.performance_logger",
            performance_log,
        ),
    ):
        result = await open_utils.async_ir_load("workflow.json")

    assert result is cached_ir
    assert any(
        item.args[0].startswith("%s HIT!") and item.args[1] == source_label
        for item in runtime_logger.debug.call_args_list
    )
    assert not any(
        item.args[0].startswith("%s HIT!") and item.args[1] == source_label
        for item in runtime_logger.info.call_args_list
    )
    performance_log.info.assert_called_once()
    assert "ir_load|" in performance_log.info.call_args.args[0]
    assert performance_log.info.call_args.args[0].endswith(f"|{source}")


@pytest.mark.asyncio
async def test_async_slow_redis_hit_keeps_info_diagnostic():
    """Slow cache hits remain visible without logging every normal hit at INFO."""
    cached_ir = {"components": {"node": {"type": "jiuwen.message"}}}
    cache = MagicMock()
    cache.aget_with_source = AsyncMock(return_value=(cached_ir, "redis"))
    cache.memory_cache.currsize = 3
    cache.memory_cache.maxsize = 10

    with (
        patch.object(open_utils, "cache_ir_queue", cache),
        patch.object(open_utils, "logger") as runtime_logger,
        patch.object(open_utils, "_log_ir_content"),
        patch.object(open_utils, "_IR_LOAD_SLOW_CACHE_HIT_MS", -1),
        patch("openjiuwen.core.common.logging.performance_logger"),
    ):
        await open_utils.async_ir_load("workflow.json")

    assert any(
        item.args[0].startswith("Slow %s HIT!") and item.args[1] == "Redis"
        for item in runtime_logger.info.call_args_list
    )


@pytest.mark.asyncio
async def test_async_ir_load_deduplicates_concurrent_same_path_within_request():
    """Concurrent callers for one IR path share one underlying load."""
    cached_ir = {"components": {"node": {"type": "jiuwen.message"}}}
    started = asyncio.Event()
    release = asyncio.Event()
    load_calls = 0

    async def load(_path):
        nonlocal load_calls
        load_calls += 1
        started.set()
        await release.wait()
        return cached_ir, "redis"

    cache = MagicMock()
    cache.aget_with_source = load
    cache.memory_cache.currsize = 3
    cache.memory_cache.maxsize = 10
    token = _request_ctx.set(RequestContext(ir_load_cache={}))
    try:
        with patch.object(open_utils, "cache_ir_queue", cache), patch.object(
            open_utils, "_log_ir_content"
        ):
            first = asyncio.create_task(open_utils.async_ir_load("workflow.json"))
            await started.wait()
            second = asyncio.create_task(open_utils.async_ir_load("workflow.json"))
            await asyncio.sleep(0)
            release.set()
            results = await asyncio.gather(first, second)
    finally:
        _request_ctx.reset(token)

    assert results == [cached_ir, cached_ir]
    assert load_calls == 1


@pytest.mark.asyncio
async def test_async_ir_load_waiter_cancellation_does_not_duplicate_load():
    """Cancelling one waiter does not cancel or duplicate the shared load."""
    cached_ir = {"components": {"node": {"type": "jiuwen.message"}}}
    started = asyncio.Event()
    release = asyncio.Event()
    load_calls = 0

    async def load(_path):
        nonlocal load_calls
        load_calls += 1
        started.set()
        await release.wait()
        return cached_ir, "redis"

    cache = MagicMock()
    cache.aget_with_source = load
    cache.memory_cache.currsize = 3
    cache.memory_cache.maxsize = 10
    token = _request_ctx.set(RequestContext(ir_load_cache={}))
    try:
        with patch.object(open_utils, "cache_ir_queue", cache), patch.object(
            open_utils, "_log_ir_content"
        ):
            first = asyncio.create_task(open_utils.async_ir_load("workflow.json"))
            await started.wait()
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first

            second = asyncio.create_task(open_utils.async_ir_load("workflow.json"))
            await asyncio.sleep(0)
            assert load_calls == 1
            release.set()
            assert await second is cached_ir
    finally:
        release.set()
        _request_ctx.reset(token)


@pytest.mark.asyncio
async def test_async_ir_load_request_memo_does_not_cross_request_boundaries():
    """The same path is loaded independently in two request contexts."""
    cached_ir = {"components": {"node": {"type": "jiuwen.message"}}}
    cache = MagicMock()
    cache.aget_with_source = AsyncMock(return_value=(cached_ir, "memory"))
    token = _request_ctx.set(RequestContext(ir_load_cache={}))
    try:
        with patch.object(open_utils, "cache_ir_queue", cache), patch.object(
            open_utils, "_log_ir_content"
        ):
            assert await open_utils.async_ir_load("workflow.json") is cached_ir
            assert await open_utils.async_ir_load("workflow.json") is cached_ir

            second_token = _request_ctx.set(RequestContext(ir_load_cache={}))
            try:
                assert await open_utils.async_ir_load("workflow.json") is cached_ir
            finally:
                _request_ctx.reset(second_token)
    finally:
        _request_ctx.reset(token)

    assert cache.aget_with_source.await_count == 2


@pytest.mark.asyncio
async def test_async_ir_load_failed_memoized_load_can_retry():
    """A failed in-flight load is removed so a later caller can retry."""
    cached_ir = {"components": {"node": {"type": "jiuwen.message"}}}
    cache = MagicMock()
    cache.aget_with_source = AsyncMock(
        side_effect=[RuntimeError("temporary failure"), (cached_ir, "memory")]
    )
    token = _request_ctx.set(RequestContext(ir_load_cache={}))
    try:
        with patch.object(open_utils, "cache_ir_queue", cache), patch.object(
            open_utils, "_log_ir_content"
        ):
            with pytest.raises(RuntimeError, match="temporary failure"):
                await open_utils.async_ir_load("workflow.json")
            assert await open_utils.async_ir_load("workflow.json") is cached_ir
    finally:
        _request_ctx.reset(token)

    assert cache.aget_with_source.await_count == 2


class _FakeIoState:
    def __init__(self, raw_state):
        self._state = SimpleNamespace(_state=raw_state)
        self.get_state = MagicMock(return_value=raw_state.copy())
        self.update_by_id = MagicMock()
        self.update_by_id_and_commit = MagicMock()


class _FakeWorkflowState:
    def __init__(self, node_id, raw_state):
        self._node_id = node_id
        self._io_state = _FakeIoState(raw_state)
        self.set_outputs = MagicMock()
        self.commit = MagicMock()


class _FakeLoopSession:
    def __init__(self, workflow_state, node_id, parent_id=""):
        self._workflow_state = workflow_state
        self._node_id = node_id
        self._parent_id = parent_id

    def node_id(self):
        return self._node_id

    def state(self):
        return self._workflow_state

    def parent_id(self):
        return self._parent_id

    def tracer(self):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_state, parent_id, expected_state",
    [
        (
            {"loop-node": {"previous": "round-1"}, "preserved": {"value": 1}},
            "",
            {"preserved": {"value": 1}},
        ),
        (
            {
                "parent": {
                    "loop": {
                        "loop-node": {"previous": "round-1"},
                        "preserved": {"value": 1},
                    }
                }
            },
            "parent.loop",
            {"preserved": {"value": 1}},
        ),
    ],
)
async def test_advanced_loop_uses_direct_commit_for_staging_and_cleanup(
    raw_state, parent_id, expected_state
):
    """Loop round writes should bypass deepcopy for both root and nested scopes."""
    node_id = "loop-node"
    workflow_state = _FakeWorkflowState(node_id, raw_state)
    session = _FakeLoopSession(workflow_state, node_id, parent_id)
    node_state = MagicMock()
    node_state.get_outputs.return_value = {"result": "done"}
    node_session = MagicMock()
    node_session.state.return_value = node_state
    compiled = MagicMock()
    compiled.invoke = AsyncMock()
    graph = MagicMock()
    graph.compile.return_value = compiled
    component = SimpleNamespace(_graph=graph)

    with (
        patch.object(loop_patch, "_LOOP_STATE_DIRECT_COMMIT_ENABLED", True),
        patch.object(loop_patch, "NodeSession", return_value=node_session),
    ):
        result = await loop_patch._patched_advanced_loop_on_invoke(
            component,
            {"input": "value"},
            session,
        )

    assert result == {"result": "done"}
    assert workflow_state.set_outputs.call_count == 0
    workflow_state.commit.assert_not_called()
    workflow_state._io_state.get_state.assert_called_once_with(copied=False)
    assert workflow_state._io_state.update_by_id.call_count == 0
    assert workflow_state._io_state.update_by_id_and_commit.call_args_list == [
        call(node_id, {node_id: {LOOP_ID: node_id}}),
        call(node_id, {node_id: expected_state}),
        call(node_id, {node_id: None}),
    ]


@pytest.mark.asyncio
async def test_advanced_loop_can_fall_back_to_staged_state_updates():
    """The direct-commit path has a process-level rollback switch."""
    node_id = "loop-node"
    workflow_state = _FakeWorkflowState(
        node_id,
        {node_id: {"previous": "round-1"}, "preserved": {"value": 1}},
    )
    session = _FakeLoopSession(workflow_state, node_id)
    node_state = MagicMock()
    node_state.get_outputs.return_value = {"result": "done"}
    node_session = MagicMock()
    node_session.state.return_value = node_state
    compiled = MagicMock()
    compiled.invoke = AsyncMock()
    graph = MagicMock()
    graph.compile.return_value = compiled
    component = SimpleNamespace(_graph=graph)

    with (
        patch.object(loop_patch, "_LOOP_STATE_DIRECT_COMMIT_ENABLED", False),
        patch.object(loop_patch, "NodeSession", return_value=node_session),
    ):
        result = await loop_patch._patched_advanced_loop_on_invoke(
            component,
            {"input": "value"},
            session,
        )

    assert result == {"result": "done"}
    assert workflow_state.set_outputs.call_args_list == [
        call({LOOP_ID: node_id}),
        call({"preserved": {"value": 1}}),
    ]
    workflow_state.commit.assert_called_once_with()
    workflow_state._io_state.update_by_id.assert_called_once_with(
        node_id, {node_id: None}
    )
    workflow_state._io_state.update_by_id_and_commit.assert_not_called()


@pytest.mark.asyncio
async def test_advanced_loop_preserves_committed_state_when_body_fails():
    """A failed body keeps the existing no-final-cleanup behavior."""
    node_id = "loop-node"
    workflow_state = _FakeWorkflowState(
        node_id,
        {node_id: {"previous": "round-1"}, "preserved": {"value": 1}},
    )
    session = _FakeLoopSession(workflow_state, node_id)
    node_session = MagicMock()
    compiled = MagicMock()
    compiled.invoke = AsyncMock(side_effect=RuntimeError("body failed"))
    graph = MagicMock()
    graph.compile.return_value = compiled
    component = SimpleNamespace(_graph=graph)

    with (
        patch.object(loop_patch, "_LOOP_STATE_DIRECT_COMMIT_ENABLED", True),
        patch.object(loop_patch, "NodeSession", return_value=node_session),
        pytest.raises(RuntimeError, match="body failed"),
    ):
        await loop_patch._patched_advanced_loop_on_invoke(
            component,
            {"input": "value"},
            session,
        )

    assert workflow_state._io_state.update_by_id_and_commit.call_args_list == [
        call(node_id, {node_id: {LOOP_ID: node_id}}),
        call(node_id, {node_id: {"preserved": {"value": 1}}}),
    ]
