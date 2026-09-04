# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""
Test force_convert with oneOf/nullable types.

基于 MCP 节点 oneOf 可选 Object 参数报错的真实场景构建测试。
IR 结构参考 Java IrAdapterService 生成的实际格式：
- 每个参数定义有 "id"（属性名）和 "type"
- object 参数的 "schema" 是子属性列表，每项也有 "id"
- oneOf: [object, null] 在 IR 中表示为 type: "object | null"

Covers the fixes for:
- _convert: "null" type handling（原 "Type null is not supported"）
- _convert_one_of_type: isinstance 返回值检查、sub_expected_type 传参修复、"null" 子类型
"""

import pytest

from jiuwen.orchestration.flow.utils import force_convert


class TestForceConvertNullType:
    """_convert 新增 "null" 类型支持"""

    def test_null_type_with_none_input(self):
        """null + None -> None"""
        inputs = {"field": None}
        definition = [{"id": "field", "type": "null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_null_type_with_empty_string(self):
        """null + "" -> None"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_null_type_with_non_empty_data(self):
        """null + non-empty data -> 原样返回"""
        inputs = {"field": "hello"}
        definition = [{"id": "field", "type": "null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] == "hello"
        assert errors == []


class TestForceConvertOneOfObjectNull:
    """object|null 联合类型 — MCP 场景的核心类型

    真实 IR 示例（MCP 工具 meta-wise-chat 的 arguments 参数）：
    {
        "id": "arguments",
        "type": "object | null",
        "schema": [
            {"id": "context", "type": "string"},
            {"id": "max_tokens", "type": "integer"},
        ]
    }
    """

    def test_mcp_arguments_none(self):
        """MCP arguments=None（用户不填可选 object 参数）-> None，无报错"""
        inputs = {"query": "hello", "arguments": None}
        definition = [
            {"id": "query", "type": "string"},
            {
                "id": "arguments",
                "type": "object | null",
                "schema": [
                    {"id": "context", "type": "string"},
                    {"id": "max_tokens", "type": "integer"},
                ],
            },
        ]
        result, errors = force_convert(inputs, definition)
        assert result["query"] == "hello"
        assert result["arguments"] is None
        assert errors == []

    def test_mcp_arguments_with_value(self):
        """MCP arguments 有值 -> 正常转换子属性类型"""
        inputs = {"query": "hello", "arguments": {"context": "test", "max_tokens": "100"}}
        definition = [
            {"id": "query", "type": "string"},
            {
                "id": "arguments",
                "type": "object | null",
                "schema": [
                    {"id": "context", "type": "string"},
                    {"id": "max_tokens", "type": "integer"},
                ],
            },
        ]
        result, errors = force_convert(inputs, definition)
        assert result["arguments"]["context"] == "test"
        assert result["arguments"]["max_tokens"] == 100
        assert isinstance(result["arguments"]["max_tokens"], int)
        assert errors == []

    def test_mcp_arguments_empty_string(self):
        """MCP arguments=""（空字符串）-> 优先走 null 返回 None，无残留错误"""
        inputs = {"query": "hello", "arguments": ""}
        definition = [
            {"id": "query", "type": "string"},
            {
                "id": "arguments",
                "type": "object | null",
                "schema": [
                    {"id": "context", "type": "string"},
                ],
            },
        ]
        result, errors = force_convert(inputs, definition)
        assert result["arguments"] is None
        assert errors == []


class TestForceConvertOneOfStringNull:
    """string|null 联合类型"""

    def test_string_null_with_none(self):
        """string|null + None -> None 或 ""（取决于 string 子类型的 None 处理）"""
        inputs = {"field": None}
        definition = [{"id": "field", "type": "string | null"}]
        result, errors = force_convert(inputs, definition)
        # string 子类型尝试 convert(None) → "" (TYPE_DEFAULT_VALUE)
        # 或 null 子类型处理 None → None
        # 两种结果都是合理的
        assert result["field"] is None or result["field"] == ""
        assert errors == []


class TestForceConvertOneOfArrayNull:
    """array|null 联合类型"""

    def test_array_null_with_none(self):
        """array|null + None -> None"""
        inputs = {"field": None}
        definition = [{"id": "field", "type": "array | null", "schema": {"type": "integer"}}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_array_null_with_valid_list(self):
        """array|null + [1, 2, 3] -> list"""
        inputs = {"field": [1, 2, 3]}
        definition = [{"id": "field", "type": "array | null", "schema": {"type": "integer"}}]
        result, errors = force_convert(inputs, definition)
        assert isinstance(result["field"], list)
        assert errors == []

    def test_array_null_with_empty_string(self):
        """array|null + "" -> 优先走 null 返回 None，无残留错误"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "array | null", "schema": {"type": "integer"}}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []


class TestUnifiedNullCheck:
    """统一 null 优先检查：data 为 None/"" 且 null 是合法子类型时直接返回 None"""

    def test_integer_null_with_empty_string(self):
        """integer|null + "" -> 优先走 null 返回 None，不尝试 int("") 避免报错"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "integer | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_number_null_with_empty_string(self):
        """number|null + "" -> 优先走 null 返回 None"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "number | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_boolean_null_with_empty_string(self):
        """boolean|null + "" -> 优先走 null 返回 None"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "boolean | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_string_null_with_empty_string(self):
        """string|null + "" -> 优先走 null 返回 None"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "string | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_object_null_with_empty_string(self):
        """object|null + "" -> 优先走 null 返回 None，不尝试 json.loads("")"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "object | null", "schema": [{"id": "x", "type": "string"}]}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []


class TestForceConvertSubExpectedTypeFix:
    """_convert_one_of_type 传参修复：传 sub_expected_type 而非完整 union type

    原 bug：_convert_simple(data, expected_type, ...) 传了完整 union type
    "integer | null"，导致 _convert_simple 不识别该类型。
    修复后传 sub_expected_type（如 "integer"），_convert_simple 能正确转换。
    """

    def test_integer_null_with_string_number(self):
        """integer|null + "42" -> 42（integer 子类型正确转换）"""
        inputs = {"field": "42"}
        definition = [{"id": "field", "type": "integer | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] == 42
        assert isinstance(result["field"], int)
        assert errors == []


class TestForceConvertRegression:
    """回归测试：修复前会崩溃的场景"""

    def test_type_null_not_supported(self):
        """原 Error 2: "Type null is not supported for key: field"
        修复：_convert 增加 "null" 分支
        """
        inputs = {"field": None}
        definition = [{"id": "field", "type": "null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    def test_unsupported_type_still_errors(self):
        """非标准非 null 类型仍然报错"""
        inputs = {"field": "data"}
        definition = [{"id": "field", "type": "unknown_type"}]
        result, errors = force_convert(inputs, definition)
        assert len(errors) > 0
