# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""COM-05: Builder 入站关联 ID 选值/校验/上下文构造/响应回写（纯函数，无副作用）。

SYNC-01 P3.3 从旧分支 debug_log_20260818 移植。Builder 契约：
- 只选 ``X-Request-Id`` + ``TraceID``，**不读取/不保存/不记录 ``X-Execution-Id``**
  （execution_id 是 Runtime 概念；Builder 平台 Header 白名单不含它）。
- Header 合法性：长度 1-64，字符集 ``[A-Za-z0-9._:-]``。
- ``trace_id`` 缺失/非法回退 ``request_id``，禁止用其他字段派生。

adapt：生成 ID 用 ``uuid.uuid4().hex``（32 位，与 P3.2 Runtime 一致）。
"""

import uuid

from agent_builder.adapter.request_context_bridge import RequestContext

X_REQUEST_ID = "x-request-id"
TRACE_ID_HEADER = "traceid"

_ALLOWED_HEADER_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
)


def valid_inbound_id(value: str | None) -> bool:
    """Header 关联 ID 合法性：非空、长度 1-64、字符集 [A-Za-z0-9._:-]。"""
    if not value or len(value) > 64:
        return False
    return frozenset(value) <= _ALLOWED_HEADER_CHARS


def select_ids(request_headers) -> tuple[str, str, bool, bool]:
    """从入站 Header 选定 (request_id, trace_id, illegal_req, illegal_trace)。

    - request_id = valid(X-Request-Id) ? 原值 : UUID4 hex；illegal_req = bool(原值非空但非法)
    - trace_id = valid(TraceID) ? 原值 : request_id（回退，禁止派生）
    """
    raw_req = request_headers.get(X_REQUEST_ID)
    if valid_inbound_id(raw_req):
        request_id, illegal_req = raw_req, False
    else:
        request_id, illegal_req = uuid.uuid4().hex, bool(raw_req)

    raw_trace = request_headers.get(TRACE_ID_HEADER)
    if valid_inbound_id(raw_trace):
        trace_id, illegal_trace = raw_trace, False
    else:
        trace_id, illegal_trace = request_id, bool(raw_trace)

    return request_id, trace_id, illegal_req, illegal_trace


def build_request_context(request_headers, customer_headers, request_id, source) -> RequestContext:
    """构造含 request_id 的 Builder RequestContext（平台 Header + 客户 Header 分仓）。"""
    ctx = RequestContext(request_id=request_id, source=source)
    apply_platform_headers(ctx, request_headers)
    ctx.customer_headers = customer_headers
    return ctx


def apply_platform_headers(ctx: RequestContext, request_headers) -> None:
    """将平台 Header 白名单直接写入 ctx.headers。纯读取，无副作用。

    白名单：X-Owner-Project-Id / X-Workspace-Id / X-Auth-Id / X-Auth-Token /
    X-Deployment-Id / x-language（回退 accept-language → "zh-cn"）。
    **不含 X-Execution-Id**（Builder 契约）。
    """
    def _h(name: str) -> str:
        return request_headers.get(name) or request_headers.get(name.lower(), "")

    ctx.headers = {
        "X-Owner-Project-Id": _h("X-Owner-Project-Id"),
        "X-Workspace-Id": _h("X-Workspace-Id"),
        "X-Auth-Id": _h("X-Auth-Id"),
        "X-Auth-Token": _h("X-Auth-Token"),
        "X-Deployment-Id": _h("X-Deployment-Id"),
        "x-language": _h("x-language") or _h("accept-language") or "zh-cn",
    }


def write_x_request_id(response, request_id: str) -> None:
    """将 X-Request-Id 写入响应 Header。外层挂载可能再写同值，但不得覆盖为不同值。"""
    response.headers["X-Request-Id"] = request_id
