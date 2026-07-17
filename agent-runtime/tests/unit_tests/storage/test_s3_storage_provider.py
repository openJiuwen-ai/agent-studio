#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""S3StorageProvider unit tests — aioboto3 migration"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.common.ir_interfaces import (
    StorageConfigError,
    StorageNotFoundError,
    StorageReadError,
)
from agent_runtime.storage.object_storage import S3StorageProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure singleton is clean before and after every test."""
    S3StorageProvider.reset()
    yield
    S3StorageProvider.reset()


def _make_mock_client():
    """Build a mock actual S3 client (returned by context's __aenter__)."""
    mock_client = AsyncMock()
    return mock_client


def _make_mock_context(mock_client):
    """Build a mock ClientCreatorContext that returns mock_client on __aenter__."""
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock()
    return mock_context


def _make_mock_body(data: bytes = b'{"key": "value"}'):
    """Build a mock Body stream that supports async-with and .read()."""
    mock_body = AsyncMock()
    mock_body.read = AsyncMock(return_value=data)
    mock_body.__aenter__ = AsyncMock(return_value=mock_body)
    mock_body.__aexit__ = AsyncMock(return_value=False)
    return mock_body


def _make_mock_settings(
    server="https://obs.example.com",
    bucket="test-bucket",
    access_key="ak123",
    secret_key="sk456",
    enable_ssl=False,
):
    """Build a mock settings.object_storage with the given values."""
    mock_os = MagicMock()
    mock_os.server = server
    mock_os.bucket = bucket
    mock_os.access_key = access_key
    mock_os.secret_key = secret_key
    mock_os.enable_ssl = enable_ssl
    # SUT passes this to botocore BotoConfig(s3={"addressing_style": ...}),
    # which validates the value against Literal["path", "virtual"]; a bare
    # MagicMock here raises InvalidS3AddressingStyleError during initialize().
    mock_os.path_style = "path"
    mock_settings = MagicMock()
    mock_settings.object_storage = mock_os
    return mock_settings


# ---------------------------------------------------------------------------
# TestS3StorageProviderInitialize
# ---------------------------------------------------------------------------


class TestS3StorageProviderInitialize:
    """Tests for S3StorageProvider.initialize()"""

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    @patch("agent_runtime.storage.object_storage.aioboto3")
    async def test_initialize_success(self, mock_aioboto3, mock_settings):
        mock_client = _make_mock_client()
        mock_context = _make_mock_context(mock_client)
        mock_session = MagicMock()
        mock_session.client = MagicMock(return_value=mock_context)
        mock_aioboto3.Session = MagicMock(return_value=mock_session)
        mock_settings.object_storage = _make_mock_settings().object_storage

        provider = S3StorageProvider()
        await provider.initialize()

        assert provider.is_initialized is True
        assert getattr(provider, "_bucket") == "test-bucket"
        assert getattr(provider, "_client") is mock_client
        mock_context.__aenter__.assert_awaited_once()
        mock_session.client.assert_called_once()

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    async def test_initialize_missing_config_raises(self, mock_settings):
        # server, ak, sk all empty
        mock_settings.object_storage = _make_mock_settings(
            server="", access_key="", secret_key=""
        ).object_storage

        provider = S3StorageProvider()
        with pytest.raises(StorageConfigError, match="DATASOURCE_OBS_SERVER/AK/SK"):
            await provider.initialize()

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    async def test_initialize_missing_bucket_raises(self, mock_settings):
        # server/ak/sk present but bucket empty
        mock_settings.object_storage = _make_mock_settings(
            server="https://obs.example.com",
            access_key="ak123",
            secret_key="sk456",
            bucket="",
        ).object_storage

        provider = S3StorageProvider()
        with pytest.raises(StorageConfigError, match="DATASOURCE_OBS_BUCKET"):
            await provider.initialize()


# ---------------------------------------------------------------------------
# TestS3StorageProviderClose
# ---------------------------------------------------------------------------


class TestS3StorageProviderClose:
    """Tests for S3StorageProvider.close()"""

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    @patch("agent_runtime.storage.object_storage.aioboto3")
    async def test_close_calls_aexit(self, mock_aioboto3, mock_settings):
        mock_client = _make_mock_client()
        mock_context = _make_mock_context(mock_client)
        mock_session = MagicMock()
        mock_session.client = MagicMock(return_value=mock_context)
        mock_aioboto3.Session = MagicMock(return_value=mock_session)
        mock_settings.object_storage = _make_mock_settings().object_storage

        provider = S3StorageProvider()
        await provider.initialize()
        assert provider.is_initialized is True

        await provider.close()

        mock_context.__aexit__.assert_awaited_once_with(None, None, None)
        assert provider.is_initialized is False
        assert getattr(provider, "_client") is None
        assert getattr(provider, "_context") is None

    @pytest.mark.asyncio
    async def test_close_when_not_initialized_is_noop(self):
        provider = S3StorageProvider()
        # Should not raise
        await provider.close()
        assert getattr(provider, "_client") is None
        assert provider.is_initialized is False


# ---------------------------------------------------------------------------
# TestS3StorageProviderRead
# ---------------------------------------------------------------------------


class TestS3StorageProviderRead:
    """Tests for S3StorageProvider.get_object_bytes() and get_content()"""

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    @patch("agent_runtime.storage.object_storage.aioboto3")
    async def test_get_object_bytes_success(self, mock_aioboto3, mock_settings):
        mock_client = _make_mock_client()
        mock_body = _make_mock_body(b'{"key": "value"}')
        mock_client.get_object = AsyncMock(return_value={"Body": mock_body})
        mock_context = _make_mock_context(mock_client)
        mock_session = MagicMock()
        mock_session.client = MagicMock(return_value=mock_context)
        mock_aioboto3.Session = MagicMock(return_value=mock_session)
        mock_settings.object_storage = _make_mock_settings().object_storage

        provider = S3StorageProvider()
        await provider.initialize()

        result = await provider.get_object_bytes("workflow/ir/test.json")

        assert result == b'{"key": "value"}'
        mock_client.get_object.assert_awaited_once_with(
            Bucket="test-bucket", Key="workflow/ir/test.json"
        )

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    @patch("agent_runtime.storage.object_storage.aioboto3")
    async def test_get_content_returns_utf8_string(self, mock_aioboto3, mock_settings):
        mock_client = _make_mock_client()
        mock_body = _make_mock_body(b'{"key": "value"}')
        mock_client.get_object = AsyncMock(return_value={"Body": mock_body})
        mock_context = _make_mock_context(mock_client)
        mock_session = MagicMock()
        mock_session.client = MagicMock(return_value=mock_context)
        mock_aioboto3.Session = MagicMock(return_value=mock_session)
        mock_settings.object_storage = _make_mock_settings().object_storage

        provider = S3StorageProvider()
        await provider.initialize()

        result = await provider.get_content("workflow/ir/test.json")

        assert isinstance(result, str)
        assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_read_without_initialize_raises(self):
        provider = S3StorageProvider()
        with pytest.raises(StorageConfigError, match="not initialized"):
            await provider.get_object_bytes("some/key.json")

    @pytest.mark.asyncio
    async def test_read_without_initialize_raises_get_content(self):
        provider = S3StorageProvider()
        with pytest.raises(StorageConfigError, match="not initialized"):
            await provider.get_content("some/key.json")

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    @patch("agent_runtime.storage.object_storage.aioboto3")
    async def test_read_s3_error_wraps_as_storage_read_error(
        self, mock_aioboto3, mock_settings
    ):
        mock_client = _make_mock_client()
        mock_client.get_object = AsyncMock(side_effect=Exception("S3 connection lost"))
        mock_context = _make_mock_context(mock_client)
        mock_session = MagicMock()
        mock_session.client = MagicMock(return_value=mock_context)
        mock_aioboto3.Session = MagicMock(return_value=mock_session)
        mock_settings.object_storage = _make_mock_settings().object_storage

        provider = S3StorageProvider()
        await provider.initialize()

        with pytest.raises(StorageReadError, match="S3 read failed"):
            await provider.get_object_bytes("workflow/ir/test.json")

    @pytest.mark.asyncio
    @patch("agent_runtime.storage.object_storage.settings")
    @patch("agent_runtime.storage.object_storage.aioboto3")
    async def test_read_s3_not_found_raises_storage_not_found(
        self, mock_aioboto3, mock_settings
    ):
        """S3 404/NoSuchKey → StorageNotFoundError（区别于传输层 StorageReadError）。

        上层（model_service.resolver）据此区分"未配置"与"OBS 不可达"。
        StorageNotFoundError 是 StorageReadError 子类，既有 ``except StorageReadError`` 仍兼容。
        """
        from botocore.exceptions import ClientError

        not_found_response = {
            "Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }
        mock_client = _make_mock_client()
        mock_client.get_object = AsyncMock(
            side_effect=ClientError(not_found_response, "GetObject"))
        mock_context = _make_mock_context(mock_client)
        mock_session = MagicMock()
        mock_session.client = MagicMock(return_value=mock_context)
        mock_aioboto3.Session = MagicMock(return_value=mock_session)
        mock_settings.object_storage = _make_mock_settings().object_storage

        provider = S3StorageProvider()
        await provider.initialize()

        with pytest.raises(StorageNotFoundError, match="S3 object not found"):
            await provider.get_object_bytes("workflow/ir/missing.json")
        # 子类兼容：仍 isinstance StorageReadError
        provider2 = S3StorageProvider()
        await provider2.initialize()
        with pytest.raises(StorageReadError):
            await provider2.get_object_bytes("workflow/ir/missing.json")


# ---------------------------------------------------------------------------
# TestS3StorageProviderSingleton
# ---------------------------------------------------------------------------


class TestS3StorageProviderSingleton:
    """Tests for S3StorageProvider.instance() and reset()"""

    @staticmethod
    def test_instance_returns_same_object():
        a = S3StorageProvider.instance()
        b = S3StorageProvider.instance()
        assert a is b

    @staticmethod
    def test_reset_clears_singleton():
        first = S3StorageProvider.instance()
        S3StorageProvider.reset()
        second = S3StorageProvider.instance()
        assert first is not second
