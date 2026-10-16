# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for common_utils.customer_header."""

import pytest

from common_utils.customer_header import (
    CustomerHeaderConfig,
    get_capture_keys,
    get_config,
    get_forward_list,
    get_profile,
    load_from_env,
    resolve,
    set_config,
    set_profile,
)


class TestCustomerHeaderConfigModel:
    @staticmethod
    def test_defaults():
        cfg = CustomerHeaderConfig()
        assert cfg.enabled is False
        assert cfg.mappings == {}

    @staticmethod
    def test_custom_values():
        cfg = CustomerHeaderConfig(enabled=True, mappings={"cust-a": "a"})
        assert cfg.enabled is True
        assert cfg.mappings == {"cust-a": "a"}


class TestSetGetConfig:
    @staticmethod
    def test_get_config_returns_default_when_unset(reset_common_utils_state):
        cfg = get_config()
        assert isinstance(cfg, CustomerHeaderConfig)
        assert cfg.enabled is False

    @staticmethod
    def test_set_config_then_get(reset_common_utils_state):
        cfg = CustomerHeaderConfig(enabled=True, mappings={"x": "y"})
        set_config(cfg)
        assert get_config() is cfg

    @staticmethod
    def test_set_config_none_resets(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True))
        set_config(None)
        assert get_config().enabled is False


class TestLoadFromEnv:
    @staticmethod
    def test_defaults_when_env_unset(env_cleanup):
        cfg = load_from_env()
        assert cfg.enabled is False
        assert cfg.mappings == {}

    @staticmethod
    def test_enabled_true(env_cleanup):
        import os
        os.environ["CUSTOMER_HEADER_ENABLED"] = "true"
        cfg = load_from_env()
        assert cfg.enabled is True

    @staticmethod
    def test_enabled_case_insensitive(env_cleanup):
        import os
        os.environ["CUSTOMER_HEADER_ENABLED"] = "TRUE"
        cfg = load_from_env()
        assert cfg.enabled is True

    @staticmethod
    def test_enabled_false_string(env_cleanup):
        import os
        os.environ["CUSTOMER_HEADER_ENABLED"] = "false"
        cfg = load_from_env()
        assert cfg.enabled is False

    @staticmethod
    def test_mappings_parsed(env_cleanup):
        import os
        os.environ["CUSTOMER_HEADER_MAPPINGS"] = "cust-userid:userId,cust-token:token"
        cfg = load_from_env()
        assert cfg.mappings == {"cust-userid": "userId", "cust-token": "token"}

    @staticmethod
    def test_mappings_with_spaces(env_cleanup):
        import os
        os.environ["CUSTOMER_HEADER_MAPPINGS"] = " cust-a : A , cust-b: B "
        cfg = load_from_env()
        assert cfg.mappings == {"cust-a": "A", "cust-b": "B"}

    @staticmethod
    def test_mappings_malformed_pair_skipped(env_cleanup):
        import os
        os.environ["CUSTOMER_HEADER_MAPPINGS"] = "no-colon-here,cust-a:A"
        cfg = load_from_env()
        assert cfg.mappings == {"cust-a": "A"}

    @staticmethod
    def test_mappings_empty(env_cleanup):
        import os
        os.environ["CUSTOMER_HEADER_MAPPINGS"] = ""
        cfg = load_from_env()
        assert cfg.mappings == {}


class TestResolve:
    @staticmethod
    def test_disabled_returns_empty(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=False, mappings={"a": "b"}))
        assert resolve({"a": "1"}) == {}

    @staticmethod
    def test_no_mappings_returns_empty(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True, mappings={}))
        assert resolve({"a": "1"}) == {}

    @staticmethod
    def test_rename_basic(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True, mappings={"cust-userid": "userId"}))
        assert resolve({"cust-userid": "42"}) == {"userId": "42"}

    @staticmethod
    def test_rename_case_insensitive_lookup(reset_common_utils_state):
        # resolve 会对 from_key 做 lower() 兜底查找：mapping 键大小写不敏感，
        # captured 中按小写键存储时也能命中。
        set_config(CustomerHeaderConfig(enabled=True, mappings={"Cust-UserID": "userId"}))
        assert resolve({"cust-userid": "42"}) == {"userId": "42"}

    @staticmethod
    def test_missing_key_omitted(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True, mappings={"cust-a": "A", "cust-b": "B"}))
        assert resolve({"cust-a": "1"}) == {"A": "1"}

    @staticmethod
    def test_multiple_mappings(reset_common_utils_state):
        set_config(
            CustomerHeaderConfig(
                enabled=True,
                mappings={"cust-userid": "userId", "cust-token": "token"},
            )
        )
        result = resolve({"cust-userid": "7", "cust-token": "abc"})
        assert result == {"userId": "7", "token": "abc"}


class TestForwardAndCaptureLists:
    @staticmethod
    def test_forward_list_contains_x_auth_token(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True, mappings={"cust-a": "A"}))
        keys = get_forward_list()
        assert "cust-a" in keys
        assert "X-Auth-Token" in keys

    @staticmethod
    def test_forward_list_no_duplicate_x_auth_token(reset_common_utils_state):
        set_config(
            CustomerHeaderConfig(
                enabled=True, mappings={"X-Auth-Token": "token", "cust-a": "A"}
            )
        )
        keys = get_forward_list()
        assert keys.count("X-Auth-Token") == 1

    @staticmethod
    def test_capture_keys_returns_mapping_keys(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True, mappings={"cust-a": "A", "cust-b": "B"}))
        keys = get_capture_keys()
        assert sorted(keys) == ["cust-a", "cust-b"]

    @staticmethod
    def test_capture_keys_empty(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True, mappings={}))
        assert get_capture_keys() == []


class TestBackwardCompat:
    @staticmethod
    def test_get_profile_matches_get_config(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True, mappings={"a": "b"}))
        assert get_profile() is get_config()

    @staticmethod
    def test_set_profile_with_config(reset_common_utils_state):
        cfg = CustomerHeaderConfig(enabled=True, mappings={"a": "b"})
        set_profile(cfg)
        assert get_config() is cfg

    @staticmethod
    def test_set_profile_none(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True))
        set_profile(None)
        assert get_config().enabled is False

    @staticmethod
    def test_set_profile_false(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True))
        set_profile(False)
        assert get_config().enabled is False

    @staticmethod
    def test_set_profile_other_object_ignored(reset_common_utils_state):
        set_config(CustomerHeaderConfig(enabled=True))
        set_profile(object())
        # 非 CustomerHeaderConfig / None / False 直接忽略，不改变当前配置。
        assert get_config().enabled is True
