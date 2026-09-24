# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.redis_manager."""

import pytest

from common_utils.common_config import RedisMode, RedisSettings
from common_utils.redis_manager import (
    RedisClientManager,
    _NonTransactionRedis,
    _NonTransactionSyncRedis,
    get_redis_client,
    get_sync_redis_client,
)


class TestSingleton:
    def test_get_instance_returns_same_object(self, reset_common_utils_state):
        a = RedisClientManager.get_instance()
        b = RedisClientManager.get_instance()
        assert a is b

    def test_direct_init_raises(self):
        with pytest.raises(RuntimeError):
            RedisClientManager()

    def test_is_initialized_false_by_default(self, reset_common_utils_state):
        assert RedisClientManager.get_instance().is_initialized is False

    def test_get_client_uninitialized_raises(self, reset_common_utils_state):
        with pytest.raises(RuntimeError):
            RedisClientManager.get_instance().get_client()

    def test_reset_clears_instance(self, reset_common_utils_state):
        RedisClientManager.get_instance()
        RedisClientManager.reset()
        inst = RedisClientManager.get_instance()
        assert inst.is_initialized is False


class TestInitNoHost:
    def test_init_with_no_host_or_cluster_skips(self, reset_common_utils_state):
        settings = RedisSettings(REDIS_HOST="", REDIS_CLUSTER_NODES="")
        inst = RedisClientManager.get_instance()
        inst.init(settings)
        assert inst.is_initialized is False

    def test_init_twice_skips_second(self, reset_common_utils_state, monkeypatch):
        inst = RedisClientManager.get_instance()
        monkeypatch.setattr(inst, "_create_client", lambda: object())
        settings = RedisSettings(REDIS_HOST="127.0.0.1")
        inst.init(settings)
        assert inst.is_initialized is True
        # 第二次 init 应跳过，_create_client 不再被调用。
        inst.init(settings)


class TestNodeParsingHelpers:
    """通过 _create_cluster_client 的节点解析路径（mock ClusterNode）测试。"""

    def test_cluster_nodes_with_port(self, reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        nodes = []

        class _FakeNode:
            def __init__(self, host, port):
                nodes.append((host, port))

        monkeypatch.setattr(rm, "ClusterNode", _FakeNode)
        monkeypatch.setattr(rm, "RedisCluster", lambda **kw: None)

        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1:7000,h2:7001")
        inst._settings = settings
        inst._create_cluster_client()
        assert nodes == [("h1", 7000), ("h2", 7001)]

    def test_cluster_nodes_without_port_defaults_6379(self, reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        nodes = []

        class _FakeNode:
            def __init__(self, host, port):
                nodes.append((host, port))

        monkeypatch.setattr(rm, "ClusterNode", _FakeNode)
        monkeypatch.setattr(rm, "RedisCluster", lambda **kw: None)

        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1,h2")
        inst._settings = settings
        inst._create_cluster_client()
        assert nodes == [("h1", 6379), ("h2", 6379)]

    def test_cluster_empty_nodes_raises(self, reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES=" , , ")
        inst._settings = settings
        with pytest.raises(ValueError):
            inst._create_cluster_client()

    def test_sentinel_empty_nodes_raises(self, reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="sentinel", REDIS_SENTINEL_NODES="")
        inst._settings = settings
        with pytest.raises(ValueError):
            inst._create_sentinel_client()


class TestNonTransactionPipeline:
    def test_async_pipeline_defaults_non_transaction(self):
        import inspect
        sig = inspect.signature(_NonTransactionRedis.pipeline)
        assert sig.parameters["transaction"].default is False

    def test_sync_pipeline_defaults_non_transaction(self):
        import inspect
        sig = inspect.signature(_NonTransactionSyncRedis.pipeline)
        assert sig.parameters["transaction"].default is False


class TestConvenienceFunctions:
    def test_get_redis_client_uninitialized_raises(self, reset_common_utils_state):
        with pytest.raises(RuntimeError):
            get_redis_client()

    def test_get_sync_redis_client_no_host_raises(self, reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        inst._settings = RedisSettings(REDIS_HOST="", REDIS_CLUSTER_NODES="")
        with pytest.raises(RuntimeError):
            get_sync_redis_client()
