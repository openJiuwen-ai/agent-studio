# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.dispatch.build_httpx_client."""

import httpx
import openjiuwen.core.common.security.ssl_utils as ssl_utils_mod
import openjiuwen.core.common.security.url_utils as url_utils_mod

from model_service.dispatch import build_httpx_client


class _FakeAsyncClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeSslContext:
    pass


class _FakeSslUtils:
    @staticmethod
    def create_strict_ssl_context(ssl_cert):
        return _FakeSslContext()


class _FakeUrlUtils:
    @staticmethod
    def get_global_proxy_url(api_base):
        return f"proxy://for/{api_base}"


def _install(monkeypatch):
    # build_httpx_client 在函数体内延迟 import，须替换 openjiuwen 源模块的符号。
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(ssl_utils_mod, "SslUtils", _FakeSslUtils)
    monkeypatch.setattr(url_utils_mod, "UrlUtils", _FakeUrlUtils)


class TestBuildHttpxClient:
    def test_verify_ssl_true_builds_context(self, monkeypatch):
        _install(monkeypatch)
        client = build_httpx_client("http://api", True, ssl_cert="/ca.pem")
        assert isinstance(client, _FakeAsyncClient)
        assert isinstance(client.kwargs["verify"], _FakeSslContext)
        assert client.kwargs["proxy"] == "proxy://for/http://api"

    def test_verify_ssl_false_passes_false(self, monkeypatch):
        _install(monkeypatch)
        client = build_httpx_client("http://api", False)
        assert client.kwargs["verify"] is False
        assert client.kwargs["proxy"] == "proxy://for/http://api"

    def test_ssl_cert_default_none(self, monkeypatch):
        _install(monkeypatch)
        client = build_httpx_client("http://api", True)
        assert isinstance(client.kwargs["verify"], _FakeSslContext)

    def test_api_base_used_for_proxy(self, monkeypatch):
        _install(monkeypatch)
        client = build_httpx_client("https://other", False)
        assert client.kwargs["proxy"] == "proxy://for/https://other"
