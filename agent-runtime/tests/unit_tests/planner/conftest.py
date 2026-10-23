# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""planner UT 共享 stub。

stream_post_utils 的导入链经 model_util → jiuwen.plugin → store 层，
强依赖 psycopg2（原生库，单测环境未装）。此处注入最小 stub，
仅满足模块导入，不触达真实 DB。
"""

import sys
import types


def _install_psycopg2_stub() -> None:
    if "psycopg2" in sys.modules:
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

        def as_string(self, *args, **kwargs):
            return ""

    for name in ("Identifier", "SQL", "Literal", "Placeholder", "Composed"):
        setattr(sql_mod, name, type(name, (_SqlObj,), {}))
    psycopg2.sql = sql_mod

    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = extras
    sys.modules["psycopg2.sql"] = sql_mod


_install_psycopg2_stub()
