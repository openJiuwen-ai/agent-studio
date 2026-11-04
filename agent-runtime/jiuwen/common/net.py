#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""Connection pool"""

import asyncio
import os
import ssl

from aiohttp import TCPConnector
from jiuwen.common.configs.env_constants import (
    PLUGIN_SSL_API_CERT_KEY,
    PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION_KEY,
)
from jiuwen.common.log.base import logger
from jiuwen.common.utils.singleton import Singleton
from jiuwen.common.utils.utils import safe_json_loads


def _is_legacy_renegotiation_enabled() -> bool:
    """是否允许 unsafe legacy renegotiation。"""
    return os.environ.get(
        PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION_KEY, ""
    ).lower() == "true"


def _build_legacy_ssl_context() -> ssl.SSLContext:
    """构建允许 unsafe legacy renegotiation 的 SSLContext。"""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.options |= ssl.OP_NO_TLSv1
    ctx.options |= ssl.OP_NO_TLSv1_1
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.options |= getattr(ssl, "OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION", 0x4)
    return ctx


def _get_ssl_config():
    """获取SSL配置。

    - 默认返回 True（校验证书，用默认 SSLContext）
    - PLUGIN_SSL_API_CERT=False 时不校验证书
    - PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION=True 时返回允许 legacy renegotiation 的 SSLContext
    """
    api_cert_env = os.environ.get(PLUGIN_SSL_API_CERT_KEY)
    allow_legacy = _is_legacy_renegotiation_enabled()

    if allow_legacy:
        ctx = _build_legacy_ssl_context()
        if not api_cert_env or safe_json_loads(api_cert_env, True) is False:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        logger.warning(
            "PLUGIN_SSL_ALLOW_LEGACY_RENEGOTIATION=True, "
            "unsafe legacy renegotiation is allowed (insecure)"
        )
        return ctx

    if not api_cert_env:
        return True

    api_cert = safe_json_loads(api_cert_env, True)

    if isinstance(api_cert, bool):
        return api_cert

    # 类型不匹配，返回True并记录警告
    logger.warning(
        f"SSL config must be bool, key: {PLUGIN_SSL_API_CERT_KEY} got {type(api_cert)}, using True"
    )
    return True


class Connector(metaclass=Singleton):
    """
    单例模式的Connector类，用于管理TCP连接池。

    在初始化时，根据全局事件循环的状态，决定是否创建一个TCPConnector实例。
    提供获取TCP连接器和关闭连接器的方法。

    使用了Singleton元类，确保整个应用程序中只有一个Connector实例。
    """

    def __init__(self):
        """
        初始化Connector实例。

        如果当前的事件循环是全局的，则根据SSL配置创建一个TCPConnector。
        """
        self.tcp_connector = None
        loop = asyncio.get_event_loop()
        if getattr(loop, "_is_global", False):
            api_cert = _get_ssl_config()
            self.tcp_connector = TCPConnector(ssl=api_cert)

    def get_tcp_connector(self):
        """
        获取TCP连接器。

        如果当前的事件循环是全局的，则返回TCP连接器实例，否则返回None。

        Returns:
            TCPConnector或None: 返回TCP连接器实例或None。
        """
        loop = asyncio.get_running_loop()
        if getattr(loop, "_is_global", False):
            return self.tcp_connector
        return None

    async def close(self):
        """
        异步关闭TCP连接器。

        如果TCP连接器存在，则异步关闭它。
        """
        if self.tcp_connector:
            await self.tcp_connector.close()
