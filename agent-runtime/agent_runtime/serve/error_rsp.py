# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""统一错误响应构造 — 四字段 ErrorRsp（error_code/error_msg/error_reason/error_suggestion）。

供 internal_routes.py / conversation_variable_api.py 等所有 runtime 接口复用，
与 server.py 的 RequestValidationError 全局处理器（02001003 四字段）形态一致。
"""

from fastapi.responses import JSONResponse

from agent_runtime.event_handler.base.mappers import ErrorContextBuilder


def build_error_response(
    status_code: int,
    code_key: str,
    language: str = "zh-cn",
    reason: str = None,
) -> JSONResponse:
    """构建四字段 ErrorRsp 错误响应。

    Args:
        status_code: HTTP 状态码
        code_key: 错误码 key（如 "02001003"，不含 openjiuwen. 前缀）
        language: 语言（zh-cn/en-us）
        reason: 附加错误原因详情（追加到 error_reason）
    """
    error_code, error_msg, error_reason, error_suggestion = (
        ErrorContextBuilder.get_language_context(language, code_key)
    )
    if reason:
        error_reason = f"{error_reason}: {reason}" if error_reason else reason
    content = {
        "error_code": error_code,
        "error_msg": error_msg,
        "error_reason": error_reason,
        "error_suggestion": error_suggestion,
    }
    return JSONResponse(status_code=status_code, content=content)
