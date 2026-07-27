# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
Patch openjiuwen Workflow._sub_stream / _sub_invoke and CompiledGraph._invoke for nested
sub-workflow interrupts.

Root causes:
1. After child graph interrupt, _sub_stream blocks on empty sub_workflow_stream.
2. CompiledGraph._invoke runs pregel.run() but never returns its result, so checking
   result.get("__interrupt__") in _sub_stream always fails.

Applied at import time from jiuwen SubWorkflow until agent-core develop merges the fix.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional

from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.base import CONFIG_KEY, INPUTS_KEY
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.graph.pregel import TASK_STATUS_INTERRUPT
from openjiuwen.core.graph.pregel.base import Interrupt
from openjiuwen.core.graph.pregel.config import PregelConfig
from openjiuwen.core.graph.pregel.constants import MAX_RECURSIVE_LIMIT
from openjiuwen.core.common.constants.constant import INTERACTIVE_INPUT
from openjiuwen.core.session import InteractiveInput
from openjiuwen.core.session import (
    WORKFLOW_EXECUTE_TIMEOUT,
    WORKFLOW_STREAM_FRAME_TIMEOUT,
    NodeSession,
    SubWorkflowSession,
)
from openjiuwen.core.session.stream import OutputSchema, StreamEmitter
from openjiuwen.core.workflow.components.base import ComponentAbility

from jiuwen.extension.patches.aggregate_upstream_resolver import (
    resolve_aggregate_upstream_node_ids_from_workflow,
)

_DEFAULT_SUB_STREAM_RECEIVE_TIMEOUT = 30
_CHECKPOINT_SCOPE_SEPARATOR = "|"

_PATCH_APPLIED = False


def _validated_scope_part(name: str, value: str) -> str:
    if not isinstance(value, str) or not value or _CHECKPOINT_SCOPE_SEPARATOR in value:
        raise ValueError(
            f"Invalid checkpoint scope {name}: expected a non-empty string "
            f"without '{_CHECKPOINT_SCOPE_SEPARATOR}'"
        )
    return value


def _checkpoint_scope_id(session) -> str:
    workflow_id = session.workflow_id()
    if not isinstance(session, SubWorkflowSession):
        return workflow_id

    main_workflow_id = session.main_workflow_id()
    executable_id = session.executable_id()
    try:
        checkpoint_scope = _CHECKPOINT_SCOPE_SEPARATOR.join(
            (
                _validated_scope_part("main_workflow_id", main_workflow_id),
                _validated_scope_part("executable_id", executable_id),
                _validated_scope_part("sub_workflow_id", workflow_id),
            )
        )
    except ValueError:
        workflow_logger.error(
            "Invalid subworkflow checkpoint scope: "
            f"session_id={session.session_id()}, "
            f"main_workflow_id={main_workflow_id}, "
            f"executable_id={executable_id}, "
            f"sub_workflow_id={workflow_id}"
        )
        raise

    workflow_logger.debug(
        "Resolved subworkflow checkpoint scope",
        extra={
            "session_id": session.session_id(),
            "workflow_id": workflow_id,
            "checkpoint_scope": checkpoint_scope,
        },
    )
    return checkpoint_scope


class _CheckpointScopedSessionView(SubWorkflowSession):
    """Type-compatible read-through view with a scoped checkpoint workflow ID.

    The native WorkflowStorage path uses ``isinstance(session, NodeSession)`` to
    retain the parent executable path for node-targeted interactive inputs. This
    view deliberately skips ``SubWorkflowSession.__init__`` and delegates every
    missing attribute to the original session, so it neither creates nor copies
    mutable session state while preserving native NodeSession type semantics.
    """

    def __init__(self, session, checkpoint_scope: str):
        self._checkpoint_session_target = session
        self._checkpoint_scope = checkpoint_scope

    def workflow_id(self) -> str:
        return self._checkpoint_scope

    def __getattr__(self, name: str):
        return getattr(self._checkpoint_session_target, name)


def _checkpoint_session(session) -> tuple[object, str]:
    checkpoint_scope = _checkpoint_scope_id(session)
    if checkpoint_scope == session.workflow_id():
        return session, checkpoint_scope
    return _CheckpointScopedSessionView(session, checkpoint_scope), checkpoint_scope


def _bounded_stream_timeout(session) -> float:
    for key in (WORKFLOW_STREAM_FRAME_TIMEOUT, WORKFLOW_EXECUTE_TIMEOUT):
        timeout = session.get_env(key) if session else None
        if timeout is not None and timeout > 0:
            return float(timeout)
    return float(_DEFAULT_SUB_STREAM_RECEIVE_TIMEOUT)


def _sub_workflow_scope_id(sub_workflow_session) -> str:
    return (
        sub_workflow_session.executable_id()
        if hasattr(sub_workflow_session, "executable_id")
        else sub_workflow_session.node_id()
    )


async def _patched_compiled_invoke(self, inputs, session, config=None):
    """CompiledGraph._invoke that returns pregel.run() result (upstream omits return)."""
    is_main = False
    session_id = session.session_id()
    checkpoint_session, checkpoint_scope = _checkpoint_session(session)
    checkpointer = getattr(self, "_checkpointer")

    if config is None:
        is_main = True
        config = PregelConfig(
            session_id=session_id,
            ns=checkpoint_scope,
            recursion_limit=MAX_RECURSIVE_LIMIT,
        )

    try:
        if is_main:
            await checkpointer.pre_workflow_execute(checkpoint_session, inputs)
        if isinstance(session, SubWorkflowSession):
            _prepare_sub_workflow_aggregate_io("compiled_invoke", session, inputs)
            # 子工作流恢复场景：确保 raw_inputs 写入 workflow_state，使 QA 能读到用户回复。
            # 仅在 InteractiveInput 且 raw_inputs 非空时写入（补足 is_main=False 时
            # pre_workflow_execute 不被调用的缺口）；非恢复场景的泄漏清除由 QA 节点负责。
            if isinstance(inputs, InteractiveInput) and inputs.raw_inputs is not None:
                session.state().update_and_commit_workflow_state(
                    {INTERACTIVE_INPUT: inputs.raw_inputs}
                )
        if not isinstance(inputs, InteractiveInput):
            session.state().commit_user_inputs(inputs)
        result = None
        exception = None

        try:
            result = await self._pregel.run(config=config)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            exception = e

        if is_main:
            await checkpointer.post_workflow_execute(
                checkpoint_session, result, exception
            )
        elif exception is not None:
            raise exception

        if exception is not None:
            raise exception
        return result
    except asyncio.CancelledError:
        if is_main:
            await checkpointer.post_workflow_execute(
                checkpoint_session, {}, None
            )
        raise


def _interrupt_output_schema(result: Any) -> Optional[OutputSchema]:
    if not isinstance(result, dict):
        return None
    interrupt_bundle = result.get(TASK_STATUS_INTERRUPT)
    if interrupt_bundle is None:
        return None

    candidates = (
        interrupt_bundle if isinstance(interrupt_bundle, tuple) else (interrupt_bundle,)
    )
    for item in candidates:
        if isinstance(item, Interrupt):
            value = item.value
            if isinstance(value, OutputSchema):
                return value
    return None


def _clear_scoped_node_io_state(
    sub_workflow_session, scope_id: str, node_ids: tuple[str, ...]
) -> list[str]:
    """Drop io_state outputs for scoped nodes under a sub-workflow / loop-body scope."""
    io_state = getattr(sub_workflow_session.state(), "_io_state", None)
    if io_state is None or not scope_id or not node_ids:
        return []

    cleared: list[str] = []
    for node_id in node_ids:
        nested_key = f"{scope_id}.{node_id}"
        io_state.update_by_id(nested_key, {nested_key: None})
        cleared.append(node_id)
    if cleared:
        io_state.commit()
    return cleared


def _cache_aggregate_ids_on_session(sub_workflow_session, workflow_self) -> None:
    sub_workflow_session._aggregate_upstream_node_ids = (
        resolve_aggregate_upstream_node_ids_from_workflow(workflow_self)
    )


def _prepare_sub_workflow_aggregate_io(
    mode: str, sub_workflow_session, inputs: Input
) -> None:
    """Prepare aggregate io_state before a sub-workflow graph run.

    - InteractiveInput resume: clear only upstream branches not in
      ``executed_nodes``. Aggregate outputs are preserved because pregel
      skips nodes already in ``executed_nodes``; clearing them would leave
      downstream references (``${aggregate.xxx}``) reading None on resume.
    - Fresh / loop re-entry (non-InteractiveInput): clear **all** aggregate upstream
      io so first-non-null does not read a prior path/round (executed_nodes may still
      list nodes from the previous inner run).
    """
    if not isinstance(sub_workflow_session, SubWorkflowSession):
        return

    scope_id = _sub_workflow_scope_id(sub_workflow_session)
    if not scope_id:
        return

    upstream_ids = getattr(sub_workflow_session, "_aggregate_upstream_node_ids", ()) or ()

    if isinstance(inputs, InteractiveInput):
        executed_nodes = set(
            sub_workflow_session.state().get_workflow_state("executed_nodes") or []
        )
        stale_upstream = tuple(
            node_id for node_id in upstream_ids if node_id not in executed_nodes
        )
        _clear_scoped_node_io_state(sub_workflow_session, scope_id, stale_upstream)
        return

    _clear_scoped_node_io_state(sub_workflow_session, scope_id, upstream_ids)


def _reset_sub_workflow_runtime_state(self) -> None:
    internal = getattr(self, "_internal", None)
    graph = getattr(internal, "_graph", None) if internal is not None else None
    get_nodes = getattr(graph, "get_nodes", None)
    if get_nodes is None:
        return
    for vertex in get_nodes().values():
        executable = getattr(vertex, "_executable", None)
        if hasattr(executable, "_invoke_executed"):
            setattr(executable, "_invoke_executed", False)
        if hasattr(executable, "_stream_executed"):
            setattr(executable, "_stream_executed", False)
        if hasattr(executable, "_collect_executed"):
            setattr(executable, "_collect_executed", False)
        if hasattr(executable, "_transform_executed"):
            setattr(executable, "_transform_executed", False)
        reset_stream_output = getattr(executable, "_reset_stream_output", None)
        if callable(reset_stream_output):
            reset_stream_output()


def _reset_sub_workflow_component_outputs(self, sub_workflow_session, inputs: Input) -> None:
    """Clear stale outputs for nodes inside a sub-workflow before a fresh run."""
    if isinstance(inputs, InteractiveInput):
        return

    internal = getattr(self, "_internal", None)
    if internal is None:
        return
    workflow_spec = internal.config().spec
    node_ids = list((workflow_spec.comp_configs or {}).keys())
    if not node_ids:
        return

    scope_id = _sub_workflow_scope_id(sub_workflow_session)
    if not scope_id:
        return

    io_state = getattr(sub_workflow_session.state(), "_io_state", None)
    if io_state is None:
        return
    io_state.update_by_id(scope_id, {scope_id: None})
    io_state.commit()


async def _patched_sub_stream(
    self,
    inputs: Input,
    session,
    context: ModelContext = None,
    **kwargs,
) -> AsyncIterator[Output]:
    sub_workflow_session = self._create_workflow_session(session, is_sub=True)
    _cache_aggregate_ids_on_session(sub_workflow_session, self)
    try:
        _reset_sub_workflow_runtime_state(self)
        if bool(kwargs.get("reset_sub_outputs")):
            _reset_sub_workflow_component_outputs(self, sub_workflow_session, inputs)
        _prepare_sub_workflow_aggregate_io("sub_stream", sub_workflow_session, inputs)
        compiled_graph = self._internal.compile(sub_workflow_session, context=context)
        result = await compiled_graph.invoke(
            {INPUTS_KEY: inputs, CONFIG_KEY: kwargs.get(CONFIG_KEY)},
            sub_workflow_session,
        )

        interrupt_chunk = _interrupt_output_schema(result)
        if interrupt_chunk is not None:
            yield interrupt_chunk
            return

        if self._is_streaming:
            stream_timeout = _bounded_stream_timeout(session)
            sub_end_ability = (
                self._internal.config()
                .spec.comp_configs.get(self._end_comp_id)
                .abilities
            )
            required_abilities = [ComponentAbility.STREAM, ComponentAbility.TRANSFORM]
            stream_ability_count = sum(
                ability in sub_end_ability for ability in required_abilities
            )
            while stream_ability_count > 0:
                try:
                    frame = (
                        await sub_workflow_session.actor_manager()
                        .sub_workflow_stream()
                        .receive(stream_timeout)
                    )
                except asyncio.TimeoutError:
                    return
                if frame is None:
                    continue
                if frame == StreamEmitter.END_FRAME:
                    stream_ability_count -= 1
                    continue
                yield frame
    finally:
        await asyncio.shield(sub_workflow_session.close())
        await asyncio.shield(self._internal.reset())


async def _patched_sub_invoke(
    self,
    inputs: Input,
    session,
    context: ModelContext = None,
    **kwargs,
) -> Output:
    sub_workflow_session = self._create_workflow_session(session, is_sub=True)
    _cache_aggregate_ids_on_session(sub_workflow_session, self)

    try:
        _reset_sub_workflow_runtime_state(self)
        if bool(kwargs.get("reset_sub_outputs")):
            _reset_sub_workflow_component_outputs(self, sub_workflow_session, inputs)
        _prepare_sub_workflow_aggregate_io("sub_invoke", sub_workflow_session, inputs)
        compiled_graph = self._internal.compile(sub_workflow_session, context)
        result = await compiled_graph.invoke(
            {INPUTS_KEY: inputs, CONFIG_KEY: kwargs.get(CONFIG_KEY)},
            sub_workflow_session,
        )

        interrupt_chunk = _interrupt_output_schema(result)
        if interrupt_chunk is not None:
            return {"stream": [interrupt_chunk]}

        if self._is_streaming:
            messages = []
            sub_end_ability = (
                self._internal.config()
                .spec.comp_configs.get(self._end_comp_id)
                .abilities
            )
            required_abilities = [ComponentAbility.STREAM, ComponentAbility.TRANSFORM]
            stream_ability_count = sum(
                ability in sub_end_ability for ability in required_abilities
            )
            stream_timeout = _bounded_stream_timeout(session)
            while stream_ability_count > 0:
                try:
                    frame = (
                        await sub_workflow_session.actor_manager()
                        .sub_workflow_stream()
                        .receive(stream_timeout)
                    )
                except asyncio.TimeoutError:
                    break
                if frame is None:
                    continue
                if frame == StreamEmitter.END_FRAME:
                    stream_ability_count -= 1
                    continue
                messages.append(frame)
            if messages:
                return dict(stream=messages)

        node_session = NodeSession(sub_workflow_session, self._end_comp_id)
        output_key = self._end_comp_id
        fallback_outputs = node_session.state().get_outputs(output_key)
        return fallback_outputs
    finally:
        await asyncio.shield(sub_workflow_session.close())
        await asyncio.shield(self._internal.reset())


def apply_workflow_sub_stream_patch() -> bool:
    """Monkey-patch Workflow sub-stream helpers and CompiledGraph._invoke once per process."""
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return False

    from openjiuwen.core.graph.graph import CompiledGraph
    from openjiuwen.core.workflow.workflow import Workflow

    CompiledGraph._invoke = _patched_compiled_invoke
    Workflow._sub_stream = _patched_sub_stream
    Workflow._sub_invoke = _patched_sub_invoke
    _PATCH_APPLIED = True
    return True
