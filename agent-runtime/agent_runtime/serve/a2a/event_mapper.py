# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Map low-code SSE events to A2A task state machine (SUBMITTED→WORKING→COMPLETED/FAILED)."""


class A2aEventMapper:
    """Maps low-code ConversationEvent types to A2A task status and JSON-RPC frames."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._status = "SUBMITTED"

    def make_task_submitted_frame(self, request_id) -> dict:
        """First frame: task accepted."""
        self._status = "WORKING"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"id": self.task_id, "status": "SUBMITTED"},
        }

    def make_artifact_update_frame(self, text: str) -> dict:
        """Intermediate frame: artifact update during WORKING."""
        return {
            "jsonrpc": "2.0",
            "method": "notification",
            "params": {
                "id": self.task_id,
                "status": "WORKING",
                "artifact": {"parts": [{"type": "text", "text": text}]},
            },
        }

    def make_completed_frame(self, final_text: str, request_id) -> dict:
        """Terminal frame: COMPLETED with final result."""
        self._status = "COMPLETED"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "id": self.task_id,
                "status": "COMPLETED",
                "artifact": {"parts": [{"type": "text", "text": final_text}]},
            },
        }

    def make_failed_frame(self, error_msg: str, request_id) -> dict:
        """Terminal frame: FAILED."""
        self._status = "FAILED"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32003,
                "message": error_msg,
                "data": {"code": "TASK_FAILED", "retryable": False},
            },
        }

    def make_input_required_degraded_frame(self, text: str, request_id) -> dict:
        """INPUT_REQUIRED degraded to COMPLETED with prompt."""
        self._status = "COMPLETED"
        prompt = f"{text}\n\n[需要补充输入，请重新发起调用提供更多信息]"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "id": self.task_id,
                "status": "COMPLETED",
                "artifact": {"parts": [{"type": "text", "text": prompt}]},
            },
        }

    def map_event(self, event_data: dict, request_id) -> dict | None:
        """Map a low-code SSE event dict to an A2A JSON-RPC frame.

        Returns None for events to skip.
        """
        event_type = event_data.get("event") or event_data.get("type", "")
        data = event_data.get("data", event_data)

        if event_type in ("START", "WORKFLOW_START", "plan_start", "start", "workflow_start"):
            return self.make_task_submitted_frame(request_id)
        elif event_type in (
            "MESSAGE", "WORKFLOW_NODE_MESSAGE", "INTERMEDIATE_MESSAGE",
            "plan_message", "node_message", "message", "workflow_node_message",
            "intermediate_message", "agent_node_message",
        ):
            text = data.get("text", data.get("message", ""))
            if text:
                return self.make_artifact_update_frame(str(text))
            return None
        elif event_type in ("DONE", "done", "end", "plan_done", "workflow_end", "workflow_finished"):
            text = data.get("text", data.get("result", data.get("message", "")))
            return self.make_completed_frame(str(text) if text else "", request_id)
        elif event_type in ("ERROR", "EXCEPTION", "error", "plan_error", "exception"):
            text = data.get("text", data.get("message", "Internal error"))
            return self.make_failed_frame(str(text), request_id)
        elif event_type in ("WAITING_USER_INPUT", "AGENT_INTERRUPTED", "interrupt", "waiting_user_input", "agent_interrupted"):
            text = data.get("text", data.get("message", ""))
            return self.make_input_required_degraded_frame(str(text) if text else "", request_id)
        return None
