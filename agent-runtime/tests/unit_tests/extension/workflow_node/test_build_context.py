# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access  # 单元测试需直接验证内部方法行为
"""OpenJiuWenWorkflowInstanceLayer._build_context 的单元测试。

覆盖缺陷①修复：
  1. 当轮 query 追加到历史末尾（带去重）
  2. 历史消息清理（去掉 intent 等多余字段后 converter 不报错）
  3. SessionModelContext 构造参数修复（history_messages=[] / processors=[]）
"""
from unittest.mock import MagicMock, patch

from jiuwen.extension.wrapper.workflow_instance_layer import (
    OpenJiuWenWorkflowInstanceLayer,
)


def _make_layer():
    """创建测试用 WorkflowInstanceLayer 实例。"""
    return OpenJiuWenWorkflowInstanceLayer(
        workflow_id="wf-test",
        workflow_name="test_workflow",
    )


class TestBuildContextQueryAppend:
    """_build_context 应将当轮 query 追加到历史末尾（带去重）。"""

    @staticmethod
    def test_append_query_to_history():
        """当轮 query 不在历史中时，应追加到末尾。"""
        layer = _make_layer()
        params = {
            "conversation_history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "您好，有什么可以帮您？"},
            ],
            "_current_query": "查询电费账单",
        }

        with patch(
            "jiuwen.extension.wrapper.workflow_instance_layer.WorkflowMessageConverter"
        ) as mock_converter:
            layer._build_context(params, None)

        call_args = mock_converter.conversation_messages_to_model_context.call_args
        clean_histories = call_args[0][0]
        assert len(clean_histories) == 3
        assert clean_histories[-1] == {"role": "user", "content": "查询电费账单"}

    @staticmethod
    def test_no_duplicate_append():
        """历史末条 user 消息已等于当轮 query 时，不重复追加。"""
        layer = _make_layer()
        params = {
            "conversation_history": [
                {"role": "user", "content": "查询电费账单"},
                {"role": "assistant", "content": "请提供户号"},
                {"role": "user", "content": "户号100023"},
            ],
            "_current_query": "户号100023",
        }

        with patch(
            "jiuwen.extension.wrapper.workflow_instance_layer.WorkflowMessageConverter"
        ) as mock_converter:
            layer._build_context(params, None)

        call_args = mock_converter.conversation_messages_to_model_context.call_args
        clean_histories = call_args[0][0]
        # 不应重复追加，长度仍为 3
        assert len(clean_histories) == 3

    @staticmethod
    def test_append_when_last_user_differs():
        """历史末条 user 消息与当轮 query 不同时，应追加。"""
        layer = _make_layer()
        params = {
            "conversation_history": [
                {"role": "user", "content": "查询电费账单"},
                {"role": "assistant", "content": "请提供户号"},
            ],
            "_current_query": "户号100023",
        }

        with patch(
            "jiuwen.extension.wrapper.workflow_instance_layer.WorkflowMessageConverter"
        ) as mock_converter:
            layer._build_context(params, None)

        call_args = mock_converter.conversation_messages_to_model_context.call_args
        clean_histories = call_args[0][0]
        assert len(clean_histories) == 3
        assert clean_histories[-1] == {"role": "user", "content": "户号100023"}

    @staticmethod
    def test_no_append_when_query_empty():
        """当轮 query 为空时，不追加。"""
        layer = _make_layer()
        params = {
            "conversation_history": [
                {"role": "user", "content": "你好"},
            ],
            "_current_query": "",
        }

        with patch(
            "jiuwen.extension.wrapper.workflow_instance_layer.WorkflowMessageConverter"
        ) as mock_converter:
            layer._build_context(params, None)

        call_args = mock_converter.conversation_messages_to_model_context.call_args
        clean_histories = call_args[0][0]
        assert len(clean_histories) == 1


class TestBuildContextMessageCleaning:
    """_build_context 应清理历史消息的多余字段后再传给 converter。"""

    @staticmethod
    def test_strip_extra_fields():
        """intent/agent_id 等多余字段应被去除，但 enable_history 和 name 应保留。"""
        layer = _make_layer()
        params = {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "查询电费账单",
                    "intent": ["dianfeizhangdanchaxungongzuoliu"],
                    "enable_history": False,
                    "name": "testUser",
                    "agent_id": "468c8dd2-xxxx",
                    "files": None,
                    "tool_call_id": None,
                    "tool_calls": None,
                    "function_call": None,
                },
            ],
        }

        with patch(
            "jiuwen.extension.wrapper.workflow_instance_layer.WorkflowMessageConverter"
        ) as mock_converter:
            layer._build_context(params, None)

        call_args = mock_converter.conversation_messages_to_model_context.call_args
        clean_histories = call_args[0][0]
        assert len(clean_histories) == 1
        msg = clean_histories[0]
        # role + content 保留
        assert msg["role"] == "user"
        assert msg["content"] == "查询电费账单"
        # enable_history 和 name 保留（converter._extract_msg_fields 会读取）
        assert msg["enable_history"] is False
        assert msg["name"] == "testUser"
        # 其余多余字段去除
        assert "intent" not in msg
        assert "agent_id" not in msg
        assert "files" not in msg

    @staticmethod
    def test_non_dict_messages_preserved():
        """非 dict 类型的消息（如 BaseMessage 对象）应原样保留。"""
        layer = _make_layer()
        mock_message = MagicMock()  # 模拟 BaseMessage 对象
        params = {
            "conversation_history": [mock_message],
        }

        with patch(
            "jiuwen.extension.wrapper.workflow_instance_layer.WorkflowMessageConverter"
        ) as mock_converter:
            layer._build_context(params, None)

        call_args = mock_converter.conversation_messages_to_model_context.call_args
        clean_histories = call_args[0][0]
        assert len(clean_histories) == 1
        assert clean_histories[0] is mock_message


class TestBuildContextSessionModelContext:
    """_build_context 应正确构造 SessionModelContext（不触发默认 None 异常）。"""

    @staticmethod
    def test_returns_session_model_context():
        """有历史消息时应返回 SessionModelContext 实例。"""
        layer = _make_layer()
        params = {
            "conversation_history": [
                {"role": "user", "content": "你好"},
            ],
        }

        result = layer._build_context(params, None)

        # 不应返回 None（修复前的 bug：SessionModelContext 构造失败静默返回 None）
        assert result is not None
        assert result is not layer._context

    @staticmethod
    def test_empty_history_returns_fallback():
        """无历史消息时应返回 self._context（fallback）。"""
        layer = _make_layer()
        params = {}

        result = layer._build_context(params, None)

        assert result is layer._context

    @staticmethod
    def test_no_mutation_of_original_histories():
        """追加 query 时不应修改原始 histories 列表（浅拷贝）。"""
        layer = _make_layer()
        original_histories = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好"},
        ]
        params = {
            "conversation_history": original_histories,
            "_current_query": "查询电费账单",
        }

        with patch(
            "jiuwen.extension.wrapper.workflow_instance_layer.WorkflowMessageConverter"
        ):
            layer._build_context(params, None)

        # 原始列表不应被修改（仍是 2 条）
        assert len(original_histories) == 2


class TestBuildContextPassthrough:
    """_build_context 传入 context 非 None 时仍应追加 _current_query。"""

    @staticmethod
    def test_existing_context_gets_query_appended():
        """传入预构建 context 时，_current_query 应追加到 context 历史中。"""
        layer = _make_layer()
        mock_context = MagicMock()
        params = {"_current_query": "户号100023"}

        result = layer._build_context(params, mock_context)

        # 应返回传入的 context（不创建新的）
        assert result is mock_context
        # 应调用 add_messages 追加当轮 query
        mock_context.add_messages.assert_called_once()
        added_messages = mock_context.add_messages.call_args[0][0]
        assert len(added_messages) == 1
        assert added_messages[0].content == "户号100023"

    @staticmethod
    def test_existing_context_no_query_no_append():
        """传入预构建 context 但无 _current_query 时，不应调用 add_messages。"""
        layer = _make_layer()
        mock_context = MagicMock()
        params = {}

        result = layer._build_context(params, mock_context)

        assert result is mock_context
        mock_context.add_messages.assert_not_called()
