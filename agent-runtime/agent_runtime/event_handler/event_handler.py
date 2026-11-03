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

from agent_runtime.common.background_task import (
    backgrounding_enabled,
    run_in_background_tracked,
)
from agent_runtime.event_handler.events.base_events import BaseEventsProcessor
from agent_runtime.event_handler.events.agent_events import AgentEventsProcessor
from agent_runtime.event_handler.events.workflow_events import WorkflowEventsProcessor
from agent_runtime.event_handler.events.controller_events import ControllerEventsProcessor
from agent_runtime.event_handler.base.models import NonStreamingResponse
from agent_runtime.event_handler.base.trace import Trace
from agent_runtime.event_handler.base.enums import EventMapping
from agent_runtime.event_handler.base.field_processor import FieldDataProcessor
from agent_runtime.event_handler.base.conversation import ConversationManager

# workflow 流式模式的终态帧原始事件名：workflow_end 由引擎发出（process_workflow_end
# 置位 dialogue_end/end_time），done 由 stream_response R-20 保证唯一且末尾。
# 先到者触发落库租约的前置登记（见 get_handler_body_iterator）。
_WORKFLOW_TERMINAL_EVENTS = frozenset({
    ConversationEvent.WORKFLOW_END.value,
    ConversationEvent.DONE.value,
})


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
        # 网页发布接口路径参数是 short_code，此时从 request.state 获取真实 id
        instance_id = (
            request.path_params.get("agent_id")
            or request.path_params.get("workflow_id")
            or getattr(request.state, "instance_id", "")
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
            # 请求级 enable_history（app_run 写入 request.state），落库补 query 时使用
            enable_history=getattr(request.state, "enable_history", None),
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

    async def _persist_conversation(self, payload=None):
        """Persist conversation history and dialogue count.

        Args:
            payload: (messages, dialogue_end) 登记时刻的同步快照。None 时执行期
                从 trace 现取——仅限 trace 已定稿的路径（非流式、同步回退、
                loop 结束后的兜底登记）；workflow 终态帧前置登记必须传快照，
                任务可能先于响应流结束执行，执行期不得再读可变 trace 字段。
        """
        if not self.conv_manager:
            return
        try:
            if payload is None:
                payload = (
                    FieldDataProcessor.generate_memory_history_messages(self.trace),
                    self.trace.dialogue_end,
                )
            messages, dialogue_end = payload
            await self.conv_manager.update_conversation(
                trace=self.trace,
                messages=messages,
                dialogue_end=dialogue_end,
            )
        except Exception as e:
            workflow_logger.warning(f"Failed to persist conversation history: {e}")

    async def _register_tracked_persist(self) -> bool:
        """登记后台落库任务（租约 HSET 在返回前完成），返回是否已登记。

        载荷在登记时刻同步快照（generate_memory_history_messages 为同步纯函数，
        dialogue_end 由 workflow_end 帧置位）；任务内 trace 仅读 init_trace 写入
        的不可变 ID 字段。登记异常返回 False，由调用方退化到 loop 后兜底重试；
        CancelledError 不捕获——客户端断连应终止响应流（协程由
        run_in_background_tracked 内部关闭，租约残留由读侧 stale 清理自愈）。
        """
        if not self.conv_manager or not backgrounding_enabled():
            return False
        try:
            payload = (
                FieldDataProcessor.generate_memory_history_messages(self.trace),
                self.trace.dialogue_end,
            )
            await run_in_background_tracked(
                self._persist_conversation(payload=payload),
                name=(
                    f"persist-conversation-"
                    f"{getattr(self.trace, 'conversation_id', '')}"
                ),
                track_key=getattr(self.trace, "conversation_id", ""),
            )
            return True
        except Exception as e:
            workflow_logger.warning(
                f"persist registration failed, fallback to post-stream-end: {e}"
            )
            return False

    async def get_handler_body_iterator(self, handler_type: str, body_iterator: AsyncGenerator) -> AsyncGenerator:
        """Process SSE stream from ir_execute, apply event transformation, yield transformed SSE bytes."""
        # 落库任务是否已登记：loop 内前置登记（workflow 终态帧）与 loop 后兜底互斥，防双重登记
        persist_registered = False
        try:
            event_handler = self.get_event_handler(handler_type, self.trace)
            async for data in body_iterator:
                data_dict = self.parse_sse_line(data)
                if data_dict is None:
                    continue

                output_event = event_handler.process_event(data_dict, self.trace)

                # workflow 流式模式的终态帧（workflow_end/done）在 loop 内转发给客户端，
                # 而租约登记若留在 loop 后，存在「客户端已见终态、租约尚不可见」的窗口
                # （stream_response finally 的 unregister + HSET/EXPIRE ≈ 数次 Redis RTT）：
                # 快速重发（如会话排队自动续发）的下一轮 await_pending 会在窗口内放行，
                # 跨轮读改写竞态（脏读/丢消息）回归。故在终态帧转发前前置登记——HSET
                # 先于 yield 完成，恢复「租约严格先于终态对外可见」不变量。触发点在
                # process_event 之后：workflow_end 已置位 dialogue_end/end_time，快照完整。
                # agent/controller 模式上游 done 被各自 processor 拦截、终态由 loop 后
                # 注入（天然先登记后终态），不走此前置登记。
                is_workflow_terminal = (
                    handler_type == IRType.Workflow.value
                    and data_dict.get("event") in _WORKFLOW_TERMINAL_EVENTS
                )
                if is_workflow_terminal and not persist_registered:
                    persist_registered = await self._register_tracked_persist()

                async for chunk in self.generate_output_data(output_event):
                    yield chunk

            # Stream ended: persist conversation history in background.
            # 会话历史落库是整段历史的 Redis 读改写（耗时随轮数增长），
            # 移出终态事件关键路径后台执行，done/end 不再等待它完成；
            # 协程内部自带 try/except，失败仅记日志不影响响应。
            # conv_manager 为空（未 init_trace）时与旧行为一致：直接跳过。
            # track_key 登记在飞任务（进程内注册表 + 跨进程 Redis 租约）：
            # 下一轮请求入口 await_pending 有界等待，恢复「上一轮落库先于
            # 下一轮读取」的单会话顺序性。PERSIST_BACKGROUND_ENABLE=false
            # 时回退同步落库（平台级回滚开关，行为与后台化之前一致）。
            # workflow 模式通常已在 loop 内终态帧前前置登记，此处仅兜底
            # 未触发前置登记的流（无终态帧、前置登记失败、回滚开关关闭）。
            if self.conv_manager and not persist_registered:
                if backgrounding_enabled():
                    await self._register_tracked_persist()
                else:
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

        # 对齐旧 Java runAgent：始终输出 end_time。事件流未显式设置时兜底取当前时间。
        if self.trace.end_time is None:
            self.trace.end_time = int(time.time() * 1000)

        non_stream_output = {}
        trace_attr = vars(self.trace)
        for key, value in trace_attr.items():
            if value is not None:
                non_stream_output[key] = value
        # 对齐旧 Java WorkflowRunRsp @Builder.Default：outputs/node_info/events
        # 即使未被事件流填充也要输出 {}、[]，避免被 exclude_none 丢弃导致字段缺失。
        non_stream_output.setdefault("outputs", {})
        non_stream_output.setdefault("node_info", [])
        non_stream_output.setdefault("events", [])
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
