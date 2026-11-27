# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""middleware._capture_customer_headers：profile 开关与伪造入站边界。"""

from types import SimpleNamespace

from common_utils import customer_header
from agent_runtime.context.middleware import _capture_customer_headers


class _Headers(dict):
    def get(self, key, default=None):
        for kk, vv in self.items():
            if str(kk).lower() == str(key).lower():
                return vv
        return default


def _req(headers: dict):
    return SimpleNamespace(headers=_Headers(headers))


def test_profile_disabled_does_not_capture_cust_userid():
    customer_header.set_config(customer_header.CustomerHeaderConfig(enabled=False))
    try:
        out = _capture_customer_headers(_req({"cust-userid": "forged", "cust-token": "t"}))
        assert out == {}
    finally:
        customer_header.set_config(None)


def test_profile_enabled_captures_allow_list_only():
    customer_header.set_config(customer_header.CustomerHeaderConfig(
        enabled=True,
        mappings={"cust-userid": "userId", "cust-token": "token"},
    ))
    try:
        out = _capture_customer_headers(_req({
            "cust-userid": "u1",
            "cust-token": "t1",
            "X-Other": "ignore",
        }))
        assert out.get("cust-userid") == "u1"
        assert out.get("cust-token") == "t1"
        assert "x-other" not in out
    finally:
        customer_header.set_config(None)
