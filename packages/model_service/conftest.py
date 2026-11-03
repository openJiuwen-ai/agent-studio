# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""model_service 包测试配置：把三个共享包源码目录插入 sys.path，确保 import 解析到本仓库源码。"""

import os
import sys

_PKG_ROOT = os.path.dirname(os.path.abspath(__file__))
_PACKAGES_ROOT = os.path.dirname(_PKG_ROOT)

_SOURCE_DIRS = (
    os.path.join(_PACKAGES_ROOT, "common_utils"),
    os.path.join(_PACKAGES_ROOT, "model_service"),
    os.path.join(_PACKAGES_ROOT, "storage"),
)

for _dir in reversed(_SOURCE_DIRS):
    if os.path.isdir(_dir) and _dir not in sys.path:
        sys.path.insert(0, _dir)  # pylint: disable=no-use-sys-path-insert  # 优先解析本仓库源码，避免命中 site-packages 同名包

import pytest  # noqa: E402


@pytest.fixture
def env_cleanup():
    """保存/恢复 os.environ，防止测试间环境变量互相污染。"""
    saved = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(saved)


@pytest.fixture
def reset_model_service_ports():
    """复位 model_service.ports 的注入端口，避免测试间残留注入。"""
    import model_service.ports as ports

    ports.set_storage_provider(None)
    ports.set_llm_settings(None)
    ports.set_request_headers(None)
    ports.set_request_customer_headers(None)
    ports.set_env_variables(None)
    ports.set_cache_queues(None, None)
    yield
    ports.set_storage_provider(None)
    ports.set_llm_settings(None)
    ports.set_request_headers(None)
    ports.set_request_customer_headers(None)
    ports.set_env_variables(None)
    ports.set_cache_queues(None, None)


@pytest.fixture
def reset_common_utils_state():
    """复位 common_utils 的 customer_header / redis manager 全局状态。"""
    from common_utils import customer_header
    from common_utils import redis_manager
    from common_utils.crypto_tool import CryptTool, PlainCrypt

    customer_header.set_config(None)
    redis_manager.RedisClientManager.reset()
    CryptTool.set_default(PlainCrypt.NAME)
    yield
    customer_header.set_config(None)
    redis_manager.RedisClientManager.reset()
    CryptTool.set_default(PlainCrypt.NAME)
