# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for storage.exceptions."""

import pytest

from storage.exceptions import (
    StorageConfigError,
    StorageNotFoundError,
    StorageReadError,
    StorageWriteError,
)


class TestExceptionCodes:
    @staticmethod
    def test_storage_config_error_code():
        assert StorageConfigError.code == 188910

    @staticmethod
    def test_storage_read_error_code():
        assert StorageReadError.code == 188911

    @staticmethod
    def test_storage_write_error_code():
        assert StorageWriteError.code == 188912

    @staticmethod
    def test_storage_not_found_inherits_read_error():
        assert StorageNotFoundError.code == 188911


class TestExceptionHierarchy:
    @staticmethod
    def test_not_found_is_read_error():
        assert issubclass(StorageNotFoundError, StorageReadError)

    @staticmethod
    def test_read_error_is_exception():
        assert issubclass(StorageReadError, Exception)

    @staticmethod
    def test_config_error_is_exception():
        assert issubclass(StorageConfigError, Exception)


class TestExceptionMessages:
    @staticmethod
    def test_config_error_message():
        exc = StorageConfigError("missing config")
        assert str(exc) == "missing config"

    @staticmethod
    def test_default_message():
        exc = StorageReadError()
        assert str(exc) == ""

    @staticmethod
    def test_not_found_caught_as_read_error():
        try:
            raise StorageNotFoundError("no such key")
        except StorageReadError as e:
            assert str(e) == "no such key"

    @staticmethod
    def test_kwargs_accepted():
        exc = StorageWriteError("write failed", foo="bar")
        assert str(exc) == "write failed"
