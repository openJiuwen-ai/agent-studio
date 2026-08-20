# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""_get_function_graph_id 出站 TLS 校验配置单测。

覆盖 S5527/S4830：FunctionGraph 调用由 FG_SSL_VERIFY 控制 TLS 证书与主机名
校验，默认关闭（对齐旧版），开启时 verify 走 True 或 FG_SSL_CA 指定 CA bundle。
"""

from unittest.mock import MagicMock

import pytest

from agent_builder.nl_to_agent.adapter.output_adapter import transform_ir_for_cloud as tfc
from agent_builder.nl_to_agent.adapter.output_adapter.transform_ir_for_cloud import (
    ConvertToEicloud,
)


def _make_adapter():
    """构造最小 ConvertToEicloud 实例，仅满足 _get_function_graph_id 依赖。"""
    adapter = ConvertToEicloud.__new__(ConvertToEicloud)
    adapter.metadata = {
        "project_id": "proj",
        "workspace_id": "ws",
        "x_auth_token": "tok",
    }
    return adapter


def _patch_deps(monkeypatch, captured):
    """屏蔽模块级依赖并捕获 requests.post 的调用参数。"""
    monkeypatch.setattr(tfc, "convert_sandbox_to_fg_code", lambda code: "FG_CODE")
    monkeypatch.setattr(tfc, "get_function_graph_payload", lambda node, code: {"k": "v"})

    fake_requests = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {"data": {"id": "fg-123"}}
    fake_requests.post.return_value = resp

    def capture_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return resp

    fake_requests.post.side_effect = capture_post
    monkeypatch.setattr(tfc, "requests", fake_requests)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """每个用例前后清理 SSL 相关环境变量，避免互相污染。"""
    for key in ("FG_SSL_VERIFY", "FG_SSL_CA"):
        monkeypatch.delenv(key, raising=False)
    yield


class TestFunctionGraphSslVerify:
    def test_default_off(self, monkeypatch):
        captured = {}
        _patch_deps(monkeypatch, captured)
        adapter = _make_adapter()

        result = adapter._get_function_graph_id(node={"id": "n1"}, code="print(1)")

        assert result == "fg-123"
        assert captured["kwargs"]["verify"] is False

    def test_enabled_uses_system_trust(self, monkeypatch):
        monkeypatch.setenv("FG_SSL_VERIFY", "true")
        captured = {}
        _patch_deps(monkeypatch, captured)
        adapter = _make_adapter()

        adapter._get_function_graph_id(node={"id": "n1"}, code="print(1)")

        assert captured["kwargs"]["verify"] is True

    def test_enabled_with_ca_bundle(self, monkeypatch):
        monkeypatch.setenv("FG_SSL_VERIFY", "true")
        monkeypatch.setenv("FG_SSL_CA", "/etc/ssl/internal-ca.pem")
        captured = {}
        _patch_deps(monkeypatch, captured)
        adapter = _make_adapter()

        adapter._get_function_graph_id(node={"id": "n1"}, code="print(1)")

        assert captured["kwargs"]["verify"] == "/etc/ssl/internal-ca.pem"
