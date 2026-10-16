# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""convert_user_field_default — Start 用户字段默认值注入归一测试。

背景(2026-09-14 bug 修复):328d4923(fix:end节点未输出空字符串)把 Start
userFields.inputs 的 default_value 原样注入 _request,object/array 等非 string
字段的空默认 '' 让 Start 输出过不了 openjiuwen IR 输出校验
(json.loads('')/int('') 失败,报 Incorrect type for key)。

修复(需求确认):所有类型字段都注入默认值,注入前按声明类型归一——
空默认(None/'')转合法类型值,避免 '' 触发 IR 输出校验失败。

本文件锁定 convert_user_field_default 的归一语义:
    string            -> 默认值(缺失/null 归一为空串 '')
    object/array/int/... 空默认 -> {} / [] / 0 / 0.0 / False
    object/array 非空 JSON 字符串 -> 解析为 dict / list
"""
# pylint: disable=protected-access

import pytest

from jiuwen.extension.workflow_node.start import Start


class TestConvertUserFieldDefault:
    """convert_user_field_default — 全部类型注入,空默认归一为类型合法值。"""

    @pytest.mark.parametrize(
        ("data_type", "default_value", "expected"),
        [
            # string:空默认注入空串;非空默认原样注入;null/缺失归一为空串
            ("string", "", ""),
            ("string", None, ""),
            ("string", "张三", "张三"),
            ("string", 0, 0),  # 数值默认值不强制转 str,原样注入
            # object:空默认 -> {};非空 JSON 字符串解析为 dict
            ("object", "", {}),
            ("object", None, {}),
            ("object", "{}", {}),
            ("object", '{"a": 1}', {"a": 1}),
            # array:空默认 -> [];非空 JSON 字符串解析为 list
            ("array", "", []),
            ("array", None, []),
            ("array", '["a", 1]', ["a", 1]),
            # integer:空默认 -> 0;非空字符串转 int
            ("integer", "", 0),
            ("integer", "30", 30),
            ("integer", 0, 0),
            # number:空默认 -> 0.0;非空字符串转 float
            ("number", "", 0.0),
            ("number", "3.14", 3.14),
            # boolean:空默认 -> False;'false'/'true' 转 bool
            ("boolean", "", False),
            ("boolean", "false", False),
            ("boolean", "true", True),
            ("boolean", False, False),
            # 未知类型:非空原样注入,空默认归一为空串
            ("", "raw", "raw"),
            ("unknown", "raw", "raw"),
            ("", "", ""),
        ],
        ids=[
            "string_empty",
            "string_null",
            "string_value",
            "string_numeric_literal",
            "object_empty",
            "object_null",
            "object_empty_json",
            "object_json",
            "array_empty",
            "array_null",
            "array_json",
            "integer_empty",
            "integer_value",
            "integer_zero_literal",
            "number_empty",
            "number_value",
            "boolean_empty",
            "boolean_false_str",
            "boolean_true_str",
            "boolean_false_literal",
            "no_type_value",
            "unknown_type_value",
            "no_type_empty",
        ],
    )
    def test_normalize(self, data_type, default_value, expected):
        assert Start.convert_user_field_default(data_type, default_value) == expected

    @staticmethod
    def test_object_empty_with_schema_fills_subfields():
        """object 空默认带 schema → 按 schema 递归填充子字段空值。"""
        schema = [
            {"id": "id", "type": "string"},
            {"id": "ot", "type": "string"},
        ]
        assert Start.convert_user_field_default("object", "", schema) == {
            "id": "",
            "ot": "",
        }

    @staticmethod
    def test_object_empty_json_with_schema_fills_subfields():
        """object 空对象默认('{}')带 schema → 同样填充子字段(对齐节点输出转换)。"""
        schema = [{"id": "id", "type": "string"}]
        assert Start.convert_user_field_default("object", "{}", schema) == {"id": ""}

    @staticmethod
    def test_object_nonempty_with_schema_keeps_value():
        """object 非空默认带 schema → 保留原值,不强制补全缺失子字段。"""
        schema = [{"id": "id", "type": "string"}]
        assert Start.convert_user_field_default("object", '{"a": 1}', schema) == {"a": 1}

    @staticmethod
    def test_object_empty_without_schema_returns_empty_dict():
        """object 空默认无 schema → 回退空 dict。"""
        assert Start.convert_user_field_default("object", "", None) == {}
        assert Start.convert_user_field_default("object", "", []) == {}

    @staticmethod
    def test_object_nested_schema_fills_recursively():
        """嵌套 object 子字段递归填充;array 子字段为空 list。"""
        schema = [
            {"id": "meta", "type": "object", "schema": [{"id": "tag", "type": "string"}]},
            {"id": "tags", "type": "array", "schema": {"type": "string"}},
            {"id": "cnt", "type": "integer"},
        ]
        assert Start.convert_user_field_default("object", "", schema) == {
            "meta": {"tag": ""},
            "tags": [],
            "cnt": 0,
        }