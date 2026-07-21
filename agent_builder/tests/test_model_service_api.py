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
import json
import types

import httpx
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
    assert "/v1/{project_id}/model-service/status/check" in routes


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


def test_nl2_uses_ir_gateway_when_strategy_ir(monkeypatch):
    monkeypatch.setattr(settings.llm, "model_config_strategy", model_bridge.ModelConfigStrategyType.IR)
    monkeypatch.setattr(settings.llm, "api_base", "http://model-gateway:8080/v1/agent-builder")
    cfg = model_bridge.Nl2ModelConfigProvider.get_llm_config(
        _ModelInfo("msid", {"auth_id": "a1", "x_auth_token": "tok"})
    )
    assert str(cfg.model_client_config.client_provider).lower() == "openai"
    # 认证头透传给网关
    assert cfg.model_client_config.custom_headers == {
        "X-Auth-Id": "a1", "X-Auth-Token": "tok"
    }


def test_nl2_uses_studio_direct_when_strategy_obs(monkeypatch):
    monkeypatch.setattr(settings.llm, "model_config_strategy", model_bridge.ModelConfigStrategyType.OBS)
    cfg = model_bridge.Nl2ModelConfigProvider.get_llm_config(
        _ModelInfo("signed|msid", {"auth_id": "a1"})
    )
    assert cfg.model_client_config.client_provider == "studio"
    # 薄配置：解析输入放 extra 字段；签名的 modelId 取首段
    assert cfg.model_client_config.model_service_id == "signed|msid".split("|")[0]
    assert cfg.model_client_config.auth_id == "a1"
    assert cfg.model_client_config.api_key == "sk-placeholder"


def test_nl2_uses_env_vars_when_strategy_env(monkeypatch):
    monkeypatch.setattr(settings.llm, "model_config_strategy", model_bridge.ModelConfigStrategyType.ENV)
    monkeypatch.setenv("IR_LLM_API_BASE", "https://env.example.com")
    cfg = model_bridge.Nl2ModelConfigProvider.get_llm_config(
        _ModelInfo("my-model", {"auth_id": "a1"})
    )
    assert str(cfg.model_client_config.client_provider).lower() == "openai"
    assert cfg.model_client_config.api_base == "https://env.example.com"


def test_prompt_optimize_uses_ir_gateway_when_strategy_ir(monkeypatch):
    monkeypatch.setattr(settings.llm, "model_config_strategy", model_bridge.ModelConfigStrategyType.IR)
    monkeypatch.setattr(settings.llm, "api_base", "http://model-gateway:8080/v1/agent-builder")
    cfg = model_bridge.PromptOptimizeModelProvider.get_llm_config(
        _ModelInfo("msid", {"auth_id": "a1", "x_auth_token": "tok"})
    )
    assert str(cfg.model_client_config.client_provider).lower() == "openai"


def test_prompt_optimize_uses_studio_direct_when_strategy_obs(monkeypatch):
    monkeypatch.setattr(settings.llm, "model_config_strategy", model_bridge.ModelConfigStrategyType.OBS)
    cfg = model_bridge.PromptOptimizeModelProvider.get_llm_config(
        _ModelInfo("msid", {"auth_id": "a1"})
    )
    assert cfg.model_client_config.client_provider == "studio"
    assert cfg.model_client_config.model_service_id == "msid"
    assert cfg.model_client_config.auth_id == "a1"


def test_prompt_optimize_uses_env_vars_when_strategy_env(monkeypatch):
    monkeypatch.setattr(settings.llm, "model_config_strategy", model_bridge.ModelConfigStrategyType.ENV)
    monkeypatch.setenv("IR_LLM_API_BASE", "https://env.example.com")
    cfg = model_bridge.PromptOptimizeModelProvider.get_llm_config(
        _ModelInfo("my-model", {})
    )
    assert str(cfg.model_client_config.client_provider).lower() == "openai"
    assert cfg.model_client_config.api_base == "https://env.example.com"


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


# ----------------------------- status check -----------------------------


def test_build_check_invoke_body_per_model_type():
    from agent_builder.serve.apis.model_service_api import _build_check_invoke_body

    chat = _build_check_invoke_body("LLM", "m1")
    assert chat == {"model": "m1", "stream": False,
                    "messages": [{"role": "user", "content": "你好"}]}
    # IMAGE-TO-TEXT 走与 LLM 相同的 chat 探针
    assert _build_check_invoke_body("image-to-text", "m1") == chat

    emb = _build_check_invoke_body("TEXT-EMBEDDING", "m1")
    assert emb == {"model": "m1", "input": "你好"}

    rerank = _build_check_invoke_body("RERANK", "m1")
    assert rerank == {"model": "m1", "query": "a", "documents": ["a", "b"]}

    # 不支持的 model_type → None（对应 Java default 分支）
    assert _build_check_invoke_body("TEXT-TO-IMAGE", "m1") is None


def test_check_auth_headers_api_key_uses_api_key_field():
    from agent_builder.serve.apis.model_service_api import _check_auth_headers

    headers = _check_auth_headers("API_KEY", {"API Key": "sk-real"})
    assert headers["Authorization"] == "Bearer sk-real"
    assert headers["Content-Type"] == "application/json"


def test_check_auth_headers_custom_apikey_strips_cust_prefix():
    from agent_builder.serve.apis.model_service_api import _check_auth_headers

    headers = _check_auth_headers("CUSTOM_APIKEY", {
        "Cust-Token": "tok", "X-Custom": "v", "Cust-UserId": "u"
    })
    assert headers["token"] == "tok"      # cust- 前缀剥离 + 小写
    assert headers["userid"] == "u"
    assert headers["x-custom"] == "v"     # 非 cust-token/userid 仅小写
    assert "Authorization" not in headers


def test_check_auth_headers_no_auth_adds_no_authorization():
    from agent_builder.serve.apis.model_service_api import _check_auth_headers

    headers = _check_auth_headers("NO_AUTH", {})
    assert "Authorization" not in headers
    assert headers["Content-Type"] == "application/json"


def _check_req(model_type="LLM", auth_type="API_KEY", **overrides):
    base = {
        "model_type": model_type,
        "api_url": "http://up/v1/chat/completions",
        "auth_type": auth_type,
        "auth_info": {"API Key": "sk-test"},
        "model_name": "m1",
        "interface_protocol": "openai",
    }
    base.update(overrides)
    from agent_builder.serve.apis.model_service_api import ModelServiceCheckReq
    return ModelServiceCheckReq(**base)


class _CheckResp:
    def __init__(self, status, text="err"):
        self.status_code = status
        self.text = text


class _CheckClient:
    def __init__(self, status, text="err"):
        self.resp = _CheckResp(status, text)
        self.closed = False
        self.posted = None

    async def post(self, url, **kwargs):
        self.posted = (url, kwargs)
        return self.resp

    async def aclose(self):
        self.closed = True


def _patch_httpx(monkeypatch, client):
    from model_service import dispatch
    monkeypatch.setattr(dispatch, "build_httpx_client", lambda *a, **kw: client)


def test_status_check_success_returns_200(monkeypatch):
    from agent_builder.serve.apis.model_service_api import model_service_status_check

    fake = _CheckClient(200)
    _patch_httpx(monkeypatch, fake)
    rsp = asyncio.run(model_service_status_check("proj", _check_req()))
    body = json.loads(rsp.body)
    assert body["success"] is True
    assert body["status_code"] == 200
    assert fake.closed
    # 探针体带最小 chat 请求
    posted_body = fake.posted[1]["json"]
    assert posted_body["messages"][0]["content"] == "你好"
    # API_KEY → Bearer
    assert fake.posted[1]["headers"]["Authorization"] == "Bearer sk-test"


def test_status_check_400_treated_as_success(monkeypatch):
    from agent_builder.serve.apis.model_service_api import model_service_status_check

    fake = _CheckClient(400, "bad request")
    _patch_httpx(monkeypatch, fake)
    rsp = asyncio.run(model_service_status_check("proj", _check_req()))
    body = json.loads(rsp.body)
    assert body["success"] is True      # 400 → 端点可达即通过
    assert body["status_code"] == 400
    assert body["reason"] == "bad request"


def test_status_check_401_is_failure(monkeypatch):
    from agent_builder.serve.apis.model_service_api import model_service_status_check

    fake = _CheckClient(401, "unauthorized")
    _patch_httpx(monkeypatch, fake)
    rsp = asyncio.run(model_service_status_check("proj", _check_req()))
    body = json.loads(rsp.body)
    assert body["success"] is False
    assert body["status_code"] == 401
    assert body["reason"] == "unauthorized"


def test_status_check_network_error_returns_500(monkeypatch):
    from agent_builder.serve.apis.model_service_api import model_service_status_check

    class _BoomClient(_CheckClient):
        async def post(self, url, **kwargs):
            raise httpx.ConnectError("boom")

    fake = _BoomClient(200)
    _patch_httpx(monkeypatch, fake)
    rsp = asyncio.run(model_service_status_check("proj", _check_req()))
    body = json.loads(rsp.body)
    assert body["success"] is False
    assert body["status_code"] == 500


def test_status_check_unsupported_model_type_short_circuits(monkeypatch):
    from agent_builder.serve.apis.model_service_api import model_service_status_check

    fake = _CheckClient(200)
    _patch_httpx(monkeypatch, fake)
    rsp = asyncio.run(model_service_status_check(
        "proj", _check_req(model_type="TEXT-TO-IMAGE")
    ))
    body = json.loads(rsp.body)
    assert body["success"] is True
    assert body["reason"] == "model type is not support to check."
    # 未发起任何上游调用
    assert fake.posted is None
