# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access

"""SSL 相关路径单测。

覆盖：
- ``_get_aiohttp_ssl`` 各分支（SSLContext 透传 / 字符串 / bool / legacy 开关）
- ``_load_cert`` 不再改写 ``request_params.api_cert``，仅加载证书链
- 异步轮询 ``check_request`` 沿用 legacy SSL 配置
- ``net._get_ssl_config`` 的「未设置 vs 显式 false」区分
"""

import asyncio
import ssl
from types import SimpleNamespace

import pytest

from jiuwen.common import net as net_module
from jiuwen.common.configs.env_constants import (
    EXECUTION_NODE_TIMEOUT_KEY,
    PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION_KEY,
    PLUGIN_SSL_API_CERT_KEY,
)
from jiuwen.extension.wrapper import restful_api_new as api_module

_TOOL = api_module.RestfulApiToolNew


class _FakeCtx:
    """记录 load_cert_chain 调用的假 SSLContext。"""

    def __init__(self):
        self.loaded = []

    def load_cert_chain(self, certfile):  # pylint: disable=missing-function-docstring
        self.loaded.append(certfile)


class _FakePostResponse:
    async def json(self):
        return {"task_id": "task-1"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self):
        self.post_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, **kwargs):
        self.post_kwargs = kwargs
        return _FakePostResponse()


@pytest.fixture
def legacy_on(monkeypatch):
    monkeypatch.setattr(api_module, "_allow_legacy_renegotiation", True)
    monkeypatch.setattr(api_module, "_legacy_ssl_context", None)
    monkeypatch.setattr(api_module, "_legacy_ssl_context_no_verify", None)


@pytest.fixture
def legacy_off(monkeypatch):
    monkeypatch.setattr(api_module, "_allow_legacy_renegotiation", False)


class TestGetAiohttpSsl:
    """RestfulApiToolNew._get_aiohttp_ssl 分支"""

    @staticmethod
    def test_ssl_context_passthrough(legacy_on):
        ctx = ssl.create_default_context()
        assert _TOOL._get_aiohttp_ssl(None, ctx) is ctx

    @staticmethod
    def test_legacy_str_returns_legacy_context(legacy_on):
        result = _TOOL._get_aiohttp_ssl(None, "/tmp/cert.pem")
        assert result is api_module._get_legacy_ssl_context()

    @staticmethod
    def test_legacy_true_returns_verifying_context(legacy_on):
        result = _TOOL._get_aiohttp_ssl(None, True)
        assert isinstance(result, ssl.SSLContext)
        assert result.verify_mode == ssl.CERT_REQUIRED
        assert result.check_hostname is True

    @staticmethod
    def test_legacy_false_returns_non_verifying_context(legacy_on):
        result = _TOOL._get_aiohttp_ssl(None, False)
        assert isinstance(result, ssl.SSLContext)
        assert result.verify_mode == ssl.CERT_NONE
        assert result.check_hostname is False

    @staticmethod
    def test_legacy_bool_context_is_cached(legacy_on):
        first = _TOOL._get_aiohttp_ssl(None, False)
        second = _TOOL._get_aiohttp_ssl(None, False)
        assert first is second, "重复调用不应重建 SSLContext（会重读系统 CA）"

    @staticmethod
    def test_non_legacy_str_returns_shared_context(legacy_off):
        assert _TOOL._get_aiohttp_ssl(None, "/tmp/cert.pem") is api_module._ssl_context

    @staticmethod
    def test_non_legacy_bool_passthrough(legacy_off):
        assert _TOOL._get_aiohttp_ssl(None, False) is False
        assert _TOOL._get_aiohttp_ssl(None, True) is True


class TestLoadCert:
    """RestfulApiToolNew._load_cert 不改写 api_cert 原值"""

    @staticmethod
    def test_legacy_str_not_mutated_and_loaded_once(monkeypatch, legacy_on):
        fake_ctx = _FakeCtx()
        monkeypatch.setattr(api_module, "_get_legacy_ssl_context", lambda: fake_ctx)
        monkeypatch.setattr(api_module, "_legacy_ssl_context_cert_loaded", False)
        request_params = SimpleNamespace(api_cert="/tmp/cert.pem")

        _TOOL._load_cert(None, request_params)
        _TOOL._load_cert(None, request_params)

        assert request_params.api_cert == "/tmp/cert.pem"
        assert fake_ctx.loaded == ["/tmp/cert.pem"]

    @staticmethod
    def test_non_legacy_str_not_mutated(monkeypatch, legacy_off):
        fake_ctx = _FakeCtx()
        monkeypatch.setattr(api_module, "_ssl_context", fake_ctx)
        monkeypatch.setattr(api_module, "_is_cert_loaded", False)
        request_params = SimpleNamespace(api_cert="/tmp/cert.pem")

        _TOOL._load_cert(None, request_params)

        assert request_params.api_cert == "/tmp/cert.pem"
        assert fake_ctx.loaded == ["/tmp/cert.pem"]

    @staticmethod
    def test_bool_kept_unchanged(legacy_on):
        request_params = SimpleNamespace(api_cert=False)
        _TOOL._load_cert(None, request_params)
        assert request_params.api_cert is False


class TestAsyncCheckRequestSsl:
    """异步轮询 check_request 沿用 legacy SSL 配置"""

    @staticmethod
    def test_check_request_uses_legacy_ssl(monkeypatch, legacy_on):
        captured = {}

        async def fake_schedule(interval, check_request, session):
            captured.update(check_request)
            return {"ok": True}

        monkeypatch.setenv(EXECUTION_NODE_TIMEOUT_KEY, "100")
        fake_session = _FakeSession()

        class _FakeConnector:
            def get_tcp_connector(self):
                return None

        monkeypatch.setattr(api_module, "Connector", _FakeConnector)
        monkeypatch.setattr(
            api_module.aiohttp, "ClientSession", lambda **kwargs: fake_session
        )

        tool = object.__new__(_TOOL)
        tool._async_conf = {
            "max_timeout": 10,
            "period_of_round": 1,
            "callback_url": "http://callback/",
        }
        tool._schedule_check_task = fake_schedule
        request_params = SimpleNamespace(
            ip_address_url="http://plugin/run",
            api_cert=False,
            file_params=None,
            headers={},
            request_arg={},
        )

        result = asyncio.run(tool._send_async_post_request(request_params))

        assert result == {"ok": True}
        assert captured["url"] == "http://callback/task-1"
        check_ssl = captured["ssl"]
        assert isinstance(check_ssl, ssl.SSLContext)
        assert check_ssl.verify_mode == ssl.CERT_NONE
        assert fake_session.post_kwargs["ssl"] is check_ssl, "初始 POST 与轮询应使用同一 legacy 配置"


class TestNetSslConfig:
    """net._get_ssl_config 默认值与显式开关"""

    @staticmethod
    def test_unset_defaults_to_legacy_enabled(monkeypatch):
        monkeypatch.delenv(PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION_KEY, raising=False)
        assert net_module._is_legacy_renegotiation_enabled() is True

        monkeypatch.delenv(PLUGIN_SSL_API_CERT_KEY, raising=False)
        result = net_module._get_ssl_config()
        assert isinstance(result, ssl.SSLContext)
        assert result.verify_mode == ssl.CERT_REQUIRED

    @staticmethod
    @pytest.mark.parametrize("raw", ["true", "True", "TRUE"])
    def test_legacy_flag_case_insensitive(monkeypatch, raw):
        monkeypatch.setenv(PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION_KEY, raw)
        assert net_module._is_legacy_renegotiation_enabled() is True

    @staticmethod
    def test_explicit_false_disables_legacy(monkeypatch):
        monkeypatch.setenv(PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION_KEY, "False")
        assert net_module._is_legacy_renegotiation_enabled() is False

        monkeypatch.delenv(PLUGIN_SSL_API_CERT_KEY, raising=False)
        assert net_module._get_ssl_config() is True

        monkeypatch.setenv(PLUGIN_SSL_API_CERT_KEY, "false")
        assert net_module._get_ssl_config() is False

    @staticmethod
    def test_legacy_enabled_with_api_cert_false_disables_verify(monkeypatch):
        monkeypatch.delenv(PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION_KEY, raising=False)
        monkeypatch.setenv(PLUGIN_SSL_API_CERT_KEY, "false")
        result = net_module._get_ssl_config()
        assert isinstance(result, ssl.SSLContext)
        assert result.verify_mode == ssl.CERT_NONE
        assert result.check_hostname is False
