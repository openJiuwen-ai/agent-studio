# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for storage.ports (settings injection)."""

import pytest

from storage import ports


class _Settings:
    def __init__(self, **kwargs):
        defaults = dict(
            server="http://obs", bucket="b", access_key="ak", secret_key="sk",
            enable_ssl=True, path_style="path", type="OBS",
            custom_module="", custom_class="", local_base_path="/tmp",
            local_bucket="default",
        )
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class TestSetGetSettings:
    @staticmethod
    def test_unregistered_raises(reset_storage_state):
        with pytest.raises(RuntimeError):
            ports.get_settings()

    @staticmethod
    def test_set_then_get(reset_storage_state):
        s = _Settings()
        ports.set_settings(lambda: s)
        assert ports.get_settings() is s

    @staticmethod
    def test_set_none_clears(reset_storage_state):
        s = _Settings()
        ports.set_settings(lambda: s)
        ports.set_settings(None)
        with pytest.raises(RuntimeError):
            ports.get_settings()

    @staticmethod
    def test_factory_called_each_time(reset_storage_state):
        calls = {"n": 0}

        def _factory():
            calls["n"] += 1
            return _Settings()

        ports.set_settings(_factory)
        ports.get_settings()
        ports.get_settings()
        assert calls["n"] == 2


class TestSettingsProtocol:
    @staticmethod
    def test_settings_satisfies_protocol(reset_storage_state):
        from storage.ports import ObjectStorageSettingsLike
        s = _Settings()
        assert isinstance(s, ObjectStorageSettingsLike)
