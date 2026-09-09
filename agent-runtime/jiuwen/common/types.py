#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from enum import Enum


class ValueTypeEnum(Enum):
    """
    Enumeration type for the plugin.
    """

    # 基本类型
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"

    # 嵌套类型
    ARRAY_STRING = "array<string>"
    ARRAY_NUMBER = "array<number>"
    ARRAY_INTEGER = "array<integer>"
    ARRAY_BOOLEAN = "array<boolean>"
    ARRAY_OBJECT = "array<object>"

    @staticmethod
    def is_object(value: str):
        """检查类型是否为object或array<object>类型"""
        return Type(value).json_schema_type.value in ("object", "array<object>")

    @staticmethod
    def split_nested_type(type_string: str):
        """拆分嵌套类型"""
        main_type, sub_type = None, None
        if ValueTypeEnum.is_nested_array(type_string):
            main_type_string, sub_type_string = (
                type_string.split("<")[0],
                type_string.split("<")[1].rstrip(">"),
            )
            main_type, sub_type = (
                Type(main_type_string).json_schema_type,
                Type(sub_type_string).json_schema_type,
            )
        return main_type, sub_type

    @classmethod
    def is_nested_array(cls, value: str):
        """检查类型是否为数组嵌套类型"""
        is_array_prefix = value.startswith(cls.ARRAY.value)
        has_array_alias = any(
            value.startswith(alias) for alias in Type.type_aliases[cls.ARRAY.value]
        )
        return value != cls.ARRAY.value if is_array_prefix else has_array_alias

    @classmethod
    def from_string(cls, type_string: str):
        """从字符串创建 ValueTypeEnum 枚举"""
        if cls.is_nested_array(type_string):
            _, sub_type = ValueTypeEnum.split_nested_type(type_string)
            array_enum_map = {
                ValueTypeEnum.STRING: cls.ARRAY_STRING,
                ValueTypeEnum.NUMBER: cls.ARRAY_NUMBER,
                ValueTypeEnum.INTEGER: cls.ARRAY_INTEGER,
                ValueTypeEnum.BOOLEAN: cls.ARRAY_BOOLEAN,
                ValueTypeEnum.OBJECT: cls.ARRAY_OBJECT,
            }
            if sub_type in array_enum_map:
                return array_enum_map[sub_type]
            raise ValueError(f"Invalid type: {type_string}")
        for item in cls:
            if item.value.lower() == type_string.lower():
                return item
        raise ValueError(f"Invalid type: {type_string}")


class Type:
    type_aliases = {
        ValueTypeEnum.STRING.value: ("String", "str", "Str"),
        ValueTypeEnum.NUMBER.value: ("Number", "Float", "float"),
        ValueTypeEnum.INTEGER.value: ("Integer", "int", "Int"),
        ValueTypeEnum.BOOLEAN.value: ("Boolean", "Bool", "bool"),
        ValueTypeEnum.ARRAY.value: ("Array", "List", "list"),
        ValueTypeEnum.OBJECT.value: ("Object", "Map", "map"),
    }
    questioner_aliases = {
        ("String", "str", "Str", "string"): "str",
        ("Number", "Float", "float", "number"): "float",
        ("Integer", "int", "Int", "integer"): "int",
        ("Boolean", "Bool", "bool", "boolean"): "bool",
    }

    def __init__(self, var_type: str):
        self.var_type = var_type
        self.json_schema_type = self._json_schema_type()

    @property
    def jiuwen_ir_type(self):
        """按照jiuwen ir格式转换的类型"""
        return

    @staticmethod
    def transform_questioner_type(
        questioner_output_param_list: list, extracted_key_fields: dict
    ):
        """按照json schema格式强制转换提问器的输出结果，如果转换失败则赋默认值"""
        for key, value in extracted_key_fields.items():
            for questioner_output_param in questioner_output_param_list:
                if key == questioner_output_param.get("id"):
                    if questioner_output_param.get(
                        "type"
                    ) == "string" and not isinstance(value, str):
                        extracted_key_fields[key] = str(value)
                    if questioner_output_param.get(
                        "type"
                    ) == "boolean" and not isinstance(value, bool):
                        try:
                            extracted_key_fields[key] = bool(value)
                        except ValueError:
                            extracted_key_fields[key] = True
                    if questioner_output_param.get(
                        "type"
                    ) == "integer" and not isinstance(value, int):
                        try:
                            extracted_key_fields[key] = int(value)
                        except ValueError:
                            extracted_key_fields[key] = 0
                    if questioner_output_param.get(
                        "type"
                    ) == "number" and not isinstance(value, float):
                        try:
                            extracted_key_fields[key] = float(value)
                        except ValueError:
                            extracted_key_fields[key] = 0.0
        return extracted_key_fields

    def _json_schema_type(self):
        """按照json schema格式转换的类型

        支持联合类型（如 "object | null"、"integer | null"），
        取第一个非 null 的子类型作为主类型。
        """
        # 处理联合类型：取第一个非 null 子类型
        if "|" in self.var_type:
            sub_types = [t.strip() for t in self.var_type.split("|")]
            primary_type = next(
                (t for t in sub_types if t != "null"), None
            )
            if primary_type is None:
                primary_type = "null"
            return Type(primary_type).json_schema_type
        for standard_type, aliases in self.type_aliases.items():
            if self.var_type in aliases:
                return ValueTypeEnum.from_string(standard_type)
        return ValueTypeEnum.from_string(self.var_type)
