"""COM-03 §4.3: Builder 异常分类器 + descriptor 工厂。

只执行一次分类，输出 ErrorDescriptor。HTTP/SSE 构建器不再选码。
request_id 只读请求上下文（COM-05 establish_inbound_context 设置的
request.state.request_id / _request_ctx），不在异常处理器生成。
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Optional, Tuple

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.common.error_contract import catalog
from agent_builder.common.error_contract.descriptor import ErrorDescriptor, ErrorDetail
from agent_builder.common.error_contract.http_builder import (
    HttpResponseSpec,
    I18nResolver,
    build_http_response,
)

_UNKNOWN_REQUEST_ID = "unknown"

_BUILDER_I18N_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "i18n",
))

#: Builder 全局 i18n 解析器（.properties，zh_cn/en_us 三段安全文案）
builder_i18n_resolver = I18nResolver(
    _BUILDER_I18N_DIR,
    {"zh_cn": "messages_zh_CN.properties", "en_us": "messages_en_US.properties"},
)


def normalize_locale(language: Optional[str]) -> str:
    """将请求头 x-language（如 zh-cn / en-us）规范化为 i18n locale 键。"""
    lang = (language or "").strip().lower().replace("-", "_")
    if lang.startswith("en"):
        return "en_us"
    return "zh_cn"

  # pylint: disable=huawei-too-many-arguments  # noqa


def _build(defn, request_id: str, safe_details=None, cause=None,
           downstream_service=None, downstream_error_code=None) -> ErrorDescriptor:
    return ErrorDescriptor(
        error_code=defn.error_code,
        http_status=defn.http_status,
        message_key=defn.message_key,
        reason_key=defn.reason_key,
        suggestion_key=defn.suggestion_key,
        request_id=request_id or _UNKNOWN_REQUEST_ID,
        safe_details=safe_details,
        downstream_service=downstream_service,
        downstream_error_code=downstream_error_code,
        cause=cause,
    )


def _rid(request_id: Optional[str]) -> str:
    return request_id if request_id else _UNKNOWN_REQUEST_ID


def from_validation(exc: RequestValidationError, request_id: Optional[str]) -> ErrorDescriptor:
    """框架校验 → 参数校验定义 + allowlist details。"""
    defn = catalog.REQUEST_VALIDATION_FAILED
    details = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", []))
        msg = err.get("msg", "")
        details.append(ErrorDetail(
            error_code=defn.error_code,
            error_msg=f"{loc}: {msg}" if loc else msg,
        ))
    return _build(defn, _rid(request_id), safe_details=details, cause=exc)


def from_pydantic_validation(exc, request_id: Optional[str]) -> ErrorDescriptor:
    """pydantic ValidationError（Flask 路径）→ 参数校验定义 + allowlist details。

    pydantic 的 ``err["loc"]`` 元素可能非字符串（索引），按 Flask 装饰器
    原有格式拼接。
    """
    defn = catalog.REQUEST_VALIDATION_FAILED
    details = []
    for i in exc.errors():
        loc = "".join(
            ("." + seg) if isinstance(seg, str) else f"[{seg}]"
            for seg in i.get("loc", [])
        ).lstrip(".")
        details.append(ErrorDetail(
            error_code=defn.error_code,
            error_msg=f"{loc}: {i.get('msg', '')}" if loc else i.get("msg", ""),
        ))
    return _build(defn, _rid(request_id), safe_details=details, cause=exc)


def from_route_not_found(request_id: Optional[str], exc: Optional[Exception] = None) -> ErrorDescriptor:
    """404 → 路由不存在。"""
    return _build(catalog.ROUTE_NOT_FOUND, _rid(request_id), cause=exc)


def from_method_not_allowed(request_id: Optional[str], exc: Optional[Exception] = None) -> ErrorDescriptor:
    """405 → 方法不被允许。"""
    return _build(catalog.METHOD_NOT_ALLOWED, _rid(request_id), cause=exc)


def from_downstream_model(exc: Exception, request_id: Optional[str]) -> ErrorDescriptor:
    """下游模型服务失败（502）。

    COM-03 阶段不解析/回显下游原始错误码与 body；精细映射由
    DEF-08/09 接入。
    """
    return _build(catalog.DOWNSTREAM_MODEL_FAILED, _rid(request_id),
                  downstream_service="external", cause=exc)


def from_internal(exc: Exception, request_id: Optional[str]) -> ErrorDescriptor:
    """未知/已知业务异常 → Builder 安全内部错误定义 + cause。

    JiuWenException 等携带 legacy 业务码的已知异常在最小目录阶段统一
    映射为 INTERNAL_ERROR(500)；业务码只进日志，route 直返迁移归 COM-06。
    """
    return _build(catalog.INTERNAL_ERROR, _rid(request_id), cause=exc)


def from_builder_exception(exc, request_id: Optional[str]) -> ErrorDescriptor:
    """DEF-06: Builder 业务异常分类入口（受控 canonical 迁移）。

    携带 legacy 业务码的 ``JiuWenBaseException`` 经 ``lookup_business_definition``
    映射到 Builder 专属 canonical 定义（``openjiuwen.13100006~13``）输出——不是
    verbatim 保留 legacy 整数码，而是受控重编号（用户已批准的契约迁移）。未登记、
    ``-1``、空值、布尔、对象、动态供应商码及语义冲突码一律回退到
    ``from_internal()``（INTERNAL_ERROR 500）。``cause`` 只供内部日志诊断，
    不进入 HTTP body、``details`` 或 SSE。
    """
    raw = getattr(exc, "error_code", "")
    # Type gate (§4.1.4): bool is an int subclass—reject it first; only int/str
    # may proceed to the string lookup. An arbitrary object whose __str__ returns
    # a registered code must NOT pass (spoof guard).
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        return from_internal(exc, request_id)
    legacy_code = str(raw)
    definition = catalog.lookup_business_definition(legacy_code)
    if definition is None:
        return from_internal(exc, request_id)
    return _build(definition, _rid(request_id), cause=exc)


def from_http_exception(exc: HTTPException, request_id: Optional[str]) -> ErrorDescriptor:
    """HTTPException 统一 adapter：404/405/4xx/5xx 分别映射。"""
    return from_http_status(exc.status_code, request_id, exc)


def from_http_status(status: int, request_id: Optional[str],
                     exc: Optional[Exception] = None) -> ErrorDescriptor:
    """按原始 HTTP 状态码映射（Flask werkzeug 的 ``exc.code`` 等场景）。"""
    if status == 404:
        return from_route_not_found(request_id, exc)
    if status == 405:
        return from_method_not_allowed(request_id, exc)
    if 400 <= status < 500:
        d = _build(catalog.REQUEST_VALIDATION_FAILED, _rid(request_id), cause=exc)
        return replace(d, http_status=status)  # 保留原状态码（422/401/403/429 等，不压平为 400）
    return from_internal(exc or _StatusOnlyError(status), request_id)


class _StatusOnlyError(Exception):
    """无原始异常时的占位 cause（不携带对外文本）。"""

    def __init__(self, status: int):
        super().__init__(f"http_status={status}")


def _response_headers(descriptor: ErrorDescriptor) -> dict[str, str]:
    return {"X-Request-Id": descriptor.request_id}


def build_json_response(descriptor: ErrorDescriptor, language: Optional[str]) -> JSONResponse:
    """descriptor + locale → FastAPI JSONResponse（COM-03 标准 HTTP 构建器输出）。

    COM-03 §4: fail-closed——i18n 解析失败时返回硬编码完整安全响应。
    """
    try:
        spec: HttpResponseSpec = build_http_response(
            descriptor, normalize_locale(language), builder_i18n_resolver)
        return JSONResponse(
            status_code=spec.status, content=spec.body, headers=_response_headers(descriptor))
    except ValueError:
        return JSONResponse(
            status_code=descriptor.http_status,
            content={
                "error_code": descriptor.error_code,
                "error_msg": "Internal server error.",
                "error_reason": "An internal error occurred while processing the request.",
                "error_suggestion": "Please retry later; contact support if the issue persists.",
                "request_id": descriptor.request_id,
            },
            headers=_response_headers(descriptor))


def build_flask_error(descriptor: ErrorDescriptor, language: Optional[str]) -> Tuple[dict, int, dict]:
    """descriptor + locale → Flask 错误三元组 ``(body, status, headers)``。

    COM-03 §4: fail-closed——i18n 解析失败时返回硬编码完整安全响应。
    """
    try:
        spec: HttpResponseSpec = build_http_response(
            descriptor, normalize_locale(language), builder_i18n_resolver)
        return spec.body, spec.status, _response_headers(descriptor)
    except ValueError:
        return ({
            "error_code": descriptor.error_code,
            "error_msg": "Internal server error.",
            "error_reason": "An internal error occurred while processing the request.",
            "error_suggestion": "Please retry later; contact support if the issue persists.",
            "request_id": descriptor.request_id,
        }, descriptor.http_status, _response_headers(descriptor))


def build_sse_error_event(
    request_id: Optional[str],
    exc: Exception,
    language: Optional[str],
    guard=None,
) -> Optional[str]:
    """COM-03 §6.2 + COM-07A §4.2: 生产可调用的 SSE error 构建函数（含 guard
    唯一终态控制与异常类型分流）。

    供 N2L/LLM streaming SSE 出口调用：guard 原子抢占终态,只有赢家产出 SSE
    error 帧；失败者返回 None。产出经 ``build_sse_error_envelope`` 构建。

    异常分类：已登记 ``JiuWenBaseException`` 走 DEF-06
    ``from_builder_exception()`` canonical 映射（未登记 code / -1 / 非法类型
    在该函数内安全回退 ``from_internal``），普通异常直接走 ``from_internal``。
    N2L 不按数值重选码,不在本函数解析下游 body。
    """
    from agent_builder.common.error_contract.sse_builder import (
        build_sse_error_envelope,
        format_sse_event,
    )

    if guard is not None and not guard.try_send_error():
        return None
    descriptor = (
        from_builder_exception(exc, request_id)
        if isinstance(exc, JiuWenBaseException)
        else from_internal(exc, request_id)
    )
    try:
        envelope = build_sse_error_envelope(
            descriptor, normalize_locale(language), builder_i18n_resolver)
        return format_sse_event(envelope)
    except ValueError:
        envelope = {
            "event": "error",
            "data": {
                "error_code": descriptor.error_code,
                "error_msg": "Internal server error.",
                "error_reason": "An internal error occurred while processing the request.",
                "error_suggestion": "Please retry later; contact support if the issue persists.",
                "request_id": descriptor.request_id,
            },
        }
        return format_sse_event(envelope)
