# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""DBUtil 单元测试 — 覆盖 G.PRM.03：连接资源在 reset/reconnect 时成对释放。"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent_builder.common.store import db as db_module
from agent_builder.common.store.db import DBUtil


def _cfg(db_type="mysql", port=3306, sslmode="disable", db_schema=None):
    """构造完整的 db_config，绕过环境变量依赖。"""
    return SimpleNamespace(
        host="db.host",
        port=port,
        user="u",
        password="p",
        database="d",
        db_type=db_type,
        sslmode=sslmode,
        db_schema=db_schema,
    )


@pytest.fixture(autouse=True)
def _isolate_singleton():
    """每个用例前后确保单例干净，避免互相污染。"""
    DBUtil._instance = None
    yield
    DBUtil._instance = None


class TestResetClosesConnection:
    """reset() 必须关闭既有连接（G.PRM.03：重置场景下成对释放）。"""

    def test_reset_closes_existing_connection(self):
        conn = MagicMock()
        DBUtil._instance = conn
        DBUtil.reset()
        conn.close.assert_called_once()
        assert DBUtil._instance is None

    def test_reset_when_none_is_safe_noop(self):
        DBUtil._instance = None
        DBUtil.reset()  # 无连接时不应抛异常
        assert DBUtil._instance is None

    def test_reset_swallows_close_failure(self):
        # close() 自身抛异常（如连接已断）不应冒泡，仍要把单例置空
        conn = MagicMock()
        conn.close.side_effect = RuntimeError("already closed")
        DBUtil._instance = conn
        DBUtil.reset()
        conn.close.assert_called_once()
        assert DBUtil._instance is None


class TestReconnectClosesOldConnection:
    """instance(reconnect=True) 必须先关闭旧连接再建新连接（G.PRM.03）。"""

    def test_reconnect_mysql_closes_old(self):
        old = MagicMock()
        new = MagicMock()
        DBUtil._instance = old
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="mysql", port=3306)
            with patch("pymysql.connect", return_value=new) as patched:
                result = DBUtil.instance(reconnect=True)
        patched.assert_called_once()
        old.close.assert_called_once()
        assert result is new
        assert DBUtil._instance is new

    def test_reconnect_gaussdb_closes_old(self):
        # 被扫描项（序号 5）：py_opengauss.open 后未 close
        old = MagicMock()
        new = MagicMock()
        DBUtil._instance = old
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="gaussdb", port=5432)
            with patch("py_opengauss.open", return_value=new) as patched:
                result = DBUtil.instance(reconnect=True)
        patched.assert_called_once()
        old.close.assert_called_once()
        assert result is new
        assert DBUtil._instance is new

    def test_first_connect_does_not_close_anything(self):
        # 首次连接（_instance 为 None）不应调用 close
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="mysql", port=3306)
            new = MagicMock()
            with patch("pymysql.connect", return_value=new):
                result = DBUtil.instance(reconnect=True)
        new.close.assert_not_called()
        assert result is new
        assert DBUtil._instance is new
