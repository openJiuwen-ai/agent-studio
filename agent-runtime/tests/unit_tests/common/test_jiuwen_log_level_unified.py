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


def test_invalid_level_name_falls_back_to_warning(monkeypatch, tmp_path):
    """非法级别名回退 WARNING：导入期不抛 ValueError（真实进程由 uvicorn 先行拦截）。"""
    monkeypatch.setenv("LOG_LEVEL", "FOO")
    probe = _get_probe_logger(tmp_path)
    try:
        assert probe.level == logging.WARNING
    finally:
        probe.handlers.clear()


def test_config_level_none_falls_back_to_warning(monkeypatch, tmp_path):
    """config.yaml 写出 level: null（键在值为 None）时回退 WARNING，不再 AttributeError。"""
    probe = SingletonLogger.build_logger(
        _PROBE_LOG_TYPE, {"level": None}, "console", str(tmp_path / "probe.log")
    )
    try:
        assert probe.level == logging.WARNING
    finally:
        probe.handlers.clear()


def test_config_level_numeric_falls_back_to_warning(monkeypatch, tmp_path):
    """数值级别（YAML level: 20）按非法名处理回退 WARNING，不再 AttributeError。"""
    probe = SingletonLogger.build_logger(
        _PROBE_LOG_TYPE, {"level": 20}, "console", str(tmp_path / "probe.log")
    )
    try:
        assert probe.level == logging.WARNING
    finally:
        probe.handlers.clear()


def test_perf_buffer_config_level_none_falls_back(monkeypatch):
    """配置 level 为 None 时 perf buffer 回退 INFO，不在构造期崩。"""
    monkeypatch.setattr("jiuwen.common.log.perf_log.config", {"logging": {"level": None}})
    assert PerformanceLogBuffer().log_level == logging.INFO


def test_perf_buffer_invalid_level_falls_back(monkeypatch):
    """非法级别名走 getLevelName 字符串路径 → 回退 INFO。"""
    monkeypatch.setenv("LOG_LEVEL", "FOO")
    monkeypatch.setattr("jiuwen.common.log.perf_log.config", {"logging": {}})
    assert PerformanceLogBuffer().log_level == logging.INFO


def test_whitespace_log_level_treated_as_unset(monkeypatch, tmp_path):
    """LOG_LEVEL 仅空白（K8s value: ' '）等价未设置：回退 config 级别，与 ServerSettings 归一口径一致。"""
    monkeypatch.setenv("LOG_LEVEL", "   ")
    probe = SingletonLogger.build_logger(
        _PROBE_LOG_TYPE, {"level": "INFO"}, "console", str(tmp_path / "probe.log")
    )
    try:
        assert probe.level == logging.INFO
    finally:
        probe.handlers.clear()


def test_perf_buffer_whitespace_level_falls_back(monkeypatch):
    """perf 路径空白级别回退 INFO（getLevelName 字符串兜底），不与 settings 分叉。"""
    monkeypatch.setenv("LOG_LEVEL", "   ")
    monkeypatch.setattr("jiuwen.common.log.perf_log.config", {"logging": {}})
    assert PerformanceLogBuffer().log_level == logging.INFO


def test_cli_log_level_syncs_env(tmp_path):
    """--log-level 必须同步写回 os.environ['LOG_LEVEL']：legacy base.py 直读 env，否则级别分叉。"""
    import os
    import subprocess
    import sys

    code = (
        "import sys, types, os\n"
        "sys.path.insert(0, '.')\n"
        "fake = types.ModuleType('EIStart_base')\n"
        "fake.main = lambda: None\n"
        "sys.modules['EIStart_base'] = fake\n"
        "sys.argv = ['EIStart.py', '--log-level', 'WARNING']\n"
        "from agent_runtime.EIStart import main\n"
        "main()\n"
        "print(os.environ.get('LOG_LEVEL'))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    # 子进程 import 链会在 stdout 打启动日志，取最后一个非空行
    last_line = [l for l in result.stdout.splitlines() if l.strip()][-1]
    assert last_line == "WARNING"
