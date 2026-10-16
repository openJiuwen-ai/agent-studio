# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.resolver async flows (resolve_strategy / metadata / auth)."""

# pylint: disable=protected-access  # 白盒单测：需直接调用 _query_model_metadata / _query_auth* 内部函数

import asyncio
import json

import pytest

import model_service.resolver as resolver
from model_service.resolver import (
    InterfaceProtocol,
    ModelServiceError,
    ModelStrategy,
    ProviderAuth,
    ResolveCtx,
    StrategyType,
)


class _FakeStorage:
    """可编程的对象存储 provider。"""

    def __init__(self, contents=None):
        self.contents = contents or {}
        self.read_keys = []
        self.listed = []

    async def get_content(self, key):
        self.read_keys.append(key)
        from storage.exceptions import StorageNotFoundError
        if key not in self.contents:
            raise StorageNotFoundError(key)
        return self.contents[key]

    async def list_keys(self, prefix):
        self.listed.append(prefix)
        return sorted(k for k in self.contents if k.startswith(prefix))


def _model_metadata(mid="m1", **overrides):
    data = {
        "id": mid, "model_name": f"model-{mid}", "api_url": "http://x/v1",
        "provider_id": "prov", "interface_protocol": "openai",
        "project_id": "proj", "workspace_id": "ws", "auth_metadata_id": "a1",
    }
    data.update(overrides)
    return {"type": "model", "data": data}


def _api_key_auth(aid="a1"):
    return {
        "id": aid, "auth_type": "API_KEY",
        "auth_info": json.dumps({"API Key": "sk-1"}),
    }


class TestResolveStrategyModelPath:
    @staticmethod
    def test_model_path_resolves(reset_model_service_ports):
        storage = _FakeStorage({
            "model-service/ir/m1.json": json.dumps(_model_metadata()),
            "model-auth/auth/proj/prov/a1.json": json.dumps(_api_key_auth()),
        })
        import model_service.ports as ports
        ports.set_storage_provider(lambda: storage)
        ports.set_cache_queues(None, None)

        async def _run():
            return await resolver.resolve_strategy("m1", "proj", "ws", "a1")

        strategy = asyncio.run(_run())
        assert strategy is not None
        assert strategy.type is StrategyType.MODEL
        assert strategy.models[0].model.id == "m1"
        assert strategy.models[0].auth is not None
        assert strategy.models[0].auth.auth_info["api_key"] == "sk-1"

    @staticmethod
    def test_missing_model_returns_none(reset_model_service_ports):
        storage = _FakeStorage({})
        import model_service.ports as ports
        ports.set_storage_provider(lambda: storage)
        ports.set_cache_queues(None, None)

        async def _run():
            return await resolver.resolve_strategy("missing", "proj", "ws", "a1")

        assert asyncio.run(_run()) is None

    @staticmethod
    def test_env_placeholder_resolved(reset_model_service_ports):
        metadata = _model_metadata(api_url="http://${_env.plugin_url_params.HOST}/v1")
        storage = _FakeStorage({
            "model-service/ir/m1.json": json.dumps(metadata),
            "model-auth/auth/proj/prov/a1.json": json.dumps(_api_key_auth()),
        })
        import model_service.ports as ports
        ports.set_storage_provider(lambda: storage)
        ports.set_cache_queues(None, None)

        async def _run():
            return await resolver.resolve_strategy(
                "m1", "proj", "ws", "a1",
                env_vars={"plugin_url_params": {"HOST": "api.example.com"}},
            )

        strategy = asyncio.run(_run())
        assert strategy.models[0].model.api_url == "http://api.example.com/v1"
        assert strategy.models[0].model.api_url_env_placeholders == "HOST"

    @staticmethod
    def test_env_placeholder_unresolved_raises(reset_model_service_ports):
        metadata = _model_metadata(api_url="http://${_env.plugin_url_params.HOST}/v1")
        storage = _FakeStorage({
            "model-service/ir/m1.json": json.dumps(metadata),
        })
        import model_service.ports as ports
        ports.set_storage_provider(lambda: storage)
        ports.set_cache_queues(None, None)

        async def _run():
            return await resolver.resolve_strategy("m1", "proj", "ws", "a1", env_vars=None)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_ENV_VAR_UNRESOLVED"

    @staticmethod
    def test_no_env_vars_placeholder_raises(reset_model_service_ports):
        metadata = _model_metadata(api_url="http://${_env.plugin_url_params.HOST}/v1")
        storage = _FakeStorage({"model-service/ir/m1.json": json.dumps(metadata)})
        import model_service.ports as ports
        ports.set_storage_provider(lambda: storage)
        ports.set_cache_queues(None, None)

        async def _run():
            return await resolver.resolve_strategy(
                "m1", "proj", "ws", "a1",
                env_vars={"plugin_url_params": {}},
            )

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_ENV_VAR_UNRESOLVED"


class TestResolveStrategyRouterPath:
    @staticmethod
    def test_router_resolves_children(reset_model_service_ports):
        storage = _FakeStorage({
            "model-service/ir/router1.json": json.dumps({
                "type": "router",
                "data": {
                    "service_id_list": "m1,m2",
                    "auth_id_list": "a1,a2",
                    "strategy_key": "rk",
                },
            }),
            "model-service/ir/m1.json": json.dumps(_model_metadata("m1")),
            "model-service/ir/m2.json": json.dumps(_model_metadata("m2")),
            "model-auth/auth/proj/prov/a1.json": json.dumps(_api_key_auth("a1")),
            "model-auth/auth/proj/prov/a2.json": json.dumps(_api_key_auth("a2")),
        })
        import model_service.ports as ports
        ports.set_storage_provider(lambda: storage)
        ports.set_cache_queues(None, None)

        async def _run():
            return await resolver.resolve_strategy("router1", "proj", "ws", "")

        strategy = asyncio.run(_run())
        assert strategy.type is StrategyType.ROUTER
        assert [m.model.id for m in strategy.models] == ["m1", "m2"]

    @staticmethod
    def test_router_invalid_raises(reset_model_service_ports):
        storage = _FakeStorage({
            "model-service/ir/router1.json": json.dumps({
                "type": "router", "data": {"service_id_list": ""},
            }),
        })
        import model_service.ports as ports
        ports.set_storage_provider(lambda: storage)
        ports.set_cache_queues(None, None)

        async def _run():
            return await resolver.resolve_strategy("router1", "proj", "ws", "")

        with pytest.raises(ModelServiceError):
            asyncio.run(_run())


class TestQueryModelMetadata:
    @staticmethod
    def test_cache_hit(reset_model_service_ports, monkeypatch):
        import model_service.ports as ports

        class _Cache:
            @staticmethod
            async def aget_with_source(key):
                return ({"type": "model", "data": {"id": "cached"}}, "l1")

            @staticmethod
            async def aput(key, value, ttl=None):
                return None

        ports.set_cache_queues(_Cache(), None)
        ports.set_storage_provider(lambda: _FakeStorage({}))

        async def _run():
            return await resolver._query_model_metadata("m1", False)

        metadata = asyncio.run(_run())
        assert metadata["data"]["id"] == "cached"

    def test_refresh_bypasses_cache(self, reset_model_service_ports):
        import model_service.ports as ports

        class _Cache:
            def __init__(self):
                self.hit = False

            async def aget_with_source(self, key):
                self.hit = True
                return ({"data": {"id": "stale"}}, "l1")

            @staticmethod
            async def aput(key, value, ttl=None):
                return None

        cache = _Cache()
        storage = _FakeStorage({"model-service/ir/m1.json": json.dumps(_model_metadata("m1"))})
        ports.set_cache_queues(cache, None)
        ports.set_storage_provider(lambda: storage)

        async def _run():
            return await resolver._query_model_metadata("m1", True)

        metadata = asyncio.run(_run())
        assert cache.hit is False
        assert metadata["data"]["id"] == "m1"

    @staticmethod
    def test_obs_read_error_wrapped(reset_model_service_ports):
        import model_service.ports as ports

        class _BoomStorage:
            @staticmethod
            async def get_content(key):
                raise RuntimeError("obs down")

            @staticmethod
            async def list_keys(prefix):
                return []

        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: _BoomStorage())

        async def _run():
            return await resolver._query_model_metadata("m1", False)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_OBS_READ_ERROR"

    @staticmethod
    def test_parse_error_wrapped(reset_model_service_ports):
        import model_service.ports as ports

        storage = _FakeStorage({"model-service/ir/m1.json": "not-json"})
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: storage)

        async def _run():
            return await resolver._query_model_metadata("m1", False)

        with pytest.raises(ModelServiceError) as exc_info:
            asyncio.run(_run())
        assert exc_info.value.code == "MD_OBS_READ_ERROR"


class TestQueryAuth:
    @staticmethod
    def test_auth_v2_missing_returns_none(reset_model_service_ports):
        import model_service.ports as ports
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: _FakeStorage({}))

        async def _run():
            return await resolver._query_auth("proj", "prov", "a1", False)

        assert asyncio.run(_run()) is None

    @staticmethod
    def test_auth_v2_hit(reset_model_service_ports):
        import model_service.ports as ports
        storage = _FakeStorage({
            "model-auth/auth/proj/prov/a1.json": json.dumps(_api_key_auth()),
        })
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: storage)

        async def _run():
            return await resolver._query_auth("proj", "prov", "a1", False)

        auth = asyncio.run(_run())
        assert isinstance(auth, ProviderAuth)
        assert auth.auth_info["api_key"] == "sk-1"


class TestQueryAuthV1:
    @staticmethod
    def test_v1_empty_list_returns_none(reset_model_service_ports):
        import model_service.ports as ports
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: _FakeStorage({}))

        async def _run():
            return await resolver._query_auth_v1("proj", "prov", "ws", "ws", False)

        assert asyncio.run(_run()) is None

    @staticmethod
    def test_v1_no_workspace_takes_first(reset_model_service_ports):
        import model_service.ports as ports
        storage = _FakeStorage({
            "model-auth/auth/proj/prov/a1.json": json.dumps(_api_key_auth("a1")),
        })
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: storage)

        async def _run():
            return await resolver._query_auth_v1("proj", "prov", "", "", False)

        auth = asyncio.run(_run())
        assert auth.auth_id == "a1"

    @staticmethod
    def test_v1_workspace_match(reset_model_service_ports):
        import model_service.ports as ports
        auth_data = _api_key_auth("a1")
        auth_data["workspace_id"] = "ws2"
        storage = _FakeStorage({
            "model-auth/auth/proj/prov/a1.json": json.dumps(auth_data),
        })
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: storage)

        async def _run():
            return await resolver._query_auth_v1("proj", "prov", "ws2", "ws2", False)

        auth = asyncio.run(_run())
        assert auth.auth_id == "a1"

    @staticmethod
    def test_v1_workspace_mismatch_returns_none(reset_model_service_ports):
        import model_service.ports as ports
        auth_data = _api_key_auth("a1")
        auth_data["workspace_id"] = "ws-other"
        storage = _FakeStorage({
            "model-auth/auth/proj/prov/a1.json": json.dumps(auth_data),
        })
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: storage)

        async def _run():
            return await resolver._query_auth_v1("proj", "prov", "ws-target", "ws-target", False)

        assert asyncio.run(_run()) is None


class TestAuthProjectIdIntegration:
    @staticmethod
    def test_platform_model_uses_caller_project(reset_model_service_ports):
        # 平台模型（project_id=SYSTEM）的 auth 应查调用方 projectId。
        metadata = _model_metadata(project_id="SYSTEM")
        storage = _FakeStorage({
            "model-service/ir/m1.json": json.dumps(metadata),
            "model-auth/auth/caller/prov/a1.json": json.dumps(_api_key_auth()),
        })
        import model_service.ports as ports
        ports.set_cache_queues(None, None)
        ports.set_storage_provider(lambda: storage)

        async def _run():
            return await resolver.resolve_strategy("m1", "caller", "ws", "a1")

        strategy = asyncio.run(_run())
        assert strategy.models[0].auth is not None
