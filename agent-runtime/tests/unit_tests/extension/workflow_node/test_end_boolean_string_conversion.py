# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for End 节点 _convert_simple 的 boolean 字符串转换。

背景 bug：End 节点按 userFields.inputs schema 做类型强转时，boolean 字段使用
裸 ``bool()``，任意非空字符串（包括 "false"）都被转成 True。Start 节点的
``_to_boolean``（start.py）已修复过同一问题——前端默认值输入框是纯文本，
'false' 字符串必须解析为 False。End 应与 Start 行为对齐。
"""

from jiuwen.extension.workflow_node.end import End


def _convert_simple(value, type_name):
    return getattr(End, "_convert_simple")(value, type_name)


class TestBooleanStringConversion:
    """boolean 类型收到字符串时按 Start._to_boolean 语义解析。"""

    @staticmethod
    def test_false_string_converts_to_false():
        assert _convert_simple("false", "boolean") is False

    @staticmethod
    def test_true_string_converts_to_true():
        assert _convert_simple("true", "boolean") is True

    @staticmethod
    def test_boolean_string_is_case_and_space_insensitive():
        assert _convert_simple(" True ", "boolean") is True
        assert _convert_simple("FALSE", "boolean") is False

    @staticmethod
    def test_bool_values_pass_through():
        assert _convert_simple(True, "boolean") is True
        assert _convert_simple(False, "boolean") is False

    @staticmethod
    def test_non_boolean_garbage_string_converts_to_false():
        # 与 Start._to_boolean 一致：仅字面 "true"（忽略大小写/空白）为 True
        assert _convert_simple("abc", "boolean") is False


class TestOtherTypesRegression:
    """其余类型强转行为不受影响。"""

    @staticmethod
    def test_integer_string_converts():
        assert _convert_simple("42", "integer") == 42

    @staticmethod
    def test_number_string_converts():
        assert _convert_simple("3.5", "number") == 3.5

    @staticmethod
    def test_none_returns_type_default():
        assert _convert_simple(None, "boolean") is None
        assert _convert_simple(None, "string") == ""

    @staticmethod
    def test_string_passthrough():
        assert _convert_simple("hello", "string") == "hello"
