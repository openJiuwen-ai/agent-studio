# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""JSON-RPC 2.0 error codes for A2A protocol."""


class A2aErrorCode:
    TASK_NOT_FOUND = -32001      # target doesn't exist or offline
    METHOD_NOT_FOUND = -32601    # not SendMessage/SendStreamingMessage
    INVALID_PARAMS = -32602      # missing required fields
    INTERNAL_ERROR = -32603      # unexpected error
    UNAUTHORIZED = -32600        # auth failed
    TASK_FAILED = -32003         # task execution failed


# Mapping: code → (stable_code_string, retryable_bool)
ERROR_DEFS = {
    -32001: ("TASK_NOT_FOUND", False),
    -32601: ("VALIDATION_METHOD", False),
    -32602: ("VALIDATION_FAILED", False),
    -32603: ("INTERNAL_ERROR", False),
    -32600: ("UNAUTHORIZED", False),
    -32003: ("TASK_FAILED", False),
}


def make_rpc_error(code: int, message: str, request_id=None) -> dict:
    """Build a JSON-RPC 2.0 error response object."""
    stable_code, retryable = ERROR_DEFS.get(code, ("UNKNOWN", False))
    error_obj = {
        "code": code,
        "message": message,
        "data": {"code": stable_code, "retryable": retryable},
    }
    return {"jsonrpc": "2.0", "id": request_id, "error": error_obj}
