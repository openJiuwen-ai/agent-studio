# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for customer header rename in verbatim headers (enabled config)."""

from model_service.client import (
    _build_verbatim_headers,
    _cust_userid_for_static_override,
    _override_static_cust_userid,
)


class _Conn:
    def __init__(self, api_key="k", custom_headers=None):
        self.api_key = api_key
        self.custom_headers = custom_headers


class TestOverrideStaticCustUserid:
    """#1728/#1761：静态 cust-userid 替换为请求用户。"""

    @staticmethod
    def test_override_replaces_cust_userid():
        out = _override_static_cust_userid(
            {"cust-userid": "static-1", "X-Other": "v"}, "login-42"
        )
        assert out["cust-userid"] == "login-42"
        assert out["X-Other"] == "v"

    @staticmethod
    def test_override_case_insensitive_key():
        out = _override_static_cust_userid({"Cust-UserId": "old"}, "u-9")
        assert out["Cust-UserId"] == "u-9"

    @staticmethod
    def test_override_noop_without_user_or_headers():
        assert _override_static_cust_userid({"cust-userid": "1"}, "") == {"cust-userid": "1"}
        assert _override_static_cust_userid({}, "u") == {}
        assert _override_static_cust_userid(None, "u") == {}


class TestCustUseridForStaticOverride:
    """仅 debug + 登录 user_id；入站伪造 header 永不覆盖。"""

    @staticmethod
    def test_published_with_forged_inbound_does_not_override(
        monkeypatch, reset_model_service_ports
    ):
        from model_service import ports
        ports.set_request_customer_headers(lambda: {"cust-userid": "forged-client"})
        ports.set_invoke_mode(lambda: "PUBLISHED")
        ports.set_request_user_id(lambda: "login-uid")
        monkeypatch.setattr(
            "model_service.client._is_studio_trial_invoke",
            lambda: False,
        )
        assert _cust_userid_for_static_override() == ""

    @staticmethod
    def test_trial_uses_login_user_not_inbound(
        monkeypatch, reset_model_service_ports
    ):
        from model_service import ports
        ports.set_request_customer_headers(lambda: {"cust-userid": "forged-or-stale"})
        ports.set_invoke_mode(lambda: "debug")
        ports.set_request_user_id(lambda: "login-uid")
        monkeypatch.setattr(
            "model_service.client._is_studio_trial_invoke", lambda: True
        )
        monkeypatch.setattr(
            "model_service.client._effective_request_user_id", lambda: "login-uid"
        )
        assert _cust_userid_for_static_override() == "login-uid"

    @staticmethod
    def test_trial_debug_falls_back_to_login_user(monkeypatch, reset_model_service_ports):
        monkeypatch.setattr(
            "model_service.client._is_studio_trial_invoke", lambda: True
        )
        monkeypatch.setattr(
            "model_service.client._effective_request_user_id", lambda: "login-uid"
        )
        assert _cust_userid_for_static_override() == "login-uid"

    @staticmethod
    def test_published_keeps_static_without_inbound(monkeypatch, reset_model_service_ports):
        monkeypatch.setattr(
            "model_service.client._is_studio_trial_invoke", lambda: False
        )
        monkeypatch.setattr(
            "model_service.client._effective_request_user_id", lambda: "login-uid"
        )
        assert _cust_userid_for_static_override() == ""

    @staticmethod
    def test_ports_drive_trial_and_user_id(reset_model_service_ports):
        from model_service import ports
        ports.set_invoke_mode(lambda: "debug")
        ports.set_request_user_id(lambda: "uid-from-port")
        assert _cust_userid_for_static_override() == "uid-from-port"
        ports.set_invoke_mode(lambda: "PUBLISHED")
        assert _cust_userid_for_static_override() == ""


class TestVerbatimHeadersRename:
    @staticmethod
    def test_custom_headers_renamed_when_enabled(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(customer_header.CustomerHeaderConfig(
            enabled=True, mappings={"cust-userid": "userId"},
        ))
        conn = _Conn(custom_headers={"cust-userid": "42", "X-Other": "v"})
        headers = _build_verbatim_headers(conn, {})
        assert headers["userId"] == "42"
        assert headers["X-Other"] == "v"

    @staticmethod
    def test_custom_headers_renamed_missing_value(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(customer_header.CustomerHeaderConfig(
            enabled=True, mappings={"cust-userid": "userId"},
        ))
        conn = _Conn(custom_headers={"X-Other": "v"})
        headers = _build_verbatim_headers(conn, {})
        # 无 cust-userid 时不产生 userId。
        assert "userId" not in headers
        assert headers["X-Other"] == "v"

    @staticmethod
    def test_rename_fallback_to_original_when_resolve_empty(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(customer_header.CustomerHeaderConfig(
            enabled=True, mappings={"cust-userid": "userId"},
        ))
        conn = _Conn(custom_headers={"cust-userid": "42"})
        headers = _build_verbatim_headers(conn, {})
        assert headers["userId"] == "42"

    @staticmethod
    def test_disabled_config_no_rename(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(customer_header.CustomerHeaderConfig(enabled=False))
        conn = _Conn(custom_headers={"cust-userid": "42"})
        headers = _build_verbatim_headers(conn, {})
        # disabled 时 capture_keys 为空，不 rename，直接透传。
        assert headers["cust-userid"] == "42"

    @staticmethod
    def test_extra_headers_still_merged_with_rename(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(customer_header.CustomerHeaderConfig(
            enabled=True, mappings={"cust-token": "token"},
        ))
        conn = _Conn(custom_headers={"cust-token": "t1"})
        headers = _build_verbatim_headers(conn, {"extra_headers": {"Z": "1"}})
        assert headers["token"] == "t1"
        assert headers["Z"] == "1"

    @staticmethod
    def test_static_cust_userid_replaced_on_trial_debug(
        reset_common_utils_state, monkeypatch
    ):
        from common_utils import customer_header
        import model_service.client as client_mod

        customer_header.set_config(customer_header.CustomerHeaderConfig(
            enabled=True, mappings={"cust-userid": "userId"},
        ))
        monkeypatch.setattr(client_mod, "_cust_userid_for_static_override", lambda: "login-uid")
        conn = _Conn(custom_headers={"cust-userid": "static-from-model", "X-Other": "v"})
        headers = _build_verbatim_headers(conn, {})
        assert headers["userId"] == "login-uid"
        assert headers["X-Other"] == "v"

    @staticmethod
    def test_published_keeps_static_cust_userid(
        reset_common_utils_state, monkeypatch
    ):
        from common_utils import customer_header
        import model_service.client as client_mod

        customer_header.set_config(customer_header.CustomerHeaderConfig(
            enabled=True, mappings={"cust-userid": "userId"},
        ))
        monkeypatch.setattr(client_mod, "_cust_userid_for_static_override", lambda: "")
        monkeypatch.setattr(client_mod, "_effective_request_user_id", lambda: "login-uid")
        conn = _Conn(custom_headers={"cust-userid": "static-from-model", "X-Other": "v"})
        headers = _build_verbatim_headers(conn, {})
        assert headers["userId"] == "static-from-model"
        assert headers["X-Other"] == "v"
