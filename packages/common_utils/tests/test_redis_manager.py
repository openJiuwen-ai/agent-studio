# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.redis_manager."""

# pylint: disable=protected-access  # 白盒单测：需直接访问 _settings / _create_*_client 等内部成员

import pytest
from unittest.mock import MagicMock

from common_utils.common_config import RedisMode, RedisSettings
from common_utils.redis_manager import (
    RedisClientManager,
    _NonTransactionRedis,
    _NonTransactionSyncRedis,
    get_redis_client,
    get_sync_redis_client,
)


class TestSingleton:
    @staticmethod
    def test_get_instance_returns_same_object(reset_common_utils_state):
        a = RedisClientManager.get_instance()
        b = RedisClientManager.get_instance()
        assert a is b

    @staticmethod
    def test_direct_init_raises():
        with pytest.raises(RuntimeError):
            RedisClientManager()

    @staticmethod
    def test_is_initialized_false_by_default(reset_common_utils_state):
        assert RedisClientManager.get_instance().is_initialized is False

    @staticmethod
    def test_get_client_uninitialized_raises(reset_common_utils_state):
        with pytest.raises(RuntimeError):
            RedisClientManager.get_instance().get_client()

    @staticmethod
    def test_reset_clears_instance(reset_common_utils_state):
        RedisClientManager.get_instance()
        RedisClientManager.reset()
        inst = RedisClientManager.get_instance()
        assert inst.is_initialized is False


class TestInitNoHost:
    @staticmethod
    def test_init_with_no_host_or_cluster_skips(reset_common_utils_state):
        settings = RedisSettings(REDIS_HOST="", REDIS_CLUSTER_NODES="")
        inst = RedisClientManager.get_instance()
        inst.init(settings)
        assert inst.is_initialized is False

    @staticmethod
    def test_init_twice_skips_second(reset_common_utils_state, monkeypatch):
        inst = RedisClientManager.get_instance()
        monkeypatch.setattr(inst, "_create_client", lambda: object())
        settings = RedisSettings(REDIS_HOST="127.0.0.1")
        inst.init(settings)
        assert inst.is_initialized is True
        # 第二次 init 应跳过，_create_client 不再被调用。
        inst.init(settings)


class TestNodeParsingHelpers:
    """通过 _create_cluster_client 的节点解析路径（mock ClusterNode）测试。"""

    @staticmethod
    def test_cluster_nodes_with_port(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        nodes = []

        class _FakeNode:
            @staticmethod
            def __init__(host, port):
                nodes.append((host, port))

        monkeypatch.setattr(rm, "ClusterNode", _FakeNode)
        monkeypatch.setattr(rm, "RedisCluster", lambda **kw: None)

        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1:7000,h2:7001")
        inst._settings = settings
        inst._create_cluster_client()
        assert nodes == [("h1", 7000), ("h2", 7001)]

    @staticmethod
    def test_cluster_nodes_without_port_defaults_6379(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        nodes = []

        class _FakeNode:
            @staticmethod
            def __init__(host, port):
                nodes.append((host, port))

        monkeypatch.setattr(rm, "ClusterNode", _FakeNode)
        monkeypatch.setattr(rm, "RedisCluster", lambda **kw: None)

        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1,h2")
        inst._settings = settings
        inst._create_cluster_client()
        assert nodes == [("h1", 6379), ("h2", 6379)]

    @staticmethod
    def test_cluster_empty_nodes_raises(reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES=" , , ")
        inst._settings = settings
        with pytest.raises(ValueError):
            inst._create_cluster_client()

    @staticmethod
    def test_sentinel_empty_nodes_raises(reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="sentinel", REDIS_SENTINEL_NODES="")
        inst._settings = settings
        with pytest.raises(ValueError):
            inst._create_sentinel_client()


class TestGetPubsubClient:
    """get_pubsub_client() 在不同模式下的行为。"""

    @staticmethod
    def test_single_mode_returns_existing_client(reset_common_utils_state):
        """单机模式返回与 get_client() 相同的客户端。"""
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_HOST="127.0.0.1", REDIS_PORT=6379)
        inst._settings = settings
        inst._client = inst._create_single_client()
        from common_utils.redis_manager import get_pubsub_client
        assert get_pubsub_client() is inst._client

    @staticmethod
    def test_cluster_mode_creates_single_node_client(reset_common_utils_state, monkeypatch):
        """集群模式创建连接到第一个节点的单机 Redis 客户端。"""
        from common_utils import redis_manager as rm
        captured = {}

        class _FakeRedis:
            def __init__(self, **kw):
                captured.update(kw)

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(
            REDIS_MODE="cluster",
            REDIS_CLUSTER_NODES="h1:7000,h2:7001",
            REDIS_PASSWORD="secret",
        )
        inst._settings = settings
        inst._client = MagicMock()
        from common_utils.redis_manager import get_pubsub_client
        client = get_pubsub_client()
        assert captured["host"] == "h1"
        assert captured["port"] == 7000
        assert captured["password"] == "secret"
        assert captured["decode_responses"] is False
        assert isinstance(client, _FakeRedis)

    @staticmethod
    def test_cluster_mode_node_without_port_defaults_6379(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm
        captured = {}

        class _FakeRedis:
            def __init__(self, **kw):
                captured.update(kw)

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1,h2")
        inst._settings = settings
        inst._client = MagicMock()
        from common_utils.redis_manager import get_pubsub_client
        get_pubsub_client()
        assert captured["host"] == "h1"
        assert captured["port"] == 6379


class TestNonTransactionPipeline:
    @staticmethod
    def test_async_pipeline_defaults_non_transaction():
        import inspect
        sig = inspect.signature(_NonTransactionRedis.pipeline)
        assert sig.parameters["transaction"].default is False

    @staticmethod
    def test_sync_pipeline_defaults_non_transaction():
        import inspect
        sig = inspect.signature(_NonTransactionSyncRedis.pipeline)
        assert sig.parameters["transaction"].default is False


class TestConvenienceFunctions:
    @staticmethod
    def test_get_redis_client_uninitialized_raises(reset_common_utils_state):
        with pytest.raises(RuntimeError):
            get_redis_client()

    @staticmethod
    def test_get_sync_redis_client_no_host_raises(reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        inst._settings = RedisSettings(REDIS_HOST="", REDIS_CLUSTER_NODES="")
        with pytest.raises(RuntimeError):
            get_sync_redis_client()
