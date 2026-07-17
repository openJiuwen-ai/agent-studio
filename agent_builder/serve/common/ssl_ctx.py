#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Creates SSL contexts. Load the dict configuration item to create an SSL context."""

import os
import ssl
from os.path import isfile
from typing import Optional, TypedDict, Union

from agent_builder.adapter.exception_bridge import JiuWenException
from agent_builder.adapter.crypto_bridge import decrypt


class ContexConfigDict(TypedDict, total=False):
    """Type hint for configuration dict."""

    cert: str
    key: str
    password: Union[str, bytes, None]
    clientRoot: Optional[list[str]]


class SslCreateException(JiuWenException):
    """Exception that only throws while creating SSL context failed."""


def set_ssl_cert(cert_path, cert_key, ca_file, encrypt_password, ssl_type="service"):
    """set ssl cert"""
    if ssl_type == "service":
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    else:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.options |= ssl.OP_NO_TLSv1
    ctx.options |= ssl.OP_NO_TLSv1_1
    ctx.options |= ssl.OP_NO_SSLv2
    ctx.options |= ssl.OP_NO_SSLv3
    ctx.options |= ssl.OP_NO_RENEGOTIATION
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers(
        "ECDHE-ECDSA-AES256-GCM-SHA384:"  # 最高强度（ECDSA+AES256+SHA384）
        "ECDHE-RSA-AES256-GCM-SHA384:"  # 次高强度（RSA+AES256+SHA384）
        "ECDHE-ECDSA-AES128-GCM-SHA256:"  # 中等强度（ECDSA+AES128+SHA256）
        "ECDHE-RSA-AES128-GCM-SHA256"  # 最低强度（RSA+AES128+SHA256）
    )
    if not all((isinstance(cert_path, str), isinstance(cert_key, str))):
        raise SslCreateException("Certificate and key must be strings.")
    if not isfile(cert_path):
        raise SslCreateException(
            "SSL certificate file not found. Please check the configuration."
        )
    if not isfile(cert_key):
        raise SslCreateException(
            "SSL key file not found. Please check the configuration."
        )
    if not isinstance(encrypt_password, str):
        raise SslCreateException("Password must be a string for encrypted key.")
    cert_path = os.path.realpath(cert_path)
    cert_key = os.path.realpath(cert_key)
    password = decrypt(encrypt_password)
    ctx.load_cert_chain(cert_path, cert_key, password)
    return ctx


def create_context(config: ContexConfigDict) -> Optional[ssl.SSLContext]:
    """Create an SSL context by loading configuration dict."""
    if config is None:
        return dict().get("Skip create and return None")
    if not isinstance(config, dict):
        raise SslCreateException("SSL contex config should be a dict but got.")
    cert, key = (
        os.getenv("TLS_CERT_PATH", config.get("cert")),
        os.getenv("TLS_CERT_KEY_PATH", config.get("key")),
    )
    password = os.getenv("TLS_CERT_KEY_PASSWD", config.get("password"))
    ca_file = os.getenv("TLS_CA_PATH", config.get("ca_cert"))
    # HTTPS=true 但未配置证书/密钥 → 降级为不启用 SSL（http），避免无证书环境（测试/本地）启动失败
    if not cert or not key:
        return None
    ssl_context = set_ssl_cert(cert, key, ca_file, password)
    return ssl_context
