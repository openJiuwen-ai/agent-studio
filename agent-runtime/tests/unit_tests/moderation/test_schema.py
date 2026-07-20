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
    def test_legacy_reply_with_input_text_and_output_text():
        """旧版 IR 格式使用 input_text / output_text 存储各通道兜底话术。"""
        config = {
            "enabled": True,
            "filter": {},
            "replace": [],
            "reply": [{
                "keywords": "华为",
                "input_text": "输入审核-华为",
                "output_text": "",
                "input_enable": True,
                "output_enable": False,
            }],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["keywords"] == ["华为"]
        assert rule["actions"]["input"]["type"] == "reply"
        assert rule["actions"]["input"]["content"] == "输入审核-华为"
        assert "output" not in rule["actions"]

    @staticmethod
    def test_legacy_reply_output_only():
        """旧版 IR 格式：仅启用输出审核通道。"""
        config = {
            "enabled": True,
            "filter": {},
            "replace": [],
            "reply": [{
                "keywords": "京东",
                "input_text": "",
                "output_text": "输出审核京东",
                "input_enable": False,
                "output_enable": True,
            }],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["keywords"] == ["京东"]
        assert "input" not in rule["actions"]
        assert rule["actions"]["output"]["type"] == "reply"
        assert rule["actions"]["output"]["content"] == "输出审核京东"

    @staticmethod
    def test_legacy_reply_dual_channel():
        """旧版 IR 格式：输入输出双通道同时启用，各自有独立兜底话术。"""
        config = {
            "enabled": True,
            "filter": {},
            "replace": [],
            "reply": [{
                "keywords": "双向词",
                "input_text": "【输入拦截】",
                "output_text": "【输出拦截】",
                "input_enable": True,
                "output_enable": True,
            }],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 1
        rule = result["rules"][0]
        assert rule["actions"]["input"]["type"] == "reply"
        assert rule["actions"]["input"]["content"] == "【输入拦截】"
        assert rule["actions"]["output"]["type"] == "reply"
        assert rule["actions"]["output"]["content"] == "【输出拦截】"

    @staticmethod
    def test_legacy_reply_default_enable():
        """旧版 IR 格式：未指定 enable 字段时默认两个通道都启用。"""
        config = {
            "enabled": True,
            "filter": {},
            "replace": [],
            "reply": [{"keywords": "forbidden", "input_text": "input-blocked", "output_text": "output-blocked"}],
        }
        result = normalize_content_review(config)
        rule = result["rules"][0]
        assert "input" in rule["actions"]
        assert "output" in rule["actions"]
        assert rule["actions"]["input"]["content"] == "input-blocked"
        assert rule["actions"]["output"]["content"] == "output-blocked"

    @staticmethod
    def test_legacy_reply_both_disabled_skipped():
        """旧版 IR 格式：两个通道都禁用时，该规则不应生成。"""
        config = {
            "enabled": True,
            "filter": {},
            "replace": [],
            "reply": [{
                "keywords": "skipme",
                "input_text": "",
                "output_text": "",
                "input_enable": False,
                "output_enable": False,
            }],
        }
        result = normalize_content_review(config)
        assert len(result["rules"]) == 0

    @staticmethod
    def test_legacy_all_three_actions():
        config = {
            "enabled": True,
            "filter": {"keywords": "fw1,fw2"},
            "replace": [{"keywords": "rw", "content": "***"}],
            "reply": [{
                "keywords": "ban",
                "input_text": "nope",
                "output_text": "nope",
                "input_enable": True,
                "output_enable": True,
            }],
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

    @staticmethod
    def test_legacy_reply_e2e_input_block():
        """End-to-end: IR 旧格式 content_review 配置 → normalize → engine → check_input_query

        验证 bug 修复：旧版 IR 中 reply 配置的 input_text 字段能正确传到引擎的输入审核结果。
        """
        from agent_runtime.moderation.engine import ModerationEngineDynamicAC

        # 模拟真实 IR 的 content_review 配置
        ir_content_review = {
            "enabled": True,
            "filter": {"keywords": "字节跳动"},
            "replace": [{"keywords": "阿里巴巴", "replace": "XXX"}],
            "reply": [
                {
                    "keywords": "华为",
                    "input_text": "输入审核-华为",
                    "output_text": "",
                    "input_enable": True,
                    "output_enable": False,
                },
                {
                    "keywords": "京东",
                    "input_text": "",
                    "output_text": "输出审核京东",
                    "input_enable": False,
                    "output_enable": True,
                },
            ],
        }

        normalized = normalize_content_review(ir_content_review)
        engine = ModerationEngineDynamicAC(normalized)

        # 华为 → input_enable=True → 输入审核应阻断并返回兜底话术
        is_safe, result = engine.check_input_query("什么是华为")
        assert is_safe is False
        assert result == "输入审核-华为"

        # 京东 → input_enable=False → 输入审核不应阻断
        is_safe, result = engine.check_input_query("什么是京东")
        assert is_safe is True

        # 京东 → output_enable=True → 输出审核应阻断
        is_int, text = engine.clean_full_text("京东很好")
        assert is_int is True
        assert text == "输出审核京东"
