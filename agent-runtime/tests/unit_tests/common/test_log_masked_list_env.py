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
