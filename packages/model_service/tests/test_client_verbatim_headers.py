# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for customer header rename in verbatim headers (enabled config)."""

from model_service.client import _build_verbatim_headers


class _Conn:
    def __init__(self, api_key="k", custom_headers=None):
        self.api_key = api_key
        self.custom_headers = custom_headers


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
