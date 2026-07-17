# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for the migrated model-service facade + conditional MODEL_ROUTER_API routing.

Covers:
- The three facade routes are registered on the agent_builder FastAPI app.
- get_nl2_model / get_prompt_optimize_model switch client_provider between
  ``openai`` (gateway) and ``studio`` (direct) based on MODEL_ROUTER_API.
- dispatch.rerank sorts upstream results by index ascending and truncates to top_n.
"""

import asyncio
import types

import pytest

from agent_builder.adapter import model_bridge
from agent_builder.adapter.config_bridge import settings


# ----------------------------- route registration -----------------------------


def _all_paths(routes):
    """Collect all route paths, recursing into FastAPI's _IncludedRouter wrappers."""
    paths = set()
    stack = list(routes)
    while stack:
        r = stack.pop()
        p = getattr(r, "path", None)
        if p is not None:
            paths.add(p)
        orig = getattr(r, "original_router", None)
        if orig is not None:
            stack.extend(getattr(orig, "routes", []))
    return paths


def test_model_service_facade_routes_registered():
    from agent_builder.serve.server_fastapi import app

    routes = _all_paths(app.routes)
    assert "/v1/agent-builder/chat/completions" in routes
    assert "/v1/agent-builder/embeddings" in routes
    assert "/v1/agent-builder/rerank" in routes


# ----------------------------- conditional routing -----------------------------


class _ModelInfo:
    """Minimal stand-in for agent_builder.prompt.common.config.LLMModelInfo."""

    def __init__(self, model, headers=None, temperature=None, top_p=None,
                 url="", api_key=""):
        self.model = model
        self.headers = headers or {}
        self.temperature = temperature
        self.top_p = top_p
        self.url = url
        self.api_key = api_key


def test_nl2_uses_openai_gateway_when_router_api_configured(monkeypatch):
    monkeypatch.setattr(settings.llm, "api_base", "http://gw:31113/v1/agent-builder")
    cfg = model_bridge.Nl2ModelConfigProvider.get_llm_config(
        _ModelInfo("msid", {"auth_id": "a1", "x_auth_token": "tok"})
    )
    assert str(cfg.model_client_config.client_provider).lower() == "openai"
    # 认证头透传给网关
    assert cfg.model_client_config.custom_headers == {
        "X-Auth-Id": "a1", "X-Auth-Token": "tok"
    }


def test_nl2_uses_studio_direct_when_router_api_unconfigured(monkeypatch):
    monkeypatch.setattr(settings.llm, "api_base", "")
    cfg = model_bridge.Nl2ModelConfigProvider.get_llm_config(
        _ModelInfo("signed|msid", {"auth_id": "a1"})
    )
    assert cfg.model_client_config.client_provider == "studio"
    # 薄配置：解析输入放 extra 字段；签名的 modelId 取首段
    assert cfg.model_client_config.model_service_id == "signed|msid".split("|")[0]
    assert cfg.model_client_config.auth_id == "a1"
    assert cfg.model_client_config.api_key == "sk-placeholder"


def test_prompt_optimize_uses_openai_gateway_when_router_api_configured(monkeypatch):
    monkeypatch.setattr(settings.llm, "api_base", "http://gw:31113/v1/agent-builder")
    cfg = model_bridge.PromptOptimizeModelProvider.get_llm_config(
        _ModelInfo("msid", {"auth_id": "a1", "x_auth_token": "tok"})
    )
    assert str(cfg.model_client_config.client_provider).lower() == "openai"


def test_prompt_optimize_uses_studio_direct_when_router_api_unconfigured(monkeypatch):
    monkeypatch.setattr(settings.llm, "api_base", "")
    cfg = model_bridge.PromptOptimizeModelProvider.get_llm_config(
        _ModelInfo("msid", {"auth_id": "a1"})
    )
    assert cfg.model_client_config.client_provider == "studio"
    assert cfg.model_client_config.model_service_id == "msid"
    assert cfg.model_client_config.auth_id == "a1"


async def _await(coro):
    return await coro


def test_get_prompt_optimize_model_is_async_coroutine():
    """get_prompt_optimize_model must return a coroutine (callers await / _run_async it)."""
    import inspect

    coro = model_bridge.get_prompt_optimize_model(_ModelInfo("msid", {"auth_id": "a1"}))
    assert inspect.iscoroutine(coro)
    # drive it to completion to avoid "coroutine never awaited" warning
    asyncio.run(coro)


# ----------------------------- rerank post-processing -----------------------------


def _make_model_auth():
    from model_service.resolver import (
        InterfaceProtocol, ModelServiceBase, ProviderAuth,
    )
    model = ModelServiceBase(
        id="m1", model_name="real-model",
        api_url="http://up/v1/rerank", provider_id="p1",
        interface_protocol=InterfaceProtocol.OPENAI,
        project_id="proj", workspace_id="ws", auth_id="a1",
    )
    auth = ProviderAuth(auth_id="a1", auth_type="API_KEY",
                        auth_info={"api_key": "sk-test"})
    return model, auth


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = str(payload)

    def json(self):
        return self._payload

    async def aclose(self):
        pass


class _FakeClient:
    def __init__(self, payload, status=200):
        self.resp = _FakeResp(payload, status)
        self.closed = False

    async def post(self, url, **kwargs):
        return self.resp

    async def aclose(self):
        self.closed = True


def test_rerank_sorts_by_index_and_truncates_to_top_n(monkeypatch):
    from model_service import dispatch

    model, auth = _make_model_auth()
    payload = {
        "id": "r1", "model": "real-model",
        "results": [
            {"index": 2, "document": {"text": "c"}, "relevance_score": 0.1},
            {"index": 0, "document": {"text": "a"}, "relevance_score": 0.9},
            {"index": 1, "document": {"text": "b"}, "relevance_score": 0.5},
        ],
    }
    fake = _FakeClient(payload)
    monkeypatch.setattr(dispatch, "build_httpx_client",
                        lambda *a, **kw: fake)
    req = types.SimpleNamespace(query="q", docs=["a", "b", "c"], top_n=2)

    data = asyncio.run(dispatch.rerank(model, auth, req))

    assert [r["index"] for r in data["results"]] == [0, 1]  # sorted asc + truncated
    assert fake.closed  # client always closed


def test_rerank_no_top_n_keeps_all_sorted(monkeypatch):
    from model_service import dispatch

    model, auth = _make_model_auth()
    payload = {"results": [
        {"index": 1, "document": {"text": "b"}, "relevance_score": 0.5},
        {"index": 0, "document": {"text": "a"}, "relevance_score": 0.9},
    ]}
    fake = _FakeClient(payload)
    monkeypatch.setattr(dispatch, "build_httpx_client",
                        lambda *a, **kw: fake)
    req = types.SimpleNamespace(query="q", docs=["a", "b"], top_n=None)

    data = asyncio.run(dispatch.rerank(model, auth, req))

    assert [r["index"] for r in data["results"]] == [0, 1]


def test_rerank_raises_on_upstream_error(monkeypatch):
    from model_service import dispatch
    from model_service.resolver import ModelServiceError

    model, auth = _make_model_auth()
    fake = _FakeClient({"error": "boom"}, status=500)
    monkeypatch.setattr(dispatch, "build_httpx_client",
                        lambda *a, **kw: fake)
    req = types.SimpleNamespace(query="q", docs=["a"], top_n=1)

    with pytest.raises(ModelServiceError):
        asyncio.run(dispatch.rerank(model, auth, req))
    assert fake.closed
