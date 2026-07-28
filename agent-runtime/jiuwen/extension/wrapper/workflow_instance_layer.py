#!/usr/bin/env python
# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""Legacy jiuwen workflow instance surface built on top of WorkflowWrapper."""

from types import SimpleNamespace
from typing import Any, AsyncGenerator, NamedTuple, Union

from jiuwen.controller.common.message import Message
from jiuwen.extension.wrapper.message_converter import WorkflowMessageConverter
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.orchestration.flow.stream.base import StreamData


class _AstreamArgs(NamedTuple):
    """Normalized arguments for WorkflowWrapper.astream()."""

    query: Any
    params: dict
    workflow_id: str
    agent_id: str
    session_id: str
    context: Any
    workflow_name: str


class _RuntimeContext(dict):
    """Dict runtime context with the old ``set`` method."""

    def set(self, key: str, value: Any = None) -> None:
        if key:
            self[key] = value


class _CompatGraphInstance:
    """Temporary graph facade for legacy callers outside WorkflowHandler."""

    def __init__(self, owner: "OpenJiuWenWorkflowInstanceLayer"):
        self._owner = owner
        self.runtime_context = owner.get_runtime_context()
        self.stop_bpmn_flag = False

    async def async_clean_up(self) -> None:
        await self._owner.cleanup()

    def get_workflow_execute_status(self):
        return self._owner.get_workflow_execute_status()

    def get_state(self):
        return self._owner.get_workflow_state()


class OpenJiuWenWorkflowInstanceLayer(WorkflowWrapper):
    """Expose the old jiuwen workflow instance contract without changing WorkflowWrapper."""

    def __init__(
        self,
        workflow_id: str = None,
        workflow_name: str = "",
        description: str = "",
        params: dict = None,
        agent_id: str = "",
        session_id: str = "",
        context=None,
        node_name_type_map: dict[str, dict] = None,
    ):
        super().__init__(node_name_type_map=node_name_type_map)
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.description = description
        self.params = params or {}
        self.agent_id = agent_id or ""
        self.session_id = session_id or ""
        self._context = context
        self.graph_engine = SimpleNamespace(graph_instance=_CompatGraphInstance(self))

    async def astream(
        self, *args, **kwargs
    ) -> AsyncGenerator[Union[Message, StreamData], None]:
        """Normalize legacy calls and delegate execution to the original WorkflowWrapper."""
        args_tuple = self._normalize_astream_args(args, kwargs)
        context = self._build_context(args_tuple.params, args_tuple.context)
        return super().astream(
            query=args_tuple.query,
            params=args_tuple.params,
            workflow_id=args_tuple.workflow_id,
            agent_id=args_tuple.agent_id,
            session_id=args_tuple.session_id,
            context=context,
            workflow_name=args_tuple.workflow_name,
        )

    def set_runtime_context(self, key: str, value: Any = None) -> None:
        if not key:
            return
        if hasattr(self._runtime_context, "set"):
            self._runtime_context.set(key, value)
        else:
            self._runtime_context[key] = value

    async def cleanup(self) -> None:
        """Release workflow execution resources."""
        return None

    def mark_interrupted(self) -> None:
        """Mark current workflow execution as interrupted."""
        setattr(self, "_questioner_interrupted", True)
        self.graph_engine.graph_instance.stop_bpmn_flag = True

    def get_workflow_execute_status(self):
        """Return openjiuwen workflow execution status when available."""
        return None

    def get_workflow_state(self):
        """Return resumable openjiuwen workflow state when checkpointer is wired."""
        return None

    def _prepare_runtime_context(self, params: dict) -> None:
        super()._prepare_runtime_context(params)
        self._runtime_context = _RuntimeContext(self._runtime_context)
        self.graph_engine.graph_instance.runtime_context = self._runtime_context

    def _normalize_astream_args(
        self, args: tuple, kwargs: dict
    ) -> _AstreamArgs:
        data = dict(kwargs)
        query = data.pop("query", None)
        params = data.pop("params", None)

        if args:
            query = args[0] if query is None else query
        if len(args) > 1 and params is None:
            params = args[1]
        if query is None and "inputs" in data:
            query = data.pop("inputs")

        workflow_id = data.pop("workflow_id", None) or self.workflow_id
        workflow_name = data.pop("workflow_name", None) or self.workflow_name
        agent_id = data.pop("agent_id", None) or self.agent_id
        session_id = data.pop("session_id", None) or self.session_id
        context = data.pop("context", None) or self._context

        params = params or self.params or {}
        if not isinstance(params, dict):
            params = {}

        # 将构造时注入的关键参数合并到 params：调用者传入的值优先
        if isinstance(self.params, dict):
            params.setdefault("is_debug", self.params.get("is_debug"))

        return _AstreamArgs(
            query=query,
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id=session_id,
            context=context,
            workflow_name=workflow_name,
        )

    def _build_context(self, params: dict, context=None):
        if context is not None:
            return context

        histories = (
            params.get("conversation_history")
            or params.get("workflow_chat_history")
            or params.get("conversationHistory")
        )
        global_vars = params.get("global_variables", {})
        if not histories and isinstance(global_vars, dict):
            sys_vars = global_vars.get("sys", {})
            if isinstance(sys_vars, dict):
                histories = sys_vars.get("conversationHistory")
        if not histories:
            return self._context

        try:
            from openjiuwen.core.context_engine.context.context import (
                SessionModelContext,
            )
            from openjiuwen.core.context_engine.schema.config import ContextEngineConfig

            model_context = SessionModelContext(
                context_id=f"{self.workflow_id or 'workflow'}_context",
                session_id=self.session_id or "",
                config=ContextEngineConfig(),
            )
            WorkflowMessageConverter.conversation_messages_to_model_context(
                histories, model_context
            )
            return model_context
        except Exception:
            return self._context
