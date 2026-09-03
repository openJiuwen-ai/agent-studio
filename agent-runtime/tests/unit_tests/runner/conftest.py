# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Runner 层 UT 共享 fixtures"""

import os
import sys
from unittest.mock import MagicMock

# storage / model_service 真实包可用（packages/ 经 editable 安装）时用真实包：
# workflow_runner 的 import 链（llm_chain.py）需要 model_service.env_resolver 真实子模块，
# MagicMock 无 __path__ 会导致 'model_service' is not a package 收集错误；
# inner_tools 需要 storage.S3StorageProvider 真实符号。仅在真实包不可导入时兜底 mock。
try:
    import storage  # noqa: F401
except ImportError:
    _storage_mock = types.ModuleType("storage")
    _storage_mock.__path__ = []
    sys.modules.setdefault("storage", _storage_mock)
    for _sub in ("exceptions", "object_storage", "storage_provider", "get_storage_provider"):
        sys.modules.setdefault(f"storage.{_sub}", MagicMock())
try:
    import model_service  # noqa: F401
except ImportError:
    sys.modules.setdefault("model_service", MagicMock())

import pytest  # noqa: E402


@pytest.fixture
def env_cleanup():
    """保存/恢复 os.environ，防止测试间环境变量污染"""
    saved = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(saved)
