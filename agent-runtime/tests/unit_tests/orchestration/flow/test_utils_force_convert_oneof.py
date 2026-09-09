# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access

"""
Test force_convert oneOf/empty-value handling (utils.py).

Covers the fix for:
- _convert_one_of_type: None → None when null is a legal subtype;
  "" → None only when string is NOT a legal subtype (string|null keeps ""
  as a valid empty string, preserving original semantics)
- _convert_object/_convert_array: empty string for OPTIONAL params returns
  type default without error residue; for REQUIRED params keeps validation
  error (not silently swallowed)
"""

from jiuwen.orchestration.flow.utils import force_convert


class TestConvertOneOfNullHandling:
    """oneOf (X | null) empty/None value handling"""

    @staticmethod
    def test_object_null_with_none_returns_none():
        """object|null + None → None, no errors"""
        definition = [
            {"id": "cfg", "type": "object | null", "required": False,
             "schema": [{"id": "k", "type": "string"}]}
        ]
        converted, errors = force_convert({"cfg": None}, definition)
        assert converted["cfg"] is None
        assert errors == []

    @staticmethod
    def test_object_null_with_empty_string_returns_none():
        """object|null + '' (optional, not filled) → None, no errors"""
        definition = [
            {"id": "cfg", "type": "object | null", "required": False,
             "schema": [{"id": "k", "type": "string"}]}
        ]
        converted, errors = force_convert({"cfg": ""}, definition)
        assert converted["cfg"] is None
        assert errors == []

    @staticmethod
    def test_integer_null_with_empty_string_returns_none():
        """integer|null + '' → None (empty is not a valid integer, null is legal)"""
        definition = [{"id": "n", "type": "integer | null", "required": False}]
        converted, errors = force_convert({"n": ""}, definition)
        assert converted["n"] is None
        assert errors == []

    @staticmethod
    def test_boolean_null_with_empty_string_returns_none():
        """boolean|null + '' → None (original bug: bool('') path left error residue)"""
        definition = [{"id": "b", "type": "boolean | null", "required": False}]
        converted, errors = force_convert({"b": ""}, definition)
        assert converted["b"] is None
        assert errors == []

    @staticmethod
    def test_string_null_with_empty_string_keeps_empty_string():
        """string|null + '' → '' ('' is a valid string value, semantics preserved)"""
        definition = [{"id": "s", "type": "string | null", "required": False}]
        converted, errors = force_convert({"s": ""}, definition)
        assert converted["s"] == ""
        assert errors == []

    @staticmethod
    def test_string_null_with_none_returns_none():
        """string|null + None → None"""
        definition = [{"id": "s", "type": "string | null", "required": False}]
        converted, errors = force_convert({"s": None}, definition)
        assert converted["s"] is None
        assert errors == []

    @staticmethod
    def test_object_null_with_valid_dict_converted():
        """object|null + valid dict → converted per schema"""
        definition = [
            {"id": "cfg", "type": "object | null", "required": False,
             "schema": [{"id": "k", "type": "string"}]}
        ]
        converted, errors = force_convert({"cfg": {"k": "v"}}, definition)
        assert converted["cfg"] == {"k": "v"}
        assert errors == []


class TestConvertObjectEmptyString:
    """_convert_object empty-string handling (required vs optional)"""

    @staticmethod
    def test_optional_object_empty_string_returns_default_no_error():
        """Optional object + '' → None default, no error residue (original crash fix)"""
        definition = [
            {"id": "cfg", "type": "object", "required": False,
             "schema": [{"id": "k", "type": "string"}]}
        ]
        converted, errors = force_convert({"cfg": ""}, definition)
        assert converted["cfg"] is None
        assert errors == []

    @staticmethod
    def test_required_object_empty_string_keeps_error():
        """Required object + '' → validation error kept (not silently swallowed)"""
        definition = [
            {"id": "cfg", "type": "object", "required": True,
             "schema": [{"id": "k", "type": "string"}]}
        ]
        converted, errors = force_convert({"cfg": ""}, definition)
        assert converted["cfg"] is None
        assert len(errors) == 1
        assert "cfg" in errors[0]

    @staticmethod
    def test_object_json_string_converted():
        """Object + JSON string → parsed and converted per schema"""
        definition = [
            {"id": "cfg", "type": "object", "required": True,
             "schema": [{"id": "k", "type": "string"}]}
        ]
        converted, errors = force_convert({"cfg": '{"k": "v"}'}, definition)
        assert converted["cfg"] == {"k": "v"}
        assert errors == []


class TestConvertArrayEmptyString:
    """_convert_array empty-string handling (required vs optional)"""

    @staticmethod
    def test_optional_array_empty_string_returns_default_no_error():
        """Optional array + '' → None default, no error residue"""
        definition = [
            {"id": "items", "type": "array", "required": False,
             "schema": {"id": "", "type": "string"}}
        ]
        converted, errors = force_convert({"items": ""}, definition)
        assert converted["items"] is None
        assert errors == []

    @staticmethod
    def test_required_array_empty_string_keeps_error():
        """Required array + '' → validation error kept"""
        definition = [
            {"id": "items", "type": "array", "required": True,
             "schema": {"id": "", "type": "string"}}
        ]
        converted, errors = force_convert({"items": ""}, definition)
        assert converted["items"] is None
        assert len(errors) == 1
        assert "items" in errors[0]

    @staticmethod
    def test_array_json_string_converted():
        """Array + JSON string → parsed and converted per element schema"""
        definition = [
            {"id": "items", "type": "array", "required": True,
             "schema": {"id": "", "type": "string"}}
        ]
        converted, errors = force_convert({"items": '["a", "b"]'}, definition)
        assert converted["items"] == ["a", "b"]
        assert errors == []
