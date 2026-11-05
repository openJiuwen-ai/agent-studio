"""Agent-core model layer with jiuwen-compatible southbound interface."""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import json
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, AsyncIterable, Callable, Iterable

from jiuwen.common.llm_service.language_model.base import InputType, LanguageModelOutput
from jiuwen.extension.wrapper.model_wrapper import ModelWrapper


@dataclass
class ModelCallContext:
    """Normalized model call context passed across the layer boundary."""

    inputs: InputType
    model_id: str
    session_id: str
    agent_id: str = ""
    context: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


class AgentCoreModelLayer:
    """Adapt changed agent-core model inputs to jiuwen's existing model contract.

    The jiuwen controller currently calls model dependencies as:

        await model.ainvoke(inputs, model_id=..., session_id=...)

    Some new integration points pass a single envelope instead:

        await model.ainvoke({
            "inputs": ...,
            "model_id": ...,
            "session_id": ...,
            "agent_id": ...,
        })

    This layer accepts both shapes, keeps the old return type unchanged, and
    forwards optional fields such as agent_id/context without making them required
    for existing controller code. Missing identifiers are passed through as empty
    strings so legacy controller paths keep their original behavior.
    """

    def __init__(
        self,
        runtime: Any | None = None,
        *,
        default_model_id: str = "",
        default_session_id: str = "",
        default_agent_id: str = "",
        default_agent_name: str = "",
    ):
        self.runtime = runtime or ModelWrapper()
        self.default_model_id = default_model_id
        self.default_session_id = default_session_id
        self.default_agent_id = default_agent_id
        self.default_agent_name = default_agent_name

    @property
    def model_name(self) -> str:
        """Return the jiuwen-compatible model name used by legacy callers.

        Older controller/planner modules read ``model.model_name`` for prompt
        template selection and for passing ``model_id`` into mocked model calls.
        The layer's model identity is the normalized openjiuwen model id.
        """
        return self.default_model_id or str(
            getattr(self.runtime, "model_name", "") or ""
        )

    @model_name.setter
    def model_name(self, value: str) -> None:
        """Keep assignment-compatible behavior for tests and legacy code."""
        self.default_model_id = value or ""

    def invoke(
        self,
        inputs: InputType | dict[str, Any],
        model_id: str = "",
        session_id: str = "",
        agent_id: str = "",
        context: Any = None,
        **kwargs: Any,
    ) -> LanguageModelOutput:
        """Synchronously invoke model through the same layer contract."""
        kwargs = {**self._ambient_span_refs(), **kwargs}
        return self._run_async_blocking(
            self.ainvoke(
                inputs,
                model_id=model_id,
                session_id=session_id,
                agent_id=agent_id,
                context=context,
                **kwargs,
            )
        )

    async def ainvoke(
        self,
        inputs: InputType | dict[str, Any],
        model_id: str = "",
        session_id: str = "",
        agent_id: str = "",
        context: Any = None,
        **kwargs: Any,
    ) -> LanguageModelOutput:
        """Invoke model through a jiuwen-compatible async interface."""
        if "agent_name" not in kwargs and self.default_agent_name:
            kwargs = {**kwargs, "agent_name": self.default_agent_name}
        call = self._normalize_call(
            inputs=inputs,
            model_id=model_id,
            session_id=session_id,
            agent_id=agent_id,
            context=context,
            extra=kwargs,
        )
        result = self.runtime.ainvoke(
            call.inputs,
            model_id=call.model_id,
            session_id=call.session_id,
            agent_id=call.agent_id,
            context=call.context,
            **call.extra,
        )
        if inspect.isawaitable(result):
            return await result
        return result

    async def astream(
        self,
        inputs: InputType | dict[str, Any],
        model_id: str = "",
        session_id: str = "",
        agent_id: str = "",
        context: Any = None,
        **kwargs: Any,
    ) -> AsyncIterable[LanguageModelOutput]:
        """Stream model output through a jiuwen-compatible async interface."""
        if "agent_name" not in kwargs and self.default_agent_name:
            kwargs = {**kwargs, "agent_name": self.default_agent_name}
        call = self._normalize_call(
            inputs=inputs,
            model_id=model_id,
            session_id=session_id,
            agent_id=agent_id,
            context=context,
            extra=kwargs,
        )
        async for item in self.runtime.astream(
            call.inputs,
            model_id=call.model_id,
            session_id=call.session_id,
            agent_id=call.agent_id,
            context=call.context,
            **call.extra,
        ):
            yield item

    def stream(
        self,
        inputs: InputType | dict[str, Any],
        model_id: str = "",
        session_id: str = "",
        agent_id: str = "",
        context: Any = None,
        **kwargs: Any,
    ) -> Iterable[LanguageModelOutput]:
        """Synchronously stream model output through the same layer contract."""
        kwargs = {**self._ambient_span_refs(), **kwargs}
        async_iterable = self.astream(
            inputs,
            model_id=model_id,
            session_id=session_id,
            agent_id=agent_id,
            context=context,
            **kwargs,
        )
        return self._iter_async_blocking(async_iterable)

    async def stream_function_call(
        self,
        messages: Any,
        functions: Any,
        runtime_data: dict[str, Any],
    ) -> AsyncIterable[Any]:
        """Stream tool-call output through agent-core and convert it to jiuwen's contract."""
        if hasattr(self.runtime, "astream"):
            async for item in self._stream_function_call_via_astream(
                messages, functions, runtime_data
            ):
                yield item
            return

        async for item in self.runtime.stream_function_call(
            messages, functions, runtime_data
        ):
            yield item

    async def _stream_function_call_via_astream(
        self,
        messages: Any,
        functions: Any,
        runtime_data: dict[str, Any],
    ) -> AsyncIterable[dict[str, Any]]:
        model_id = self._resolve_runtime_value(
            runtime_data, "model_id", "modelId", default_attr="model_id"
        )
        session_id = self._resolve_runtime_value(
            runtime_data,
            "session_id",
            "conversation_id",
            "task_id",
            default_attr="session_id",
        )
        agent_id = self._resolve_runtime_value(runtime_data, "agent_id", "agentId")
        context = runtime_data.get("context")
        streamed_content = ""
        final_content = ""
        usage_metadata = None
        function_call_list: list[dict[str, Any]] = []

        result = self.runtime.astream(
            inputs={"messages": messages, "tools": functions},
            model_id=model_id,
            session_id=session_id,
            agent_id=agent_id,
            context=context,
            runtime_data=runtime_data,
        )
        async for item in result:
            item_content = self._extract_content(item)
            item_function_calls = self._extract_function_calls(item)
            item_usage_metadata = getattr(item, "usage_metadata", None)
            if item_usage_metadata is not None:
                usage_metadata = item_usage_metadata

            if self._is_finish_item(item):
                final_content = item_content
                function_call_list.extend(item_function_calls)
                continue

            if item_content:
                streamed_content += item_content
                yield {"role": "assistant", "content": item_content}

        content = final_content or streamed_content

        llm_output: dict[str, Any] = {
            "role": "assistant",
            "content": content,
            "latency": self._extract_model_latency(usage_metadata),
        }
        if len(function_call_list) == 1:
            llm_output["function_call"] = function_call_list[0]
        elif function_call_list:
            llm_output["function_call_list"] = function_call_list
        yield {"llm_output": llm_output}
        yield {"time_consumption": self._build_time_consumption(usage_metadata)}

    def _normalize_call(
        self,
        *,
        inputs: InputType | dict[str, Any],
        model_id: str,
        session_id: str,
        agent_id: str,
        context: Any,
        extra: dict[str, Any],
    ) -> ModelCallContext:
        """Normalize old positional inputs and new envelope inputs."""
        normalized_inputs = inputs
        normalized_model_id = model_id
        normalized_session_id = session_id
        normalized_agent_id = agent_id
        normalized_context = context
        normalized_extra = dict(extra)

        if isinstance(inputs, dict) and "inputs" in inputs:
            normalized_inputs = inputs["inputs"]
            normalized_model_id = normalized_model_id or inputs.get("model_id", "")
            normalized_session_id = normalized_session_id or inputs.get(
                "session_id", ""
            )
            normalized_agent_id = normalized_agent_id or inputs.get("agent_id", "")
            normalized_context = (
                normalized_context
                if normalized_context is not None
                else inputs.get("context")
            )
            for key, value in inputs.items():
                if key not in {
                    "inputs",
                    "model_id",
                    "session_id",
                    "agent_id",
                    "context",
                }:
                    normalized_extra.setdefault(key, value)

        runtime_data = normalized_extra.get("runtime_data")
        normalized_model_id = self._resolve_identifier(
            normalized_model_id,
            normalized_extra,
            runtime_data,
            normalized_context,
            "model_id",
            "modelId",
            default_value=self.default_model_id
            or getattr(self.runtime, "model_id", ""),
        )
        normalized_session_id = self._resolve_identifier(
            normalized_session_id,
            normalized_extra,
            runtime_data,
            normalized_context,
            "session_id",
            "sessionId",
            "conversation_id",
            "conversationId",
            "task_id",
            "taskId",
            default_value=self.default_session_id
            or getattr(self.runtime, "session_id", ""),
        )
        normalized_agent_id = self._resolve_identifier(
            normalized_agent_id,
            normalized_extra,
            runtime_data,
            normalized_context,
            "agent_id",
            "agentId",
            "id",
            default_value=self.default_agent_id
            or getattr(self.runtime, "agent_id", ""),
        )

        return ModelCallContext(
            inputs=normalized_inputs,
            model_id=normalized_model_id,
            session_id=normalized_session_id,
            agent_id=normalized_agent_id,
            context=normalized_context,
            extra=normalized_extra,
        )

    def _resolve_runtime_value(
        self,
        runtime_data: dict[str, Any] | None,
        *keys: str,
        default_attr: str | None = None,
    ) -> str:
        runtime_data = runtime_data or {}
        for key in keys:
            value = runtime_data.get(key)
            if value:
                return str(value)
        default_from_layer = {
            "model_id": self.default_model_id,
            "session_id": self.default_session_id,
            "agent_id": self.default_agent_id,
        }.get(default_attr or "", "")
        if default_from_layer:
            return str(default_from_layer)
        if default_attr:
            value = getattr(self.runtime, default_attr, "")
            if value:
                return str(value)
        return ""

    @classmethod
    def _resolve_identifier(
        cls,
        explicit_value: str,
        extra: dict[str, Any],
        runtime_data: Any,
        context: Any,
        *keys: str,
        default_value: str = "",
    ) -> str:
        if explicit_value:
            return str(explicit_value)
        for source in (extra, runtime_data, context):
            value = cls._lookup_identifier(source, *keys)
            if value:
                return str(value)
        return str(default_value or "")

    @classmethod
    def _lookup_identifier(cls, source: Any, *keys: str) -> Any:
        if source is None:
            return None
        if isinstance(source, dict):
            for key in keys:
                value = source.get(key)
                if value:
                    return value
            for nested_key in ("agent_config", "metadata", "config"):
                value = cls._lookup_identifier(source.get(nested_key), *keys)
                if value:
                    return value
            return None
        for key in keys:
            value = getattr(source, key, None)
            if value:
                return value
        for nested_key in ("agent_config", "metadata", "config"):
            value = cls._lookup_identifier(getattr(source, nested_key, None), *keys)
            if value:
                return value
        return None

    @staticmethod
    async def _collect_async_iterable(async_iterable: AsyncIterable[Any]) -> list[Any]:
        return [item async for item in async_iterable]

    @staticmethod
    def _ambient_span_refs() -> dict[str, str]:
        """Capture the caller's current OTel span as explicit parent refs.

        嵌入双写桥下 llm span 的父级若依赖环境回退，会被链路中的上下文
        污染破坏（create_agent_session 实证：current span 被换成死根，
        recording=False）。同步入口（桥线程启动前、node executor 上下文
        内）显式捕获 (trace_id, span_id, trace_flags)，随 kwargs 走与
        agent_id 同一条 get_model(identity=) 通道——core 端显式 > 逻辑 >
        环境三级定父。无合法 recording span 时不注入，wire 形态不变。
        """
        try:
            from opentelemetry import trace as _otel_trace

            span_context = _otel_trace.get_current_span().get_span_context()
            if not span_context.is_valid or span_context.span_id == 0:
                return {}
            return {
                "parent_trace_id": f"{span_context.trace_id:032x}",
                "parent_span_id": f"{span_context.span_id:016x}",
                "parent_trace_flags": f"{span_context.trace_flags:02x}",
            }
        except Exception:
            return {}

    @staticmethod
    def _run_in_bridge_thread(fn: Callable[[], None]) -> None:
        """Run fn on a fresh thread carrying the caller's contextvars.

        The sync bridge exists so sync controller code can await async model
        calls while the caller's own event loop is running. A bare thread
        starts with an EMPTY context, so OTel ambient spans, request ids and
        other ContextVar state silently vanish mid-call: spans mis-parent
        onto whatever context the new thread happens to have, traces split.
        copy_context() on the caller side plus Context.run on the thread side
        hands the bridge a private copy of that state — set/reset inside the
        bridge never leaks back to the caller, and a per-call copy can never
        bleed across requests.
        """
        caller_context = contextvars.copy_context()
        thread = threading.Thread(target=caller_context.run, args=(fn,), daemon=True)
        thread.start()
        thread.join()

    @staticmethod
    def _iter_async_blocking(async_iterable: AsyncIterable[Any]) -> Iterable[Any]:
        output_queue: queue.Queue[Any] = queue.Queue()
        sentinel = object()

        async def _consume() -> None:
            async for item in async_iterable:
                output_queue.put(item)

        def _runner() -> None:
            try:
                asyncio.run(_consume())
            except BaseException as exc:
                output_queue.put(exc)
            finally:
                output_queue.put(sentinel)

        AgentCoreModelLayer._run_in_bridge_thread(_runner)
        while True:
            item = output_queue.get()
            if item is sentinel:
                break
            if isinstance(item, BaseException):
                raise item
            yield item

    @staticmethod
    def _run_async_blocking(awaitable: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(awaitable)

        result_holder: dict[str, Any] = {}
        error_holder: dict[str, BaseException] = {}

        def _runner() -> None:
            try:
                result_holder["result"] = asyncio.run(awaitable)
            except BaseException as exc:
                error_holder["error"] = exc

        AgentCoreModelLayer._run_in_bridge_thread(_runner)
        if "error" in error_holder:
            raise error_holder["error"]
        return result_holder.get("result")

    @staticmethod
    def _extract_content(item: Any) -> str:
        if isinstance(item, dict):
            llm_output = item.get("llm_output")
            if isinstance(llm_output, dict):
                return str(llm_output.get("content") or "")
            return str(item.get("content") or "")
        return str(getattr(item, "content", "") or "")

    @classmethod
    def _extract_function_calls(cls, item: Any) -> list[dict[str, Any]]:
        if isinstance(item, dict):
            llm_output = item.get("llm_output")
            if isinstance(llm_output, dict):
                if llm_output.get("function_call"):
                    return [llm_output["function_call"]]
                if llm_output.get("function_call_list"):
                    return list(llm_output["function_call_list"])
            return []

        tool_calls = getattr(item, "tool_calls", None)
        if not tool_calls:
            return []
        if not isinstance(tool_calls, list):
            tool_calls = [tool_calls]
        return [cls._convert_tool_call(tool_call) for tool_call in tool_calls]

    @staticmethod
    def _is_finish_item(item: Any) -> bool:
        usage_metadata = getattr(item, "usage_metadata", None)
        finish_reason = getattr(usage_metadata, "finish_reason", None)
        if finish_reason in {"stop", "function_call"}:
            return True
        tool_calls = getattr(item, "tool_calls", None)
        return bool(tool_calls)

    @staticmethod
    def _extract_model_latency(usage_metadata: Any) -> float:
        if usage_metadata is None:
            return 0.0
        return float(getattr(usage_metadata, "total_latency", 0.0) or 0.0)

    @classmethod
    def _build_time_consumption(cls, usage_metadata: Any) -> dict[str, float | None]:
        model_latency = (
            cls._extract_model_latency(usage_metadata)
            if usage_metadata is not None
            else None
        )
        total_latency = model_latency or 0.0
        wait_latency = None if model_latency is None else 0.0
        return {
            "total_latency": total_latency,
            "model_latency": model_latency,
            "wait_latency": wait_latency,
        }

    @staticmethod
    def _convert_tool_call(tool_call: Any) -> dict[str, Any]:
        arguments = getattr(tool_call, "arguments", None)
        if arguments is None:
            arguments = getattr(tool_call, "args", None)
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments or {}, ensure_ascii=False)
        return {
            "name": getattr(tool_call, "name", ""),
            "arguments": arguments,
            "tool_call_id": getattr(tool_call, "id", ""),
        }
