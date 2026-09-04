import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent_runtime.supervisor import runner as runner_module
from agent_runtime.supervisor.skill_context import (
    attach_agent_context,
    get_skill_context,
    reset_skill_context as real_reset_skill_context,
)
from agent_runtime.supervisor.event.channel import get_channel
from agent_runtime.supervisor.skill_model import SkillDescriptor


def descriptor(skill_id, version_id):
    return SkillDescriptor(
        skill_id=skill_id,
        version_id=version_id,
        name=f"name-{skill_id}",
        description=f"description-{skill_id}",
        object_key=f"user/skills/{skill_id}/{version_id}/{skill_id}.zip",
    )


class EmptyAgent:
    card = object()

    async def stream(self, _inputs, _session):
        if False:
            yield None


class FailingAgent:
    card = object()

    async def stream(self, _inputs, _session):
        raise RuntimeError("stream exploded")
        yield None


@pytest.mark.asyncio
@pytest.mark.parametrize("agent", [EmptyAgent(), FailingAgent()])
async def test_runner_resets_skill_context_after_normal_and_failing_stream(monkeypatch, agent):
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    reset = Mock(wraps=real_reset_skill_context)
    monkeypatch.setattr(runner_module, "reset_skill_context", reset)
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())

    events = [event async for event in runner_module.run_supervisor(agent, "q", "c1", "e1")]

    assert reset.call_count == 1
    assert get_skill_context() is None
    if isinstance(agent, FailingAgent):
        assert events[0]["event"] == "error"
    else:
        assert events[0]["event"] == "run_done"


@pytest.mark.asyncio
async def test_early_close_cancels_stream_task_before_context_reset_and_isolates_concurrent_nested_agent(monkeypatch):
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    monkeypatch.setattr(
        runner_module,
        "adapt_stream_chunk",
        lambda _chunk, ctx: [{"event": "message", "data": {"skill": ctx.execution_id}}],
    )
    first_started = asyncio.Event()
    first_finished = asyncio.Event()
    release_first = asyncio.Event()
    observed = []

    class NestedAgent:
        async def stream(self):
            observed.append(("nested", get_skill_context().catalog_by_id["s1"].version_id))
            yield object()

    class BlockingAgent:
        card = object()

        async def stream(self, _inputs, _session):
            observed.append(("top", get_skill_context().catalog_by_id["s1"].version_id))
            async for chunk in NestedAgent().stream():
                yield chunk
            first_started.set()
            try:
                await release_first.wait()
            finally:
                first_finished.set()

    class CompleteAgent:
        card = object()

        async def stream(self, _inputs, _session):
            observed.append(("concurrent", get_skill_context().catalog_by_id["s1"].version_id))
            yield object()

    first_agent = BlockingAgent()
    second_agent = CompleteAgent()
    attach_agent_context(first_agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    attach_agent_context(second_agent, [descriptor("s1", "v2")], [], SimpleNamespace())
    first_stream = runner_module.run_supervisor(first_agent, "q", "c1", "e1")

    first_event = await first_stream.__anext__()
    await first_started.wait()
    second_events = [event async for event in runner_module.run_supervisor(second_agent, "q", "c2", "e2")]
    await first_stream.aclose()

    assert first_event["event"] == "message"
    assert second_events[-1]["event"] == "run_done"
    assert first_finished.is_set()
    assert observed == [("top", "v1"), ("nested", "v1"), ("concurrent", "v2")]
    assert get_skill_context() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_point", ["channel", "session"])
async def test_runner_resets_bound_context_when_initialization_fails(monkeypatch, failure_point):
    agent = EmptyAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    reset_order = []
    original_reset_channel = runner_module.reset_channel
    original_reset_skill = runner_module.reset_skill_context

    def reset_channel(token):
        reset_order.append("channel")
        original_reset_channel(token)

    def reset_skill(token):
        reset_order.append("skill")
        original_reset_skill(token)

    monkeypatch.setattr(runner_module, "reset_channel", reset_channel)
    monkeypatch.setattr(runner_module, "reset_skill_context", reset_skill)
    if failure_point == "channel":
        class ExplodingChannel:
            def __init__(self, _execution_id):
                raise RuntimeError("channel setup failed")

        monkeypatch.setattr(runner_module, "EventChannel", ExplodingChannel)
    else:
        monkeypatch.setattr(runner_module, "create_agent_session", Mock(side_effect=RuntimeError("session setup failed")))

    with pytest.raises(RuntimeError, match="setup failed"):
        await runner_module.run_supervisor(agent, "q", "c1", "e1").__anext__()

    assert get_skill_context() is None
    assert get_channel() is None
    assert reset_order == (["skill"] if failure_point == "channel" else ["channel", "skill"])


class WorkerAbort(BaseException):
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [asyncio.CancelledError(), WorkerAbort("worker base exception")])
async def test_runner_resets_after_worker_base_exception_and_preserves_it(monkeypatch, failure):
    class BaseFailingAgent:
        card = object()

        async def stream(self, _inputs, _session):
            raise failure
            yield None

    agent = BaseFailingAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())

    stream = runner_module.run_supervisor(agent, "q", "c1", "e1")
    with pytest.raises(type(failure)):
        await stream.__anext__()

    assert get_channel() is None
    assert get_skill_context() is None


@pytest.mark.asyncio
async def test_cancelled_queue_consumer_waits_for_child_before_reset(monkeypatch):
    class BlockingAgent:
        card = object()

        async def stream(self, _inputs, _session):
            child_started.set()
            try:
                await release.wait()
            finally:
                child_finished.set()
            if False:
                yield None

    child_started = asyncio.Event()
    child_finished = asyncio.Event()
    release = asyncio.Event()
    reset_order = []
    agent = BlockingAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    original_reset_channel = runner_module.reset_channel
    original_reset_skill = runner_module.reset_skill_context

    def reset_channel(token):
        assert child_finished.is_set()
        reset_order.append("channel")
        original_reset_channel(token)

    def reset_skill(token):
        assert child_finished.is_set()
        reset_order.append("skill")
        original_reset_skill(token)

    monkeypatch.setattr(runner_module, "reset_channel", reset_channel)
    monkeypatch.setattr(runner_module, "reset_skill_context", reset_skill)
    stream = runner_module.run_supervisor(agent, "q", "c1", "e1")
    consumer = asyncio.create_task(stream.__anext__())
    await child_started.wait()
    consumer.cancel()

    with pytest.raises(asyncio.CancelledError):
        await consumer

    assert child_finished.is_set()
    assert reset_order == ["channel", "skill"]


@pytest.mark.asyncio
async def test_reset_channel_failure_still_resets_skill_after_child_finishes(monkeypatch):
    class BlockingAgent:
        card = object()

        async def stream(self, _inputs, _session):
            yield object()
            try:
                await release.wait()
            finally:
                child_finished.set()

    child_finished = asyncio.Event()
    release = asyncio.Event()
    reset_order = []
    agent = BlockingAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    monkeypatch.setattr(runner_module, "adapt_stream_chunk", lambda *_args: [{"event": "message", "data": {}}])
    original_reset_channel = runner_module.reset_channel
    original_reset_skill = runner_module.reset_skill_context

    def reset_channel(token):
        assert child_finished.is_set()
        reset_order.append("channel")
        original_reset_channel(token)
        raise RuntimeError("channel reset failed")

    def reset_skill(token):
        assert child_finished.is_set()
        reset_order.append("skill")
        original_reset_skill(token)

    monkeypatch.setattr(runner_module, "reset_channel", reset_channel)
    monkeypatch.setattr(runner_module, "reset_skill_context", reset_skill)
    stream = runner_module.run_supervisor(agent, "q", "c1", "e1")

    await stream.__anext__()
    await stream.aclose()

    assert child_finished.is_set()
    assert reset_order == ["channel", "skill"]
    assert get_channel() is None
    assert get_skill_context() is None


@pytest.mark.asyncio
async def test_normal_completion_propagates_channel_reset_failure_after_skill_reset(monkeypatch):
    agent = EmptyAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    original_reset_channel = runner_module.reset_channel
    original_reset_skill = runner_module.reset_skill_context
    reset_order = []

    def reset_channel(token):
        reset_order.append("channel")
        original_reset_channel(token)
        raise RuntimeError("channel reset failed")

    def reset_skill(token):
        reset_order.append("skill")
        original_reset_skill(token)

    monkeypatch.setattr(runner_module, "reset_channel", reset_channel)
    monkeypatch.setattr(runner_module, "reset_skill_context", reset_skill)

    with pytest.raises(RuntimeError, match="channel reset failed"):
        _ = [event async for event in runner_module.run_supervisor(agent, "q", "c1", "e1")]

    assert reset_order == ["channel", "skill"]
    assert get_channel() is None
    assert get_skill_context() is None


@pytest.mark.asyncio
async def test_repeated_consumer_cancellation_waits_for_child_before_reset(monkeypatch):
    class CancellationDelayingAgent:
        card = object()

        async def stream(self, _inputs, _session):
            child_started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                child_cancelled.set()
                await release_after_cancel.wait()
                raise
            finally:
                child_finished.set()
            if False:
                yield None

    child_started = asyncio.Event()
    child_cancelled = asyncio.Event()
    child_finished = asyncio.Event()
    release = asyncio.Event()
    release_after_cancel = asyncio.Event()
    reset_order = []
    agent = CancellationDelayingAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    original_reset_channel = runner_module.reset_channel
    original_reset_skill = runner_module.reset_skill_context

    def reset_channel(token):
        assert child_finished.is_set()
        reset_order.append("channel")
        original_reset_channel(token)

    def reset_skill(token):
        assert child_finished.is_set()
        reset_order.append("skill")
        original_reset_skill(token)

    monkeypatch.setattr(runner_module, "reset_channel", reset_channel)
    monkeypatch.setattr(runner_module, "reset_skill_context", reset_skill)
    stream = runner_module.run_supervisor(agent, "q", "c1", "e1")
    consumer = asyncio.create_task(stream.__anext__())
    await child_started.wait()
    consumer.cancel()
    await child_cancelled.wait()
    consumer.cancel()
    release_after_cancel.set()

    with pytest.raises(asyncio.CancelledError):
        await consumer

    assert child_finished.is_set()
    assert reset_order == ["channel", "skill"]


@pytest.mark.asyncio
async def test_cancelling_close_task_escalates_to_child_and_propagates_without_manual_release(monkeypatch):
    class EscalationAgent:
        card = object()

        async def stream(self, _inputs, _session):
            yield object()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                first_cancel.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    second_cancel.set()
                    raise
            finally:
                child_finished.set()

    first_cancel = asyncio.Event()
    second_cancel = asyncio.Event()
    child_finished = asyncio.Event()
    agent = EscalationAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    monkeypatch.setattr(runner_module, "adapt_stream_chunk", lambda *_args: [{"event": "message", "data": {}}])

    async def consume_and_close():
        stream = runner_module.run_supervisor(agent, "q", "c1", "e1")
        await stream.__anext__()
        await stream.aclose()

    close_task = asyncio.create_task(consume_and_close())
    await first_cancel.wait()
    close_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await close_task

    assert second_cancel.is_set()
    assert child_finished.is_set()
    assert get_channel() is None
    assert get_skill_context() is None


@pytest.mark.asyncio
async def test_same_turn_child_completion_does_not_hide_new_close_task_cancellation(monkeypatch):
    class SameTurnAgent:
        card = object()

        async def stream(self, _inputs, _session):
            yield object()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cleanup_cancelled.set()
                await release_child.wait()
                child_finished.set()
                raise

    cleanup_cancelled = asyncio.Event()
    release_child = asyncio.Event()
    child_finished = asyncio.Event()
    reset_order = []
    agent = SameTurnAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    monkeypatch.setattr(runner_module, "adapt_stream_chunk", lambda *_args: [{"event": "message", "data": {}}])
    original_reset_channel = runner_module.reset_channel
    original_reset_skill = runner_module.reset_skill_context

    def reset_channel(token):
        assert child_finished.is_set()
        reset_order.append("channel")
        original_reset_channel(token)

    def reset_skill(token):
        assert child_finished.is_set()
        reset_order.append("skill")
        original_reset_skill(token)

    monkeypatch.setattr(runner_module, "reset_channel", reset_channel)
    monkeypatch.setattr(runner_module, "reset_skill_context", reset_skill)

    async def consume_and_close():
        stream = runner_module.run_supervisor(agent, "q", "c1", "e1")
        await stream.__anext__()
        await stream.aclose()

    close_task = asyncio.create_task(consume_and_close())
    await cleanup_cancelled.wait()
    loop = asyncio.get_running_loop()
    loop.call_soon(release_child.set)
    loop.call_soon(close_task.cancel)

    with pytest.raises(asyncio.CancelledError):
        await close_task

    assert child_finished.is_set()
    assert reset_order == ["channel", "skill"]


@pytest.mark.asyncio
async def test_generator_close_propagates_child_base_exception_from_cancellation_cleanup(monkeypatch):
    class CleanupFailure(BaseException):
        pass

    class FailingCleanupAgent:
        card = object()

        async def stream(self, _inputs, _session):
            yield object()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise CleanupFailure("child cleanup failed")

    agent = FailingCleanupAgent()
    attach_agent_context(agent, [descriptor("s1", "v1")], [], SimpleNamespace())
    monkeypatch.setattr(runner_module, "create_agent_session", lambda **_kwargs: object())
    monkeypatch.setattr(runner_module, "adapt_stream_chunk", lambda *_args: [{"event": "message", "data": {}}])
    stream = runner_module.run_supervisor(agent, "q", "c1", "e1")

    await stream.__anext__()
    with pytest.raises(CleanupFailure, match="child cleanup failed"):
        await stream.aclose()

    assert get_channel() is None
    assert get_skill_context() is None
