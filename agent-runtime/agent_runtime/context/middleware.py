#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
请求上下文中间件 — 在整个请求生命周期内管理 RequestContext

解决异步场景下 contextvars 的生命周期问题：
- StreamingResponse 返回时函数立即结束，但流式内容还在生成中
- 中间件在 await call_next() 期间阻塞，保证 context 在流式过程中有效

改造：
- capture cust-* header（白名单，不含 x-auth-token）
- ctx.customer_headers / ctx.platform_headers 独立分仓
- 配置启用 + cust-userid 非空 → 覆盖 ctx.user_id（effective userId）
"""

import json
import uuid

from agent_runtime.context.request_context import RequestContext, _request_ctx
from common_utils.customer_header import get_capture_keys, get_config
from openjiuwen.core.common.logging import set_session_id
from openjiuwen.core.common.logging import workflow_logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

X_EXECUTION_ID = "x-execution-id"
X_REQUEST_ID = "x-request-id"
DEFAULT_USER = "testUser"


def _capture_customer_headers(request: Request) -> dict[str, str]:
    """按白名单捕获客户 header（cust-*，不含 x-auth-token）"""
    cfg = get_config()
    if not cfg.enabled:
        return {}

    allow_list = get_capture_keys()
    result = {}
    for name in allow_list:
        value = request.headers.get(name) or request.headers.get(name.lower())
        if value:
            result[name.lower()] = value
    return result


def _capture_platform_headers(request: Request) -> dict:
    """捕获平台 header（X-Auth-Token 等）"""
    return {
        "X-Auth-Token": request.headers.get("x-auth-token", ""),
        "X-Execution-Id": request.headers.get("x-execution-id", ""),
        "X-Invoke-Mode": request.headers.get("x-invoke-mode", ""),
        "Cookie": request.headers.get("cookie", ""),
        "x-language": request.headers.get("x-language", ""),
        "accept-language": request.headers.get("accept-language", ""),
    }


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

        # 3. 捕获平台 header 和客户 header
        platform_headers = _capture_platform_headers(request)
        customer_headers = _capture_customer_headers(request)

        ctx = RequestContext(
            headers={
                "X-Auth-Token": platform_headers.get("X-Auth-Token", ""),
                "Cookie": platform_headers.get("Cookie", ""),
                "x-language": platform_headers.get("x-language", ""),
                "accept-language": platform_headers.get("accept-language", ""),
            },
            user_id="",
            conversation_id="",
            execution_id=execution_id,
            request_id=request_id,
            customer_headers=customer_headers,
            platform_headers=platform_headers,
        )

        # 从 X-Auth-Token 或 AGENT_SID cookie 解析 user_id（格式: userId|projectId）
        auth_token = ctx.headers.get("X-Auth-Token", "")
        if not auth_token:
            cookie_header = ctx.headers.get("Cookie", "")
            for cookie_part in cookie_header.split(";"):
                cookie_part = cookie_part.strip()
                if cookie_part.startswith("AGENT_SID="):
                    auth_token = cookie_part.split("=", 1)[1]
                    break

        if auth_token and "|" in auth_token:
            parts = auth_token.split("|", 1)
            ctx.user_id = parts[0]
            ctx.project_id = parts[1] if len(parts) > 1 else ""

        if body:
            try:
                body_json = json.loads(body)
                if not ctx.user_id:
                    ctx.user_id = body_json.get("userId", DEFAULT_USER)
                ctx.conversation_id = body_json.get("conversationId", "")
                params = body_json.get("params") or {}
                ctx.secret_env_keys = params.get("secretEnvKeys", [])
            except Exception as e:
                workflow_logger.warning(
                    f"Failed to parse request body as JSON: {e}", exc_info=True
                )

        # 4. 配置启用时，覆盖 effective userId
        cfg = get_config()
        if cfg.enabled:
            cust_userid = ctx.customer_headers.get("cust-userid")
            if cust_userid:
                ctx.user_id = cust_userid

        # 5. 设置日志上下文
        set_session_id(ctx.conversation_id or execution_id)
        token = _request_ctx.set(ctx)
        try:
            response = await call_next(request)
            return response
        finally:
            _request_ctx.reset(token)
            set_session_id("default_trace_id")
