# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""storage 包测试配置：把三个共享包源码目录插入 sys.path，确保 import 解析到本仓库源码。"""

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
def reset_storage_state():
    """复位 storage 包的单例状态。"""
    import storage
    import storage.ports as storage_ports

    storage.S3StorageProvider.reset()
    storage_ports.set_settings(None)
    yield
    storage.S3StorageProvider.reset()
    storage_ports.set_settings(None)
