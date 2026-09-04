# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""
Test _format_api_inputs for None/empty value handling in MCP parameters.

Covers the fix for:
- transform_type(None, "string") → str(None) → "None" string → MCP server Pydantic crash
- param_deserialization extracts actual type from oneOf (e.g. object|null → "object")
- _format_api_inputs uses correct type to handle None/empty/JSON values
"""

from unittest.mock import MagicMock

import pytest

from jiuwen.extension.workflow_node.flow_mcp import FlowMcp


class MockParam:
    """Mock tool parameter for testing"""

    def __init__(self, name, param_type="string", method="Body", required=False, default_value=None):
        self.name = name
        self.type = param_type
        self.method = method
        self.required = required
        self.default_value = default_value


def _create_flow_mcp_with_params(params):
    """Create a FlowMcp instance with mock client and tool_params"""
    mcp = FlowMcp.__new__(FlowMcp)
    mcp._conf = {"type": "sse", "url": "http://test", "tool_name": "test_tool"}
    mcp._is_older_version = False
    mcp._header_params = {}

    mock_client = MagicMock()
    mock_client._tool_params = params
    mcp._client = mock_client

    return mcp


class TestFormatApiInputsNoneValue:
    """Test _format_api_inputs when value is None → should pass through as None"""

    def test_none_value_object_type(self):
        """None + object type → None (MCP server accepts None for optional params)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": None})
        assert result["arguments"] is None

    def test_none_value_array_type(self):
        """None + array type → None"""
        params = [MockParam("items", param_type="array", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"items": None})
        assert result["items"] is None

    def test_none_value_string_type(self):
        """None + string type → None (not str(None) → "None")"""
        params = [MockParam("name", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"name": None})
        assert result["name"] is None

    def test_none_value_integer_type(self):
        """None + integer type → None"""
        params = [MockParam("count", param_type="integer", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"count": None})
        assert result["count"] is None

    def test_none_value_boolean_type(self):
        """None + boolean type → None"""
        params = [MockParam("flag", param_type="boolean", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"flag": None})
        assert result["flag"] is None


class TestFormatApiInputsEmptyString:
    """Test _format_api_inputs when value is empty string"""

    def test_empty_string_object_type_passes_through(self):
        """'' + object type → '' (transform_type passes through; force_convert upstream handles conversion)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": ""})
        # transform_type("", "object") returns "" as-is (line 77: return value)
        # The empty string → {} conversion is handled upstream by force_convert (utils.py)
        assert result["arguments"] == ""

    def test_empty_string_array_type_passes_through(self):
        """'' + array type → '' (transform_type passes through; force_convert upstream handles conversion)"""
        params = [MockParam("items", param_type="array", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"items": ""})
        assert result["items"] == ""

    def test_empty_string_string_type_stays_empty(self):
        """'' + string type → '' (pass through)"""
        params = [MockParam("name", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"name": ""})
        assert result["name"] == ""


class TestFormatApiInputsValidValue:
    """Test _format_api_inputs with valid (non-None, non-empty) values"""

    def test_valid_dict_for_object_type(self):
        """Valid dict → dict (no transformation needed)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": {"key": "value"}})
        assert result["arguments"] == {"key": "value"}

    def test_valid_list_for_array_type(self):
        """Valid list → list"""
        params = [MockParam("items", param_type="array", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"items": [1, 2, 3]})
        assert result["items"] == [1, 2, 3]

    def test_valid_string_value(self):
        """Valid string → string"""
        params = [MockParam("query", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"query": "hello world"})
        assert result["query"] == "hello world"

    def test_invalid_json_string_keeps_original(self):
        """Invalid JSON string not starting with {/[ → kept as-is (heuristic skips)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": "not valid json"})
        # "not valid json" doesn't start with '{' or '[', so heuristic is skipped
        assert result["arguments"] == "not valid json"


class TestFormatApiInputsHeaders:
    """Test _format_api_inputs for method=Headers parameters"""

    def test_headers_extracted_separately(self):
        """method=Headers → extracted to _header_params, not in api_inputs"""
        params = [
            MockParam("auth_token", param_type="string", method="Headers"),
            MockParam("query", param_type="string", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({
            "auth_token": "my_token",
            "query": "hello world",
        })
        assert "auth_token" not in result
        assert result["query"] == "hello world"
        assert mcp._header_params["auth_token"] == "my_token"


class TestFormatApiInputsParamNotFound:
    """Test _format_api_inputs when input param is not in tool_params"""

    def test_unknown_param_raises_error(self):
        """Input param not found in tool_params → raises JiuWenBaseException"""
        params = [MockParam("query", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        with pytest.raises(Exception):  # JiuWenBaseException
            mcp._format_api_inputs({"unknown_param": "value"})


class TestFormatApiInputsJsonHeuristic:
    """Test _format_api_inputs JSON heuristic: strings starting with {/[ get parsed"""

    def _create_mcp_with_tool_card(self, params, input_params_schema):
        """Create FlowMcp with both client params and MCPTool card for schema patching"""
        mcp = _create_flow_mcp_with_params(params)
        # Mock MCPTool with card for schema patching
        mock_tool = MagicMock()
        mock_tool._card = MagicMock()
        mock_tool._card.input_params = input_params_schema
        mcp.api = mock_tool
        return mcp

    def test_json_object_string_parsed_to_dict(self):
        """'{"key": "value"}' string → parsed to dict when schema says string but value is JSON"""
        params = [MockParam("arguments", param_type="string", method="Body")]
        schema = {"properties": {"arguments": {"type": "string"}}}
        mcp = self._create_mcp_with_tool_card(params, schema)

        result = mcp._format_api_inputs({"arguments": '{"key": "value"}'})
        assert result["arguments"] == {"key": "value"}
        # Schema should be patched to "object"
        assert schema["properties"]["arguments"]["type"] == "object"

    def test_json_array_string_parsed_to_list(self):
        """'[1, 2, 3]' string → parsed to list"""
        params = [MockParam("items", param_type="string", method="Body")]
        schema = {"properties": {"items": {"type": "string"}}}
        mcp = self._create_mcp_with_tool_card(params, schema)

        result = mcp._format_api_inputs({"items": "[1, 2, 3]"})
        assert result["items"] == [1, 2, 3]
        assert schema["properties"]["items"]["type"] == "array"

    def test_json_string_without_tool_card_still_parsed(self):
        """JSON string parsed even without MCPTool (no schema patching)"""
        params = [MockParam("arguments", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)
        mcp.api = None  # No MCPTool

        result = mcp._format_api_inputs({"arguments": '{"key": "value"}'})
        assert result["arguments"] == {"key": "value"}

    def test_invalid_json_keeps_string(self):
        """'{"broken": ' invalid JSON → kept as original string"""
        params = [MockParam("arguments", param_type="string", method="Body")]
        schema = {"properties": {"arguments": {"type": "string"}}}
        mcp = self._create_mcp_with_tool_card(params, schema)

        result = mcp._format_api_inputs({"arguments": '{"broken": '})
        assert result["arguments"] == '{"broken": '
        # Schema should NOT be patched
        assert schema["properties"]["arguments"]["type"] == "string"

    def test_empty_dict_string_parsed(self):
        """'{}' empty JSON object string → parsed to empty dict"""
        params = [MockParam("arguments", param_type="string", method="Body")]
        schema = {"properties": {"arguments": {"type": "string"}}}
        mcp = self._create_mcp_with_tool_card(params, schema)

        result = mcp._format_api_inputs({"arguments": "{}"})
        assert result["arguments"] == {}
        assert schema["properties"]["arguments"]["type"] == "object"


class TestFormatApiInputsRegression:
    """Regression tests for the original crash scenario"""

    def test_none_value_never_becomes_none_string(self):
        """Core regression: None must NOT become the string "None" """
        params = [
            MockParam("query", param_type="string", method="Body", required=True),
            MockParam("arguments", param_type="object", method="Body", required=False),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({
            "query": "hello",
            "arguments": None,
        })

        assert result["arguments"] is None
        assert result["arguments"] != "None", (
            "Regression: arguments should not be string 'None'"
        )

    def test_multiple_none_params(self):
        """Multiple None params of different types all stay None"""
        params = [
            MockParam("query", param_type="string", method="Body"),
            MockParam("arguments", param_type="object", method="Body"),
            MockParam("items", param_type="array", method="Body"),
            MockParam("count", param_type="integer", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({
            "query": None,
            "arguments": None,
            "items": None,
            "count": None,
        })

        assert result["query"] is None
        assert result["arguments"] is None
        assert result["items"] is None
        assert result["count"] is None
