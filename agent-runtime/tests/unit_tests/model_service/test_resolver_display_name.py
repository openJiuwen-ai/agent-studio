# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""query_model_display_name 契约：元数据 data.model_name → 显示名，全程降级空串。"""

import pytest

import model_service.resolver as resolver
from model_service import query_model_display_name


@pytest.mark.asyncio
async def test_display_name_reads_data_layer(monkeypatch):
    """元数据经 data 包装（与 _build_strategy 同层），模型名取 data.model_name。"""

    async def fake_query(model_id, refresh):
        assert model_id == "svc-1"
        assert refresh is False
        return {"type": "model", "data": {"model_name": "MiniMax-M2.7", "api_url": "x"}}

    monkeypatch.setattr(resolver, "_query_model_metadata", fake_query)

    assert await query_model_display_name("svc-1") == "MiniMax-M2.7"


@pytest.mark.asyncio
async def test_missing_metadata_returns_empty(monkeypatch):
    async def fake_query(model_id, refresh):
        return None

    monkeypatch.setattr(resolver, "_query_model_metadata", fake_query)

    assert await query_model_display_name("svc-1") == ""


@pytest.mark.asyncio
async def test_router_without_model_name_returns_empty(monkeypatch):
    """router 型元数据 data 层无 model_name——显示名缺失按空串（不覆盖）。"""

    async def fake_query(model_id, refresh):
        return {"type": "router", "data": {"service_id_list": "a,b"}}

    monkeypatch.setattr(resolver, "_query_model_metadata", fake_query)

    assert await query_model_display_name("svc-1") == ""


@pytest.mark.asyncio
async def test_query_failure_degrades_to_empty(monkeypatch):
    async def fake_query(model_id, refresh):
        raise resolver.ModelServiceError("MD_OBS_READ_ERROR", "boom")

    monkeypatch.setattr(resolver, "_query_model_metadata", fake_query)

    assert await query_model_display_name("svc-1") == ""


@pytest.mark.asyncio
async def test_empty_id_returns_empty_without_query(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("空 id 不得触发元数据查询")

    monkeypatch.setattr(resolver, "_query_model_metadata", boom)

    assert await query_model_display_name("") == ""
