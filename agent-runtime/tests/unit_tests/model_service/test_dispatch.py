#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""model_service.dispatch 单元测试。

覆盖 normalize_protocol（OBS 原始字符串归一）+ get_chat_connection（auth→api_key /
custom_headers 映射、api_url 剥离、ANTHROPIC 预留 raise、auth None fail-fast 对应 Java
doChatCompletions 的 MD_PROVIDER_AUTH_DATA_NOT_EXIST）。_settings_llm 打桩避免 settings 依赖。
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from model_service.dispatch import get_chat_connection, normalize_protocol
from model_service.resolver import (
    InterfaceProtocol, ModelServiceBase, ModelServiceError, ProviderAuth,
)


def _model(protocol=InterfaceProtocol.OPENAI, api_url="http://x/v1/chat/completions",
           mid="m1", name="mm"):
    return ModelServiceBase(
        id=mid, model_name=name, api_url=api_url, provider_id="prov1",
        interface_protocol=protocol, project_id="0", workspace_id="w", auth_id="a",
    )


def _auth(auth_type="API_KEY", auth_info=None):
    return ProviderAuth(auth_id="a", auth_type=auth_type,
                         auth_info=auth_info if auth_info is not None else {"api_key": "k1"})


def _llm():
    return SimpleNamespace(timeout=30.0, ssl_verify=False)


# ── normalize_protocol ────────────────────────────────────────────────────────────────────

def test_normalize_protocol_openai_family():
    for raw in ("openai", "standard", "qwen", "zhipu", "multi_openai", "maasv2"):
        assert normalize_protocol(raw) == InterfaceProtocol.OPENAI


def test_normalize_protocol_anthropic():
    assert normalize_protocol("anthropic") == InterfaceProtocol.ANTHROPIC


def test_normalize_protocol_unknown_defaults_openai():
    assert normalize_protocol("") == InterfaceProtocol.OPENAI
    assert normalize_protocol("whatever") == InterfaceProtocol.OPENAI
    assert normalize_protocol(None) == InterfaceProtocol.OPENAI


# ── get_chat_connection ───────────────────────────────────────────────────────────────────

@patch("model_service.dispatch._settings_llm")
def test_get_chat_connection_api_key(mock_llm):
    mock_llm.return_value = _llm()
    conn = get_chat_connection(_model(), _auth("API_KEY", {"api_key": "k1"}))
    assert conn.api_key == "k1"
    assert conn.custom_headers is None
    assert conn.api_base == "http://x/v1"          # 剥离 /chat/completions
    assert conn.model_name == "mm"
    assert conn.interface_protocol == InterfaceProtocol.OPENAI
    assert conn.timeout == 30.0
    assert conn.verify_ssl is False


@patch("model_service.dispatch._settings_llm")
def test_get_chat_connection_custom_apikey(mock_llm):
    mock_llm.return_value = _llm()
    conn = get_chat_connection(_model(), _auth("CUSTOM_APIKEY", {"token": "t"}))
    assert conn.api_key == "sk-placeholder"        # 无 Bearer，占位
    assert conn.custom_headers == {"token": "t"}   # auth_info 直传（cust- 剥离在 _auth_from_data 已做）


@patch("model_service.dispatch._settings_llm")
def test_get_chat_connection_none_auth_fails_fast(mock_llm):
    """对应 Java doChatCompletions：auth 为空 → MD_PROVIDER_AUTH_DATA_NOT_EXIST，不带 placeholder 往下调。"""
    mock_llm.return_value = _llm()
    with pytest.raises(ModelServiceError) as exc:
        get_chat_connection(_model(), None)
    assert exc.value.code == "MD_PROVIDER_AUTH_DATA_NOT_EXIST"


def test_get_chat_connection_anthropic_raises():
    """ANTHROPIC 协议预留接口，当前 raise。"""
    with pytest.raises(ModelServiceError) as exc:
        get_chat_connection(_model(protocol=InterfaceProtocol.ANTHROPIC), _auth())
    assert exc.value.code == "PROTOCOL_NOT_SUPPORTED"


@patch("model_service.dispatch._settings_llm")
def test_get_chat_connection_api_key_empty_falls_to_placeholder(mock_llm):
    """API_KEY 但 auth_info 缺 'API Key' → 占位（防御，由模型端拒）。"""
    mock_llm.return_value = _llm()
    conn = get_chat_connection(_model(), _auth("API_KEY", {}))
    assert conn.api_key == "sk-placeholder"


# ── build_httpx_client（对齐父类 _create_async_openai_client 网络层）─────────────────────────

@patch("httpx.AsyncClient")
@patch("openjiuwen.core.common.security.url_utils.UrlUtils.get_global_proxy_url")
@patch("openjiuwen.core.common.security.ssl_utils.SslUtils.create_strict_ssl_context")
def test_build_httpx_client_verify_true_uses_strict_context_and_proxy(
        mock_strict, mock_proxy, mock_asyncclient):
    """对齐父类：verify_ssl=True → verify=create_strict_ssl_context(ssl_cert)，
    proxy=get_global_proxy_url(api_base)。

    回归 Important#2：studio 路径不再裸 httpx，proxy + ssl_cert 钉扎与父类一致。
    """
    from model_service.dispatch import build_httpx_client
    strict_ctx = object()   # sentinel：证明 verify 传的是 strict context 而非裸 bool
    mock_strict.return_value = strict_ctx
    mock_proxy.return_value = "http://proxy:3128"
    build_httpx_client("http://x/v1", True, ssl_cert="/path/ca.pem")
    mock_strict.assert_called_once_with("/path/ca.pem")
    mock_proxy.assert_called_once_with("http://x/v1")
    _, kwargs = mock_asyncclient.call_args
    assert kwargs["proxy"] == "http://proxy:3128"
    assert kwargs["verify"] is strict_ctx


@patch("httpx.AsyncClient")
@patch("openjiuwen.core.common.security.url_utils.UrlUtils.get_global_proxy_url")
def test_build_httpx_client_verify_false_passthrough_no_strict_context(
        mock_proxy, mock_asyncclient):
    """verify_ssl=False → verify=False（不建 strict context，对齐父类 verify_ssl else 分支），proxy 仍按 env 判定。"""
    from model_service.dispatch import build_httpx_client
    mock_proxy.return_value = None   # 无 env 代理
    build_httpx_client("http://x/v1", False)
    _, kwargs = mock_asyncclient.call_args
    assert kwargs["verify"] is False
    assert kwargs["proxy"] is None
