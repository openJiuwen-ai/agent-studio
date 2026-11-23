# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""单行日志长度上限（LOG_MSG_MAX_LENGTH）。

归一化后 common.log 是唯一日志副本，模型请求体/响应体没有自身截断，完全依赖
MaskingFormatter 的 console 截断；这里钉住默认值、环境变量改名与截断语义。
"""

import logging

import pytest

from jiuwen.common.log.base import (
    DEFAULT_LOG_MSG_MAX_LENGTH,
    MaskingFormatter,
    get_msg_max_length,
)

_FMT = "%(levelname)s|%(log_type)s|%(message)s"


def _record(message: str) -> logging.LogRecord:
    record = logging.LogRecord("t", logging.INFO, "f.py", 1, message, None, None)
    record.log_type = "workflow"
    return record


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("LOG_MSG_MAX_LENGTH", raising=False)
    monkeypatch.delenv("JIUWEN_LOG_MSG_MAX_LENGTH", raising=False)


def test_default_is_4000():
    assert DEFAULT_LOG_MSG_MAX_LENGTH == 4000
    assert get_msg_max_length() == 4000


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("LOG_MSG_MAX_LENGTH", "8000")
    assert get_msg_max_length() == 8000


def test_legacy_env_name_is_ignored(monkeypatch):
    """旧名 JIUWEN_LOG_MSG_MAX_LENGTH 已废弃，不应再影响截断。"""
    monkeypatch.setenv("JIUWEN_LOG_MSG_MAX_LENGTH", "123")
    assert get_msg_max_length() == 4000


@pytest.mark.parametrize("value", ["abc", "", "0", "-5"])
def test_invalid_values_fall_back_to_default(monkeypatch, value):
    monkeypatch.setenv("LOG_MSG_MAX_LENGTH", value)
    assert get_msg_max_length() == 4000


def test_console_formatter_truncates_whole_line(monkeypatch):
    monkeypatch.setenv("LOG_MSG_MAX_LENGTH", "200")
    formatter = MaskingFormatter(fmt=_FMT, truncate_for_console=True)

    out = formatter.format(_record("M" * 1000))

    assert len(out) == 200
    assert out.endswith("...")


def test_short_message_is_not_truncated(monkeypatch):
    monkeypatch.setenv("LOG_MSG_MAX_LENGTH", "200")
    formatter = MaskingFormatter(fmt=_FMT, truncate_for_console=True)

    assert formatter.format(_record("short")) == "INFO|workflow|short"


def test_non_console_formatter_keeps_full_message():
    formatter = MaskingFormatter(fmt=_FMT, truncate_for_console=False)

    assert not formatter.format(_record("M" * 1000)).endswith("...")
    assert len(formatter.format(_record("M" * 1000))) > 1000


@pytest.mark.parametrize("cap", [1, 2])
def test_tiny_cap_honors_length_contract(monkeypatch, cap):
    """max 为 1/2 时截断输出也不得超过上限。

    修复前该分支返回固定 "..."（长度 3）会超上限，截断契约在边界被破坏；
    修复后返回等长截断标记（"." * cap）。
    """
    monkeypatch.setenv("LOG_MSG_MAX_LENGTH", str(cap))
    formatter = MaskingFormatter(fmt=_FMT, truncate_for_console=True)

    out = formatter.format(_record("M" * 1000))

    assert len(out) == cap
    assert set(out) == {"."}
