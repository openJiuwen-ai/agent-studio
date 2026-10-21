# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Workflow 实例缓存（LazyWorkflow 保留制，spec §6 / issue #1555）。

- 缓存对象为 LazyWorkflow（构建时机不变：仍发生在首次 stream，
  LazyWorkflow._instantiate_lock 双检锁天然去重并发首调构建）；
- key = ir_path——"重新发布即刻 miss"的依据是发布路径版本化：backend
  发布链路强制 versionId（毫秒时间戳）拼入 OBS 文件名（ControllerAdapter/
  WorkflowAdapter），重新发布必然产生新路径新 key；会被覆盖写的无版本
  路径（调试/试运行）不满足 is_published 门控，进不了本缓存。同 path
  内容漂移（OBS 人工覆盖等异常场景）的兜底为 LRU 容量驱逐/进程重启/
  evict 端点，不设 TTL 与内容 hash 防御——换来热路径零序列化开销
  （此前每次请求对全量 IR 做 canonical dumps + sha256）；key 不含
  build_kwargs（构建期 IO 参数，如 cust_headers/project_id 不影响产物
  图）——白名单 ``_BUILD_KWARGS_NOT_AFFECTING_GRAPH`` 显式枚举不影响
  图结构的键，非白名单键绕过缓存直建（防御：未来新增影响图结构的参数
  时宁可少缓存也不误共享）；
- 仅进程内 memory LRU：Workflow 实例含 Future/Lock/闭包不可序列化，
  不进 Redis，不复用 cache_workflow_queue（BPMN spec 专用）；
- 资格：static_graph 模式 + 未降级 + is_published（跟随 IR 缓存惯例）。

注意 `STATIC_GRAPH_DOWNGRADED` 一旦置位即进程级终态（T6 审查裁定）：
接线点异常路径置 flag 不置幂等守卫，另一入口重试成功也无法自愈；
误差方向保守——实例缓存被强制关闭，不会误用静态图。

降级标志经**双通道**读取（T7 审查 Important-1）：from-import 名字是
导入时刻的值拷贝（仅作测试 monkeypatch 目标），生产端降级都是对
static_graph_patch 模块属性的重绑定，故门控同时 OR 读活属性——
本模块先于接线模块被导入时（如测试进程），模块属性通道仍能看到 True，
降级闸不会失效。
"""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any, Awaitable, Callable, Optional

from agent_runtime.common.config import settings
from openjiuwen.core.common.logging import performance_logger

# 降级标志双通道读取：from-import 名字是导入时刻的值拷贝，仅作测试
# monkeypatch 目标（wic.STATIC_GRAPH_DOWNGRADED）；生产端三处降级
# （apply 内 global、ir_converter/sub_workflow 的 except 兜底）都是对
# static_graph_patch 模块属性的重绑定，须经活属性通道才可见。
from jiuwen.extension.patches import static_graph_patch
from jiuwen.extension.patches.static_graph_patch import (  # noqa: F401 测试 monkeypatch 目标
    STATIC_GRAPH_DOWNGRADED,
)

_lock = asyncio.Lock()
_cache: "OrderedDict[str, Any]" = OrderedDict()
_DOWNGRADE_METRIC_LOGGED = False

# build_kwargs 白名单：不影响产物图结构的构建期 IO 参数（模型配置拉取的
# 请求头 / 项目上下文），故不入缓存 key（PR #1 评审 Suggestion 防漏项）。
# **新增键时须先评估**：若参数开始影响图结构（节点/边/组件配置），必须把
# 其纳入缓存 key，否则不同结构的产物会被误共享。非白名单键走防御
# 路径——绕过缓存直建，宁可少缓存也不误共享（fail-safe）。
_BUILD_KWARGS_NOT_AFFECTING_GRAPH = frozenset({"cust_headers", "project_id"})


async def aget_or_create_workflow_instance(
    ir_path: str,
    ir_data: dict,
    build: Callable[..., Awaitable[Any]],
    build_kwargs: Optional[dict] = None,
) -> Any:
    """命中返回缓存的 LazyWorkflow；未命中调用 build 并缓存。

    build 为 ``IRConverter.async_ir_to_workflow``（创建 LazyWorkflow 壳，
    毫秒级）；miss 路径在锁内 await build——并发 miss 经锁串行后首个
    存入、其余转 hit，昂贵构建仍由 LazyWorkflow 自身的双检锁去重。
    """
    global _DOWNGRADE_METRIC_LOGGED

    if STATIC_GRAPH_DOWNGRADED or static_graph_patch.STATIC_GRAPH_DOWNGRADED:
        if not _DOWNGRADE_METRIC_LOGGED:
            _DOWNGRADE_METRIC_LOGGED = True
            performance_logger.info("workflow_cache|downgrade")
        return await build(ir_data, **(build_kwargs or {}))
    if not ir_data.get("is_published"):
        return await build(ir_data, **(build_kwargs or {}))

    # 防御（评审 Suggestion）：非白名单的 build_kwargs 可能影响产物图结构
    # 而缓存 key 不含它们——直建绕过缓存，避免不同结构的产物被误共享
    if set(build_kwargs or {}) - _BUILD_KWARGS_NOT_AFFECTING_GRAPH:
        return await build(ir_data, **(build_kwargs or {}))

    async with _lock:
        cached = _cache.get(ir_path)
        if cached is not None:
            _cache.move_to_end(ir_path)
            performance_logger.info("workflow_cache|hit")
            return cached

        performance_logger.info("workflow_cache|miss")
        workflow = await build(ir_data, **(build_kwargs or {}))
        _cache[ir_path] = workflow
        capacity = settings.cache.workflow_instance_cache_num
        while len(_cache) > capacity:
            _cache.popitem(last=False)
        return workflow


async def evict_workflow_instances_by_path(ir_path: str) -> int:
    """按精确 path 驱逐（删除执行实例端点的内存卫生钩子，非正确性需要）。

    path-only key 下每个 path 至多一条条目，精确匹配即可——无前缀扫描，
    相近路径（如 ``a.json`` 与 ``a.json.bak``）不会误伤。
    """
    async with _lock:
        return 1 if _cache.pop(ir_path, None) is not None else 0


def clear_workflow_instance_cache() -> None:
    """清空缓存（测试用）。"""
    _cache.clear()
