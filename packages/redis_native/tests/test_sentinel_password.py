# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""哨兵自身认证传参单测：sentinel_password 必须经命名形参 sentinel_kwargs 传入。

若经 ** 展开进 connection_kwargs：(a) 哨兵节点自身收不到密码（认证目的落空）；
(b) sentinel_password 键混入数据节点连接参数，master_for 建连时抛
TypeError（AbstractConnection 不识别该参数）——哨兵模式一旦配置密码即全不可用。
"""

from types import SimpleNamespace

from redis_native import connection as connection_module
from redis_native.connection import build_async_client
from redis_spi.config import RedisMode, RedisProviderSettings


def make_settings(**overrides) -> RedisProviderSettings:
    return RedisProviderSettings(_env_file=None, **overrides)


def _capture_sentinel_ctor(monkeypatch):
    """以模块级工厂函数替换 Sentinel，捕获构造参数。

    免类定义（Fake 类方法体不用 self 会命中 CodeCheck G.CLS.07），
    master_for 用 SimpleNamespace 挂 lambda 提供空实现。
    """
    captured = {}

    def _fake_sentinel(sentinels, sentinel_kwargs=None, **connection_kwargs):
        captured["sentinel_kwargs"] = sentinel_kwargs
        captured["connection_kwargs"] = connection_kwargs
        return SimpleNamespace(master_for=lambda *args, **kwargs: object())

    monkeypatch.setattr(connection_module, "Sentinel", _fake_sentinel)
    return captured


def test_sentinel_password_via_named_kwarg(monkeypatch):
    """哨兵密码必须落在命名形参 sentinel_kwargs 的 password 键，不得混入 connection_kwargs。"""
    captured = _capture_sentinel_ctor(monkeypatch)
    build_async_client(
        make_settings(
            mode=RedisMode.SENTINEL,
            sentinel_nodes="s1:26379",
            sentinel_master="mymaster",
            sentinel_password="sentinel-pw",
            password="data-pw",
        )
    )
    assert captured["sentinel_kwargs"] is not None
    assert captured["sentinel_kwargs"].get("password") == "sentinel-pw"
    # 显式 sentinel_kwargs 会关闭 redis-py 对 socket_* 的自动复用，须自带（与
    # connection_kwargs 同值），否则配密码路径的哨兵连接丢失超时
    assert (
        captured["sentinel_kwargs"]["socket_timeout"]
        == captured["connection_kwargs"]["socket_timeout"]
    )
    assert (
        captured["sentinel_kwargs"]["socket_connect_timeout"]
        == captured["connection_kwargs"]["socket_connect_timeout"]
    )
    assert "sentinel_password" not in captured["connection_kwargs"]


def test_without_sentinel_password_connection_kwargs_unchanged(monkeypatch):
    """未配置哨兵密码：connection_kwargs 保持 socket_* 两键（master 池继承语义不变）。"""
    captured = _capture_sentinel_ctor(monkeypatch)
    build_async_client(
        make_settings(
            mode=RedisMode.SENTINEL,
            sentinel_nodes="s1:26379",
            sentinel_master="mymaster",
        )
    )
    assert captured["sentinel_kwargs"] is None
    assert set(captured["connection_kwargs"]) == {"socket_timeout", "socket_connect_timeout"}
