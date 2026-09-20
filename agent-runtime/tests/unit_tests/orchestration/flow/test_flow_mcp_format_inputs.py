# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access

"""
Test _format_api_inputs for None/empty value handling in MCP parameters.

Covers the fix for:
- transform_type(None, "string") → str(None) → "None" string → MCP server Pydantic crash
- param_deserialization extracts actual type from oneOf (e.g. object|null → "object")
- _format_api_inputs uses correct type to handle None/empty/JSON values
- JSON heuristic constrained to declared object/array params or type-inferred
  (legacy IR) string params; explicit string params are never rewritten
- schema patches returned per call (shared tool card is never mutated)
- method=Headers params with None value are skipped (no "None" header);
  REQUIRED headers with None value raise explicitly instead of being
  silently swallowed (headers bypass card schema validation)
"""

from unittest.mock import MagicMock

import pytest

from jiuwen.extension.workflow_node.flow_mcp import FlowMcp


class MockParam:
    """Mock tool parameter for testing"""

    def __init__(
        self,
        name,
        param_type="string",
        method="Body",
        required=False,
        default_value=None,
        type_inferred=False,
        description="",
    ):
        self.name = name
        self.type = param_type
        self.method = method
        self.required = required
        self.default_value = default_value
        self.type_inferred = type_inferred
        self.description = description


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


def _create_mcp_with_tool_card(params, input_params_schema):
    """Create FlowMcp with both client params and MCPTool card (for patched-tool tests)"""
    mcp = _create_flow_mcp_with_params(params)
    mock_tool = MagicMock()
    mock_card = MagicMock()
    mock_card.input_params = input_params_schema
    mock_card.model_copy = MagicMock(
        side_effect=lambda update=None: MagicMock(input_params=update["input_params"])
    )
    # Tool 基类通过公开 card property 暴露 _card，产品代码只访问 self.api.card
    mock_tool.card = mock_card
    mcp.api = mock_tool
    return mcp


class TestFormatApiInputsNoneValue:
    """Test _format_api_inputs when value is None → should pass through as None"""

    @staticmethod
    def test_none_value_object_type():
        """None + object type → None (MCP server accepts None for optional params)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": None})
        assert result["arguments"] is None
        assert patches == {}

    @staticmethod
    def test_none_value_array_type():
        """None + array type → None"""
        params = [MockParam("items", param_type="array", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"items": None})
        assert result["items"] is None

    @staticmethod
    def test_none_value_string_type():
        """None + string type → None (not str(None) → "None")"""
        params = [MockParam("name", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"name": None})
        assert result["name"] is None

    @staticmethod
    def test_none_value_integer_type():
        """None + integer type → None"""
        params = [MockParam("count", param_type="integer", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"count": None})
        assert result["count"] is None

    @staticmethod
    def test_none_value_boolean_type():
        """None + boolean type → None"""
        params = [MockParam("flag", param_type="boolean", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"flag": None})
        assert result["flag"] is None


class TestFormatApiInputsEmptyString:
    """Test _format_api_inputs when value is empty string"""

    @staticmethod
    def test_empty_string_object_type_passes_through():
        """'' + object type → '' (no JSON parse, no error)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": ""})
        assert result["arguments"] == ""
        assert patches == {}

    @staticmethod
    def test_empty_string_array_type_passes_through():
        """'' + array type → ''"""
        params = [MockParam("items", param_type="array", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"items": ""})
        assert result["items"] == ""

    @staticmethod
    def test_empty_string_string_type_stays_empty():
        """'' + string type → '' (pass through)"""
        params = [MockParam("name", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"name": ""})
        assert result["name"] == ""


class TestFormatApiInputsValidValue:
    """Test _format_api_inputs with valid (non-None, non-empty) values"""

    @staticmethod
    def test_valid_dict_for_object_type():
        """Valid dict → dict (no transformation needed)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": {"key": "value"}})
        assert result["arguments"] == {"key": "value"}
        assert patches == {}

    @staticmethod
    def test_valid_list_for_array_type():
        """Valid list → list"""
        params = [MockParam("items", param_type="array", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"items": [1, 2, 3]})
        assert result["items"] == [1, 2, 3]

    @staticmethod
    def test_valid_string_value():
        """Valid string → string"""
        params = [MockParam("query", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"query": "hello world"})
        assert result["query"] == "hello world"

    @staticmethod
    def test_invalid_json_string_keeps_original():
        """Invalid JSON string not starting with {/[ → kept as-is (heuristic skips)"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": "not valid json"})
        # "not valid json" doesn't start with '{' or '[', so heuristic is skipped
        assert result["arguments"] == "not valid json"
        assert patches == {}


class TestFormatApiInputsHeaders:
    """Test _format_api_inputs for method=Headers parameters"""

    @staticmethod
    def test_headers_extracted_separately():
        """method=Headers → extracted to _header_params, not in api_inputs"""
        params = [
            MockParam("auth_token", param_type="string", method="Headers"),
            MockParam("query", param_type="string", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({
            "auth_token": "my_token",
            "query": "hello world",
        })
        assert "auth_token" not in result
        assert result["query"] == "hello world"
        assert mcp._header_params["auth_token"] == "my_token"

    @staticmethod
    def test_none_header_value_skipped():
        """method=Headers + None → skipped, not converted to "None" string"""
        params = [
            MockParam("auth_token", param_type="string", method="Headers"),
            MockParam("query", param_type="string", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({
            "auth_token": None,
            "query": "hello",
        })
        assert "auth_token" not in mcp._header_params
        assert result["query"] == "hello"

    @staticmethod
    def test_required_header_none_raises():
        """method=Headers + required=True + None → 显式报错

        header 不参与 card schema 的 client-side 校验，静默跳过后
        下游没有任何报错点，必须与 Body 分支必填校验行为一致。
        """
        params = [
            MockParam("auth_token", param_type="string", method="Headers", required=True),
            MockParam("query", param_type="string", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        with pytest.raises(Exception):  # JiuWenBaseException 101876
            mcp._format_api_inputs({"auth_token": None, "query": "hello"})

    @staticmethod
    def test_required_header_string_true_none_raises():
        """required="true"（字符串形式，见 _create_client 兼容校验）+ None → 同样报错"""
        params = [
            MockParam("auth_token", param_type="string", method="Headers", required="true"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        with pytest.raises(Exception):
            mcp._format_api_inputs({"auth_token": None})

    @staticmethod
    def test_required_header_string_false_none_skipped():
        """required="false"（字符串形式）+ None → 非空字符串不得被 truthy 误判为必填"""
        params = [
            MockParam("auth_token", param_type="string", method="Headers", required="false"),
            MockParam("query", param_type="string", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({"auth_token": None, "query": "hello"})
        assert "auth_token" not in mcp._header_params
        assert result["query"] == "hello"

    @staticmethod
    def test_required_header_with_value_included():
        """required header 有值 → 正常写入 _header_params，不报错"""
        params = [
            MockParam("auth_token", param_type="string", method="Headers", required=True),
        ]
        mcp = _create_flow_mcp_with_params(params)

        mcp._format_api_inputs({"auth_token": "tok123"})
        assert mcp._header_params["auth_token"] == "tok123"


class TestFormatApiInputsParamNotFound:
    """Test _format_api_inputs when input param is not in tool_params"""

    @staticmethod
    def test_unknown_param_raises_error():
        """Input param not found in tool_params → raises JiuWenBaseException"""
        params = [MockParam("query", param_type="string", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        with pytest.raises(Exception):  # JiuWenBaseException
            mcp._format_api_inputs({"unknown_param": "value"})


class TestFormatApiInputsJsonHeuristic:
    """Test JSON heuristic gating: which params get JSON-string values parsed"""

    @staticmethod
    def test_declared_object_type_json_string_parsed():
        """Declared object param + JSON string → parsed to dict + patch recorded"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": '{"key": "value"}'})
        assert result["arguments"] == {"key": "value"}
        assert patches == {"arguments": "object"}

    @staticmethod
    def test_declared_array_type_json_string_parsed():
        """Declared array param + JSON string → parsed to list + patch recorded"""
        params = [MockParam("items", param_type="array", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"items": "[1, 2, 3]"})
        assert result["items"] == [1, 2, 3]
        assert patches == {"items": "array"}

    @staticmethod
    def test_inferred_string_type_json_string_parsed():
        """Legacy IR (no type info → inferred string) + JSON string → parsed"""
        params = [
            MockParam("arguments", param_type="string", method="Body", type_inferred=True)
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": '{"key": "value"}'})
        assert result["arguments"] == {"key": "value"}
        assert patches == {"arguments": "object"}

    @staticmethod
    def test_inferred_string_type_json_array_parsed():
        """Legacy IR inferred string + JSON array string → parsed to list"""
        params = [
            MockParam("items", param_type="string", method="Body", type_inferred=True)
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"items": '["a", "b"]'})
        assert result["items"] == ["a", "b"]
        assert patches == {"items": "array"}

    @staticmethod
    def test_explicit_string_type_json_string_kept():
        """Explicit string param + JSON-looking string → kept as string (no rewrite)"""
        params = [
            MockParam("payload", param_type="string", method="Body", type_inferred=False)
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"payload": '{"key": "value"}'})
        assert result["payload"] == '{"key": "value"}'
        assert patches == {}

    @staticmethod
    def test_explicit_string_type_json_array_kept():
        """Explicit string param + JSON array string → kept as string"""
        params = [
            MockParam("payload", param_type="string", method="Body", type_inferred=False)
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"payload": "[1, 2]"})
        assert result["payload"] == "[1, 2]"
        assert patches == {}

    @staticmethod
    def test_param_without_inferred_flag_defaults_to_no_parse():
        """Missing type_inferred attr (other Param sources) → treated as explicit"""
        params = [MockParam("payload", param_type="string", method="Body")]
        del params[0].type_inferred  # simulate Param from other loaders
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"payload": '{"a": 1}'})
        assert result["payload"] == '{"a": 1}'
        assert patches == {}

    @staticmethod
    def test_invalid_json_keeps_string_no_patch():
        """'{"broken": ' invalid JSON → kept as original string, no patch"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": '{"broken": '})
        assert result["arguments"] == '{"broken": '
        assert patches == {}

    @staticmethod
    def test_empty_dict_string_parsed():
        """'{}' empty JSON object string → parsed to empty dict"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"arguments": "{}"})
        assert result["arguments"] == {}
        assert patches == {"arguments": "object"}

    @staticmethod
    def test_json_scalar_string_not_parsed():
        """'123' / '"quoted"' → not dict/list, heuristic leaves value as-is"""
        params = [MockParam("count", param_type="string", method="Body", type_inferred=True)]
        mcp = _create_flow_mcp_with_params(params)

        result, patches = mcp._format_api_inputs({"count": "123"})
        assert result["count"] == "123"
        assert patches == {}


class TestBuildInputParamsFromArguments:
    """Test card schema required 列表构建的 required 归一化（检视意见：flow_mcp.py:234）"""

    @staticmethod
    def test_bool_required_true_in_required_list():
        """required=True（bool）→ 进入 required 列表（原有行为不变）"""
        params = [MockParam("query", param_type="string", required=True)]
        mcp = _create_flow_mcp_with_params(params)
        schema = mcp._build_input_params_from_arguments()
        assert schema["required"] == ["query"]

    @staticmethod
    def test_bool_required_false_no_required_key():
        """required=False（bool）→ 无 required 键（原有行为不变）"""
        params = [MockParam("opt", param_type="string", required=False)]
        mcp = _create_flow_mcp_with_params(params)
        schema = mcp._build_input_params_from_arguments()
        assert "required" not in schema

    @staticmethod
    def test_string_required_false_not_in_required_list():
        """required="false"（字符串形态）→ 非空字符串不得被 truthy 误判为必填

        误判会使可选参数进入 card required 列表，未填写时被
        format_with_schema + skip_none_value 强校验拦截。
        """
        params = [MockParam("opt", param_type="string", required="false")]
        mcp = _create_flow_mcp_with_params(params)
        schema = mcp._build_input_params_from_arguments()
        assert "required" not in schema

    @staticmethod
    def test_string_required_true_in_required_list():
        """required="true"（字符串形态）→ 正常进入 required 列表，混合形态判定正确"""
        params = [
            MockParam("query", param_type="string", required="true"),
            MockParam("opt", param_type="string", required="false"),
        ]
        mcp = _create_flow_mcp_with_params(params)
        schema = mcp._build_input_params_from_arguments()
        assert schema["required"] == ["query"]

    @staticmethod
    def test_headers_param_excluded_from_properties_and_required():
        """method=Headers 参数不进 properties/required（原有行为不变）"""
        params = [
            MockParam("auth", param_type="string", method="Headers", required=True),
            MockParam("query", param_type="string", required=True),
        ]
        mcp = _create_flow_mcp_with_params(params)
        schema = mcp._build_input_params_from_arguments()
        assert "auth" not in schema["properties"]
        assert schema["required"] == ["query"]


class TestBuildPatchedTool:
    """Test _build_patched_tool creates per-call copy without mutating shared card"""

    @staticmethod
    def test_shared_card_not_mutated():
        """Patching builds a copy — original card.input_params stays untouched"""
        params = [MockParam("arguments", param_type="object", method="Body")]
        schema = {"type": "object", "properties": {"arguments": {"type": "string"}}}
        mcp = _create_mcp_with_tool_card(params, schema)

        _, patches = mcp._format_api_inputs({"arguments": '{"k": "v"}'})
        assert patches == {"arguments": "object"}
        # shared schema untouched by _format_api_inputs
        assert schema["properties"]["arguments"]["type"] == "string"

        patched_tool = mcp._build_patched_tool(patches)
        # original card still untouched after building patched tool
        assert schema["properties"]["arguments"]["type"] == "string"
        # patched copy has the corrected type
        model_copy_call = mcp.api.card.model_copy.call_args
        patched_params = model_copy_call.kwargs["update"]["input_params"]
        assert patched_params["properties"]["arguments"]["type"] == "object"
        assert patched_tool is not None

    @staticmethod
    def test_patched_params_are_deep_copy():
        """Nested structures in patched schema are independent from the original"""
        params = [MockParam("items", param_type="array", method="Body")]
        schema = {
            "type": "object",
            "properties": {
                "items": {"type": "string", "description": "keep me"},
                "other": {"type": "string"},
            },
        }
        mcp = _create_mcp_with_tool_card(params, schema)

        patched_tool = mcp._build_patched_tool({"items": "array"})
        model_copy_call = mcp.api.card.model_copy.call_args
        patched_params = model_copy_call.kwargs["update"]["input_params"]
        assert patched_params["properties"]["items"]["type"] == "array"
        assert patched_params["properties"]["items"]["description"] == "keep me"
        assert patched_params["properties"]["other"]["type"] == "string"
        # original unchanged
        assert schema["properties"]["items"]["type"] == "string"
        assert patched_tool is not None


class TestFormatApiInputsRegression:
    """Regression tests for the original crash scenario"""

    @staticmethod
    def test_none_value_never_becomes_none_string():
        """Core regression: None must NOT become the string "None" """
        params = [
            MockParam("query", param_type="string", method="Body", required=True),
            MockParam("arguments", param_type="object", method="Body", required=False),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({
            "query": "hello",
            "arguments": None,
        })

        assert result["arguments"] is None
        assert result["arguments"] != "None", (
            "Regression: arguments should not be string 'None'"
        )

    @staticmethod
    def test_multiple_none_params():
        """Multiple None params of different types all stay None"""
        params = [
            MockParam("query", param_type="string", method="Body"),
            MockParam("arguments", param_type="object", method="Body"),
            MockParam("items", param_type="array", method="Body"),
            MockParam("count", param_type="integer", method="Body"),
        ]
        mcp = _create_flow_mcp_with_params(params)

        result, _ = mcp._format_api_inputs({
            "query": None,
            "arguments": None,
            "items": None,
            "count": None,
        })

        assert result["query"] is None
        assert result["arguments"] is None
        assert result["items"] is None
        assert result["count"] is None
