#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Customer Header 投影引擎单元测试

不依赖 runtime 运行环境，直接测试 customer_header 包的核心逻辑:
- HeaderProjectionEngine.project() rename 原语
- resolve_outbound_headers() 统一出站函数
- RESERVED_BLACKLIST 黑名单防护
- CUSTOM_APIKEY 剥前缀 + request-over-config

运行方式:
    cd agent-runtime
    python -m pytest tests/integration_tests/customer_header/test_customer_header_unit.py -v
"""

import pytest

from customer_header.engine import HeaderProjectionEngine, resolve_outbound_headers, RESERVED_BLACKLIST
from customer_header.profile import CustomerHeaderProfile, set_profile, get_profile
from customer_header.target import InternalTarget
from customer_header.types import HeaderProvenance, HeaderValue


def _make_profile(
    enabled: bool = True,
    capture_allow: list[str] | None = None,
    targets: dict | None = None,
) -> CustomerHeaderProfile:
    """构造测试用 Profile"""
    if capture_allow is None:
        capture_allow = ["cust-userid", "cust-token"]
    if targets is None:
        targets = {
            "RUNTIME_LLM_CHAT": {
                "mappings": [
                    {"from": "cust-userid", "to": "userid"},
                    {"from": "cust-token", "to": "token"},
                ]
            },
            "LAKESEARCH": {
                "mappings": [
                    {"from": "cust-userid", "to": "userid"},
                    {"from": "cust-token", "to": "token"},
                ]
            },
            "IR_AUTH_KEYS": {
                "forward-list": ["cust-userid", "cust-token"],
            },
        }

    return CustomerHeaderProfile.model_validate({
        "enabled": enabled,
        "environment": "simple",
        "capture": {"customer-allow": capture_allow},
        "targets": targets,
    })


def _make_captured(userid: str = "user001", token: str = "tok123") -> dict[str, HeaderValue]:
    """构造捕获的客户 Header"""
    result = {}
    if userid:
        hv = HeaderValue.customer_captured("cust-userid", userid)
        result[hv.normalized_name] = hv
    if token:
        hv = HeaderValue.customer_captured("cust-token", token)
        result[hv.normalized_name] = hv
    return result


class TestHeaderProjectionEngine:
    """HeaderProjectionEngine.project() rename 原语"""

    def __init__(self):
        self.profile = None
        self.engine = None

    def setup_method(self):
        self.profile = _make_profile()
        set_profile(self.profile)
        self.engine = HeaderProjectionEngine(self.profile)

    def test_basic_rename(self):
        """cust-userid -> userid, cust-token -> token"""
        captured = _make_captured("alice", "secret")
        result = self.engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured)
        assert result["userid"] == "alice"
        assert result["token"] == "secret"
        # 原始 cust-* 不应出现在结果中
        assert "cust-userid" not in result
        assert "cust-token" not in result

    def test_rename_with_config_headers(self):
        """config_headers 不参与 rename，直接透传"""
        captured = _make_captured("alice", "secret")
        config = {"x-model-id": "gpt-4", "x-api-version": "2024-01"}
        result = self.engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured, config)
        assert result["userid"] == "alice"
        assert result["token"] == "secret"
        assert result["x-model-id"] == "gpt-4"
        assert result["x-api-version"] == "2024-01"

    def test_blacklist_blocks_reserved_headers(self):
        """黑名单中的 header 不允许被 rename 覆盖"""
        assert self.engine is not None
        # 构造一个 profile，将 cust-userid rename 为 authorization (在黑名单中)
        profile = _make_profile(targets={
            "RUNTIME_LLM_CHAT": {
                "mappings": [
                    {"from": "cust-userid", "to": "authorization"},
                    {"from": "cust-token", "to": "host"},
                ]
            }
        })
        engine = HeaderProjectionEngine(profile)
        captured = _make_captured("alice", "secret")
        result = engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured)
        # 黑名单 header 不应出现
        assert "authorization" not in result
        assert "host" not in result

    def test_config_blacklist_headers_also_blocked(self):
        """config_headers 中的黑名单 header 也不允许通过"""
        assert self.engine is not None
        captured = _make_captured()
        config = {"authorization": "Bearer evil", "host": "evil.com", "x-safe": "ok"}
        result = self.engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured, config)
        assert "authorization" not in result
        assert "host" not in result
        assert result["x-safe"] == "ok"

    def test_no_mappings_returns_config_only(self):
        """target 没有 mappings 时只返回 config_headers"""
        captured = _make_captured()
        config = {"x-model-id": "gpt-4"}
        result = self.engine.project(InternalTarget.BUILDER_LLM_CHAT, captured, config)
        assert result == {"x-model-id": "gpt-4"}

    def test_empty_captured_returns_config_only(self):
        """captured 为空时只返回 config_headers"""
        result = self.engine.project(InternalTarget.RUNTIME_LLM_CHAT, {})
        assert result == {}


class TestResolveOutboundHeaders:
    """resolve_outbound_headers() 统一出站函数"""

    def __init__(self):
        self.profile = None

    def setup_method(self):
        self.profile = _make_profile()
        set_profile(self.profile)

    def test_non_custom_apikey_does_rename_only(self):
        """非 CUSTOM_APIKEY: 只做 rename"""
        assert self.profile is not None
        captured = _make_captured("bob", "tok456")
        result = resolve_outbound_headers(
            target=InternalTarget.RUNTIME_LLM_CHAT,
            auth_type="API_KEY",
            config_headers={"x-model": "gpt-4"},
            captured_headers=captured,
        )
        assert result["userid"] == "bob"
        assert result["token"] == "tok456"
        assert result["x-model"] == "gpt-4"

    def test_custom_apikey_strips_cust_prefix(self):
        """CUSTOM_APIKEY: 剥 cust- 前缀 + request-over-config"""
        assert self.profile is not None
        captured = _make_captured("charlie", "tok789")
        config = {
            "cust-authorization": "Bearer static-key",
            "x-model": "gpt-4",
        }
        result = resolve_outbound_headers(
            target=InternalTarget.RUNTIME_LLM_CHAT,
            auth_type="CUSTOM_APIKEY",
            config_headers=config,
            captured_headers=captured,
        )
        # cust- 前缀被剥掉
        assert "authorization" in result
        assert result["authorization"] == "Bearer static-key"
        assert result["x-model"] == "gpt-4"
        # rename 后的 userid/token 也在
        assert result["userid"] == "charlie"
        assert result["token"] == "tok789"

    def test_custom_apikey_request_over_config(self):
        """CUSTOM_APIKEY: 请求中的值覆盖 config 中的值"""
        assert self.profile is not None
        # config 中有 cust-authorization，请求中也有 cust-userid -> userid
        captured = _make_captured("dave", "override-tok")
        config = {"cust-userid": "config-user"}  # config 中的值应被请求覆盖
        result = resolve_outbound_headers(
            target=InternalTarget.RUNTIME_LLM_CHAT,
            auth_type="CUSTOM_APIKEY",
            config_headers=config,
            captured_headers=captured,
        )
        # 请求值优先
        assert result["userid"] == "dave"

    def test_no_captured_headers(self):
        """captured 为 None 时不报错"""
        assert self.profile is not None
        result = resolve_outbound_headers(
            target=InternalTarget.RUNTIME_LLM_CHAT,
            auth_type="API_KEY",
            config_headers={"x-model": "gpt-4"},
            captured_headers=None,
        )
        assert result == {"x-model": "gpt-4"}


class TestProfileConfiguration:
    """CustomerHeaderProfile 配置解析"""

    def __init__(self):
        self.result_profile = None

    def test_profile_enabled(self):
        self.result_profile = _make_profile()
        profile = _make_profile(enabled=True)
        assert profile.is_enabled_in_simple_mode() is True

    def test_profile_disabled(self):
        self.result_profile = _make_profile()
        profile = _make_profile(enabled=False)
        assert profile.is_enabled_in_simple_mode() is False

    def test_capture_allow_list(self):
        self.result_profile = _make_profile()
        profile = _make_profile(capture_allow=["cust-userid", "cust-token", "cust-org"])
        assert profile.get_capture_allow_list() == ["cust-userid", "cust-token", "cust-org"]

    def test_target_mappings(self):
        self.result_profile = _make_profile()
        profile = _make_profile()
        mappings = profile.get_target_mappings(InternalTarget.RUNTIME_LLM_CHAT)
        assert len(mappings) == 2
        assert mappings[0].from_ == "cust-userid"
        assert mappings[0].to == "userid"

    def test_ir_auth_keys_forward_list(self):
        self.result_profile = _make_profile()
        profile = _make_profile()
        fl = profile.get_ir_auth_keys_forward_list()
        assert fl == ["cust-userid", "cust-token"]


class TestReservedBlacklist:
    """RESERVED_BLACKLIST 内容验证"""

    def __init__(self):
        self.blacklist = None

    def test_authorization_in_blacklist(self):
        self.blacklist = RESERVED_BLACKLIST
        assert "authorization" in RESERVED_BLACKLIST

    def test_host_in_blacklist(self):
        self.blacklist = RESERVED_BLACKLIST
        assert "host" in RESERVED_BLACKLIST

    def test_x_forwarded_for_in_blacklist(self):
        self.blacklist = RESERVED_BLACKLIST
        assert "x-forwarded-for" in RESERVED_BLACKLIST

    def test_userid_not_in_blacklist(self):
        """userid 不在黑名单中 (它是合法的 rename 目标)"""
        self.blacklist = RESERVED_BLACKLIST
        assert "userid" not in RESERVED_BLACKLIST

    def test_token_not_in_blacklist(self):
        """token 不在黑名单中"""
        self.blacklist = RESERVED_BLACKLIST
        assert "token" not in RESERVED_BLACKLIST


class TestHeaderValue:
    """HeaderValue 不可变 DTO"""

    def __init__(self):
        self.hv = None

    def test_customer_captured_factory(self):
        self.hv = None
        hv = HeaderValue.customer_captured("Cust-UserId", "alice")
        assert hv.normalized_name == "cust-userid"
        assert hv.value == "alice"
        assert hv.provenance == HeaderProvenance.CUSTOMER_CAPTURED

    def test_platform_generated_factory(self):
        self.hv = None
        hv = HeaderValue.platform_generated("X-Exec-Id", "abc123")
        assert hv.normalized_name == "x-exec-id"
        assert hv.value == "abc123"
        assert hv.provenance == HeaderProvenance.PLATFORM_GENERATED

    def test_frozen_dataclass(self):
        self.hv = None
        hv = HeaderValue.customer_captured("test", "val")
        with pytest.raises(AttributeError):
            hv.value = "changed"