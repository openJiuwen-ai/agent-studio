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
    def test_storage_config_error_code(self):
        assert StorageConfigError.code == 188910

    def test_storage_read_error_code(self):
        assert StorageReadError.code == 188911

    def test_storage_write_error_code(self):
        assert StorageWriteError.code == 188912

    def test_storage_not_found_inherits_read_error(self):
        assert StorageNotFoundError.code == 188911


class TestExceptionHierarchy:
    def test_not_found_is_read_error(self):
        assert issubclass(StorageNotFoundError, StorageReadError)

    def test_read_error_is_exception(self):
        assert issubclass(StorageReadError, Exception)

    def test_config_error_is_exception(self):
        assert issubclass(StorageConfigError, Exception)


class TestExceptionMessages:
    def test_config_error_message(self):
        exc = StorageConfigError("missing config")
        assert str(exc) == "missing config"

    def test_default_message(self):
        exc = StorageReadError()
        assert str(exc) == ""

    def test_not_found_caught_as_read_error(self):
        try:
            raise StorageNotFoundError("no such key")
        except StorageReadError as e:
            assert str(e) == "no such key"

    def test_kwargs_accepted(self):
        exc = StorageWriteError("write failed", foo="bar")
        assert str(exc) == "write failed"
