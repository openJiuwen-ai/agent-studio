#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""adapter.utils 单元测试"""

from dataclasses import dataclass
from unittest.mock import MagicMock, mock_open, patch

import pytest
from agent_builder.nl_to_agent.adapter.utils import (
    _build_prompt_with_xml,
    _format_component_as_inline_prompt,
    _format_schema_as_inline_prompt,
    _get_markdown_str,
    _get_yaml_dict,
    _load_examples_from_directory,
    parse_adapter_info,
)


@dataclass
class AdapterMocks:
    yaml: MagicMock
    comp: MagicMock
    schema: MagicMock
    load: MagicMock
    build: MagicMock


@pytest.fixture
def adapter_mocks():
    with (
        patch("agent_builder.nl_to_agent.adapter.utils._get_yaml_dict", return_value={"n1": {"name": "A"}}) as mock_yaml,
        patch("agent_builder.nl_to_agent.adapter.utils._format_component_as_inline_prompt", return_value="comp_result") as mock_comp,
        patch("agent_builder.nl_to_agent.adapter.utils._format_schema_as_inline_prompt", return_value="schema_result") as mock_schema,
        patch("agent_builder.nl_to_agent.adapter.utils._load_examples_from_directory", return_value=["ex1"]) as mock_load,
        patch("agent_builder.nl_to_agent.adapter.utils._build_prompt_with_xml", return_value="xml_output") as mock_build,
    ):
        yield AdapterMocks(
            yaml=mock_yaml,
            comp=mock_comp,
            schema=mock_schema,
            load=mock_load,
            build=mock_build,
        )


class TestBuildPromptWithXml:
    """_build_prompt_with_xml 函数测试"""

    @staticmethod
    def test_empty_list_returns_empty_string():
        """空列表返回空字符串"""
        result = _build_prompt_with_xml([])
        assert result == ""

    @staticmethod
    def test_single_item_wrapped_in_xml():
        """单个示例被 <example> 标签包裹"""
        result = _build_prompt_with_xml(["hello"])
        assert result == "<example>\nhello</example>"

    @staticmethod
    def test_multiple_items_joined_by_newline():
        """多个示例各自包裹后用换行连接"""
        result = _build_prompt_with_xml(["aaa", "bbb", "ccc"])
        expected = (
            "<example>\naaa</example>\n"
            "<example>\nbbb</example>\n"
            "<example>\nccc</example>"
        )
        assert result == expected

    @staticmethod
    def test_content_with_newlines_preserved():
        """示例内容中的换行符被保留"""
        result = _build_prompt_with_xml(["line1\nline2"])
        assert result == "<example>\nline1\nline2</example>"


class TestGetMarkdownStr:
    """_get_markdown_str 函数测试"""

    @patch("agent_builder.nl_to_agent.adapter.utils.open", mock_open(read_data="# 标题\n内容"))
    @staticmethod
    def test_reads_file_content(self):
        """正常读取文件内容"""
        result = _get_markdown_str("/fake/path.md")
        assert result == "# 标题\n内容"

    @patch("agent_builder.nl_to_agent.adapter.utils.logger")
    @patch("agent_builder.nl_to_agent.adapter.utils.open", side_effect=FileNotFoundError)
    @staticmethod
    def test_file_not_found_logs_warning(self, mock_file, mock_logger):
        """文件不存在时记录警告日志"""
        with pytest.raises(UnboundLocalError):
            _get_markdown_str("/nonexistent.md")
        mock_logger.warning.assert_called_once()

    @patch("agent_builder.nl_to_agent.adapter.utils.logger")
    @patch("agent_builder.nl_to_agent.adapter.utils.open", side_effect=PermissionError("no access"))
    @staticmethod
    def test_other_exception_logs_warning(self, mock_file, mock_logger):
        """其他异常时记录警告日志"""
        with pytest.raises(UnboundLocalError):
            _get_markdown_str("/fake/path.md")
        mock_logger.warning.assert_called_once()


class TestGetYamlDict:
    """_get_yaml_dict 函数测试"""

    @patch("agent_builder.nl_to_agent.adapter.utils.yaml.safe_load", return_value={"key": "value"})
    @patch("agent_builder.nl_to_agent.adapter.utils.open", mock_open(read_data="key: value"))
    @staticmethod
    def test_returns_yaml_dict(self, mock_safe_load):
        """正常返回 YAML 字典"""
        result = _get_yaml_dict("/fake/componets.yaml")
        assert result == {"key": "value"}

    @patch("agent_builder.nl_to_agent.adapter.utils.yaml.safe_load", return_value={})
    @patch("agent_builder.nl_to_agent.adapter.utils.open", mock_open(read_data=""))
    @staticmethod
    def test_empty_yaml_returns_empty_dict(self, mock_safe_load):
        """空 YAML 文件返回空字典"""
        result = _get_yaml_dict("/fake/empty.yaml")
        assert result == {}

    @patch("agent_builder.nl_to_agent.adapter.utils.yaml.safe_load", return_value={"nodes": {"a": 1, "b": 2}})
    @patch("agent_builder.nl_to_agent.adapter.utils.open", mock_open(read_data="nodes:\n  a: 1\n  b: 2"))
    @staticmethod
    def test_nested_yaml_dict(self, mock_safe_load):
        """嵌套 YAML 结构正确返回"""
        result = _get_yaml_dict("/fake/nested.yaml")
        assert "nodes" in result
        assert result["nodes"]["a"] == 1


class TestLoadExamplesFromDirectory:
    """_load_examples_from_directory 函数测试"""

    @patch("agent_builder.nl_to_agent.adapter.utils.os.path.isdir", return_value=False)
    @patch("agent_builder.nl_to_agent.adapter.utils.logger")
    @staticmethod
    def test_nonexistent_directory_returns_empty_list(self, mock_logger, mock_isdir):
        """目录不存在时返回空列表并记录警告"""
        result = _load_examples_from_directory("/nonexistent/dir")
        assert result == []
        mock_logger.warning.assert_called_once()

    @patch(
        "agent_builder.nl_to_agent.adapter.utils.open",
        mock_open(read_data="example content"),
    )
    @patch("agent_builder.nl_to_agent.adapter.utils.os.listdir", return_value=["a.md", "b.md"])
    @patch("agent_builder.nl_to_agent.adapter.utils.os.path.isdir", return_value=True)
    @staticmethod
    def test_reads_md_files_sorted(self, mock_isdir, mock_listdir):
        """按字母顺序读取 .md 文件"""
        result = _load_examples_from_directory("/fake/examples")
        assert len(result) == 2
        assert all(item == "example content" for item in result)

    @patch("agent_builder.nl_to_agent.adapter.utils.os.listdir", return_value=["a.txt", "b.json"])
    @patch("agent_builder.nl_to_agent.adapter.utils.os.path.isdir", return_value=True)
    @staticmethod
    def test_ignores_non_md_files(self, mock_isdir, mock_listdir):
        """忽略非 .md 文件"""
        result = _load_examples_from_directory("/fake/examples")
        assert result == []

    @patch("agent_builder.nl_to_agent.adapter.utils.os.path.isdir", return_value=True)
    @patch("agent_builder.nl_to_agent.adapter.utils.os.listdir", return_value=["c.md", "a.md", "b.md"])
    @patch("agent_builder.nl_to_agent.adapter.utils.open", mock_open(read_data="content"))
    @staticmethod
    def test_files_sorted_alphabetically(self, mock_listdir, mock_isdir):
        """文件按字母顺序排序"""
        _load_examples_from_directory("/fake/examples")
        filenames = sorted(["c.md", "a.md", "b.md"])
        assert filenames == ["a.md", "b.md", "c.md"]

    @patch("agent_builder.nl_to_agent.adapter.utils.logger")
    @patch(
        "agent_builder.nl_to_agent.adapter.utils.open",
        side_effect=Exception("read error"),
    )
    @patch("agent_builder.nl_to_agent.adapter.utils.os.listdir", return_value=["bad.md"])
    @patch("agent_builder.nl_to_agent.adapter.utils.os.path.isdir", return_value=True)
    @staticmethod
    def test_single_file_error_logs_warning_and_continues(self, mock_isdir, mock_listdir, mock_file, mock_logger):
        """单个文件读取失败时记录警告并继续"""
        result = _load_examples_from_directory("/fake/examples")
        assert result == []
        mock_logger.warning.assert_called_once()

    @patch("agent_builder.nl_to_agent.adapter.utils.os.listdir", side_effect=Exception("listdir failed"))
    @patch("agent_builder.nl_to_agent.adapter.utils.os.path.isdir", return_value=True)
    @staticmethod
    def test_listdir_exception_raises(self, mock_isdir, mock_listdir):
        """os.listdir 异常时抛出异常"""
        with pytest.raises(Exception, match="Unable to list directory contents"):
            _load_examples_from_directory("/fake/examples")


class TestFormatComponentAsInlinePrompt:
    """_format_component_as_inline_prompt 函数测试"""

    @staticmethod
    def test_basic_schema_formatting():
        """基本 schema 字典格式化"""
        schema = {
            "node1": {"name": "开始节点", "type": "start", "description": "流程的起始节点"}
        }
        result = _format_component_as_inline_prompt(schema)
        assert '**开始节点**("type": "start")：流程的起始节点' in result

    @staticmethod
    def test_missing_name_uses_key():
        """缺少 name 时使用字典键"""
        schema = {"my_node": {"type": "end", "description": "结束节点"}}
        result = _format_component_as_inline_prompt(schema)
        assert '**my_node**("type": "end")：结束节点' in result

    @staticmethod
    def test_missing_type_defaults_empty():
        """缺少 type 时默认为空字符串"""
        schema = {"node1": {"name": "节点1", "description": "描述"}}
        result = _format_component_as_inline_prompt(schema)
        assert '**节点1**("type": "")：描述' in result

    @staticmethod
    def test_missing_description_defaults_to_no_desc():
        """缺少 description 时默认为"无描述" """
        schema = {"node1": {"name": "节点1", "type": "process"}}
        result = _format_component_as_inline_prompt(schema)
        assert '**节点1**("type": "process")：无描述' in result

    @staticmethod
    def test_name_with_extra_quotes_stripped():
        """name 中多余的引号被去除"""
        schema = {"node1": {"name": "'开始'", "type": "start", "description": "描述"}}
        result = _format_component_as_inline_prompt(schema)
        assert '**开始**("type": "start")：描述' in result

    @staticmethod
    def test_multiple_components_each_on_line():
        """多个组件各占一行"""
        schema = {
            "n1": {"name": "A", "type": "t1", "description": "d1"},
            "n2": {"name": "B", "type": "t2", "description": "d2"},
        }
        result = _format_component_as_inline_prompt(schema)
        assert '**A**("type": "t1")：d1' in result
        assert '**B**("type": "t2")：d2' in result

    @staticmethod
    def test_summary_line_appended():
        """末尾追加总结行"""
        schema = {"n1": {"name": "A", "type": "t1", "description": "d1"}}
        result = _format_component_as_inline_prompt(schema)
        assert result.endswith("上述这些节点可以组合使用，以构建复杂的工作流，实现多种功能。")

    @staticmethod
    def test_empty_schema_returns_summary_only():
        """空 schema 只返回总结行"""
        result = _format_component_as_inline_prompt({})
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0] == ""
        assert "上述这些节点可以组合使用" in lines[1]


class TestFormatSchemaAsInlinePrompt:
    """_format_schema_as_inline_prompt 函数测试"""

    @staticmethod
    def test_basic_schema_with_description_and_example():
        """包含 description 和 example 的嵌套 schema"""
        schema = {
            "node1": {
                "name": "LLM",
                "schema": {
                    "description": "大模型节点描述",
                    "example": '{"model": "gpt-4"}',
                },
            }
        }
        result = _format_schema_as_inline_prompt(schema)
        assert "LLM节点：大模型节点描述" in result
        assert "```json" in result
        assert '{"model": "gpt-4"}' in result
        assert "```" in result

    @staticmethod
    def test_schema_without_nested_schema():
        """没有嵌套 schema 字段时只输出节点名称行"""
        schema = {"node1": {"name": "简单节点"}}
        result = _format_schema_as_inline_prompt(schema)
        assert result == "简单节点节点："

    @staticmethod
    def test_schema_with_description_only():
        """嵌套 schema 只有 description 没有 example"""
        schema = {
            "node1": {
                "name": "节点A",
                "schema": {"description": "仅有描述"},
            }
        }
        result = _format_schema_as_inline_prompt(schema)
        assert "节点A节点：仅有描述" in result
        assert "```json" not in result

    @staticmethod
    def test_schema_with_example_only():
        """嵌套 schema 只有 example 没有 description"""
        schema = {
            "node1": {
                "name": "节点B",
                "schema": {"example": '{"key": "val"}'},
            }
        }
        result = _format_schema_as_inline_prompt(schema)
        assert "节点B节点：" in result
        assert "```json" in result
        assert '{"key": "val"}' in result

    @staticmethod
    def test_missing_name_uses_key():
        """缺少 name 时使用字典键"""
        schema = {"my_key": {"schema": {"description": "用键名"}}}
        result = _format_schema_as_inline_prompt(schema)
        assert "my_key节点：用键名" in result

    @staticmethod
    def test_name_with_quotes_stripped():
        """name 中多余的引号被去除"""
        schema = {"node1": {"name": "'开始'", "schema": {"description": "描述"}}}
        result = _format_schema_as_inline_prompt(schema)
        assert "开始节点：描述" in result

    @staticmethod
    def test_multiple_entries_separated_by_double_newline():
        """多个条目之间用双换行分隔"""
        schema = {
            "n1": {"name": "A", "schema": {"description": "d1"}},
            "n2": {"name": "B", "schema": {"description": "d2"}},
        }
        result = _format_schema_as_inline_prompt(schema)
        assert "A节点：d1\n\nB节点：d2" in result

    @staticmethod
    def test_empty_schema_returns_empty_string():
        """空 schema 字典返回空字符串"""
        result = _format_schema_as_inline_prompt({})
        assert result == ""


class TestParseAdapterInfo:
    """parse_adapter_info 函数测试"""

    @staticmethod
    def test_returns_dict_with_three_keys(adapter_mocks):
        """返回包含 components、examples、schema 三个键的字典"""
        result = parse_adapter_info()
        assert "components" in result
        assert "examples" in result
        assert "schema" in result

    @staticmethod
    def test_components_from_format_component(adapter_mocks):
        """components 取自 _format_component_as_inline_prompt"""
        result = parse_adapter_info()
        assert result["components"] == "comp_result"

    @staticmethod
    def test_schema_from_format_schema(adapter_mocks):
        """schema 取自 _format_schema_as_inline_prompt"""
        result = parse_adapter_info()
        assert result["schema"] == "schema_result"

    @staticmethod
    def test_examples_from_build_prompt(adapter_mocks):
        """examples 取自 _build_prompt_with_xml"""
        result = parse_adapter_info()
        assert result["examples"] == "xml_output"

    @staticmethod
    def test_loads_builtin_and_user_examples(adapter_mocks):
        """加载内置模板和用户模板"""
        adapter_mocks.load.return_value = ["builtin_ex"]
        parse_adapter_info()
        assert adapter_mocks.load.call_count == 2

    @staticmethod
    def test_yaml_dict_passed_to_formatters(adapter_mocks):
        """_get_yaml_dict 的结果传递给两个格式化函数"""
        parse_adapter_info()
        adapter_mocks.comp.assert_called_once_with({"n1": {"name": "A"}})
        adapter_mocks.schema.assert_called_once_with({"n1": {"name": "A"}})

    @staticmethod
    def test_user_examples_merged_into_list(adapter_mocks):
        """用户模板合并到内置模板列表中"""
        adapter_mocks.yaml.return_value = {}
        adapter_mocks.load.side_effect = [["builtin"], ["user"]]
        parse_adapter_info()
        adapter_mocks.build.assert_called_once_with(["builtin", "user"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])