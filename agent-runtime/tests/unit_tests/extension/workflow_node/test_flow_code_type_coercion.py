#!/usr/bin/env python
# -*- coding: UTF-8
"""Tests for Code node output type coercion."""

import pytest

from jiuwen.orchestration.flow.constant import INTEGER, TYPE_DEFAULT_VALUE_DICT

from agent_runtime.extension.workflow_node.flow_code import (
    _coerce_value,
    _coerce_outputs,
    _coerce_inputs,
)


class TestCoerceValueString:
    def test_int_to_string(self):
        assert _coerce_value(123, "string") == "123"

    def test_float_to_string(self):
        assert _coerce_value(1.5, "string") == "1.5"

    def test_bool_to_string(self):
        assert _coerce_value(True, "string") == "True"
        assert _coerce_value(False, "string") == "False"

    def test_string_passthrough(self):
        assert _coerce_value("hello", "string") == "hello"

    def test_none_unchanged(self):
        assert _coerce_value(None, "string") is None

    def test_none_input_mode_returns_empty_string(self):
        assert _coerce_value(None, "string", input_mode=True) == ""


class TestCoerceValueInteger:
    def test_string_to_int(self):
        assert _coerce_value("123123123", "integer") == 123123123

    def test_float_to_int(self):
        assert _coerce_value(3.7, "integer") == 3

    def test_int_passthrough(self):
        assert _coerce_value(42, "integer") == 42

    def test_bool_to_int(self):
        assert _coerce_value(True, "integer") == 1
        assert _coerce_value(False, "integer") == 0

    def test_invalid_string_unchanged(self):
        assert _coerce_value("abc", "integer") == "abc"

    def test_none_unchanged(self):
        assert _coerce_value(None, "integer") is None


class TestCoerceValueNumber:
    def test_string_to_float(self):
        assert _coerce_value("3.14", "number") == 3.14

    def test_int_to_float(self):
        assert _coerce_value(42, "number") == 42.0

    def test_float_passthrough(self):
        assert _coerce_value(1.5, "number") == 1.5

    def test_bool_to_float(self):
        assert _coerce_value(True, "number") == 1.0

    def test_invalid_string_unchanged(self):
        assert _coerce_value("abc", "number") == "abc"


class TestCoerceValueBoolean:
    def test_string_true(self):
        assert _coerce_value("true", "boolean") is True
        assert _coerce_value("True", "boolean") is True
        assert _coerce_value("1", "boolean") is True
        assert _coerce_value("yes", "boolean") is True

    def test_string_false(self):
        assert _coerce_value("false", "boolean") is False
        assert _coerce_value("0", "boolean") is False
        assert _coerce_value("no", "boolean") is False

    def test_int_to_bool(self):
        assert _coerce_value(1, "boolean") is True
        assert _coerce_value(0, "boolean") is False

    def test_bool_passthrough(self):
        assert _coerce_value(True, "boolean") is True
        assert _coerce_value(False, "boolean") is False


class TestCoerceValueObject:
    def test_dict_passthrough(self):
        assert _coerce_value({"a": 1}, "object") == {"a": 1}

    def test_string_json_to_dict(self):
        assert _coerce_value('{"a": 1}', "object") == {"a": 1}

    def test_invalid_json_unchanged(self):
        assert _coerce_value("not json", "object") == "not json"

    def test_non_dict_non_string_unchanged(self):
        assert _coerce_value(42, "object") == 42

    def test_none_input_mode_returns_empty_dict(self):
        assert _coerce_value(None, "object", input_mode=True) == {}

    def test_none_without_input_mode_unchanged(self):
        assert _coerce_value(None, "object") is None


class TestCoerceValueArray:
    def test_list_passthrough(self):
        assert _coerce_value([1, 2, 3], "array") == [1, 2, 3]

    def test_string_json_to_list(self):
        assert _coerce_value("[1, 2, 3]", "array") == [1, 2, 3]

    def test_invalid_json_unchanged(self):
        assert _coerce_value("not json", "array") == "not json"

    def test_none_input_mode_returns_empty_list(self):
        assert _coerce_value(None, "array", input_mode=True) == []

    def test_none_without_input_mode_unchanged(self):
        assert _coerce_value(None, "array") is None


class TestCoerceValueArrayTyped:
    def test_array_string(self):
        assert _coerce_value([1, 2, 3], "array<string>") == ["1", "2", "3"]

    def test_array_integer(self):
        assert _coerce_value(["1", "2", "3"], "array<integer>") == [1, 2, 3]

    def test_array_number(self):
        assert _coerce_value(["1.1", "2.2"], "array<number>") == [1.1, 2.2]

    def test_array_boolean(self):
        assert _coerce_value(["true", "false", "1", "0"], "array<boolean>") == [
            True,
            False,
            True,
            False,
        ]

    def test_array_non_list_unchanged(self):
        assert _coerce_value("not a list", "array<string>") == "not a list"

    def test_array_object(self):
        assert _coerce_value(['{"a":1}', '{"b":2}'], "array<object>") == [
            {"a": 1},
            {"b": 2},
        ]

    def test_array_typed_from_json_string(self):
        """字符串形式的 JSON 数组应先解析再逐元素转换"""
        assert _coerce_value("[1,2,3,4]", "array<integer>") == [1, 2, 3, 4]
        assert _coerce_value('["a","b"]', "array<string>") == ["a", "b"]
        assert _coerce_value("[1.1,2.2]", "array<number>") == [1.1, 2.2]

    def test_array_typed_invalid_json_string_unchanged(self):
        assert _coerce_value("not json", "array<integer>") == "not json"

    def test_array_unknown_item_type_unchanged(self):
        assert _coerce_value([1, 2], "array<unknown>") == [1, 2]

    def test_none_input_mode_returns_empty_list(self):
        assert _coerce_value(None, "array<string>", input_mode=True) == []

    def test_none_without_input_mode_unchanged(self):
        assert _coerce_value(None, "array<string>") is None


class TestCoerceValueUnknownType:
    def test_unknown_type_passthrough(self):
        assert _coerce_value("hello", "custom_type") == "hello"


class TestCoerceOutputs:
    def test_basic_type_conversion(self):
        result = {"key0": "123123123", "key1": "hi"}
        schema = [
            {"id": "key0", "type": "integer"},
            {"id": "key1", "type": "string"},
        ]
        assert _coerce_outputs(result, schema) == {"key0": 123123123, "key1": "hi"}

    def test_mixed_types(self):
        result = {"count": "42", "price": "3.14", "name": "test", "active": "true"}
        schema = [
            {"id": "count", "type": "integer"},
            {"id": "price", "type": "number"},
            {"id": "name", "type": "string"},
            {"id": "active", "type": "boolean"},
        ]
        expected = {"count": 42, "price": 3.14, "name": "test", "active": True}
        assert _coerce_outputs(result, schema) == expected

    def test_no_schema_returns_unchanged(self):
        result = {"key0": "123"}
        assert _coerce_outputs(result, []) == result
        assert _coerce_outputs(result, None) == result

    def test_field_not_in_schema_kept_unchanged(self):
        result = {"key0": "123", "extra": "value"}
        schema = [{"id": "key0", "type": "integer"}]
        coerced = _coerce_outputs(result, schema)
        assert coerced["key0"] == 123
        assert coerced["extra"] == "value"

    def test_non_dict_result_returns_unchanged(self):
        assert _coerce_outputs("not a dict", []) == "not a dict"

    def test_array_typed_output(self):
        result = {"ids": ["1", "2", "3"]}
        schema = [{"id": "ids", "type": "array<integer>"}]
        assert _coerce_outputs(result, schema) == {"ids": [1, 2, 3]}

    def test_ir_array_with_schema_field(self):
        """IR 中 array 类型实际存储为 type: "array" + schema: {"type": "integer"}，需从 schema 子字段读取元素类型"""
        result = {"output_arrayInt": ["1", "2", "3"]}
        schema = [
            {
                "id": "output_arrayInt",
                "type": "array",
                "schema": {"id": "", "type": "integer"},
            }
        ]
        assert _coerce_outputs(result, schema) == {"output_arrayInt": [1, 2, 3]}

    def test_ir_array_with_schema_string(self):
        result = {"items": [1, 2, 3]}
        schema = [
            {"id": "items", "type": "array", "schema": {"id": "", "type": "string"}}
        ]
        assert _coerce_outputs(result, schema) == {"items": ["1", "2", "3"]}

    def test_ir_array_without_schema_treated_as_plain_array(self):
        """array 类型没有 schema 子字段时，按普通 array 处理"""
        result = {"items": [1, 2, 3]}
        schema = [{"id": "items", "type": "array"}]
        assert _coerce_outputs(result, schema) == {"items": [1, 2, 3]}

    def test_invalid_schema_entry_ignored(self):
        result = {"key0": "42"}
        schema = [{"id": "key0"}]  # missing "type"
        assert _coerce_outputs(result, schema) == {"key0": "42"}

    def test_empty_result(self):
        assert _coerce_outputs({}, []) == {}


class TestCoerceInputs:
    def test_none_string_input_to_empty(self):
        """string 类型输入为 None 时应转为空字符串"""
        user_fields = {"input": None}
        schema = [{"id": "input", "type": "string"}]
        assert _coerce_inputs(user_fields, schema) == {"input": ""}

    def test_none_integer_input_unchanged(self):
        """非 string 类型的 None 输入保持不变"""
        user_fields = {"count": None}
        schema = [{"id": "count", "type": "integer"}]
        assert _coerce_inputs(user_fields, schema) == {"count": None}

    def test_none_number_input_unchanged(self):
        user_fields = {"price": None}
        schema = [{"id": "price", "type": "number"}]
        assert _coerce_inputs(user_fields, schema) == {"price": None}

    def test_none_boolean_input_unchanged(self):
        user_fields = {"active": None}
        schema = [{"id": "active", "type": "boolean"}]
        assert _coerce_inputs(user_fields, schema) == {"active": None}

    def test_mixed_none_and_values(self):
        """部分字段为 None 部分有值"""
        user_fields = {"name": None, "count": "42"}
        schema = [
            {"id": "name", "type": "string"},
            {"id": "count", "type": "integer"},
        ]
        result = _coerce_inputs(user_fields, schema)
        assert result == {"name": "", "count": 42}

    def test_no_schema_returns_unchanged(self):
        user_fields = {"key": None}
        assert _coerce_inputs(user_fields, []) == user_fields
        assert _coerce_inputs(user_fields, None) == user_fields

    def test_non_dict_user_fields_returns_unchanged(self):
        assert (
            _coerce_inputs("not a dict", [{"id": "x", "type": "string"}])
            == "not a dict"
        )

    def test_field_not_in_schema_kept_unchanged(self):
        user_fields = {"known": None, "extra": None}
        schema = [{"id": "known", "type": "string"}]
        result = _coerce_inputs(user_fields, schema)
        assert result == {"known": "", "extra": None}

    def test_string_value_not_none_passthrough(self):
        """非 None 的 string 输入正常透传"""
        user_fields = {"name": "hello"}
        schema = [{"id": "name", "type": "string"}]
        assert _coerce_inputs(user_fields, schema) == {"name": "hello"}

    def test_empty_user_fields(self):
        assert _coerce_inputs({}, [{"id": "x", "type": "string"}]) == {}

    def test_reproduce_original_bug(self):
        """复现原始 bug 场景：start 节点 test_str 为 None 传入代码节点 input (string)"""
        user_fields = {"input": None}
        schema = [
            {"id": "input", "type": "string", "sourceType": "ref", "required": True}
        ]
        result = _coerce_inputs(user_fields, schema)
        assert result["input"] == ""
        # 原始代码 len(args.get('input', 'default')) 对 None 会报 TypeError
        # 转换后 len("") == 0，不再报错
        assert len(result["input"]) == 0

    def test_none_array_input_to_empty_list(self):
        """array 类型输入为 None 时应转为空列表"""
        user_fields = {"payCardList": None}
        schema = [{"id": "payCardList", "type": "array"}]
        result = _coerce_inputs(user_fields, schema)
        assert result["payCardList"] == []
        assert len(result["payCardList"]) == 0

    def test_none_object_input_to_empty_dict(self):
        """object 类型输入为 None 时应转为空字典"""
        user_fields = {"config": None}
        schema = [{"id": "config", "type": "object"}]
        result = _coerce_inputs(user_fields, schema)
        assert result["config"] == {}

    @staticmethod
    def test_none_object_input_populates_schema_like_legacy_engine():
        """None object 应先按 {} 应用 schema，兼容旧架构的代码入参。"""
        user_fields = {"env_input2": None}
        schema = [
            {
                "id": "env_input2",
                "type": "object",
                "required": True,
                "schema": [
                    {"id": key, "type": "string", "required": True}
                    for key in "abcde"
                ],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result == {"env_input2": {key: "" for key in "abcde"}}
        assert result["env_input2"]["a"] == ""

    @staticmethod
    def test_empty_object_input_populates_schema_like_legacy_engine():
        """空字典与 None 一样，按旧架构补齐直接子字段的默认值。"""
        user_fields = {"config": {}}
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [
                    {"id": "a", "type": "string"},
                    {"id": "b", "type": "string"},
                ],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result == {"config": {"a": "", "b": ""}}

    @staticmethod
    def test_none_object_nested_defaults_match_legacy_engine():
        """嵌套 array/object 按旧架构保持 None，而非额外物化为 []/{}。"""
        user_fields = {"config": None}
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [
                    {"id": "text", "type": "string"},
                    {"id": "count", "type": "integer"},
                    {"id": "items", "type": "array", "schema": {"type": "string"}},
                    {
                        "id": "nested",
                        "type": "object",
                        "schema": [{"id": "deep", "type": "string"}],
                    },
                ],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        # integer 默认值随 workflow_constant 配置走（默认 None / 定制 0），
        # 本用例核心断言是嵌套 array/object 保持 None 不物化
        assert result == {
            "config": {
                "text": "",
                "count": TYPE_DEFAULT_VALUE_DICT.get(INTEGER),
                "items": None,
                "nested": None,
            }
        }

    @staticmethod
    def test_partial_object_input_populates_missing_schema_defaults():
        """部分填充字典保留已有值，并按旧架构补齐缺失的直接子字段。"""
        user_fields = {"config": {"a": "configured"}}
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [
                    {"id": "a", "type": "string"},
                    {"id": "b", "type": "string"},
                ],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result == {"config": {"a": "configured", "b": ""}}

    @staticmethod
    def test_partial_object_preserves_undeclared_and_existing_values():
        """兼容性补值不得丢弃额外字段或重写调用方已经提供的值。"""
        user_fields = {
            "config": {
                "a": 7,
                "undeclared": {"keep": True},
            }
        }
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [
                    {"id": "a", "type": "string"},
                    {"id": "b", "type": "string"},
                ],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result == {
            "config": {
                "a": 7,
                "b": "",
                "undeclared": {"keep": True},
            }
        }

    @staticmethod
    def test_partial_object_input_does_not_mutate_source():
        """补齐默认值应返回新对象，不修改上游输入。"""
        original = {"configured": "value"}
        user_fields = {"config": original}
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [{"id": "missing", "type": "string"}],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result["config"] is not original
        assert original == {"configured": "value"}
        assert result["config"] == {"configured": "value", "missing": ""}

    @staticmethod
    def test_none_object_array_child_without_schema_falls_back(monkeypatch):
        """不完整的嵌套 schema 不应阻断代码节点，且降级必须记录字段名。"""
        warnings = []
        monkeypatch.setattr(
            "agent_runtime.extension.workflow_node.flow_code."
            "workflow_logger.warning",
            lambda message: warnings.append(message),
        )
        user_fields = {"config": None}
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [{"id": "items", "type": "array"}],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result == {"config": {}}
        assert len(warnings) == 1
        assert "config" in warnings[0]

    @staticmethod
    def test_none_object_unsupported_child_type_falls_back():
        """不支持的子字段类型只跳过默认值补齐，不升级为节点执行失败。"""
        user_fields = {"config": None}
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [{"id": "value", "type": "any"}],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result == {"config": {}}

    @staticmethod
    def test_partial_object_conversion_failure_preserves_original_value():
        """部分填充对象转换失败时保留已有值，不因兼容性补值而丢失数据。"""
        user_fields = {"config": {"configured": "value"}}
        schema = [
            {
                "id": "config",
                "type": "object",
                "schema": [{"id": "items", "type": "array"}],
            }
        ]

        result = _coerce_inputs(user_fields, schema)

        assert result == {"config": {"configured": "value"}}

    @staticmethod
    def test_unexpected_object_conversion_error_is_not_swallowed(monkeypatch):
        """非 schema 校验异常仍须抛出，避免兼容性降级掩盖程序错误。"""
        def raise_runtime_error(*args):
            raise RuntimeError("conversion regression")

        monkeypatch.setattr(
            "agent_runtime.extension.workflow_node.flow_code.force_convert",
            raise_runtime_error,
        )
        schema = [{"id": "config", "type": "object"}]

        with pytest.raises(RuntimeError, match="conversion regression"):
            _coerce_inputs({"config": None}, schema)

    def test_reproduce_array_none_bug(self):
        """复现本次 bug：payCardList=None 导致 len(None) 报 TypeError"""
        user_fields = {"payCardList": None}
        schema = [
            {
                "id": "payCardList",
                "type": "array",
                "schema": {"id": "", "type": "object"},
                "sourceType": "ref",
                "required": True,
            }
        ]
        result = _coerce_inputs(user_fields, schema)
        assert result["payCardList"] == []
        # 用户代码 len(payCardList) 不再报 TypeError
        assert len(result["payCardList"]) == 0
