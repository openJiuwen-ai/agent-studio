# -*- coding: utf-8 -*-
"""Header 投影引擎 — Python 侧，执行下游 rename/passthrough/forward-list 原语

与 Java 侧 HeaderProjectionEngine 共享 Schema。
处理跨进程 Target（如 runtime LLM ）。
"""

from __future__ import annotations

from typing import Mapping

from customer_header.profile import CustomerHeaderProfile, get_profile
from customer_header.target import InternalTarget
from customer_header.types import HeaderValue

# 保留 header 黑名单 — 客户捕获值不得生成这些 header
RESERVED_BLACKLIST: frozenset[str] = frozenset({
    "authorization", "host", "content-length", "transfer-encoding",
    "connection", "via", "max-forwards", "forwarded",
    "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto",
    "x-real-ip", "x-original-url", "x-rewrite-url",
})


class HeaderProjectionEngine:
    """Header 投影引擎 — 执行下游 rename/passthrough/forward-list 原语

    Python 侧引擎处理跨进程 Target（如 runtime LLM ）。
    每请求每 Target 只投影一次（ 防双投影）。
    """

    def __init__(self, profile: CustomerHeaderProfile | None = None):
        self._profile = profile or get_profile()

    @property
    def profile(self) -> CustomerHeaderProfile:
        return self._profile

    def project(
        self,
        target: InternalTarget,
        captured_headers: Mapping[str, HeaderValue],
        config_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """执行下游 rename 投影 — 将 captured headers 按 Target mappings 改名

        原语：rename（值不变，只改名）。适用于  LakeSearch runtime LLM 等。

        Args:
            target: 下游 Target（如 LAKESEARCH、RUNTIME_LLM_CHAT）
            captured_headers: 捕获的客户 headers（key 为规范化小写名）
            config_headers: 静态配置 headers（如模型自身的认证 header，不参与 rename）

        Returns:
            投影后的 header 映射（key 为目标名，value 为 header 值）
        """
        result: dict[str, str] = {}

        # 先放入静态配置 headers
        if config_headers:
            for name, value in config_headers.items():
                lower_name = name.lower()
                if lower_name not in RESERVED_BLACKLIST:
                    result[lower_name] = value

        # 按 Target mappings 执行 rename
        mappings = self._profile.get_target_mappings(target)
        for mapping in mappings:
            from_name = mapping.from_.lower()
            to_name = mapping.to

            # 检查黑名单
            if to_name in RESERVED_BLACKLIST:
                continue

            # 从 captured_headers 中查找值
            hv = captured_headers.get(from_name)
            if hv and hv.value:
                # 同一目标名已有值且来源不同 → 拒绝（规则3 冲突检测）
                # 与 Java HeaderProjectionEngine 对齐（同结果）
                if to_name in result and result[to_name] != hv.value:
                    raise ValueError(
                        f"Header projection conflict on '{to_name}' for target {target}: "
                        f"existing='{result[to_name]}', incoming='{hv.value}'"
                    )
                result[to_name] = hv.value

        return result

    def passthrough(
        self,
        target: InternalTarget,
        captured_headers: Mapping[str, HeaderValue],
    ) -> dict[str, HeaderValue]:
        """执行 boundary customer-passthrough

        将 captured headers 按白名单原样转发到 boundary target。

        Args:
            target: boundary target（AGENT_RUNTIME_INBOUND / AGENT_BUILDER_INBOUND）
            captured_headers: 捕获的客户 headers

        Returns:
            passthrough header 映射（key 为原始名，value 为 HeaderValue）
        """
        allow_list = self._profile.get_boundary_passthrough(target)
        result: dict[str, HeaderValue] = {}
        for name in allow_list:
            lower_name = name.lower()
            hv = captured_headers.get(lower_name)
            if hv and hv.value:
                result[hv.normalized_name] = hv
        return result

    def forward_list(self, target: InternalTarget) -> list[str]:
        """执行 IR auth_keys forward-list 声明

        返回 Profile 配置的 forward-list（确定性，不读当次请求存在性）。
        """
        if target == InternalTarget.IR_AUTH_KEYS:
            return self._profile.get_ir_auth_keys_forward_list()
        return []


def resolve_outbound_headers(
    target: InternalTarget,
    auth_type: str = "",
    config_headers: dict[str, str] | None = None,
    captured_headers: Mapping[str, HeaderValue] | None = None,
) -> dict[str, str]:
    """统一出站 header 解析函数 — 复用于 runtime 正式调用/builder 正式调用/探针

    非 CUSTOM_APIKEY 时只做  rename；CUSTOM_APIKEY 时剥 cust- 前缀 + request-over-config。

    Args:
        target: 下游 Target
        auth_type: 认证类型（CUSTOM_APIKEY 时触发归一/覆盖逻辑）
        config_headers: 静态配置 headers
        captured_headers: 捕获的客户 headers

    Returns:
        投影后的 header 映射
    """
    engine = HeaderProjectionEngine()

    if not captured_headers:
        captured_headers = {}

    # 非 CUSTOM_APIKEY：只做 rename
    if auth_type != "CUSTOM_APIKEY":
        return engine.project(target, captured_headers, config_headers)

    # CUSTOM_APIKEY：剥 cust- 前缀 + request-over-config
    result: dict[str, str] = {}

    # 先放入静态配置 headers（剥 cust- 前缀后的终态）
    mappings = engine.profile.get_target_mappings(target)
    from_to_map: dict[str, str] = {}
    for mapping in mappings:
        from_to_map[mapping.from_.lower()] = mapping.to

    if config_headers:
        for name, value in config_headers.items():
            lower_name = name.lower()
            if lower_name in RESERVED_BLACKLIST:
                continue
            if lower_name in from_to_map:
                result[from_to_map[lower_name]] = value
            elif lower_name.startswith("cust-"):
                result[lower_name[5:]] = value
            else:
                result[lower_name] = value

    for mapping in mappings:
        from_name = mapping.from_.lower()
        to_name = mapping.to
        if to_name.lower() in RESERVED_BLACKLIST:
            continue
        hv = captured_headers.get(from_name)
        if hv and hv.value:
            result[to_name] = hv.value

    return result
