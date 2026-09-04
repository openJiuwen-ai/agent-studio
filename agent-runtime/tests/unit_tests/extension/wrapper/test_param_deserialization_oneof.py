# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""
Test param_deserialization oneOf type extraction.

Covers the fix for:
- Java SchemaConfig.getType() returns null for oneOf schemas
- Python defaults param_type to "" → ValueTypeEnum.from_string("") → "string"
- param_deserialization now extracts actual type from oneOf definition
"""

from jiuwen.extension.wrapper.restful_api_loader import param_deserialization


class TestParamDeserializationOneOf:
    """Test param_deserialization extracts type from oneOf definitions"""

    def test_one_of_object_null_extracts_object(self):
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

    def test_one_of_array_null_extracts_array(self):
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

    def test_one_of_integer_null_extracts_integer(self):
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

    def test_one_of_boolean_null_extracts_boolean(self):
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

    def test_one_of_string_null_extracts_string(self):
        """oneOf: [{type: string}, {type: null}] → param_type='string'"""
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

    def test_snake_case_one_of_also_works(self):
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

    def test_explicit_type_takes_precedence(self):
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

    def test_no_type_no_oneof_defaults_to_string(self):
        """No type and no oneOf → defaults to 'string' (ValueTypeEnum behavior)"""
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

    def test_one_of_all_null_no_extraction(self):
        """oneOf with only null types → no extraction, defaults to 'string'"""
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

    def test_multiple_params_mixed_types(self):
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
        assert params[1].type == "object"
        assert params[1].name == "filters"
        assert params[2].type == "integer"
        assert params[2].name == "limit"
