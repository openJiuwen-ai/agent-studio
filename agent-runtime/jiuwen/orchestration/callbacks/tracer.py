#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import logging
from typing import Optional

from jiuwen.common.log.base import logger
from jiuwen.insight.handlers.insight_callback_handler import Insight4CallbackHandler
from jiuwen.orchestration.callbacks.manager import CallbackHandlerManager
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_EXECUTE_DEBUG_INFO,
    EXECUTION_ID,
    PARENT_INVOKE_ID,
    WORKFLOW_X_INVOKE_MODE,
)
from jiuwen.orchestration.flow.state import TraceState


class Tracer:
    def __init__(self, context, trace_state: TraceState = None):
        # 记录上一个span
        self._active_spans = []
        # workflow中断恢复之后该列表为空
        self._context = context
        self.loop_span_dict = {}
        runtime_debug_info = self._context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {})
        self._trace_id = runtime_debug_info.get(EXECUTION_ID, "")
        self.last_span_id = runtime_debug_info.get(PARENT_INVOKE_ID, "")
        if trace_state:
            self._load_state(trace_state)

    @property
    def trace_id(self) -> str:
        """
        获取trace_id
        """
        return self._trace_id

    def get_state(self) -> TraceState:
        """get trace state"""
        cur_span: Optional[Span] = self.get_cur_span()
        if cur_span:
            self._context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {}).update(
                dict(invoke_id=cur_span.span_id, parent_invoke_id=cur_span.parent_id)
            )
        req_invoke_mode = self._context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {}).get(
            WORKFLOW_X_INVOKE_MODE, ""
        )
        handler: Insight4CallbackHandler = CallbackHandlerManager().get_handler(
            Insight4CallbackHandler
        )
        # 只有子图的提问器数据会被中断恢复
        if handler and req_invoke_mode == "debug":
            if cur_span and handler.invoke_map.get(cur_span.span_id, {}):
                return TraceState(
                    invoke_id=cur_span.span_id,
                    insight_invoke_map=handler.invoke_map.get(cur_span.span_id, {})
                    if cur_span and handler
                    else {},
                    insight_on_invoke_map=handler.on_invoke_map.get(
                        cur_span.span_id, []
                    )
                    if cur_span and handler
                    else [],
                    insight_invoke_maps=handler.invoke_map
                    if cur_span and handler
                    else {},
                    insight_on_invoke_maps=handler.on_invoke_map
                    if cur_span and handler
                    else {},
                    loop_span_dict=self.loop_span_dict,
                )

        return TraceState(
            invoke_id="",
            insight_invoke_map={},
            insight_on_invoke_map={},
            insight_invoke_maps={},
            insight_on_invoke_maps={},
            loop_span_dict=self.loop_span_dict,
        )

    def start_span(self, span_id=""):
        """

        Args:
        Returns:

        """
        span = Span(
            parent_id=self.last_span_id, trace_id=self._trace_id, span_id=span_id
        )
        self.last_span_id = span.span_id
        self._active_spans.append(span)
        return span

    def get_cur_span(self):
        """
        Returns the latest span.
        """
        if self._active_spans:
            return self._active_spans[-1]
        return None

    def finish_span(self, span):
        """

        Args:
            span:

        Returns:

        """
        span.finish()
        self._context.remove(span)

    def inject_context(self, span):
        """

        Args:
            span:

        Returns:

        """
        self._context.set({"span_id": span.span_id, "parent_id": span.parent_id})

    def extract_context(self, span):
        """

        Args:
            span:

        Returns:

        """
        self._context.get(span.span_id)

    def report(self):
        """

        Returns:

        """
        # 诊断性 span dump，仅 DEBUG 级别启用时构造
        if not logger.isEnabledFor(logging.DEBUG):
            return
        for span in self._active_spans:
            logger.debug("Span %s (%s):", span.span_id, span.operation_name)
            logger.debug("  Parent ID: %s", span.parent_id)
            logger.debug("  Start time: %s", span.start_time)
            logger.debug("  End time: %s", span.end_time)
            for log in span.logs:
                logger.debug("  Log: %s", log, simple_log="Log")

    def _load_state(self, trace_state: TraceState):
        handler: Insight4CallbackHandler = CallbackHandlerManager().get_handler(
            Insight4CallbackHandler
        )
        req_invoke_mode = self._context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {}).get(
            WORKFLOW_X_INVOKE_MODE, ""
        )
        if not handler or req_invoke_mode != "debug":
            return
        invoke_id = trace_state.invoke_id
        if not invoke_id:
            return
        handler.invoke_map[invoke_id] = trace_state.insight_invoke_map
        handler.on_invoke_map[invoke_id] = trace_state.insight_on_invoke_map
        for _, span in trace_state.loop_span_dict.items():
            handler.invoke_map[span.span_id] = trace_state.insight_invoke_maps.get(
                span.span_id
            )
            on_invoke_map = trace_state.insight_on_invoke_maps.get(span.span_id)
            if on_invoke_map:
                handler.on_invoke_map[span.span_id] = on_invoke_map
