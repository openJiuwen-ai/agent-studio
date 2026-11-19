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


def is_valid_outbound_header_value(value: str) -> bool:
    """Latin-1 可编码且无控制字符（0x20~0xFF，禁 0x7F）。

    与 Java 调测侧 isLatin1HeaderValue 同语义；保护 wrapper 直接信任
    独立通道内容的出站注入/请求走私面（防上游校验被绕过后直达 HTTP 客户端）。
    """
    if not isinstance(value, str):
        return False
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code == 0x7F or code > 0xFF:
            return False
    return True
