# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.client helper functions (endpoint / body / headers / AttrDict)."""

import pytest

from model_service.client import (
    _AttrDict,
    _build_verbatim_body,
    _build_verbatim_headers,
    _is_verbatim_endpoint,
    _wrap,
)


class TestIsVerbatimEndpoint:
    @staticmethod
    def test_chat_completions_suffix_false():
        assert _is_verbatim_endpoint("http://x/v1/chat/completions") is False

    @staticmethod
    def test_empty_path_false():
        assert _is_verbatim_endpoint("http://x") is False
        assert _is_verbatim_endpoint("http://x/") is False

    @staticmethod
    def test_version_base_false():
        assert _is_verbatim_endpoint("http://x/v1") is False
        assert _is_verbatim_endpoint("http://x/v2") is False

    @staticmethod
    def test_other_path_true():
        assert _is_verbatim_endpoint("http://x/xxx/yyy") is True

    @staticmethod
    def test_empty_url_false():
        assert _is_verbatim_endpoint("") is False

    @staticmethod
    def test_none_false():
        assert _is_verbatim_endpoint(None) is False


class TestBuildVerbatimBody:
    @staticmethod
    def test_removes_transport_keys():
        params = {
            "model": "m",
            "messages": [],
            "extra_headers": {"X": "1"},
            "custom_headers": {"Y": "2"},
            "tracer_foo": "bar",
        }
        body = _build_verbatim_body(params)
        assert body == {"model": "m", "messages": []}

    @staticmethod
    def test_merges_extra_body():
        params = {"model": "m", "extra_body": {"temperature": 0.7}}
        body = _build_verbatim_body(params)
        assert body == {"model": "m", "temperature": 0.7}

    @staticmethod
    def test_non_dict_extra_body_ignored():
        params = {"model": "m", "extra_body": "not-a-dict"}
        body = _build_verbatim_body(params)
        assert body == {"model": "m"}

    @staticmethod
    def test_empty_params():
        assert _build_verbatim_body({}) == {}


class _FakeConn:
    def __init__(self, api_key="k", custom_headers=None):
        self.api_key = api_key
        self.custom_headers = custom_headers


class TestBuildVerbatimHeaders:
    @staticmethod
    def test_api_key_uses_bearer(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(None)
        conn = _FakeConn(api_key="sk-1")
        headers = _build_verbatim_headers(conn, {})
        assert headers["Authorization"] == "Bearer sk-1"
        assert headers["Content-Type"] == "application/json"

    @staticmethod
    def test_custom_headers_no_rename(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(None)
        conn = _FakeConn(custom_headers={"X-A": "v"})
        headers = _build_verbatim_headers(conn, {})
        assert headers["X-A"] == "v"
        assert "Authorization" not in headers

    @staticmethod
    def test_extra_headers_merged(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(None)
        conn = _FakeConn(api_key="k")
        headers = _build_verbatim_headers(conn, {"extra_headers": {"Z": "1"}})
        assert headers["Z"] == "1"

    @staticmethod
    def test_custom_headers_param_merged(reset_common_utils_state):
        from common_utils import customer_header
        customer_header.set_config(None)
        conn = _FakeConn(api_key="k")
        headers = _build_verbatim_headers(conn, {"custom_headers": {"Q": "2"}})
        assert headers["Q"] == "2"


class TestAttrDict:
    @staticmethod
    def test_attribute_access():
        d = _AttrDict({"a": 1, "b": {"c": 2}})
        assert d.a == 1
        assert d.b.c == 2

    @staticmethod
    def test_missing_attribute_returns_none():
        d = _AttrDict({})
        assert d.nonexistent is None

    @staticmethod
    def test_bool():
        assert bool(_AttrDict({})) is False
        assert bool(_AttrDict({"a": 1})) is True

    @staticmethod
    def test_getitem():
        d = _AttrDict({"a": 1})
        assert d["a"] == 1

    @staticmethod
    def test_iter():
        d = _AttrDict({"a": 1, "b": 2})
        assert sorted(list(d)) == ["a", "b"]

    @staticmethod
    def test_len():
        assert len(_AttrDict({"a": 1, "b": 2})) == 2

    @staticmethod
    def test_model_dump():
        d = _AttrDict({"a": 1})
        assert d.model_dump() == {"a": 1}


class TestWrap:
    @staticmethod
    def test_scalar_unchanged():
        assert _wrap(1) == 1
        assert _wrap("x") == "x"
        assert _wrap(None) is None

    @staticmethod
    def test_dict_wrapped():
        w = _wrap({"a": 1})
        assert isinstance(w, _AttrDict)

    @staticmethod
    def test_list_elements_wrapped():
        w = _wrap([{"a": 1}, 2])
        assert isinstance(w[0], _AttrDict)
        assert w[1] == 2
