# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.common_config (RedisMode / RedisSettings)."""

import pytest

from common_utils.common_config import RedisMode, RedisSettings


class TestRedisMode:
    @staticmethod
    def test_enum_values():
        assert RedisMode.SINGLE.value == "single"
        assert RedisMode.CLUSTER.value == "cluster"
        assert RedisMode.SENTINEL.value == "sentinel"

    @staticmethod
    def test_enum_membership():
        assert RedisMode("single") is RedisMode.SINGLE
        assert RedisMode("cluster") is RedisMode.CLUSTER
        assert RedisMode("sentinel") is RedisMode.SENTINEL

    @staticmethod
    def test_invalid_mode_raises():
        with pytest.raises(ValueError):
            RedisMode("invalid-mode")


class TestRedisSettingsDefaults:
    @staticmethod
    def test_default_mode():
        settings = RedisSettings()
        assert settings.mode is RedisMode.SINGLE

    @staticmethod
    def test_default_host_port():
        settings = RedisSettings()
        assert settings.host == "127.0.0.1"
        assert settings.port == 6379

    @staticmethod
    def test_default_db():
        settings = RedisSettings()
        assert settings.db == 0

    @staticmethod
    def test_default_password_none():
        settings = RedisSettings()
        assert settings.password is None

    @staticmethod
    def test_default_transaction_enabled():
        settings = RedisSettings()
        assert settings.redis_transaction_enabled is True

    @staticmethod
    def test_default_cluster_nodes_empty():
        settings = RedisSettings()
        assert settings.cluster_nodes == ""

    @staticmethod
    def test_default_sentinel():
        settings = RedisSettings()
        assert settings.sentinel_master == "mymaster"
        assert settings.sentinel_nodes == ""

    @staticmethod
    def test_default_pool_sizes():
        settings = RedisSettings()
        assert settings.max_connections == 50
        assert settings.socket_timeout == 5
        assert settings.socket_connect_timeout == 5

    @staticmethod
    def test_default_ssl_disabled():
        settings = RedisSettings()
        assert settings.ssl_enabled is False
        assert settings.ssl_ca_cert == ""
        assert settings.ssl_cert_file == ""
        assert settings.ssl_key_file == ""

    @staticmethod
    def test_default_datasource_ttl():
        settings = RedisSettings()
        assert settings.datasource_ttl_seconds == 3 * 24 * 60 * 60


class TestRedisSettingsFromEnv:
    @staticmethod
    def test_mode_from_env(env_cleanup):
        import os
        os.environ["REDIS_MODE"] = "cluster"
        settings = RedisSettings()
        assert settings.mode is RedisMode.CLUSTER

    @staticmethod
    def test_host_from_env(env_cleanup):
        import os
        os.environ["REDIS_HOST"] = "redis.example.com"
        settings = RedisSettings()
        assert settings.host == "redis.example.com"

    @staticmethod
    def test_port_from_env(env_cleanup):
        import os
        os.environ["REDIS_PORT"] = "6380"
        settings = RedisSettings()
        assert settings.port == 6380

    @staticmethod
    def test_password_plaintext_from_env(env_cleanup):
        import os
        os.environ["REDIS_PASSWORD"] = "plain-pass"
        settings = RedisSettings()
        # 明文密码经 decrypt（PlainCrypt）透传，保持原值。
        assert settings.password == "plain-pass"

    @staticmethod
    def test_transaction_enabled_from_env(env_cleanup):
        import os
        os.environ["REDIS_TRANSACTION_ENABLED"] = "false"
        settings = RedisSettings()
        assert settings.redis_transaction_enabled is False

    @staticmethod
    def test_cluster_nodes_from_env(env_cleanup):
        import os
        os.environ["REDIS_CLUSTER_NODES"] = "a:1,b:2"
        settings = RedisSettings()
        assert settings.cluster_nodes == "a:1,b:2"

    @staticmethod
    def test_sentinel_from_env(env_cleanup):
        import os
        os.environ["REDIS_SENTINEL_MASTER"] = "master-x"
        os.environ["REDIS_SENTINEL_NODES"] = "s1:26379"
        settings = RedisSettings()
        assert settings.sentinel_master == "master-x"
        assert settings.sentinel_nodes == "s1:26379"

    @staticmethod
    def test_ttl_from_env(env_cleanup):
        import os
        os.environ["REDIS_TTL"] = "3600"
        settings = RedisSettings()
        assert settings.datasource_ttl_seconds == 3600


class TestRedisSettingsUnknownKeysIgnored:
    @staticmethod
    def test_extra_env_ignored(env_cleanup):
        import os
        os.environ["REDIS_SOMETHING_UNKNOWN"] = "whatever"
        # extra="ignore"，未知字段不应导致实例化失败。
        settings = RedisSettings()
        assert settings.host == "127.0.0.1"
