# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""EventHandler — 流式数据封装处理主入口.

Key adaptations for open-source:
- Input: StreamingResponse.body_iterator from ir_execute (SSE bytes), not Java execution_response
- Handler type determined from IR mode or endpoint path
"""

import json
import time
import traceback
from typing import Dict, Type, AsyncGenerator, Any, Optional

from pydantic import BaseModel
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse
from jiuwen.serve.controllers.execution.enum import PlanModeType, IRType, ConversationEvent
from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.event_handler.events.base_events import BaseEventsProcessor
from agent_runtime.event_handler.events.agent_events import AgentEventsProcessor
from agent_runtime.event_handler.events.workflow_events import WorkflowEventsProcessor
from agent_runtime.event_handler.events.controller_events import ControllerEventsProcessor
from agent_runtime.event_handler.base.models import NonStreamingResponse
from agent_runtime.event_handler.base.trace import Trace
from agent_runtime.event_handler.base.enums import EventMapping
from agent_runtime.event_handler.base.field_processor import FieldDataProcessor
from agent_runtime.event_handler.base.conversation import ConversationManager


class EventHandler:
    """事件结果封装类，_handler_map为处理的agent类型映射."""

    _handler_map: Dict[str, Type[BaseEventsProcessor]] = {
        PlanModeType.ReAct.value: AgentEventsProcessor,
        PlanModeType.PlanExecute.value: AgentEventsProcessor,
        PlanModeType.Controller.value: ControllerEventsProcessor,
        IRType.Workflow.value: WorkflowEventsProcessor,
    }

    def __init__(self):
        self.trace = None
        self.conv_manager = None

    def get_event_handler(self, handler_type: str, trace: Trace) -> BaseEventsProcessor:
        handler_class = self._handler_map.get(handler_type)
        if not handler_class:
            workflow_logger.error(
                f"Unsupported handler type: {handler_type}, "
                f"event type should be ReAct, Controller, Workflow or PlanExecute."
            )
            trace.error_code = 121007
            trace.error_message = (
                f"error type: {handler_type}, "
                f"agent type should be ReAct, Controller, Workflow or PlanExecute."
            )
            raise ValueError(
                f"Unsupported handler type: {handler_type}, "
                f"should be ReAct, Controller, Workflow or PlanExecute."
            )
        return handler_class()

    def init_trace(
        self,
        handler_type: str,
        request: Request,
        ir_path: str,
        query: str = "",
    ):
        """Initialize trace context from request and IR path."""
        conversation_id = request.path_params.get("conversation_id", "")
        user_id = getattr(request.state, "user_id", "")
        version_id = getattr(request.state, "version_id", "")
        is_debug = request.headers.get("x-invoke-mode", "").lower() == "debug"
        language = request.headers.get("x-language", "en-us")
        # instance_id 使用 agent_id 或 workflow_id（与读取路径一致），不从 IR 路径文件名提取
        instance_id = (
            request.path_params.get("agent_id")
            or request.path_params.get("workflow_id")
        )
        if not instance_id:
            raise ValueError(
                "Missing required path param: agent_id or workflow_id"
            )

        self.trace = Trace(
            handler_type=handler_type,
            conversation_id=conversation_id,
            instance_id=instance_id,
            user_id=user_id,
            version_id=version_id,
            is_debug=is_debug,
            language=language,
            query=query,
        )
        self.conv_manager = ConversationManager()

    @staticmethod
    def parse_sse_line(data: bytes) -> Optional[dict]:
        """Parse a single SSE data line into a dict. Returns None if not a valid data line."""
        data_str = data.decode("utf-8") if isinstance(data, bytes) else str(data)
        if not data_str.startswith("data: "):
            return None
        payload = data_str.split("data: ", 1)[1].strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def serialize_sse(item: dict) -> bytes:
        """Serialize a dict to SSE data line."""
        return f"data: {json.dumps(item, ensure_ascii=False)}\n\n".encode("utf-8")

    @classmethod
    async def generate_output_data(cls, output_event: Any) -> AsyncGenerator:
        """Convert processor output to SSE bytes."""
        if output_event is None:
            return
        # Normalize to list of dicts
        if isinstance(output_event, BaseModel):
            items = [output_event.model_dump(by_alias=True, exclude_none=True)]
        elif isinstance(output_event, list):
            items = output_event
        elif isinstance(output_event, dict):
            items = [output_event]
        else:
            return
        for item in items:
            yield cls.serialize_sse(item)

    async def _persist_conversation(self):
        """Persist conversation history and dialogue count."""
        if not self.conv_manager:
            return
        try:
            history_messages = FieldDataProcessor.generate_memory_history_messages(self.trace)
            await self.conv_manager.update_conversation(
                trace=self.trace,
                messages=history_messages,
                dialogue_end=self.trace.dialogue_end,
            )
        except Exception as e:
            workflow_logger.warning(f"Failed to persist conversation history: {e}")

    async def get_handler_body_iterator(self, handler_type: str, body_iterator: AsyncGenerator) -> AsyncGenerator:
        """Process SSE stream from ir_execute, apply event transformation, yield transformed SSE bytes."""
        try:
            event_handler = self.get_event_handler(handler_type, self.trace)
            async for data in body_iterator:
                data_dict = self.parse_sse_line(data)
                if data_dict is None:
                    continue

                output_event = event_handler.process_event(data_dict, self.trace)
                async for chunk in self.generate_output_data(output_event):
                    yield chunk

            # Stream ended: persist conversation history
            await self._persist_conversation()

            # Agent mode: inject done event
            if handler_type in (PlanModeType.ReAct.value, PlanModeType.PlanExecute.value):
                yield self.serialize_sse({
                    "event": ConversationEvent.DONE.value,
                    "createdTime": self.trace.end_time or int(time.time() * 1000),
                })

            # Controller mode: inject end event
            if handler_type == PlanModeType.Controller.value:
                yield self.serialize_sse({
                    "event": EventMapping.DONE.value,
                    "createdTime": self.trace.end_time or int(time.time() * 1000),
                })

        except Exception as e:
            workflow_logger.error("encapsulate stream response failed.")
            workflow_logger.error("".join(traceback.format_exception(e)))
            error_event = FieldDataProcessor.generate_error_event_field(self.trace)
            yield self.serialize_sse(error_event.model_dump(by_alias=True, exclude_none=True))

    async def get_stream_result(self, handler_type: str, body_iterator: AsyncGenerator) -> StreamingResponse:
        transformed_iterator = self.get_handler_body_iterator(
            handler_type=handler_type,
            body_iterator=body_iterator,
        )
        return StreamingResponse(content=transformed_iterator, media_type="text/event-stream")

    async def get_non_stream_result(self, handler_type: str, body_iterator: AsyncGenerator) -> Any:
        """Consume stream fully, aggregate into NonStreamingResponse."""
        try:
            event_handler = self.get_event_handler(handler_type, self.trace)
            async for data in body_iterator:
                data_dict = self.parse_sse_line(data)
                if data_dict is None:
                    continue
                output_event = event_handler.process_event(data_dict, self.trace)
                async for _ in self.generate_output_data(output_event):
                    continue
            await self._persist_conversation()
        except Exception as e:
            workflow_logger.error("encapsulate non stream response failed.")
            workflow_logger.error("".join(traceback.format_exception(e)))

        non_stream_output = {}
        trace_attr = vars(self.trace)
        for key, value in trace_attr.items():
            if value is not None:
                non_stream_output[key] = value
        response = NonStreamingResponse.model_construct(**non_stream_output)
        return JSONResponse(content=response.model_dump(exclude_none=True, by_alias=True))

    @classmethod
    async def encapsulate_stream_response(
        cls,
        response: StreamingResponse,
        handler_type: str,
        request: Request,
        ir_path: str,
        query: str = "",
    ) -> StreamingResponse:
        """Unified entry point for stream response encapsulation."""
        handler = cls()
        handler.init_trace(
            handler_type=handler_type,
            request=request,
            ir_path=ir_path,
            query=query,
        )
        return await handler.get_stream_result(
            handler_type=handler_type,
            body_iterator=response.body_iterator,
        )

    @classmethod
    async def encapsulate_non_stream_response(
        cls,
        response: StreamingResponse,
        handler_type: str,
        request: Request,
        ir_path: str,
        query: str = "",
    ) -> Any:
        """Unified entry point for non-stream response encapsulation."""
        handler = cls()
        handler.init_trace(
            handler_type=handler_type,
            request=request,
            ir_path=ir_path,
            query=query,
        )
        return await handler.get_non_stream_result(
            handler_type=handler_type,
            body_iterator=response.body_iterator,
        )
