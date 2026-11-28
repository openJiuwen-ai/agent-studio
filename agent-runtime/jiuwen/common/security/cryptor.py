#!/usr/bin/env python
# -*- coding:utf-8 -*-

#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""
An encryption and decryption module,
which uses the RootKey and WorkKey keys for encryption and decryption operations.
"""

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode


class Crypt:
    """
    保护敏感信息在传输过程中不被窃取或篡改。
    委托 common_utils.crypto_tool 加解密：默认 PlainCrypt 明文透传，
    商用环境通过 CryptTool.register 注册自定义实现（如 AES）后自动生效，
    异常时返回原文（明文兼容）。
    """

    @staticmethod
    def encrypt(origin: str):
        """委托 common_utils.crypto_tool.encrypt。"""
        from common_utils.crypto_tool import encrypt as _encrypt
        return _encrypt(origin)

    @staticmethod
    def decrypt(encrypt_str: str):
        """委托 common_utils.crypto_tool.decrypt。"""
        from common_utils.crypto_tool import decrypt as _decrypt
        return _decrypt(encrypt_str)
