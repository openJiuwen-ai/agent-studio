# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for ModerationEngineDynamicAC."""

import pytest

from agent_runtime.moderation.engine import ActionType, ModerationEngineDynamicAC


def _make_config(keywords, action_type="filter", content="", channel="output", enabled=True):
    """Helper: build a single-rule new-format config."""
    action_cfg = {"enable": True, "type": action_type, "content": content}
    actions = {}
    actions[channel] = action_cfg
    return {
        "enabled": enabled,
        "rules": [{"keywords": keywords, "actions": actions}],
    }


class TestModerationEngineDynamicAC:

    @staticmethod
    def test_disabled_engine_allows_everything():
        engine = ModerationEngineDynamicAC({"enabled": False, "rules": []})
        assert engine.enabled is False
        assert engine.check_input_query("anything") == (True, "anything")
        assert engine.clean_full_text("anything") == (False, "anything")

    @staticmethod
    def test_no_rules_allows_everything():
        engine = ModerationEngineDynamicAC({"enabled": True, "rules": []})
        assert engine.check_input_query("anything") == (True, "anything")
        assert engine.clean_full_text("anything") == (False, "anything")

    @staticmethod
    def test_output_filter_removes_keyword():
        engine = ModerationEngineDynamicAC(_make_config(["badword"], "filter"))
        is_int, text = engine.clean_full_text("hello badword world")
        assert is_int is False
        assert "badword" not in text
        assert "hello" in text
        assert "world" in text

    @staticmethod
    def test_output_replace_replaces_keyword():
        engine = ModerationEngineDynamicAC(_make_config(["badword"], "replace", "***"))
        is_int, text = engine.clean_full_text("hello badword world")
        assert is_int is False
        assert text == "hello *** world"

    @staticmethod
    def test_output_reply_blocks_and_returns_fallback():
        engine = ModerationEngineDynamicAC(_make_config(["badword"], "reply", "请更换内容"))
        is_int, text = engine.clean_full_text("hello badword world")
        assert is_int is True
        assert text == "请更换内容"

    @staticmethod
    def test_input_reply_blocks_query():
        engine = ModerationEngineDynamicAC(_make_config(["badword"], "reply", "不允许", "input"))
        is_safe, result = engine.check_input_query("this is badword here")
        assert is_safe is False
        assert result == "不允许"

    @staticmethod
    def test_input_filter_does_not_block():
        """Input FILTER only blocks on REPLY — filter/replace are output-side actions."""
        engine = ModerationEngineDynamicAC(_make_config(["badword"], "filter", "", "input"))
        is_safe, result = engine.check_input_query("this is badword here")
        assert is_safe is True

    @staticmethod
    def test_multiple_keywords_all_matched():
        engine = ModerationEngineDynamicAC(_make_config(["bad1", "bad2"], "replace", "***"))
        is_int, text = engine.clean_full_text("bad1 and bad2")
        assert is_int is False
        assert "bad1" not in text
        assert "bad2" not in text

    @staticmethod
    def test_max_kw_len_set():
        engine = ModerationEngineDynamicAC(_make_config(["short", "verylongkeyword"], "filter"))
        assert engine.max_kw_len == len("verylongkeyword")

    @staticmethod
    def test_build_sensitive_event():
        event = ModerationEngineDynamicAC.build_sensitive_event("fallback", 1000)
        assert event["event"] == "sensitive"
        assert event["data"]["text"] == "fallback"
        assert event["createdTime"] == 1000

    @staticmethod
    def test_build_sensitive_event_without_timestamp():
        event = ModerationEngineDynamicAC.build_sensitive_event("fallback")
        assert event["event"] == "sensitive"
        assert event["data"]["text"] == "fallback"
        assert isinstance(event["createdTime"], int)

    @staticmethod
    def test_build_sensitive_event_with_node_context():
        """sensitive 事件应携带 node_id/index 等上下文，node_type 自动映射。"""
        event = ModerationEngineDynamicAC.build_sensitive_event(
            "blocked",
            1000,
            node_id="node_end",
            node_type="jiuwen.end",
            node_name="结束",
            index=6,
        )
        assert event["event"] == "sensitive"
        assert event["data"]["text"] == "blocked"
        assert event["data"]["node_id"] == "node_end"
        assert event["data"]["node_type"] == "End"  # jiuwen.end → End
        assert event["data"]["node_name"] == "结束"
        assert event["data"]["index"] == 6
        assert event["data"]["offset"] == 0

    @staticmethod
    def test_build_sensitive_event_no_node_context():
        """无节点上下文时不生成 node_id/node_type 字段。"""
        event = ModerationEngineDynamicAC.build_sensitive_event("fallback", 1000)
        assert "node_id" not in event["data"]
        assert "node_type" not in event["data"]
        assert "node_name" not in event["data"]
        assert "index" not in event["data"]

    @staticmethod
    def test_empty_keyword_is_ignored():
        engine = ModerationEngineDynamicAC(_make_config(["", "badword"], "filter"))
        is_int, text = engine.clean_full_text("badword")
        assert is_int is False
        assert "badword" not in text

    @staticmethod
    def test_reply_priority_over_replace():
        """When same keyword has both reply and replace rules, reply wins."""
        config = {
            "enabled": True,
            "rules": [
                {"keywords": ["bad"], "actions": {"output": {"enable": True, "type": "replace", "content": "***"}}},
                {"keywords": ["bad"], "actions": {"output": {"enable": True, "type": "reply", "content": "blocked"}}},
            ],
        }
        engine = ModerationEngineDynamicAC(config)
        is_int, text = engine.clean_full_text("bad")
        assert is_int is True
        assert text == "blocked"
