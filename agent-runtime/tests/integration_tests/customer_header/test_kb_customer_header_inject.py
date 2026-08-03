# -*- coding: utf-8 -*-
"""KB 出站 customer header inject 单元测试

验证 agent_runtime.extension.workflow_node.kb_adapter.customer_header_inject.inject_customer_headers_to_kb：
- 开关启用 + captured → 映射 userid/token 注入 headers
- 开关未启用 → 不动（走原始逻辑，captured 也不生效）
- 无 captured → 不动
- KB 适配器 headers 不含 cust-*（KB 走纯映射 auth_type=""，无  剥前缀）
- 非 cust- header（Authorization / Content-Type）不受影响
- 空 headers / ports 未注册时降级不报错

与 test_mcp_customer_header_inject.py 差异：KB 是纯映射（无 ），所以没有"剥前缀"相关用例；
profile disabled 时 KB 完全 no-op（MCP 在 profile disabled 时仍剥 auth_keys 前缀）。

运行:
    cd agent-runtime
    python -m pytest tests/integration_tests/customer_header/test_kb_customer_header_inject.py -v
"""

import pytest

from customer_header.profile import CustomerHeaderProfile, set_profile
from customer_header.types import HeaderValue
from agent_runtime.extension.workflow_node.kb_adapter.customer_header_inject import (
    inject_customer_headers_to_kb,
)


def _make_profile(enabled: bool = True, targets: dict | None = None) -> CustomerHeaderProfile:
    """构造测试用 Profile（含 RUNTIME_KB_CALL mappings）"""
    if targets is None:
        targets = {
            "RUNTIME_KB_CALL": {
                "mappings": [
                    {"from": "cust-userid", "to": "userid"},
                    {"from": "cust-token", "to": "token"},
                ]
            }
        }
    return CustomerHeaderProfile.model_validate({
        "enabled": enabled,
        "environment": "simple",
        "capture": {"customer-allow": ["cust-userid", "cust-token"]},
        "targets": targets,
    })


def _make_captured(userid: str = "", token: str = "") -> dict:
    """构造捕获的客户 Header（与 middleware _capture_customer_headers 同构）"""
    result: dict = {}
    if userid:
        hv = HeaderValue.customer_captured("cust-userid", userid)
        result[hv.normalized_name] = hv
    if token:
        hv = HeaderValue.customer_captured("cust-token", token)
        result[hv.normalized_name] = hv
    return result


class TestInjectCustomerHeadersToKb:
    def __init__(self):
        self.profile = None

    def setup_method(self):
        self.profile = _make_profile()
        set_profile(self.profile)

    def test_captured_injects_userid_token(self, monkeypatch):
        """开关启用 + captured → 映射出 userid/token 注入 headers（KB 真实常态）"""
        assert self.profile is not None
        monkeypatch.setattr(
            "model_service.ports.get_request_customer_headers",
            lambda: _make_captured(userid="req-user", token="req-tok"),
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
        }
        inject_customer_headers_to_kb(headers)
        assert headers.get("userid") == "req-user"
        assert headers.get("token") == "req-tok"
        assert headers.get("Content-Type") == "application/json"
        assert headers.get("Authorization") == "Bearer secret"

    def test_profile_disabled_is_noop(self, monkeypatch):
        """开关未启用 → 不动，captured 也不生效（走原始逻辑）"""
        assert self.profile is not None
        set_profile(_make_profile(enabled=False))
        monkeypatch.setattr(
            "model_service.ports.get_request_customer_headers",
            lambda: _make_captured(userid="req-user", token="req-tok"),
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
        }
        original = dict(headers)
        inject_customer_headers_to_kb(headers)
        assert headers == original
        assert "userid" not in headers
        assert "token" not in headers

    def test_no_captured_noop(self, monkeypatch):
        """无 captured → 不动（即使开关启用）"""
        assert self.profile is not None
        monkeypatch.setattr("model_service.ports.get_request_customer_headers", lambda: {})
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer x",
        }
        original = dict(headers)
        inject_customer_headers_to_kb(headers)
        assert headers == original

    def test_no_cust_in_kb_headers(self, monkeypatch):
        """KB 适配器 headers 不含 cust-*（KB 走纯映射，无  剥前缀语义）——
        即使 headers 被误放了 cust-*，本函数也不剥（auth_type='' 只走  映射分支）
        """
        assert self.profile is not None
        monkeypatch.setattr(
            "model_service.ports.get_request_customer_headers",
            lambda: _make_captured(userid="u", token="t"),
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
            "cust-token": "stray",  # 误放，KB 不应剥（不适用）
        }
        inject_customer_headers_to_kb(headers)
        # captured 投影出 userid/token
        assert headers.get("userid") == "u"
        assert headers.get("token") == "t"
        # stray cust-token 不被剥（KB 不走）
        assert headers.get("cust-token") == "stray"

    def test_non_cust_headers_not_affected(self, monkeypatch):
        """非 cust- 的 Authorization / Content-Type / Content-Length 不受影响"""
        assert self.profile is not None
        monkeypatch.setattr(
            "model_service.ports.get_request_customer_headers",
            lambda: _make_captured(userid="u", token="t"),
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
            "Content-Length": "42",
            "X-Request-Id": "req-1",
        }
        inject_customer_headers_to_kb(headers)
        assert headers.get("userid") == "u"
        assert headers.get("token") == "t"
        assert headers.get("Content-Type") == "application/json"
        assert headers.get("Authorization") == "Bearer secret"
        assert headers.get("Content-Length") == "42"
        assert headers.get("X-Request-Id") == "req-1"

    def test_empty_or_none_headers_no_error(self, monkeypatch):
        """空 dict / None 不报错，直接返回"""
        assert self.profile is not None
        monkeypatch.setattr(
            "model_service.ports.get_request_customer_headers",
            lambda: _make_captured("u", "t"),
        )
        empty: dict = {}
        inject_customer_headers_to_kb(empty)
        assert empty == {}
        inject_customer_headers_to_kb(None)  # type: ignore[arg-type]

    def test_ports_not_registered_no_error(self):
        """model_service.ports.get_request_customer_headers 抛异常时降级（captured={}）→ no-op"""
        assert self.profile is not None
        import model_service.ports as ports
        original = ports.get_request_customer_headers
        ports.get_request_customer_headers = None  # 调用会抛 TypeError
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer x",
            }
            original_headers = dict(headers)
            inject_customer_headers_to_kb(headers)
            # ports 异常 → captured={} → 早返回 → headers 不变
            assert headers == original_headers
        finally:
            ports.get_request_customer_headers = original

    def test_profile_not_set_no_error(self):
        """get_profile 抛异常时降级 → 走原始逻辑，headers 不变"""
        assert self.profile is not None
        import customer_header.profile as profile_mod
        original = profile_mod.get_profile

        def _raise():
            raise RuntimeError("profile not initialized")

        profile_mod.get_profile = _raise  # type: ignore[assignment]
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer x",
            }
            original_headers = dict(headers)
            inject_customer_headers_to_kb(headers)
            assert headers == original_headers
        finally:
            profile_mod.get_profile = original
