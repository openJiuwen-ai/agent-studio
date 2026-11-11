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

    @staticmethod
    def test_cluster_mode_rotates_nodes_on_repeated_calls(reset_common_utils_state, monkeypatch):
        """每次调用推进游标，多次调用（模拟重连重试）在节点间轮换。"""
        from common_utils import redis_manager as rm
        created = []

        class _FakeRedis:
            def __init__(self, **kw):
                created.append((kw["host"], kw["port"]))

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(
            REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1:7000,h2:7001",
        )
        inst._settings = settings
        inst._client = MagicMock()
        from common_utils.redis_manager import get_pubsub_client
        # 3 次调用、2 个节点 → h1, h2, h1
        get_pubsub_client()
        get_pubsub_client()
        get_pubsub_client()
        assert created == [("h1", 7000), ("h2", 7001), ("h1", 7000)]

    @staticmethod
    def test_cluster_mode_first_node_down_rotates_to_next(reset_common_utils_state, monkeypatch):
        """首节点不可用时，重连重试切换到其他节点。

        模拟 subscribe_runtime_cancel 的重试场景：首次 get_pubsub_client 连接首节点
        （h1）后订阅失败，重试再次调用 get_pubsub_client 应返回下一节点（h2）的客户端，
        而非再次绑定同一首节点——否则首节点下线时订阅会持续失败直到进程重启。
        """
        from common_utils import redis_manager as rm
        created = []

        class _FakeRedis:
            def __init__(self, **kw):
                created.append((kw["host"], kw["port"]))

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(
            REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1:7000,h2:7001,h3:7002",
        )
        inst._settings = settings
        inst._client = MagicMock()
        from common_utils.redis_manager import get_pubsub_client
        first = get_pubsub_client()  # 首次：首节点 h1
        second = get_pubsub_client()  # 重试：应切换到 h2
        assert created[0] == ("h1", 7000)
        assert created[1] == ("h2", 7001)
        assert created[0] != created[1]  # 重试不再绑定同一首节点
        assert isinstance(first, _FakeRedis)
        assert isinstance(second, _FakeRedis)

    @staticmethod
    def test_cluster_mode_single_node_still_works(reset_common_utils_state, monkeypatch):
        """仅配置一个节点时轮换退化为固定该节点，不报错。"""
        from common_utils import redis_manager as rm
        created = []

        class _FakeRedis:
            def __init__(self, **kw):
                created.append((kw["host"], kw["port"]))

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="only:6380")
        inst._settings = settings
        inst._client = MagicMock()
        from common_utils.redis_manager import get_pubsub_client
        get_pubsub_client()
        get_pubsub_client()
        assert created == [("only", 6380), ("only", 6380)]

    @staticmethod
    def test_cluster_mode_empty_nodes_raises(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        class _FakeRedis:
            def __init__(self, **kw):
                pass

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES=" , , ")
        inst._settings = settings
        inst._client = MagicMock()
        from common_utils.redis_manager import get_pubsub_client
        with pytest.raises(ValueError):
            get_pubsub_client()

    @staticmethod
    def test_pubsub_node_index_reset_on_singleton_reset(reset_common_utils_state, monkeypatch):
        """reset() 复位游标，避免跨用例残留导致起始节点不确定。"""
        from common_utils import redis_manager as rm
        created = []

        class _FakeRedis:
            def __init__(self, **kw):
                created.append(kw["host"])

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(
            REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1:7000,h2:7001",
        )
        inst._settings = settings
        inst._client = MagicMock()
        from common_utils.redis_manager import get_pubsub_client
        get_pubsub_client()  # h1，游标推进到 1
        assert inst._pubsub_node_index == 1
        RedisClientManager.reset()
        assert RedisClientManager._pubsub_node_index == 0


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
