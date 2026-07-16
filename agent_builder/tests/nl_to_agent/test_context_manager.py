#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""ContextManager 单元测试"""

from datetime import datetime, timezone

import pytest
from agent_builder.nl_to_agent.agent_creator.context_manager import (
    ContextManager,
    DialogueHistoryCache,
    DialogueMessage,
)


def _make_message(**kwargs):
    defaults = {
        "content": "hello",
        "role": "user",
        "name": "test",
        "timestamp": None,
        "intent_label": None,
        "function_call": None,
    }
    defaults.update(kwargs)
    if defaults["timestamp"] is None:
        defaults["timestamp"] = datetime.now(tz=timezone.utc)
    return DialogueMessage(**defaults)


class TestDialogueMessage:
    """DialogueMessage 数据类测试"""

    @staticmethod
    def test_creation_with_fields():
        """创建包含所有字段的消息"""
        ts = datetime.now(tz=timezone.utc)
        msg = DialogueMessage(
            content="hello",
            role="user",
            name="test_user",
            timestamp=ts,
            intent_label="greeting",
            function_call={"name": "func1"},
        )
        assert msg.content == "hello"
        assert msg.role == "user"
        assert msg.name == "test_user"
        assert msg.timestamp == ts
        assert msg.intent_label == "greeting"
        assert msg.function_call == {"name": "func1"}

    @staticmethod
    def test_default_none_for_optional_fields():
        """可选字段默认为 None"""
        ts = datetime.now(tz=timezone.utc)
        msg = DialogueMessage(
            content="hello", role="user", name="test", timestamp=ts
        )
        assert msg.intent_label is None
        assert msg.function_call is None


class TestDialogueHistoryCache:
    """DialogueHistoryCache 类测试"""

    @staticmethod
    def test_add_message():
        """添加消息到会话"""
        cache = DialogueHistoryCache()
        msg = _make_message(content="hello")
        cache.add_message("session1", msg)
        history = cache.get_history("session1")
        assert len(history) == 1
        assert history[0].content == "hello"

    @staticmethod
    def test_get_history_empty_session():
        """获取不存在会话的历史返回空列表"""
        cache = DialogueHistoryCache()
        history = cache.get_history("nonexistent")
        assert history == []

    @staticmethod
    def test_get_latest_k_messages():
        """获取最近 k 条消息"""
        cache = DialogueHistoryCache()
        for i in range(5):
            cache.add_message("s1", _make_message(content=f"msg{i}"))
        result = cache.get_latest_k_messages("s1", 3)
        assert len(result) == 3
        assert result[0]["content"] == "msg2"
        assert result[1]["content"] == "msg3"
        assert result[2]["content"] == "msg4"

    @staticmethod
    def test_get_latest_k_messages_with_function_call():
        """包含 function_call 的消息在格式化输出中保留"""
        cache = DialogueHistoryCache()
        msg = _make_message(content="call", function_call={"name": "tool1"})
        cache.add_message("s1", msg)
        result = cache.get_latest_k_messages("s1", 1)
        assert "function_call" in result[0]

    @staticmethod
    def test_get_latest_k_messages_nonexistent_session():
        """获取不存在会话的最近消息返回空列表"""
        cache = DialogueHistoryCache()
        result = cache.get_latest_k_messages("nonexistent", 5)
        assert result == []

    @staticmethod
    def test_clear_session():
        """清除会话历史"""
        cache = DialogueHistoryCache()
        cache.add_message("s1", _make_message())
        result = cache.clear_session("s1")
        assert result is True
        assert cache.get_history("s1") == []

    @staticmethod
    def test_clear_nonexistent_session():
        """清除不存在的会话返回 False"""
        cache = DialogueHistoryCache()
        result = cache.clear_session("nonexistent")
        assert result is False

    @staticmethod
    def test_max_history_per_session_overflow():
        """超过最大容量时移除最早的消息"""
        cache = DialogueHistoryCache(max_history_per_session=3)
        for i in range(5):
            cache.add_message("s1", _make_message(content=f"msg{i}"))
        history = cache.get_history("s1")
        assert len(history) == 3
        assert history[0].content == "msg2"
        assert history[1].content == "msg3"
        assert history[2].content == "msg4"

    @staticmethod
    def test_set_and_get_latest_query():
        """设置和获取最新查询"""
        cache = DialogueHistoryCache()
        cache.set_latest_query("s1", "query1")
        assert cache.get_latest_query("s1") == "query1"

    @staticmethod
    def test_get_latest_query_nonexistent():
        """获取不存在会话的最新查询返回 None"""
        cache = DialogueHistoryCache()
        assert cache.get_latest_query("nonexistent") is None


class TestContextManager:
    """ContextManager 类测试"""

    @staticmethod
    def test_add_message():
        """添加消息到对话历史"""
        cm = ContextManager()
        cm.add_message("s1", "hello", "user", name="test")
        history = cm.get_dialogue_history("s1")
        assert len(history) == 1
        assert history[0].content == "hello"

    @staticmethod
    def test_add_user_message():
        """添加用户消息"""
        cm = ContextManager()
        cm.add_user_message("s1", "user input")
        history = cm.get_dialogue_history("s1")
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "user input"

    @staticmethod
    def test_add_assistant_message():
        """添加助手消息"""
        cm = ContextManager()
        cm.add_assistant_message("s1", "assistant reply", intent="answer")
        history = cm.get_dialogue_history("s1")
        assert len(history) == 1
        assert history[0].role == "assistant"
        assert history[0].intent_label == "answer"

    @staticmethod
    def test_get_formatted_history():
        """获取格式化的对话历史"""
        cm = ContextManager()
        cm.add_user_message("s1", "你好")
        cm.add_assistant_message("s1", "你好，有什么可以帮助你？", intent="greeting")
        formatted = cm.get_formatted_history("s1")
        assert "用户: 你好" in formatted
        assert "助手: 你好，有什么可以帮助你？" in formatted

    @staticmethod
    def test_get_formatted_history_with_intent_filter():
        """按意图过滤格式化历史"""
        cm = ContextManager()
        cm.add_user_message("s1", "hello", intent_label="chat")
        cm.add_assistant_message("s1", "hi", intent="chat")
        cm.add_user_message("s1", "build agent", intent_label="build")
        formatted = cm.get_formatted_history("s1", intent="chat")
        assert "hello" in formatted
        assert "hi" in formatted
        assert "build agent" not in formatted

    @staticmethod
    def test_get_formatted_history_empty_session():
        """获取不存在会话的格式化历史返回空字符串"""
        cm = ContextManager()
        formatted = cm.get_formatted_history("nonexistent")
        assert formatted == ""

    @staticmethod
    def test_get_filtered_messages():
        """获取过滤后的消息列表"""
        cm = ContextManager()
        cm.add_user_message("s1", "msg1", intent_label="a")
        cm.add_user_message("s1", "msg2", intent_label="b")
        result = cm.get_filtered_messages("s1", intent="a")
        assert len(result) == 1
        assert result[0]["content"] == "msg1"

    @staticmethod
    def test_get_filtered_messages_no_filter():
        """不指定意图时返回所有消息"""
        cm = ContextManager()
        cm.add_user_message("s1", "msg1")
        cm.add_user_message("s1", "msg2")
        result = cm.get_filtered_messages("s1")
        assert len(result) == 2

    @staticmethod
    def test_get_filtered_messages_empty_session():
        """获取不存在会话的过滤消息返回空列表"""
        cm = ContextManager()
        result = cm.get_filtered_messages("nonexistent")
        assert result == []

    @staticmethod
    def test_update_latest_message_intent():
        """更新最后一条消息的意图标签"""
        cm = ContextManager()
        cm.add_user_message("s1", "hello")
        result = cm.update_latest_message_intent("s1", "greeting")
        assert result is True
        history = cm.get_dialogue_history("s1")
        assert history[-1].intent_label == "greeting"

    @staticmethod
    def test_update_latest_message_intent_nonexistent_session():
        """更新不存在会话的意图返回 False"""
        cm = ContextManager()
        result = cm.update_latest_message_intent("nonexistent", "intent")
        assert result is False

    @staticmethod
    def test_clear_dialogue():
        """清除对话历史"""
        cm = ContextManager()
        cm.add_user_message("s1", "hello")
        cm.clear_dialogue("s1")
        history = cm.get_dialogue_history("s1")
        assert len(history) == 0

    @staticmethod
    def test_get_latest_k_chat_history():
        """获取最近 k 条对话历史"""
        cm = ContextManager()
        for i in range(5):
            cm.add_user_message("s1", f"msg{i}")
        result = cm.get_latest_k_chat_history("s1", 3)
        assert len(result) == 3
        assert result[0]["content"] == "msg2"
        assert result[2]["content"] == "msg4"

    @staticmethod
    def test_get_non_function_messages():
        """获取非 function 角色且不包含 function_call 的消息"""
        cm = ContextManager()
        cm.add_user_message("s1", "user msg")
        cm.add_assistant_message("s1", "assistant msg", intent="reply")
        func_msg = _make_message(
            content="func call", role="function", function_call={"name": "tool"}
        )
        cm.dialogue_history.add_message("s1", func_msg)
        result = cm.get_non_function_messages("s1")
        assert len(result) == 2
        contents = [m["content"] for m in result]
        assert "user msg" in contents
        assert "assistant msg" in contents
        assert "func call" not in contents

    @staticmethod
    def test_get_non_function_messages_empty_session():
        """获取不存在会话的非 function 消息返回空列表"""
        cm = ContextManager()
        result = cm.get_non_function_messages("nonexistent")
        assert result == []

    @staticmethod
    def test_set_and_get_latest_query():
        """设置和获取最新查询"""
        cm = ContextManager()
        cm.set_latest_query("s1", "my query")
        assert cm.get_latest_query("s1") == "my query"

    @staticmethod
    def test_multiple_sessions():
        """多个会话独立管理"""
        cm = ContextManager()
        cm.add_user_message("s1", "session1 msg")
        cm.add_user_message("s2", "session2 msg")
        assert len(cm.get_dialogue_history("s1")) == 1
        assert len(cm.get_dialogue_history("s2")) == 1
        assert cm.get_dialogue_history("s1")[0].content == "session1 msg"
        assert cm.get_dialogue_history("s2")[0].content == "session2 msg"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])