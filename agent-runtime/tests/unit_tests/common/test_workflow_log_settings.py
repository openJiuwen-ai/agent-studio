#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""WorkflowLogSettings unit tests — 日志级别可由配置/环境变量调整。

performance logger 原先在 server.py 里硬编码为 WARNING，导致
``performance_logger.info(...)`` 的性能埋点（workflow_cache|hit/miss、
ir_convert|、agent_group_stream| 等）全部被丢弃，排查时无法开启。
"""
import os
from unittest.mock import patch

from agent_runtime.common.config import WorkflowLogSettings


class TestPerformanceLogLevel:
    @staticmethod
    def _settings_without_env():
        os.environ.pop("PERFORMANCE_LOG_LEVEL", None)
        return WorkflowLogSettings(_env_file=None)

    @staticmethod
    def test_default_warning_when_env_absent():
        """缺省保持 WARNING：性能埋点静默，不放大正常运行时日志量。"""
        with patch.dict(os.environ, {}, clear=False):
            assert TestPerformanceLogLevel._settings_without_env().performance_level == "WARNING"

    @staticmethod
    def test_env_override_info():
        with patch.dict(os.environ, {"PERFORMANCE_LOG_LEVEL": "INFO"}):
            s = WorkflowLogSettings(_env_file=None)
            assert s.performance_level == "INFO"

    @staticmethod
    def test_env_override_debug():
        with patch.dict(os.environ, {"PERFORMANCE_LOG_LEVEL": "DEBUG"}):
            s = WorkflowLogSettings(_env_file=None)
            assert s.performance_level == "DEBUG"
