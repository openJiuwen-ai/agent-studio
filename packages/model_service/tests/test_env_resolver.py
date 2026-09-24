# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.env_resolver."""

import pytest

from model_service.env_resolver import (
    ENV_PLACEHOLDER_PATTERN,
    env_url_error_hint,
    friendly_message,
    has_env_placeholder,
    resolve_env_placeholders,
)
from model_service.resolver import ModelServiceError


class TestHasEnvPlaceholder:
    def test_no_placeholder_returns_false(self):
        assert has_env_placeholder("http://example.com/v1") is False

    def test_with_placeholder_returns_true(self):
        assert has_env_placeholder("http://${_env.plugin_url_params.HOST}/v1") is True

    def test_empty_url_returns_false(self):
        assert has_env_placeholder("") is False

    def test_none_url_returns_false(self):
        assert has_env_placeholder(None) is False

    def test_partial_match_returns_true(self):
        assert has_env_placeholder("prefix ${_env.plugin_url_params.X} suffix") is True

    def test_missing_closing_brace_returns_false(self):
        assert has_env_placeholder("${_env.plugin_url_params.X") is False


class TestResolveEnvPlaceholders:
    def test_no_placeholder_returns_same(self):
        url = "http://example.com/v1"
        assert resolve_env_placeholders(url, None) == url

    def test_empty_url_returns_empty(self):
        assert resolve_env_placeholders("", {"plugin_url_params": {"X": "1"}}) == ""

    def test_resolves_single_placeholder(self):
        url = "http://${_env.plugin_url_params.HOST}/v1"
        env = {"plugin_url_params": {"HOST": "api.example.com"}}
        assert resolve_env_placeholders(url, env) == "http://api.example.com/v1"

    def test_resolves_multiple_placeholders(self):
        url = "${_env.plugin_url_params.SCHEME}://${_env.plugin_url_params.HOST}"
        env = {"plugin_url_params": {"SCHEME": "https", "HOST": "x.com"}}
        assert resolve_env_placeholders(url, env) == "https://x.com"

    def test_none_env_vars_keeps_placeholder_without_fail(self):
        url = "http://${_env.plugin_url_params.HOST}/v1"
        assert resolve_env_placeholders(url, None, fail_fast=False) == url

    def test_missing_var_fail_fast_raises(self):
        url = "http://${_env.plugin_url_params.UNKNOWN}/v1"
        env = {"plugin_url_params": {}}
        with pytest.raises(ModelServiceError) as exc_info:
            resolve_env_placeholders(url, env)
        assert exc_info.value.code == "MD_ENV_VAR_UNRESOLVED"

    def test_missing_var_no_fail_fast_keeps_literal(self):
        url = "http://${_env.plugin_url_params.UNKNOWN}/v1"
        env = {"plugin_url_params": {}}
        assert resolve_env_placeholders(url, env, fail_fast=False) == url

    def test_none_value_replaced_with_empty(self):
        url = "http://${_env.plugin_url_params.X}/v1"
        env = {"plugin_url_params": {"X": None}}
        assert resolve_env_placeholders(url, env) == "http:///v1"

    def test_int_value_stringified(self):
        url = "${_env.plugin_url_params.PORT}"
        env = {"plugin_url_params": {"PORT": 8080}}
        assert resolve_env_placeholders(url, env) == "8080"

    def test_missing_plugin_url_params_key(self):
        url = "http://${_env.plugin_url_params.X}/v1"
        env = {"other": "value"}
        with pytest.raises(ModelServiceError):
            resolve_env_placeholders(url, env)

    def test_empty_env_vars_fail_fast_raises(self):
        url = "http://${_env.plugin_url_params.X}/v1"
        with pytest.raises(ModelServiceError):
            resolve_env_placeholders(url, {})

    def test_error_message_contains_friendly_placeholder(self):
        url = "http://${_env.plugin_url_params.ali}/v1"
        with pytest.raises(ModelServiceError) as exc_info:
            resolve_env_placeholders(url, {"plugin_url_params": {}})
        assert "{ali}" in exc_info.value.msg
        assert "${_env.plugin_url_params.ali}" not in exc_info.value.msg


class TestEnvUrlErrorHint:
    def test_empty_returns_empty(self):
        assert env_url_error_hint("") == ""
        assert env_url_error_hint(None) == ""

    def test_with_placeholders(self):
        hint = env_url_error_hint("ali,host")
        assert "ali,host" in hint
        assert "环境管理" in hint


class TestFriendlyMessage:
    def test_model_service_error_uses_msg(self):
        exc = ModelServiceError("MD_X", "用户可读信息")
        assert friendly_message(exc) == "用户可读信息"

    def test_model_service_error_empty_msg_falls_back(self):
        exc = ModelServiceError("MD_X", "")
        assert friendly_message(exc) == str(exc)

    def test_strips_leading_code_prefix(self):
        exc = Exception("[181001] Model invoke failed: boom")
        assert friendly_message(exc) == "Model invoke failed: boom"

    def test_strips_trailing_tab(self):
        exc = Exception("[code]msg\t")
        assert friendly_message(exc) == "msg"

    def test_plain_exception_unchanged(self):
        exc = Exception("plain message")
        assert friendly_message(exc) == "plain message"

    def test_json_decode_error_with_msg_attr(self):
        import json
        exc = json.JSONDecodeError("msg", "doc", 0)
        # 非 ModelServiceError，走 strip 前缀逻辑，msg 不受影响。
        assert "msg" in friendly_message(exc)


class TestPattern:
    def test_pattern_matches(self):
        assert ENV_PLACEHOLDER_PATTERN.search("${_env.plugin_url_params.X}") is not None

    def test_pattern_extracts_name(self):
        m = ENV_PLACEHOLDER_PATTERN.search("${_env.plugin_url_params.myvar}")
        assert m.group(1) == "myvar"
