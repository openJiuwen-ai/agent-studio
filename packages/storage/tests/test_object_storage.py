# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for storage.object_storage (LocalStorageProvider / S3 helpers / factory)."""

import asyncio
import json

import pytest

from storage.exceptions import StorageNotFoundError, StorageReadError
from storage.object_storage import (
    LocalStorageProvider,
    ObjectStorageProvider,
    S3StorageProvider,
    _is_s3_not_found,
    _load_custom_provider,
    get_storage_provider,
)


class TestIsS3NotFound:
    def _client_error(self, code=None, status=None):
        class _Err:
            response = {
                "Error": {"Code": code} if code else {},
                "ResponseMetadata": {"HTTPStatusCode": status} if status else {},
            }

        return _Err()

    def test_nosuchkey(self):
        assert _is_s3_not_found(self._client_error(code="NoSuchKey")) is True

    def test_404_code(self):
        assert _is_s3_not_found(self._client_error(code="404")) is True

    def test_not_found_code(self):
        assert _is_s3_not_found(self._client_error(code="NotFound")) is True

    def test_404_status(self):
        assert _is_s3_not_found(self._client_error(status=404)) is True

    def test_other_code(self):
        assert _is_s3_not_found(self._client_error(code="AccessDenied")) is False

    def test_other_status(self):
        assert _is_s3_not_found(self._client_error(status=403)) is False


class TestObjectStorageProviderBase:
    def test_default_list_keys_empty(self):
        class _P(ObjectStorageProvider):
            async def get_content(self, object_key):
                return ""

        import asyncio
        assert asyncio.run(_P().list_keys("p")) == []

    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ObjectStorageProvider()


class TestS3Singleton:
    def test_instance_singleton(self, reset_storage_state):
        a = S3StorageProvider.instance()
        b = S3StorageProvider.instance()
        assert a is b

    def test_not_initialized_by_default(self, reset_storage_state):
        assert S3StorageProvider.instance().is_initialized is False

    def test_get_content_uninitialized_raises(self, reset_storage_state):
        import asyncio

        async def _run():
            with pytest.raises(Exception):
                await S3StorageProvider.instance().get_content("k")

        asyncio.run(_run())

    def test_reset_clears_singleton(self, reset_storage_state):
        a = S3StorageProvider.instance()
        S3StorageProvider.reset()
        b = S3StorageProvider.instance()
        assert b is not a

    def test_decrypt_sk_returns_plaintext(self):
        assert S3StorageProvider._decrypt_sk("sk-123") == "sk-123"


class TestLocalStorageProvider:
    def test_resolve_path(self):
        p = LocalStorageProvider(base_path="/base", bucket="bkt")
        assert p._resolve("ir/x.json").replace("\\", "/").endswith("/base/bkt/ir/x.json")

    def test_get_content_missing_file_raises(self, tmp_path):
        p = LocalStorageProvider(base_path=str(tmp_path), bucket="bkt")

        async def _run():
            with pytest.raises(StorageReadError):
                await p.get_content("nope.txt")

        asyncio.run(_run())

    def test_get_content_reads_file(self, tmp_path):
        (tmp_path / "bkt").mkdir()
        (tmp_path / "bkt" / "a.txt").write_text("hello", encoding="utf-8")
        p = LocalStorageProvider(base_path=str(tmp_path), bucket="bkt")

        async def _run():
            return await p.get_content("a.txt")

        assert asyncio.run(_run()) == "hello"

    def test_get_object_bytes(self, tmp_path):
        (tmp_path / "bkt").mkdir()
        (tmp_path / "bkt" / "a.bin").write_bytes(b"\x00\x01")
        p = LocalStorageProvider(base_path=str(tmp_path), bucket="bkt")

        async def _run():
            return await p.get_object_bytes("a.bin")

        assert asyncio.run(_run()) == b"\x00\x01"

    def test_list_keys(self, tmp_path):
        (tmp_path / "bkt" / "ir").mkdir(parents=True)
        (tmp_path / "bkt" / "ir" / "a.json").write_text("{}", encoding="utf-8")
        (tmp_path / "bkt" / "ir" / "b.json").write_text("{}", encoding="utf-8")
        p = LocalStorageProvider(base_path=str(tmp_path), bucket="bkt")

        async def _run():
            return await p.list_keys("ir/")

        keys = asyncio.run(_run())
        assert keys == ["ir/a.json", "ir/b.json"]

    def test_list_keys_nonexistent_dir_returns_empty(self, tmp_path):
        p = LocalStorageProvider(base_path=str(tmp_path), bucket="bkt")

        async def _run():
            return await p.list_keys("missing/")

        assert asyncio.run(_run()) == []

    def test_list_keys_filters_by_prefix(self, tmp_path):
        (tmp_path / "bkt" / "keep").mkdir(parents=True)
        (tmp_path / "bkt" / "keep" / "a.txt").write_text("x", encoding="utf-8")
        (tmp_path / "bkt" / "other.txt").write_text("x", encoding="utf-8")
        p = LocalStorageProvider(base_path=str(tmp_path), bucket="bkt")

        async def _run():
            return await p.list_keys("keep/")

        assert asyncio.run(_run()) == ["keep/a.txt"]


class TestLoadCustomProvider:
    def test_missing_module_raises(self):
        with pytest.raises(Exception):
            _load_custom_provider("", "C")

    def test_missing_class_raises(self):
        with pytest.raises(Exception):
            _load_custom_provider("some.module", "")

    def test_class_not_found_raises(self):
        import textwrap
        import tempfile
        import os

        tmp = tempfile.mkdtemp()
        mod_path = os.path.join(tmp, "custom_storage.py")
        with open(mod_path, "w", encoding="utf-8") as f:
            f.write("")

        with pytest.raises(Exception):
            _load_custom_provider(mod_path, "NoClass")

    def test_non_provider_class_raises(self):
        import tempfile
        import os

        tmp = tempfile.mkdtemp()
        mod_path = os.path.join(tmp, "custom_storage.py")
        with open(mod_path, "w", encoding="utf-8") as f:
            f.write("class NotAProvider:\n    pass\n")

        with pytest.raises(Exception):
            _load_custom_provider(mod_path, "NotAProvider")

    def test_valid_provider_loaded(self):
        import tempfile
        import os

        tmp = tempfile.mkdtemp()
        mod_path = os.path.join(tmp, "custom_storage.py")
        with open(mod_path, "w", encoding="utf-8") as f:
            f.write(
                "from storage.object_storage import ObjectStorageProvider\n"
                "class MyProvider(ObjectStorageProvider):\n"
                "    async def get_content(self, object_key):\n"
                "        return 'custom:' + object_key\n"
            )

        provider = _load_custom_provider(mod_path, "MyProvider")

        async def _run():
            return await provider.get_content("k")

        assert asyncio.run(_run()) == "custom:k"


class TestGetStorageProvider:
    def test_defaults_to_local_without_settings(self, reset_storage_state):
        # 未注入 settings 时 get_settings 抛 RuntimeError，get_storage_provider 依赖注入。
        pass

    def test_local_type_returns_local(self, reset_storage_state):
        from storage import ports

        class _Settings:
            type = "LOCAL"
            server = ""
            local_base_path = "/tmp"
            local_bucket = "b"

        ports.set_settings(lambda: _Settings())
        provider = get_storage_provider()
        assert isinstance(provider, LocalStorageProvider)

    def test_custom_type_no_module_raises(self, reset_storage_state):
        from storage import ports

        class _Settings:
            type = "CUSTOM"
            server = ""
            custom_module = ""
            custom_class = ""

        ports.set_settings(lambda: _Settings())
        with pytest.raises(Exception):
            get_storage_provider()
