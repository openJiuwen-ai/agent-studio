"""COM-03 §10.2: Builder HTTP builder 契约测试。"""

import os

from agent_builder.common.error_contract.descriptor import ErrorDescriptor
from agent_builder.common.error_contract.http_builder import I18nResolver, build_http_response
from agent_builder.common.error_contract import catalog


_I18N_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "common", "error_contract", "i18n",
)
_RESOLVER = I18nResolver(
    _I18N_DIR,
    {"zh_cn": "messages_zh_CN.properties", "en_us": "messages_en_US.properties"},
)


def _descriptor(**overrides):
    defn = catalog.resolve("openjiuwen.13100001")
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
    for field in ("error_code", "error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[field], f"{field} should be non-empty"
        assert isinstance(body[field], str)


def test_body_request_id_equals_header():
    spec = build_http_response(_descriptor(request_id="req-xyz"), "zh_cn", _RESOLVER)
    assert spec.body["request_id"] == "req-xyz"
    assert spec.headers["X-Request-Id"] == "req-xyz"


def test_http_status_from_descriptor():
    spec = build_http_response(_descriptor(), "zh_cn", _RESOLVER)
    assert spec.status == 400


def test_details_omitted_when_none():
    assert "details" not in build_http_response(_descriptor(), "zh_cn", _RESOLVER).body


def test_details_empty_array_when_empty_list():
    assert build_http_response(_descriptor(safe_details=[]), "zh_cn", _RESOLVER).body["details"] == []


def test_cause_not_in_body():
    spec = build_http_response(_descriptor(cause=ValueError("secret")), "zh_cn", _RESOLVER)
    assert "secret" not in str(spec.body)
    assert "cause" not in spec.body


def test_downstream_not_in_body():
    spec = build_http_response(
        _descriptor(http_status=502, downstream_service="external",
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
    spec_en = build_http_response(_descriptor(), "en_us", _RESOLVER)
    spec_zh = build_http_response(_descriptor(), "zh_cn", _RESOLVER)
    assert spec_en.body["error_msg"] != spec_zh.body["error_msg"]
