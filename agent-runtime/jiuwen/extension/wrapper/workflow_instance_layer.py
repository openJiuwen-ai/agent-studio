#!/usr/bin/env python
# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""Legacy jiuwen workflow instance surface built on top of WorkflowWrapper."""

from types import SimpleNamespace
from typing import Any, AsyncGenerator, NamedTuple, Union

from jiuwen.common.log.base import logger
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
        workflow_instance=None,
    ):
        super().__init__(node_name_type_map=node_name_type_map)
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.description = description
        self.params = params or {}
        self.agent_id = agent_id or ""
        self.session_id = session_id or ""
        self._context = context
        # 本次请求注册的本地工作流实例（LazyWorkflow shell），执行时优先使用，
        # 避免并发会话经全局注册表取到同一 Workflow 实例造成 session 串扰
        self._workflow_instance = workflow_instance
        self.graph_engine = SimpleNamespace(graph_instance=_CompatGraphInstance(self))

    async def astream(
        self, *args, **kwargs
    ) -> AsyncGenerator[Union[Message, StreamData], None]:
        """Normalize legacy calls and delegate execution to the original WorkflowWrapper."""
        args_tuple = self._normalize_astream_args(args, kwargs)
        # 提取当轮 query，供 _build_context 追加到历史（缺陷①）。
        # 逻辑与 WorkflowWrapper._extract_resume_query 对齐：raw_inputs 优先，
        # 为空时回退到 user_inputs 末条值（覆盖 InteractiveInput 仅有 user_inputs 的场景）。
        current_query = ""
        if hasattr(args_tuple.query, "raw_inputs"):
            current_query = str(args_tuple.query.raw_inputs or "")
            if not current_query and hasattr(args_tuple.query, "user_inputs"):
                user_inputs = args_tuple.query.user_inputs
                if user_inputs:
                    current_query = str(list(user_inputs.values())[-1])
        elif isinstance(args_tuple.query, str):
            current_query = args_tuple.query
        # 用 params 副本传递 _current_query，避免污染调用方原始 params
        # （同一实例复用或并发调用时残留上一次的 _current_query）。
        context_params = args_tuple.params
        if current_query and context_params is not None:
            context_params = {**context_params, "_current_query": current_query}
        context = self._build_context(context_params, args_tuple.context)
        # 当调用方传入预构建 context 时（_build_context 直接返回），
        # 在 async 上下文中追加当轮 query（带去重），否则提问器读不到当轮回复。
        # 注意：此处原地修改调用方传入的 context。当前架构下每次工作流执行
        # 创建独立 context，不存在跨执行共享；若未来引入 context 池化/复用，
        # 需改为拷贝后追加。
        if args_tuple.context is not None and current_query:
            try:
                from openjiuwen.core.foundation.llm import UserMessage
                # 防御性检查：确认 context 具备预期接口
                if not hasattr(context, "get_context_window") or not hasattr(context, "add_messages"):
                    logger.warning(
                        f"Passthrough context for workflow {self.workflow_id} "
                        f"lacks get_context_window/add_messages, skipping query append"
                    )
                else:
                    # 去重：检查 context 末条 user 消息是否已等于当轮 query
                    cw = await context.get_context_window()
                    msgs = cw.get_messages() if cw and hasattr(cw, "get_messages") else []
                    last_user = next(
                        (m for m in reversed(msgs) if getattr(m, "role", None) == "user"),
                        None,
                    )
                    if last_user is None or getattr(last_user, "content", None) != current_query:
                        await context.add_messages([UserMessage(role="user", content=current_query)])
            except (AttributeError, TypeError) as e:
                logger.warning(
                    f"Failed to append current query to passthrough context "
                    f"for workflow {self.workflow_id}: {e}"
                )
        return super().astream(
            query=args_tuple.query,
            params=args_tuple.params,
            workflow_id=args_tuple.workflow_id,
            agent_id=args_tuple.agent_id,
            session_id=args_tuple.session_id,
            context=context,
            workflow_name=args_tuple.workflow_name,
            workflow=self._workflow_instance,
        )

    def set_runtime_context(self, key: str, value: Any = None) -> None:
        if not key:
            return
        if hasattr(self._runtime_context, "set"):
            self._runtime_context.set(key, value)
        else:
            self._runtime_context[key] = value

    async def cleanup(self, preserve_state: bool = False) -> None:
        """Release workflow execution resources.

        Args:
            preserve_state: True 时保留 openjiuwen session 的 checkpoint state
                （供下一轮中断恢复使用）；False 时清理 Redis 中该 session 的
                残留 state，避免下一轮首发执行触发 111121
                （workflow state exists but non-interactive input and cleanup is disabled）。
        """
        if preserve_state or not self.session_id:
            return
        try:
            from openjiuwen.core.session.checkpointer.checkpointer import (
                CheckpointerFactory,
            )

            checkpointer = CheckpointerFactory.get_checkpointer()
            release_workflow = getattr(checkpointer, "release_workflow", None)
            if release_workflow is not None:
                # 只清理本工作流的残留 state。不能用 session 级 release()——
                # 同一会话可能还有其他中断中的工作流（含子工作流 scoped NS），
                # session 级释放会把它们的 checkpoint 一并清掉，导致之后无法
                # 回到中断入口。正常完成/异常路径 post_workflow_execute 已做过
                # 按工作流精确清理，这里只是兜底清残留。
                await release_workflow(self.session_id, self.workflow_id)
                logger.info(
                    f"cleanup released checkpoint state for workflow "
                    f"{self.workflow_id}, session: {self.session_id}"
                )
            else:
                # 非 FastRedisCheckpointer：post_workflow_execute 已按工作流
                # 精确清理，跳过（session 级 release 会误删其他中断工作流）。
                logger.info(
                    f"cleanup skipped per-workflow release for workflow "
                    f"{self.workflow_id}, session: {self.session_id}"
                )
        except Exception as e:
            logger.warning(
                f"cleanup release checkpoint state failed for session "
                f"{self.session_id}: {e}"
            )

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
        # 当调用方传入预构建的 context 时直接返回；当轮 query 的追加
        # 由 astream() 在 async 上下文中完成（add_messages 是 async 方法，
        # 不能在 sync 的 _build_context 中调用）。
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

        # 确保当轮输入在历史末尾（带去重），提问器从 context 读历史，
        # 不追加则 context 不含当轮输入，提问器提取必然失败（缺陷①）。
        query = params.get("_current_query", "")
        if query and isinstance(histories, list):
            last_user = next(
                (m for m in reversed(histories)
                 if isinstance(m, dict) and m.get("role") == "user"),
                None,
            )
            if last_user is None or last_user.get("content") != query:
                histories = list(histories)  # 浅拷贝防改原列表
                histories.append(dict(role="user", content=query))
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
                history_messages=[],  # 必须传空列表，默认 None 会触发 validate_messages 异常
                processors=[],  # 必须传空列表，默认 None 会在 get_context_window 迭代时报错
            )
            # 清理历史消息：去除 intent/agent_id/files/tool_call_id 等多余字段，
            # 保留 converter._extract_msg_fields 实际读取的 role/content/name/enable_history，
            # 避免 "context message is invalid" 异常（一直存在的静默 bug）。
            clean_histories = []
            for msg in histories:
                if isinstance(msg, dict):
                    clean_msg = {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    }
                    # 保留 enable_history 和 name，converter 会读取这两个字段：
                    # enable_history=False 的消息不应注入模型上下文，
                    # name 会传入 ConversationUserMessage/ConversationAssistantMessage。
                    if "enable_history" in msg:
                        clean_msg["enable_history"] = msg["enable_history"]
                    if msg.get("name"):
                        clean_msg["name"] = msg["name"]
                    clean_histories.append(clean_msg)
                else:
                    # 非 dict 消息（如 BaseMessage 对象）跳过：converter 的
                    # _extract_msg_fields 调用 .get() 方法，非 dict 类型会报
                    # AttributeError。实际运行中 get_message_by_intent 返回的
                    # 均为 dict，此处为防御性处理。
                    logger.warning(
                        f"_build_context: skipping non-dict history message "
                        f"(type={type(msg).__name__}) for workflow {self.workflow_id}"
                    )
            WorkflowMessageConverter.conversation_messages_to_model_context(
                clean_histories, model_context
            )
            return model_context
        except Exception as e:
            logger.warning(
                f"_build_context failed for workflow {self.workflow_id}, "
                f"falling back to self._context: {e}"
            )
            return self._context
