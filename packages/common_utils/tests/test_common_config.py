# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.common_config (RedisMode / RedisSettings)."""

import pytest

from common_utils.common_config import RedisMode, RedisSettings


class TestRedisMode:
    def test_enum_values(self):
        assert RedisMode.SINGLE.value == "single"
        assert RedisMode.CLUSTER.value == "cluster"
        assert RedisMode.SENTINEL.value == "sentinel"

    def test_enum_membership(self):
        assert RedisMode("single") is RedisMode.SINGLE
        assert RedisMode("cluster") is RedisMode.CLUSTER
        assert RedisMode("sentinel") is RedisMode.SENTINEL

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            RedisMode("invalid-mode")


class TestRedisSettingsDefaults:
    def test_default_mode(self):
        settings = RedisSettings()
        assert settings.mode is RedisMode.SINGLE

    def test_default_host_port(self):
        settings = RedisSettings()
        assert settings.host == "127.0.0.1"
        assert settings.port == 6379

    def test_default_db(self):
        settings = RedisSettings()
        assert settings.db == 0

    def test_default_password_none(self):
        settings = RedisSettings()
        assert settings.password is None

    def test_default_transaction_enabled(self):
        settings = RedisSettings()
        assert settings.redis_transaction_enabled is True

    def test_default_cluster_nodes_empty(self):
        settings = RedisSettings()
        assert settings.cluster_nodes == ""

    def test_default_sentinel(self):
        settings = RedisSettings()
        assert settings.sentinel_master == "mymaster"
        assert settings.sentinel_nodes == ""

    def test_default_pool_sizes(self):
        settings = RedisSettings()
        assert settings.max_connections == 50
        assert settings.socket_timeout == 5
        assert settings.socket_connect_timeout == 5

    def test_default_ssl_disabled(self):
        settings = RedisSettings()
        assert settings.ssl_enabled is False
        assert settings.ssl_ca_cert == ""
        assert settings.ssl_cert_file == ""
        assert settings.ssl_key_file == ""

    def test_default_datasource_ttl(self):
        settings = RedisSettings()
        assert settings.datasource_ttl_seconds == 3 * 24 * 60 * 60


class TestRedisSettingsFromEnv:
    def test_mode_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_MODE"] = "cluster"
        settings = RedisSettings()
        assert settings.mode is RedisMode.CLUSTER

    def test_host_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_HOST"] = "redis.example.com"
        settings = RedisSettings()
        assert settings.host == "redis.example.com"

    def test_port_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_PORT"] = "6380"
        settings = RedisSettings()
        assert settings.port == 6380

    def test_password_plaintext_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_PASSWORD"] = "plain-pass"
        settings = RedisSettings()
        # 明文密码经 decrypt（PlainCrypt）透传，保持原值。
        assert settings.password == "plain-pass"

    def test_transaction_enabled_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_TRANSACTION_ENABLED"] = "false"
        settings = RedisSettings()
        assert settings.redis_transaction_enabled is False

    def test_cluster_nodes_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_CLUSTER_NODES"] = "a:1,b:2"
        settings = RedisSettings()
        assert settings.cluster_nodes == "a:1,b:2"

    def test_sentinel_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_SENTINEL_MASTER"] = "master-x"
        os.environ["REDIS_SENTINEL_NODES"] = "s1:26379"
        settings = RedisSettings()
        assert settings.sentinel_master == "master-x"
        assert settings.sentinel_nodes == "s1:26379"

    def test_ttl_from_env(self, env_cleanup):
        import os
        os.environ["REDIS_TTL"] = "3600"
        settings = RedisSettings()
        assert settings.datasource_ttl_seconds == 3600


class TestRedisSettingsUnknownKeysIgnored:
    def test_extra_env_ignored(self, env_cleanup):
        import os
        os.environ["REDIS_SOMETHING_UNKNOWN"] = "whatever"
        # extra="ignore"，未知字段不应导致实例化失败。
        settings = RedisSettings()
        assert settings.host == "127.0.0.1"
