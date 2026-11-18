# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""legacy jiuwen logger 的唯一级别开关是 LOG_LEVEL。

这里钉住：LOG_LEVEL 生效（含小写值）、未配置时回退 config.yaml。
"""

import logging

import pytest

from jiuwen.common.log.base import SingletonLogger
from jiuwen.common.log.perf_log import PerformanceLogBuffer

_PROBE_LOG_TYPE = "jiuwen_level_probe"


def _get_probe_logger(tmp_path):
    return SingletonLogger.build_logger(
        _PROBE_LOG_TYPE,
        {"level": "WARNING"},
        "console",
        str(tmp_path / "probe.log"),
    )


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)


def test_env_level_is_applied_and_uppercased(monkeypatch, tmp_path):
    """部署常写小写（debug），stdlib setLevel 只认大写，必须归一。"""
    monkeypatch.setenv("LOG_LEVEL", "debug")
    probe = _get_probe_logger(tmp_path)
    try:
        assert probe.level == logging.DEBUG
    finally:
        probe.handlers.clear()


def test_falls_back_to_config_level_when_env_absent(tmp_path):
    probe = _get_probe_logger(tmp_path)
    try:
        assert probe.level == logging.WARNING
    finally:
        probe.handlers.clear()


def test_perf_buffer_follows_log_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "warning")
    assert PerformanceLogBuffer().log_level == logging.WARNING
