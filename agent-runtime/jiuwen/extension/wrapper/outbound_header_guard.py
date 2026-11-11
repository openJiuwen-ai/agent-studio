# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""出站头名合法性校验（MCP wrapper 共享）。

与 Java 侧 McpBaseImpl 同构名单：RFC 7230 token 字符集 +
逐跳（hop-by-hop）敏感头 + 平台保留关联头（D-02/B07）。
流式/非流式 wrapper 共用，避免名单演化时两处漂移。
"""
import re

# D-02/B07 平台保留关联头（与 Python 侧 strip_correlation_headers 同一份名单）
RESERVED_CORRELATION_HEADERS = frozenset({"x-request-id", "x-execution-id", "traceparent"})

# 逐跳（hop-by-hop）敏感头（与 Java 侧 FORBIDDEN_HEADER_NAMES 同构）
FORBIDDEN_HEADER_NAMES = frozenset({
    "host", "content-length", "transfer-encoding", "connection",
    "keep-alive", "te", "trailer", "upgrade",
    "proxy-authenticate", "proxy-authorization",
})

# RFC 7230 token 字符集（\ 转义 \-, 避免被解析为范围符）
_VALID_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-\.^_`|~0-9A-Za-z]+$")


def is_valid_outbound_header_name(name: str) -> bool:
    """RFC 7230 token 字符集 + 逐跳敏感头 + 平台保留关联头。"""
    lower = name.lower()
    if lower in RESERVED_CORRELATION_HEADERS or lower in FORBIDDEN_HEADER_NAMES:
        return False
    return bool(_VALID_HEADER_NAME_RE.match(name))
