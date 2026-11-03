# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""connection 单测：三模式构建参数 + 独立池判定 + 节点解析。

真实 redis-py 对象惰性建连（首命令才连接），构建安全无网络副作用；
**cluster 不构建实例**（RedisCluster 构造期做拓扑发现），只测纯解析函数。
"""

from __future__ import annotations

import pytest
from redis.asyncio import Redis
from redis.asyncio.connection import SSLConnection

from redis_native.connection import (
    _NonTransactionRedis,
    _parse_cluster_nodes,
    _parse_sentinel_nodes,
    build_async_client,
    should_use_independent_pool,
)
from redis_spi.exceptions import RedisConfigError

from redis_spi.config import RedisMode, RedisProviderSettings


def make_settings(**overrides) -> RedisProviderSettings:
    return RedisProviderSettings(_env_file=None, **overrides)


class TestBuildSingle:
    @staticmethod
    def test_default_kwargs():
        settings = make_settings(
            host="h1", port=6380, db=3, password="secret"
        )
        client = build_async_client(settings)
        assert isinstance(client, Redis)
        kwargs = client.connection_pool.connection_kwargs
        assert kwargs["host"] == "h1"
        assert kwargs["port"] == 6380
        assert kwargs["db"] == 3
        assert kwargs["password"] == "secret"
        assert kwargs["decode_responses"] is False
        assert kwargs["socket_timeout"] == 5.0
        # max_connections 是池级参数（ConnectionPool 构造期消费），不在连接参数里
        assert client.connection_pool.max_connections == 50

    @staticmethod
    def test_transaction_wrapper_selected():
        wrapped = build_async_client(make_settings(redis_transaction_enabled=False))
        assert isinstance(wrapped, _NonTransactionRedis)
        plain = build_async_client(make_settings(redis_transaction_enabled=True))
        # 精确类型断言（G.TYP.08 有意豁免）：isinstance 会放行子类，此处验证的就是缺省装配的精确基类
        assert plain.__class__ is Redis

    @staticmethod
    def test_text_mode():
        client = build_async_client(make_settings(text_mode=True))
        assert client.connection_pool.connection_kwargs["decode_responses"] is True

    @staticmethod
    def test_socket_timeout_override_none():
        client = build_async_client(make_settings(), socket_timeout=None)
        assert client.connection_pool.connection_kwargs["socket_timeout"] is None

    @staticmethod
    def test_socket_timeout_override_value():
        client = build_async_client(make_settings(), socket_timeout=9.5)
        assert client.connection_pool.connection_kwargs["socket_timeout"] == 9.5

    @staticmethod
    def test_max_connections_override():
        client = build_async_client(make_settings(), max_connections=3)
        assert client.connection_pool.max_connections == 3

    @staticmethod
    def test_empty_password_omitted():
        client = build_async_client(make_settings(password=""))
        # 未传时 redis-py 填默认 None（区别于显式空串）
        assert client.connection_pool.connection_kwargs.get("password") is None

    @staticmethod
    def test_ssl_enabled():
        # 行为对齐口径：redis-py asyncio 的 Redis(ssl=...) 把 SSLContext 当
        # 真值标志消费（旧 redis_manager 同款传法，bug 兼容），可观测效果是
        # 连接类切到 SSLConnection；自定义 CA 参数实际未生效（Phase 4 复评点）。
        client = build_async_client(make_settings(ssl_enabled=True))
        assert client.connection_pool.connection_class is SSLConnection


class TestNonTransactionPipelineDefault:
    @staticmethod
    def test_bare_pipeline_defaults_to_false():
        client = _NonTransactionRedis(host="localhost")
        # 包装类唯一职责：翻转裸 .pipeline() 默认（SPI 路径恒显式传参）；
        # redis-py asyncio pipeline 的事务标志属性是 is_transaction
        # （.transaction 是 MULTI 命令方法，勿混淆）。
        assert client.pipeline().is_transaction is False
        assert client.pipeline(transaction=True).is_transaction is True


class TestBuildSentinel:
    @staticmethod
    def test_master_kwargs_parity_and_override():
        settings = make_settings(
            mode=RedisMode.SENTINEL, sentinel_nodes="s1:26379", password="p"
        )
        # 缺省：master 池不带显式 socket_timeout（自 sentinel 基础 kwargs 复制）
        client = build_async_client(settings)
        assert isinstance(client, Redis)
        kwargs = client.connection_pool.connection_kwargs
        assert kwargs["socket_timeout"] == 5.0
        assert kwargs["password"] == "p"
        assert kwargs["decode_responses"] is False
        # 阻塞池覆盖：显式 None 注入 master 连接参数
        blocking = build_async_client(settings, max_connections=2, socket_timeout=None)
        assert blocking.connection_pool.connection_kwargs["socket_timeout"] is None
        assert blocking.connection_pool.max_connections == 2


class TestIndependentPool:
    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (RedisMode.SINGLE, True),
            (RedisMode.SENTINEL, True),
            (RedisMode.CLUSTER, False),
        ],
    )
    def test_dispatch(self, mode, expected):
        assert should_use_independent_pool(make_settings(mode=mode)) is expected


class TestParseClusterNodes:
    @staticmethod
    def test_mixed_forms():
        nodes = _parse_cluster_nodes("h1:7000, h2")
        assert [(n.host, n.port) for n in nodes] == [("h1", 7000), ("h2", 6379)]

    @staticmethod
    def test_empty_raises():
        with pytest.raises(RedisConfigError, match="REDIS_CLUSTER_NODES"):  # S6: 配置错误族（原裸 ValueError）
            _parse_cluster_nodes("  ")


class TestParseSentinelNodes:
    @staticmethod
    def test_default_port():
        assert _parse_sentinel_nodes("s1") == [("s1", 26379)]

    @staticmethod
    def test_explicit_ports():
        assert _parse_sentinel_nodes("s1:26380,s2:26381") == [
            ("s1", 26380),
            ("s2", 26381),
        ]

    @staticmethod
    def test_empty_raises():
        with pytest.raises(RedisConfigError, match="REDIS_SENTINEL_NODES"):  # S6: 配置错误族（原裸 ValueError）
            _parse_sentinel_nodes("")
