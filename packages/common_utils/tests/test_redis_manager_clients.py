# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for RedisClientManager sync client & single client creation (mocked redis classes)."""

# pylint: disable=protected-access  # 白盒单测：需直接访问 _settings / _create_*_client 等内部成员

import pytest

from common_utils.common_config import RedisSettings
from common_utils.redis_manager import (
    RedisClientManager,
    _NonTransactionRedis,
    _NonTransactionSyncRedis,
)


class TestCreateSingleClient:
    @staticmethod
    def test_transaction_enabled_uses_redis(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        captured = {}

        class _FakeRedis:
            @staticmethod
            def __init__(**kwargs):
                captured.update(kwargs)

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(
            REDIS_HOST="h", REDIS_PORT=7000, REDIS_DATABASE=2, REDIS_PASSWORD="pw",
            REDIS_TRANSACTION_ENABLED="true",
        )
        inst._settings = settings
        client = inst._create_single_client()
        assert isinstance(client, _FakeRedis)
        assert captured["host"] == "h"
        assert captured["port"] == 7000
        assert captured["db"] == 2
        assert captured["password"] == "pw"

    @staticmethod
    def test_transaction_disabled_uses_non_transaction(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        monkeypatch.setattr(rm, "_NonTransactionRedis", lambda **kw: "non-tx")
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(
            REDIS_HOST="h", REDIS_TRANSACTION_ENABLED="false",
        )
        inst._settings = settings
        assert inst._create_single_client() == "non-tx"

    @staticmethod
    def test_no_password_omits_kwarg(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        captured = {}

        class _FakeRedis:
            @staticmethod
            def __init__(**kwargs):
                captured.update(kwargs)

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_HOST="h")
        inst._settings = settings
        inst._create_single_client()
        assert "password" not in captured

    @staticmethod
    def test_ssl_enabled_adds_ssl(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        captured = {}

        class _FakeRedis:
            @staticmethod
            def __init__(**kwargs):
                captured.update(kwargs)

        class _FakeCtx:
            @staticmethod
            def load_verify_locations(*a, **k):
                return None

            @staticmethod
            def load_cert_chain(*a, **k):
                return None

        monkeypatch.setattr(rm, "Redis", _FakeRedis)
        monkeypatch.setattr(rm.ssl, "create_default_context", lambda: _FakeCtx())
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_HOST="h", REDIS_SSL_ENABLED="true")
        inst._settings = settings
        inst._create_single_client()
        assert "ssl" in captured
        assert isinstance(captured["ssl"], _FakeCtx)


class TestCreateSyncClient:
    @staticmethod
    def test_sync_transaction_enabled(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        captured = {}

        class _FakeSyncRedis:
            @staticmethod
            def __init__(**kwargs):
                captured.update(kwargs)

        monkeypatch.setattr(rm, "SyncRedis", _FakeSyncRedis)
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_HOST="h", REDIS_PORT=6379, REDIS_TRANSACTION_ENABLED="true")
        inst._settings = settings
        client = inst._create_sync_single_client()
        assert isinstance(client, _FakeSyncRedis)
        assert captured["host"] == "h"

    @staticmethod
    def test_sync_transaction_disabled(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        monkeypatch.setattr(rm, "_NonTransactionSyncRedis", lambda **kw: "non-tx-sync")
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_HOST="h", REDIS_TRANSACTION_ENABLED="false")
        inst._settings = settings
        assert inst._create_sync_single_client() == "non-tx-sync"


class TestSyncClusterParsing:
    @staticmethod
    def test_sync_cluster_nodes_parsed(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        nodes = []

        class _FakeSyncNode:
            @staticmethod
            def __init__(host, port):
                nodes.append((host, port))

        monkeypatch.setattr(rm, "SyncClusterNode", _FakeSyncNode)
        monkeypatch.setattr(rm, "SyncRedisCluster", lambda **kw: None)

        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h1:7001,h2")
        inst._settings = settings
        inst._create_sync_cluster_client()
        assert nodes == [("h1", 7001), ("h2", 6379)]

    @staticmethod
    def test_sync_cluster_empty_raises(reset_common_utils_state):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="")
        inst._settings = settings
        with pytest.raises(ValueError):
            inst._create_sync_cluster_client()


class TestModeDispatch:
    @staticmethod
    def test_create_client_cluster_mode(reset_common_utils_state, monkeypatch):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="cluster", REDIS_CLUSTER_NODES="h:1")
        inst._settings = settings
        monkeypatch.setattr(inst, "_create_cluster_client", lambda: "cluster-client")
        assert inst._create_client() == "cluster-client"

    @staticmethod
    def test_create_client_sentinel_mode(reset_common_utils_state, monkeypatch):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="sentinel", REDIS_SENTINEL_NODES="s:26379")
        inst._settings = settings
        monkeypatch.setattr(inst, "_create_sentinel_client", lambda: "sentinel-client")
        assert inst._create_client() == "sentinel-client"

    @staticmethod
    def test_create_client_single_mode(reset_common_utils_state, monkeypatch):
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(REDIS_MODE="single", REDIS_HOST="h")
        inst._settings = settings
        monkeypatch.setattr(inst, "_create_single_client", lambda: "single-client")
        assert inst._create_client() == "single-client"


class TestSSLContext:
    @staticmethod
    def test_ssl_context_loads_certs(reset_common_utils_state, monkeypatch):
        import ssl as ssl_mod
        from common_utils import redis_manager as rm

        loaded = {}

        class _FakeCtx:
            @staticmethod
            def load_verify_locations(cafile):
                loaded["ca"] = cafile

            @staticmethod
            def load_cert_chain(certfile, keyfile):
                loaded["cert"] = certfile
                loaded["key"] = keyfile

        monkeypatch.setattr(rm.ssl, "create_default_context", lambda: _FakeCtx())
        inst = RedisClientManager.get_instance()
        settings = RedisSettings(
            REDIS_SSL_CA_CERT="/ca.pem",
            REDIS_SSL_CERT_FILE="/cert.pem",
            REDIS_SSL_KEY_FILE="/key.pem",
        )
        inst._settings = settings
        ctx = inst._create_ssl_context()
        assert loaded["ca"] == "/ca.pem"
        assert loaded["cert"] == "/cert.pem"
        assert loaded["key"] == "/key.pem"

    @staticmethod
    def test_ssl_context_no_certs(reset_common_utils_state, monkeypatch):
        from common_utils import redis_manager as rm

        class _FakeCtx:
            @staticmethod
            def load_verify_locations(*a, **k):
                return None

            @staticmethod
            def load_cert_chain(*a, **k):
                return None

        monkeypatch.setattr(rm.ssl, "create_default_context", lambda: _FakeCtx())
        inst = RedisClientManager.get_instance()
        settings = RedisSettings()
        inst._settings = settings
        ctx = inst._create_ssl_context()
        assert isinstance(ctx, _FakeCtx)
