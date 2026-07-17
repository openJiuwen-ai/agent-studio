#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""model_service.resolver 单元测试。

覆盖从旧 OBSModelConfigProvider 搬走的解析逻辑：resolve_strategy (MODEL/ROUTER)、
三层缓存 + refresh（cache_model_*_queue.aget_with_source 返回 (value, source) 二元组）、
auth V2 直查、_auth_from_data (API_KEY/CUSTOM_APIKEY cust- 剥离)、平台 TTL、authProject。
mock cache + OBS storage；不连真实 Redis/OBS。
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from model_service.resolver import (
    InterfaceProtocol, ModelServiceBase, ModelServiceDetail, ModelServiceError,
    ModelStrategy, ProviderAuth, StrategyType, _auth_from_data, _auth_project_id,
    _cache_ttl_for_model, resolve_strategy,
)
from agent_runtime.common.ir_interfaces import StorageNotFoundError, StorageReadError


# ── 测试数据 ─────────────────────────────────────────────────────────────────────────────

def _svc_json(mid="m1", name="mm", project_id="0", protocol="openai"):
    return json.dumps({
        "type": "model",
        "data": {
            "id": mid, "provider_id": "prov1", "model_name": name,
            "api_url": "http://x/v1/chat/completions", "interface_protocol": protocol,
            "project_id": project_id, "workspace_id": "w", "auth_metadata_id": "am1",
        },
    })


def _auth_json(auth_id="a1", auth_type="API_KEY", auth_info=None, project_id="0"):
    return json.dumps({
        "id": auth_id, "auth_type": auth_type,
        "auth_info": auth_info if auth_info is not None else json.dumps({"API Key": "k1"}),
        "project_id": project_id,
    })


def _router_json(strategy_key="rk", service_ids="m1,m2", auth_ids="a1,a2",
                 timeout=30000, retry=2):
    return json.dumps({
        "type": "router",
        "data": {
            "strategy_key": strategy_key, "service_id_list": service_ids,
            "auth_id_list": auth_ids, "strategy_timeout": timeout,
            "strategy_retry_count": retry,
        },
    })


def _run(coro):
    return asyncio.run(coro)


# ── 纯单测（无 IO）────────────────────────────────────────────────────────────────────────

def test_auth_from_data_api_key():
    a = _auth_from_data({"id": "a1", "auth_type": "API_KEY",
                         "auth_info": json.dumps({"API Key": "k1"})})
    assert a.auth_type == "API_KEY"
    assert a.auth_info == {"api_key": "k1"}


def test_auth_from_data_custom_apikey_pass_through():
    a = _auth_from_data({"id": "a1", "auth_type": "CUSTOM_APIKEY",
                         "auth_info": json.dumps({"Authorization": "Bearer x", "X-Api-Key": "k", "cust-token": "t"})})
    # 直接透传原始 key，不做大小写转换或 cust- 前缀剥离
    assert a.auth_info == {"Authorization": "Bearer x", "X-Api-Key": "k", "cust-token": "t"}


def test_auth_from_data_unknown_type():
    a = _auth_from_data({"id": "a1", "auth_type": "NO_AUTH", "auth_info": ""})
    assert a.auth_type == "NO_AUTH"
    assert a.auth_info == {}


def test_cache_ttl_platform_system_no_ttl():
    assert _cache_ttl_for_model({"type": "model", "data": {"project_id": "SYSTEM"}}) == -1


def test_cache_ttl_non_platform_finite():
    assert _cache_ttl_for_model({"type": "model", "data": {"project_id": "0"}}) is None


def test_cache_ttl_router_finite():
    assert _cache_ttl_for_model({"type": "router", "data": {}}) is None


def test_auth_project_id_platform_uses_caller():
    assert _auth_project_id("SYSTEM", "caller-proj") == "caller-proj"


def test_auth_project_id_non_platform_uses_model():
    assert _auth_project_id("proj-x", "caller-proj") == "proj-x"


# ── cache + OBS mock ─────────────────────────────────────────────────────────────────────

def _patch_cache_and_storage(svc_cache_ret, auth_cache_ret, svc_obs=None, auth_obs=None):
    """返回三个 patch 装饰器工厂：用顺序 (svc_cache, auth_cache, storage_fn)。
    aget_with_source 返回二元组 (value, source) —— 对齐真实 CacheUtils。"""
    raise NotImplementedError  # 占位，用下面的 fixture 风格


@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_resolve_strategy_model_cache_hit(mock_storage_fn, mock_svc_cache, mock_auth_cache):
    """cache 命中 → 不读 OBS。回归测：aget_with_source 返回 (value, source) 二元组须解包。"""
    mock_svc_cache.aget_with_source = AsyncMock(return_value=(json.loads(_svc_json()), "memory"))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(json.loads(_auth_json()), "redis"))
    mock_auth_cache.aput = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=AssertionError("cache hit 不应读 OBS"))
    mock_storage_fn.return_value = mock_storage

    strat = _run(resolve_strategy("m1", "0", "w", "a1"))
    assert strat is not None
    assert strat.type == StrategyType.MODEL
    assert strat.name == "mm"
    assert len(strat.models) == 1
    d = strat.models[0]
    assert d.model.model_name == "mm"
    assert d.model.api_url == "http://x/v1/chat/completions"
    assert d.model.interface_protocol == InterfaceProtocol.OPENAI
    assert d.auth.auth_type == "API_KEY"
    assert d.auth.auth_info == {"api_key": "k1"}
    assert d.available is True
    mock_storage.get_content.assert_not_called()


@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_resolve_strategy_cache_miss_reads_obs(mock_storage_fn, mock_svc_cache, mock_auth_cache):
    """cache miss → 读 OBS 并回填。auth 路径用 authProject（model project_id="0" 非平台 → 用 "0"）。"""
    mock_svc_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_auth_cache.aput = AsyncMock()

    async def _get(key):
        if key == "model-service/ir/m1.json":
            return _svc_json()
        if key == "model-auth/auth/0/prov1/a1.json":
            return _auth_json()
        raise StorageNotFoundError(key)
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=_get)
    mock_storage_fn.return_value = mock_storage

    strat = _run(resolve_strategy("m1", "0", "w", "a1"))
    assert strat.type == StrategyType.MODEL
    assert strat.models[0].auth.auth_info == {"api_key": "k1"}
    mock_svc_cache.aput.assert_called_once()   # 回填 model-service
    mock_auth_cache.aput.assert_called_once()  # 回填 auth（始终 5min，无平台 no-TTL）


@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_resolve_strategy_refresh_bypasses_cache(mock_storage_fn, mock_svc_cache, mock_auth_cache):
    """refresh=True → 不读 cache，直接读 OBS 并回填（对应 Java queryModelMetadata refresh 分支）。"""
    mock_svc_cache.aget_with_source = AsyncMock(side_effect=AssertionError("refresh 不应读 cache"))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(side_effect=AssertionError("refresh 不应读 cache"))
    mock_auth_cache.aput = AsyncMock()

    async def _get(key):
        if key.startswith("model-service/"):
            return _svc_json()
        if key.startswith("model-auth/"):
            return _auth_json()
        raise StorageNotFoundError(key)
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=_get)
    mock_storage_fn.return_value = mock_storage

    strat = _run(resolve_strategy("m1", "0", "w", "a1", refresh=True))
    assert strat.type == StrategyType.MODEL
    assert strat.models[0].auth.auth_info == {"api_key": "k1"}
    # refresh 走了 OBS
    assert mock_storage.get_content.call_count >= 2


@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_resolve_strategy_not_found(mock_storage_fn, mock_svc_cache, mock_auth_cache):
    """OBS 也没有 → 返回 None。"""
    mock_svc_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_auth_cache.aput = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=StorageNotFoundError)
    mock_storage_fn.return_value = mock_storage

    assert _run(resolve_strategy("missing", "0", "w", "a1")) is None


@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_resolve_strategy_platform_model_auth_project_uses_caller(mock_storage_fn, mock_svc_cache, mock_auth_cache):
    """model project_id=SYSTEM → auth 路径用 caller projectId（'0'），对应 Java getModelServiceDetail。"""
    mock_svc_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_auth_cache.aput = AsyncMock()
    seen_keys = []

    async def _get(key):
        seen_keys.append(key)
        if key == "model-service/ir/m1.json":
            return _svc_json(project_id="SYSTEM")
        # auth 路径应为 model-auth/auth/0/prov1/a1.json（caller '0'）
        if key == "model-auth/auth/0/prov1/a1.json":
            return _auth_json()
        raise StorageNotFoundError(key)
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=_get)
    mock_storage_fn.return_value = mock_storage

    strat = _run(resolve_strategy("m1", "0", "w", "a1"))
    assert strat.type == StrategyType.MODEL
    assert "model-auth/auth/0/prov1/a1.json" in seen_keys


@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_resolve_strategy_router(mock_storage_fn, mock_svc_cache, mock_auth_cache):
    """ROUTER：拆 service_id_list/auth_id_list，逐子解析，带 strategyTimeout/retryCount。"""
    # router 元数据走 cache 命中；子模型 m1/m2 走 OBS
    svc_cache_map = {
        "model-service/ir/router1.json": (json.loads(_router_json()), "memory"),
        "model-service/ir/m1.json": (None, ""),
        "model-service/ir/m2.json": (None, ""),
    }

    def _svc_get(key):
        if key not in svc_cache_map:
            raise KeyError(key)
        return svc_cache_map.get(key)
    mock_svc_cache.aget_with_source = AsyncMock(side_effect=_svc_get)
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_auth_cache.aput = AsyncMock()

    async def _get(key):
        if key == "model-service/ir/m1.json":
            return _svc_json(mid="m1", name="mm1")
        if key == "model-service/ir/m2.json":
            return _svc_json(mid="m2", name="mm2")
        if key.startswith("model-auth/"):
            return _auth_json()
        raise StorageNotFoundError(key)
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=_get)
    mock_storage_fn.return_value = mock_storage

    strat = _run(resolve_strategy("router1", "0", "w", "a1"))
    assert strat.type == StrategyType.ROUTER
    assert strat.name == "rk"
    assert strat.retry_count == 2
    assert strat.strategy_timeout_ms == 30000
    assert len(strat.models) == 2
    assert strat.models[0].model.model_name == "mm1"
    assert strat.models[1].model.model_name == "mm2"


def test_build_router_strategy_invalid_raises():
    """空 service_id_list → 抛 UNEXPECTED_ERROR（校验在 IO 之前，不需 mock）。"""
    from model_service.resolver import _build_router_strategy
    with pytest.raises(ModelServiceError) as exc:
        asyncio.run(_build_router_strategy({"service_id_list": "", "auth_id_list": ""}, "0", "w", False))
    assert exc.value.code == "UNEXPECTED_ERROR"


@patch("openjiuwen.core.common.logging.performance_logger")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_query_model_metadata_perf_log_cache_hit(mock_storage_fn, mock_svc_cache, mock_auth_cache, mock_perf):
    """cache 命中时发 model_service_load|<ms>|memory 性能日志（对齐 async_ir_load 范式）。"""
    from model_service.resolver import _query_model_metadata
    mock_svc_cache.aget_with_source = AsyncMock(return_value=(json.loads(_svc_json()), "memory"))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_auth_cache.aput = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=AssertionError("cache hit 不应读 OBS"))
    mock_storage_fn.return_value = mock_storage

    _run(_query_model_metadata("m1", False))

    mock_perf.info.assert_called_once()
    msg = mock_perf.info.call_args.args[0]
    assert msg.startswith("model_service_load|") and msg.endswith("|memory")


# ── OBS 读错误区分 not-found / read-error；cache 降级告警 ───────────────────────

@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_resolve_strategy_obs_read_error_raises_md_obs_read_error(
        mock_storage_fn, mock_svc_cache, mock_auth_cache):
    """OBS 传输层读失败（非 not-found）→ MD_OBS_READ_ERROR，不再吞成'未配置'误导运维。"""
    mock_svc_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_auth_cache.aput = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=StorageReadError("obs unreachable"))
    mock_storage_fn.return_value = mock_storage

    with pytest.raises(ModelServiceError) as exc:
        _run(resolve_strategy("m1", "0", "w", "a1"))
    assert exc.value.code == "MD_OBS_READ_ERROR"


@patch("model_service.resolver._logger")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_auth_queue")
@patch("jiuwen.serve.controllers.execution.open_utils.cache_model_service_queue")
@patch("agent_runtime.storage.get_storage_provider")
def test_query_model_metadata_cache_read_failure_warns_and_falls_through(
        mock_storage_fn, mock_svc_cache, mock_auth_cache, mock_logger):
    """cache 读故障（aget_with_source raise）→ 告警 + 降级到 OBS（不破坏调用）。"""
    mock_svc_cache.aget_with_source = AsyncMock(side_effect=RuntimeError("redis down"))
    mock_svc_cache.aput = AsyncMock()
    mock_auth_cache.aget_with_source = AsyncMock(return_value=(None, ""))
    mock_auth_cache.aput = AsyncMock()

    async def _get(key):
        if key == "model-service/ir/m1.json":
            return _svc_json()
        if key.startswith("model-auth/"):
            return _auth_json()
        raise StorageNotFoundError(key)
    mock_storage = AsyncMock()
    mock_storage.get_content = AsyncMock(side_effect=_get)
    mock_storage_fn.return_value = mock_storage

    strat = _run(resolve_strategy("m1", "0", "w", "a1"))
    assert strat.type == StrategyType.MODEL          # cache 挂了仍能从 OBS 解析
    mock_logger.warning.assert_called()              # cache 降级有告警
