# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for extract_params.py — ExtractParams.parse_llm_response regex fix."""

from jiuwen.controller.atomic_skills.extract_params import ExtractParams


def _make_extractor():
    """创建 ExtractParams 实例，绕过 __init__ 中的外部依赖。"""
    obj = ExtractParams.__new__(ExtractParams)
    return obj


class TestParseLlmResponseCodeBlock:
    """parse_llm_response — markdown 代码块正则提取。"""

    @staticmethod
    def test_code_block_with_json_lang():
        """```json 代码块应正确提取内容。"""
        response = '```json\n{"name": "Alice", "age": 30}\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"name": "Alice", "age": 30}

    @staticmethod
    def test_code_block_without_lang():
        """不带 json 语言标识的 ``` 代码块也应正确提取。"""
        response = '```\n{"city": "Shanghai"}\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"city": "Shanghai"}

    @staticmethod
    def test_code_block_with_extra_whitespace():
        """代码块内有额外空白时应正确提取并 strip。"""
        response = '```json\n\n  {"key": "value"}  \n\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"key": "value"}

    @staticmethod
    def test_code_block_multiline_json():
        """多行 JSON 代码块应正确提取。"""
        response = '```json\n{\n  "name": "Bob",\n  "age": 25\n}\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"name": "Bob", "age": 25}

    @staticmethod
    def test_code_block_with_surrounding_text():
        """代码块前后有额外文本时应只提取代码块内容。"""
        response = 'Here is the result:\n```json\n{"status": "ok"}\n```\nDone.'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"status": "ok"}


class TestParseLlmResponsePlainJson:
    """parse_llm_response — 无 markdown 代码块的纯 JSON。"""

    @staticmethod
    def test_plain_json():
        """无 ``` 标记的纯 JSON 应直接解析。"""
        response = '{"name": "Charlie", "age": 40}'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"name": "Charlie", "age": 40}

    @staticmethod
    def test_plain_json_with_null_filtered():
        """值为 null 的键应被过滤掉。"""
        response = '{"name": "Dave", "nickname": null}'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"name": "Dave"}

    @staticmethod
    def test_code_block_json_with_null_filtered():
        """``` 代码块内值为 null 的键也应被过滤。"""
        response = '```json\n{"name": "Eve", "nickname": null}\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"name": "Eve"}


class TestParseLlmResponseBooleanReplace:
    """parse_llm_response — true/false 替换为 True/False。"""

    @staticmethod
    def test_json_with_true_false():
        """JSON 中的 true/false 应被替换后正确解析。"""
        response = '{"enabled": true, "disabled": false}'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"enabled": True, "disabled": False}

    @staticmethod
    def test_code_block_json_with_true_false():
        """``` 代码块内的 true/false 也应被正确替换。"""
        response = '```json\n{"active": true, "archived": false}\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"active": True, "archived": False}


class TestParseLlmResponseEdgeCases:
    """parse_llm_response — 边界场景与回归测试。"""

    @staticmethod
    def test_empty_string_response():
        """空字符串响应应返回空 dict。"""
        extractor = _make_extractor()
        result = extractor.parse_llm_response("")
        assert result == {}

    @staticmethod
    def test_invalid_json_returns_empty():
        """无法解析的内容应返回空 dict。"""
        extractor = _make_extractor()
        result = extractor.parse_llm_response("not a json at all")
        assert result == {}

    @staticmethod
    def test_code_block_invalid_json_returns_empty():
        """代码块内不是有效 JSON 时应返回空 dict。"""
        response = '```json\nnot valid json\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {}

    @staticmethod
    def test_empty_code_block_regression():
        """回归测试：修复前正则缺少 ``` 边界，非贪婪匹配返回空字符串导致解析失败。

        修复前正则: r"(?:json)?\\s*([\\s\\S]*?)\\s*"
        - 缺少开头的 ``` 和结尾的 ```
        - 非贪婪 [\\s\\S]*? 在位置0匹配零个字符
        - group(1) 返回 "" → cleaned_response = "" → JSONDecodeError

        修复后正则: r"```(?:json)?\\s*([\\s\\S]*?)\\s*```"
        - 正确匹配 ```...``` 之间的内容
        """
        response = '```json\n{"field": "value"}\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        # 修复前会返回 {} (因正则匹配到空字符串)，修复后正确解析
        assert result == {"field": "value"}

    @staticmethod
    def test_multiple_code_blocks():
        """存在多个代码块时，应提取第一个匹配的内容。"""
        response = (
            '```json\n{"first": 1}\n```\n'
            'some text\n'
            '```\n{"second": 2}\n```'
        )
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"first": 1}

    @staticmethod
    def test_nested_braces_in_code_block():
        """代码块内 JSON 含嵌套大括号时应正确解析。"""
        response = '```json\n{"data": {"inner": "value"}}\n```'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"data": {"inner": "value"}}

    @staticmethod
    def test_none_value_string_filtered():
        """字符串值 "None" (不区分大小写) 应被过滤。"""
        response = '{"name": "Frank", "opt": "none"}'
        extractor = _make_extractor()
        result = extractor.parse_llm_response(response)
        assert result == {"name": "Frank"}
