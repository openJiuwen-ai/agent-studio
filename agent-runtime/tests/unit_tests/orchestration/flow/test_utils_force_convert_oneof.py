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

    @staticmethod
    def test_null_type_with_none_input():
        """null + None -> None"""
        inputs = {"field": None}
        definition = [{"id": "field", "type": "null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    @staticmethod
    def test_null_type_with_empty_string():
        """null + "" -> None"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    @staticmethod
    def test_null_type_with_non_empty_data():
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

    @staticmethod
    def test_mcp_arguments_none():
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

    @staticmethod
    def test_mcp_arguments_with_value():
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

    @staticmethod
    def test_mcp_arguments_empty_string():
        """MCP arguments=""（空字符串）-> object 尝试失败后走 null 返回 None，无残留错误"""
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
        # 关键断言：object 分支失败的错误不能残留在 errors 中
        # 修复前 errors 包含 "Incorrect type for key: arguments, expected: object"
        assert errors == []


class TestForceConvertOneOfStringNull:
    """string|null 联合类型"""

    @staticmethod
    def test_string_null_with_none():
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

    @staticmethod
    def test_array_null_with_none():
        """array|null + None -> None"""
        inputs = {"field": None}
        definition = [{"id": "field", "type": "array | null", "schema": {"type": "integer"}}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    @staticmethod
    def test_array_null_with_valid_list():
        """array|null + [1, 2, 3] -> list"""
        inputs = {"field": [1, 2, 3]}
        definition = [{"id": "field", "type": "array | null", "schema": {"type": "integer"}}]
        result, errors = force_convert(inputs, definition)
        assert isinstance(result["field"], list)
        assert errors == []


class TestForceConvertSubExpectedTypeFix:
    """_convert_one_of_type 传参修复：传 sub_expected_type 而非完整 union type

    原 bug：_convert_simple(data, expected_type, ...) 传了完整 union type
    "integer | null"，导致 _convert_simple 不识别该类型。
    修复后传 sub_expected_type（如 "integer"），_convert_simple 能正确转换。
    """

    @staticmethod
    def test_integer_null_with_string_number():
        """integer|null + "42" -> 42（integer 子类型正确转换）"""
        inputs = {"field": "42"}
        definition = [{"id": "field", "type": "integer | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] == 42
        assert isinstance(result["field"], int)
        assert errors == []


class TestForceConvertOneOfSimpleTypeErrorCleanup:
    """oneOf 简单类型错误清理修复

    发现过程：MCP echo 工具的 opt_integer（integer|null）不填时，
    前端传空字符串 ""，_convert_simple("", "integer") 内部 int("") 抛 ValueError，
    但 _convert_simple 捕获异常后 append error + return None（不抛异常），
    _convert_one_of_type 的 except JiuWenBaseException 分支永远不触发，
    导致 "Incorrect type for key: opt_integer, expected: integer" 残留在 errors 中。

    修复：在 _convert_simple 返回后检查 errors 增长，有则清理并 continue。
    """

    @staticmethod
    def test_integer_null_with_empty_string():
        """integer|null + "" -> null 分支返回 None，无残留错误"""
        inputs = {"text": "hello", "opt_integer": ""}
        definition = [
            {"id": "text", "type": "string"},
            {"id": "opt_integer", "type": "integer | null"},
        ]
        result, errors = force_convert(inputs, definition)
        assert result["opt_integer"] is None
        # 关键断言：integer 分支 int("") 失败的错误不能残留
        assert errors == []

    @staticmethod
    def test_number_null_with_empty_string():
        """number|null + "" -> null 分支返回 None，无残留错误"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "number | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    @staticmethod
    def test_boolean_null_with_empty_string():
        """boolean|null + "" -> False（bool("") 不报错，boolean 分支直接成功）"""
        inputs = {"field": ""}
        definition = [{"id": "field", "type": "boolean | null"}]
        result, errors = force_convert(inputs, definition)
        # bool("") == False，_convert_simple 不报错，boolean 分支直接返回
        assert result["field"] is False
        assert errors == []

    @staticmethod
    def test_integer_null_with_valid_value():
        """integer|null + 42 -> 42（integer 分支直接成功）"""
        inputs = {"field": 42}
        definition = [{"id": "field", "type": "integer | null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] == 42
        assert errors == []

    @staticmethod
    def test_echo_tool_all_optional_params():
        """模拟 MCP echo 工具：所有类型可选参数都不填（全传空字符串或 None）"""
        inputs = {
            "text": "hello",
            "opt_string": "",
            "opt_integer": "",
            "opt_boolean": "",
            "opt_object": "",
            "opt_array": "",
        }
        definition = [
            {"id": "text", "type": "string"},
            {"id": "opt_string", "type": "string | null"},
            {"id": "opt_integer", "type": "integer | null"},
            {"id": "opt_boolean", "type": "boolean | null"},
            {"id": "opt_object", "type": "object | null", "schema": []},
            {"id": "opt_array", "type": "array | null", "schema": {}},
        ]
        result, errors = force_convert(inputs, definition)
        assert errors == []
        assert result["text"] == "hello"
        # string 分支 str("") == "" 直接成功
        assert result["opt_string"] == ""
        # boolean 分支 bool("") == False 直接成功（不报错，不走 null）
        assert result["opt_boolean"] is False
        # integer/number: int("")/float("") 报错 → 走 null 分支 → None
        assert result["opt_integer"] is None
        # object: json.loads("") 报错 → 走 null 分支 → None
        assert result["opt_object"] is None
        # array: json.loads("") 报错 → 走 null 分支 → None
        assert result["opt_array"] is None


class TestForceConvertRegression:
    """回归测试：修复前会崩溃的场景"""

    @staticmethod
    def test_type_null_not_supported():
        """原 Error 2: "Type null is not supported for key: field"
        修复：_convert 增加 "null" 分支
        """
        inputs = {"field": None}
        definition = [{"id": "field", "type": "null"}]
        result, errors = force_convert(inputs, definition)
        assert result["field"] is None
        assert errors == []

    @staticmethod
    def test_unsupported_type_still_errors():
        """非标准非 null 类型仍然报错"""
        inputs = {"field": "data"}
        definition = [{"id": "field", "type": "unknown_type"}]
        result, errors = force_convert(inputs, definition)
        assert len(errors) > 0
