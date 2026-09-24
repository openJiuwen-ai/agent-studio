# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.resolver (pure helpers / auth & model construction)."""

import json

import pytest

from model_service.resolver import (
    AUTH_LIST_PATH,
    AUTH_PATH,
    MODEL_PATH,
    PLATFORM_PROJECT_IDS,
    InterfaceProtocol,
    ModelServiceBase,
    ModelServiceError,
    ModelServiceDetail,
    ModelStrategy,
    ProviderAuth,
    ResolveCtx,
    StrategyType,
    _auth_from_data,
    _auth_project_id,
    _build_router_strategy,
    _cache_ttl_for_model,
    _is_platform,
    _model_from_data,
)


class TestModelServiceError:
    def test_str_format(self):
        exc = ModelServiceError("CODE_X", "message")
        assert str(exc) == "[CODE_X] message"

    def test_default_msg(self):
        exc = ModelServiceError("CODE_X")
        assert exc.msg == ""
        assert str(exc) == "[CODE_X] "

    def test_upstream_fields(self):
        exc = ModelServiceError("CODE", "m", upstream_status=404, upstream_body="b")
        assert exc.upstream_status == 404
        assert exc.upstream_body == "b"

    def test_upstream_fields_default_none(self):
        exc = ModelServiceError("CODE", "m")
        assert exc.upstream_status is None
        assert exc.upstream_body is None


class TestInterfaceProtocol:
    def test_values(self):
        assert InterfaceProtocol.OPENAI.value == "openai"
        assert InterfaceProtocol.ANTHROPIC.value == "anthropic"


class TestPathTemplates:
    def test_model_path(self):
        assert MODEL_PATH % "m1" == "model-service/ir/m1.json"

    def test_auth_path(self):
        assert AUTH_PATH % ("p", "prov", "a") == "model-auth/auth/p/prov/a.json"

    def test_auth_list_path(self):
        assert AUTH_LIST_PATH % ("p", "prov") == "model-auth/auth/p/prov/"


class TestIsPlatform:
    def test_system_is_platform(self):
        assert _is_platform("SYSTEM") is True

    def test_other_not_platform(self):
        assert _is_platform("proj-1") is False

    def test_platform_project_ids(self):
        assert "SYSTEM" in PLATFORM_PROJECT_IDS


class TestAuthProjectId:
    def test_platform_model_uses_caller(self):
        assert _auth_project_id("SYSTEM", "caller") == "caller"

    def test_normal_model_uses_own(self):
        assert _auth_project_id("model-proj", "caller") == "model-proj"


class TestCacheTtlForModel:
    def test_router_returns_none(self):
        assert _cache_ttl_for_model({"type": "router"}) is None

    def test_platform_model_no_ttl(self):
        metadata = {"type": "model", "data": {"project_id": "SYSTEM"}}
        assert _cache_ttl_for_model(metadata) == -1

    def test_normal_model_uses_default(self):
        metadata = {"type": "model", "data": {"project_id": "proj"}}
        assert _cache_ttl_for_model(metadata) is None

    def test_missing_data_no_ttl_key(self):
        metadata = {"type": "model", "data": {}}
        assert _cache_ttl_for_model(metadata) is None


class TestModelFromData:
    def test_full_data(self):
        data = {
            "id": "m1", "model_name": "gpt", "api_url": " http://x/v1 ",
            "provider_id": "p", "interface_protocol": "openai",
            "project_id": "proj", "workspace_id": "ws", "auth_metadata_id": "a",
        }
        model = _model_from_data(data)
        assert model.id == "m1"
        assert model.model_name == "gpt"
        assert model.api_url == "http://x/v1"
        assert model.provider_id == "p"
        assert model.interface_protocol is InterfaceProtocol.OPENAI
        assert model.project_id == "proj"
        assert model.workspace_id == "ws"
        assert model.auth_id == "a"

    def test_empty_data_defaults(self):
        model = _model_from_data({})
        assert model.id == ""
        assert model.model_name == ""
        assert model.api_url == ""
        assert model.provider_id == ""

    def test_int_id_stringified(self):
        model = _model_from_data({"id": 42})
        assert model.id == "42"


class TestAuthFromData:
    def test_api_key_snake_case(self):
        data = {
            "id": "a1", "auth_type": "API_KEY",
            "auth_info": json.dumps({"API Key": "sk-1"}),
        }
        auth = _auth_from_data(data)
        assert auth.auth_id == "a1"
        assert auth.auth_type == "API_KEY"
        assert auth.auth_info == {"api_key": "sk-1"}

    def test_api_key_camel_case(self):
        data = {
            "id": "a1", "authType": "API_KEY",
            "authInfo": json.dumps({"API Key": "sk-2"}),
        }
        auth = _auth_from_data(data)
        assert auth.auth_id == "a1"
        assert auth.auth_info == {"api_key": "sk-2"}

    def test_api_key_empty_info(self):
        data = {"auth_type": "API_KEY", "auth_info": ""}
        auth = _auth_from_data(data)
        assert auth.auth_info == {"api_key": ""}

    def test_custom_apikey(self):
        data = {
            "auth_type": "CUSTOM_APIKEY",
            "auth_info": json.dumps({"cust-userid": "1", "X-Key": "v"}),
        }
        auth = _auth_from_data(data)
        assert auth.auth_type == "CUSTOM_APIKEY"
        assert auth.auth_info == {"cust-userid": "1", "X-Key": "v"}

    def test_unknown_auth_type_empty_info(self):
        data = {"auth_type": "OTHER", "auth_info": json.dumps({"a": "b"})}
        auth = _auth_from_data(data)
        assert auth.auth_type == "OTHER"
        assert auth.auth_info == {}

    def test_missing_auth_type_empty(self):
        auth = _auth_from_data({})
        assert auth.auth_type == ""
        assert auth.auth_info == {}


class TestResolveCtx:
    def test_defaults(self):
        ctx = ResolveCtx(project_id="p", workspace_id="w")
        assert ctx.refresh is False
        assert ctx.env_vars is None

    def test_full(self):
        ctx = ResolveCtx(project_id="p", workspace_id="w", refresh=True, env_vars={"a": 1})
        assert ctx.refresh is True
        assert ctx.env_vars == {"a": 1}

    def test_frozen(self):
        ctx = ResolveCtx(project_id="p", workspace_id="w")
        with pytest.raises(Exception):
            ctx.project_id = "x"


class TestBuildRouterStrategy:
    def _mk_detail(self, mid):
        model = ModelServiceBase(
            id=mid, model_name=f"m-{mid}", api_url="http://x", provider_id="p",
            interface_protocol=InterfaceProtocol.OPENAI, project_id="proj",
            workspace_id="w", auth_id="a",
        )
        auth = ProviderAuth(auth_id="a", auth_type="API_KEY", auth_info={"api_key": "k"})
        return ModelServiceDetail(model=model, auth=auth, available=True, is_free_model=False)

    def test_router_parses_service_and_auth_ids(self, monkeypatch):
        import model_service.resolver as mod

        details = {}

        async def _query(metadata_id, refresh):
            return {"type": "model", "data": {
                "id": metadata_id, "model_name": f"m-{metadata_id}",
                "api_url": "http://x", "provider_id": "p",
                "interface_protocol": "openai", "project_id": "proj",
                "workspace_id": "w", "auth_metadata_id": "a",
            }}

        async def _detail(model, ctx, aid):
            details[model.id] = aid
            return self._mk_detail(model.id)

        monkeypatch.setattr(mod, "_query_model_metadata", _query)
        monkeypatch.setattr(mod, "_build_detail", _detail)

        data = {
            "service_id_list": "m1,m2",
            "auth_id_list": "a1",
            "strategy_key": "rk",
            "strategy_retry_count": "2",
            "strategy_timeout": "30000",
        }
        ctx = ResolveCtx(project_id="p", workspace_id="w")

        async def _run():
            return await _build_router_strategy(data, ctx)

        strategy = asyncio_run(_run())
        assert strategy.type is StrategyType.ROUTER
        assert strategy.name == "rk"
        assert strategy.retry_count == 2
        assert strategy.strategy_timeout_ms == 30000
        assert list(details) == ["m1", "m2"]
        # 只有一个 authId，第二个模型回退使用最后一个 authId。
        assert details["m2"] == "a1"

    def test_router_empty_service_ids_raises(self):
        ctx = ResolveCtx(project_id="p", workspace_id="w")

        async def _run():
            return await _build_router_strategy({"service_id_list": ""}, ctx)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio_run(_run())
        assert exc_info.value.code == "UNEXPECTED_ERROR"

    def test_router_missing_child_raises(self, monkeypatch):
        import model_service.resolver as mod

        async def _query(metadata_id, refresh):
            return None

        monkeypatch.setattr(mod, "_query_model_metadata", _query)
        ctx = ResolveCtx(project_id="p", workspace_id="w")

        async def _run():
            return await _build_router_strategy({"service_id_list": "m1"}, ctx)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio_run(_run())
        assert exc_info.value.code == "MD_MODEL_ROUTER_INVALID"


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
