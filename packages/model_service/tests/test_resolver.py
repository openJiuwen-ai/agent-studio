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
    @staticmethod
    def test_str_format():
        exc = ModelServiceError("CODE_X", "message")
        assert str(exc) == "[CODE_X] message"

    @staticmethod
    def test_default_msg():
        exc = ModelServiceError("CODE_X")
        assert exc.msg == ""
        assert str(exc) == "[CODE_X] "

    @staticmethod
    def test_upstream_fields():
        exc = ModelServiceError("CODE", "m", upstream_status=404, upstream_body="b")
        assert exc.upstream_status == 404
        assert exc.upstream_body == "b"

    @staticmethod
    def test_upstream_fields_default_none():
        exc = ModelServiceError("CODE", "m")
        assert exc.upstream_status is None
        assert exc.upstream_body is None


class TestInterfaceProtocol:
    @staticmethod
    def test_values():
        assert InterfaceProtocol.OPENAI.value == "openai"
        assert InterfaceProtocol.ANTHROPIC.value == "anthropic"


class TestPathTemplates:
    @staticmethod
    def test_model_path():
        assert MODEL_PATH % "m1" == "model-service/ir/m1.json"

    @staticmethod
    def test_auth_path():
        assert AUTH_PATH % ("p", "prov", "a") == "model-auth/auth/p/prov/a.json"

    @staticmethod
    def test_auth_list_path():
        assert AUTH_LIST_PATH % ("p", "prov") == "model-auth/auth/p/prov/"


class TestIsPlatform:
    @staticmethod
    def test_system_is_platform():
        assert _is_platform("SYSTEM") is True

    @staticmethod
    def test_other_not_platform():
        assert _is_platform("proj-1") is False

    @staticmethod
    def test_platform_project_ids():
        assert "SYSTEM" in PLATFORM_PROJECT_IDS


class TestAuthProjectId:
    @staticmethod
    def test_platform_model_uses_caller():
        assert _auth_project_id("SYSTEM", "caller") == "caller"

    @staticmethod
    def test_normal_model_uses_own():
        assert _auth_project_id("model-proj", "caller") == "model-proj"


class TestCacheTtlForModel:
    @staticmethod
    def test_router_returns_none():
        assert _cache_ttl_for_model({"type": "router"}) is None

    @staticmethod
    def test_platform_model_no_ttl():
        metadata = {"type": "model", "data": {"project_id": "SYSTEM"}}
        assert _cache_ttl_for_model(metadata) == -1

    @staticmethod
    def test_normal_model_uses_default():
        metadata = {"type": "model", "data": {"project_id": "proj"}}
        assert _cache_ttl_for_model(metadata) is None

    @staticmethod
    def test_missing_data_no_ttl_key():
        metadata = {"type": "model", "data": {}}
        assert _cache_ttl_for_model(metadata) is None


class TestModelFromData:
    @staticmethod
    def test_full_data():
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

    @staticmethod
    def test_empty_data_defaults():
        model = _model_from_data({})
        assert model.id == ""
        assert model.model_name == ""
        assert model.api_url == ""
        assert model.provider_id == ""

    @staticmethod
    def test_int_id_stringified():
        model = _model_from_data({"id": 42})
        assert model.id == "42"


class TestAuthFromData:
    @staticmethod
    def test_api_key_snake_case():
        data = {
            "id": "a1", "auth_type": "API_KEY",
            "auth_info": json.dumps({"API Key": "sk-1"}),
        }
        auth = _auth_from_data(data)
        assert auth.auth_id == "a1"
        assert auth.auth_type == "API_KEY"
        assert auth.auth_info == {"api_key": "sk-1"}

    @staticmethod
    def test_api_key_camel_case():
        data = {
            "id": "a1", "authType": "API_KEY",
            "authInfo": json.dumps({"API Key": "sk-2"}),
        }
        auth = _auth_from_data(data)
        assert auth.auth_id == "a1"
        assert auth.auth_info == {"api_key": "sk-2"}

    @staticmethod
    def test_api_key_empty_info():
        data = {"auth_type": "API_KEY", "auth_info": ""}
        auth = _auth_from_data(data)
        assert auth.auth_info == {"api_key": ""}

    @staticmethod
    def test_custom_apikey():
        data = {
            "auth_type": "CUSTOM_APIKEY",
            "auth_info": json.dumps({"cust-userid": "1", "X-Key": "v"}),
        }
        auth = _auth_from_data(data)
        assert auth.auth_type == "CUSTOM_APIKEY"
        assert auth.auth_info == {"cust-userid": "1", "X-Key": "v"}

    @staticmethod
    def test_unknown_auth_type_empty_info():
        data = {"auth_type": "OTHER", "auth_info": json.dumps({"a": "b"})}
        auth = _auth_from_data(data)
        assert auth.auth_type == "OTHER"
        assert auth.auth_info == {}

    @staticmethod
    def test_missing_auth_type_empty():
        auth = _auth_from_data({})
        assert auth.auth_type == ""
        assert auth.auth_info == {}


class TestResolveCtx:
    @staticmethod
    def test_defaults():
        ctx = ResolveCtx(project_id="p", workspace_id="w")
        assert ctx.refresh is False
        assert ctx.env_vars is None

    @staticmethod
    def test_full():
        ctx = ResolveCtx(project_id="p", workspace_id="w", refresh=True, env_vars={"a": 1})
        assert ctx.refresh is True
        assert ctx.env_vars == {"a": 1}

    @staticmethod
    def test_frozen():
        ctx = ResolveCtx(project_id="p", workspace_id="w")
        with pytest.raises(Exception):
            ctx.project_id = "x"


class TestBuildRouterStrategy:
    @staticmethod
    def _mk_detail(mid):
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

    @staticmethod
    def test_router_empty_service_ids_raises():
        ctx = ResolveCtx(project_id="p", workspace_id="w")

        async def _run():
            return await _build_router_strategy({"service_id_list": ""}, ctx)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio_run(_run())
        assert exc_info.value.code == "UNEXPECTED_ERROR"

    @staticmethod
    def test_router_missing_child_raises(monkeypatch):
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
