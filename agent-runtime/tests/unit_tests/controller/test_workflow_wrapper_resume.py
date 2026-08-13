# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for workflow_wrapper.py — _extract_resume_query 恢复模式输入提取 (commit cf93abd)。

修复前: 恢复模式(is_resuming=True)下不追加用户查询到对话历史，导致 LLM 上下文不完整
修复后: 新增 _extract_resume_query 方法，从 InteractiveInput 中提取用户最新回复并追加
"""
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_COMMON_UTILS = os.path.join(_REPO_ROOT, "packages", "common_utils")
if os.path.isdir(_COMMON_UTILS) and _COMMON_UTILS not in sys.path:
    sys.path.insert(0, _COMMON_UTILS)

from openjiuwen.core.session.interaction.interactive_input import InteractiveInput

from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper


def _make_wrapper():
    """创建 WorkflowWrapper 实例，绕过构造器外部依赖。"""
    obj = WorkflowWrapper.__new__(WorkflowWrapper)
    return obj


class TestExtractResumeQuery:
    """_extract_resume_query — 从 InteractiveInput 或字符串中提取恢复时的用户回复。"""

    @staticmethod
    def test_extract_from_raw_inputs():
        """InteractiveInput 有 raw_inputs 时，应返回 raw_inputs 的字符串。"""
        wrapper = _make_wrapper()
        query = InteractiveInput()
        query.raw_inputs = "user_resume_reply"

        result = wrapper._extract_resume_query(query)

        assert result == "user_resume_reply"

    @staticmethod
    def test_extract_from_user_inputs_when_raw_empty():
        """raw_inputs 为空时，应从 user_inputs 取最后一个值。"""
        wrapper = _make_wrapper()
        query = InteractiveInput()
        query.raw_inputs = None
        query.user_inputs = {"field1": "first", "field2": "second"}

        result = wrapper._extract_resume_query(query)

        assert result == "second"

    @staticmethod
    def test_raw_inputs_takes_priority():
        """raw_inputs 和 user_inputs 都有值时，应优先取 raw_inputs。"""
        wrapper = _make_wrapper()
        query = InteractiveInput()
        query.raw_inputs = "from_raw"
        query.user_inputs = {"key": "from_user"}

        result = wrapper._extract_resume_query(query)

        assert result == "from_raw"

    @staticmethod
    def test_string_query_returns_as_is():
        """传入普通字符串时，应直接返回该字符串。"""
        wrapper = _make_wrapper()

        assert wrapper._extract_resume_query("hello world") == "hello world"

    @staticmethod
    def test_empty_string_query_returns_empty():
        """传入空字符串时，应返回空字符串。"""
        wrapper = _make_wrapper()

        assert wrapper._extract_resume_query("") == ""

    @staticmethod
    def test_none_query_returns_empty():
        """传入 None 时，应返回空字符串。"""
        wrapper = _make_wrapper()

        assert wrapper._extract_resume_query(None) == ""

    @staticmethod
    def test_empty_interactive_input_returns_repr():
        """InteractiveInput 无任何输入时，raw_inputs 和 user_inputs 均为空，
        回退到 str(query) 返回对象字符串表示。"""
        wrapper = _make_wrapper()
        query = InteractiveInput()

        result = wrapper._extract_resume_query(query)

        # raw_inputs=None, user_inputs={} 均为 falsy，回退到 str(query)
        assert "user_inputs" in result

    @staticmethod
    def test_user_inputs_with_numeric_value():
        """user_inputs 值为数字时，应转为字符串返回。"""
        wrapper = _make_wrapper()
        query = InteractiveInput()
        query.raw_inputs = None
        query.user_inputs = {"count": 99}

        result = wrapper._extract_resume_query(query)

        assert result == "99"
