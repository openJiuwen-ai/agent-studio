"""COM-03 §10.1: Builder ErrorDescriptor + catalog 不变量测试。"""

import pytest

from agent_builder.common.error_contract.descriptor import ErrorDescriptor, ErrorDetail
from agent_builder.common.error_contract import catalog


CODE = "openjiuwen.13100001"
MSG_KEY = "openjiuwen.13100001"
REASON_KEY = "openjiuwen.13100001.reason"
SUGGESTION_KEY = "openjiuwen.13100001.suggestion"
REQ_ID = "req-abc-123"
CAUSE = ValueError("boom")
VALID_DETAIL = ErrorDetail(error_code="openjiuwen.13100001", error_msg="Invalid param")


def _base(**overrides):
    defaults = dict(
        error_code=CODE, http_status=400, message_key=MSG_KEY,
        reason_key=REASON_KEY, suggestion_key=SUGGESTION_KEY, request_id=REQ_ID,
    )
    defaults.update(overrides)
    return ErrorDescriptor(**defaults)


def test_all_required_present_constructs():
    d = _base()
    assert d.error_code == CODE
    assert d.http_status == 400


def test_blank_error_code_rejected():
    with pytest.raises(ValueError):
        _base(error_code="  ")


def test_http_status_out_of_range_rejected():
    with pytest.raises(ValueError):
        _base(http_status=200)
    with pytest.raises(ValueError):
        _base(http_status=600)


def test_downstream_paired_accepted():
    d = _base(http_status=502, downstream_service="external",
             downstream_error_code="test-fake-99999")
    assert d.downstream_service == "external"


def test_downstream_service_without_code_accepted():
    """基础契约 §5：传输失败等无原码场景允许只记录 downstream_service。"""
    d = _base(http_status=502, downstream_service="external")
    assert d.downstream_service == "external"
    assert d.downstream_error_code is None


def test_cause_not_in_repr():
    d = _base(cause=CAUSE)
    assert "boom" not in repr(d)


def test_cause_not_in_eq():
    d1 = _base(cause=CAUSE)
    d2 = _base(cause=RuntimeError("different"))
    assert d1 == d2
    assert hash(d1) == hash(d2)


def test_safe_details_valid_accepted():
    d = _base(safe_details=[VALID_DETAIL])
    assert len(d.safe_details) == 1


def test_safe_details_blank_error_code_rejected():
    with pytest.raises(ValueError):
        ErrorDetail(error_code="  ", error_msg="msg")


def test_to_safe_dict_excludes_cause_and_downstream():
    d = _base(http_status=502, downstream_service="external",
             downstream_error_code="test-fake-99999", cause=CAUSE,
             safe_details=[VALID_DETAIL])
    safe = d.to_safe_dict()
    assert "cause" not in safe
    assert "downstream_service" not in safe
    assert safe["error_code"] == CODE


def test_catalog_resolves_registered_code():
    defn = catalog.resolve("openjiuwen.13100001")
    assert defn.http_status == 400
    assert defn.reason_key == "openjiuwen.13100001.reason"


def test_catalog_rejects_unregistered_code():
    with pytest.raises(KeyError):
        catalog.resolve("test-fake-99999")


def test_catalog_has_framework_and_business_codes():
    """DEF-06 §7.1: 五个框架码仍全部存在且未改义；八个业务 canonical 码已登记。

    不以固定总数阻断 catalog 扩展——只断言已知码集存在。
    legacy 整数码(102154 等)不登记在 _CATALOG(避免与 Runtime 副本冲突),
    只作 _LEGACY_TO_CANONICAL 映射 key。
    """
    codes = {d.error_code for d in catalog.all_definitions()}
    # COM-03 five framework codes unchanged
    for fc in (
        "openjiuwen.13100001", "openjiuwen.13100002", "openjiuwen.13100003",
        "openjiuwen.13100004", "openjiuwen.13100005",
    ):
        assert fc in codes
    # DEF-06 eight business canonical codes (Builder-exclusive, not legacy integers)
    for bc in (
        "openjiuwen.13100006", "openjiuwen.13100007", "openjiuwen.13100008",
        "openjiuwen.13100009", "openjiuwen.13100010", "openjiuwen.13100011",
        "openjiuwen.13100012", "openjiuwen.13100013",
    ):
        assert bc in codes
    # legacy integers are NOT registered in _CATALOG
    assert "102154" not in codes
    assert "102155" not in codes


def test_catalog_lookup_business_definition_maps_legacy_to_canonical():
    """DEF-06: lookup_business_definition 把 legacy 整数码映射到 canonical 定义。"""
    assert catalog.lookup_business_definition("102154") is catalog.PROMPT_OPTIMIZE_INVALID_PARAMS
    assert catalog.lookup_business_definition("102154").error_code == "openjiuwen.13100006"
    assert catalog.lookup_business_definition("102155") is catalog.PROMPT_OPTIMIZE_JOB_NOT_FOUND
    # framework codes are NOT legacy-mapped
    assert catalog.lookup_business_definition("openjiuwen.13100001") is None
    assert catalog.lookup_business_definition("openjiuwen.13100004") is None
    # canonical business codes are not legacy-mapped (only legacy integers are keys)
    assert catalog.lookup_business_definition("openjiuwen.13100006") is None


def test_catalog_404_and_405_have_correct_http_status():
    assert catalog.resolve("openjiuwen.13100002").http_status == 404
    assert catalog.resolve("openjiuwen.13100003").http_status == 405
