# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""model_service UT 共享 path 修正 + sys.modules 污染防御。

pytest 的 AssertionRewritingHook 会盖住 .pth 装的 editable finder，致
packages/model_service 在测试收集期不可导入。这里手动把三个共享包源码目录插回
sys.path，model_service.client / dispatch / policy / resolver 才能正常 init。

另（CI 根因）：兄弟目录 common/test_load_components.py 等在收集期会向 sys.modules 预注入
``model_service`` / ``model_service.env_resolver`` 的 MagicMock（非包，无 __path__）以兜底其
import 链。因 common/ 字母序先于 model_service/ 收集，本 conftest 加载时
``sys.modules["model_service"]`` 可能已被污染为 MagicMock，致
``from model_service.client import`` 报 ``'model_service' is not a package``。故加载时检测：若已被
污染为非包，清除所有 model_service* 缓存项后重新导入真实包，确保子模块按需解析到真实源码。
"""

import os
import sys

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

for _pkg in ("common_utils", "storage", "model_service"):
    _pkg_path = os.path.join(_REPO_ROOT, "packages", _pkg)
    if os.path.isdir(_pkg_path) and _pkg_path not in sys.path:
        sys.path.insert(0, _pkg_path)  # pylint: disable=no-use-sys-path-insert  # 优先解析本仓库源码

# 防御 sys.modules 污染（见模块 docstring）：仅当 model_service 已被兄弟目录预注入 MagicMock
# （非包）且真实包源码可用时，清除污染缓存后重新导入真实包。
# 注意：不能仅用 ``not hasattr(_ms, "__path__")`` 判定——MagicMock 会按访问自动创建任意属性，
# ``hasattr(MagicMock(), "__path__")`` 为 True，使判定失效、漏过污染。真实包的 __path__ 是 list；
# MagicMock/普通 module 的 __path__ 不是 list，据此区分。重新导入后 sys.modules["model_service"]
# 为真实包，后续 from model_service.client import 才能按需解析子模块；不污染其他已收集目录
# （它们持有的旧引用不受 sys.modules 删除影响）。
_ms = sys.modules.get("model_service")
_ms_src = os.path.join(_REPO_ROOT, "packages", "model_service")
if os.path.isdir(_ms_src) and not isinstance(getattr(_ms, "__path__", None), list):
    for _k in [k for k in sys.modules if k == "model_service" or k.startswith("model_service.")]:
        del sys.modules[_k]
    import model_service  # noqa: F401,E402  重新缓存真实包（子模块按需解析到 packages/ 源码）
