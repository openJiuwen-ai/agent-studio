# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.dispatch."""

import pytest

from model_service.dispatch import (
    _normalize_api_base,
    get_chat_connection,
    normalize_protocol,
)
from model_service.resolver import (
    InterfaceProtocol,
    ModelServiceBase,
    ModelServiceError,
    ProviderAuth,
)


def _model(**kwargs):
    defaults = dict(
        id="m1", model_name="gpt-x", api_url="http://x/v1",
        provider_id="p", interface_protocol=InterfaceProtocol.OPENAI,
        project_id="proj", workspace_id="ws", auth_id="a",
    )
    defaults.update(kwargs)
    return ModelServiceBase(**defaults)


class TestNormalizeProtocol:
    def test_openai(self):
        assert normalize_protocol("openai") is InterfaceProtocol.OPENAI

    def test_multi_openai(self):
        assert normalize_protocol("multi_openai") is InterfaceProtocol.OPENAI

    def test_maasv2(self):
        assert normalize_protocol("maasv2") is InterfaceProtocol.OPENAI

    def test_qwen(self):
        assert normalize_protocol("qwen") is InterfaceProtocol.OPENAI

    def test_zhipu(self):
        assert normalize_protocol("zhipu") is InterfaceProtocol.OPENAI

    def test_standard(self):
        assert normalize_protocol("standard") is InterfaceProtocol.OPENAI

    def test_anthropic(self):
        assert normalize_protocol("anthropic") is InterfaceProtocol.ANTHROPIC

    def test_unknown_defaults_openai(self):
        assert normalize_protocol("unknown") is InterfaceProtocol.OPENAI

    def test_none_defaults_openai(self):
        assert normalize_protocol(None) is InterfaceProtocol.OPENAI

    def test_case_insensitive(self):
        assert normalize_protocol("OPENAI") is InterfaceProtocol.OPENAI

    def test_whitespace_trimmed(self):
        assert normalize_protocol("  openai  ") is InterfaceProtocol.OPENAI


class TestNormalizeApiBase:
    def test_strips_chat_completions(self):
        assert _normalize_api_base("http://x/v1/chat/completions") == "http://x/v1"

    def test_no_suffix_unchanged(self):
        assert _normalize_api_base("http://x/v1") == "http://x/v1"

    def test_strips_trailing_slash(self):
        assert _normalize_api_base("http://x/v1/") == "http://x/v1"

    def test_empty_returns_empty(self):
        assert _normalize_api_base("") == ""

    def test_none_returns_empty(self):
        assert _normalize_api_base(None) == ""


class TestGetChatConnection:
    def test_anthropic_raises(self, reset_model_service_ports):
        model = _model(interface_protocol=InterfaceProtocol.ANTHROPIC)
        auth = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "k"})
        with pytest.raises(ModelServiceError) as exc_info:
            get_chat_connection(model, auth)
        assert exc_info.value.code == "PROTOCOL_NOT_SUPPORTED"

    def test_auth_none_raises(self, reset_model_service_ports):
        model = _model()
        with pytest.raises(ModelServiceError) as exc_info:
            get_chat_connection(model, None)
        assert exc_info.value.code == "MD_PROVIDER_AUTH_DATA_NOT_EXIST"

    def test_api_key_auth(self, reset_model_service_ports):
        from model_service import ports

        class _Settings:
            timeout = 30.0
            ssl_verify = False

        ports.set_llm_settings(lambda: _Settings())

        model = _model(api_url="http://x/v1/chat/completions")
        auth = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "sk-1"})
        conn = get_chat_connection(model, auth)
        assert conn.api_key == "sk-1"
        assert conn.custom_headers is None
        assert conn.api_base == "http://x/v1"
        assert conn.model_name == "gpt-x"
        assert conn.timeout == 30.0
        assert conn.verify_ssl is False

    def test_api_key_missing_uses_placeholder(self, reset_model_service_ports):
        from model_service import ports

        class _Settings:
            timeout = 10.0
            ssl_verify = True

        ports.set_llm_settings(lambda: _Settings())

        model = _model()
        auth = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={})
        conn = get_chat_connection(model, auth)
        assert conn.api_key == "sk-placeholder"

    def test_custom_apikey_auth(self, reset_model_service_ports):
        from model_service import ports

        class _Settings:
            timeout = 10.0
            ssl_verify = True

        ports.set_llm_settings(lambda: _Settings())

        model = _model()
        auth = ProviderAuth(
            auth_id="a", auth_type="CUSTOM_APIKEY",
            auth_info={"X-Header": "val"},
        )
        conn = get_chat_connection(model, auth)
        assert conn.custom_headers == {"X-Header": "val"}
        assert conn.api_key == "sk-placeholder"
