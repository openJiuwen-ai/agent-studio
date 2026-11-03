# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Provider 注册表（设计文档 5.2）。

解析优先级（与工厂配合，1030 亮点吸收）：

  1. 显式配置（REDIS_PROVIDER 直指 模块：Class / 文件路径）——工厂层处理；
  2. entry_points 注册表（组 ``openjiuwen.redis_providers``，**同名可覆盖内置实现**）；
  3. 内置保留实现（native——保留名，不可被插件覆盖）。

本模块职责：注册名 → Provider 工厂（无参可调用、返回 RedisProvider 实例）的
解析与枚举；**不做** RedisProvider 类型校验（校验统一在 factory 装配边界做，
避免与 factory 的循环导入）。

手动注册（register_provider）面向测试与嵌入式场景；entry_points 与手动注册
同名时 **entry_points 优先**（自动发现的为"官方"插件；测试请用独一名或 force）。
"""

from __future__ import annotations

import logging
from importlib import metadata
from typing import Callable

from redis_spi.exceptions import RedisConfigError

logger = logging.getLogger(__name__)

#: entry_points 组名（企业插件以 [project.entry-points.openjiuwen.redis_providers] 注册）。
ENTRY_POINT_GROUP = "openjiuwen.redis_providers"

#: 内置保留名（工厂短路处理；插件注册这些名字直接拒绝）。
RESERVED_NAMES = frozenset({"native"})

#: Provider 工厂签名：无参可调用，返回 redis_spi.factory.RedisProvider 实例。
ProviderFactoryCallable = Callable[[], object]


def register_provider(
    name: str,
    factory: ProviderFactoryCallable,
    *,
    force: bool = False,
) -> None:
    """手动注册 Provider 工厂（测试 / 嵌入式场景）。

    - name 为保留名（native）抛 RedisConfigError；
    - 重复注册默认抛错；force=True 覆盖（测试替换用）。
    """
    _validate_name(name)
    if not callable(factory):
        raise RedisConfigError(
            f"provider factory for '{name}' must be callable, "
            f"got {type(factory).__name__}"
        )
    if name in _manual and not force:
        raise RedisConfigError(
            f"provider '{name}' already registered; pass force=True to override"
        )
    _manual[name] = factory


def unregister_provider(name: str) -> None:
    """移除手动注册（仅测试清理用；entry_points 项不可移除）。"""
    _manual.pop(name, None)


def available_names() -> list[str]:
    """全部可用 Provider 名（保留名 + entry_points + 手动注册），排序去重。

    供报错自描述（1030 亮点吸收：名字解析失败必须列出可用名全集）。
    """
    names = set(RESERVED_NAMES) | set(_manual)
    names.update(_entry_points().keys())
    return sorted(names)


def lookup(name: str) -> ProviderFactoryCallable | None:
    """按名解析 Provider 工厂。

    优先级：entry_points > 手动注册；未知名返回 None（由工厂层生成自描述报错）；
    entry_point 加载失败抛 RedisConfigError（含插件名与底层原因）。
    """
    entry_points = _entry_points()
    if name in entry_points:
        return _load_entry_point(name, entry_points[name])
    return _manual.get(name)


def reset() -> None:
    """清空手动注册（测试隔离用）。"""
    _manual.clear()


# ---------------------------------------------------------------- internal

#: 手动注册表（模块级单例；进程内生效）。
_manual: dict[str, ProviderFactoryCallable] = {}


def _validate_name(name: str) -> None:
    if not name or not name.strip():
        raise RedisConfigError("provider name must be non-empty")
    if name.strip() != name:
        raise RedisConfigError(f"provider name '{name}' has leading/trailing spaces")
    if name in RESERVED_NAMES:
        raise RedisConfigError(
            f"'{name}' is a reserved builtin provider name and cannot be "
            f"registered by plugins"
        )


def _entry_points() -> dict[str, metadata.EntryPoint]:
    """发现（不加载）entry_points 组内插件。

    - 保留名（native）的 entry_point 声明被忽略并警告（native 不可被插件覆盖）；
    - 损坏的发行版元数据跳过并警告（不应拖垮启动，但绝不静默）。
    """
    found: dict[str, metadata.EntryPoint] = {}
    try:
        eps = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception as exc:  # noqa: BLE001 - 元数据损坏不应拖垮启动
        logger.warning(
            "failed to enumerate entry_points group '%s': %s", ENTRY_POINT_GROUP, exc
        )
        return found
    for ep in eps:
        if ep.name in RESERVED_NAMES:
            logger.warning(
                "entry point '%s' (%s) declares reserved provider name '%s'; ignored",
                ep.name,
                ep.value,
                ep.name,
            )
            continue
        # 同组同名重复声明：后者覆盖（entry_points 语义本身如此）。
        found[ep.name] = ep
    return found


def _load_entry_point(name: str, ep: metadata.EntryPoint) -> ProviderFactoryCallable:
    try:
        loaded = ep.load()
    except Exception as exc:  # noqa: BLE001 - 插件加载错误必须带名上报
        raise RedisConfigError(
            f"failed to load redis provider plugin '{name}' "
            f"(entry point '{ep.value}'): {exc}"
        ) from exc
    if not callable(loaded):
        raise RedisConfigError(
            f"redis provider plugin '{name}' (entry point '{ep.value}') "
            f"resolved to a non-callable: {type(loaded).__name__}"
        )
    return loaded
