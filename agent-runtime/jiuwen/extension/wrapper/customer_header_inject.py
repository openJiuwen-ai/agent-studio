# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""MCP 出站 customer header rename（同构）——复用 LLM CUSTOM_APIKEY 投影模式。

参考 packages/model_service/model_service/client.py:286-307（RUNTIME_LLM_CHAT 投影）。
MCP auth_keys 配置的 target_name（cust-token/cust-userid）经
RequestParamsCreator._add_auth_params 注入 request_params.headers；此处仅使用自身配置的
auth_keys 做 rename（剥 cust- 前缀），不透传上游 captured，使外部 MCP server 收到 token/userid。

只传 request_params.headers 中的 cust-* 部分给 （与 LLM 的 conn.custom_headers
同构——只含 auth 的 cust-* headers），避免  的 RESERVED_BLACKLIST 误丢
Authorization/Content-Length 等非 cust- header，也避免全量小写化影响其他 header。
"""

from openjiuwen.core.common.logging import logger

from customer_header.engine import resolve_outbound_headers
from customer_header.target import InternalTarget
from model_service import ports as _ports


def inject_customer_headers_to_mcp(request_params) -> None:
    """MCP 出站 cust-* header 剥前缀。仅使用自身配置的 auth_keys，不透传上游 captured。

    在 _prepare_request_params / McpAPI.ainvoke / McpServer.list_tools 的 header 组装
    末尾调用（auth_hook 之后，出站之前）：
    - 过滤 request_params.headers 中的 cust-*（auth_keys 注入的静态配置）
    - resolve_outbound_headers(RUNTIME_MCP_CALL, CUSTOM_APIKEY) 仅使用自身 auth_keys 做 rename
    - 删原 cust-*，update 剥前缀后的 token/userid（避免 cust-* 与 token/userid 共存）

     剥前缀不依赖 profile 启用（与 LLM 一致），故 MCP 总是剥 auth_keys 的 cust- 前缀。
    不透传上游 captured（与 Java 侧 McpCustomerHeaderProjection 对齐）。
    无 cust-* 时直接返回（无 auth_keys 的 MCP 调用不受影响）。
    """
    if not getattr(request_params, "headers", None):
        return
    cust_headers = {
        k: v for k, v in request_params.headers.items()
        if k.lower().startswith("cust-")
    }
    if not cust_headers:
        return

    # 仅使用自身配置的 auth_keys 做 rename，不透传上游 captured
    projected = resolve_outbound_headers(
        target=InternalTarget.RUNTIME_MCP_CALL,
        auth_type="CUSTOM_APIKEY",  # 剥 cust- 前缀，仅使用自身 auth_keys
        config_headers=cust_headers,
        captured_headers={},  # 不透传上游 captured
    )
    logger.info(
        f"[customer-header] MCP customer header rename: static_cust_keys={list(cust_headers.keys())}, "
        f"projected_keys={list(projected.keys())}"
    )
    # 删原 cust-*，再加剥前缀后的 token/userid（仅自身 auth_keys）
    for k in list(request_params.headers):
        if k.lower().startswith("cust-"):
            del request_params.headers[k]
    if projected:
        request_params.headers.update(projected)
