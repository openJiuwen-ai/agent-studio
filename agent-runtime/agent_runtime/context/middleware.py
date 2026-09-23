#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
请求上下文中间件 — 在整个请求生命周期内管理 RequestContext

DEF-03（SYNC-01 P3.2 移植自旧分支 debug_log_20260818）：在可能写日志的请求
解析逻辑之前确定 request_id、trace_id、execution_id 并建立基础上下文；
trace_id 只来自合法 TraceID，缺失/非法时使用 request_id；finally 用 token
逆序 reset 恢复（不再 set_session_id("default_trace_id") 假清理）。

COM-05：conversation_id 按声明式路由来源矩阵解析（路径段 / 直接编排请求体 /
非会话留空），删除任意 JSON body 误绑定；路径与 body 冲突集中安全拒绝；
响应回写 X-Request-Id；未处理异常在 token 有效期内于 try 内收口（固定外层
关联字段由当前 ContextVar 注入），不再依赖外层 ServerErrorMiddleware。

SYNC-01 P3.2 adapt（2026-09-19）：
- 保留新分支 sync_01 独有能力：OTel span 注入（_to_otel_trace_id + NonRecordingSpan
  + otel_context.attach）、jiuwen request_ctx（set_x_request_id/execution_id）、
  IR 加载缓存（ir_load_cache）、客户 header 分仓（customer_headers）、env_variables
  占位、effective userId 配置覆盖。
- OTel trace_id 继续从 request_id 派生（D-A 决策 a：保留新 OTel 行为，业务
  trace_id 独立选值；两者映射可核查，不假定字面同）。
- error 收口（build_unhandled_error_response / _conflict_response）P5-R3
  （2026-09-21）已落地 COM-03 error_factory：build_unhandled_error_response
  → from_internal/build_json_response（openjiuwen.12100004 INTERNAL_ERROR 500），
  _conflict_response → from_request_conflict/build_json_response（12100001
  REQUEST_VALIDATION_FAILED 400）；均 canonical8 五字段 + X-Request-Id。P3.2
  时用裸 JSONResponse 延后（规划 L148 S3），P5-R3 升级完毕。

改造：
- capture cust-* header（白名单，不含 x-auth-token）
- ctx.customer_headers / ctx.platform_headers 独立分仓
- 配置启用 + cust-userid 非空 → 覆盖 ctx.user_id（effective userId）
"""

import hashlib
import json
import uuid

from agent_runtime.context.conversation_source import (
    SOURCE_BODY,
    SOURCE_PATH,
    resolve_conversation_source,
)
from agent_runtime.context.request_context import RequestContext, _request_ctx
from agent_runtime.serve.error_response import build_unhandled_error_response
from common_utils.customer_header import get_capture_keys, get_config
from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.log.base import set_x_execution_id, set_x_request_id
from jiuwen.serve.common.context import request_ctx as _jiuwen_request_ctx
from openjiuwen.core.common.logging import set_session_id, workflow_logger
try:
    from openjiuwen.core.common.logging import reset_session_id
except ImportError:
    # 兼容 agent-core 未合入 DEF-03：reset_session_id 不存在
    # set_session_id 旧版不返回 token → trace_token=None → reset 跳过（middleware 已检查 None）
    def reset_session_id(_token):
        pass
from opentelemetry import context as otel_context, trace as otel_trace
from opentelemetry.trace import SpanContext, TraceFlags, TraceState
from opentelemetry.trace.span import NonRecordingSpan
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

X_EXECUTION_ID = "x-execution-id"
X_REQUEST_ID = "x-request-id"
TRACE_ID_HEADER = "traceid"
DEFAULT_USER = "testUser"

_HEX_CHARS = set("0123456789abcdefABCDEF")

# Header 关联 ID 合法字符集（协议 §3.2：[A-Za-z0-9._:-]，长度 1-64）
_ALLOWED_HEADER_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
)


def _valid_header(value: str | None) -> bool:
    """Header 关联 ID 合法性：非空、长度 1-64、字符集 [A-Za-z0-9._:-]。"""
    if not value or len(value) > 64:
        return False
    return frozenset(value) <= _ALLOWED_HEADER_CHARS


def _to_otel_trace_id(trace_id_str: str) -> int:
    """Convert a string to a valid OTel 128-bit trace_id.

    OTel trace_id must be 32 hex chars (128-bit). If the input is already
    32 hex, use it directly; otherwise hash with md5 to get 32 hex chars.
    """
    if len(trace_id_str) == 32 and all(c in _HEX_CHARS for c in trace_id_str):
        val = int(trace_id_str, 16)
        if val != 0:
            return val
    return int(hashlib.md5(trace_id_str.encode()).hexdigest(), 16)


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


def _body_conversation_id(body_json: dict) -> str:
    """body 来源会话 ID 的类型守卫（复审 §2.2）。

    只接受非空字符串；数字/字典/列表/null 等无效类型一律返回空——
    不做 ``str()`` 强制转换，不得把业务对象内容带进统一日志槽位。
    无效输入由下游 Pydantic 模型产生参数错误。
    """
    value = body_json.get("conversationId")
    if isinstance(value, str) and value:
        return value
    return ""


def _conflict_response(request_id: str, language: str = "zh-cn") -> JSONResponse:
    """路径与请求体会话冲突的集中拒绝出口（400，不回显任何原值）。

    COM-03 §7.2 第 3 点：通过 descriptor/HTTP builder 构建，
    继续使用入口已选定 request ID。

    SYNC-01 P5-R3 落地（2026-09-21）：旧分支 COM-03 用 error_factory
    .from_request_conflict 构建 canonical8（REQUEST_VALIDATION_FAILED
    12100001）；sync_01 P3.2 时无 COM-03，用裸 400 JSONResponse 延后。
    P5-R3 升级为 canonical8 五字段。机制（不回显原值 + 入口 request_id）不变。
    """
    from agent_runtime.error_contract import factory as error_factory

    descriptor = error_factory.from_request_conflict(request_id)
    return error_factory.build_json_response(descriptor, language)


async def _read_delete_body_conversation_id(request: Request) -> str:
    """DELETE 会话来源路由的请求体读取（只取 conversationId 字段）。

    不读取 userId / secretEnvKeys——这两个字段的既有适用方法保持
    POST/PUT/PATCH 不变（规划 §3.4.7）。
    """
    try:
        body = await request.body()
        if not body:
            return ""
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            return _body_conversation_id(parsed)
    except Exception as e:  # JSON 解析边界，所有异常都需安全降级
        workflow_logger.warning(
            f"Failed to parse DELETE request body as JSON: {e}", exc_info=True
        )
    return ""


class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文中间件 — 在整个请求生命周期内管理 RequestContext"""

    async def dispatch(self, request: Request, call_next):
        """请求上下文唯一建立点。先选值、后 set、立即进 try、finally 逆序 reset。"""
        # 1. 读+校验三个 Header，记非法标志，缺失/非法生成替代值
        raw_exec = request.headers.get(X_EXECUTION_ID)
        if _valid_header(raw_exec):
            execution_id, illegal_exec = raw_exec, False
        else:
            execution_id, illegal_exec = uuid.uuid4().hex, bool(raw_exec)

        raw_req = request.headers.get(X_REQUEST_ID)
        if _valid_header(raw_req):
            request_id, illegal_req = raw_req, False
        else:
            request_id, illegal_req = uuid.uuid4().hex, bool(raw_req)

        raw_trace = request.headers.get(TRACE_ID_HEADER)
        if _valid_header(raw_trace):
            trace_id, illegal_trace = raw_trace, False
        else:
            # 缺失/非法以 request_id 回退，禁止派生
            trace_id, illegal_trace = request_id, bool(raw_trace)

        # 2. 构造基础 ctx + 同步写 request.state（sync_01 保留 ir_load_cache 占位）
        ctx = RequestContext(
            execution_id=execution_id,
            request_id=request_id,
            trace_id=trace_id,
            ir_load_cache={},
        )
        request.state.execution_id = execution_id
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        # 3. set ContextVar 集合进入 try：建立期任一 set 抛错（OTel attach / core
        # set_session_id 等）时，已得 token 由 finally 条件逆序恢复，不泄漏。
        # （DEF-03 §3.2：set 与 try 之间零操作——sets 本身即 try 的首段。）
        _jiuwen_ctx_token = None
        _otel_token = None
        request_token = None
        trace_token = None
        try:
            _jiuwen_ctx_token = _jiuwen_request_ctx.set({})
            set_x_request_id(request_id)
            set_x_execution_id(execution_id)
            # 注入 OTel 上下文，使 openjiuwen 创建的 span 继承业务关联 trace_id
            # （D-A：OTel trace 从 request_id 派生，业务 trace_id 独立选值）
            _otel_span_ctx = SpanContext(
                trace_id=_to_otel_trace_id(request_id),
                span_id=int(uuid.uuid4().hex[:16], 16),
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
                trace_state=TraceState(),
            )
            _otel_span = NonRecordingSpan(_otel_span_ctx)
            _otel_token = otel_context.attach(otel_trace.set_span_in_context(_otel_span))
            request_token = _request_ctx.set(ctx)
            trace_token = set_session_id(trace_id)

            # 非法 Header 告警（含替代 ID，不含非法原值）
            if illegal_exec:
                workflow_logger.warning(
                    f"header {X_EXECUTION_ID} is illegal; "
                    f"regenerated execution_id={execution_id}"
                )
            if illegal_req:
                workflow_logger.warning(
                    f"header {X_REQUEST_ID} is illegal; "
                    f"regenerated request_id={request_id}"
                )
            if illegal_trace:
                workflow_logger.warning(
                    f"header TraceID is illegal; fell back to trace_id={trace_id}"
                )

            # COM-05: 会话来源声明式匹配（只需 method+path，先于 body 读取）
            source, path_cid = resolve_conversation_source(
                request.method, request.url.path
            )

            # 读取请求体
            body = None
            if request.method in ("POST", "PUT", "PATCH"):
                body = await request.body()

            # 捕获平台 header 和客户 header
            platform_headers = _capture_platform_headers(request)
            customer_headers = _capture_customer_headers(request)
            ctx.headers = {
                "X-Auth-Token": platform_headers.get("X-Auth-Token", ""),
                "Cookie": platform_headers.get("Cookie", ""),
                "x-language": platform_headers.get("x-language", ""),
                "accept-language": platform_headers.get("accept-language", ""),
            }
            ctx.customer_headers = customer_headers
            ctx.platform_headers = platform_headers

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

            # 请求体 JSON 解析：只保留 userId / secretEnvKeys（POST/PUT/PATCH
            # 既有语义）；conversationId 全局误绑定已删除，改由下方来源矩阵解析
            body_json = None
            if body:
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict):
                        body_json = parsed
                        if not ctx.user_id:
                            ctx.user_id = body_json.get("userId", DEFAULT_USER)
                        params = body_json.get("params") or {}
                        ctx.secret_env_keys = params.get("secretEnvKeys", [])
                except Exception as e:  # JSON 解析边界
                    workflow_logger.warning(
                        f"Failed to parse request body as JSON: {e}", exc_info=True
                    )

            # COM-05: 会话来源矩阵解析（无值也显式写空，避免读取旧属性）
            if source == SOURCE_PATH:
                # 兼容请求体冲突（复审 §3.1 冻结矩阵）：
                #   键缺失                          → 用路径值
                #   字符串且等于路径值              → 用路径值
                #   字符串但与路径值不同            → 400
                #   键存在但值非字符串（含 null）   → 400
                if body_json is not None and \
                        "conversationId" in body_json:
                    body_value = body_json["conversationId"]
                    if not isinstance(body_value, str) or body_value != path_cid:
                        return _conflict_response(request_id, request.headers.get("x-language", "zh-cn") if request else "zh-cn")
                conversation_id = path_cid
            elif source == SOURCE_BODY:
                if body_json is not None:
                    conversation_id = _body_conversation_id(body_json)
                elif request.method == "DELETE":
                    # DELETE body 来源单独读取，只取会话字段（§3.4.7）
                    conversation_id = await _read_delete_body_conversation_id(request)
                else:
                    conversation_id = ""
            else:
                conversation_id = ""
            ctx.conversation_id = conversation_id
            request.state.conversation_id = conversation_id

            # 配置启用时，覆盖 effective userId
            cfg = get_config()
            if cfg.enabled:
                cust_userid = ctx.customer_headers.get("cust-userid")
                if cust_userid:
                    ctx.user_id = cust_userid

            response = await call_next(request)
            # COM-05: 响应回写本次 X-Request-Id（成功/404/校验/业务响应统一）
            response.headers[X_REQUEST_ID] = request_id
            return response
        except JiuWenBaseException:
            # 框架业务异常透传至 server.py 的 i18n handler（保 error_code），
            # 不在此收口——其响应契约由 server.py JiuWenBaseException handler 处理。
            # finally 仍逆序 reset；handler 读 request.state（非 ContextVar）不受影响。
            raise
        except Exception as exc:  # 请求级异常边界，需收口全部未处理异常
            # COM-05: token 有效期内收口未处理异常——固定外层关联字段由当前
            # ContextVar 注入（而非仅拼进 message）；finally 仍逆序 reset
            err_response = build_unhandled_error_response(request, exc)
            err_response.headers[X_REQUEST_ID] = request_id
            return err_response
        finally:
            # LIFO 逆序、条件 reset：建立期任一 set 抛错时，已得 token 仍尝试恢复
            # （token 为 None 表示该层未建立，跳过）；恢复期任一 reset 抛错时，嵌套
            # try/finally 保证其余 reset 仍被尝试。reset 异常不吞，异常链 Python 保留。
            try:
                if trace_token is not None:
                    reset_session_id(trace_token)
            finally:
                try:
                    if request_token is not None:
                        _request_ctx.reset(request_token)
                finally:
                    try:
                        if _otel_token is not None:
                            otel_context.detach(_otel_token)
                    finally:
                        if _jiuwen_ctx_token is not None:
                            _jiuwen_request_ctx.reset(_jiuwen_ctx_token)
