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
    @staticmethod
    def test_openai():
        assert normalize_protocol("openai") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_multi_openai():
        assert normalize_protocol("multi_openai") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_maasv2():
        assert normalize_protocol("maasv2") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_qwen():
        assert normalize_protocol("qwen") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_zhipu():
        assert normalize_protocol("zhipu") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_standard():
        assert normalize_protocol("standard") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_anthropic():
        assert normalize_protocol("anthropic") is InterfaceProtocol.ANTHROPIC

    @staticmethod
    def test_unknown_defaults_openai():
        assert normalize_protocol("unknown") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_none_defaults_openai():
        assert normalize_protocol(None) is InterfaceProtocol.OPENAI

    @staticmethod
    def test_case_insensitive():
        assert normalize_protocol("OPENAI") is InterfaceProtocol.OPENAI

    @staticmethod
    def test_whitespace_trimmed():
        assert normalize_protocol("  openai  ") is InterfaceProtocol.OPENAI


class TestNormalizeApiBase:
    @staticmethod
    def test_strips_chat_completions():
        assert _normalize_api_base("http://x/v1/chat/completions") == "http://x/v1"

    @staticmethod
    def test_no_suffix_unchanged():
        assert _normalize_api_base("http://x/v1") == "http://x/v1"

    @staticmethod
    def test_strips_trailing_slash():
        assert _normalize_api_base("http://x/v1/") == "http://x/v1"

    @staticmethod
    def test_empty_returns_empty():
        assert _normalize_api_base("") == ""

    @staticmethod
    def test_none_returns_empty():
        assert _normalize_api_base(None) == ""


class TestGetChatConnection:
    @staticmethod
    def test_anthropic_raises(reset_model_service_ports):
        model = _model(interface_protocol=InterfaceProtocol.ANTHROPIC)
        auth = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "k"})
        with pytest.raises(ModelServiceError) as exc_info:
            get_chat_connection(model, auth)
        assert exc_info.value.code == "PROTOCOL_NOT_SUPPORTED"

    @staticmethod
    def test_auth_none_raises(reset_model_service_ports):
        model = _model()
        with pytest.raises(ModelServiceError) as exc_info:
            get_chat_connection(model, None)
        assert exc_info.value.code == "MD_PROVIDER_AUTH_DATA_NOT_EXIST"

    @staticmethod
    def test_api_key_auth(reset_model_service_ports):
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

    @staticmethod
    def test_api_key_missing_uses_placeholder(reset_model_service_ports):
        from model_service import ports

        class _Settings:
            timeout = 10.0
            ssl_verify = True

        ports.set_llm_settings(lambda: _Settings())

        model = _model()
        auth = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={})
        conn = get_chat_connection(model, auth)
        assert conn.api_key == "sk-placeholder"

    @staticmethod
    def test_custom_apikey_auth(reset_model_service_ports):
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
