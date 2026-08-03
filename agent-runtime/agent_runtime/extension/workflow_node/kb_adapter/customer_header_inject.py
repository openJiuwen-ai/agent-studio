# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""KB（知识库检索）出站 customer header 映射（纯映射，无  剥前缀）。

与 MCP/LLM 的差异：MCP/LLM 使用 auth_type="CUSTOM_APIKEY" 走  路径（剥 cust- 前缀 +
request-over-config），因为它们的 headers 含 auth_keys 注入的 cust-*。KB 适配器（LakeSearch /
KooSearch / RagFlow / General）出站 headers 只含 Content-Type + 一个认证头，无 cust-*，所以
 剥前缀语义不适用。KB 只需要：
- 开关启用 → 把 captured 的 cust-userid / cust-token 按 profile mappings 映射成 userid / token
- 开关未开 → 不动（走原始逻辑）

auth_type 传 ""，走 resolve_outbound_headers 的  纯 rename 分支。
"""

from __future__ import annotations

from typing import Any, Dict

from openjiuwen.core.common.logging import logger

from customer_header.engine import resolve_outbound_headers
from customer_header.profile import get_profile
from customer_header.target import InternalTarget
from model_service import ports as _ports


def inject_customer_headers_to_kb(headers: Dict[str, Any]) -> None:
    """KB 出站 customer header 纯映射。

    在 KB 适配器（LakeSearch / KooSearch / RagFlow / General）search 方法中，
    构造完 headers dict 之后、构造 request dataclass / 调用 _search_* 之前调用：
    - 若 customer-header 开关未启用，直接返回（走原始逻辑，headers 不变）
    - 取请求级 captured（RequestContextMiddleware 捕获，经 model_service.ports provider）
    - resolve_outbound_headers(RUNTIME_KB_CALL, auth_type="") 按 profile mappings 映射
    - 把 userid / token 注入 headers（mutate 会一路透传到 aiohttp.post）
    - 无 captured 时不动 headers
    """
    if not headers:
        return

    # 开关未开，走原始逻辑
    try:
        profile = get_profile()
    except Exception:  # noqa: BLE001
        return
    if not profile.is_enabled_in_simple_mode():
        return

    # 取请求级 captured
    try:
        captured = _ports.get_request_customer_headers() or {}
    except Exception:  # noqa: BLE001 — ports 未注册 / _request_ctx 缺失时降级
        captured = {}
    if not captured:
        return

    # 开关打开：纯映射（auth_type="" → 不走  剥前缀分支）
    projected = resolve_outbound_headers(
        target=InternalTarget.RUNTIME_KB_CALL,
        auth_type="",
        config_headers={},
        captured_headers=captured,
    )
    if not projected:
        return
    logger.info(
        f"[customer-header] KB customer header rename: captured_keys={list(captured.keys())}, "
        f"projected_keys={list(projected.keys())}"
    )
    headers.update(projected)
