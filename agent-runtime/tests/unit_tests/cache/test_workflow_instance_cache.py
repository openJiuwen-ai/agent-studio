# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""workflow_instance_cache：LazyWorkflow 保留制实例缓存单测（spec §6）。"""
import pytest

from agent_runtime.common.config import settings
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic


@pytest.fixture(autouse=True)
def _clean_cache():
    wic.clear_workflow_instance_cache()
    yield
    wic.clear_workflow_instance_cache()


def _published_ir():
    return {"workflowId": "wf-1", "is_published": True, "nodes": []}


def _unpublished_ir():
    return {"workflowId": "wf-2", "is_published": False, "nodes": []}


class TestGating:
    @pytest.mark.asyncio
    async def test_off_mode_bypasses_cache_entirely(self, monkeypatch):
        """off 模式：直通 build，缓存零触碰（默认行为不变式）。"""
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "off")
        builds = []

        async def build(ir_data, **kwargs):
            builds.append(ir_data)
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is not r2
        assert len(builds) == 2
        assert wic._cache == {}  # 缓存零触碰

    @pytest.mark.asyncio
    async def test_static_graph_mode_with_downgrade_bypasses(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        monkeypatch.setattr(wic, "STATIC_GRAPH_DOWNGRADED", True)
        builds = []

        async def build(ir_data, **kwargs):
            builds.append(ir_data)
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is not r2
        assert len(builds) == 2

    @pytest.mark.asyncio
    async def test_unpublished_ir_bypasses(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        builds = []

        async def build(ir_data, **kwargs):
            builds.append(ir_data)
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _unpublished_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _unpublished_ir(), build)
        assert r1 is not r2
        assert wic._cache == {}


class TestHitMissAndEviction:
    @pytest.mark.asyncio
    async def test_second_call_hits_cache(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")

        async def build(ir_data, **kwargs):
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is r2  # LazyWorkflow 保留制：同一实例

    @pytest.mark.asyncio
    async def test_capacity_lru_eviction(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        monkeypatch.setattr(settings.cache, "workflow_instance_cache_num", 2)

        async def build(ir_data, **kwargs):
            return object()

        a = await wic.aget_or_create_workflow_instance("p1", _published_ir(), build)
        b = await wic.aget_or_create_workflow_instance("p2", _published_ir(), build)
        c = await wic.aget_or_create_workflow_instance("p3", _published_ir(), build)
        assert len(wic._cache) == 2
        # p1（最旧）被淘汰
        a2 = await wic.aget_or_create_workflow_instance("p1", _published_ir(), build)
        assert a2 is not a

    @pytest.mark.asyncio
    async def test_content_hash_key_republish_invalidates(self, monkeypatch):
        """同 path 不同内容 → 不同 key（重新发布即刻 miss，无旧图窗口）。"""
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")

        async def build(ir_data, **kwargs):
            return object()

        v1 = _published_ir()
        r1 = await wic.aget_or_create_workflow_instance("p", v1, build)
        v2 = _published_ir()
        v2["nodes"] = [{"id": "n1"}]  # 内容变化
        r2 = await wic.aget_or_create_workflow_instance("p", v2, build)
        assert r2 is not r1

    @pytest.mark.asyncio
    async def test_evict_by_path_prefix(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")

        async def build(ir_data, **kwargs):
            return object()

        await wic.aget_or_create_workflow_instance("wf/ir/a.json", _published_ir(), build)
        await wic.aget_or_create_workflow_instance("wf/ir/b.json", _published_ir(), build)
        evicted = await wic.evict_workflow_instances_by_path("wf/ir/a.json")
        assert evicted == 1
        assert len(wic._cache) == 1

    @pytest.mark.asyncio
    async def test_build_kwargs_forwarded_on_miss(self, monkeypatch):
        monkeypatch.setattr(settings.cache, "workflow_instance_reuse_mode", "static_graph")
        seen = {}

        async def build(ir_data, **kwargs):
            seen.update(kwargs)
            return object()

        await wic.aget_or_create_workflow_instance(
            "p", _published_ir(), build, build_kwargs={"cust_headers": {"k": "v"}, "project_id": "pj"}
        )
        assert seen == {"cust_headers": {"k": "v"}, "project_id": "pj"}
