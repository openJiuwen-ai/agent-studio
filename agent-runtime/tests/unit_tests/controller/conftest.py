# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""controller UT 共享 fixtures 与 path 修正。

pytest 的 AssertionRewritingHook 会盖住 .pth 装的 editable finder，
导致 packages/ 下的 editable 包在测试里 import 不到。这里手动加回
sys.path，jiuwen.multi_agent / jiuwen.extension 等模块才能正常 init。
"""

import logging
import os
import sys

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

for _pkg in ("common_utils", "storage", "model_service", "redis_spi", "redis_native"):
    _pkg_path = os.path.join(_REPO_ROOT, "packages", _pkg)
    if os.path.isdir(_pkg_path) and _pkg_path not in sys.path:
        sys.path.insert(0, _pkg_path)


# psycopg2 导入 stub：与 tests/unit_tests/planner/conftest.py 同一手法。
# controller 用例的导入链（llm_service.messages / plan_execute_mode →
# openjiuwen connector_pool）强依赖 psycopg2（原生库，单测环境可能未装）。
# 真实库可导入时不装替身；仅当导入失败时临时装最小 stub 供被测模块完成
# 导入并立即卸载，不向同会话其他用例泄漏。
def _install_psycopg2_stub() -> None:
    import types

    psycopg2 = types.ModuleType("psycopg2")

    class _Error(Exception):
        """对齐 psycopg2.Error 基类（仅满足引用，不触发）。"""

    psycopg2.Error = _Error
    psycopg2.OperationalError = type("OperationalError", (_Error,), {})

    extras = types.ModuleType("psycopg2.extras")

    def _execute_values(*args, **kwargs):
        raise AssertionError("unit tests must not touch the database")

    extras.execute_values = _execute_values
    psycopg2.extras = extras

    sql_mod = types.ModuleType("psycopg2.sql")

    class _SqlObj:
        """占位组合对象：接受任意参数，支持链式 format/join（不真正执行）。"""

        def __init__(self, *args, **kwargs):
            self._args = args

        def format(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        @staticmethod
        def as_string(*args, **kwargs):
            return ""

    for name in ("Identifier", "SQL", "Literal", "Placeholder", "Composed"):
        setattr(sql_mod, name, type(name, (_SqlObj,), {}))
    psycopg2.sql = sql_mod

    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = extras
    sys.modules["psycopg2.sql"] = sql_mod


def _preload_with_stub(modname: str) -> None:
    """真实 psycopg2 可用时零替身；缺失时临时 stub 导入后卸载。"""
    import importlib

    try:
        import psycopg2  # noqa: F401

        importlib.import_module(modname)
        return
    except ModuleNotFoundError:
        pass

    _install_psycopg2_stub()
    try:
        importlib.import_module(modname)
    finally:
        for key in ("psycopg2", "psycopg2.extras", "psycopg2.sql"):
            sys.modules.pop(key, None)


def _preload_best_effort(modname: str) -> None:
    """预加载失败不拖垮整目录 conftest。

    完整环境（CI）下预加载必然成功（全新进程直导已验证无循环导入）；
    残缺本地环境中，若更早采集的目录留下了半初始化模块，这里降级为
    用例自身的导入错误，不影响 controller 目录其他用例的采集。
    """
    try:
        _preload_with_stub(modname)
    except ImportError as exc:
        logging.warning(
            "[controller-conftest] preload %s degraded: %s", modname, exc
        )


_preload_best_effort("jiuwen.planner.common.stream_post_utils")
_preload_best_effort("jiuwen.controller.agent.control_mode.plan_execute_mode")
