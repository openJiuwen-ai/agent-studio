# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access

"""
Test param_deserialization oneOf type extraction.

Covers the fix for:
- Java SchemaConfig.getType() returns null for oneOf schemas
- Python defaults param_type to "" → ValueTypeEnum.from_string("") → "string"
- param_deserialization now extracts actual type from oneOf definition,
  only when the non-null subtype is unique (ambiguous unions keep the
  string fallback instead of misclassifying)
- union extraction also covers anyOf/any_of keys, array-form types
  ({"type": ["object", "null"]}, both top-level and inside union items),
  duplicate-but-unique subtypes (deduped via set), and ignores
  non-string garbage items instead of crashing
- type_inferred flag marks params whose type was defaulted (no type info
  in IR), used by FlowMcp to gate the JSON heuristic
"""

from jiuwen.extension.wrapper.restful_api_loader import param_deserialization


class TestParamDeserializationOneOf:
    """Test param_deserialization extracts type from oneOf definitions"""

    @staticmethod
    def test_one_of_object_null_extracts_object():
        """oneOf: [{type: object}, {type: null}] → param_type='object'"""
        arguments = [
            {
                "name": "arguments",
                "description": "Optional structured params",
                "required": False,
                "oneOf": [{"type": "object"}, {"type": "null"}],
                "schema": [{"name": "key", "type": "string", "description": "a key"}],
            }
        ]
        params = param_deserialization(arguments)
        assert len(params) == 1
        assert params[0].type == "object"
        assert params[0].type_inferred is False

    @staticmethod
    def test_one_of_array_null_extracts_array():
        """oneOf: [{type: array}, {type: null}] → param_type='array'"""
        arguments = [
            {
                "name": "items",
                "description": "Optional list",
                "required": False,
                "oneOf": [{"type": "array"}, {"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "array"
        assert params[0].type_inferred is False

    @staticmethod
    def test_one_of_integer_null_extracts_integer():
        """oneOf: [{type: integer}, {type: null}] → param_type='integer'"""
        arguments = [
            {
                "name": "count",
                "description": "Optional count",
                "required": False,
                "oneOf": [{"type": "integer"}, {"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "integer"

    @staticmethod
    def test_one_of_boolean_null_extracts_boolean():
        """oneOf: [{type: boolean}, {type: null}] → param_type='boolean'"""
        arguments = [
            {
                "name": "flag",
                "description": "Optional flag",
                "required": False,
                "oneOf": [{"type": "boolean"}, {"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "boolean"

    @staticmethod
    def test_one_of_string_null_extracts_string():
        """oneOf: [{type: string}, {type: null}] → param_type='string' (extracted, not inferred)"""
        arguments = [
            {
                "name": "label",
                "description": "Optional label",
                "required": False,
                "oneOf": [{"type": "string"}, {"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "string"
        assert params[0].type_inferred is False

    @staticmethod
    def test_snake_case_one_of_also_works():
        """one_of (snake_case) also recognized"""
        arguments = [
            {
                "name": "data",
                "description": "Optional data",
                "required": False,
                "one_of": [{"type": "object"}, {"type": "null"}],
                "schema": [{"name": "key", "type": "string", "description": "a key"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "object"

    @staticmethod
    def test_explicit_type_takes_precedence():
        """When type is explicitly set, oneOf is not used"""
        arguments = [
            {
                "name": "data",
                "description": "Explicit type",
                "required": False,
                "type": "integer",
                "oneOf": [{"type": "object"}, {"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "integer"
        assert params[0].type_inferred is False

    @staticmethod
    def test_no_type_no_oneof_defaults_to_string():
        """No type and no oneOf → defaults to 'string', marked type_inferred"""
        arguments = [
            {
                "name": "data",
                "description": "No type info",
                "required": False,
            }
        ]
        params = param_deserialization(arguments)
        # ValueTypeEnum.from_string("") returns "string"
        assert params[0].type == "string"
        assert params[0].type_inferred is True

    @staticmethod
    def test_one_of_all_null_no_extraction():
        """oneOf with only null types → no extraction, defaults to 'string' (inferred)"""
        arguments = [
            {
                "name": "data",
                "description": "Only null",
                "required": False,
                "oneOf": [{"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "string"
        assert params[0].type_inferred is True

    @staticmethod
    def test_one_of_multiple_non_null_types_no_extraction():
        """oneOf with multiple non-null types (ambiguous) → no extraction, string fallback"""
        arguments = [
            {
                "name": "data",
                "description": "object or array",
                "required": False,
                "oneOf": [{"type": "object"}, {"type": "array"}, {"type": "null"}],
            },
            {
                "name": "num_or_str",
                "description": "string or number",
                "required": False,
                "oneOf": [{"type": "string"}, {"type": "number"}],
            },
        ]
        params = param_deserialization(arguments)
        # 取第一个非 null 子类型会错误归类（object+array → object），
        # 无法确定唯一类型时保持 string 兜底并标记 type_inferred
        assert params[0].type == "string"
        assert params[0].type_inferred is True
        assert params[1].type == "string"
        assert params[1].type_inferred is True

    @staticmethod
    def test_multiple_params_mixed_types():
        """Multiple params with mixed oneOf and explicit types"""
        arguments = [
            {
                "name": "query",
                "description": "Search query",
                "required": True,
                "type": "string",
            },
            {
                "name": "filters",
                "description": "Optional filters",
                "required": False,
                "oneOf": [{"type": "object"}, {"type": "null"}],
                "schema": [{"name": "key", "type": "string", "description": "filter key"}],
            },
            {
                "name": "limit",
                "description": "Result limit",
                "required": False,
                "oneOf": [{"type": "integer"}, {"type": "null"}],
            },
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "string"
        assert params[0].name == "query"
        assert params[0].type_inferred is False
        assert params[1].type == "object"
        assert params[1].name == "filters"
        assert params[2].type == "integer"
        assert params[2].name == "limit"


class TestParamDeserializationUnionTypeForms:
    """JSON Schema 联合类型的多种合法形态（检视意见：数组形式 type / anyOf / 重复子类型）"""

    @staticmethod
    def test_one_of_item_array_form_type_extracts_object():
        """oneOf 子项 type 为数组形式 {"type": ["object", "null"]} → 提取 "object"

        修复前 list 直接流入 Param → Type → .startswith() AttributeError 崩溃。
        """
        arguments = [
            {
                "name": "data",
                "description": "Array-form type in oneOf item",
                "required": False,
                "oneOf": [{"type": ["object", "null"]}],
                "schema": [{"name": "k", "type": "string", "description": "a key"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "object"
        assert params[0].type_inferred is False

    @staticmethod
    def test_one_of_mixed_scalar_and_array_form_extracts_unique():
        """标量与数组形式混合：[{type: ["object","null"]}, {type: "null"}] → "object" """
        arguments = [
            {
                "name": "data",
                "description": "Mixed forms",
                "required": False,
                "oneOf": [{"type": ["object", "null"]}, {"type": "null"}],
                "schema": [{"name": "k", "type": "string", "description": "a key"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "object"
        assert params[0].type_inferred is False

    @staticmethod
    def test_one_of_item_array_form_ambiguous_no_extraction():
        """数组形式含多个非 null 类型 {"type": ["object", "array"]} → 歧义，string 兜底"""
        arguments = [
            {
                "name": "data",
                "description": "Ambiguous array-form",
                "required": False,
                "oneOf": [{"type": ["object", "array"]}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "string"
        assert params[0].type_inferred is True

    @staticmethod
    def test_one_of_duplicate_types_deduped_extracts():
        """重复但唯一的子类型 [object, object, null] → 去重后唯一 → 提取 "object" """
        arguments = [
            {
                "name": "data",
                "description": "Duplicate object entries",
                "required": False,
                "oneOf": [
                    {"type": "object"},
                    {"type": "object"},
                    {"type": "null"},
                ],
                "schema": [{"name": "k", "type": "string", "description": "a key"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "object"
        assert params[0].type_inferred is False

    @staticmethod
    def test_any_of_camel_case_extracts_object():
        """anyOf（camelCase）与 oneOf 同样处理 → 提取 "object" """
        arguments = [
            {
                "name": "data",
                "description": "anyOf camelCase",
                "required": False,
                "anyOf": [{"type": "object"}, {"type": "null"}],
                "schema": [{"name": "k", "type": "string", "description": "a key"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "object"
        assert params[0].type_inferred is False

    @staticmethod
    def test_any_of_snake_case_extracts_array():
        """any_of（snake_case）同样处理 → 提取 "array" """
        arguments = [
            {
                "name": "items",
                "description": "any_of snake_case",
                "required": False,
                "any_of": [{"type": "array"}, {"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "array"
        assert params[0].type_inferred is False

    @staticmethod
    def test_one_of_non_string_type_items_ignored_no_crash():
        """非法子项（int/dict/缺失 type）被忽略，不崩溃；无有效项 → string 兜底"""
        arguments = [
            {
                "name": "data",
                "description": "Garbage type items",
                "required": False,
                "oneOf": [{"type": 123}, {"type": {"a": 1}}, {"no_type": 1}, "raw_string"],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "string"
        assert params[0].type_inferred is True

    @staticmethod
    def test_one_of_garbage_plus_valid_extracts_valid():
        """非法子项与合法子项混合 → 忽略非法项，提取唯一合法类型"""
        arguments = [
            {
                "name": "data",
                "description": "Garbage mixed with valid",
                "required": False,
                "oneOf": [{"type": 123}, {"type": "integer"}, {"type": "null"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "integer"
        assert params[0].type_inferred is False

    @staticmethod
    def test_top_level_array_form_type_extracts_object():
        """顶层 type 为数组形式 ["object", "null"]（无 oneOf）→ 归一为 "object"

        兄弟分支：与 oneOf 子项同样的崩溃路径，修复前 list 直达 Param。
        """
        arguments = [
            {
                "name": "data",
                "description": "Top-level array-form type",
                "required": False,
                "type": ["object", "null"],
                "schema": [{"name": "k", "type": "string", "description": "a key"}],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "object"
        assert params[0].type_inferred is False

    @staticmethod
    def test_top_level_array_form_ambiguous_falls_back_to_string():
        """顶层 type ["object", "array"] 歧义 → 归一为空 → string 兜底 + inferred"""
        arguments = [
            {
                "name": "data",
                "description": "Top-level ambiguous array-form",
                "required": False,
                "type": ["object", "array"],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "string"
        assert params[0].type_inferred is True

    @staticmethod
    def test_top_level_array_form_null_only_falls_back_to_string():
        """顶层 type ["null"] → 无非 null 类型 → string 兜底 + inferred"""
        arguments = [
            {
                "name": "data",
                "description": "Top-level null-only array-form",
                "required": False,
                "type": ["null"],
            }
        ]
        params = param_deserialization(arguments)
        assert params[0].type == "string"
        assert params[0].type_inferred is True
