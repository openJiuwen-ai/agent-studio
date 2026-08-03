# -*- coding: utf-8 -*-
"""客户 Header 类型定义 — 与 Java 侧 HeaderValue/HeaderProvenance 保持一致（Schema 一致性）。

不可变 DTO（@dataclass(frozen=True)），字段与 Java 契约一致：
- normalized_name: 规范化后的 header 名（小写）
- value: header 值
- provenance: 值来源
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HeaderProvenance(Enum):
    """Header 来源枚举 — 标识 header 值的来源，用于合并优先级判断"""

    #: 平台生成的 header（如 X-Auth-Token、X-Execution-Id），优先级最高
    PLATFORM_GENERATED = "platform_generated"

    #: 已认证平台 principal 中的 header
    AUTHENTICATED_PRINCIPAL = "authenticated_principal"

    #: 客户捕获的 header（如 cust-userid、cust-token）
    CUSTOMER_CAPTURED = "customer_captured"

    #: 请求原始 header（最低优先级）
    REQUEST_RAW = "request_raw"


@dataclass(frozen=True)
class HeaderValue:
    """不可变 Header 值 — 携带来源信息，用于投影引擎合并判断

    字段与 Java 侧 com.openjiuwen.studio.agent.common.customerheader.HeaderValue 保持一致。
    """

    normalized_name: str
    value: str
    provenance: HeaderProvenance

    @classmethod
    def customer_captured(cls, name: str, value: str) -> HeaderValue:
        """创建客户捕获的 HeaderValue"""
        return cls(normalized_name=name.lower(), value=value, provenance=HeaderProvenance.CUSTOMER_CAPTURED)

    @classmethod
    def platform_generated(cls, name: str, value: str) -> HeaderValue:
        """创建平台生成的 HeaderValue"""
        return cls(normalized_name=name.lower(), value=value, provenance=HeaderProvenance.PLATFORM_GENERATED)
