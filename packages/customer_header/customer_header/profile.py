# -*- coding: utf-8 -*-
"""客户 Header Profile 配置 — 对应  YAML 配置

Python 侧 Profile 加载器，与 Java 侧 CustomerHeaderProfile 共享 Schema。
使用 pydantic BaseModel 进行 Schema 校验。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from customer_header.target import InternalTarget


class Mapping(BaseModel):
    """rename 映射项"""

    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class TargetConfig(BaseModel):
    """Target 配置 — mappings 或 forward-list"""

    mappings: list[Mapping] = Field(default_factory=list)
    forward_list: list[str] = Field(default_factory=lambda: [], alias="forward-list")

    model_config = {"populate_by_name": True}


class Identity(BaseModel):
    """身份配置"""

    user_id_header: str = Field(default="cust-userid", alias="user-id-header")
    token_header: str = Field(default="cust-token", alias="token-header")
    fallback: str = "iam"

    model_config = {"populate_by_name": True}


class Capture(BaseModel):
    """捕获白名单"""

    customer_allow: list[str] = Field(default_factory=list, alias="customer-allow")

    model_config = {"populate_by_name": True}


class BoundaryEntry(BaseModel):
    """boundary 条目"""

    customer_passthrough: list[str] = Field(default_factory=list, alias="customer-passthrough")

    model_config = {"populate_by_name": True}


class Boundary(BaseModel):
    """boundary 配置"""

    agent_runtime_inbound: BoundaryEntry | None = Field(default=None, alias="agent-runtime-inbound")
    agent_builder_inbound: BoundaryEntry | None = Field(default=None, alias="agent-builder-inbound")

    model_config = {"populate_by_name": True}


class CustomerHeaderProfile(BaseModel):
    """客户 Header 根配置 — 对应 YAML customer-header 块（扁平结构，单客户本期约束）。

    environment/identity/capture/boundary/targets 直接挂在根上，无 profile 选择层。
    """

    enabled: bool = False
    environment: str = "simple"
    identity: Identity | None = None
    capture: Capture | None = None
    boundary: Boundary | None = None
    targets: dict[str, TargetConfig] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    def is_enabled_in_simple_mode(self) -> bool:
        """判断是否在 simple 模式下启用（门控）"""
        return bool(self.enabled and self.environment and self.environment.lower() == "simple")

    def get_capture_allow_list(self) -> list[str]:
        """获取捕获白名单"""
        if not self.enabled or not self.capture:
            return []
        return self.capture.customer_allow

    def get_boundary_passthrough(self, target: InternalTarget) -> list[str]:
        """获取指定 boundary target 的 customer-passthrough 白名单"""
        if not self.enabled or not self.boundary:
            return []
        entry = None
        if target == InternalTarget.AGENT_RUNTIME_INBOUND:
            entry = self.boundary.agent_runtime_inbound
        elif target == InternalTarget.AGENT_BUILDER_INBOUND:
            entry = self.boundary.agent_builder_inbound
        if not entry:
            return []
        return entry.customer_passthrough

    def get_target_mappings(self, target: InternalTarget) -> list[Mapping]:
        """获取指定 Target 的 mappings 配置"""
        if not self.enabled or not self.targets:
            return []
        config = self.targets.get(target.value)
        if not config:
            return []
        return config.mappings

    def get_ir_auth_keys_forward_list(self) -> list[str]:
        """获取 IR_AUTH_KEYS 的 forward-list"""
        if not self.enabled or not self.targets:
            return []
        config = self.targets.get(InternalTarget.IR_AUTH_KEYS.value)
        if not config:
            return []
        return config.forward_list

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomerHeaderProfile:
        """从字典构造 Profile（YAML 加载后）"""
        return cls.model_validate(data)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> CustomerHeaderProfile:
        """从 YAML 文件加载 Profile"""
        import yaml

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return cls()
        # 取 customer-header 块
        block = data.get("customer-header", data)
        return cls.model_validate(block)


# 全局 Profile 单例 — 由宿主启动时加载
_profile: CustomerHeaderProfile | None = None


def set_profile(profile: CustomerHeaderProfile | None) -> None:
    """设置全局 Profile 单例"""
    global _profile
    _profile = profile


def get_profile() -> CustomerHeaderProfile:
    """获取全局 Profile 单例，未设置返回默认（enabled=false）"""
    global _profile
    if _profile is None:
        _profile = CustomerHeaderProfile()
    return _profile
