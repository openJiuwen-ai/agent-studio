# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""知识库检索出站 customer header rename

配置启用时，把 captured 的 cust-userid / cust-token 按 mappings 映射成 userId / token。
配置未启用时，不动 headers（走原始逻辑）。
"""

from __future__ import annotations

from typing import Any, Dict

from openjiuwen.core.common.logging import logger

from common_utils.customer_header import resolve, get_config


def inject_customer_headers_to_kb(headers: Dict[str, Any]) -> None:
    """知识库检索出站 customer header rename

    在 KB 适配器（LakeSearch / KooSearch / RagFlow / General）search 方法中，
    构造完 headers dict 之后、构造 request dataclass / 调用 _search_* 之前调用。
    """
    if not headers:
        return

    cfg = get_config()
    if not cfg.enabled:
        return

    # 从请求上下文获取 captured headers
    try:
        from agent_runtime.context.request_context import _request_ctx
        ctx = _request_ctx.get()
        captured = ctx.customer_headers if ctx else {}
    except Exception as e:
        logger.warning(f"[customer-header] KB captured-header lookup failed, skip inject: {e}")
        captured = {}

    if not captured:
        return

    projected = resolve(captured)
    if projected:
        headers.update(projected)
        logger.info(
            f"[customer-header] KB customer header rename: captured_keys={list(captured.keys())}, "
            f"projected_keys={list(projected.keys())}"
        )
