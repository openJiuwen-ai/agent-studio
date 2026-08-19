# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""DBUtil 单元测试 — 覆盖 G.PRM.03：连接资源在 reset/reconnect 时成对释放。

测试仅通过公开 API（DBUtil.instance / DBUtil.reset / 返回值）观察行为，
不直接访问受保护成员 _instance（G.CLS.11）。
"""

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
    """每个用例前后确保单例干净，避免互相污染（走公开 reset）。"""
    DBUtil.reset()
    yield
    DBUtil.reset()


class TestResetClosesConnection:
    """reset() 必须关闭既有连接（G.PRM.03：重置场景下成对释放）。"""

    @staticmethod
    def test_reset_closes_existing_connection():
        conn = MagicMock()
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="mysql", port=3306)
            with patch("pymysql.connect", return_value=conn):
                DBUtil.instance()  # 通过公开 API 填入单例
        DBUtil.reset()
        conn.close.assert_called_once()

    @staticmethod
    def test_reset_when_none_is_safe_noop():
        # 单例为 None 时 reset 不应抛异常（连续 reset 验证幂等安全）
        DBUtil.reset()
        DBUtil.reset()

    @staticmethod
    def test_reset_swallows_close_failure():
        # close() 自身抛异常（如连接已断）不应冒泡，仍要把单例置空
        conn = MagicMock()
        conn.close.side_effect = RuntimeError("already closed")
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="mysql", port=3306)
            with patch("pymysql.connect", return_value=conn):
                DBUtil.instance()
        DBUtil.reset()  # close 抛异常不应冒泡
        conn.close.assert_called_once()


class TestReconnectClosesOldConnection:
    """instance(reconnect=True) 必须先关闭旧连接再建新连接（G.PRM.03）。"""

    @staticmethod
    def test_reconnect_mysql_closes_old():
        old = MagicMock()
        new = MagicMock()
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="mysql", port=3306)
            with patch("pymysql.connect", return_value=old):
                DBUtil.instance()  # 先建立旧连接
            with patch("pymysql.connect", return_value=new) as patched:
                result = DBUtil.instance(reconnect=True)
        old.close.assert_called_once()
        patched.assert_called_once()
        assert result is new

    @staticmethod
    def test_reconnect_gaussdb_closes_old():
        # 被扫描项（序号 5）：py_opengauss.open 后未 close
        old = MagicMock()
        new = MagicMock()
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="gaussdb", port=5432)
            with patch("py_opengauss.open", return_value=old):
                DBUtil.instance()
            with patch("py_opengauss.open", return_value=new) as patched:
                result = DBUtil.instance(reconnect=True)
        old.close.assert_called_once()
        patched.assert_called_once()
        assert result is new

    @staticmethod
    def test_first_connect_does_not_close_anything():
        # 首次连接（单例为空）不应调用 close
        new = MagicMock()
        with patch.object(db_module, "settings") as settings_mock:
            settings_mock.db_config = _cfg(db_type="mysql", port=3306)
            with patch("pymysql.connect", return_value=new):
                result = DBUtil.instance(reconnect=True)
        new.close.assert_not_called()
        assert result is new
