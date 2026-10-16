# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for S3StorageProvider lifecycle & operations (mocked aioboto3 client)."""

import asyncio

import pytest

from storage.exceptions import (
    StorageConfigError,
    StorageNotFoundError,
    StorageReadError,
    StorageWriteError,
)
from storage.object_storage import S3StorageProvider


class _FakeBody:
    def __init__(self, data: bytes):
        self._data = data

    async def __aenter__(self):
        return self

    @staticmethod
    async def __aexit__(*args):
        return None

    async def read(self):
        return self._data


class _FakeS3Client:
    """boto3 client 假实现。

    生产代码按 boto3 约定以 CamelCase 关键字调用（Bucket=/Key=/Body=...），
    这里统一经 **kwargs 接收后在函数体内取值，避免非 snake_case 形参命名。
    """

    def __init__(self, objects=None):
        self.objects = objects or {}
        self.put_calls = []
        self.get_calls = []

    async def get_object(self, **kwargs):
        bucket, key = kwargs["Bucket"], kwargs["Key"]
        self.get_calls.append((bucket, key))
        if key not in self.objects:
            from botocore.exceptions import ClientError
            error_response = {
                "Error": {"Code": "NoSuchKey"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            }
            raise ClientError(error_response, "GetObject")
        return {"Body": _FakeBody(self.objects[key])}

    async def put_object(self, **kwargs):
        self.put_calls.append((kwargs["Bucket"], kwargs["Key"], kwargs["Body"]))

    @staticmethod
    def generate_presigned_url(op, **kwargs):
        params = kwargs["Params"]
        return f"http://presigned/{params['Bucket']}/{params['Key']}?expires={kwargs['ExpiresIn']}"

    def get_paginator(self, name):
        class _Paginator:
            def __init__(self, client):
                self._client = client

            def paginate(self, **kwargs):
                prefix = kwargs["Prefix"]
                keys = sorted(k for k in self._client.objects if k.startswith(prefix))

                async def _gen():
                    yield {"Contents": [{"Key": k} for k in keys]}
                return _gen()

        return _Paginator(self)


class _FakeContext:
    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    @staticmethod
    async def __aexit__(*args):
        return None


def _install_settings(reset_storage_state, monkeypatch, **overrides):
    from storage import ports

    class _Settings:
        server = "http://obs"
        bucket = "bkt"
        access_key = "ak"
        secret_key = "sk"
        enable_ssl = True
        path_style = "path"

    for k, v in overrides.items():
        setattr(_Settings, k, v)
    ports.set_settings(lambda: _Settings())
    return _Settings


def _install_fake_client(monkeypatch, objects):
    import aioboto3

    client = _FakeS3Client(objects)

    class _Session:
        @staticmethod
        def client(*args, **kwargs):
            return _FakeContext(client)

    monkeypatch.setattr(aioboto3, "Session", lambda: _Session())
    return client


class TestS3Initialize:
    @staticmethod
    def test_initialize_creates_client(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        client = _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            return provider.is_initialized

        assert asyncio.run(_run()) is True

    @staticmethod
    def test_initialize_missing_server_raises(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch, server="")

        async def _run():
            provider = S3StorageProvider.instance()
            with pytest.raises(StorageConfigError):
                await provider.initialize()

        asyncio.run(_run())

    @staticmethod
    def test_initialize_missing_ak_raises(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch, access_key="")

        async def _run():
            with pytest.raises(StorageConfigError):
                await S3StorageProvider.instance().initialize()

        asyncio.run(_run())

    @staticmethod
    def test_initialize_missing_sk_raises(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch, secret_key="")

        async def _run():
            with pytest.raises(StorageConfigError):
                await S3StorageProvider.instance().initialize()

        asyncio.run(_run())

    @staticmethod
    def test_initialize_missing_bucket_raises(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch, bucket="")

        async def _run():
            with pytest.raises(StorageConfigError):
                await S3StorageProvider.instance().initialize()

        asyncio.run(_run())

    @staticmethod
    def test_initialize_twice_is_noop(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            await provider.initialize()
            return provider.is_initialized

        assert asyncio.run(_run()) is True


class TestS3GetObjectBytes:
    @staticmethod
    def test_get_existing_object(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {"k": b"data"})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            return await provider.get_object_bytes("k")

        assert asyncio.run(_run()) == b"data"

    @staticmethod
    def test_get_missing_object_raises_not_found(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            with pytest.raises(StorageNotFoundError):
                await provider.get_object_bytes("missing")

        asyncio.run(_run())

    @staticmethod
    def test_get_uninitialized_raises(reset_storage_state):
        async def _run():
            with pytest.raises(StorageConfigError):
                await S3StorageProvider.instance().get_object_bytes("k")

        asyncio.run(_run())


class TestS3GetContent:
    @staticmethod
    def test_decodes_utf8(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {"k": "héllo".encode("utf-8")})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            return await provider.get_content("k")

        assert asyncio.run(_run()) == "héllo"


class TestS3PutObject:
    @staticmethod
    def test_put_object(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        client = _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            await provider.put_object_bytes("k", b"payload")

        asyncio.run(_run())
        assert client.put_calls[0][0] == "bkt"
        assert client.put_calls[0][1] == "k"
        assert client.put_calls[0][2] == b"payload"

    @staticmethod
    def test_put_object_custom_bucket(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        client = _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            await provider.put_object_bytes("k", b"x", bucket_name="other")

        asyncio.run(_run())
        assert client.put_calls[0][0] == "other"


class TestS3ListKeys:
    @staticmethod
    def test_list_keys(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {"ir/a.json": b"{}", "ir/b.json": b"{}", "x.txt": b""})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            return await provider.list_keys("ir/")

        assert asyncio.run(_run()) == ["ir/a.json", "ir/b.json"]


class TestS3PresignedUrl:
    @staticmethod
    def test_presigned_url(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            return await provider.get_presigned_url("k", 3600)

        url = asyncio.run(_run())
        assert url.startswith("http://presigned/bkt/k")

    @staticmethod
    def test_presigned_url_custom_bucket(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            return await provider.get_presigned_url("k", 60, bucket_name="b2")

        url = asyncio.run(_run())
        assert url.startswith("http://presigned/b2/k")


class TestS3Close:
    @staticmethod
    def test_close_resets_state(reset_storage_state, monkeypatch):
        _install_settings(reset_storage_state, monkeypatch)
        _install_fake_client(monkeypatch, {})

        async def _run():
            provider = S3StorageProvider.instance()
            await provider.initialize()
            assert provider.is_initialized is True
            await provider.close()
            return provider.is_initialized

        assert asyncio.run(_run()) is False
