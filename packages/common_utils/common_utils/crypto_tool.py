# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from typing import Optional

from openjiuwen.core.common.security.crypt_utils import BaseCrypt, CryptUtils


class PlainCrypt(BaseCrypt):
    """明文（不加密）实现。"""

    NAME = "plain"

    def __init__(self):
        CryptUtils.register_crypt(self.NAME, self)

    def encrypt(self, key: bytes, origin: str) -> str:
        return origin

    def decrypt(self, key: bytes, encrypt_str: str) -> str:
        return encrypt_str


class CryptTool:
    """加解密管理工具。

    使用方式：
        from common_utils.crypto_tool import CryptTool, BaseCrypt

        class MyAesCrypt(BaseCrypt):
            ...

        # 注册加解密实现，并设为主用
        CryptTool.register("my_aes", MyAesCrypt())

        # 之后全项目直接用 encrypt / decrypt，自动走 MyAesCrypt
        from common_utils.crypto_tool import encrypt, decrypt
        encrypt("secret")                          # 用默认
        encrypt("secret", crypt_name="my_aes")     # 用指定

    或者仅切换默认（不注册）：
        CryptTool.set_default("plain")
    """

    _default_name: Optional[str] = None

    @classmethod
    def register(cls, name: str, crypt_impl: BaseCrypt) -> None:
        """注册加解密实现，并将其设为主用。"""
        CryptUtils.register_crypt(name, crypt_impl)

    @classmethod
    def set_default(cls, name: str) -> None:
        """仅切换主用加解密实现（不注册）。"""
        cls._default_name = name

    def encrypt(self, data: str, key: bytes = None, crypt_name: Optional[str] = None) -> str:
        """加密。传入 crypt_name 则用指定实现，否则用默认实现。"""
        target = crypt_name or self._default_name
        impl = CryptUtils.get_crypt(target)
        return impl.encrypt(key or b"", data)

    def decrypt(self, data: str, key: bytes = None, crypt_name: Optional[str] = None) -> str:
        """解密。传入 crypt_name 则用指定实现，否则用默认实现。

        若解密失败（输入为明文）则返回原文。
        """
        if not data:
            return data
        try:
            target = crypt_name or self._default_name
            impl = CryptUtils.get_crypt(target)
            return impl.decrypt(key or b"", data)
        except Exception:
            return data


PlainCrypt()
CryptTool.set_default(PlainCrypt.NAME)


encrypt = CryptTool().encrypt
decrypt = CryptTool().decrypt
