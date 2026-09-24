"""COM-08 §6.2: HTTP 双配置不变性矩阵（真实 handler + 真实异常 + 日志断言）。

直接调用 ``app.exception_handlers[ExcType]`` 真实闭包 handler（非重写），
用真实异常类型（RequestValidationError / HTTPException / AgentBuilderError /
StorageReadError / StorageConfigError / Exception）在两种 DiagnosticPolicy 下：
- 比较真实 Response status/headers/body 精确一致；
- 捕获日志，断言级别、次数、关联 ID、exc_info 不随 verbose 变化；
- 敏感哨兵不进响应也不进日志 message。
"""

from __future__ import annotations

import asyncio
import json
import logging

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from agent_runtime.common.exception.errors import AgentBuilderError, StatusCode
from agent_runtime.serve.server import app
from agent_runtime.error_contract import factory as ec_factory
from jiuwen.common.log.diagnostics import DiagnosticPolicy, set_default_policy
from storage.exceptions import StorageConfigError, StorageReadError


_REQ_ID = "req-com08-1"
_EXEC_ID = "exec-com08-1"
_SENTINEL = "SECRET-TOKEN-abc-123-sensitivedetail"


def _request_stub():
    from types import SimpleNamespace

    return SimpleNamespace(
        state=SimpleNamespace(request_id=_REQ_ID, execution_id=_EXEC_ID),
        headers={"x-language": "zh-cn"},
    )


def _call_handler(exc_type, exc):
    """真实调用注册 handler，并在捕获该异常的 except 上下文中执行，
    使 handler 内 ``logger.error(..., exc_info=True)`` 得到真实 traceback
    （而非 (None, None, None)）。"""
    req = _request_stub()
    handler = app.exception_handlers[exc_type]

    async def _go():
        try:
            raise exc
        except exc_type:
            return await handler(req, exc)

    return asyncio.run(_go())


def _resp_body(resp):
    return json.loads(resp.body)


def _with_policy(verbose: bool, fn):
    set_default_policy(DiagnosticPolicy(verbose=verbose))
    try:
        return fn()
    finally:
        set_default_policy(None)


# --- 真实异常构造 ------------------------------------------------------


def _validation_exc():
    return RequestValidationError(
        [{"loc": ("body", "x"), "msg": "field required", "type": "missing"}]
    )


def _http_404():
    return StarletteHTTPException(status_code=404, detail="not found")


def _http_405():
    return StarletteHTTPException(status_code=405, detail="method not allowed")


def _agent_builder_exc():
    return AgentBuilderError(
        StatusCode.AGENT_BUILDER_LLM_SERVICE_ERROR, msg=f"downstream {_SENTINEL}"
    )


def _storage_read_exc():
    return StorageReadError(f"read fail {_SENTINEL}")


def _storage_config_exc():
    return StorageConfigError(f"config fail {_SENTINEL}")


def _unknown_exc():
    return RuntimeError(f"unknown boom {_SENTINEL}")


# 真实异常 × handler 矩阵
SCENARIOS = [
    ("validation", RequestValidationError, _validation_exc),
    ("404", StarletteHTTPException, _http_404),
    ("405", StarletteHTTPException, _http_405),
    ("AgentBuilderError", AgentBuilderError, _agent_builder_exc),
    ("StorageReadError", StorageReadError, _storage_read_exc),
    ("StorageConfigError", StorageConfigError, _storage_config_exc),
    ("unknown", Exception, _unknown_exc),
]


# --- §6.2 响应双配置不变 ------------------------------------------------


@pytest.mark.parametrize("name,exc_type,exc_fn", SCENARIOS)
def test_http_response_two_configs_identical(name, exc_type, exc_fn):
    r_false = _with_policy(False, lambda: _call_handler(exc_type, exc_fn()))
    r_true = _with_policy(True, lambda: _call_handler(exc_type, exc_fn()))
    assert r_false.status_code == r_true.status_code
    assert r_false.headers.get("X-Request-Id") == r_true.headers.get("X-Request-Id")
    assert _resp_body(r_false) == _resp_body(r_true)


@pytest.mark.parametrize("name,exc_type,exc_fn", SCENARIOS)
def test_http_response_no_sentinel(name, exc_type, exc_fn):
    r = _with_policy(True, lambda: _call_handler(exc_type, exc_fn()))
    body_str = str(_resp_body(r))
    assert _SENTINEL not in body_str
    assert "SECRET-TOKEN" not in body_str


# --- §6.2 日志不变量（caplog）------------------------------------------


@pytest.mark.parametrize("name,exc_type,exc_fn", SCENARIOS)
def test_http_log_level_and_count_not_changed_by_verbose(
    caplog, name, exc_type, exc_fn
):
    """两配置下 ERROR 日志次数一致；verbose 不增减日志级别。"""
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    _with_policy(False, lambda: _call_handler(exc_type, exc_fn()))
    n_false = sum(1 for r in caplog.records if r.levelno >= logging.ERROR)
    caplog.clear()
    _with_policy(True, lambda: _call_handler(exc_type, exc_fn()))
    n_true = sum(1 for r in caplog.records if r.levelno >= logging.ERROR)
    assert n_false == n_true, f"{name}: ERROR count differs ({n_false} vs {n_true})"


_TERMINAL_SCENARIOS = [
    (n, e, f) for n, e, f in SCENARIOS
    if n in ("AgentBuilderError", "StorageReadError", "StorageConfigError", "unknown")
]


@pytest.mark.parametrize("name,exc_type,exc_fn", _TERMINAL_SCENARIOS)
def test_http_terminal_error_traceback_both_configs(caplog, name, exc_type, exc_fn):
    """最终责任边界（5xx）两配置均在真实异常上下文中保留有效 traceback。"""
    caplog.set_level(logging.ERROR)
    for verbose in (False, True):
        caplog.clear()
        exc = exc_fn()
        _with_policy(verbose, lambda: _call_handler(exc_type, exc))
        errs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(errs) == 1, f"{name} verbose={verbose}: ERROR 次数={len(errs)}，期望 1"
        rec = errs[-1]
        # 真实 traceback 元组（非 (None,None,None)）
        assert rec.exc_info is not None, f"{name} verbose={verbose}: exc_info 为 None"
        assert issubclass(rec.exc_info[0], exc_type), (
            f"{name} verbose={verbose}: exc_info[0]={rec.exc_info[0]} 不是 {exc_type} 子类"
        )
        assert rec.exc_info[1] is exc, f"{name} verbose={verbose}: exc_info[1] 不是原异常"
        assert rec.exc_info[2] is not None, f"{name} verbose={verbose}: traceback 为空"


@pytest.mark.parametrize("name,exc_type,exc_fn", _TERMINAL_SCENARIOS)
def test_http_log_message_no_sentinel(caplog, name, exc_type, exc_fn):
    """敏感哨兵不进日志 message（§3.2/§4.6）。

    注意：traceback（exc_info）按 §3.2 保留，可能含 str(exc)——属框架保留的
    异常栈，不与 message 混淆；本断言只检查 record.getMessage()。
    """
    caplog.set_level(logging.ERROR)
    _with_policy(True, lambda: _call_handler(exc_type, exc_fn()))
    errs = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errs, f"{name}: 无 ERROR"
    msg = errs[-1].getMessage()
    assert _SENTINEL not in msg
    assert "SECRET-TOKEN" not in msg


def test_http_log_single_error_not_duplicate(caplog):
    """§4.8: verbose=true 不增加第二条 ERROR（未知异常只记录一次）。"""
    caplog.set_level(logging.ERROR)
    caplog.clear()
    _with_policy(True, lambda: _call_handler(Exception, _unknown_exc()))
    errs = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errs) == 1, f"期望 1 条 ERROR，实际 {len(errs)}"


def test_http_cause_preserved_both_configs():
    """未知异常 cause 两配置都保留（descriptor.cause）。"""
    cause = RuntimeError("root")
    d_false = _with_policy(False, lambda: ec_factory.from_internal(cause, _REQ_ID))
    d_true = _with_policy(True, lambda: ec_factory.from_internal(cause, _REQ_ID))
    assert d_false.cause is cause
    assert d_true.cause is cause


# --- §6.2 i18n fail-closed --------------------------------------------


def test_http_i18n_fail_closed_two_configs_identical():
    """i18n 失败（message_key 无文案）→ fail-closed 硬编码安全响应，两配置一致。"""
    from agent_runtime.error_contract.descriptor import ErrorDescriptor

    d = ErrorDescriptor(
        error_code="openjiuwen.99999999",
        http_status=500,
        message_key="openjiuwen.99999999.bogus",
        reason_key="openjiuwen.99999999.bogus.reason",
        suggestion_key="openjiuwen.99999999.bogus.suggestion",
        request_id=_REQ_ID,
    )
    r_false = _with_policy(False, lambda: ec_factory.build_json_response(d, "zh_cn"))
    r_true = _with_policy(True, lambda: ec_factory.build_json_response(d, "zh_cn"))
    assert r_false.status_code == r_true.status_code
    assert r_false.headers.get("X-Request-Id") == r_true.headers.get("X-Request-Id")
    assert _resp_body(r_false) == _resp_body(r_true)
    body = _resp_body(r_false)
    # fail-closed：五字段非空，未用异常正文降级
    assert body.get("error_msg") and body.get("error_reason") and body.get("error_suggestion")
    assert body.get("request_id") == _REQ_ID
    assert _SENTINEL not in str(body)


# §5.1 已登记业务异常——真实入口等价覆盖
def test_http_registered_business_exception_via_real_entry(caplog):
    """已登记业务异常（JiuWenBaseException）经真实 generic Exception handler
    → from_internal → INTERNAL_ERROR。COM-03 §7.2 设计：未处理异常统一映射
    INTERNAL_ERROR，业务 code 为内部诊断、不进公开响应（§3.3）。
    false/true 分别证明：响应精确一致；各恰好一条 ERROR + 有效 traceback +
    稳定关联字段 + message 无业务正文/哨兵。
    """
    from jiuwen.common.exception.base import JiuWenBaseException
    from jiuwen.common.exception.status_code import StatusCode as SC

    caplog.set_level(logging.ERROR)
    snapshots = {}
    responses = {}
    for verbose in (False, True):
        business_exc = JiuWenBaseException(
            error_code=SC.WORKFLOW_EXCEPTION_END_ERROR.code,
            message=f"business detail {_SENTINEL}",
        )
        caplog.clear()
        responses[verbose] = _with_policy(verbose, lambda e=business_exc: _call_handler(Exception, e))
        snapshots[verbose] = [
            r for r in caplog.records if r.levelno >= logging.ERROR
        ]

    # 两配置响应一致；code=INTERNAL_ERROR（业务码不进公开响应，COM-03 §7.2）
    r_false, r_true = responses.get(False), responses.get(True)
    assert r_false is not None and r_true is not None
    assert r_false.status_code == r_true.status_code == 500
    assert _resp_body(r_false) == _resp_body(r_true)
    body = _resp_body(r_false)
    assert body["error_code"] == "openjiuwen.12100004"  # INTERNAL_ERROR
    assert body.get("error_msg") and body.get("error_reason") and body.get("error_suggestion")
    assert _SENTINEL not in str(body)

    # false/true 分别断言日志不变量
    for verbose, errs in snapshots.items():
        assert len(errs) == 1, f"verbose={verbose}: ERROR 次数={len(errs)}，期望 1"
        rec = errs[-1]
        assert rec.exc_info[1] is not None, f"verbose={verbose}: 缺原异常"
        assert rec.exc_info[2] is not None, f"verbose={verbose}: traceback 为空"
        assert rec.levelno == logging.ERROR
        # message 不含业务异常正文与哨兵
        assert _SENTINEL not in rec.getMessage()
        assert "business detail" not in rec.getMessage()
        # 关联字段稳定（execution_id/request_id）
        assert "exec-com08-1" in rec.getMessage()
        assert "req-com08-1" in rec.getMessage()
    # 两配置基础 message 一致（verbose 不改变基础事件）
    snap_false = snapshots.get(False)
    snap_true = snapshots.get(True)
    assert snap_false is not None and snap_true is not None
    assert snap_false[-1].getMessage() == snap_true[-1].getMessage()


def test_jiuwen_handler_105015_maps_to_12100006():
    """P5-R3 决策 A: server.py JiuWen handler 对 JiuWenBaseException(105015) → 12100006。

    非流式路径：run_blocking 抛 JiuWenBaseException(105015) → middleware
    except JiuWenBaseException: raise → server.py JiuWen handler（error_code==105015
    分支 → from_plugin_exception/build_json_response）。决策 A：105015 不发布 +
    sentinel 不泄漏 + status 422（12100006 http_status）。
    """
    from jiuwen.common.exception.base import JiuWenBaseException

    exc = JiuWenBaseException(error_code=105015, message=f"plugin {_SENTINEL}")
    r = _with_policy(True, lambda: _call_handler(JiuWenBaseException, exc))
    body = _resp_body(r)
    assert r.status_code == 422
    assert body["error_code"] == "openjiuwen.12100006"
    for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[f], f"{f} non-empty"
    # 决策 A: 105015 不外露 + sentinel 不泄漏
    assert _SENTINEL not in str(body)
    assert "105015" not in str(body)


def test_generic_handler_wrapped_105015_maps_to_12100006():
    """P5-R3a: server.py generic Exception handler 对 ExecutionError(cause=105015)
    → from_plugin_exception（认 __cause__ 链）→ 12100006。

    非流式路径：run_blocking re-raise 包装异常 → ir_execute 无 try →
    generic_error_handler 兜底。修复前 from_internal → 12100004（包装路径
    105015 达不到 12100006）。
    """
    from jiuwen.common.exception.base import JiuWenBaseException
    from openjiuwen.core.common.exception.codes import StatusCode as CoreStatusCode
    from openjiuwen.core.common.exception.errors import ExecutionError

    wrapped = ExecutionError(
        CoreStatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
        cause=JiuWenBaseException(error_code=105015, message=f"plugin {_SENTINEL}"))
    r = _with_policy(True, lambda: _call_handler(Exception, wrapped))
    body = _resp_body(r)
    assert r.status_code == 422  # 12100006 http_status（而非 12100004 的 500）
    assert body["error_code"] == "openjiuwen.12100006"
    for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[f], f"{f} non-empty"
    assert _SENTINEL not in str(body)
    assert "105015" not in str(body)


def test_generic_handler_non_105015_keeps_internal():
    """反证：generic handler 对普通未处理异常 → 仍 from_internal(12100004,500)。

    from_plugin_exception 改造不影响非 105015 兜底行为。
    """
    r = _with_policy(True, lambda: _call_handler(Exception, RuntimeError(f"x {_SENTINEL}")))
    body = _resp_body(r)
    assert r.status_code == 500
    assert body["error_code"] == "openjiuwen.12100004"
    assert _SENTINEL not in str(body)
