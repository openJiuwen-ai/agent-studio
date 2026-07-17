# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for content_review config normalization."""

import pytest

from agent_runtime.moderation.schema import normalize_content_review


class TestNormalizeContentReview:

    @staticmethod
    def test_new_format_passes_through():
        config = {
            "enabled": True,
            "rules": [{
                "keywords": ["badword"],
                "actions": {
                    "output": {"enable": True, "type": "filter", "content": ""},
                },
            }],
        }
        result = normalize_content_review(config)
        assert result["enabled"] is True
        assert len(result["rules"]) == 1
        assert result["rules"][0]["keywords"] == ["badword"]

    @staticmethod
    def test_legacy_filter_converts_to_output_filter():
        config = {
            "enabled": True,
            "filter": {"keywords": "word1,word2"},
            "replace": [],
            "reply": [],
        }
        result = normalize_content_review(config)
        assert result["enabled"] is True
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["keywords"] == ["word1", "word2"]
        assert rule["actions"]["output"]["type"] == "filter"
        assert "input" not in rule["actions"]

    @staticmethod
    def test_legacy_replace_converts_to_output_replace():
        config = {
            "enabled": True,
            "filter": {},
            "replace": [{"keywords": "bad", "content": "***"}],
            "reply": [],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["keywords"] == ["bad"]
        assert rule["actions"]["output"]["type"] == "replace"
        assert rule["actions"]["output"]["content"] == "***"

    @staticmethod
    def test_legacy_replace_with_replace_field_name():
        """旧格式 IR 中 replace 的替换内容字段名可能是 'replace' 而非 'content'。"""
        config = {
            "enabled": True,
            "filter": {},
            "replace": [{"keywords": "阿里巴巴", "replace": "XXX"}],
            "reply": [],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["actions"]["output"]["type"] == "replace"
        assert rule["actions"]["output"]["content"] == "XXX"

    @staticmethod
    def test_legacy_reply_converts_to_input_and_output():
        config = {
            "enabled": True,
            "filter": {},
            "replace": [],
            "reply": [{"keywords": "forbidden", "content": "不允许"}],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["keywords"] == ["forbidden"]
        assert rule["actions"]["input"]["type"] == "reply"
        assert rule["actions"]["input"]["content"] == "不允许"

    @staticmethod
    def test_legacy_reply_with_reply_field_name():
        """旧格式 IR 中 reply 的兜底话术字段名可能是 'reply' 而非 'content'。"""
        config = {
            "enabled": True,
            "filter": {},
            "replace": [],
            "reply": [{"keywords": "badword", "reply": "blocked"}],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["actions"]["input"]["type"] == "reply"
        assert rule["actions"]["input"]["content"] == "blocked"
        assert rule["actions"]["output"]["content"] == "blocked"

    @staticmethod
    def test_legacy_all_three_actions():
        config = {
            "enabled": True,
            "filter": {"keywords": "fw1,fw2"},
            "replace": [{"keywords": "rw", "content": "***"}],
            "reply": [{"keywords": "ban", "content": "nope"}],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 3

    @staticmethod
    def test_empty_filter_keywords_skipped():
        config = {
            "enabled": True,
            "filter": {"keywords": ""},
            "replace": [],
            "reply": [],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 0

    @staticmethod
    def test_disabled_returns_as_is():
        config = {"enabled": False}
        result = normalize_content_review(config)
        assert result["enabled"] is False
        assert result["rules"] == []

    @staticmethod
    def test_non_dict_input_returns_disabled():
        result = normalize_content_review("not a dict")
        assert result["enabled"] is False
        assert result["rules"] == []

    @staticmethod
    def test_none_input_returns_disabled():
        result = normalize_content_review(None)
        assert result["enabled"] is False
        assert result["rules"] == []

    @staticmethod
    def test_legacy_replace_with_list_keywords():
        config = {
            "enabled": True,
            "filter": {},
            "replace": [{"keywords": ["bad1", "bad2"], "content": "***"}],
            "reply": [],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        assert result["rules"][0]["keywords"] == ["bad1", "bad2"]

    @staticmethod
    def test_new_format_with_valid_rule():
        config = {
            "enabled": True,
            "rules": [
                {"keywords": ["valid"], "actions": {"output": {"enable": True, "type": "filter", "content": ""}}},
            ],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
