#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""get_storage_provider factory unit tests

S3StorageProvider / get_storage_provider 已迁移至共享包 ``storage``。OBS 配置经
``storage.set_settings`` 注入（不再 patch 模块级 settings）。
"""

from unittest.mock import MagicMock

import pytest

from storage.object_storage import (
    LocalStorageProvider,
    S3StorageProvider,
    get_storage_provider,
)


@pytest.fixture(autouse=True)
def reset_singleton_and_settings():
    """Reset S3StorageProvider singleton + storage settings before/after each test."""
    import storage

    S3StorageProvider.reset()
    storage.set_settings(None)
    try:
        yield
    finally:
        S3StorageProvider.reset()
        storage.set_settings(None)


def _set_obj_storage(server):
    """注册一个 mock object_storage settings（仅 server 字段被 get_storage_provider 使用）。"""
    import storage

    mock_os = MagicMock()
    mock_os.server = server
    storage.set_settings(lambda: mock_os)


class TestGetStorageProvider:
    @staticmethod
    def test_returns_s3_when_configured_and_initialized():
        """Returns S3StorageProvider when server is configured and client is initialized"""
        provider = S3StorageProvider.instance()
        setattr(provider, "_initialized", True)
        setattr(provider, "_bucket", "test-bucket")

        _set_obj_storage("https://obs.example.com")
        result = get_storage_provider()

        assert isinstance(result, S3StorageProvider)

    @staticmethod
    def test_returns_local_when_server_not_configured():
        """Returns LocalStorageProvider when server is not configured"""
        _set_obj_storage("")
        result = get_storage_provider()

        assert isinstance(result, LocalStorageProvider)

    @staticmethod
    def test_returns_local_when_s3_not_initialized():
        """Returns LocalStorageProvider when S3 is configured but not initialized"""
        # Singleton exists but is not initialized (default state after instance())
        S3StorageProvider.instance()

        _set_obj_storage("https://obs.example.com")
        result = get_storage_provider()

        assert isinstance(result, LocalStorageProvider)
