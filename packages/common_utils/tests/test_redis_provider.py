# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Redis Provider 工厂测试：配置解析、自定义插件加载（文件路径/模块名）、错误报文。

与 Java 侧 RedisClientProviderFactoryTest 对应，验证可替换性：
以配置切换到演示用自研 Provider（不修改框架源码）。
"""

import os
import sys
from pathlib import Path

import pytest

from common_utils.common_config import RedisSettings
from common_utils.redis_provider import (
    DefaultRedisProvider,
    InMemoryRedisProvider,
    get_redis_provider,
)

_TESTS_DIR = Path(__file__).resolve().parent
_DEMO_FILE = _TESTS_DIR / "demo_custom_provider.py"


def _settings(provider_type="redis", module="", cls=""):
    # pydantic validation_alias 生效：以别名（环境变量名）构造（与 test_redis_manager 约定一致）
    return RedisSettings(
        REDIS_PROVIDER_TYPE=provider_type,
        REDIS_PROVIDER_MODULE=module,
        REDIS_PROVIDER_CLASS=cls,
    )


# ------------------------------------------------------------------ #
# 默认与内置 Provider
# ------------------------------------------------------------------ #
def test_default_provider_is_redis_py():
    provider = get_redis_provider(_settings())
    assert provider.name() == DefaultRedisProvider.NAME


def test_memory_provider_by_type():
    provider = get_redis_provider(_settings(provider_type="memory"))
    assert isinstance(provider, InMemoryRedisProvider)


def test_provider_type_is_case_insensitive():
    provider = get_redis_provider(_settings(provider_type="MEMORY"))
    assert isinstance(provider, InMemoryRedisProvider)


def test_unknown_provider_type_raises_with_available_names():
    with pytest.raises(ValueError, match="not-registered"):
        get_redis_provider(_settings(provider_type="not-registered"))


# ------------------------------------------------------------------ #
# 自定义 Provider 插件加载（不修改框架源码）
# ------------------------------------------------------------------ #
def test_custom_provider_loaded_by_file_path():
    provider = get_redis_provider(
        _settings(module=str(_DEMO_FILE), cls="DemoCustomRedisProvider")
    )
    assert provider.name() == "demo-custom"


def test_custom_provider_loaded_by_module_name():
    # tests 目录加入 sys.path 后按模块名加载（模拟已安装到 site-packages 的插件包）
    sys.path.insert(0, str(_TESTS_DIR))
    try:
        provider = get_redis_provider(
            _settings(module="demo_custom_provider", cls="DemoCustomRedisProvider")
        )
        assert provider.name() == "demo-custom"
    finally:
        sys.path.remove(str(_TESTS_DIR))


def test_custom_provider_client_works():
    provider = get_redis_provider(
        _settings(module=str(_DEMO_FILE), cls="DemoCustomRedisProvider")
    )
    client = provider.create_sync_client(None)
    client.set("demo:key", "value")
    assert client.get("demo:key") == b"value"
    assert client.write_ops == 1
    assert client.read_ops == 1


def test_custom_provider_module_not_found_raises_import_error():
    with pytest.raises(ImportError, match="not-exists-module"):
        get_redis_provider(
            _settings(module="not-exists-module", cls="Whatever")
        )


def test_custom_provider_class_not_found_raises_attribute_error():
    with pytest.raises(AttributeError, match="NoSuchClass"):
        get_redis_provider(
            _settings(module=str(_DEMO_FILE), cls="NoSuchClass")
        )


def test_custom_provider_class_not_inheriting_raises_type_error():
    # 目标模块中的非 Provider 类
    with pytest.raises(TypeError, match="does not inherit from RedisProvider"):
        get_redis_provider(
            _settings(module=str(_DEMO_FILE), cls="DemoCustomSyncRedisClient")
        )


def test_custom_provider_missing_module_raises_value_error():
    with pytest.raises(ValueError, match="REDIS_PROVIDER_MODULE"):
        get_redis_provider(_settings(module="", cls="DemoCustomRedisProvider"))


def test_custom_provider_missing_class_raises_value_error():
    with pytest.raises(ValueError, match="REDIS_PROVIDER_CLASS"):
        get_redis_provider(_settings(module=str(_DEMO_FILE), cls=""))


# ------------------------------------------------------------------ #
# 环境变量配置切换
# ------------------------------------------------------------------ #
def test_provider_switch_by_env_variables(env_cleanup):
    os.environ["REDIS_PROVIDER_TYPE"] = "memory"
    provider = get_redis_provider()
    assert isinstance(provider, InMemoryRedisProvider)


def test_custom_provider_by_env_variables(env_cleanup):
    os.environ["REDIS_PROVIDER_TYPE"] = "custom"
    os.environ["REDIS_PROVIDER_MODULE"] = str(_DEMO_FILE)
    os.environ["REDIS_PROVIDER_CLASS"] = "DemoCustomRedisProvider"
    provider = get_redis_provider()
    assert provider.name() == "demo-custom"
