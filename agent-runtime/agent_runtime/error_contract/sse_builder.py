"""COM-03 §6.1: Runtime SSE 错误事件构建器。

输入 ErrorDescriptor + locale，输出统一 ``event="error"`` envelope。
只负责序列化，不选码、不读原始异常、不递归创建第二个 error。
"""

from __future__ import annotations

import json
from typing import Any

from agent_runtime.error_contract.descriptor import ErrorDescriptor
from agent_runtime.error_contract.http_builder import I18nResolver


def build_sse_error_envelope(
    descriptor: ErrorDescriptor,
    locale: str,
    resolver: I18nResolver,
) -> dict[str, Any]:
    """构建 SSE error 事件的业务 JSON envelope（未做 SSE wire 编码）。"""
    message, reason, suggestion = resolver.resolve(locale, descriptor.message_key)

    data: dict[str, Any] = {
        "error_code": descriptor.error_code,
        "error_msg": message,
        "error_reason": reason,
        "error_suggestion": suggestion,
        "request_id": descriptor.request_id,
    }

    return {
        "event": "error",
        "data": data,
    }


def format_sse_event(envelope: dict[str, Any]) -> str:
    """将 envelope 编码为 SSE ``data:`` 帧。"""
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n"
