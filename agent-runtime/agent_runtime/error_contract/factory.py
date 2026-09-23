"""COM-03 §4.3: Runtime 异常分类器 + descriptor 工厂。

只执行一次分类，输出 ErrorDescriptor。HTTP/SSE 构建器不再选码。
request_id 只读请求上下文（COM-05 RequestContextMiddleware 设置的
request.state.request_id），不在异常处理器生成。
"""

from __future__ import annotations

import os
from typing import Optional

from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agent_runtime.error_contract import catalog
from agent_runtime.error_contract.descriptor import ErrorDescriptor, ErrorDetail
from agent_runtime.error_contract.http_builder import (
    I18nResolver,
    HttpResponseSpec,
    build_http_response,
)

_UNKNOWN_REQUEST_ID = "unknown"

_RUNTIME_I18N_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "event_handler", "base", "resources", "i18n",
))

#: Runtime 全局 i18n 解析器（.properties，zh_cn/en_us 三段安全文案）
runtime_i18n_resolver = I18nResolver(
    _RUNTIME_I18N_DIR,
    {"zh_cn": "runtime-msg_zh_CN.properties", "en_us": "runtime-msg_en_US.properties"},
)


def normalize_locale(language: Optional[str]) -> str:
    """将请求头 x-language（如 zh-cn / en-us）规范化为 i18n locale 键。"""
    lang = (language or "").strip().lower().replace("-", "_")
    if lang.startswith("en"):
        return "en_us"
    return "zh_cn"


def _build(defn, request_id: str, safe_details=None, cause=None,
           downstream_service=None, downstream_error_code=None) -> ErrorDescriptor:  # noqa: G.FNM.03 - ErrorDescriptor 构造参数，具名封装过度
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


def from_route_not_found(request_id: Optional[str], exc: Optional[Exception] = None) -> ErrorDescriptor:
    """404 → 路由不存在。"""
    return _build(catalog.ROUTE_NOT_FOUND, _rid(request_id), cause=exc)


def from_request_conflict(request_id: Optional[str]) -> ErrorDescriptor:
    """会话冲突（路径 vs body）→ 参数校验定义（400，不回显任何原值）。

    供 ``RequestContextMiddleware._conflict_response`` 使用；
    具体冲突值只进日志，不进 descriptor。
    """
    return _build(catalog.REQUEST_VALIDATION_FAILED, _rid(request_id))


def from_method_not_allowed(request_id: Optional[str], exc: Optional[Exception] = None) -> ErrorDescriptor:
    """405 → 方法不被允许。"""
    return _build(catalog.METHOD_NOT_ALLOWED, _rid(request_id), cause=exc)


def from_downstream_builder(exc: Exception, request_id: Optional[str]) -> ErrorDescriptor:
    """下游 Builder 调用失败（502）。

    COM-03 阶段不解析/回显下游原始错误码与 body；精细沿用规则由
    COM-04 响应单元接入（downstream_* 字段保留内部诊断能力）。
    """
    return _build(catalog.DOWNSTREAM_BUILDER_FAILED, _rid(request_id),
                  downstream_service="builder", cause=exc)


def from_internal(exc: Exception, request_id: Optional[str]) -> ErrorDescriptor:
    """未知/存储异常 → Runtime 安全内部错误定义 + cause。"""
    return _build(catalog.INTERNAL_ERROR, _rid(request_id), cause=exc)


#: 插件响应格式错误的内部错误码（sync_01 `960dbf23` 引入，未发布；
#: 决策 A 不对外发布该码，raise 端保留作内部诊断）
_PLUGIN_RESPONSE_FORMAT_ERROR_CODE = 105015


def is_plugin_response_format_error(exc: BaseException) -> bool:
    """判定异常（直接或 ``__cause__`` 链）是否为插件响应格式错误（105015）。

    SYNC-01 P5-R3a：openjiuwen 引擎（graph/vertex.py）在节点能力执行期把
    Exception（含 vendored jiuwen ``JiuWenBaseException(105015)``——它是
    Exception 子类而非 BaseError 子类，不走 vertex 的 ``except BaseError``
    再抛路径）包成 ``ExecutionError/BaseError(cause=原异常)``（BaseError
    ``__init__`` 显式 ``self.__cause__ = cause``）。因此判定必须覆盖：

    - 直接异常 ``error_code == 105015``（含 bpmn_workflow._process_exception
      包出的 plain JiuWenBaseException，基类 property 保留 .error_code）；
    - 包装异常的 ``__cause__`` 链（ExecutionError.__cause__ / BaseError
      ``__cause__`` / 多层 cause）。

    非 105015（直接与 cause 链全部非 105015）返回 False，调用方保持既有行为。
    duck-typing，不导入 jiuwen/openjiuwen（避免层耦合）。
    """
    if getattr(exc, "error_code", None) == _PLUGIN_RESPONSE_FORMAT_ERROR_CODE:
        return True
    cause = getattr(exc, "__cause__", None)
    # 循环检测：__cause__ 链自引用/互引用（编程错误或反序列化）会导致无限循环，
    # visited id 集合在命中已访问对象时终止（adversarial-reviewer P5-R3a gap）。
    visited = {id(exc)}
    while cause is not None:
        if id(cause) in visited:
            return False
        visited.add(id(cause))
        if getattr(cause, "error_code", None) == _PLUGIN_RESPONSE_FORMAT_ERROR_CODE:
            return True
        cause = getattr(cause, "__cause__", None)
    return False


def from_plugin_exception(exc: Exception, request_id: Optional[str]) -> ErrorDescriptor:
    """插件层异常 → COM-03 descriptor（SYNC-01 P5-R3 Phase 3 决策 A）。

    sync_01 105015(PLUGIN_RESPONSE_FORMAT_ERROR)未发布 → 替换为 canonical
    ``openjiuwen.12100006``。raise 端（jiuwen/plugin）保留 105015（``exc.code``）
    作内部诊断；catch 端（agent_runtime）调用本函数：直接或 ``__cause__`` 链
    携带 ``error_code == 105015``（P5-R3a：覆盖 openjiuwen vertex 包装成
    ExecutionError/BaseError 的路径）映射到 catalog
    ``PLUGIN_RESPONSE_FORMAT_FAILED``，其余回退 ``from_internal``。

    注：bpmn_workflow._process_exception 把 PluginCommonException 包成 plain
    JiuWenBaseException（保留 .error_code，但 .code 是 PluginCommonException 子类
    property 丢失）→ 用 .error_code（JiuWenBaseException 基类 property）识别，
    而非 .code。不导入 jiuwen（避免层耦合），duck-typing。
    """
    if is_plugin_response_format_error(exc):
        return _build(
            catalog.PLUGIN_RESPONSE_FORMAT_FAILED, _rid(request_id), cause=exc)
    return from_internal(exc, request_id)


def from_http_exception(exc: HTTPException, request_id: Optional[str]) -> ErrorDescriptor:
    """HTTPException 统一 adapter：404/405/4xx/5xx 分别映射。"""
    status = exc.status_code
    if status == 404:
        return from_route_not_found(request_id, exc)
    if status == 405:
        return from_method_not_allowed(request_id, exc)
    if 400 <= status < 500:
        return _build(catalog.REQUEST_VALIDATION_FAILED, _rid(request_id), cause=exc)
    return from_internal(exc, request_id)


def build_json_response(descriptor: ErrorDescriptor, language: Optional[str]) -> JSONResponse:
    """descriptor + locale → FastAPI JSONResponse（COM-03 标准 HTTP 构建器输出）。

    COM-03 §4: fail-closed——i18n 解析失败时返回硬编码完整安全响应
    （五字段非空），不以空串降级。
    """
    try:
        spec: HttpResponseSpec = build_http_response(
            descriptor, normalize_locale(language), runtime_i18n_resolver)
        return JSONResponse(status_code=spec.status, content=spec.body,
                            headers={"X-Request-Id": descriptor.request_id})
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
            headers={"X-Request-Id": descriptor.request_id})


def build_sse_error_event(
    request_id: Optional[str],
    exc: Exception,
    language: Optional[str],
    guard=None,
) -> Optional[str]:
    """COM-03 §6.2: 生产可调用的 SSE error 构建函数（含 guard 唯一终态控制）。

    供 runner/controller SSE 出口调用：guard 原子抢占终态,只有赢家产出 SSE
    error 帧；失败者返回 None。产出经 ``build_sse_error_envelope`` 构建,
    不手构 JSON。
    """
    from agent_runtime.error_contract.sse_builder import (
        build_sse_error_envelope,
        format_sse_event,
    )

    if guard is not None and not guard.try_send_error():
        return None
    # SYNC-01 P5-R3 Phase 3 决策 A: 插件异常(105015)→12100006,其余→from_internal(12100004)
    descriptor = from_plugin_exception(exc, request_id)
    try:
        envelope = build_sse_error_envelope(
            descriptor, normalize_locale(language), runtime_i18n_resolver)
        return format_sse_event(envelope)
    except ValueError:
        # COM-03 §4: i18n fail-closed — 硬编码安全 SSE envelope（五字段非空）
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
