"""COM-03 §10.2: Runtime HTTP builder 契约测试。"""

import os

from agent_runtime.error_contract.descriptor import ErrorDescriptor, ErrorDetail
from agent_runtime.error_contract.http_builder import I18nResolver, build_http_response
from agent_runtime.error_contract import catalog


_I18N_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "agent_runtime", "event_handler", "base", "resources", "i18n",
)
_RESOLVER = I18nResolver(
    _I18N_DIR,
    {"zh_cn": "runtime-msg_zh_CN.properties", "en_us": "runtime-msg_en_US.properties"},
)


def _descriptor(**overrides):
    defn = catalog.resolve("openjiuwen.12100001")
    defaults = dict(
        error_code=defn.error_code,
        http_status=defn.http_status,
        message_key=defn.message_key,
        reason_key=defn.reason_key,
        suggestion_key=defn.suggestion_key,
        request_id="req-test-001",
    )
    defaults.update(overrides)
    return ErrorDescriptor(**defaults)


def test_five_fields_non_empty_strings():
    spec = build_http_response(_descriptor(), "zh_cn", _RESOLVER)
    body = spec.body
    assert body["error_code"]
    assert isinstance(body["error_code"], str)
    assert body["error_msg"]
    assert isinstance(body["error_msg"], str)
    assert body["error_reason"]
    assert isinstance(body["error_reason"], str)
    assert body["error_suggestion"]
    assert isinstance(body["error_suggestion"], str)
    assert body["request_id"]
    assert isinstance(body["request_id"], str)


def test_body_request_id_equals_header():
    spec = build_http_response(_descriptor(request_id="req-xyz-789"), "zh_cn", _RESOLVER)
    assert spec.body["request_id"] == "req-xyz-789"
    assert spec.headers["X-Request-Id"] == "req-xyz-789"


def test_http_status_from_descriptor():
    d = _descriptor()
    spec = build_http_response(d, "zh_cn", _RESOLVER)
    assert spec.status == d.http_status


def test_details_omitted_when_none():
    spec = build_http_response(_descriptor(), "zh_cn", _RESOLVER)
    assert "details" not in spec.body


def test_details_empty_array_when_empty_list():
    spec = build_http_response(_descriptor(safe_details=[]), "zh_cn", _RESOLVER)
    assert spec.body["details"] == []


def test_details_valid_when_non_empty():
    detail = ErrorDetail(
        error_code="openjiuwen.12100001", error_msg="Invalid field: name"
    )
    spec = build_http_response(_descriptor(safe_details=[detail]), "zh_cn", _RESOLVER)
    assert len(spec.body["details"]) == 1
    assert spec.body["details"][0]["error_code"] == "openjiuwen.12100001"


def test_cause_not_in_body():
    spec = build_http_response(
        _descriptor(cause=ValueError("secret")), "zh_cn", _RESOLVER
    )
    body_str = str(spec.body)
    assert "secret" not in body_str
    assert "cause" not in spec.body


def test_downstream_not_in_body():
    spec = build_http_response(
        _descriptor(http_status=502, downstream_service="builder",
                    downstream_error_code="test-fake"),
        "zh_cn", _RESOLVER,
    )
    assert "downstream_service" not in spec.body
    assert "downstream_error_code" not in spec.body


def test_locale_fallback_to_zh_cn():
    spec_zh = build_http_response(_descriptor(), "zh_cn", _RESOLVER)
    spec_missing = build_http_response(_descriptor(), "nonexistent", _RESOLVER)
    assert spec_missing.body["error_msg"] == spec_zh.body["error_msg"]


def test_en_us_locale_resolves():
    spec = build_http_response(_descriptor(), "en_us", _RESOLVER)
    # English message should differ from Chinese
    assert spec.body["error_msg"]
    assert spec.body["error_msg"] != build_http_response(_descriptor(), "zh_cn", _RESOLVER).body["error_msg"]
