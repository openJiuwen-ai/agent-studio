#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse
from openjiuwen.core.common.logging import logger

ALLOWED_SCHEMES = {"http", "https"}

# 扩展拦截列表，涵盖主流云厂商（AWS, GCP, Azure, Aliyun, Huawei Cloud 等）的元数据域名
BLOCKED_HOSTNAMES = frozenset({
    "metadata.google.internal",
    "metadata.google.internal.",
    "169.254.169.254",
    "metadata",
    "metadata.internal",
    "instance-data",
    "instance-data.ec2.internal",
    "100.100.100.200",  # 阿里云元数据常用 IP
})


# 云元数据常用的链路本地地址段 (IPv4 & IPv6)
# 只要落入这些范围，无论是否是 .254，在插件场景下通常都是危险的
def _is_cloud_metadata_address(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        # 1. 拦截 IPv4 链路本地地址段: 169.254.0.0/16
        if isinstance(addr, ipaddress.IPv4Address):
            return addr.is_link_local or str(addr) == "100.100.100.200"

        # 2. 拦截 IPv6 链路本地地址段: fe80::/10
        # 以及部分云厂商特有的 IPv6 元数据地址 (如 AWS 的 [fd00:ec2::254])
        if isinstance(addr, ipaddress.IPv6Address):
            return addr.is_link_local or str(addr).startswith("fd00:ec2")

        return False
    except ValueError:
        return False


def validate_plugin_url(url: Optional[str]) -> Optional[str]:
    """
    专门防御云元数据 SSRF 的验证器。
    放行内网 IP (10.x, 172.x, 192.x)，但严格拦截链路本地地址。
    """
    if not url:
        return url

    # Strip whitespace
    url = url.strip()
    if not url:
        return url

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}") from e

    # 1. 协议校验
    if not parsed.scheme:
        raise ValueError(
            f"URL must include a scheme. "
            f"Did you mean 'https://{url}'? "
            f"Received: {url}"
        )

    scheme_lower = parsed.scheme.lower()
    if scheme_lower not in ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{scheme_lower}' is not allowed. "
            f"Only HTTP and HTTPS are permitted. "
            f"Received: {url}"
        )

    # 2. 获取主机名
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"URL must contain a valid hostname: {url}")

    # 3. 静态黑名单检查
    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise ValueError(f"URL hostname '{hostname}' is a blocked metadata endpoint.")

    # 4. 解析并检查 IP
    # 这一步能防止攻击者使用 A.B.C.D 这种 IP 形式或者域名解析后的结果
    try:
        # 获取所有可能的解析 IP (IPv4 和 IPv6)
        resolved_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _, _, _, _, sockaddr in resolved_info:
            ip_to_check = sockaddr[0]
            if _is_cloud_metadata_address(ip_to_check):
                raise ValueError(
                    f"URL resolves to a blocked cloud metadata IP: {ip_to_check}. "
                    "Access to 169.254.x.x or cloud-specific metadata is prohibited."
                )
    except socket.gaierror:
        # 允许解析失败，但在生产环境下应记录警告
        logger.warning(f"DNS resolution failed for hostname: {hostname}")
    except ValueError as ve:
        # 重新抛出我们的验证错误
        raise ve

    # 5. 端口限制 (可选，建议保留以增加攻击成本)
    port = parsed.port
    if port is not None:
        if port < 1 or port > 65535:
            raise ValueError(f"Invalid port number: {port}")
        # 如果需要进一步安全，可以限制只能访问 80/443/8080 等常用端口

    return url
