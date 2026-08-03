# -*- coding: utf-8 -*-
"""执行 Header 上下文 —  子工作流/子智能体/工具继承的统一上下文

不可变，包含 customer_headers + platform_headers + project_id + 双 ID。
Runner 从 _request_ctx 取得该上下文，但进入 IRConverter/workflow build API 时必须显式传递。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from customer_header.types import HeaderValue


@dataclass(frozen=True)
class ExecutionHeaderContext:
    """不可变执行 Header 上下文 — 请求级，用于  继承

    Attributes:
        customer_headers: 仅 Profile 允许的 customer Header，保留 provenance
        platform_headers: 仅供服务器认证和平台协议字段，不得混入 customer_headers
        project_id: 项目 ID
        platform_user_id: 平台 userId（Memory 用）
        effective_user_id: 执行用 userId（cust-userid 或回退平台 userId）
    """

    customer_headers: Mapping[str, HeaderValue] = field(default_factory=dict)
    platform_headers: Mapping[str, str] = field(default_factory=dict)
    project_id: str = ""
    platform_user_id: str = ""
    effective_user_id: str = ""

    def get_customer_header(self, name: str) -> str | None:
        """按名称获取客户 header 值（大小写不敏感）"""
        if not name:
            return None
        hv = self.customer_headers.get(name.lower())
        return hv.value if hv else None

    def to_customer_headers_dict(self) -> dict[str, str]:
        """转换为简单的 dict[str, str]（供旧调用方兼容）"""
        return {hv.normalized_name: hv.value for hv in self.customer_headers.values()}

    @classmethod
    def empty(cls) -> ExecutionHeaderContext:
        """空上下文"""
        return cls()
