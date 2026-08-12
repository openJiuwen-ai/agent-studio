# -*- coding: utf-8 -*-
"""customer_header — 配置驱动的 Header rename 引擎（common_utils 共享模块）

简化版：从环境变量加载配置，执行 cust-* → userId/token 的 rename。
三服务共享：agent_runtime / agent_builder（同进程 import）。
"""
from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


# ── 配置 Schema ──

class CustomerHeaderConfig(BaseModel):
    """客户 Header 配置 — 从环境变量加载"""
    enabled: bool = False
    mappings: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


CustomerHeaderConfig.model_rebuild()


# ── 全局配置单例 ──

_config: CustomerHeaderConfig | None = None


def set_config(cfg: CustomerHeaderConfig | None) -> None:
    """设置全局配置单例"""
    global _config
    _config = cfg


def get_config() -> CustomerHeaderConfig:
    """获取全局配置单例，未设置返回默认（enabled=false）"""
    global _config
    if _config is None:
        _config = CustomerHeaderConfig()
    return _config


def load_from_env() -> CustomerHeaderConfig:
    """从环境变量加载配置

    环境变量：
        CUSTOMER_HEADER_ENABLED: true/false
        CUSTOMER_HEADER_MAPPINGS: "cust-userid:userId,cust-token:token"
    """
    enabled = os.environ.get("CUSTOMER_HEADER_ENABLED", "false").lower() == "true"
    raw = os.environ.get("CUSTOMER_HEADER_MAPPINGS", "")

    mappings = {}
    if raw:
        for pair in raw.split(","):
            pair = pair.strip()
            if ":" in pair:
                from_key, to_key = pair.split(":", 1)
                mappings[from_key.strip()] = to_key.strip()

    return CustomerHeaderConfig(enabled=enabled, mappings=mappings)


# ── rename 核心逻辑 ──

def resolve(captured: dict[str, str]) -> dict[str, str]:
    """按配置执行 header rename: captured[from_key] → result[to_key]

    Args:
        captured: 请求中捕获的 cust-* headers（原始名 → 值）

    Returns:
        rename 后的 headers dict
    """
    cfg = get_config()
    if not cfg.enabled or not cfg.mappings:
        return {}

    result = {}
    for from_key, to_key in cfg.mappings.items():
        value = captured.get(from_key) or captured.get(from_key.lower())
        if value:
            result[to_key] = value
    return result


def get_forward_list() -> list[str]:
    """获取 IR_AUTH_KEYS 的 forward-list

    = mappings 的 key + X-Auth-Token
    """
    cfg = get_config()
    keys = list(cfg.mappings.keys())
    if "X-Auth-Token" not in keys:
        keys.append("X-Auth-Token")
    return keys


def get_capture_keys() -> list[str]:
    """获取入站捕获白名单 = mappings 的所有 from_key"""
    cfg = get_config()
    return list(cfg.mappings.keys())


# ── 向后兼容别名 ──

def get_profile() -> CustomerHeaderConfig:
    """向后兼容：get_profile → get_config"""
    return get_config()


def set_profile(cfg: Any) -> None:
    """向后兼容：set_profile → set_config"""
    if isinstance(cfg, CustomerHeaderConfig):
        set_config(cfg)
    elif cfg is None or cfg is False:
        set_config(CustomerHeaderConfig())