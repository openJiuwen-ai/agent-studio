# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for sub_workflow.py — _extract_from_interactive_input 兜底提取 (commit cf93abd)。

修复前: _extract_parent_resume_query 三层查找失败后，回退到 Start 节点陈旧 query
修复后: 新增 _extract_from_interactive_input 兜底方法，从 InteractiveInput 中提取用户最新输入
"""
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_COMMON_UTILS = os.path.join(_REPO_ROOT, "packages", "common_utils")
if os.path.isdir(_COMMON_UTILS) and _COMMON_UTILS not in sys.path:
    sys.path.insert(0, _COMMON_UTILS)

from openjiuwen.core.session.interaction.interactive_input import InteractiveInput

from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow


def _make_sub_workflow():
    """创建 SubWorkflow 实例，绕过构造器外部依赖。"""
    obj = SubWorkflow.__new__(SubWorkflow)
    return obj


class TestExtractFromInteractiveInput:
    """_extract_from_interactive_input — 从 InteractiveInput 提取用户最新输入。"""

    @staticmethod
    def test_extract_from_user_inputs():
        """应优先从 user_inputs 中取最新值。"""
        sw = _make_sub_workflow()
        inputs = InteractiveInput()
        inputs.user_inputs = {"field1": "old_value", "field2": "latest_value"}

        result = sw._extract_from_interactive_input(inputs)

        assert result == "latest_value"

    @staticmethod
    def test_extract_from_raw_inputs_when_user_inputs_empty():
        """user_inputs 为空时，应从 raw_inputs 中取。"""
        sw = _make_sub_workflow()
        inputs = InteractiveInput()
        inputs.user_inputs = {}
        inputs.raw_inputs = "raw_user_reply"

        result = sw._extract_from_interactive_input(inputs)

        assert result == "raw_user_reply"

    @staticmethod
    def test_user_inputs_takes_priority_over_raw_inputs():
        """user_inputs 和 raw_inputs 都有值时，应优先取 user_inputs。"""
        sw = _make_sub_workflow()
        inputs = InteractiveInput()
        inputs.user_inputs = {"key1": "from_user_inputs"}
        inputs.raw_inputs = "from_raw_inputs"

        result = sw._extract_from_interactive_input(inputs)

        assert result == "from_user_inputs"

    @staticmethod
    def test_empty_interactive_input_returns_none():
        """user_inputs 和 raw_inputs 均为空时，应返回 None。"""
        sw = _make_sub_workflow()
        inputs = InteractiveInput()

        result = sw._extract_from_interactive_input(inputs)

        assert result is None

    @staticmethod
    def test_non_interactive_input_returns_none():
        """传入非 InteractiveInput 类型时，应返回 None。"""
        sw = _make_sub_workflow()

        assert sw._extract_from_interactive_input("plain string") is None
        assert sw._extract_from_interactive_input(None) is None
        assert sw._extract_from_interactive_input({"key": "val"}) is None

    @staticmethod
    def test_user_inputs_with_falsy_value_falls_back_to_raw():
        """user_inputs 最后一个值为 falsy (空字符串) 时，应回退到 raw_inputs。"""
        sw = _make_sub_workflow()
        inputs = InteractiveInput()
        inputs.user_inputs = {"key1": "valid", "key2": ""}
        inputs.raw_inputs = "fallback_raw"

        result = sw._extract_from_interactive_input(inputs)

        assert result == "fallback_raw"

    @staticmethod
    def test_user_inputs_with_numeric_value():
        """user_inputs 值为数字时，应转为字符串返回。"""
        sw = _make_sub_workflow()
        inputs = InteractiveInput()
        inputs.user_inputs = {"count": 42}

        result = sw._extract_from_interactive_input(inputs)

        assert result == "42"
