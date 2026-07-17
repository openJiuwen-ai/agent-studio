#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
请求上下文中间件 — 在整个请求生命周期内管理 RequestContext

解决异步场景下 contextvars 的生命周期问题：
- StreamingResponse 返回时函数立即结束，但流式内容还在生成中
- 中间件在 await call_next() 期间阻塞，保证 context 在流式过程中有效
"""

import json
import uuid

from agent_runtime.context.request_context import RequestContext, _request_ctx
from openjiuwen.core.common.logging import set_session_id
from openjiuwen.core.common.logging import workflow_logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

X_EXECUTION_ID = "x-execution-id"
X_REQUEST_ID = "x-request-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文中间件 — 在整个请求生命周期内管理 RequestContext"""

    async def dispatch(self, request: Request, call_next):
        # 1. 提取 execution_id / request_id
        execution_id = request.headers.get(X_EXECUTION_ID)
        if not execution_id or len(execution_id) > 64:
            if execution_id:
                workflow_logger.warning(f"header {X_EXECUTION_ID} is illegal")
            execution_id = str(uuid.uuid4())

        request_id = request.headers.get(X_REQUEST_ID)
        if not request_id or len(request_id) > 64:
            if request_id:
                workflow_logger.warning(f"header {X_REQUEST_ID} is illegal")
            request_id = str(uuid.uuid4())

        request.state.execution_id = execution_id
        request.state.request_id = request_id

        # 2. 解析请求体
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()

        ctx = RequestContext(
            headers={
                "X-Auth-Token": request.headers.get("x-auth-token", ""),
                "Cookie": request.headers.get("cookie", ""),
                "x-language": request.headers.get("x-language", ""),
                "accept-language": request.headers.get("accept-language", ""),
            },
            user_id="",
            conversation_id="",
            execution_id=execution_id,
            request_id=request_id,
        )

        if body:
            try:
                body_json = json.loads(body)
                ctx.user_id = body_json.get("userId", "")
                ctx.conversation_id = body_json.get("conversationId", "")
                params = body_json.get("params") or {}
                ctx.secret_env_keys = params.get("secretEnvKeys", [])
            except Exception as e:
                workflow_logger.warning(
                    f"Failed to parse request body as JSON: {e}", exc_info=True
                )

        # 3. 设置日志上下文，用 conversationId 作为 trace_id，便于按会话追踪日志
        set_session_id(ctx.conversation_id or execution_id)
        token = _request_ctx.set(ctx)
        try:
            response = await call_next(request)
            return response
        finally:
            _request_ctx.reset(token)
            set_session_id("default_trace_id")
