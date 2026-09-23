"""COM-03 §10.1: Runtime ErrorDescriptor + catalog 不变量测试。"""

import pytest

from agent_runtime.error_contract.descriptor import ErrorDescriptor, ErrorDetail
from agent_runtime.error_contract import catalog


CODE = "openjiuwen.12100001"
MSG_KEY = "openjiuwen.12100001"
REASON_KEY = "openjiuwen.12100001.reason"
SUGGESTION_KEY = "openjiuwen.12100001.suggestion"
REQ_ID = "req-abc-123"
CAUSE = ValueError("boom")
VALID_DETAIL = ErrorDetail(error_code="openjiuwen.12100001", error_msg="Invalid param")


def _base(**overrides):
    defaults = dict(
        error_code=CODE, http_status=400, message_key=MSG_KEY,
        reason_key=REASON_KEY, suggestion_key=SUGGESTION_KEY, request_id=REQ_ID,
    )
    defaults.update(overrides)
    return ErrorDescriptor(**defaults)


# ---- required fields / http_status ----

def test_all_required_present_constructs():
    d = _base()
    assert d.error_code == CODE
    assert d.http_status == 400
    assert d.request_id == REQ_ID


def test_blank_error_code_rejected():
    with pytest.raises(ValueError):
        _base(error_code="  ")


def test_http_status_out_of_range_rejected():
    with pytest.raises(ValueError):
        _base(http_status=200)
    with pytest.raises(ValueError):
        _base(http_status=600)


def test_blank_request_id_rejected():
    with pytest.raises(ValueError):
        _base(request_id="")


# ---- downstream pairing ----

def test_downstream_service_without_code_accepted():
    """基础契约 §5：传输失败等无原码场景允许只记录 downstream_service。"""
    d = _base(http_status=502, downstream_service="builder")
    assert d.downstream_service == "builder"
    assert d.downstream_error_code is None


def test_downstream_code_without_service_rejected():
    with pytest.raises(ValueError):
        _base(http_status=502, downstream_error_code="test-fake-bld-downstream")


def test_downstream_paired_accepted():
    d = _base(http_status=502, downstream_service="builder",
             downstream_error_code="test-fake-bld-downstream")
    assert d.downstream_service == "builder"


def test_downstream_invalid_service_rejected():
    with pytest.raises(ValueError):
        _base(http_status=502, downstream_service="invalid",
             downstream_error_code="some-code")


# ---- cause / downstream excluded from eq/repr ----

def test_cause_not_in_repr():
    d = _base(cause=CAUSE)
    assert "boom" not in repr(d)
    assert "ValueError" not in repr(d)


def test_cause_not_in_eq():
    d1 = _base(cause=CAUSE)
    d2 = _base(cause=RuntimeError("different"))
    assert d1 == d2
    assert hash(d1) == hash(d2)


def test_downstream_not_in_eq_or_repr():
    d1 = _base(http_status=502, downstream_service="builder",
             downstream_error_code="test-fake-bld-downstream")
    d2 = _base(http_status=502, downstream_service="external",
             downstream_error_code="test-fake-99999")
    assert d1 == d2
    assert "builder" not in repr(d1)
    assert "downstream" not in repr(d1)


# ---- safe_details ----

def test_safe_details_none_omitted():
    d = _base()
    assert d.safe_details is None


def test_safe_details_empty_accepted():
    d = _base(safe_details=[])
    assert len(d.safe_details) == 0  # tuple, not list


def test_safe_details_valid_accepted():
    d = _base(safe_details=[VALID_DETAIL])
    assert len(d.safe_details) == 1


def test_safe_details_blank_error_code_rejected():
    with pytest.raises(ValueError):
        ErrorDetail(error_code="  ", error_msg="msg")


def test_safe_details_blank_error_msg_rejected():
    with pytest.raises(ValueError):
        ErrorDetail(error_code="openjiuwen.12100001", error_msg="")


# ---- to_safe_dict excludes internal fields ----

def test_to_safe_dict_excludes_cause_and_downstream():
    d = _base(http_status=502, downstream_service="builder",
             downstream_error_code="test-fake-bld-downstream", cause=CAUSE,
             safe_details=[VALID_DETAIL])
    safe = d.to_safe_dict()
    assert "cause" not in safe
    assert "downstream_service" not in safe
    assert "downstream_error_code" not in safe
    assert safe["error_code"] == CODE
    assert safe["request_id"] == REQ_ID
    assert len(safe["safe_details"]) == 1


# ---- catalog ----

def test_catalog_resolves_registered_code():
    defn = catalog.resolve("openjiuwen.12100001")
    assert defn.http_status == 400
    assert defn.message_key == "openjiuwen.12100001"
    assert defn.reason_key == "openjiuwen.12100001.reason"
    assert defn.suggestion_key == "openjiuwen.12100001.suggestion"


def test_catalog_rejects_unregistered_code():
    with pytest.raises(KeyError):
        catalog.resolve("test-fake-99999")


def test_catalog_has_five_framework_codes():
    codes = {d.error_code for d in catalog.all_definitions()}
    assert "openjiuwen.12100001" in codes
    assert "openjiuwen.12100002" in codes
    assert "openjiuwen.12100003" in codes
    assert "openjiuwen.12100004" in codes
    assert "openjiuwen.12100005" in codes


def test_catalog_404_and_405_have_correct_http_status():
    assert catalog.resolve("openjiuwen.12100002").http_status == 404
    assert catalog.resolve("openjiuwen.12100003").http_status == 405
