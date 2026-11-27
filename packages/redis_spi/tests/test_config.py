# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""config.py 配置契约测试。"""

import json

import pytest
from pydantic import ValidationError

from redis_spi.config import RedisMode, RedisProviderSettings
from redis_spi.exceptions import RedisConfigError


class TestDefaults:
    @staticmethod
    def test_provider_defaults_to_native():
        settings = RedisProviderSettings()
        assert settings.provider == "native"
        assert settings.provider_class == ""
        assert settings.text_mode is False

    @staticmethod
    def test_pool_defaults():
        settings = RedisProviderSettings()
        assert settings.subscriber_pool_size == 1
        assert settings.blocking_pool_size == 2

    @staticmethod
    def test_connection_defaults():
        settings = RedisProviderSettings()
        assert settings.mode is RedisMode.SINGLE
        assert settings.host == "127.0.0.1"
        assert settings.port == 6379
        assert settings.redis_transaction_enabled is True


class TestAliasConstruction:
    @staticmethod
    def test_alias_kwargs_follow_repo_convention():
        # 与 common_utils.RedisSettings 相同的别名 kwarg 形态
        settings = RedisProviderSettings(
            REDIS_PROVIDER="module:pkg.Cls",
            REDIS_TEXT_MODE=True,
            REDIS_SUBSCRIBER_POOL_SIZE=4,
        )
        assert settings.provider == "module:pkg.Cls"
        assert settings.text_mode is True
        assert settings.subscriber_pool_size == 4

    @staticmethod
    def test_env_var_overrides_default(monkeypatch):
        monkeypatch.setenv("REDIS_PROVIDER", "some-plugin")
        monkeypatch.setenv("REDIS_PORT", "6380")
        settings = RedisProviderSettings()
        assert settings.provider == "some-plugin"
        assert settings.port == 6380

    @staticmethod
    def test_field_name_kwargs_accepted():
        # populate_by_name：字段名 kwarg（代码内构造的正统形态）同样可用
        settings = RedisProviderSettings(provider="my-plugin", port=6380, db=3)
        assert settings.provider == "my-plugin"
        assert settings.port == 6380
        assert settings.db == 3


class TestProviderConfig:
    @staticmethod
    def test_json_string_parsed():
        settings = RedisProviderSettings(
            REDIS_PROVIDER_CONFIG=json.dumps({"endpoint": "proxy:7000", "timeout": 30})
        )
        assert settings.provider_config == {"endpoint": "proxy:7000", "timeout": 30}

    @staticmethod
    def test_dict_passthrough():
        settings = RedisProviderSettings(REDIS_PROVIDER_CONFIG={"a": 1})
        assert settings.provider_config == {"a": 1}

    @staticmethod
    def test_invalid_json_rejected():
        with pytest.raises(ValidationError):
            RedisProviderSettings(REDIS_PROVIDER_CONFIG="{not json")

    @staticmethod
    def test_non_object_json_rejected():
        with pytest.raises(ValidationError):
            RedisProviderSettings(REDIS_PROVIDER_CONFIG="[1, 2]")

    @staticmethod
    def test_empty_string_means_empty_dict():
        settings = RedisProviderSettings(REDIS_PROVIDER_CONFIG="")
        assert settings.provider_config == {}


class TestRawProviderConfig:
    @staticmethod
    def test_merges_file_and_inline_inline_wins(tmp_path):
        config_file = tmp_path / "plugin.json"
        config_file.write_text(
            json.dumps({"endpoint": "file-endpoint", "only-in-file": 1}),
            encoding="utf-8",
        )
        settings = RedisProviderSettings(
            REDIS_PROVIDER_CONFIG_FILE=str(config_file),
            REDIS_PROVIDER_CONFIG={"endpoint": "inline-endpoint"},
        )
        merged = settings.raw_provider_config()
        assert merged == {
            "endpoint": "inline-endpoint",  # 内联优先
            "only-in-file": 1,
        }

    @staticmethod
    def test_returns_new_dict_each_call():
        settings = RedisProviderSettings(REDIS_PROVIDER_CONFIG={"a": 1})
        first = settings.raw_provider_config()
        first["a"] = 999
        assert settings.raw_provider_config() == {"a": 1}

    @staticmethod
    def test_missing_file_raises_config_error(tmp_path):
        settings = RedisProviderSettings(
            REDIS_PROVIDER_CONFIG_FILE=str(tmp_path / "nope.json")
        )
        with pytest.raises(RedisConfigError):
            settings.raw_provider_config()

    @staticmethod
    def test_non_json_file_raises_config_error(tmp_path):
        config_file = tmp_path / "bad.json"
        config_file.write_text("not-json", encoding="utf-8")
        settings = RedisProviderSettings(REDIS_PROVIDER_CONFIG_FILE=str(config_file))
        with pytest.raises(RedisConfigError):
            settings.raw_provider_config()

    @staticmethod
    def test_gbk_encoded_file_raises_config_error(tmp_path):
        # 中文 Windows 真实运维错误：记事本另存为 ANSI(GBK) 的配置文件
        config_file = tmp_path / "gbk.json"
        config_file.write_bytes(b'{"k": "\xd6\xd0\xce\xc4"}')
        settings = RedisProviderSettings(REDIS_PROVIDER_CONFIG_FILE=str(config_file))
        with pytest.raises(RedisConfigError):
            settings.raw_provider_config()
