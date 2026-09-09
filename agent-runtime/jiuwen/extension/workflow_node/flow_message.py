# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
Workflow message node: template-based user-visible message, aligned with jiuwen FlowMessage.

- invoke: batch render, append to workflow-level ``message_outputs``, return ``{"result": str}``.
  Each record includes scope fields (``host_workflow_id``, ``root_workflow_id``, ``workflow_nesting_depth``,
  ``executable_id``, …) so callers can tell root vs nested sub-workflow messages despite one shared state bucket.
- stream: ``MESSAGE_NODE_STREAM`` frames plus a final ``MESSAGE_NODE_END`` frame;
  does not append ``message_outputs`` on the stream path.
"""

from __future__ import annotations

import datetime
import inspect
from collections.abc import AsyncIterable
from typing import Any, AsyncGenerator, AsyncIterator, Optional, Union

from openjiuwen.core.common.constants.constant import (
    USER_FIELDS,
)
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import BaseError, build_error
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session import END_COMP_TEMPLATE_RENDER_POSITION_TIMEOUT_KEY
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream import OutputSchema, CustomSchema
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.flow.end_comp import (
    TemplateProcessor,
    TemplateUtils,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator

MESSAGE_EVENT_TASK_COMPLETION = "task_completion"
MESSAGE_COMPONENT_TYPE = "message"
JIUWEN_MESSAGE_TYPE = "jiuwen.message"
BJ_TZ = datetime.timezone(datetime.timedelta(hours=8), name="Asia/Beijing")
SPLIT_DELIMITER = "\001"
# Message node streaming protocol (distinct from end node stream)
MESSAGE_NODE_STREAM = "message node stream"  # 保留用于向后兼容
PARTIAL_CONTENT = "partial_content"
MESSAGE_NODE_END = "message_end"
# Workflow-level list of message component outputs (invoke path)
MESSAGE_OUTPUTS_KEY = "message_outputs"


def _workflow_message_scope(session: Session) -> dict[str, Any]:
    """
    Snapshot of execution scope for one Message append (root vs nested sub-workflow).

    Uses the same ``Session`` / ``NodeSession`` surface as the rest of the workflow runtime:
    ``workflow_nesting_depth`` is 0 on the root graph and increases inside ``SubWorkflowSession``;
    ``host_workflow_id`` is ``Session.get_workflow_id()`` (card id of the graph layer running this node);
    ``root_workflow_id`` comes from ``main_workflow_id()`` on the inner session when available.
    """
    inner = session._inner
    scope: dict[str, Any] = {
        "host_workflow_id": session.get_workflow_id(),
        "message_component_id": session.get_component_id(),
        "executable_id": session.get_executable_id(),
    }
    main_id = getattr(inner, "main_workflow_id", None)
    if callable(main_id):
        try:
            scope["root_workflow_id"] = main_id()
        except Exception as e:
            workflow_logger.error(f"Failed to get root_workflow_id: {e}")
    depth_fn = getattr(inner, "workflow_nesting_depth", None)
    if callable(depth_fn):
        try:
            scope["workflow_nesting_depth"] = depth_fn()
        except Exception as e:
            workflow_logger.error(f"Failed to get workflow_nesting_depth: {e}")
    parent_id_fn = getattr(inner, "parent_id", None)
    if callable(parent_id_fn):
        try:
            pid = parent_id_fn()
            if pid:
                scope["parent_executable_prefix"] = pid
        except Exception as e:
            workflow_logger.error(f"Failed to get parent_id: {e}")
    return scope


def _is_async_iterable(value: Any) -> bool:
    if isinstance(value, (AsyncGenerator, AsyncIterable)):
        return True
    return inspect.isasyncgen(value) or hasattr(value, "__aiter__")


def _append_workflow_message_output(session: Session, record: dict) -> None:
    """Persist one message record to workflow-level ``message_outputs`` without extending :class:`Session`."""
    state = session._inner.state()
    updater = getattr(state, "update_and_commit_workflow_state", None)
    if updater is None:
        return
    getter = getattr(state, "get_workflow_state", None)
    current = getter(MESSAGE_OUTPUTS_KEY) if getter else None
    bucket: list = list(current) if isinstance(current, list) else []
    bucket.append(record)
    updater({MESSAGE_OUTPUTS_KEY: bucket})


class MessageConfig(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="Node name.",
    )
    template: str = Field(
        default="",
        description="Message body with placeholders; variables from userFields or flat inputs.",
    )
    output_mode: Optional[str] = Field(
        default=None,
        alias="outputMode",
        description="Optional label echoed in the stream end payload (e.g. 'text').",
    )
    struct_output_template: str = Field(
        default="",
        alias="struct_output_template",
        description="When set with structured mode, rendered after the main body using _NODE_OUTPUT and other keys.",
    )
    enable_struct_message: bool = Field(
        default=False,
        alias="isStructMessage",
        description="If true, stream end frame may include struct_answer and related fields.",
    )
    enable_history: Union[bool, str] = Field(
        default=True,
        description="Whether the message is history-eligible; string 'false' is normalized to False.",
    )
    event: Optional[dict[str, Any]] = Field(
        default=None,
        description='Optional control dict, e.g. {"type": "task_completion"} sets end_interrupt.',
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @field_validator("enable_history", mode="before")
    @classmethod
    def _normalize_enable_history(cls, value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() != "false"
        if value is None:
            return True
        return bool(value)


class Message(WorkflowComponent):
    """
    Renders a template into a workflow-visible message.

    Reads variables from ``inputs[USER_FIELDS]`` when present; otherwise from the top-level inputs dict.

    Same construction style as :class:`End`: pass ``conf`` as ``dict`` or :class:`MessageConfig`.
    Use :meth:`from_fields` for explicit field-by-field construction in code.
    """

    def __init__(self, conf: Union[MessageConfig, dict, None] = None):
        super().__init__()
        self.end_interrupt = False
        if not conf:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="message",
                reason="conf is required",
                workflow="n/a",
            )
        try:
            self._conf = (
                MessageConfig.model_validate(conf)
                if not isinstance(conf, MessageConfig)
                else conf
            )
        except BaseError:
            raise
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="message",
                reason=str(e),
                workflow="n/a",
                cause=e,
            )
        self._processor = TemplateProcessor(self._conf.template)
        ev = self._conf.event
        if ev and ev.get("type", "") == MESSAGE_EVENT_TASK_COMPLETION:
            self.end_interrupt = True

    @classmethod
    def from_fields(
        cls,
        *,
        template: str,
        output_mode: Optional[str] = None,
        struct_output_template: str = "",
        enable_struct_message: bool = False,
        enable_history: Union[bool, str] = True,
        event: Optional[dict[str, Any]] = None,
    ) -> Message:
        """Build from Python field names; equivalent to passing a validated :class:`MessageConfig`."""
        return cls(
            MessageConfig(
                template=template,
                output_mode=output_mode,
                struct_output_template=struct_output_template,
                enable_struct_message=enable_struct_message,
                enable_history=enable_history,
                event=event,
            )
        )

    def component_type(self) -> str:
        return MESSAGE_COMPONENT_TYPE

    @staticmethod
    def _resolve_user_fields(inputs: Input) -> dict[str, Any]:
        if inputs is None:
            return {}
        if isinstance(inputs, dict) and USER_FIELDS in inputs:
            inner = inputs.get(USER_FIELDS)
            return dict(inner) if isinstance(inner, dict) else {}
        return dict(inputs) if isinstance(inputs, dict) else {}

    @staticmethod
    def _now_iso_cn() -> str:
        return datetime.datetime.now(tz=BJ_TZ).isoformat()

    def _message_output_record(self, output: str, session: Session) -> dict[str, Any]:
        record: dict[str, Any] = {
            "node_type": MESSAGE_COMPONENT_TYPE,
            "output": output,
            "time_stamp": self._now_iso_cn(),
        }
        record.update(_workflow_message_scope(session))
        return record

    @staticmethod
    def _extract_stream_piece(value: Any) -> str:
        """Normalize a stream frame (str / LLM chunk dict / plain dict) to display text."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            user_fields = value.get(USER_FIELDS)
            if isinstance(user_fields, dict):
                for key in ("raw_output", "answer", "response", "result", "content"):
                    nested = user_fields.get(key)
                    if nested is not None and not _is_async_iterable(nested):
                        return nested if isinstance(nested, str) else str(nested)
            for key in ("answer", "response", "result", "content", "raw_output"):
                direct = value.get(key)
                if direct is not None and not _is_async_iterable(direct):
                    return direct if isinstance(direct, str) else str(direct)
        return str(value)

    @staticmethod
    def _split_answer_think(answer: str) -> tuple[str, str]:
        parts = answer.split(SPLIT_DELIMITER, 1)
        if len(parts) > 1:
            return parts[0], parts[1]
        return parts[0], ""

    def _format_struct_answer(
        self, origin_output: str, struct_template: str, variables: dict[str, Any]
    ) -> str:
        if not struct_template:
            return ""
        vars_copy = dict(variables)
        vars_copy["_NODE_OUTPUT"] = (
            origin_output.get("answer", "")
            if isinstance(origin_output, dict)
            else origin_output
        )
        try:
            return TemplateUtils.render_template(struct_template, vars_copy)
        except Exception as e:
            workflow_logger.warning(
                "Message struct template render failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                metadata={"error": str(e)},
            )
            return ""

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        workflow_logger.debug(
            "Message component invoke started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_id=session.get_component_id(),
            component_type_str=MESSAGE_COMPONENT_TYPE,
            session_id=session.get_session_id(),
        )
        user = self._resolve_user_fields(inputs)
        timeout = session.get_env(END_COMP_TEMPLATE_RENDER_POSITION_TIMEOUT_KEY)
        if timeout is None:
            timeout = 0.2

        node_id = session.get_component_id()
        node_name = self._conf.name or node_id
        node_type = JIUWEN_MESSAGE_TYPE
        should_interrupt = self.end_interrupt

        # Progressive PARTIAL_CONTENT via render_stream
        # matches old framework FlowMessage.ainvoke() → process_generator_values_of_dict
        chunks: list[str] = []
        frame_count = 0
        try:
            async for frame in self._processor.render_stream(user, session, timeout):
                frame_count += 1
                piece = self._extract_stream_piece(frame.get("data"))
                chunks.append(piece)

                partial_data: dict[str, Any] = {
                    "answer": piece,
                    "result": piece,
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "should_interrupt": should_interrupt,
                }
                await session.write_custom_stream(
                    CustomSchema(
                        type=PARTIAL_CONTENT,
                        index=frame.get("index"),
                        data=partial_data,
                    )
                )
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp=session.get_component_id(),
                ability="invoke",
                reason=str(e),
                workflow=session.get_workflow_id(),
                cause=e,
            )

        final_res = "".join(chunks)

        # MESSAGE_END: same payload structure as stream() end frame
        struct_answer = ""
        if self._conf.enable_struct_message and self._conf.struct_output_template:
            struct_answer = self._format_struct_answer(
                final_res, self._conf.struct_output_template, user
            )
        answer, think = self._split_answer_think(final_res)
        end_payload: dict[str, Any] = {
            "result": final_res,
            "answer": struct_answer
            if struct_answer
            else answer,  # 结构化输出优先作为 answer
            "think": think,
            "enable_history": self._conf.enable_history,
            "output_mode": self._conf.output_mode,
            "origin_answer": answer,  # 原始文本输出
            "is_struct_message": bool(struct_answer),
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "should_interrupt": should_interrupt,
        }
        await session.write_custom_stream(
            CustomSchema(
                type=MESSAGE_NODE_END,
                index=frame_count,
                data=end_payload,
            )
        )

        try:
            _append_workflow_message_output(
                session, self._message_output_record(final_res, session)
            )
        except Exception as e:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp=session.get_component_id(),
                ability="invoke",
                reason=str(e),
                workflow=session.get_workflow_id(),
                cause=e,
            )
        workflow_logger.debug(
            "Message component invoke succeeded",
            event_type=LogEventType.WORKFLOW_COMPONENT_END,
            component_id=session.get_component_id(),
            component_type_str=MESSAGE_COMPONENT_TYPE,
            session_id=session.get_session_id(),
            metadata={"chunk_num": frame_count},
        )
        return {"result": final_res}

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        workflow_logger.debug(
            "Message component stream started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_id=session.get_component_id(),
            component_type_str=MESSAGE_COMPONENT_TYPE,
            session_id=session.get_session_id(),
        )
        if inputs is None:
            inputs = {}
        user = self._resolve_user_fields(inputs)
        timeout = session.get_env(END_COMP_TEMPLATE_RENDER_POSITION_TIMEOUT_KEY)
        if timeout is None:
            timeout = 0.2
        chunks: list[str] = []
        frame_count = 0
        try:
            async for frame in self._processor.render_stream(user, session, timeout):
                frame_count += 1
                piece = self._extract_stream_piece(frame.get("data"))
                chunks.append(piece)
                node_id = session.get_component_id()
                node_name = self._conf.name or node_id
                node_type = JIUWEN_MESSAGE_TYPE
                should_interrupt = self.end_interrupt

                output_schema = OutputSchema(
                    type=MESSAGE_NODE_STREAM,
                    index=frame.get("index"),
                    payload={"result": piece},
                )
                yield output_schema
                # 直接通过 session.write_custom_stream 抛出相同内容的 CustomSchema
                custom_schema = CustomSchema(
                    type=PARTIAL_CONTENT,
                    index=frame.get("index"),
                    data={
                        "answer": piece,
                        "result": piece,
                        "node_id": node_id,
                        "node_name": node_name,
                        "node_type": node_type,
                        "should_interrupt": should_interrupt,
                    },
                )
                await session.write_custom_stream(custom_schema)
            final_res = "".join(chunks)
            struct_answer = ""
            if self._conf.enable_struct_message and self._conf.struct_output_template:
                struct_answer = self._format_struct_answer(
                    final_res, self._conf.struct_output_template, user
                )
            answer, think = self._split_answer_think(final_res)
            node_id = session.get_component_id()
            node_name = self._conf.name or node_id
            node_type = JIUWEN_MESSAGE_TYPE
            should_interrupt = self.end_interrupt

            end_payload: dict[str, Any] = {
                "result": final_res,
                "answer": struct_answer
                if struct_answer
                else answer,  # 结构化输出优先作为 answer
                "think": think,
                "enable_history": self._conf.enable_history,
                "output_mode": self._conf.output_mode,
                "origin_answer": answer,  # 原始文本输出
                "is_struct_message": bool(struct_answer),
                "node_id": node_id,
                "node_name": node_name,
                "node_type": node_type,
                "should_interrupt": should_interrupt,
            }
            output_schema = OutputSchema(
                type=MESSAGE_NODE_END,
                index=frame_count,
                payload=end_payload,
            )
            yield output_schema
            # 直接通过 session.write_custom_stream 抛出相同内容的 CustomSchema
            custom_schema = CustomSchema(
                type=MESSAGE_NODE_END,
                index=frame_count,
                data=end_payload,
            )
            await session.write_custom_stream(custom_schema)
            workflow_logger.debug(
                "Message component stream succeeded",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str=MESSAGE_COMPONENT_TYPE,
                session_id=session.get_session_id(),
                metadata={"chunk_num": frame_count},
            )
        except Exception as e:
            workflow_logger.error(
                "Message component stream failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=session.get_component_id(),
                component_type_str=MESSAGE_COMPONENT_TYPE,
                session_id=session.get_session_id(),
                exception=e,
            )
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp=session.get_component_id(),
                ability="stream",
                reason=str(e),
                workflow=session.get_workflow_id(),
                cause=e,
            )

    async def collect(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """
        流式输入聚合为批量输出。

        旧框架中 Message 在 _pre_process 被豁免生成器预解析（与 End、Card 同组），
        直接接收上游组件（如 LLM）的 AsyncGenerator 输出。
        此方法将流式输入聚合后委托给 invoke() 进行模板渲染。
        """
        # Preserve upstream AsyncGenerators so invoke()/render_stream() can emit
        # progressive PARTIAL_CONTENT like old FlowMessage.process_generator_values_of_dict.
        resolved = await self._resolve_stream_inputs(inputs, preserve_generators=True)
        return await self.invoke(resolved, session, context)

    async def transform(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """
        流式输入转换为流式输出。

        当 Message 同时作为流式接收端和流式发送端时
        （如 LLM → Message → End(isStreamOut)），
        auto_complete_abilities 授予 TRANSFORM 能力。
        此方法将流式输入交给 stream()，由 render_stream 逐帧产出。
        """
        resolved = await self._resolve_stream_inputs(inputs, preserve_generators=True)
        async for output in self.stream(resolved, session, context):
            yield output

    @staticmethod
    async def _resolve_stream_inputs(
        inputs: Input, *, preserve_generators: bool = False
    ) -> dict:
        """
        将 inputs 中的 AsyncGenerator 值解析为最终内容。

        当上游组件（如 LLM）通过流式连接输出时，inputs 中对应的变量值
        是 AsyncGenerator 对象。默认迭代并聚合为最终文本；collect/transform
        路径应 preserve_generators=True，以便 render_stream 边读边发 PARTIAL_CONTENT。
        """

        async def _resolve_value(value: Any) -> Any:
            if _is_async_iterable(value):
                if preserve_generators:
                    return value
                chunks: list[str] = []
                async for frame in value:
                    chunks.append(Message._extract_stream_piece(frame))
                return "".join(chunks)
            if isinstance(value, dict):
                resolved_dict: dict[str, Any] = {}
                for key, nested in value.items():
                    resolved_dict[key] = await _resolve_value(nested)
                return resolved_dict
            return value

        if inputs is None:
            return {}
        if not isinstance(inputs, dict):
            if _is_async_iterable(inputs):
                if preserve_generators:
                    return inputs
                collected: list[str] = []
                async for chunk in inputs:
                    collected.append(Message._extract_stream_piece(chunk))
                return "".join(collected)
            return {}
        resolved: dict[str, Any] = {}
        for key, value in inputs.items():
            resolved[key] = await _resolve_value(value)
        return resolved
