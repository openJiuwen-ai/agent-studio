# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for error code i18n — LanguageManager and ErrorContextBuilder."""

from agent_runtime.event_handler.base.language import LanguageManager
from agent_runtime.event_handler.base.mappers import ErrorContextBuilder


class TestLanguageManager:
    """LanguageManager i18n错误码加载测试."""

    @staticmethod
    def test_singleton():
        lm1 = LanguageManager()
        lm2 = LanguageManager()
        assert lm1 is lm2

    @staticmethod
    def test_load_english_error():
        lm = LanguageManager()
        msg, reason, suggestion = lm.get_error_context("en-us", 999999)
        assert msg == "Internal system error."
        assert "Internal system error" in reason
        assert "Contact technical support" in suggestion

    @staticmethod
    def test_load_chinese_error():
        lm = LanguageManager()
        msg, reason, suggestion = lm.get_error_context("zh-cn", 999999)
        assert msg == "系统内部错误"
        assert reason == "系统内部错误"
        assert suggestion == "请联系技术支持进行定位"

    @staticmethod
    def test_language_mapping_en():
        lm = LanguageManager()
        msg_en, _, _ = lm.get_error_context("en-us", 100002)
        msg_en2, _, _ = lm.get_error_context("en", 100002)
        assert msg_en == msg_en2 == "Parameter validation failed"

    @staticmethod
    def test_language_mapping_zh():
        lm = LanguageManager()
        msg_zh, _, _ = lm.get_error_context("zh-cn", 100002)
        msg_zh2, _, _ = lm.get_error_context("zh", 100002)
        assert msg_zh == msg_zh2 == "参数校验失败"

    @staticmethod
    def test_cache_works():
        lm = LanguageManager()
        # 第一次加载
        msg1, _, _ = lm.get_error_context("en-us", 800001)
        # 第二次应从缓存读取，结果一致
        msg2, _, _ = lm.get_error_context("en-us", 800001)
        assert msg1 == msg2 == "The inputs structure of the components does not match its definition"

    @staticmethod
    def test_unknown_code_returns_fallback():
        lm = LanguageManager()
        msg, reason, suggestion = lm.get_error_context("en-us", 0)
        assert msg == "Error 0"
        assert reason == "Internal error"
        assert suggestion == "Please try again later"

    @staticmethod
    def test_121007_encapsulation_error():
        lm = LanguageManager()
        msg, reason, suggestion = lm.get_error_context("zh-cn", 121007)
        assert "封装" in msg
        assert "异常" in reason
        assert "日志" in suggestion


class TestErrorContextBuilder:
    """ErrorContextBuilder 错误上下文构造测试."""

    @staticmethod
    def test_error_code_prefix_lowercase():
        error_code, _, _, _ = ErrorContextBuilder.get_language_context("en-us", 103004)
        assert error_code == "openjiuwen.103004"

    @staticmethod
    def test_chinese_error_context():
        error_code, error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder.get_language_context("zh-cn", 999999)
        )
        assert error_code == "openjiuwen.999999"
        assert error_msg == "系统内部错误"
        assert error_reason == "系统内部错误"
        assert error_suggestion == "请联系技术支持进行定位"

    @staticmethod
    def test_english_error_context():
        error_code, error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder.get_language_context("en-us", 100002)
        )
        assert error_code == "openjiuwen.100002"
        assert error_msg == "Parameter validation failed"
        assert "input parameter format" in error_reason
        assert "interface specification" in error_suggestion

    @staticmethod
    def test_unknown_code_fallback():
        error_code, error_msg, error_reason, error_suggestion = (
            ErrorContextBuilder.get_language_context("en-us", 0)
        )
        assert error_code == "openjiuwen.0"
        assert error_msg == "Error 0"
        assert error_reason == "Internal error"
        assert error_suggestion == "Please try again later"
