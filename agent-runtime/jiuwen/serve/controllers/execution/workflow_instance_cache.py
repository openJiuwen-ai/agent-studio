# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Workflow 实例缓存（LazyWorkflow 保留制，spec §6 / issue #1555）。

- 缓存对象为 LazyWorkflow（构建时机不变：仍发生在首次 stream，
  LazyWorkflow._instantiate_lock 双检锁天然去重并发首调构建）；
- key = ir_path + IR 内容 hash（canonical JSON 的 sha256 前 16 位）——
  重新发布即刻 miss，不存在旧图窗口；key 不含 build_kwargs（构建期 IO
  参数，如 cust_headers/project_id 不影响产物图）——若未来 build 参数
  影响图结构，须把其纳入 key；
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
import hashlib
import json
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


def _cache_key(ir_path: str, ir_data: dict) -> str:
    canonical = json.dumps(ir_data, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{ir_path}:{digest}"


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

    if settings.cache.workflow_instance_reuse_mode != "static_graph":
        return await build(ir_data, **(build_kwargs or {}))
    if STATIC_GRAPH_DOWNGRADED or static_graph_patch.STATIC_GRAPH_DOWNGRADED:
        if not _DOWNGRADE_METRIC_LOGGED:
            _DOWNGRADE_METRIC_LOGGED = True
            performance_logger.info("workflow_cache|downgrade")
        return await build(ir_data, **(build_kwargs or {}))
    if not ir_data.get("is_published"):
        return await build(ir_data, **(build_kwargs or {}))

    key = _cache_key(ir_path, ir_data)
    async with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            performance_logger.info("workflow_cache|hit")
            return cached

        performance_logger.info("workflow_cache|miss")
        workflow = await build(ir_data, **(build_kwargs or {}))
        _cache[key] = workflow
        capacity = settings.cache.workflow_instance_cache_num
        while len(_cache) > capacity:
            _cache.popitem(last=False)
        return workflow


async def evict_workflow_instances_by_path(ir_path: str) -> int:
    """按 ir_path 前缀驱逐（删除执行实例端点的内存卫生钩子，非正确性需要）。"""
    evicted = 0
    async with _lock:
        for key in [k for k in _cache if k.startswith(f"{ir_path}:")]:
            _cache.pop(key, None)
            evicted += 1
    return evicted


def clear_workflow_instance_cache() -> None:
    """清空缓存（测试用）。"""
    _cache.clear()
