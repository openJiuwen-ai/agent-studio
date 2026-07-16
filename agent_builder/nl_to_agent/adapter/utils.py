# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
from typing import List

import yaml
from agent_builder.adapter.logger_bridge import logger

AGENT_BUILDER_SCHEMA_INFO = "versatile_schema_info"
COMPONETS_YAML = "componets.yaml"
BUILT_IN_EXAMPLES = "built_in_examples"
USER_EXAMPLES = "user_examples"


def parse_adapter_info():
    """解析节点schema信息"""
    # get file path
    current_file_path = __file__
    current_dir = os.path.dirname(current_file_path)
    components_dir = os.path.join(
        current_dir, AGENT_BUILDER_SCHEMA_INFO, COMPONETS_YAML
    )  # 节点
    built_in_examples_dir = os.path.join(
        current_dir, AGENT_BUILDER_SCHEMA_INFO, BUILT_IN_EXAMPLES
    )  # 内置模板

    # 用户路径
    user_examples_path = os.path.join(
        current_dir, AGENT_BUILDER_SCHEMA_INFO, USER_EXAMPLES
    )  # 用户模板

    # get components & schema
    components_dict = _get_yaml_dict(components_dir)

    components = _format_component_as_inline_prompt(components_dict)  # get components
    schema = _format_schema_as_inline_prompt(components_dict)  # get schema

    # get examples
    # 导入内置markdown模板

    list_markdown = _load_examples_from_directory(built_in_examples_dir)

    # 导入用户自定义模板
    if user_examples_path:
        user_examples = _load_examples_from_directory(user_examples_path)
        list_markdown.extend(user_examples)

    examples = _build_prompt_with_xml(list_markdown)  # get examples

    return {"components": components, "examples": examples, "schema": schema}


def _get_markdown_str(file_path: str) -> str:
    try:
        # 'r' 代表读取模式 (read)
        # 'encoding='utf-8'' 是为了正确处理中文
        with open(file_path, "r", encoding="utf-8") as f:
            # .read() 会读取文件的全部内容
            # 并将其存储为一个包含所有换行符 (\n) 的字符串
            markdown_content = f.read()
    except FileNotFoundError:
        logger.warning(f"Error: File not found. '{file_path}'")
    except Exception as e:
        logger.warning(f"Error reading file: {e}")
    return markdown_content


def _get_yaml_dict(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as config_file:
        yaml_dict = yaml.safe_load(config_file)
    return yaml_dict


def _build_prompt_with_xml(examples: list) -> str:
    prompt_parts = []
    # 循环遍历列表中的每个 markdown 字符串
    for md_content in examples:
        # 将每个内容格式化并包裹在 <example> 标签中
        formatted_part = f"<example>\n{md_content}</example>"
        prompt_parts.append(formatted_part)

    # 使用两个换行符（一个空行）将所有部分连接成一个大字符串
    return "\n".join(prompt_parts)


def _load_examples_from_directory(directory_path: str) -> List[str]:
    """
    扫描指定目录，读取所有.md 文件的内容，并返回按字母顺序排序的字符串列表。
    参数：
    directory_path (str)：包含.md 示例文件的文件夹路径。
    返回值：
    List[str]：一个列表，其中每个元素都是一个.md 文件的全部内容。
    异常：
    FileNotFoundError：如果目录不存在。
    """
    example_list = []
    if not os.path.isdir(directory_path):
        logger.warning(f"Example directory not found: {directory_path}")
        return example_list

    # 关键：sorted() 保证了文件是按名称顺序读取的
    try:
        filenames = sorted(os.listdir(directory_path))
    except Exception as e:
        raise Exception(
            f"Unable to list directory contents {directory_path}: {e}"
        ) from e

    for filename in filenames:
        # 确保我们只读取 Markdown 文件
        if filename.endswith(".md"):
            file_path = os.path.join(directory_path, filename)

            try:
                # 使用我们之前讨论过的 'utf-8' 编码读取文件
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                example_list.append(content)
            except Exception as e:
                # 即使单个文件读取失败，也不要停止，而是打印一个警告
                logger.warning(f"Warning: Unable to read file {file_path}: {e}")

    return example_list


def _format_component_as_inline_prompt(schema: dict) -> str:
    """
    将 components 字典格式化为一行一个的、紧凑的 Markdown 字符串。

    输出格式:
    **{name}**("type": "{type}")：{description}

    参数:
    schema (dict): 包含组件信息的字典，每个组件有 name, type 和 description 键。

    返回:
    str: 格式化后的 Markdown 字符串，每个组件信息占一行。
    """

    prompt_parts = []

    for key, details in schema.items():
        # 1. 获取 Name
        name_to_display = details.get("name", key)

        # 清理 "'开始'" 这样多余的引号
        if isinstance(name_to_display, str):
            name_to_display = name_to_display.strip("'")

        # 获取 Type 和 Description
        # 使用 .get() 避免 KeyError，如果键不存在则返回默认值
        item_type = details.get("type", "")
        item_description = details.get("description", "无描述")

        # 按格式拼接字符串
        line = f'**{name_to_display}**("type": "{item_type}")：{item_description}'

        prompt_parts.append(line)

    # 使用两个换行符 (一个空行) 来分隔每个条目
    return (
        "\n".join(prompt_parts)
        + "\n"
        + "上述这些节点可以组合使用，以构建复杂的工作流，实现多种功能。"
    )


def _format_schema_as_inline_prompt(schema_dict: dict) -> str:
    """
    将 schema 字典格式化为一行一个的、紧凑的 Markdown 字符串。

    输出格式:
    {name}：{schema_description}
    ```json
    { ... example ... }
    ```
    """
    prompt_parts = []

    for key, details in schema_dict.items():
        # 获取 Name
        name_to_display = details.get("name", key)

        if isinstance(name_to_display, str):
            name_to_display = name_to_display.strip("'")
        # 拼接字符串
        line = f"{name_to_display}节点："
        # 检查并获取嵌套的 'schema' 字段 (它是一个字典)
        nested_schema = details.get("schema")

        # 确保 nested_schema 存在并且是一个字典
        if nested_schema and isinstance(nested_schema, dict):
            # 获取 schema description
            schema_desc = nested_schema.get("description")
            if schema_desc:
                # 换行并添加 Schema 描述
                line += f"{schema_desc}"

            # 获取 schema example
            schema_example = nested_schema.get("example")
            if schema_example:
                # 确保 example 是干净的字符串
                clean_example = str(schema_example).strip()

                # 换行并添加 Example (使用 Markdown JSON 代码块)
                line += f"\n```json\n{clean_example}\n```"

        prompt_parts.append(line)

    # 使用单个换行符分隔每个条目，并在末尾添加总结
    return "\n\n".join(prompt_parts)


if __name__ == "__main__":
    schema_config_dict = parse_adapter_info()
    logger.info(schema_config_dict)
