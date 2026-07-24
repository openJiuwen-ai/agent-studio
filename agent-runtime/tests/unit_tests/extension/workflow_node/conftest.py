# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""workflow_node UT 共享 fixtures 与 path 修正。

pytest 的 AssertionRewritingHook 会盖住 .pth 装的 editable finder，
导致 packages/common_utils 在测试里 import 不到。这里手动把它加回
sys.path，agent_runtime.common 才能正常 init。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
_COMMON_UTILS = os.path.join(_REPO_ROOT, "packages", "common_utils")
if os.path.isdir(_COMMON_UTILS) and _COMMON_UTILS not in sys.path:
    sys.path.append(_COMMON_UTILS)
