# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 白盒单测：缓存字典、降级标记、构建参数白名单都是模块级内部状态，没有公开读取入口，
# 而本用例要断言的正是它们自身的取值（缓存是否为空、键集是否被生产调用点覆盖），
# 只能直接访问这些成员，属测试观测面的正当用法。
# pylint: disable=protected-access
"""workflow_instance_cache：LazyWorkflow 保留制实例缓存单测（spec §6）。"""
import pytest

from agent_runtime.common.config import settings
from jiuwen.serve.controllers.execution import workflow_instance_cache as wic


@pytest.fixture(autouse=True)
def _clean_cache():
    wic.clear_workflow_instance_cache()
    wic._DOWNGRADE_METRIC_LOGGED = False
    yield
    wic.clear_workflow_instance_cache()
    wic._DOWNGRADE_METRIC_LOGGED = False


def _published_ir():
    return {"workflowId": "wf-1", "is_published": True, "nodes": []}


def _unpublished_ir():
    return {"workflowId": "wf-2", "is_published": False, "nodes": []}


class TestGating:
    @pytest.mark.asyncio
    async def test_static_graph_mode_with_downgrade_bypasses(self, monkeypatch):
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
    async def test_production_module_rebinding_visible(self, monkeypatch):
        """生产降级通道：static_graph_patch 模块属性重绑定必须可见。

        from-import 只拷贝导入时刻的值；apply 内部与两个接线点的 except
        路径都是对 static_graph_patch 模块属性的重绑定。本模块若先于接线
        模块被导入，仅读 from-import 名字会永远看不到 True（T7 审查
        Important-1：未打补丁仍启用实例缓存 = 误用静态图）。
        """
        from jiuwen.extension.patches import static_graph_patch

        monkeypatch.setattr(static_graph_patch, "STATIC_GRAPH_DOWNGRADED", True)
        builds = []

        async def build(ir_data, **kwargs):
            builds.append(ir_data)
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is not r2
        assert len(builds) == 2
        assert wic._cache == {}

    @pytest.mark.asyncio
    async def test_unpublished_ir_bypasses(self, monkeypatch):
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

        async def build(ir_data, **kwargs):
            return object()

        r1 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        r2 = await wic.aget_or_create_workflow_instance("p", _published_ir(), build)
        assert r1 is r2  # LazyWorkflow 保留制：同一实例

    @pytest.mark.asyncio
    async def test_capacity_lru_eviction(self, monkeypatch):
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

        async def build(ir_data, **kwargs):
            return object()

        await wic.aget_or_create_workflow_instance("wf/ir/a.json", _published_ir(), build)
        await wic.aget_or_create_workflow_instance("wf/ir/b.json", _published_ir(), build)
        evicted = await wic.evict_workflow_instances_by_path("wf/ir/a.json")
        assert evicted == 1
        assert len(wic._cache) == 1

    @pytest.mark.asyncio
    async def test_build_kwargs_forwarded_on_miss(self, monkeypatch):
        seen = {}

        async def build(ir_data, **kwargs):
            seen.update(kwargs)
            return object()

        await wic.aget_or_create_workflow_instance(
            "p", _published_ir(), build, build_kwargs={"cust_headers": {"k": "v"}, "project_id": "pj"}
        )
        assert seen == {"cust_headers": {"k": "v"}, "project_id": "pj"}

    @pytest.mark.asyncio
    async def test_whitelisted_build_kwargs_still_cached(self, monkeypatch):
        """白名单内的 build_kwargs（不影响图结构）正常走缓存：同 key 命中。"""

        async def build(ir_data, **kwargs):
            return object()

        r1 = await wic.aget_or_create_workflow_instance(
            "p", _published_ir(), build,
            build_kwargs={"cust_headers": {"k": "v"}, "project_id": "pj"},
        )
        r2 = await wic.aget_or_create_workflow_instance(
            "p", _published_ir(), build,
            build_kwargs={"cust_headers": {"other": "h"}, "project_id": "pj2"},
        )
        assert r1 is r2
        assert len(wic._cache) == 1

    @pytest.mark.asyncio
    async def test_non_whitelisted_build_kwargs_bypass_cache(self, monkeypatch):
        """非白名单的 build_kwargs 绕过缓存直建（key 不含它们，缓存会误共享）。

        防御路径（评审 Suggestion 防漏项）：未来新增影响图结构的构建参数时，
        在参数进白名单评估前，宁可少缓存也不共享不同结构的产物。
        """

        async def build(ir_data, **kwargs):
            return object()

        r1 = await wic.aget_or_create_workflow_instance(
            "p", _published_ir(), build, build_kwargs={"graph_structure_param": "x"}
        )
        r2 = await wic.aget_or_create_workflow_instance(
            "p", _published_ir(), build, build_kwargs={"graph_structure_param": "y"}
        )
        assert r1 is not r2
        assert len(wic._cache) == 0

    @staticmethod
    def test_production_build_kwargs_within_whitelist():
        """生产调用点传入的 build_kwargs 键 ⊆ 白名单（同步断言）。

        workflow_runner 是唯一生产调用点；其新增构建参数时若未同步白名单，
        该断言失败——提示评估参数是否影响图结构（影响则须纳入缓存 key）。
        """
        import inspect
        import re

        from agent_runtime.runner import workflow_runner

        src = inspect.getsource(workflow_runner)
        match = re.search(r"build_kwargs=\{(.*?)\}", src, re.DOTALL)
        assert match, "workflow_runner 生产调用点未找到 build_kwargs"
        keys = set(re.findall(r'"(\w+)":', match.group(1)))
        assert keys, "build_kwargs 键解析为空"
        assert keys <= wic._BUILD_KWARGS_NOT_AFFECTING_GRAPH, (
            f"生产调用点新增了非白名单构建参数 {keys - wic._BUILD_KWARGS_NOT_AFFECTING_GRAPH}："
            "评估其是否影响产物图结构——影响则须纳入 _cache_key，"
            "不影响则加入 _BUILD_KWARGS_NOT_AFFECTING_GRAPH 白名单"
        )
