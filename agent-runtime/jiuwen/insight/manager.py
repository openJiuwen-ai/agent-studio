#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""handler send trace log to Insight backend"""

import asyncio
import uuid
import logging
from typing import Any, Dict, List, Type, Optional, Union

from jiuwen.common.log.base import logger
from jiuwen.insight.handlers.base import (
    PromptTraceHandler,
    LLMTraceHandler,
    PluginTraceHandler,
    ChainTraceHandler,
    RetrieverTraceHandler,
    EvaluatorTraceHandler,
)
from jiuwen.insight.handlers.data import BaseDataHandler

Trace = Optional[Union[List[BaseDataHandler], "TraceManager"]]


async def _trace_event(
    trace_handlers: List[BaseDataHandler], event_name: str, *args: Any, **kwargs: Any
):
    """Invoke trace event"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("insight trace type:%s, invoke_id:%s", event_name, kwargs.get("invoke_id"))
    for trace_handler in trace_handlers:
        handler = getattr(trace_handler, event_name)
        result = handler(*args, **kwargs)
        if asyncio.iscoroutine(result):
            await result


class TraceManager(
    PromptTraceHandler,
    LLMTraceHandler,
    PluginTraceHandler,
    ChainTraceHandler,
    RetrieverTraceHandler,
    EvaluatorTraceHandler,
):
    """Tracer manager that manage trace handlers"""

    def __init__(
        self,
        trace_handlers: Optional[List[BaseDataHandler]] = None,
        parent_invoke_id: Optional[str] = None,
        instance_info: Optional[dict] = None,
        openjiuwen_tracer=None,
        **kwargs,
    ) -> None:
        """Initialize"""
        self.trace_handlers = trace_handlers or []
        self.invoke_id = None
        self.parent_invoke_id = parent_invoke_id
        self.instance_info = instance_info
        self.extra = kwargs

        # openjiuwen Tracer 双写
        self._oj_tracer = openjiuwen_tracer
        self._oj_span_map: Dict[str, Any] = {}  # invoke_id -> TraceAgentSpan
        self._oj_root_span = None
        if openjiuwen_tracer is not None:
            self._oj_init_root_span()

    # ── openjiuwen 双写内部方法 ─────────────────────────────

    def _oj_init_root_span(self):
        """初始化 openjiuwen agent 根 span。"""
        from openjiuwen.core.session.tracer.span import SpanManager
        span_manager = self._oj_tracer.tracer_agent_span_manager
        self._oj_root_span = span_manager.create_agent_span(span_manager.last_span)
        span_manager.update_span(self._oj_root_span, {
            "invoke_type": "agent",
            "name": "agent",
        })

    def _oj_get_or_create_span(self, invoke_id: str, parent_invoke_id: Optional[str] = None):
        """获取已有 openjiuwen span 或创建新 span。"""
        if invoke_id in self._oj_span_map:
            return self._oj_span_map[invoke_id]

        span_manager = self._oj_tracer.tracer_agent_span_manager

        # 查找 parent span
        parent_span = None
        if parent_invoke_id and parent_invoke_id in self._oj_span_map:
            parent_span = self._oj_span_map[parent_invoke_id]

        # 如果没有显式 parent，使用 agent 根 span
        if parent_span is None:
            parent_span = self._oj_root_span

        span = span_manager.create_agent_span(parent_span)

        # 对齐 invoke_id，使 TraceManager 和 openjiuwen 的 id 一致
        original_id = span.invoke_id
        span_manager.update_span(span, {"invoke_id": invoke_id})

        # 修正 parent 的 child_invokes_id：将原始 UUID 替换为对齐后的 invoke_id
        if parent_span and parent_span.child_invokes_id:
            child_list = parent_span.child_invokes_id
            if original_id in child_list:
                idx = child_list.index(original_id)
                child_list[idx] = invoke_id
                span_manager.refresh_span_record(
                    parent_span.invoke_id,
                    {parent_span.invoke_id: parent_span},
                )

        self._oj_span_map[invoke_id] = span
        return span

    def _oj_cleanup_span(self, invoke_id: str):
        """end/error 后清理 span 引用。"""
        self._oj_span_map.pop(invoke_id, None)

    async def _oj_trigger(self, event_name: str, **kwargs):
        """异步触发 openjiuwen tracer 事件。"""
        try:
            await self._oj_tracer.trigger("tracer_agent", event_name, **kwargs)
        except Exception as e:
            logger.warning(f"OpenJiuWenTracer dual-write trigger failed: {e}")

    async def _oj_on_start(self, event_name: str, invoke_id: str, parent_invoke_id: Optional[str],
                     inputs: Any, instance_info: Optional[dict], **kwargs):
        """openjiuwen 双写：start 事件通用逻辑。"""
        if self._oj_tracer is None:
            return
        span = self._oj_get_or_create_span(invoke_id, parent_invoke_id)
        # TraceAgentHandler._update_start_trace_data 要求 instance_info 含 class_name，
        # 缺失时提供默认值避免 KeyError
        safe_instance_info = instance_info or {}
        if "class_name" not in safe_instance_info:
            safe_instance_info = {**safe_instance_info, "class_name": "unknown"}
        # 将 inputs 包装为 {"inputs": 原始inputs, "params": kwargs相关信息}
        formatted_inputs = {"inputs": inputs}
        if kwargs:
            formatted_inputs["params"] = kwargs
        await self._oj_trigger(
            event_name, span=span,
            inputs=formatted_inputs,
            instance_info=safe_instance_info, **kwargs
        )

    async def _oj_on_end(self, event_name: str, invoke_id: str, outputs: Any, **kwargs):
        """openjiuwen 双写：end 事件通用逻辑。"""
        if self._oj_tracer is None:
            return
        span = self._oj_span_map.get(invoke_id)
        if span:
            await self._oj_trigger(
                event_name, span=span,
                outputs=outputs, **kwargs
            )
            self._oj_cleanup_span(invoke_id)

    async def _oj_on_error(self, event_name: str, invoke_id: str, error: BaseException, **kwargs):
        """openjiuwen 双写：error 事件通用逻辑。"""
        if self._oj_tracer is None:
            return
        span = self._oj_span_map.get(invoke_id)
        if span:
            await self._oj_trigger(event_name, span=span, error=error, **kwargs)
            self._oj_cleanup_span(invoke_id)

    # ── 公共方法 ────────────────────────────────────────────

    @classmethod
    def generate_manager(
        cls,
        trace_handlers: Optional["TraceManager"] = None,
        instance_info: Optional[dict] = None,
        session=None,
    ) -> "TraceManager":
        """Return a trace handlers manager"""
        return _generate_manager(cls, trace_handlers, instance_info, session)

    def add_trace_handler(self, trace_handler: BaseDataHandler) -> None:
        """Add a trace handler to the manager"""
        trace_handlers_type = [
            type(inheritable_trace_handler)
            for inheritable_trace_handler in self.trace_handlers
        ]
        if type(trace_handler) not in trace_handlers_type:
            self.trace_handlers.append(trace_handler)

    def remove_trace_handler(self, trace_handler: BaseDataHandler) -> None:
        """Remove a trace handler from the manager"""
        self.trace_handlers.remove(trace_handler)

    # ── Prompt ──────────────────────────────────────────────

    async def on_prompt_start(self, inputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when prompt start"""
        self.get_run_id()
        await _trace_event(
            self.trace_handlers,
            "on_prompt_start",
            self.instance_info,
            inputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **self.extra,
            **kwargs,
        )
        await self._oj_on_start(
            "on_prompt_start", self.invoke_id, self.parent_invoke_id,
            inputs, self.instance_info,
        )

    async def on_prompt_end(self, outputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when prompt end"""
        await _trace_event(
            self.trace_handlers,
            "on_prompt_end",
            outputs,
            invoke_id=self.invoke_id,
            partent_run_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_end("on_prompt_end", self.invoke_id, outputs)

    async def on_prompt_error(self, error: BaseException, *args: Any, **kwargs: Any) -> None:
        """Invoke when prompt error"""
        await _trace_event(
            self.trace_handlers,
            "on_prompt_error",
            error,
            invoke_id=self.invoke_id,
            partent_run_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_error("on_prompt_error", self.invoke_id, error)

    # ── LLM ────────────────────────────────────────────────

    async def on_llm_start(self, inputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when llm start"""
        self.get_run_id()
        await _trace_event(
            self.trace_handlers,
            "on_llm_start",
            self.instance_info,
            inputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **self.extra,
            **kwargs,
        )
        await self._oj_on_start(
            "on_llm_start", self.invoke_id, self.parent_invoke_id,
            inputs, self.instance_info,
        )

    async def on_llm_end(self, outputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when llm end"""
        await _trace_event(
            self.trace_handlers,
            "on_llm_end",
            outputs,
            invoke_id=self.invoke_id,
            partent_run_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_end("on_llm_end", self.invoke_id, outputs)

    async def on_llm_error(self, error: BaseException, *args: Any, **kwargs: Any) -> None:
        """Invoke when llm error"""
        await _trace_event(
            self.trace_handlers,
            "on_llm_error",
            error,
            invoke_id=self.invoke_id,
            partent_run_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_error("on_llm_error", self.invoke_id, error)

    # ── Chain ──────────────────────────────────────────────

    async def on_chain_start(self, inputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when chain start"""
        self.get_run_id()
        await _trace_event(
            self.trace_handlers,
            "on_chain_start",
            self.instance_info,
            inputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **self.extra,
            **kwargs,
        )
        await self._oj_on_start(
            "on_chain_start", self.invoke_id, self.parent_invoke_id,
            inputs, self.instance_info,
        )

    async def on_chain_end(self, outputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when chain end"""
        await _trace_event(
            self.trace_handlers,
            "on_chain_end",
            outputs,
            invoke_id=self.invoke_id,
            partent_run_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_end("on_chain_end", self.invoke_id, outputs)

    async def on_chain_error(self, error: BaseException, *args: Any, **kwargs: Any) -> None:
        """Invoke when chain error"""
        await _trace_event(
            self.trace_handlers,
            "on_chain_error",
            error,
            invoke_id=self.invoke_id,
            partent_run_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_error("on_chain_error", self.invoke_id, error)

    # ── Plugin ─────────────────────────────────────────────

    async def on_plugin_start(self, inputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when tool start"""
        self.get_run_id()
        await _trace_event(
            self.trace_handlers,
            "on_plugin_start",
            self.instance_info,
            inputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **self.extra,
            **kwargs,
        )
        await self._oj_on_start(
            "on_plugin_start", self.invoke_id, self.parent_invoke_id,
            inputs, self.instance_info,
        )

    async def on_plugin_end(self, outputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when tool end"""
        await _trace_event(
            self.trace_handlers,
            "on_plugin_end",
            outputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_end("on_plugin_end", self.invoke_id, outputs)

    async def on_plugin_error(self, error: BaseException, *args: Any, **kwargs: Any) -> None:
        """Invoke when tool error"""
        await _trace_event(
            self.trace_handlers,
            "on_plugin_error",
            error,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_error("on_plugin_error", self.invoke_id, error)

    # ── Retriever ──────────────────────────────────────────

    async def on_retriever_start(self, inputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when retriever start"""
        self.get_run_id()
        await _trace_event(
            self.trace_handlers,
            "on_retriever_start",
            self.instance_info,
            inputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **self.extra,
            **kwargs,
        )
        await self._oj_on_start(
            "on_retriever_start", self.invoke_id, self.parent_invoke_id,
            inputs, self.instance_info,
        )

    async def on_retriever_end(self, outputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when retriever end"""
        await _trace_event(
            self.trace_handlers,
            "on_retriever_end",
            outputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_end("on_retriever_end", self.invoke_id, outputs)

    async def on_retriever_error(
        self, error: BaseException, *args: Any, **kwargs: Any
    ) -> None:
        """Invoke when retriever error"""
        await _trace_event(
            self.trace_handlers,
            "on_retriever_error",
            error,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_error("on_retriever_error", self.invoke_id, error)

    # ── Evaluator ──────────────────────────────────────────

    async def on_evaluator_start(self, inputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when evaluator start"""
        self.get_run_id()
        await _trace_event(
            self.trace_handlers,
            "on_evaluator_start",
            self.instance_info,
            inputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **self.extra,
            **kwargs,
        )
        await self._oj_on_start(
            "on_evaluator_start", self.invoke_id, self.parent_invoke_id,
            inputs, self.instance_info,
        )

    async def on_evaluator_end(self, outputs: Any, *args: Any, **kwargs: Any) -> None:
        """Invoke when evaluator end"""
        await _trace_event(
            self.trace_handlers,
            "on_evaluator_end",
            outputs,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_end("on_evaluator_end", self.invoke_id, outputs)

    async def on_evaluator_error(
        self, error: BaseException, *args: Any, **kwargs: Any
    ) -> None:
        """Invoke when evaluator error"""
        await _trace_event(
            self.trace_handlers,
            "on_evaluator_error",
            error,
            invoke_id=self.invoke_id,
            parent_invoke_id=self.parent_invoke_id,
            **kwargs,
        )
        await self._oj_on_error("on_evaluator_error", self.invoke_id, error)

    # ── 工具方法 ────────────────────────────────────────────

    def get_run_id(self) -> None:
        """
        获取运行ID的方法。
        如果当前的invoke_id为None，则生成一个新的UUID作为invoke_id。

        :return: None
        """
        if self.invoke_id is None:
            self.invoke_id = str(uuid.uuid4())


def remove_duplicate_trace_handlers(
    trace_handlers: Optional[List[Trace]],
) -> List[Trace]:
    """Remove duplicate trace handlers which have the same type."""
    if trace_handlers is None:
        return []

    processed_trace_handlers = []
    processed_trace_handlers_type = []
    for trace_handler in trace_handlers:
        if type(trace_handler) not in processed_trace_handlers_type:
            processed_trace_handlers_type.append(type(trace_handler))
            processed_trace_handlers.append(trace_handler)

    return processed_trace_handlers


def _generate_manager(
    trace_manager_cls: Type[TraceManager],
    trace_handlers: Trace = None,
    instance_info: Optional[dict] = None,
    session=None,
) -> TraceManager:
    """Return a trace manager"""
    trace_manager = trace_manager_cls(
        trace_handlers=[], instance_info=instance_info,
        openjiuwen_tracer=session._inner.tracer() if session else None,
    )
    if trace_handlers:
        if isinstance(trace_handlers, list) or trace_handlers is None:
            trace_handlers_ = remove_duplicate_trace_handlers(trace_handlers)
            trace_manager.trace_handlers = trace_handlers_.copy()
        else:
            trace_manager.trace_handlers = trace_handlers.trace_handlers.copy()
            trace_manager.parent_invoke_id = trace_handlers.parent_invoke_id
            trace_manager.extra = trace_handlers.extra
            # 继承 openjiuwen 双写状态
            if trace_handlers._oj_tracer is not None and trace_manager._oj_tracer is None:
                trace_manager._oj_tracer = trace_handlers._oj_tracer
                trace_manager._oj_span_map = trace_handlers._oj_span_map
                trace_manager._oj_root_span = trace_handlers._oj_root_span
    return trace_manager


def get_child_manager(parent_manager: TraceManager, name: str = None) -> TraceManager:
    """Get a child trace handlers manager"""
    manager = TraceManager(
        trace_handlers=[], parent_invoke_id=parent_manager.invoke_id, name=name
    )
    for trace_handler in parent_manager.trace_handlers:
        manager.add_trace_handler(trace_handler)

    # 继承 openjiuwen 双写状态：共享 tracer、span_map、root_span
    manager._oj_tracer = parent_manager._oj_tracer
    manager._oj_span_map = parent_manager._oj_span_map
    manager._oj_root_span = parent_manager._oj_root_span

    return manager
