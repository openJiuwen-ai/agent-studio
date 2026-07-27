# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Runner 层 UT 共享 fixtures。

pytest 的 AssertionRewritingHook 会盖住 .pth 装的 editable finder，
导致 packages/common_utils 在测试里 import 不到。这里手动把它加回
sys.path，agent_runtime.common 才能正常 init。
"""

import os
import sys
from unittest.mock import MagicMock

# 补 common_utils 到 sys.path（agent_runtime.common.config 依赖它）
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_COMMON_UTILS = os.path.join(_REPO_ROOT, "packages", "common_utils")
if os.path.isdir(_COMMON_UTILS) and _COMMON_UTILS not in sys.path:
    sys.path.append(_COMMON_UTILS)

# model_service、storage 等包在 packages/ 下，测试环境不一定在 sys.path 中，
# 提前 mock 避免 import 链报错
import types
_storage_mock = types.ModuleType("storage")
_storage_mock.__path__ = []
sys.modules.setdefault("storage", _storage_mock)
for _sub in ("exceptions", "object_storage", "storage_provider", "get_storage_provider"):
    sys.modules.setdefault(f"storage.{_sub}", MagicMock())
sys.modules.setdefault("model_service", MagicMock())

import pytest  # noqa: E402


@pytest.fixture
def env_cleanup():
    """保存/恢复 os.environ，防止测试间环境变量污染"""
    saved = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(saved)
