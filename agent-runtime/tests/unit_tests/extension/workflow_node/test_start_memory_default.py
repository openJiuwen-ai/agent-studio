# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Start 节点记忆变量默认值提取与类型转换测试。

背景(2026-09-03 bug 修复):_extract_assignment_values 曾按 schema 存在性分支,
数组/对象类型记忆变量的 default_value 被整个丢弃;_transform_type 的
boolean/number/array 转换分别存在 "false" 反转、tuple 不可调用、
list() 拆字符问题。

2026-09-10 检视意见修复(方案 D):空默认统一为 key 保留 + 值 None ——
values_define 的成员资格是 Redis 会话变量存取与 SetVariable 持久化的
门控依据,key 缺失会导致跨轮丢值(空默认 array 的 SetVariable 赋值
跨轮丢失已在本地实测复现);渲染层引用解析对 None 与 key 缺失等价。
同时:嵌套 object 自身 default_value 优先(检视意见1)、schema 为
None/非 list 容错不再抛 TypeError(检视意见3)、空容器 '[]'/'{}'
归一为空默认(检视意见4)。
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
        """七种类型声明:非空默认全部提取,子字段不泄漏到顶层,空默认为 None。"""
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
        # 空默认归一为 None(key 保留在 values_define 注册表,
        # 门控 Redis 存取与 SetVariable 持久化;渲染层 None ≡ key 缺失)
        assert result["v_arr_empty"] is None
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
    def test_object_all_children_empty_defaults_none():
        """object 子字段全空:整体值为 None,key 保留(不写入空 dict)。"""
        fields = [
            _var(
                "v_obj",
                "object",
                "",
                schema=[_var("a", "string", "")],
            )
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["v_obj"] is None

    @staticmethod
    def test_empty_container_defaults_normalized_to_none():
        """空容器默认('[]'/'{}' 及各空写法)归一为 None,key 保留(检视意见4)。"""
        fields = [
            _var("a1", "array", "[]", schema={"id": "", "type": "string"}),
            _var("a2", "array", [], schema={"id": "", "type": "string"}),
            _var("a3", "array", " [ ] ", schema={"id": "", "type": "string"}),
            _var("a4", "array", "", schema={"id": "", "type": "string"}),
            _var("o1", "object", "{}", schema=[_var("x", "string", "xv")]),
            _var("o2", "object", "{\n}"),
            _var("o3", "object", "{}"),
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["a1"] is None
        assert result["a2"] is None
        assert result["a3"] is None
        assert result["a4"] is None
        # '{}' 视为无整体默认,回落子字段组装
        assert result["o1"] == {"x": "xv"}
        assert result["o2"] is None
        assert result["o3"] is None

    @staticmethod
    def test_falsy_defaults_still_extracted():
        """0/False 是合法默认值,空默认归一不许误伤 falsy 默认。"""
        fields = [
            _var("v_zero", "integer", "0"),
            _var("v_zero_num", "number", "0"),
            _var("v_false", "boolean", "false"),
        ]

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["v_zero"] == 0
        assert result["v_zero_num"] == 0
        assert result["v_false"] is False

    @staticmethod
    def test_object_schema_null_or_malformed_tolerated():
        """schema 为 null/非 list 容错为无子字段,不再抛 TypeError(检视意见3)。"""
        fields = [
            _var("v1", "object", ""),
            _var("v2", "object", ""),
        ]
        fields[0]["schema"] = None
        fields[1]["schema"] = {"id": "x", "type": "string"}

        result = Start._extract_assignment_values(_memory_inputs(*fields), "session")

        assert result["v1"] is None
        assert result["v2"] is None

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

    @staticmethod
    def test_nested_object_own_default_wins():
        """嵌套 object 自带默认优先(对齐顶层语义),空默认才从子字段组装(检视意见1)。"""
        subfields = [
            _var("obj_no_children", "object", '{"x": 1}'),
            _var(
                "obj_with_children",
                "object",
                '{"y": 2}',
                schema=[_var("z", "string", "zv")],
            ),
            _var(
                "obj_empty_default",
                "object",
                "",
                schema=[_var("w", "string", "wv")],
            ),
        ]

        assembled = Start._assemble_object_default(subfields)

        # 自带默认胜出:子字段不参与;空 schema 也不丢
        assert assembled["obj_no_children"] == {"x": 1}
        assert assembled["obj_with_children"] == {"y": 2}
        # 空默认才回落子字段组装
        assert assembled["obj_empty_default"] == {"w": "wv"}

    @staticmethod
    def test_nested_object_empty_default_no_children_skipped():
        """嵌套 object 空默认且无子字段:组装结果跳过该子字段(不为 None)。"""
        subfields = [_var("obj", "object", "")]

        assembled = Start._assemble_object_default(subfields)

        assert assembled == {}

    @staticmethod
    def test_nested_empty_container_skipped_and_falsy_preserved():
        """嵌套子字段空容器默认('[]')跳过;0/False 正常提取。"""
        subfields = [
            _var("arr_empty", "array", "[]", schema={"id": "", "type": "string"}),
            _var("n_zero", "integer", "0"),
            _var("b_false", "boolean", "false"),
        ]

        assembled = Start._assemble_object_default(subfields)

        assert assembled == {"n_zero": 0, "b_false": False}

    @staticmethod
    def test_schema_none_or_non_list_returns_empty():
        """schema 为 None/非 list 容错为空,不再抛 TypeError(检视意见3)。"""
        assert Start._assemble_object_default(None) == {}
        assert Start._assemble_object_default({"id": "x", "type": "string"}) == {}
        assert Start._assemble_object_default(5) == {}
