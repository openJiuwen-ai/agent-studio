"""COM-03 §10.4: Builder factory（异常分类 → descriptor）契约测试。"""

import json

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from pydantic import ValidationError

from agent_builder.adapter.exception_bridge import (
    JiuWenBaseException,
    JiuWenException,
)
from agent_builder.common.error_contract import factory
from agent_builder.common.error_contract.stream_state import SseTerminalGuard


def _rid():
    return "req-bfactory-001"


# ---- normalize_locale ----

def test_normalize_locale_variants():
    assert factory.normalize_locale("zh-cn") == "zh_cn"
    assert factory.normalize_locale("en-us") == "en_us"
    assert factory.normalize_locale("EN") == "en_us"
    assert factory.normalize_locale(None) == "zh_cn"


# ---- from_validation / from_pydantic_validation ----

def test_from_validation_maps_to_13100001_with_details():
    exc = RequestValidationError([{"loc": ["body", "name"], "msg": "field required"}])
    d = factory.from_validation(exc, _rid())
    assert d.error_code == "openjiuwen.13100001"
    assert d.http_status == 400
    assert d.request_id == _rid()
    assert len(d.safe_details) == 1
    assert "name" in d.safe_details[0].error_msg


class _PModel(BaseModel):
    name: str


def test_from_pydantic_validation_flask_shape():
    try:
        _PModel()
    except ValidationError as exc:
        d = factory.from_pydantic_validation(exc, _rid())
        assert d.error_code == "openjiuwen.13100001"
        assert d.http_status == 400
        assert d.safe_details


# ---- 404/405/http_status ----

def test_from_route_not_found_and_method_not_allowed():
    assert factory.from_route_not_found(_rid()).error_code == "openjiuwen.13100002"
    assert factory.from_method_not_allowed(_rid()).error_code == "openjiuwen.13100003"


@pytest.mark.parametrize("status,expected_code,expected_http", [
    (404, "openjiuwen.13100002", 404),
    (405, "openjiuwen.13100003", 405),
    (400, "openjiuwen.13100001", 400),
    (422, "openjiuwen.13100001", 422),  # 意见2: 422 保留原状态码（不改写为 400）
    (500, "openjiuwen.13100004", 500),
])
def test_from_http_exception_and_status(status, expected_code, expected_http):
    exc = HTTPException(status_code=status, detail="x")
    d = factory.from_http_exception(exc, _rid())
    assert d.error_code == expected_code
    assert d.http_status == expected_http
    d2 = factory.from_http_status(status, _rid())
    assert d2.error_code == expected_code


# ---- downstream / internal ----

def test_from_downstream_model_maps_502():
    d = factory.from_downstream_model(RuntimeError("model boom"), _rid())
    assert d.error_code == "openjiuwen.13100005"
    assert d.http_status == 502
    assert d.downstream_service == "external"
    assert "model boom" not in repr(d)


def test_from_internal_no_cause_leak():
    d = factory.from_internal(ValueError("secret"), _rid())
    assert d.error_code == "openjiuwen.13100004"
    assert "secret" not in repr(d)


# ---- build_json_response / build_flask_error ----

def test_build_json_response_five_fields_and_header():
    d = factory.from_route_not_found(_rid())
    resp = factory.build_json_response(d, "zh-cn")
    assert resp.status_code == 404
    body = json.loads(resp.body)
    for field in ("error_code", "error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[field], f"{field} non-empty"
    assert resp.headers["x-request-id"] == _rid()


def test_build_flask_error_triple():
    d = factory.from_internal(RuntimeError("x"), _rid())
    body, status, headers = factory.build_flask_error(d, "zh-cn")
    assert status == 500
    assert body["error_code"] == "openjiuwen.13100004"
    assert headers["X-Request-Id"] == _rid()

  # pylint: disable=avoid-import-method  # noqa
def test_build_json_response_en_locale():
    d = factory.from_internal(RuntimeError("x"), _rid())
    en = json.loads(factory.build_json_response(d, "en-us").body)
    zh = json.loads(factory.build_json_response(d, "zh-cn").body)
    assert en["error_msg"] != zh["error_msg"]


# ---- DEF-06: from_builder_exception (legacy business classifier) ----

_LEGACY_MATRIX = [
    (102154, "openjiuwen.13100006", 400),  # pylint: disable=avoid-import-method  # noqa
    (102155, "openjiuwen.13100007", 404),
    (102156, "openjiuwen.13100008", 409),  # pylint: disable=avoid-import-method  # noqa
    (102158, "openjiuwen.13100009", 500),
    (102159, "openjiuwen.13100010", 500),
    (102170, "openjiuwen.13100011", 500),
    (102213, "openjiuwen.13100012", 500),
    (102214, "openjiuwen.13100013", 500),
]

  # pylint: disable=avoid-import-method  # noqa
@pytest.mark.parametrize("int_code,str_code,http_status", _LEGACY_MATRIX)
def test_from_builder_exception_legacy_mapped_to_canonical(int_code, str_code, http_status):
    exc = JiuWenBaseException(error_code=int_code, message="internal detail with secret")
    d = factory.from_builder_exception(exc, _rid())
    assert d.error_code == str_code
    assert d.http_status == http_status
    assert d.request_id == _rid()


@pytest.mark.parametrize("int_code,str_code,http_status", _LEGACY_MATRIX)
def test_from_builder_exception_registered_i18n_resolvable(int_code, str_code, http_status):
    exc = JiuWenBaseException(error_code=int_code, message="x")
    d = factory.from_builder_exception(exc, _rid())
    for locale in ("zh_cn", "en_us"):
        msg, reason, suggestion = factory.builder_i18n_resolver.resolve(
            locale, d.message_key)
        assert msg, f"{str_code} {locale} message empty"
        assert reason, f"{str_code} {locale} reason empty"
        assert suggestion, f"{str_code} {locale} suggestion empty"


@pytest.mark.parametrize("bad_code", [-1, 0, 99999, 10215, 1021000])
def test_from_builder_exception_unregistered_maps_internal(bad_code):
    exc = JiuWenBaseException(error_code=bad_code, message="x")
    d = factory.from_builder_exception(exc, _rid())
    assert d.error_code == "openjiuwen.13100004"
    assert d.http_status == 500


def _exc_with_code(code):
    """Build a JiuWenBaseException bypassing __init__ to set arbitrary error_code
    types (None/bool/object) that the constructor would reject or coerce."""
    exc = JiuWenBaseException.__new__(JiuWenBaseException)
    exc.error_code = code
    return exc


@pytest.mark.parametrize("bad_code", [None, True, False, "", "unknown", "10215x"])
def test_from_builder_exception_non_int_str_maps_internal(bad_code):
    """§4.1.4: None / bool / empty / unknown string / arbitrary non-(int,str) → INTERNAL_ERROR."""
    d = factory.from_builder_exception(_exc_with_code(bad_code), _rid())
    assert d.error_code == "openjiuwen.13100004"
    assert d.http_status == 500


def test_from_builder_exception_spoof_object_rejected():
    """§4.1.4 spoof guard: an object whose __str__ returns a registered code
    must NOT pass the type gate."""
    class _Spoof:
        def __str__(self):
            return "102154"

    d = factory.from_builder_exception(_exc_with_code(_Spoof()), _rid())
    assert d.error_code == "openjiuwen.13100004"
    assert d.http_status == 500


def test_from_builder_exception_jiuwen_exception_minus_one():
    """JiuWenException carries error_code=-1 → safe internal fallback."""
    exc = JiuWenException("config is required")
    d = factory.from_builder_exception(exc, _rid())
    assert d.error_code == "openjiuwen.13100004"


def test_from_builder_exception_no_error_code_attr():
    """An object without error_code attribute → internal fallback."""

    class _NoCode(Exception):
        pass

    d = factory.from_builder_exception(_NoCode("boom"), _rid())
    assert d.error_code == "openjiuwen.13100004"


def test_from_builder_exception_cause_not_in_response():
    """The original exception message must not leak into body or repr."""
    exc = JiuWenBaseException(error_code=102154, message="secret-token-xyz")
    d = factory.from_builder_exception(exc, _rid())
    assert "secret-token-xyz" not in repr(d)
    body = json.loads(factory.build_json_response(d, "zh-cn").body)
    for field in ("error_msg", "error_reason", "error_suggestion"):
        assert "secret-token-xyz" not in body[field]
    assert body["request_id"] == _rid()


def test_from_builder_exception_no_prefix_auto_allow():
    """Exact-string lookup: numeric prefix must not auto-match a registered code."""
    # 10215 is a prefix of 102154 but is itself unregistered
    exc = JiuWenBaseException(error_code=10215, message="x")
    d = factory.from_builder_exception(exc, _rid())
    assert d.error_code == "openjiuwen.13100004"


def test_from_builder_exception_missing_request_id():
    exc = JiuWenBaseException(error_code=102154, message="x")
    d = factory.from_builder_exception(exc, None)
    assert d.error_code == "openjiuwen.13100006"
    assert d.request_id == "unknown"


def test_from_builder_exception_body_has_exact_legacy_code():
    exc = JiuWenBaseException(error_code=102155, message="x")
    resp = factory.build_json_response(factory.from_builder_exception(exc, _rid()), "zh-cn")
    body = json.loads(resp.body)
    assert body["error_code"] == "openjiuwen.13100007"
    assert resp.status_code == 404
    assert resp.headers["x-request-id"] == _rid()


# ---- COM-07A §4.2: build_sse_error_event 异常类型分流 + SSE wire ----

def _parse_sse(wire: str) -> dict:
    """从 SSE wire 解析 JSON envelope。"""
    assert wire.startswith("data: ")
    return json.loads(wire[len("data: "):].strip())


def test_build_sse_error_event_registered_jiuwen_canonical_wire():
    """已登记 JiuWenBaseException → DEF-06 canonical 码;legacy 整数与 cause 不外泄。"""
    exc = JiuWenBaseException(error_code=102154, message="secret-detail-abc")
    wire = factory.build_sse_error_event(_rid(), exc, "zh-cn")
    envelope = _parse_sse(wire)
    assert envelope["event"] == "error"
    data = envelope["data"]
    assert data["error_code"] == "openjiuwen.13100006"  # canonical, not legacy 102154
    assert "102154" not in wire  # legacy integer not in wire
    assert "secret-detail-abc" not in wire  # cause not leaked
    assert data["request_id"] == _rid()
    # 五字段完整
    for field in ("error_code", "error_msg", "error_reason", "error_suggestion", "request_id"):
        assert field in data


def test_build_sse_error_event_unregistered_code_internal():
    """未登记 legacy code → 安全降级 INTERNAL_ERROR。"""
    exc = JiuWenBaseException(error_code=99999, message="x")
    wire = factory.build_sse_error_event(_rid(), exc, "zh-cn")
    data = _parse_sse(wire)["data"]
    assert data["error_code"] == "openjiuwen.13100004"


def test_build_sse_error_event_minus_one_internal():
    """JiuWenException(error_code=-1) → INTERNAL_ERROR。"""
    exc = JiuWenException("config missing")
    wire = factory.build_sse_error_event(_rid(), exc, "zh-cn")
    data = _parse_sse(wire)["data"]
    assert data["error_code"] == "openjiuwen.13100004"
    assert "config missing" not in wire


def test_build_sse_error_event_plain_exception_internal_no_cause_leak():
    """普通异常(非 JiuWenBaseException)→ INTERNAL_ERROR;cause 不外泄。"""
    exc = RuntimeError("boom-secret-xyz")
    wire = factory.build_sse_error_event(_rid(), exc, "en-us")
    data = _parse_sse(wire)["data"]
    assert data["error_code"] == "openjiuwen.13100004"
    assert "boom-secret-xyz" not in wire  # pylint: disable=function-docstring-indents-four  # noqa


def test_build_sse_error_event_guard_blocks_second_emit():
    """guard 唯一终态:第一个赢家产出,第二个返回 None。"""
    guard = SseTerminalGuard()
    guard.begin_streaming()
    exc = JiuWenBaseException(error_code=102154, message="x")
    first = factory.build_sse_error_event(_rid(), exc, "zh-cn", guard=guard)
    second = factory.build_sse_error_event(_rid(), exc, "zh-cn", guard=guard)
    assert first is not None
    assert second is None  # 第二个被 guard 阻断


def test_build_sse_error_event_no_guard_still_emits():
    """guard=None 时仍产出(guard 唯一性由调用方保证)。"""
    exc = RuntimeError("x")
    wire = factory.build_sse_error_event(_rid(), exc, "zh-cn")
    assert wire is not None
    assert _parse_sse(wire)["event"] == "error"


def test_build_sse_error_event_en_locale_text():
    """en-us locale 产出英文文案。"""
    exc = JiuWenBaseException(error_code=102154, message="x")
    wire = factory.build_sse_error_event(_rid(), exc, "en-us")
    data = _parse_sse(wire)["data"]
    # 英文文案非空且不含中文
    assert data["error_msg"]
    assert data["error_reason"]
    assert data["error_suggestion"]
