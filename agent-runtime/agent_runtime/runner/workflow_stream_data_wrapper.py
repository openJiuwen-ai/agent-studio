#!/usr/bin env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Chunk 封装器 - 将 workflow.stream 产生的单个 chunk 转换为统一的 StreamData 格式
"""
import contextvars
import datetime
import logging
import time
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)

from agent_runtime.common.logging_context import mask_debug_data, find_secret_env_field_names
from agent_runtime.common.session_state_access import get_state_info
from agent_runtime.context.request_context import _request_ctx
from openjiuwen.core.common.constants.constant import INTERACTION
from openjiuwen.core.common.logging import performance_logger
from openjiuwen.core.session.stream.base import (
    OutputSchema,
    CustomSchema,
    TraceSchema,
)

# 映射：调试事件返回 → service
_DEBUG_EVENT_RETURN_TO_SERVICE: dict[str, str] = {
    "FlowQA": "EI.qa",
    "LLMChain": "LLM",
    "SubWorkflow": "jiuwen.workflowComposite",
    "BranchComponent": "Branch",
    "_RoutedIntentDetection": "IntentDetection",
    "LoopComponent": "jiuwen.loop",
    "FlowApi": "Api",
    "FlowInput": "jiuwen.input",
    "ExceptionInfo": "jiuwen.exception",
    "LoopSetVariable": "jiuwen.setVariable",
    "Aggregate": "jiuwen.aggregation",
    "FlowCode": "Code",
    "ComplexIntentDetection": "EI.ComplexIntentDetection",
    "FlowStreamTransform": "jiuwen.paramExtraction",
    "FlowMcp": "jiuwen.mcp",
}

_SKIP_COMPONENT_KEY: list[str] = [
    "_break_branch_",
    "_break_",
    "_loop_end_",
    "_input",
    "_output",
    "_parallel_done"
]

GLOBAL_REF_PREFIX = "MEMORY_VARIABLE."
NODE_DEFS_KEY = "__node_defs__"
END_NODE_TYPE = "jiuwen.end"
END_COMPONENT_TYPES = {END_NODE_TYPE, "End"}
SUB_WORKFLOW_COMPONENT_TYPES = {"jiuwen.workflowComposite", "jiuwen.subWorkflow", "SubWorkflow"}
END_OUTPUT_PREFIX = "#end_"
_SPECIAL_REF_ROOTS = {"global", "_env", "_request", "query", "sys"}


def _extract_ref_source_id(value: Any) -> str | None:
    """Extract source node id from a direct ${node.field} reference."""
    if not isinstance(value, str) or not value.startswith("${") or not value.endswith("}"):
        return None
    origin_key = value[2:-1]
    if not origin_key or "." not in origin_key:
        return None
    source_id = origin_key.split(".", 1)[0]
    return source_id or None


def _is_unresolved_end_ref_literal(value: Any, schema_value: Any) -> bool:
    """Whether the input is still the unresolved ${node.field} ref literal from schema."""
    if not isinstance(value, str) or not isinstance(schema_value, str):
        return False
    if value != schema_value:
        return False
    return _extract_ref_source_id(schema_value) is not None


@dataclass(frozen=True)
class EndRefInputFilterContext:
    """Context required to filter unresolved End node ref inputs."""

    session: Any
    wf_defs: dict


def _should_skip_end_ref_input(source_id: str | None, context: EndRefInputFilterContext) -> bool:
    """Whether the ref input is not a workflow node reference to validate."""
    if not source_id or source_id in _SPECIAL_REF_ROOTS:
        return True
    return source_id not in context.wf_defs or source_id == context.session.node_id()


def _schema_value_by_definition(definition: dict, *, for_input: bool = False) -> Any:
    """Build schema default/placeholder for End ref fill before validation."""
    if not isinstance(definition, dict):
        return "" if for_input else None
    expected_type = str(definition.get("type", "")).lower()
    if expected_type == "string":
        return ""
    if expected_type == "array":
        return []
    if expected_type == "object":
        schema = definition.get("schema")
        if isinstance(schema, list):
            return {
                item.get("id"): _schema_value_by_definition(item, for_input=for_input)
                for item in schema
                if isinstance(item, dict) and item.get("id")
            }
        return {}
    if for_input:
        if expected_type == "integer":
            return 0
        if expected_type == "number":
            return 0.0
        if expected_type == "boolean":
            return False
        return ""
    if expected_type in {"integer", "number", "boolean"}:
        return None
    return None


def _fill_unexecuted_end_branch_inputs(
    inputs: dict,
    input_schema: dict,
    uf_inputs_defs: list,
    sf_inputs_defs: list,
    context: EndRefInputFilterContext,
) -> dict:
    """Fill missing End ref inputs from unexecuted branches with typed placeholders.

    Vertex sanitize may set these fields to ``""``; array/object fields need typed
    values so force_convert strict validation passes and fields stay in userFields.
    """
    if not isinstance(inputs, dict) or not isinstance(input_schema, dict):
        return inputs

    executed_nodes = context.session.state().get_workflow_state("executed_nodes") or []
    for category, defs in (
        ("userFields", uf_inputs_defs),
        ("systemFields", sf_inputs_defs),
    ):
        schema_fields = input_schema.get(category)
        input_fields = inputs.get(category)
        if not isinstance(schema_fields, dict) or not isinstance(input_fields, dict):
            continue
        defs_by_id = {
            item["id"]: item
            for item in defs
            if isinstance(item, dict) and item.get("id")
        }
        for field_id, schema_value in schema_fields.items():
            source_id = _extract_ref_source_id(schema_value)
            if _should_skip_end_ref_input(source_id, context):
                continue
            if source_id in executed_nodes:
                continue
            current_value = input_fields.get(field_id)
            if current_value is not None and current_value != "":
                continue
            definition = defs_by_id.get(field_id)
            if definition is None:
                continue
            input_fields[field_id] = _schema_value_by_definition(definition, for_input=True)
    return inputs


def _fill_missing_ref_outputs(result: dict, ctx: dict) -> dict:
    """Fill missing array/object ref outputs with schema defaults before validation."""
    if not isinstance(result, dict) or not isinstance(ctx, dict):
        return result
    node_type = ctx.get("node_type")
    if node_type not in END_COMPONENT_TYPES | SUB_WORKFLOW_COMPONENT_TYPES:
        return result

    user_fields = result.get("userFields")
    if not isinstance(user_fields, dict):
        return result

    for definition in ctx.get("uf_outputs_defs", []):
        if not isinstance(definition, dict) or definition.get("sourceType") != "ref":
            continue
        field_type = str(definition.get("type", "")).lower()
        if field_type not in {"array", "object"}:
            continue
        field_id = definition.get("id")
        if not field_id:
            continue
        output_key = f"{END_OUTPUT_PREFIX}{field_id}" if node_type in END_COMPONENT_TYPES else field_id
        if user_fields.get(output_key) in (None, ""):
            user_fields[output_key] = _schema_value_by_definition(definition)
    return result


def _filter_empty_end_ref_inputs(
    inputs: dict,
    input_schema: dict,
    uf_inputs_defs: list,
    sf_inputs_defs: list,
    context: EndRefInputFilterContext,
) -> tuple[list, list]:
    """Skip End strict validation only for unresolved ${node.field} ref literals.

    Missing branch values are filled with typed placeholders by
    ``_fill_unexecuted_end_branch_inputs`` before force_convert runs.

    Only when a field value is still the exact ref string from inputs_schema
    (variable pool did not resolve it) do we drop that field from the type
    definition list so array/object strict validation does not fail.
    """
    if not isinstance(inputs, dict) or not isinstance(input_schema, dict):
        return uf_inputs_defs, sf_inputs_defs
    if not isinstance(context.wf_defs, dict):
        return uf_inputs_defs, sf_inputs_defs

    dropped: dict[str, set[str]] = {"userFields": set(), "systemFields": set()}
    for category in ("userFields", "systemFields"):
        schema_fields = input_schema.get(category)
        input_fields = inputs.get(category)
        if not isinstance(schema_fields, dict) or not isinstance(input_fields, dict):
            continue
        for field_id, schema_value in schema_fields.items():
            source_id = _extract_ref_source_id(schema_value)
            if _should_skip_end_ref_input(source_id, context):
                continue
            if not _is_unresolved_end_ref_literal(input_fields.get(field_id), schema_value):
                continue
            dropped[category].add(field_id)

    if dropped["userFields"]:
        uf_inputs_defs = [
            item for item in uf_inputs_defs
            if not isinstance(item, dict) or item.get("id") not in dropped["userFields"]
        ]
    if dropped["systemFields"]:
        sf_inputs_defs = [
            item for item in sf_inputs_defs
            if not isinstance(item, dict) or item.get("id") not in dropped["systemFields"]
        ]
    return uf_inputs_defs, sf_inputs_defs


class WorkflowStreamDataWrapper:
    """封装 workflow.stream 产生的单个 chunk，转换为统一的 StreamData 格式

    该类负责将 openjiuwen 的 OutputSchema/CustomSchema 转换为 StreamData 格式。
    """

    def __init__(
        self,
        execution_id: str = "",
        is_debug: bool = False,
        conversation_id: str = "",
        node_id_to_name: dict = None,
        history: list = None,
        query: str = "",
        is_resuming: bool = False,
    ):
        if node_id_to_name is None:
            node_id_to_name = {}
        self._execution_id = execution_id
        self._last_node = {"node_id": "", "node_type": ""}
        self._is_debug = is_debug
        self._conversation_id = conversation_id if conversation_id else execution_id
        self._node_id_to_name = node_id_to_name
        self._history = history or []
        self._query = query
        self._is_resuming = is_resuming
        # Collect field names that reference encrypted env vars, per node.
        # Flag-based: checks if the referenced env var key is in secretEnvKeys,
        # not value matching. Per-node mapping avoids cross-node field name
        # collisions (e.g. two nodes both having "value3" but only one
        # references an encrypted env var).
        self._node_secret_fields: dict[str, dict] = {}
        self._end_node_secret_fields: dict = {}
        try:
            _ctx = _request_ctx.get()
            _secret_keys = _ctx.secret_env_keys
        except Exception:
            _secret_keys = []
        if _secret_keys and node_id_to_name:
            for _wf_nodes in node_id_to_name.values():
                for _node_id, _node_def in _wf_nodes.items():
                    _fields = find_secret_env_field_names(_node_def, _secret_keys)
                    if _fields:
                        self._node_secret_fields[_node_id] = _fields
                        if _node_def.get("node_type") == END_NODE_TYPE:
                            self._end_node_secret_fields = _fields
        # Loop debug trace state: track invokeIds for building parentInvokeId chains
        self._loop_invoke_id: dict[str, str] = {}
        self._loop_last_invoke_id: dict[str, str] = {}
        self._loop_parent_cache: dict[str, str] = {}
        self._loop_workflow_id: dict[str, str] = {}
        self._loop_iter_count: dict[str, int] = {}
        # 子工作流中断 trace 缓存列表
        self._interrupt_trace_cache: list[TraceSchema] = []

    @staticmethod
    def _serialize_datetime(value: Any) -> Any:
        """将 datetime 对象转换为 ISO 格式字符串，其他值原样返回"""
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                # 补上本地时区偏移
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                local_tz = now_utc.astimezone().tzinfo
                value = value.replace(tzinfo=local_tz)
            return value.isoformat()
        return value

    def wrap_stream_data(self, chunk: Any, is_resuming: bool = False) -> list[dict]:
        """将单个 chunk 转换为统一的 StreamData 格式

        Args:
            chunk: 原始 chunk (OutputSchema/CustomSchema/dict)
            is_resuming: 是否为恢复执行（跳过重复的中断输出）

        Returns:
            list[dict]: 转换后的 StreamData 格式字典列表，debug 模式下可能包含多个事件
        """
        if chunk is None:
            return []

        # 非调试模式下跳过 TraceSchema
        if isinstance(chunk, TraceSchema):
            if not self._is_debug:
                return []

            payload = chunk.payload if isinstance(chunk.payload, dict) else {}
            ts_status = payload.get("status", "")
            ts_comp_type = payload.get("componentType", "")

            # 子工作流的 running trace 含中断标记 → 缓存，不立即发送
            is_sub_workflow = (
                ts_comp_type == "SubWorkflow"
                or _DEBUG_EVENT_RETURN_TO_SERVICE.get(ts_comp_type, "")
                == "jiuwen.workflowComposite"
            )
            if (
                is_sub_workflow
                and ts_status == "running"
                and self._has_interrupt_marker(payload)
            ):
                self._interrupt_trace_cache.append(chunk)
                return []

            trace_event = self._convert_trace_schema_to_stream_data(chunk)
            if not trace_event:
                return []
            # 调试事件去除openjiuwen的总帧
            if trace_event and not trace_event.get("data", {}).get("componentId", ""):
                return []

            # 当前 trace 为中断/异常状态时，刷出缓存列表中的中断标记帧，
            # 将它们转换为 finish 后追加到返回值末尾
            if (
                ts_status in ("interrupted", "error")
                and self._interrupt_trace_cache
            ):
                events = [trace_event]
                for cached_chunk in self._interrupt_trace_cache:
                    # 补充结束时间
                    if cached_chunk.payload and not cached_chunk.payload.get("endTime"):
                        data = trace_event.get("data", {})
                        cached_chunk.payload["endTime"] = (
                            data.get("endTime", self._serialize_datetime(datetime.datetime.now())))

                    cached_event = self._convert_trace_schema_to_stream_data(
                        cached_chunk
                    )
                    if cached_event and cached_event.get("data", {}).get(
                        "componentId", ""
                    ):
                        cached_event["data"]["status"] = "finish"
                        events.append(cached_event)
                self._interrupt_trace_cache.clear()
                return events

            return [trace_event]

        stream_data = self._convert_chunk_to_stream_data(chunk)
        if stream_data and isinstance(stream_data.get("data"), dict):
            node_id = stream_data["data"].get("node_id", "")
            node_type = stream_data["data"].get("node_type", "")
            if node_id:
                self._last_node["node_id"] = node_id
                self._last_node["node_type"] = node_type

        if not stream_data:
            return []

        return [stream_data]

    def _convert_chunk_to_stream_data(self, chunk: Any) -> dict | None:
        """将 chunk 转换为 StreamData 格式的字典"""
        if chunk.type == INTERACTION or chunk.type == "workflow_end" or chunk.type == "struct_output":
            return None
        elif isinstance(chunk, OutputSchema):
            return self._convert_output_schema(chunk)
        elif isinstance(chunk, CustomSchema):
            return self._convert_custom_schema(chunk)
        elif isinstance(chunk, dict):
            return self._convert_dict(chunk)
        return None

    def _convert_output_schema(self, chunk: OutputSchema) -> dict:
        """转换 OutputSchema 为 StreamData 格式"""
        type_converters = {
            "workflow_final": self._convert_workflow_final,
            "end node stream": self._convert_end_node_stream,
            "message_end": self._convert_message_end,
            "workflow_end": self._convert_workflow_end,
            "workflow_start": self._convert_workflow_start,
            "workflow_exception": self._convert_workflow_exception,
            "component_execute_error": self._convert_error,
            "partial_content": self._convert_partial_content_from_output,
        }

        converter = type_converters.get(chunk.type)
        if converter:
            return converter(chunk)

        payload = chunk.payload
        return {
            "code": "PARTIAL_CONTENT",
            "msg": chunk.type,
            "data": payload if isinstance(payload, dict) else {"answer": str(payload)},
            "executionId": self._execution_id,
            "index": chunk.index,
        }

    def _convert_custom_schema(self, chunk: CustomSchema) -> dict:
        """转换 CustomSchema 为 StreamData 格式"""
        type_converters = {
            "workflow_final": self._convert_workflow_final_from_custom,
            "end node stream": self._convert_end_node_stream_from_custom,
            "message_end": self._convert_message_end_from_custom,
            "partial_content": self._convert_partial_content_from_custom,
            "message node stream": self._convert_partial_content_from_custom,
            "workflow_end": self._convert_workflow_end_from_custom,
            "workflow_start": self._convert_workflow_start_from_custom,
            "workflow_exception": self._convert_workflow_exception_from_custom,
            "component_execute_error": self._convert_error_from_custom,
        }

        chunk_type = getattr(chunk, "type", None)
        converter = type_converters.get(chunk_type)
        if converter:
            return converter(chunk)

        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        return {
            "code": "PARTIAL_CONTENT",
            "msg": chunk_type or "custom_stream",
            "data": data if isinstance(data, dict) else {"answer": str(data)},
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
        }

    def _convert_dict(self, chunk: dict) -> dict:
        """转换字典类型的 chunk"""
        return {
            "code": chunk.get("code", "PARTIAL_CONTENT"),
            "msg": chunk.get("msg", ""),
            "data": chunk.get("data", chunk),
            "executionId": self._execution_id,
            "index": chunk.get("index", 0),
        }

    def _convert_workflow_final(self, chunk: OutputSchema) -> dict:
        """转换 workflow_final → workflow_end"""
        payload = chunk.payload
        if isinstance(payload, dict):
            data = dict(payload)
            _sf = self._end_node_secret_fields
            if "userFields" in data:
                data["userFields"] = mask_debug_data(data["userFields"], _sf)
        else:
            data = {"answer": str(payload)}

        return {
            "event": "workflow_end",
            "data": data,
            "executionId": self._execution_id,
            "index": chunk.index,
            "createdTime": int(time.time() * 1000),
        }

    def _convert_end_node_stream(self, chunk: OutputSchema) -> dict:
        """转换 end node stream → message"""
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"answer": payload}

        data = {
            "answer": payload.get("answer", payload.get("response", "")),
            "node_id": payload.get("node_id", ""),
            "node_name": payload.get("node_name", ""),
            "node_type": payload.get("node_type", ""),
            "should_interrupt": payload.get("should_interrupt", False),
        }
        for key in ("think", "output_mode"):
            if key in payload:
                data[key] = payload[key]

        return {
            "event": "message",
            "data": data,
            "executionId": self._execution_id,
            "index": chunk.index,
            "createdTime": int(time.time() * 1000),
        }

    def _convert_message_end(self, chunk: OutputSchema) -> dict:
        """转换 message_end → message_end"""
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"answer": str(payload)}

        _node_sf = self._node_secret_fields.get(payload.get("node_id", ""), {})

        data = {
            "answer": payload.get("answer", ""),
            "node_id": payload.get("node_id", ""),
            "node_name": payload.get("node_name", ""),
            "node_type": payload.get("node_type", ""),
            "should_interrupt": payload.get("should_interrupt", False),
        }
        user_fields = payload.get("userFields")
        if user_fields:
            data["outputs"] = {"user_fields": mask_debug_data(user_fields, _node_sf)}
        for key in (
            "origin_answer",
            "enable_history",
            "think",
            "output_mode",
            "parentNodeId",
        ):
            if key in payload:
                data[key] = payload[key]

        return {
            "event": "message_end",
            "data": data,
            "executionId": self._execution_id,
            "index": chunk.index,
            "createdTime": int(time.time() * 1000),
        }

    def _convert_workflow_end(self, chunk: OutputSchema) -> dict:
        """转换 workflow_end → workflow_end"""
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"answer": payload}

        data = {
            "answer": payload.get("answer", ""),
            "node_id": payload.get("node_id", ""),
            "node_name": payload.get("node_name", ""),
            "node_type": payload.get("node_type", ""),
            "should_interrupt": payload.get("should_interrupt", False),
        }
        for key in ("output_mode",):
            if key in payload:
                data[key] = payload[key]

        return {
            "event": "workflow_end",
            "data": data,
            "executionId": self._execution_id,
            "index": chunk.index,
            "createdTime": int(time.time() * 1000),
        }

    def _convert_workflow_start(self, chunk: OutputSchema) -> dict:
        """转换 workflow_start → workflow_start"""
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"workflow_id": str(payload)}

        return {
            "event": "workflow_start",
            "data": payload,
            "executionId": self._execution_id,
            "index": chunk.index,
            "createdTime": int(time.time() * 1000),
        }

    def _convert_workflow_exception(self, chunk: OutputSchema) -> dict:
        """转换 workflow_exception → exception"""
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"error_code": -1, "message": str(payload)}

        return {
            "event": "exception",
            "data": payload,
            "executionId": self._execution_id,
            "index": chunk.index,
            "createdTime": int(time.time() * 1000),
        }

    def _convert_error(self, chunk: OutputSchema) -> dict:
        """转换 component_execute_error → error"""
        payload = chunk.payload
        if not isinstance(payload, dict):
            payload = {"message": str(payload)}

        return {
            "event": "error",
            "data": payload,
            "executionId": self._execution_id,
            "index": chunk.index,
            "createdTime": int(time.time() * 1000),
        }

    def _convert_partial_content_from_output(self, chunk: OutputSchema) -> dict:
        """转换 partial_content (OutputSchema) → message"""
        data = chunk.payload if hasattr(chunk, "payload") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"result": data}

        result_data = {
            "answer": data.get("answer", data.get("result", "")),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
        }
        for key in ("think", "output_mode"):
            if key in data:
                result_data[key] = data[key]

        return {
            "event": "message",
            "data": result_data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_partial_content_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 partial_content (CustomSchema) → message"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"result": data}

        result_data = {
            "answer": data.get("answer", data.get("result", "")),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
        }
        for key in ("think", "output_mode"):
            if key in data:
                result_data[key] = data[key]

        return {
            "event": "message",
            "data": result_data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_end_node_stream_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 end node stream (CustomSchema) → message"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"response": data}

        result_data = {
            "answer": data.get("answer", data.get("response", "")),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
        }
        for key in ("think", "output_mode"):
            if key in data:
                result_data[key] = data[key]

        return {
            "event": "message",
            "data": result_data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_message_end_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 message_end (CustomSchema) → message_end"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"answer": str(data)}

        _node_sf = self._node_secret_fields.get(data.get("node_id", ""), {})

        result_data = {
            "answer": data.get("answer", ""),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
            "outputs": {"user_fields": mask_debug_data(data.get("userFields", {}), _node_sf)},
        }

        for key in (
            "origin_answer",
            "enable_history",
            "think",
            "output_mode",
            "parentNodeId",
        ):
            if key in data:
                result_data[key] = data[key]

        return {
            "event": "message_end",
            "data": result_data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_workflow_end_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 workflow_end (CustomSchema) → workflow_end"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"answer": str(data)}

        _node_sf = self._node_secret_fields.get(data.get("node_id", ""), {})

        result_data = {
            "answer": data.get("answer", ""),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
            "outputs": {"user_fields": mask_debug_data(data.get("userFields", {}), _node_sf)},
        }

        for key in ("output_mode",):
            if key in data:
                result_data[key] = data[key]

        return {
            "event": "workflow_end",
            "data": result_data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_workflow_final_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 workflow_final (CustomSchema) → done"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"answer": str(data)}

        _sf = self._end_node_secret_fields
        if "userFields" in data:
            data["userFields"] = mask_debug_data(data["userFields"], _sf)

        return {
            "event": "workflow_end",
            "data": dict(data),
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_workflow_start_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 workflow_start (CustomSchema) → workflow_start"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"workflow_id": str(data)}

        return {
            "event": "workflow_start",
            "data": data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_workflow_exception_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 workflow_exception (CustomSchema) → exception"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"error_code": -1, "message": str(data)}

        return {
            "event": "exception",
            "data": data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _convert_error_from_custom(self, chunk: CustomSchema) -> dict:
        """转换 component_execute_error (CustomSchema) → error"""
        data = chunk.data if hasattr(chunk, "data") else chunk.model_dump()
        if not isinstance(data, dict):
            data = {"message": str(data)}

        return {
            "event": "error",
            "data": data,
            "executionId": self._execution_id,
            "index": getattr(chunk, "index", 0),
            "createdTime": int(time.time() * 1000),
        }

    def _is_skip_component(self, payload: dict):
        comp_id = payload.get("componentId", "")
        if not comp_id:
            return False

        for key in _SKIP_COMPONENT_KEY:
            if key in comp_id:
                return True
        return False

    def _convert_trace_schema_to_stream_data(self, chunk: TraceSchema) -> dict:
        """将 TraceSchema 转换为 StreamData 格式（调试模式）。

        Args:
            chunk: TraceSchema 实例

        Returns:
            list[dict]: 转换后的 StreamData 格式字典列表
        """
        payload = chunk.payload if isinstance(chunk.payload, dict) else {}
        if not payload or self._is_skip_component(payload):
            return {}

        trace_status = payload.get("status", "")
        outputs = payload.get("outputs")
        stream_outputs = payload.get("streamOutputs")
        on_invoke_data = payload.get("onInvokeData", [])

        memory = None
        inner_error = None
        effective_outputs = outputs
        computed_status = None

        if trace_status == "error":
            # Degraded completion: engine may still report error while outputs/endTime exist.
            if outputs is not None and payload.get("endTime"):
                computed_status = "finish"
            else:
                computed_status = "error"
            inner_error = payload.get("innerError")
        elif trace_status == "interrupted":
            computed_status = "running"
        elif trace_status == "finish":
            if outputs is not None:
                if isinstance(outputs, dict):
                    memory = outputs.pop("memory", None)
                effective_outputs = outputs
            elif (
                stream_outputs
                and isinstance(stream_outputs, list)
                and len(stream_outputs) > 0
            ):
                last_frame = stream_outputs[-1]
                effective_outputs = last_frame
                if isinstance(last_frame, dict):
                    memory = last_frame.pop("memory", None)
            computed_status = "finish"
        elif trace_status == "running":
            # Retry inner_error is already emitted once via trace_status=error (on_invoke).
            # pre_invoke on the next attempt stays running while onInvokeData keeps history.
            if on_invoke_data:
                last_item = on_invoke_data[-1]
                if isinstance(last_item, dict) and "inner_error" not in last_item:
                    memory = last_item.get("memory")
            computed_status = "running"
        else:
            computed_status = "start"
            if self._is_resuming and payload.get("componentType", "") == "Questioner":
                computed_status = "running"

        end_time_override = None
        if inner_error is not None:
            for item in reversed(on_invoke_data):
                if isinstance(item, dict) and "current_time" in item:
                    end_time_override = item["current_time"]
                    break

        # 名字转换
        name = payload.get("componentName", "")
        if payload.get("componentId", "") and self._node_id_to_name:
            node_def = self._node_id_to_name.get(payload.get("workflowId"), {}).get(payload.get("componentId", ""), {})
            if not node_def:
                for workflow_id, nodes in self._node_id_to_name.items():
                    if payload.get("componentId", "") in nodes:
                        name = nodes[payload.get("componentId", "")].get("node_name", name)
                        break
            name = node_def.get("node_name", name)

        # 提问器无用帧
        if (
            payload.get("componentType", "") == "Questioner"
            and not on_invoke_data
            and computed_status == "running"
        ):
            return {}

        # Build parentInvokeId for loop body nodes
        loop_node_id = payload.get("loopNodeId")
        raw_loop_index = payload.get("loopIndex")
        # Convert loopIndex from 0-based to 1-based
        loop_index = (raw_loop_index + 1) if raw_loop_index is not None else None
        invoke_id = payload.get("invokeId", "")
        component_type_raw = payload.get("componentType", "")
        component_type_mapped = _DEBUG_EVENT_RETURN_TO_SERVICE.get(
            component_type_raw, component_type_raw
        )
        component_id = payload.get("componentId", "")

        parent_invoke_id = payload.get("parentInvokeId", "")
        if loop_node_id:
            # Node is inside a loop body — build parentInvokeId from tracked state
            if raw_loop_index is not None:
                # For finish/running events, use cached parentInvokeId from the start event
                cache_key = f"{component_id}:{raw_loop_index}"
                if trace_status == "finish" and cache_key in self._loop_parent_cache:
                    parent_invoke_id = self._loop_parent_cache[cache_key]
                else:
                    # For start events, compute parentInvokeId from the chain
                    # Chain is continuous: msg[1] → code[2] → msg[2] → code[3]...
                    if loop_node_id in self._loop_last_invoke_id:
                        parent_invoke_id = self._loop_last_invoke_id[loop_node_id]
                    elif loop_node_id in self._loop_invoke_id:
                        parent_invoke_id = self._loop_invoke_id[loop_node_id]
                    # Cache for the corresponding finish event
                    if trace_status in ("start", ""):
                        self._loop_parent_cache[cache_key] = parent_invoke_id
            # Update tracking for next node (continuous chain, only on start)
            if (
                invoke_id
                and raw_loop_index is not None
                and trace_status in ("start", "")
            ):
                self._loop_last_invoke_id[loop_node_id] = invoke_id
                # Track iteration count (1-based after conversion)
                self._loop_iter_count[loop_node_id] = max(
                    self._loop_iter_count.get(loop_node_id, 0), loop_index or 0
                )
        elif component_type_mapped == "jiuwen.loop":
            # Loop node itself — record its invokeId and workflowId for child nodes to reference
            if invoke_id and component_id and trace_status in ("start", ""):
                self._loop_invoke_id[component_id] = invoke_id
                if payload.get("workflowId"):
                    self._loop_workflow_id[component_id] = payload["workflowId"]

        # Enrich inputs/outputs with systemFields
        inputs = payload.get("inputs")
        if isinstance(inputs, dict) and "systemFields" not in inputs:
            inputs = {**inputs, "systemFields": {}}
        if (
            isinstance(effective_outputs, dict)
            and "systemFields" not in effective_outputs
        ):
            effective_outputs = {**effective_outputs, "systemFields": {}}

        # Add loop execution info to loop node outputs
        if component_type_mapped == "jiuwen.loop" and computed_status == "finish":
            effective_outputs = self._enrich_loop_outputs(payload, effective_outputs)

        # Set metaData for Code nodes
        meta_data = None
        if component_type_mapped == "Code":
            meta_data = {"function_log": ""}

        parent_node_id = payload.get("parentNodeId", "")
        parent_node_id = parent_node_id.rsplit(".", 1)[-1]

        _node_sf = self._node_secret_fields.get(payload.get("componentId", ""), {})

        data = {
            "executionId": self._execution_id,
            "conversationId": self._conversation_id,
            "startTime": self._serialize_datetime(payload.get("startTime")),
            "endTime": self._serialize_datetime(
                end_time_override if end_time_override else payload.get("endTime")
            ),
            "onInvokeData": on_invoke_data,
            "agentId": payload.get("workflowId", ""),
            "componentId": payload.get("componentId", ""),
            "componentName": name,
            "componentType": _DEBUG_EVENT_RETURN_TO_SERVICE.get(
                payload.get("componentType", "unknown"),
                payload.get("componentType", ""),
            ),
            "agentParentInvokeId": "",
            "inputs": mask_debug_data(payload.get("inputs"), _node_sf),
            "outputs": mask_debug_data(effective_outputs, _node_sf),
            "error": payload.get("error"),
            "metaData": None,
            "invokeId": payload.get("invokeId"),
            "parentInvokeId": payload.get("parentInvokeId"),
            "traceId": payload.get("traceId", ""),
            "loopNodeId": payload.get("loopNodeId"),
            "loopIndex": payload.get("loopIndex"),
            "innerError": inner_error,
            "memory": memory,
            "parentNodeId": parent_node_id if not payload.get("loopNodeId") else None,
        }

        if (data["startTime"] and data["endTime"]) and (data["startTime"] > data["endTime"]):
            data["endTime"] = self._serialize_datetime(datetime.datetime.now())

        if data["outputs"] == "":
            data["outputs"] = None

        data["status"] = computed_status

        return {
            "event": "workflow_node_message",
            "data": data,
            "executionId": self._execution_id,
            "index": 0,
            "createdTime": int(time.time() * 1000),
        }

    def _enrich_loop_outputs(self, payload: dict, outputs: dict | None) -> dict | None:
        """Add index, loop_nums, is_break to loop node outputs."""
        if outputs is None:
            return outputs
        result = dict(outputs)
        # Extract loop count from inputs
        inputs = payload.get("inputs")
        if isinstance(inputs, dict):
            loop_number = inputs.get("loop_number") or inputs.get("loop_nums")
            if loop_number is not None:
                result["loop_nums"] = loop_number
        # Add iteration index and break status
        component_id = payload.get("componentId", "")
        if component_id in self._loop_iter_count:
            result["index"] = self._loop_iter_count[component_id]
            result["is_break"] = False
        return result

    # ---------- 子工作流中断 trace 缓存 ----------

    @staticmethod
    def _has_interrupt_marker(payload: dict) -> bool:
        """检查 TraceSchema payload 的 on_invoke_data 是否包含中断标记。"""
        on_invoke_data = payload.get("onInvokeData", [])
        if not isinstance(on_invoke_data, list):
            return False
        for item in on_invoke_data:
            if isinstance(item, dict) and item.get("_sub_interrupt_marker"):
                return True
        return False

    def get_last_node(self) -> dict:
        """获取最后执行的节点信息"""
        return self._last_node.copy()


# ==================== 模块级回调注册 ====================
# task-local 存储，在 type_convert_inputs（有 session）中写入 output 类型定义，
# 供 type_convert_outputs（无 session）在同节点 Task 内读取。
# ContextVar per-Task 隔离：每个节点在 openjiuwen Pregel 引擎中运行在独立的
# asyncio Task 中（task.py:29 asyncio.create_task），
# 不同节点/不同工作流之间的 .set() 互不干扰。
# 存储结构: {"uf_outputs_defs": [], "sf_outputs_defs": [], "node_name": str, "node_type": str, "node_id": str}
_current_output_convert_ctx: contextvars.ContextVar = contextvars.ContextVar(
    '_current_output_convert_ctx', default=None
)

_node_start_time_ctx: contextvars.ContextVar = contextvars.ContextVar(
    '_node_start_time_ctx', default=None
)


def _register_jiuwen_callbacks() -> None:
    """模块级一次性注册 jiuwen 回调到 openjiuwen CallbackFramework。

    Python 模块导入机制保证模块级代码只执行一次，天然满足"只注册一次"。
    回调闭包不引用任何 WorkflowWrapper 实例成员（无 self），通过
    get_state_info(session, "global_state.__node_defs__...") 引用路径读取
    节点定义数据，避开 get_global 的 deepcopy 开销。

    注册四类回调：
    1. resolve_global_vars_transform (transform, priority=10)
       — 解析 ${global.xxx} 引用，在 type_convert_inputs 之前执行
    2. type_convert_inputs / type_convert_outputs (transform)
       — 从 session global_state 读取节点 configs，做类型强转
    3. notify_start_trace_resolved (regular)
       — 通过 CustomSchema 通知 WorkflowWrapper 发送缓存的 start trace
    4. node_perf_start / node_perf_end (transform+regular)
       — 记录节点执行耗时，输出 node_executed<node_id>|{ms} 性能日志
    """
    try:
        from openjiuwen.core.runner.callback.events import WorkflowEvents
        from openjiuwen.core.runner.callback.utils import get_callback_framework
        from openjiuwen.core.session.utils import is_ref_path, extract_origin_key
        from openjiuwen.core.session.internal.workflow import NodeSession

        _fw = get_callback_framework()
        if _fw is None:
            return


        def _resolve_global_refs(schema, inputs, session_state, global_updates):
            """Recursively resolve ${global.xxx} references in nested input_schema."""
            if not isinstance(schema, dict) or not isinstance(inputs, dict):
                return
            for key, schema_value in schema.items():
                if isinstance(schema_value, str) and is_ref_path(schema_value):
                    origin_key = extract_origin_key(schema_value)
                    if origin_key.startswith(GLOBAL_REF_PREFIX):
                        var_name = origin_key[len(GLOBAL_REF_PREFIX):]
                        var_value = session_state.get_global(origin_key)
                        if var_value is None:
                            global_updates[var_name] = None
                        inputs[key] = var_value
                elif isinstance(schema_value, dict):
                    if key not in inputs or not isinstance(inputs[key], dict):
                        inputs[key] = {}
                    _resolve_global_refs(schema_value, inputs[key], session_state, global_updates)

        @_fw.on(WorkflowEvents.COMPONENT_BATCH_INPUT, callback_type="transform", priority=10)
        async def resolve_global_vars_transform(*args, **kwargs):
            """Transform-type callback: resolve ${global.xxx} references in inputs.

            Runs with priority=10 so it executes before type_convert_inputs (priority=0)
            within trigger_transform. Returns (new_args, new_kwargs) format as required
            by transform_io's _input_from_events.
            """
            session = kwargs.get("session")
            if session is None and len(args) >= 2:
                session = args[1]
            if session is None or not isinstance(session, NodeSession):
                return (args, kwargs)

            inputs = args[1] if len(args) >= 2 else kwargs.get("inputs")
            if not isinstance(inputs, dict):
                return (args, kwargs)

            node_config = session.node_config()
            if not node_config or not node_config.io_configs:
                return (args, kwargs)

            input_schema = node_config.io_configs.inputs_schema
            if not isinstance(input_schema, dict):
                return (args, kwargs)

            global_updates = {}
            _resolve_global_refs(input_schema, inputs, session.state(), global_updates)

            if global_updates:
                session.state().update_global(global_updates)

            return (args, kwargs)

        from jiuwen.orchestration.flow.utils import force_convert_component_by_schema_raise_openjiuwen_exception
        from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowMetadata
        from jiuwen.orchestration.flow.constant import (
            STRUCTURE_POSITION_INPUTS,
            STRUCTURE_POSITION_OUTPUTS,
        )

        @_fw.on(WorkflowEvents.COMPONENT_BATCH_INPUT, callback_type="transform")
        async def type_convert_inputs(*args, **kwargs):
            """按照 __node_defs__ 中 configs 的类型定义对节点输入值做类型强转。

            从 session global_state 经 get_state_info 引用路径读取 __node_defs__，
            按 session.workflow_id() + session.node_id() 定位具体节点数据。

            同时将 output 类型定义提前存入 ContextVar，
            供 type_convert_outputs（无 session）在同 Task 内读取。

            transform_io 输入回调需返回 (new_args, new_kwargs) 格式。
            """
            _current_output_convert_ctx.set(None)

            session = kwargs.get("session")
            if session is None and len(args) >= 2:
                session = args[1]
            if session is None:
                return (args, kwargs)

            if not isinstance(session, NodeSession):
                return (args, kwargs)

            # 优先从 component 实例的 _node_def 取（IRConverter 创建时赋值），
            # 避免 session global_state 的 deepcopy 开销；
            # 回退到 session 读取（旧路径兼容，find_secret_env 等仍依赖）。
            node_def = getattr(args[0], "_node_def", None) if args else None
            if not isinstance(node_def, dict):
                node_def = get_state_info(
                    session,
                    f"global_state.{NODE_DEFS_KEY}.{session.workflow_id()}.{session.node_id()}",
                ) or {}
            if not isinstance(node_def, dict):
                node_def = {}
            if node_def:
                configs = node_def.get("configs", {})
                _current_output_convert_ctx.set({
                    "uf_outputs_defs": configs.get("userFields", {}).get("outputs", []),
                    "sf_outputs_defs": configs.get("systemFields", {}).get("outputs", []),
                    "node_name": node_def.get("node_name", ""),
                    "node_type": session.node_type() or "",
                    "node_id": session.node_id(),
                })
                uf_inputs_defs = configs.get("userFields", {}).get("inputs", [])
                sf_inputs_defs = configs.get("systemFields", {}).get("inputs", [])
            else:
                uf_inputs_defs = []
                sf_inputs_defs = []

            # args[0] = self (ComponentExecutable 实例，因 on_invoke 是类级包装)
            # args[1] = inputs (输入数据 dict)
            inputs = args[1] if len(args) >= 2 else kwargs.get("inputs")
            if not isinstance(inputs, dict):
                return (args, kwargs)

            if not uf_inputs_defs and not sf_inputs_defs:
                return (args, kwargs)

            if node_def and node_def.get("node_type") == END_NODE_TYPE:
                node_config = session.node_config()
                input_schema = None
                if node_config and node_config.io_configs:
                    input_schema = node_config.io_configs.inputs_schema
                # End 节点 ref 过滤只需本 workflow 的 node_id 集合，
                # 优先从 component 实例的 _workflow_node_ids 取（避免 session deepcopy）；
                # 回退到 session 读取（旧路径兼容）。
                wf_defs = getattr(args[0], "_workflow_node_ids", None) if args else None
                if wf_defs is None:
                    wf_defs = get_state_info(
                        session,
                        f"global_state.{NODE_DEFS_KEY}.{session.workflow_id()}",
                    ) or {}
                end_ctx = EndRefInputFilterContext(
                    session=session,
                    wf_defs=wf_defs,
                )
                if isinstance(input_schema, dict):
                    inputs = _fill_unexecuted_end_branch_inputs(
                        inputs=inputs,
                        input_schema=input_schema,
                        uf_inputs_defs=uf_inputs_defs,
                        sf_inputs_defs=sf_inputs_defs,
                        context=end_ctx,
                    )
                uf_inputs_defs, sf_inputs_defs = _filter_empty_end_ref_inputs(
                    inputs=inputs,
                    input_schema=input_schema,
                    uf_inputs_defs=uf_inputs_defs,
                    sf_inputs_defs=sf_inputs_defs,
                    context=end_ctx,
                )
                if not uf_inputs_defs and not sf_inputs_defs:
                    new_args = (args[0], inputs) + args[2:] if len(args) >= 2 else (inputs,)
                    return (new_args, kwargs)

            node_name = node_def.get("node_name", "")
            node_info = WorkflowMetadata(
                node_id=session.node_id(),
                node_type=session.node_type() or "",
                node_name=node_name,
            )

            converted = force_convert_component_by_schema_raise_openjiuwen_exception(
                inputs=inputs,
                node_configs={
                    "userFields": {"inputs": uf_inputs_defs},
                    "systemFields": {"inputs": sf_inputs_defs},
                },
                node_info=node_info,
                structure_pos=STRUCTURE_POSITION_INPUTS,
            )

            # 保留 args[0] (self)，替换 args[1] (inputs)
            new_args = (args[0], converted) + args[2:] if len(args) >= 2 else (converted,)
            return (new_args, kwargs)

        @_fw.on(WorkflowEvents.COMPONENT_BATCH_OUTPUT, callback_type="transform")
        async def type_convert_outputs(result, **kwargs):
            """按照 __node_defs__ 中 configs 的类型定义对节点输出值做类型强转。

            从 ContextVar 读取类型定义（由 type_convert_inputs 在同 Task 内写入），
            不依赖 session（output transform 回调不传 session）。
            """
            if not isinstance(result, dict):
                return result

            ctx = _current_output_convert_ctx.get()
            if ctx is None:
                _logger.warning(
                    "type_convert_outputs: ContextVar is None for result (node output may "
                    "not be type-validated). This typically indicates the output transform "
                    "is running in a different asyncio Task than type_convert_inputs."
                )
                return result

            uf_outputs_defs = ctx.get("uf_outputs_defs", [])
            sf_outputs_defs = ctx.get("sf_outputs_defs", [])
            if not uf_outputs_defs and not sf_outputs_defs:
                return result

            node_info = WorkflowMetadata(
                node_id=ctx.get("node_id", ""),
                node_type=ctx.get("node_type", ""),
                node_name=ctx.get("node_name", ""),
            )

            result = _fill_missing_ref_outputs(result, ctx)

            return force_convert_component_by_schema_raise_openjiuwen_exception(
                inputs=result,
                node_configs={
                    "userFields": {"outputs": uf_outputs_defs},
                    "systemFields": {"outputs": sf_outputs_defs},
                },
                node_info=node_info,
                structure_pos=STRUCTURE_POSITION_OUTPUTS,
            )

        # ---------- 节点执行耗时性能日志 ----------
        @_fw.on(WorkflowEvents.COMPONENT_BATCH_INPUT, callback_type="transform", priority=-10)
        async def node_perf_start(*args, **kwargs):
            """Record node execution start time and metadata via ContextVar.

            Priority=-10 ensures this runs after all other input transforms
            (type_convert_inputs=0, resolve_global_vars=10).
            """
            session = kwargs.get("session")
            if session is None and len(args) >= 2:
                session = args[1]
            if session is not None and isinstance(session, NodeSession):
                # 优先从 component 实例的 _node_def 取（避免 session deepcopy）；
                # 回退到 session 读取（旧路径兼容）。
                node_def = getattr(args[0], "_node_def", None) if args else None
                if not isinstance(node_def, dict):
                    node_def = get_state_info(
                        session,
                        f"global_state.{NODE_DEFS_KEY}.{session.workflow_id()}.{session.node_id()}",
                    ) or {}
                if not isinstance(node_def, dict):
                    node_def = {}
                _node_start_time_ctx.set({
                    "start": time.perf_counter(),
                    "node_type": node_def.get("node_type", ""),
                    "node_name": node_def.get("node_name", ""),
                })
            return (args, kwargs)

        @_fw.on(WorkflowEvents.NODE_EXECUTED, priority=0)
        async def node_perf_end(node_id, ability, graph_id, inputs, outputs):
            """Emit per-node execution timing.

            Format: node_executed<type_name>|{ms}
            e.g. node_executed<jiuwen.code_代码>|12
            Aligns with old project: _execute_invokable<node=jiuwen.code_代码>|12
            """
            ctx = _node_start_time_ctx.get()
            if ctx is None:
                return
            duration_ms = round((time.perf_counter() - ctx["start"]) * 1000)
            node_type = ctx.get("node_type", "")
            node_name = ctx.get("node_name", "")
            # 对齐老项目格式: type_name (e.g. jiuwen.code_代码)
            if node_type and node_name:
                label = f"{node_type}_{node_name}"
            elif node_type:
                label = node_type
            elif node_name:
                label = node_name
            else:
                label = node_id
            performance_logger.info(f"node_executed<{label}>|{duration_ms}")
            _node_start_time_ctx.set(None)
    except Exception as e:
        _logger.warning(
            "Failed to register jiuwen callbacks (type_convert/resolve_global/perf): %s",
            e,
            exc_info=True,
        )


# 模块首次导入时自动注册回调（Python 保证只执行一次）
_register_jiuwen_callbacks()
