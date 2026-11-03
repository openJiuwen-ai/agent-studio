# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""planner UT 共享 stub。

stream_post_utils 的导入链经 model_util → jiuwen.plugin → store 层，
强依赖 psycopg2（原生库，单测环境可能未装）。真实库可导入时不装替身；
仅当导入失败时装最小 stub 供被测模块完成导入，并在加载完成后立即卸载，
不向同会话其他用例泄漏（真实库已装的环境不得拿到残缺替身；后续用例的
导入均命中 sys.modules 缓存，不再触发 psycopg2）。
"""

import importlib
import sys
import types

_PSYCOPG2_STUB_KEYS = ("psycopg2", "psycopg2.extras", "psycopg2.sql")


def _install_psycopg2_stub() -> None:
    """注入最小 psycopg2 替身（仅满足模块导入，不触达真实 DB）。"""
    if any(key in sys.modules for key in _PSYCOPG2_STUB_KEYS):
        return

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


def _uninstall_psycopg2_stub() -> None:
    for key in _PSYCOPG2_STUB_KEYS:
        sys.modules.pop(key, None)


def _load_stream_post_utils():
    """加载被测模块：真实 psycopg2 可用时零替身；缺失时临时 stub 后卸载。"""
    try:
        import psycopg2  # noqa: F401

        return importlib.import_module("jiuwen.planner.common.stream_post_utils")
    except ModuleNotFoundError:
        pass

    _install_psycopg2_stub()
    try:
        return importlib.import_module("jiuwen.planner.common.stream_post_utils")
    finally:
        _uninstall_psycopg2_stub()


load_stream_post_utils = _load_stream_post_utils()
