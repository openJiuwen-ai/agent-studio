# -*- coding: UTF-8 -*-
"""MCP 出站 customer header rename — 剥 cust- 前缀

参考 common_utils.customer_header.resolve() 的统一 rename 逻辑。
MCP auth_keys 配置的 target_name（cust-token/cust-userid）经
RequestParamsCreator._add_auth_params 注入 request_params.headers；
此处使用 resolve(cust_headers) 做 rename（剥 cust- 前缀），
不透传上游 captured，使外部 MCP server 收到 token/userid。
"""

from common_utils.customer_header import resolve, get_config
from openjiuwen.core.common.logging import logger


def inject_customer_headers_to_mcp(request_params) -> None:
    """MCP 出站 cust-* header 剥前缀。使用 resolve() 统一 rename。

    在 _prepare_request_params / McpAPI.ainvoke / McpServer.list_tools 的 header 组装
    末尾调用（auth_hook 之后，出站之前）：
    - 过滤 request_params.headers 中的 cust-*（auth_keys 注入的静态配置）
    - resolve(cust_headers) 执行 rename
    - 删原 cust-*，update 剥前缀后的 token/userid

    无 cust-* 时直接返回（无 auth_keys 的 MCP 调用不受影响）。
    """
    if not getattr(request_params, "headers", None):
        return
    cfg = get_config()
    if not cfg.enabled:
        return
    cust_headers = {
        k: v for k, v in request_params.headers.items()
        if k.lower().startswith("cust-")
    }
    if not cust_headers:
        return

    projected = resolve(cust_headers)
    logger.info(
        f"[customer-header] MCP customer header rename: static_cust_keys={list(cust_headers.keys())}, "
        f"projected_keys={list(projected.keys())}"
    )
    for k in list(request_params.headers):
        if k.lower().startswith("cust-"):
            del request_params.headers[k]
    if projected:
        request_params.headers.update(projected)