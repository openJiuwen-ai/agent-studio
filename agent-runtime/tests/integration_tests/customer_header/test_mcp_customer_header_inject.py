#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP 出站 customer header inject 单元测试

验证 jiuwen.extension.wrapper.customer_header_inject.inject_customer_headers_to_mcp：
- 剥 auth_keys 注入的 cust- 前缀（cust-token→token, cust-userid→userid）
- 仅使用自身配置的 auth_keys，不透传上游 captured
- 非 cust- header（X-Request-Id / Authorization / Content-Length）不受影响
- 无 cust-* 时不动
- profile disabled 时仍剥 auth_keys 前缀（剥前缀不依赖 profile）

不依赖 runtime 请求上下文，model_service.ports.get_request_customer_headers 用 monkeypatch mock。

运行:
    cd agent-runtime
    python -m pytest tests/integration_tests/customer_header/test_mcp_customer_header_inject.py -v
"""

from types import SimpleNamespace

import pytest

from customer_header.profile import CustomerHeaderProfile, set_profile
from customer_header.types import HeaderValue
from jiuwen.extension.wrapper.customer_header_inject import inject_customer_headers_to_mcp


def _make_profile(enabled: bool = True, targets: dict | None = None) -> CustomerHeaderProfile:
    """构造测试用 Profile（含 RUNTIME_MCP_CALL mappings）"""
    if targets is None:
        targets = {
            "RUNTIME_MCP_CALL": {
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


def _make_request_params(headers: dict) -> SimpleNamespace:
    """构造 MCP client 的 request_params（含 headers dict）"""
    return SimpleNamespace(headers=dict(headers))


class TestInjectCustomerHeadersToMcp:
    def __init__(self):
        self.profile = None

    def setup_method(self):
        self.profile = _make_profile()
        set_profile(self.profile)

    def test_strips_cust_prefix_keeps_others(self, monkeypatch):
        """auth_keys 注入 cust-* → 剥前缀；非 cust- header 保留；无 captured 仍剥"""
        assert self.profile is not None
        monkeypatch.setattr("model_service.ports.get_request_customer_headers", lambda: {})
        rp = _make_request_params({
            "cust-token": "tokenmock",
            "cust-userid": "123456",
            "X-Request-Id": "req-1",
            "X-Execution-Id": "exec-1",
        })
        inject_customer_headers_to_mcp(rp)
        assert rp.headers["token"] == "tokenmock"
        assert rp.headers["userid"] == "123456"
        assert "cust-token" not in rp.headers
        assert "cust-userid" not in rp.headers
        assert rp.headers["X-Request-Id"] == "req-1"
        assert rp.headers["X-Execution-Id"] == "exec-1"

    def test_captured_ignored_uses_static_only(self, monkeypatch):
        """MCP 不透传上游 captured，仅使用自身配置的 auth_keys"""
        assert self.profile is not None
        # 设置上游 captured（应被忽略）
        monkeypatch.setattr(
            "model_service.ports.get_request_customer_headers",
            lambda: _make_captured(userid="req-user", token="req-tok"),
        )
        rp = _make_request_params({
            "cust-token": "static-tok",
            "cust-userid": "static-user",
        })
        inject_customer_headers_to_mcp(rp)
        # captured 被忽略，保留静态值（static-only）
        assert rp.headers["token"] == "static-tok"
        assert rp.headers["userid"] == "static-user"

    def test_no_cust_unchanged(self, monkeypatch):
        """无 cust-* → headers 不动"""
        assert self.profile is not None
        monkeypatch.setattr("model_service.ports.get_request_customer_headers", lambda: {})
        rp = _make_request_params({"X-Request-Id": "req-1", "Authorization": "Bearer x"})
        inject_customer_headers_to_mcp(rp)
        assert rp.headers == {"X-Request-Id": "req-1", "Authorization": "Bearer x"}

    def test_non_cust_headers_not_dropped_or_lowercased(self, monkeypatch):
        """非 cust- 的 Authorization/Content-Length 不被 RESERVED_BLACKLIST 误丢、不小写化（只传 cust-* 给）"""
        assert self.profile is not None
        monkeypatch.setattr("model_service.ports.get_request_customer_headers", lambda: {})
        rp = _make_request_params({
            "cust-token": "tok",
            "Authorization": "Bearer secret",
            "Content-Length": "42",
        })
        inject_customer_headers_to_mcp(rp)
        assert rp.headers["token"] == "tok"
        assert rp.headers["Authorization"] == "Bearer secret"
        assert rp.headers["Content-Length"] == "42"
        assert "cust-token" not in rp.headers

    def test_profile_disabled_still_strips_no_captured(self, monkeypatch):
        """profile disabled + 无 captured： 仍剥 auth_keys 前缀（剥前缀不依赖 profile）"""
        assert self.profile is not None
        set_profile(_make_profile(enabled=False))
        monkeypatch.setattr("model_service.ports.get_request_customer_headers", lambda: {})
        rp = _make_request_params({"cust-token": "tok", "cust-userid": "u"})
        inject_customer_headers_to_mcp(rp)
        assert rp.headers["token"] == "tok"
        assert rp.headers["userid"] == "u"
        assert "cust-token" not in rp.headers
        assert "cust-userid" not in rp.headers

    def test_no_headers_attr_no_error(self, monkeypatch):
        """request_params 无 headers 属性时不报错（降级返回）"""
        assert self.profile is not None
        monkeypatch.setattr(
            "model_service.ports.get_request_customer_headers",
            lambda: _make_captured("u", "t"),
        )
        rp = SimpleNamespace()
        inject_customer_headers_to_mcp(rp)

    def test_ports_not_registered_no_error(self):
        """model_service.ports.get_request_customer_headers 抛异常时降级（captured={}）"""
        assert self.profile is not None
        import model_service.ports as ports
        original = ports.get_request_customer_headers
        ports.get_request_customer_headers = None  # 调用会抛 TypeError
        try:
            rp = _make_request_params({"cust-token": "tok"})
            inject_customer_headers_to_mcp(rp)
            # None 抛 TypeError → except 降级 captured={} → 仍剥前缀
            assert rp.headers["token"] == "tok"
        finally:
            ports.get_request_customer_headers = original
