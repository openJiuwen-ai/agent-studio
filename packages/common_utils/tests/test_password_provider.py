# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.password_provider."""

import textwrap

import pytest

from common_utils.password_provider import (
    DataSourcePasswordProvider,
    DefaultDataSourcePasswordProvider,
    get_password_provider,
)


class TestDefaultDataSourcePasswordProvider:
    @staticmethod
    def test_returns_plaintext():
        provider = DefaultDataSourcePasswordProvider()
        assert provider.get_password("my-pass") == "my-pass"

    @staticmethod
    def test_empty_password_returns_empty():
        provider = DefaultDataSourcePasswordProvider()
        assert provider.get_password("") == ""

    @staticmethod
    def test_none_password_returns_none():
        provider = DefaultDataSourcePasswordProvider()
        assert provider.get_password(None) is None


class TestGetPasswordProvider:
    @staticmethod
    def test_no_config_returns_default():
        provider = get_password_provider()
        assert isinstance(provider, DefaultDataSourcePasswordProvider)

    @staticmethod
    def test_module_without_class_raises():
        with pytest.raises(ValueError):
            get_password_provider(custom_module="some.module")

    @staticmethod
    def test_class_without_module_raises():
        with pytest.raises(ValueError):
            get_password_provider(custom_class="SomeClass")

    @staticmethod
    def test_nonexistent_module_raises_import_error():
        with pytest.raises(ImportError):
            get_password_provider(custom_module="nonexistent.module.xyz", custom_class="C")

    @staticmethod
    def test_missing_class_in_module_raises_attribute_error():
        # 使用真实可导入的模块，但类名不存在。
        with pytest.raises(AttributeError):
            get_password_provider(custom_module="common_utils.password_provider", custom_class="NoSuchClass")

    @staticmethod
    def test_non_provider_class_raises_type_error():
        with pytest.raises(TypeError):
            get_password_provider(custom_module="common_utils.common_config", custom_class="RedisSettings")


class TestCustomProviderFileLoading:
    @staticmethod
    def test_load_from_py_file(tmp_path):
        py_file = tmp_path / "my_provider.py"
        py_file.write_text(
            textwrap.dedent(
                """
                from common_utils.password_provider import DataSourcePasswordProvider

                class MyProvider(DataSourcePasswordProvider):
                    def get_password(self, raw_password):
                        return "decoded:" + raw_password
                """
            ),
            encoding="utf-8",
        )
        provider = get_password_provider(
            custom_module=str(py_file), custom_class="MyProvider"
        )
        assert provider.get_password("x") == "decoded:x"

    @staticmethod
    def test_load_from_file_without_suffix(tmp_path):
        # 传入不带 .py 后缀的路径时，实现会按 with_suffix(".py") 查找实际文件。
        py_file = tmp_path / "my_provider"
        (tmp_path / "my_provider.py").write_text(
            textwrap.dedent(
                """
                from common_utils.password_provider import DataSourcePasswordProvider

                class MyProvider(DataSourcePasswordProvider):
                    def get_password(self, raw_password):
                        return raw_password.upper()
                """
            ),
            encoding="utf-8",
        )
        provider = get_password_provider(
            custom_module=str(py_file), custom_class="MyProvider"
        )
        assert provider.get_password("abc") == "ABC"

    @staticmethod
    def test_abstract_provider_cannot_instantiate():
        with pytest.raises(TypeError):
            DataSourcePasswordProvider()
