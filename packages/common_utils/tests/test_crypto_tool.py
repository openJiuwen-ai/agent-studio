# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.crypto_tool."""

import pytest

from common_utils.crypto_tool import (
    BaseCrypt,
    CryptTool,
    PlainCrypt,
    decrypt,
    encrypt,
)


class TestPlainCrypt:
    """PlainCrypt：明文加解密，encrypt/decrypt 均为透传。"""

    @staticmethod
    def test_encrypt_returns_origin():
        crypt = PlainCrypt()
        assert crypt.encrypt(b"", "hello") == "hello"

    @staticmethod
    def test_encrypt_ignores_key():
        crypt = PlainCrypt()
        assert crypt.encrypt(b"some-key", "secret") == "secret"

    @staticmethod
    def test_decrypt_returns_encrypted_str():
        crypt = PlainCrypt()
        assert crypt.decrypt(b"", "hello") == "hello"

    @staticmethod
    def test_decrypt_ignores_key():
        crypt = PlainCrypt()
        assert crypt.decrypt(b"k", "cipher") == "cipher"

    @staticmethod
    def test_name_attribute():
        assert PlainCrypt.NAME == "plain"

    @staticmethod
    def test_registers_itself_on_instantiation():
        # PlainCrypt 实例化时自动注册到 CryptUtils，这里验证能再次实例化且不抛错。
        crypt = PlainCrypt()
        assert isinstance(crypt, BaseCrypt)


class _RecordingCrypt(BaseCrypt):
    """测试用记录型 crypt，记录 encrypt/decrypt 调用。"""

    def __init__(self, encrypted_prefix="enc:"):
        self.encrypted_prefix = encrypted_prefix
        self.encrypt_calls = []
        self.decrypt_calls = []

    def encrypt(self, key, origin):
        self.encrypt_calls.append((key, origin))
        return self.encrypted_prefix + origin

    def decrypt(self, key, encrypt_str):
        self.decrypt_calls.append((key, encrypt_str))
        if encrypt_str.startswith(self.encrypted_prefix):
            return encrypt_str[len(self.encrypted_prefix):]
        return encrypt_str


class TestCryptToolRegister:
    """CryptTool.register / set_default 行为。"""

    @staticmethod
    def test_register_sets_implementation(reset_common_utils_state):
        crypt = _RecordingCrypt()
        CryptTool.register("recording", crypt)
        tool = CryptTool()
        tool.set_default("recording")
        assert tool.encrypt("data") == "enc:data"

    @staticmethod
    def test_encrypt_with_explicit_crypt_name(reset_common_utils_state):
        crypt = _RecordingCrypt()
        CryptTool.register("recording", crypt)
        tool = CryptTool()
        assert tool.encrypt("abc", crypt_name="recording") == "enc:abc"

    @staticmethod
    def test_encrypt_with_key_and_name(reset_common_utils_state):
        crypt = _RecordingCrypt()
        CryptTool.register("recording", crypt)
        tool = CryptTool()
        result = tool.encrypt("abc", key=b"k", crypt_name="recording")
        assert result == "enc:abc"
        assert crypt.encrypt_calls == [(b"k", "abc")]

    @staticmethod
    def test_decrypt_with_explicit_name(reset_common_utils_state):
        crypt = _RecordingCrypt()
        CryptTool.register("recording", crypt)
        tool = CryptTool()
        assert tool.decrypt("enc:abc", crypt_name="recording") == "abc"

    @staticmethod
    def test_decrypt_passes_key(reset_common_utils_state):
        crypt = _RecordingCrypt()
        CryptTool.register("recording", crypt)
        tool = CryptTool()
        tool.decrypt("enc:abc", key=b"k", crypt_name="recording")
        assert crypt.decrypt_calls == [(b"k", "enc:abc")]

    @staticmethod
    def test_set_default_then_encrypt_uses_default(reset_common_utils_state):
        crypt = _RecordingCrypt()
        CryptTool.register("recording", crypt)
        tool = CryptTool()
        tool.set_default("recording")
        assert tool.encrypt("xyz") == "enc:xyz"


class TestCryptToolDecryptFallback:
    """decrypt 对异常 / 空输入的降级行为。"""

    @staticmethod
    def test_decrypt_empty_string_returns_empty():
        tool = CryptTool()
        assert tool.decrypt("") == ""

    @staticmethod
    def test_decrypt_none_returns_none():
        tool = CryptTool()
        assert tool.decrypt(None) is None


class TestModuleLevelEncryptDecrypt:
    """模块级 encrypt / decrypt 便捷函数。"""

    @staticmethod
    def test_encrypt_roundtrip_plain():
        assert encrypt("plain-value") == "plain-value"

    @staticmethod
    def test_decrypt_roundtrip_plain():
        assert decrypt("plain-value") == "plain-value"
