#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""ServerSettings unit tests."""

import os
from unittest.mock import patch

from agent_runtime.common.config import ServerSettings


class TestServerSettingsPerformanceLog:
    @staticmethod
    def _clear_performance_log_env():
        return os.environ.pop("PERFORMANCE_LOG_ENABLED", None)

    @staticmethod
    def test_default_true_when_env_absent():
        saved = TestServerSettingsPerformanceLog._clear_performance_log_env()
        try:
            s = ServerSettings(_env_file=None)
            assert s.performance_log_enabled is True
        finally:
            if saved is not None:
                os.environ["PERFORMANCE_LOG_ENABLED"] = saved

    @staticmethod
    def test_env_override_false():
        with patch.dict(os.environ, {"PERFORMANCE_LOG_ENABLED": "false"}):
            s = ServerSettings(_env_file=None)
            assert s.performance_log_enabled is False

    @staticmethod
    def test_env_override_true():
        with patch.dict(os.environ, {"PERFORMANCE_LOG_ENABLED": "true"}):
            s = ServerSettings(_env_file=None)
            assert s.performance_log_enabled is True

    @staticmethod
    def test_empty_string_defaults_true():
        """K8s YAML 空字符串 value: '' 应回退为默认值 True。"""
        with patch.dict(os.environ, {"PERFORMANCE_LOG_ENABLED": ""}):
            s = ServerSettings(_env_file=None)
            assert s.performance_log_enabled is True
