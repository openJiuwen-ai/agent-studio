# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""
Test _format_api_inputs for None/empty value handling in MCP parameters.

Covers the fix for the core root cause:
- transform_type(None, "string") → str(None) → "None" string → MCP server Pydantic crash
- The fix intercepts None and empty string BEFORE calling transform_type.
"""

import json
import pytest
from unittest.mock import MagicMock

from jiuwen.extension.workflow_node.flow_mcp import FlowMcp


class MockParam:
    """Mock tool parameter for testing"""

    def __init__(self, name, type="string", method="Body", required=False, default_value=None):
        self.name = name
        self.type = type
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
    """Test _format_api_inputs when value is None"""

    def test_none_value_object_type_returns_empty_dict(self):
        """None + object type → {} (not str(None) → "None")"""
        params = [MockParam("arguments", type="object | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": None})
        assert result["arguments"] == {}

    def test_none_value_array_type_returns_empty_list(self):
        """None + array type → []"""
        params = [MockParam("items", type="array | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"items": None})
        assert result["items"] == []

    def test_none_value_string_type_returns_none(self):
        """None + string type → None (not str(None) → "None")"""
        params = [MockParam("name", type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"name": None})
        assert result["name"] is None

    def test_none_value_integer_type_returns_none(self):
        """None + integer type → None"""
        params = [MockParam("count", type="integer", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"count": None})
        assert result["count"] is None

    def test_none_value_boolean_type_returns_none(self):
        """None + boolean type → None"""
        params = [MockParam("flag", type="boolean", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"flag": None})
        assert result["flag"] is None


class TestFormatApiInputsEmptyString:
    """Test _format_api_inputs when value is empty string"""

    def test_empty_string_object_type_returns_empty_dict(self):
        """'' + object type → {}"""
        params = [MockParam("arguments", type="object | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": ""})
        assert result["arguments"] == {}

    def test_empty_string_array_type_returns_empty_list(self):
        """'' + array type → []"""
        params = [MockParam("items", type="array | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"items": ""})
        assert result["items"] == []

    def test_empty_string_string_type_stays_empty(self):
        """'' + string type → '' (transform_type passes through)"""
        params = [MockParam("name", type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"name": ""})
        assert result["name"] == ""


class TestFormatApiInputsValidValue:
    """Test _format_api_inputs with valid (non-None, non-empty) values"""

    def test_valid_dict_for_object_type(self):
        """Valid dict → dict (no transformation needed)"""
        params = [MockParam("arguments", type="object | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": {"key": "value"}})
        assert result["arguments"] == {"key": "value"}

    def test_valid_list_for_array_type(self):
        """Valid list → list"""
        params = [MockParam("items", type="array | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"items": [1, 2, 3]})
        assert result["items"] == [1, 2, 3]

    def test_json_string_for_object_type(self):
        """JSON string → parsed dict (for object type that comes as string)"""
        params = [MockParam("arguments", type="object | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        json_str = '{"key": "value"}'
        result = mcp._format_api_inputs({"arguments": json_str})
        assert result["arguments"] == {"key": "value"}

    def test_json_string_for_array_type(self):
        """JSON string → parsed list (for array type that comes as string)"""
        params = [MockParam("items", type="array | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        json_str = '[1, 2, 3]'
        result = mcp._format_api_inputs({"items": json_str})
        assert result["items"] == [1, 2, 3]

    def test_invalid_json_string_for_object_type_keeps_original(self):
        """Invalid JSON string → kept as-is (no crash)"""
        params = [MockParam("arguments", type="object | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({"arguments": "not valid json"})
        assert result["arguments"] == "not valid json"

    def test_empty_json_string_for_object_type_returns_empty_dict(self):
        """'' (after transform_type produces '') for object type → {}"""
        params = [MockParam("arguments", type="object | null", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        # Empty string is handled by the explicit empty string check
        result = mcp._format_api_inputs({"arguments": ""})
        assert result["arguments"] == {}


class TestFormatApiInputsHeaders:
    """Test _format_api_inputs for method=Headers parameters"""

    def test_headers_extracted_separately(self):
        """method=Headers → extracted to _header_params, not in api_inputs"""
        params = [
            MockParam("auth_token", type="string", method="Headers"),
            MockParam("query", type="string", method="Body"),
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
        params = [MockParam("query", type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        with pytest.raises(Exception):  # JiuWenBaseException
            mcp._format_api_inputs({"unknown_param": "value"})


class TestFormatApiInputsRegression:
    """Regression tests for the original crash scenario"""

    def test_mcp_oneof_object_null_full_scenario(self):
        """Full scenario: MCP tool with oneOf [object, null] argument,
        user doesn't fill it → force_convert returns None →
        _format_api_inputs should NOT produce "None" string.
        """
        params = [
            MockParam("query", type="string", method="Body", required=True),
            MockParam("arguments", type="object | null", method="Body", required=False),
        ]
        mcp = _create_flow_mcp_with_params(params)

        # Simulating what force_convert returns for empty arguments
        result = mcp._format_api_inputs({
            "query": "hello",
            "arguments": None,  # user didn't fill, force_convert → None
        })

        # Critical: arguments must NOT be the string "None"
        assert result["arguments"] != "None", (
            "Regression: arguments should not be string 'None', "
            "this is the exact bug that caused Pydantic validation failure"
        )
        # Should be empty dict for object type
        assert result["arguments"] == {}

    def test_mcp_optional_string_param_with_none(self):
        """Optional string param with None → None, not "None" string"""
        params = [
            MockParam("query", type="string", method="Body", required=True),
            MockParam("optional_text", type="string", method="Body", required=False),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({
            "query": "hello",
            "optional_text": None,
        })

        assert result["optional_text"] is None, (
            "Optional string param with None should stay None, not become string 'None'"
        )

    def test_multiple_none_params(self):
        """Multiple None params of different types"""
        params = [
            MockParam("query", type="string", method="Body"),
            MockParam("arguments", type="object | null", method="Body"),
            MockParam("items", type="array | null", method="Body"),
            MockParam("count", type="integer", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result = mcp._format_api_inputs({
            "query": None,
            "arguments": None,
            "items": None,
            "count": None,
        })

        assert result["query"] is None
        assert result["arguments"] == {}
        assert result["items"] == []
        assert result["count"] is None
