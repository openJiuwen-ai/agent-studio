#!/usr/bin/env python
# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""Controller StreamData adapter - converts ControllerMode StreamData to SSE format."""

import json
import time
from typing import Any

from jiuwen.orchestration.flow.stream.base import StreamCode
from pydantic import BaseModel


def _make_json_serializable(obj: Any) -> Any:
    """Recursively convert Pydantic models and other non-JSON-serializable objects to dicts."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    return obj


# Reuse commercial mapping logic from utils.py line 112-140
STREAM_CODE_TO_EVENT = {
    StreamCode.START.value: "start",
    StreamCode.PARTIAL_CONTENT.value: "message",
    StreamCode.MESSAGE_END.value: "message_end",
    StreamCode.FINISH.value: "done",
    StreamCode.ERROR.value: "error",
    StreamCode.WORKFLOW_EXCEPTION.value: "exception",
    StreamCode.WORKFLOW_START.value: "workflow_start",
    StreamCode.WORKFLOW_END.value: "workflow_end",
    StreamCode.WORKFLOW_NODE_MESSAGE.value: "workflow_node_message",
    StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value: "intermediate_message",
    StreamCode.CONTROLLER_START_MESSAGE.value: "task_start",
    StreamCode.CONTROLLER_FINISH_MESSAGE.value: "task_end",
    StreamCode.CONTROLLER_WAIT_USER_INPUT_MESSAGE.value: "waiting_user_input",
    StreamCode.CONTROLLER_AGENT_HANDOFF_MESSAGE.value: "agent_handoff",
    StreamCode.CONTROLLER_AGENT_INTERRUPT_MESSAGE.value: "agent_interrupted",
    StreamCode.TASK_TERMINATED_MESSAGE.value: "task_terminated",
}


class ControllerStreamDataAdapter:
    """Adapt ControllerMode StreamData objects to SSE event dictionaries."""

    def __init__(self, execution_id: str = ""):
        self._execution_id = execution_id

    def adapt(self, stream_data: Any) -> list[dict]:
        """Convert a single StreamData to SSE event dict(s).

        Args:
            stream_data: StreamData object from ControllerMode.stream()

        Returns:
            List of SSE event dictionaries (usually 1, may be empty for filtered types)
        """
        if stream_data is None:
            return []

        code = getattr(stream_data, "code", None)
        if code is None:
            return []

        event_name = STREAM_CODE_TO_EVENT.get(code, "message")

        # Extract data payload
        data = getattr(stream_data, "data", None)
        if isinstance(data, dict):
            data = _make_json_serializable(data)
        elif data is not None:
            data = {"answer": str(data)}
        else:
            data = {}

        execution_id = getattr(stream_data, "execution_id", None) or self._execution_id
        index = getattr(stream_data, "index", 0)

        return [
            {
                "event": event_name,
                "data": data,
                "executionId": execution_id,
                "index": index,
                "createdTime": int(time.time() * 1000),
                "isStructMessage": False,
            }
        ]

    def adapt_start(self, execution_id: str = "") -> dict:
        """Create a start event."""
        return {
            "event": "start",
            "data": {},
            "executionId": execution_id or self._execution_id,
            "index": 0,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }

    def adapt_task_start(self, execution_id: str = "") -> dict:
        """Create a task_start event."""
        return {
            "event": "task_start",
            "data": {},
            "executionId": execution_id or self._execution_id,
            "index": 0,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }

    def adapt_error(self, error_msg: str, execution_id: str = "", error_code: int = 103104, node_name: str = "控制器") -> dict:
        """Create an error event.

        Args:
            error_msg: Raw error message (will be wrapped with unified format)
            execution_id: Execution ID for tracking
            error_code: Application-level error code (default 103104 = general execution error)
            node_name: Display name of the node where the error occurred
        """
        from jiuwen.orchestration.flow.constant import WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE
        formatted_msg = WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE.format(error_code, error_msg)
        return {
            "event": "error",
            "data": {
                "code": error_code,
                "message": formatted_msg,
                "node_name": node_name,
            },
            "executionId": execution_id or self._execution_id,
            "index": 0,
            "createdTime": int(time.time() * 1000),
            "isStructMessage": False,
        }

    def adapt_execution_id(self, chunk: bytes) -> bytes:
        """Replace executionId in SSE chunk bytes with adapter's _execution_id.

        Args:
            chunk: SSE bytes containing JSON with executionId field

        Returns:
            Modified SSE bytes with updated executionId
        """
        if isinstance(chunk, bytes):
            chunk_str = chunk.decode("utf-8")
        else:
            chunk_str = chunk

        if not chunk_str.startswith("data: "):
            return chunk

        json_str = chunk_str[6:]  # Remove "data: " prefix
        try:
            data = json.loads(json_str)
            if "executionId" in data:
                data["executionId"] = self._execution_id
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
        except json.JSONDecodeError:
            return chunk
