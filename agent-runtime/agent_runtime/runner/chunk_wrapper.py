#!/usr/bin env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Chunk 封装器 - 将 workflow.stream 产生的单个 chunk 转换为统一的 StreamData 格式
"""

import datetime
import time
from typing import Any

from openjiuwen.core.common.constants.constant import INTERACTION
from openjiuwen.core.session.stream.base import (
    OutputSchema,
    CustomSchema,
    TraceSchema,
)


class StreamDataWrapper:
    """封装 workflow.stream 产生的单个 chunk，转换为统一的 StreamData 格式

    该类负责将 openjiuwen 的 OutputSchema/CustomSchema 转换为 StreamData 格式。
    """

    def __init__(
        self, execution_id: str = "", is_debug: bool = False, conversation_id: str = ""
    ):
        self._execution_id = execution_id
        self._last_node = {"node_id": "", "node_type": ""}
        self._is_debug = is_debug
        self._conversation_id = conversation_id if conversation_id else execution_id

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

    def wrap_chunk(self, chunk: Any, is_resuming: bool = False) -> list[dict]:
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
            trace_event = self._convert_trace_schema_to_stream_data(chunk)
            # 调试事件去除openjiuwen的总帧
            if trace_event and not trace_event.get("data", {}).get("componentId", ""):
                return []
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
        if chunk.type == INTERACTION or chunk.type == "workflow_end":
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

        data = {
            "answer": payload.get("answer", ""),
            "node_id": payload.get("node_id", ""),
            "node_name": payload.get("node_name", ""),
            "node_type": payload.get("node_type", ""),
            "should_interrupt": payload.get("should_interrupt", False),
        }
        user_fields = payload.get("userFields")
        if user_fields:
            data["outputs"] = {"user_fields": user_fields}
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

        result_data = {
            "answer": data.get("answer", ""),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
            "outputs": {"user_fields": data.get("userFields", {})},
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

        result_data = {
            "answer": data.get("answer", ""),
            "node_id": data.get("node_id", ""),
            "node_name": data.get("node_name", ""),
            "node_type": data.get("node_type", ""),
            "should_interrupt": data.get("should_interrupt", False),
            "outputs": {"user_fields": data.get("userFields", {})},
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

    def _convert_trace_schema_to_stream_data(self, chunk: TraceSchema) -> dict:
        """将 TraceSchema 转换为 StreamData 格式（调试模式）。

        Args:
            chunk: TraceSchema 实例

        Returns:
            list[dict]: 转换后的 StreamData 格式字典列表
        """
        payload = chunk.payload if isinstance(chunk.payload, dict) else {}
        if not payload:
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
            computed_status = "error"
            inner_error = payload.get("innerError")
        elif trace_status == "interrupted":
            computed_status = "error"
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
            if on_invoke_data:
                last_item = on_invoke_data[-1]
                if isinstance(last_item, dict) and "inner_error" in last_item:
                    inner_error = last_item["inner_error"]
                    computed_status = "error"
                else:
                    if isinstance(last_item, dict):
                        memory = last_item.get("memory")
                    computed_status = "running"
        else:
            computed_status = "start"

        end_time_override = None
        if inner_error is not None:
            for item in reversed(on_invoke_data):
                if isinstance(item, dict) and "current_time" in item:
                    end_time_override = item["current_time"]
                    break

        data = {
            "executionId": self._execution_id,
            "conversationId": self._conversation_id,
            "startTime": self._serialize_datetime(payload.get("startTime")),
            "endTime": self._serialize_datetime(
                end_time_override if end_time_override else payload.get("endTime")
            ),
            "onInvokeData": on_invoke_data,
            "agentId": "",
            "componentId": payload.get("componentId", ""),
            "componentName": payload.get("componentName", ""),
            "componentType": payload.get("componentType", ""),
            "agentParentInvokeId": "",
            "inputs": payload.get("inputs"),
            "outputs": effective_outputs,
            "error": payload.get("error"),
            "metaData": None,
            "invokeId": payload.get("invokeId"),
            "parentInvokeId": payload.get("parentInvokeId"),
            "traceId": payload.get("traceId", ""),
            "loopNodeId": payload.get("loopNodeId"),
            "loopIndex": payload.get("loopIndex"),
            "innerError": inner_error,
            "memory": memory,
        }

        if trace_status == "interrupted":
            # 中断不返回调试事件的finished状态
            return {}

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

    def get_last_node(self) -> dict:
        """获取最后执行的节点信息"""
        return self._last_node.copy()
