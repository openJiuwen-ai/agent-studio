"""COM-03 §10.4: Runtime factory（异常分类 → descriptor）契约测试。"""

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from agent_runtime.error_contract import factory


def _rid():
    return "req-factory-001"


# ---- normalize_locale ----

def test_normalize_locale_zh_variants():
    assert factory.normalize_locale("zh-cn") == "zh_cn"
    assert factory.normalize_locale("zh_CN") == "zh_cn"
    assert factory.normalize_locale("") == "zh_cn"
    assert factory.normalize_locale(None) == "zh_cn"


def test_normalize_locale_en_variants():
    assert factory.normalize_locale("en-us") == "en_us"
    assert factory.normalize_locale("en") == "en_us"
    assert factory.normalize_locale("EN-US") == "en_us"


# ---- from_validation ----

def test_from_validation_maps_to_12100001_with_details():
    exc = RequestValidationError([{"loc": ["body", "name"], "msg": "field required"}])
    d = factory.from_validation(exc, _rid())
    assert d.error_code == "openjiuwen.12100001"
    assert d.http_status == 400
    assert d.request_id == _rid()
    assert d.safe_details is not None
    assert len(d.safe_details) == 1
    assert "name" in d.safe_details[0].error_msg


def test_from_validation_none_request_id_falls_back():
    exc = RequestValidationError([{"loc": [], "msg": "bad"}])
    d = factory.from_validation(exc, None)
    assert d.request_id == "unknown"


# ---- from_route_not_found / from_method_not_allowed ----

def test_from_route_not_found():
    d = factory.from_route_not_found(_rid())
    assert d.error_code == "openjiuwen.12100002"
    assert d.http_status == 404


def test_from_method_not_allowed():
    d = factory.from_method_not_allowed(_rid())
    assert d.error_code == "openjiuwen.12100003"
    assert d.http_status == 405


# ---- from_request_conflict ----

def test_from_request_conflict_is_400_validation():
    d = factory.from_request_conflict(_rid())
    assert d.error_code == "openjiuwen.12100001"
    assert d.http_status == 400
    assert d.safe_details is None


# ---- from_downstream_builder ----

def test_from_downstream_builder_maps_502_with_internal_diag():
    exc = RuntimeError("builder exploded")
    d = factory.from_downstream_builder(exc, _rid())
    assert d.error_code == "openjiuwen.12100005"
    assert d.http_status == 502
    assert d.downstream_service == "builder"
    # 对外不泄漏 cause
    assert "builder exploded" not in repr(d)


# ---- from_internal ----

def test_from_internal_maps_500():
    exc = ValueError("secret detail")
    d = factory.from_internal(exc, _rid())
    assert d.error_code == "openjiuwen.12100004"
    assert d.http_status == 500
    assert "secret detail" not in repr(d)


# ---- from_http_exception ----

@pytest.mark.parametrize("status,expected_code,expected_http", [
    (404, "openjiuwen.12100002", 404),
    (405, "openjiuwen.12100003", 405),
    (400, "openjiuwen.12100001", 400),
    (422, "openjiuwen.12100001", 422),  # 意见2: 422 保留原状态码
    (500, "openjiuwen.12100004", 500),
    (503, "openjiuwen.12100004", 500),
])
def test_from_http_exception_mapping(status, expected_code, expected_http):
    exc = HTTPException(status_code=status, detail="x")
    d = factory.from_http_exception(exc, _rid())
    assert d.error_code == expected_code
    assert d.http_status == expected_http


# ---- build_json_response ----

def test_build_json_response_five_fields_and_header():
    d = factory.from_route_not_found(_rid())
    resp = factory.build_json_response(d, "zh-cn")
    assert resp.status_code == 404
    body = __import__("json").loads(resp.body)
    for field in ("error_code", "error_msg", "error_reason", "error_suggestion", "request_id"):
        assert body[field], f"{field} non-empty"
    assert body["error_code"] == "openjiuwen.12100002"
    assert body["request_id"] == _rid()
    assert resp.headers["x-request-id"] == _rid()


def test_build_json_response_en_locale():
    d = factory.from_internal(RuntimeError("x"), _rid())
    resp = factory.build_json_response(d, "en-us")
    body = __import__("json").loads(resp.body)
    assert body["error_msg"]
    zh = __import__("json").loads(factory.build_json_response(d, "zh-cn").body)
    assert body["error_msg"] != zh["error_msg"]


def test_build_json_response_details_present_for_validation():
    exc = RequestValidationError([{"loc": ["query", "q"], "msg": "required"}])
    d = factory.from_validation(exc, _rid())
    resp = factory.build_json_response(d, "zh-cn")
    body = __import__("json").loads(resp.body)
    assert body["details"]
    assert body["details"][0]["error_code"] == "openjiuwen.12100001"


class _PluginExc(Exception):
    """模拟被 bpmn_workflow._process_exception 包成的 plain JiuWenBaseException。

    _process_exception 把 PluginCommonException(105015) 包成 plain
    JiuWenBaseException——保留 .error_code（基类 property=105015），但 .code
    （PluginCommonException 子类 property）丢失。from_plugin_exception 用
    .error_code 识别。此处直接设 .error_code 模拟被包形态。
    """

    def __init__(self, error_code, message=""):
        super().__init__(message)
        self._error_code = error_code

    @property
    def error_code(self):
        return self._error_code


def test_from_plugin_exception_105015_maps_to_12100006():
    """SYNC-01 P5-R3 决策 A: 105015(未发布)→canonical openjiuwen.12100006(422)。

    用 .error_code（被 _process_exception 包成的 plain JiuWenBaseException 形态，
    无 .code）——验证 from_plugin_exception 用 .error_code 而非 .code。
    """
    d = factory.from_plugin_exception(_PluginExc(105015, "not a list"), _rid())
    assert d.error_code == "openjiuwen.12100006"
    assert d.http_status == 422
    assert d.cause is not None


def test_from_plugin_exception_non_105015_falls_back_to_internal():
    """非 105015 插件码 / 无 error_code 属性 → from_internal(12100004)。"""
    assert (
        factory.from_plugin_exception(_PluginExc(999), _rid()).error_code
        == "openjiuwen.12100004"
    )
    assert (
        factory.from_plugin_exception(RuntimeError("no error_code"), _rid()).error_code
        == "openjiuwen.12100004"
    )


# ---------------------------------------------------------------------------
# P5-R3a: is_plugin_response_format_error（直接 + __cause__ 链）与包装映射
# ---------------------------------------------------------------------------

def _openjiuwen_exec_error(cause=None):
    """构造 openjiuwen ExecutionError(BaseError 子类,cause 显式设 __cause__)。

    真实形态：openjiuwen graph/vertex.py `except Exception` 把 vendored
    JiuWenBaseException(105015)(Exception 子类,非 BaseError)包成
    build_error(StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR, cause=e)。
    BaseError.__init__ 显式 self.__cause__ = cause。
    """
    from openjiuwen.core.common.exception.codes import StatusCode
    from openjiuwen.core.common.exception.errors import ExecutionError
    return ExecutionError(
        StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR, cause=cause)


def _openjiuwen_base_error(cause=None):
    """构造非 ExecutionError 的 BaseError 直接子类（走 except BaseError 分支）。"""
    from openjiuwen.core.common.exception.codes import StatusCode
    from openjiuwen.core.common.exception.errors import BaseError
    return BaseError(StatusCode.ERROR, cause=cause)


class _JiuWenExc(Exception):
    """模拟 vendored JiuWenBaseException(error_code 属性形态)。"""

    def __init__(self, error_code, message=""):
        super().__init__(message)
        self._error_code = error_code

    @property
    def error_code(self):
        return self._error_code


def test_is_plugin_response_format_error_direct():
    """直接异常 error_code==105015 → True（plain JiuWenBaseException 形态）。"""
    assert factory.is_plugin_response_format_error(_PluginExc(105015)) is True
    assert factory.is_plugin_response_format_error(_JiuWenExc(105015)) is True


def test_is_plugin_response_format_error_wrapped_execution_error():
    """ExecutionError(cause=JiuWenBaseException(105015)) → True（引擎包装路径）。"""
    wrapped = _openjiuwen_exec_error(cause=_JiuWenExc(105015))
    assert factory.is_plugin_response_format_error(wrapped) is True


def test_is_plugin_response_format_error_wrapped_base_error():
    """BaseError 直接子类(非 ExecutionError)的 cause 链 → True（except BaseError 分支）。"""
    wrapped = _openjiuwen_base_error(cause=_JiuWenExc(105015))
    assert factory.is_plugin_response_format_error(wrapped) is True


def test_is_plugin_response_format_error_multilayer_cause():
    """多层 cause 链（ExecutionError←BaseError←105015）→ True。"""
    inner = _JiuWenExc(105015)
    mid = _openjiuwen_base_error(cause=inner)
    outer = _openjiuwen_exec_error(cause=mid)
    assert factory.is_plugin_response_format_error(outer) is True


def test_is_plugin_response_format_error_negative():
    """非 105015（直接与 cause 链）/ 无 error_code → False（保持既有行为）。"""
    assert factory.is_plugin_response_format_error(_PluginExc(105001)) is False
    assert factory.is_plugin_response_format_error(
        _openjiuwen_exec_error(cause=_JiuWenExc(105001))) is False
    assert factory.is_plugin_response_format_error(RuntimeError("plain")) is False
    # 包装异常自身无 105015 且 cause 无 error_code → False
    assert factory.is_plugin_response_format_error(
        _openjiuwen_exec_error(cause=ValueError("v"))) is False


def test_is_plugin_response_format_error_cyclic_cause_terminates():
    """adversarial P5-R3a gap: __cause__ 自引用/互引用不得无限循环。

    编程错误（BaseError(cause=self)）或反序列化造成的 cause 循环——
    visited id 集合在命中已访问对象时终止,不挂起请求。
    """
    cyclic = _JiuWenExc(105001)
    cyclic.__cause__ = cyclic  # 自引用
    assert factory.is_plugin_response_format_error(cyclic) is False

    # 互引用循环 a→b→a
    a = _JiuWenExc(105001)
    b = _openjiuwen_exec_error(cause=a)
    a.__cause__ = b
    assert factory.is_plugin_response_format_error(a) is False

    # 循环链中含 105015 仍应命中（先检测到 105015 再遇循环终止）
    c = _JiuWenExc(105015)
    c.__cause__ = c
    assert factory.is_plugin_response_format_error(c) is True


def test_from_plugin_exception_wrapped_105015_maps_to_12100006():
    """P5-R3a: ExecutionError(cause=105015) → 12100006（catch 端认 __cause__ 链）。

    re-raise 的包装异常传播到 catch 端（首帧预取/stream_response except/
    server.py generic handler）后由 from_plugin_exception 分类——若只判
    exc.error_code（ExecutionError 为引擎码非 105015）会落到 12100004。
    """
    wrapped = _openjiuwen_exec_error(cause=_JiuWenExc(105015, "SECRET-X"))
    d = factory.from_plugin_exception(wrapped, _rid())
    assert d.error_code == "openjiuwen.12100006"
    assert d.http_status == 422
    assert d.cause is wrapped  # 保留原异常供日志诊断


def test_from_plugin_exception_wrapped_non_105015_keeps_internal():
    """反证：ExecutionError(cause=105001) → from_internal(12100004)，
    非 105015 业务码不被误映射（分支级 yield 行为由 workflow_runner
    guard 测试另行锁定）。"""
    wrapped = _openjiuwen_exec_error(cause=_JiuWenExc(105001))
    assert factory.from_plugin_exception(wrapped, _rid()).error_code == \
        "openjiuwen.12100004"
