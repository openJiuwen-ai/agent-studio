# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""脱敏列表环境变量（LOG_MASKED_PATTERNS / LOG_MASKED_SENS_WORDS）的解析。

空值必须快速失败：打开 LOG_MASKED_ENABLED 却不给任何规则，是自相矛盾的配置，
宁可让进程起不来，也不能让用户误以为脱敏已生效。这里把这个裁定钉死。
"""

import pytest

from jiuwen.common.log.base import get_list_from_env

_PATTERNS = "LOG_MASKED_PATTERNS"
_WORDS = "LOG_MASKED_SENS_WORDS"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (_PATTERNS, _WORDS):
        monkeypatch.delenv(name, raising=False)


def test_valid_json_array_is_parsed(monkeypatch):
    monkeypatch.setenv(_PATTERNS, '["sk-[A-Za-z0-9]{8,}", "token=\\\\w+"]')
    assert get_list_from_env(_PATTERNS) == ['sk-[A-Za-z0-9]{8,}', "token=\\w+"]


def test_unset_falls_back_to_empty_list():
    """未设置时用默认值 "[]"：脱敏总开关关着，不读这两个变量。"""
    assert get_list_from_env(_PATTERNS) == []


def test_empty_string_raises(monkeypatch):
    """compose/.env.template 的 `LOG_MASKED_PATTERNS=` 形态：开了总开关就是配错。"""
    monkeypatch.setenv(_PATTERNS, "")
    with pytest.raises(ValueError, match="Invalid JSON format"):
        get_list_from_env(_PATTERNS)


@pytest.mark.parametrize("value", [" ", "\t", "\n  "])
def test_whitespace_only_raises(monkeypatch, value):
    monkeypatch.setenv(_WORDS, value)
    with pytest.raises(ValueError, match="Invalid JSON format"):
        get_list_from_env(_WORDS)


def test_malformed_json_raises(monkeypatch):
    monkeypatch.setenv(_WORDS, "password")
    with pytest.raises(ValueError, match="Invalid JSON format"):
        get_list_from_env(_WORDS)


def test_formatter_patch_fails_fast_when_mask_rule_missing(monkeypatch):
    """install_log_formatter_patch 安装期读取：空列表必须把进程拦在启动阶段。"""
    from agent_runtime.common import logging_context

    monkeypatch.setenv("LOG_MASKED_ENABLED", "true")
    monkeypatch.setenv(_PATTERNS, "")
    monkeypatch.setenv(_WORDS, "")

    with pytest.raises(ValueError):
        logging_context.get_sensitive_patterns()


def test_masking_formatter_fails_fast_on_invalid_regex():
    """非法正则与空串同口径 fail-fast：构造期抛 ValueError，不再静默降级关闭脱敏。"""
    from jiuwen.common.log.base import MaskingFormatter

    with pytest.raises(ValueError, match="LOG_MASKED_PATTERNS"):
        MaskingFormatter(
            fmt="%(message)s",
            sensitive_patterns=["sk-[A-Za-z0-9{8,}"],  # 缺右括号，re.error
            truncate_for_console=True,
        )


def test_get_logger_fails_fast_on_invalid_regex(monkeypatch, tmp_path):
    """base 的 SingletonLogger 构造路径（= 模块导入期形态）对非法正则同样 fail-fast。

    真实启动顺序：install_log_formatter_patch 先 import base（触发本路径，
    _OPENJIUWEN_LOGGING_MANAGED 尚为 False、会构造 handler），import 完成后才
    置位该标志。测试进程里标志已被早前 import 置位，须压回 False 复现导入期形态。
    """
    from jiuwen.common.log.base import SingletonLogger

    monkeypatch.setattr(
        "agent_runtime.common.logging_context._OPENJIUWEN_LOGGING_MANAGED", False
    )
    monkeypatch.setenv("LOG_MASKED_ENABLED", "true")
    monkeypatch.setenv(_PATTERNS, '["("]')

    with pytest.raises(ValueError, match="LOG_MASKED_PATTERNS"):
        SingletonLogger.build_logger(
            "probe_invalid_regex", {"level": "INFO"}, "console", str(tmp_path / "p.log")
        )
