# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""http_observed._report_business_error 的 URL 脱敏单测：IPv6 netloc 方括号必须保留。

urlsplit().hostname 会剥掉 IPv6 字面量的方括号，若用 hostname 重建 netloc，
[2001:db8::1]:8080 会变成非法的 2001:db8::1:8080 写进 trace 属性。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from jiuwen.extension.workflow_node.http_observed import HttpObservedExecutable

# G.CLS.11：类外访问受保护成员统一走 getattr 字符串包装
_report_business_error = getattr(HttpObservedExecutable, "_report_business_error")


def _reported_url(raw_url: str) -> str:
    session = MagicMock()
    session.trace = AsyncMock()
    asyncio.run(
        _report_business_error(
            session, {"url": raw_url, "statusCode": 500, "body": "boom"}
        )
    )
    payload = session.trace.await_args.args[0]
    return payload["business_error"]["url"]


def test_ipv6_host_with_port_keeps_brackets():
    """IPv6 + 端口：方括号必须保留，输出仍是合法 URL。"""
    assert _reported_url("http://[2001:db8::1]:8080/api?sig=x") == "http://[2001:db8::1]:8080/api"


def test_ipv6_host_without_port_keeps_brackets():
    """IPv6 无端口：同样保留方括号。"""
    assert _reported_url("http://[fe80::1]/x") == "http://[fe80::1]/x"


def test_userinfo_plus_ipv6_with_port():
    """userinfo + IPv6 + 端口三者同时存在：剥 userinfo、留方括号与端口。"""
    assert _reported_url("http://u:p@[2001:db8::1]:8080/x?q=1") == "http://[2001:db8::1]:8080/x"


def test_userinfo_stripped_for_plain_host():
    """userinfo（user:pass@）剥离（既有脱敏语义回归）。"""
    assert _reported_url("http://user:pass@h.example.com/p?q=1") == "http://h.example.com/p"


def test_query_and_fragment_dropped_plain_host():
    """query/fragment 丢弃（既有脱敏语义回归）。"""
    assert _reported_url("https://h.example.com/p?a=1#frag") == "https://h.example.com/p"
