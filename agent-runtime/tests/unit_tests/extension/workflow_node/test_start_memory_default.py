# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Start 节点记忆变量默认值提取与类型转换测试。

背景(2026-09-03 bug 修复):_extract_assignment_values 曾按 schema 存在性分支,
数组/对象类型记忆变量的 default_value 被整个丢弃;_transform_type 的
boolean/number/array 转换分别存在 "false" 反转、tuple 不可调用、
list() 拆字符问题。本文件锁定修复后的全类型行为。
"""
# pylint: disable=protected-access

import pytest

from jiuwen.extension.workflow_node.start import Start


def _var(var_id, var_type, default_value, schema=None):
    field = {
        "storage_method": "assignment",
        "aging_level": "session",
        "id": var_id,
        "type": var_type,
        "default_value": default_value,
    }
    if schema is not None:
        field["schema"] = schema
    return field


def _memory_inputs(*fields):
    return [{"schema": list(fields), "id": "memory", "type": "object"}]


class TestExtractAssignmentValues:
    """_extract_assignment_values — 全类型默认值提取。"""

    @staticmethod
    def test_all_types_extracted_no_leak():
        """七种类型声明:非空默认全部提取,子字段不泄漏到顶层,空默认 key 缺失。"""
        fields = [
            _var("v_str", "string", "特色美食"),
            _var("v_int", "integer", "5"),
            _var("v_num", "number", "3.14"),
            _var("v_bool_f", "boolean", "false"),
            _var("v_bool_t", "boolean", "true"),
            _var(
                "v_arr",
                "array",
                '["西安", "洛阳"]',
                schema={"id": "", "type": "string"},
            ),
            _var(
                "v_arr_num",
                "array",
                "[3.14, 1.414]",
                schema={"id": "", "type": "number"},
            ),
            _var(
                "v_arrobj",
                "array",
                '[{"cityname": "南京"}]',
                schema={
                    "id": "",
                    "type": "object",
                    "schema": [
                        {
                            "storage_method": "assignment",
                            "aging_level": "session",
                            "id": "cityname",
                            "type": "string",
                            "default_value": "南京",
                        }
                    ],
                },
            ),
            _var(
                "v_obj",
                "object",
                '{"cityname": "北京", "level": 1}',
                schema=[
                    {
                        "storage_method": "assignment",
                        "aging_level": "session",
                        "id": "cityname",
                        "type": "string",
                        "default_value": "北京",
                    }
                ],
            ),
            _var(
                "v_obj_children",
                "object",
                "",
                schema=[
                    _var("c1", "string", "cv1"),
                    _var("c2", "integer", "2"),
                    _var("c_empty", "string", ""),
                ],
            ),
            _var("v_arr_empty", "array", "", schema={"id": "", "type": "string"}),
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["v_str"] == "特色美食"
        assert result["v_int"] == 5
        assert result["v_num"] == 3.14
        assert result["v_bool_f"] is False
        assert result["v_bool_t"] is True
        assert result["v_arr"] == ["西安", "洛阳"]
        assert result["v_arr_num"] == [3.14, 1.414]
        assert result["v_arrobj"] == [{"cityname": "南京"}]
        assert result["v_obj"] == {"cityname": "北京", "level": 1}
        assert result["v_obj_children"] == {"c1": "cv1", "c2": 2}
        # 空默认保持 key 缺失(渲染为空,与历史行为一致)
        assert "v_arr_empty" not in result
        # 子字段不泄漏到顶层
        assert "cityname" not in result
        assert "c1" not in result
        assert "c_empty" not in result

    @staticmethod
    def test_object_assembled_from_children_skips_empty():
        """object 顶层默认为空时从子字段组装;空默认子字段跳过。"""
        fields = [
            _var(
                "v_obj",
                "object",
                "",
                schema=[
                    _var("a", "string", "va"),
                    _var("b_empty", "string", ""),
                    _var(
                        "nested",
                        "object",
                        "",
                        schema=[_var("deep", "string", "dv")],
                    ),
                ],
            )
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["v_obj"] == {"a": "va", "nested": {"deep": "dv"}}
        assert "b_empty" not in result["v_obj"]

    @staticmethod
    def test_object_all_children_empty_key_absent():
        """object 子字段全空时整体 key 缺失(不写入空 dict)。"""
        fields = [
            _var(
                "v_obj",
                "object",
                "",
                schema=[_var("a", "string", "")],
            )
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert "v_obj" not in result

    @staticmethod
    def test_permanent_aging_level_treated_as_session():
        """permanent 视同 session(既有兼容行为)。"""
        fields = [
            {
                "storage_method": "assignment",
                "aging_level": "permanent",
                "id": "v_perm",
                "type": "string",
                "default_value": "pv",
            }
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["v_perm"] == "pv"

    @staticmethod
    def test_scalar_with_schema_still_extracted():
        """畸形 IR(标量带 schema)按基本类型提取自身 default_value。"""
        fields = [
            _var("v_weird", "string", "wv", schema={"id": "", "type": "string"})
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["v_weird"] == "wv"


class TestTransformType:
    """_transform_type — 类型转换边界。"""

    @pytest.mark.parametrize(
        "data_type,value,expected",
        [
            ("string", "abc", "abc"),
            ("integer", "5", 5),
            ("number", "3", 3),
            ("number", "3.14", 3.14),
            ("boolean", "false", False),
            ("boolean", "true", True),
            ("boolean", "TRUE", True),
            ("boolean", " true ", True),
            ("boolean", "1", False),
            ("boolean", True, True),
            ("boolean", False, False),
            ("array", '["a", "b"]', ["a", "b"]),
            ("array", [1, 2], [1, 2]),
            ("object", '{"a": 1}', {"a": 1}),
            ("object", {"b": 2}, {"b": 2}),
        ],
    )
    def test_conversion(self, data_type, value, expected):
        assert Start._transform_type(data_type, value) == expected

    @pytest.mark.parametrize(
        "data_type,value",
        [
            ("integer", ""),
            ("number", None),
            ("boolean", ""),
            ("array", ""),
        ],
    )
    def test_empty_non_string_returns_none(self, data_type, value):
        assert Start._transform_type(data_type, value) is None

    @staticmethod
    def test_invalid_json_falls_back_to_original():
        assert Start._transform_type("array", "not-json") == "not-json"
        assert Start._transform_type("object", "[1, 2]") == "[1, 2]"
        assert Start._transform_type("number", "abc") == "abc"


class TestAssembleObjectDefault:
    """_assemble_object_default — 子字段组装。"""

    @staticmethod
    def test_nested_object_and_array_children():
        subfields = [
            _var("s", "string", "sv"),
            _var("arr", "array", '["x"]', schema={"id": "", "type": "string"}),
            _var(
                "obj",
                "object",
                "",
                schema=[_var("inner", "boolean", "false")],
            ),
            _var("empty", "string", ""),
        ]

        assembled = Start._assemble_object_default(subfields)

        assert assembled == {
            "s": "sv",
            "arr": ["x"],
            "obj": {"inner": False},
        }
