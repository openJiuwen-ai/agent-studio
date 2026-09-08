#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Plugin Param class"""

from typing import Any, List

from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.types import Type, ValueTypeEnum
from jiuwen.plugin.common.exception import PluginCommonException

TYPE = "type"
RESULTS = "results"
DESCRIPTION = "description"
SCHEMA = "schema"
VISIBLE = "visible"
NAME = "name"
PARAMETERS = "parameters"
WORKFLOW_NAME = "workflowName"
WORKFLOW_PROMPT = "无需提供properties以外的参数信息"
QUERY_DESC = "用户输入的query信息"


class Param:
    """Plugin parameter"""

    def __init__(
        self,
        name,
        description,
        param_type=None,
        default_value=None,
        required=True,
        visible=True,
        level=0,
        schema=None,
        **kwargs,
    ):
        if name:
            self.name: str = name
        else:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message="Plugin Param's name cannot be empty.",
            )
        # 插件参数描述可以为空
        if description is None:
            description = ""
        self.description: str = description
        param_type = param_type if param_type else "string"
        self.type: str = Type(param_type).json_schema_type.value
        self.default_value: Any = default_value
        if default_value:
            Param.validate_default_value(self.type, default_value)
        self.required: bool = required
        self.visible: bool = visible
        self.method: str = kwargs.get("method", "Body")
        self.actual_type: str = kwargs.get("actual_type", "")
        if level > 0:
            self.level: int = level
        allow_schema_is_empty = kwargs.get("allow_schema_is_empty", False)
        if allow_schema_is_empty:
            schema_is_invalid = not isinstance(schema, list) or schema is None
        else:
            schema_is_invalid = not schema
        if ValueTypeEnum.is_object(self.type) and schema_is_invalid:
            raise PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=f"The schema field is missing for object parameter '{name}'.",
            )
        if schema is not None:
            self.schema: list = self._format_schema(schema)
        else:
            self.schema = []

    @staticmethod
    def validate_default_value(type_string: str, default_value: Any):
        """Validate whether the default value matches the given type."""
        if ValueTypeEnum.is_nested_array(type_string):
            main_type, sub_type = ValueTypeEnum.split_nested_type(type_string)
        else:
            main_type, sub_type = Type(type_string).json_schema_type, None
        type_check = {
            "string": lambda x: isinstance(x, str),
            "integer": lambda x: isinstance(x, int),
            "number": lambda x: isinstance(x, (int, float)),
            "boolean": lambda x: isinstance(x, bool),
            "object": lambda x: isinstance(x, dict),
            "array": lambda x: isinstance(x, list),
        }
        # object的default value也是一个list
        if sub_type is None:
            if not type_check.get(main_type.value)(default_value):
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message=f"Default value 'default_value' does not match the type for {main_type.value}.",
                )
        else:
            if not isinstance(default_value, list):
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="Default value 'default_value' must be a array.",
                )
            if not all(type_check.get(sub_type.value)(item) for item in default_value):
                raise PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message=f"Not all items in the default value list match the type for {sub_type.value}.",
                )

    @staticmethod
    def format_functions_for_complex(params: List["Param"], properties: dict):
        """format complex type to json schema"""
        required = []
        for param in params:
            if not param.visible:
                continue
            if param.required:
                required.append(param.name)
            param_type = param.type
            if ValueTypeEnum.is_object(param_type):
                properties[param.name] = {}
                properties[param.name]["description"] = param.description
                if ValueTypeEnum.is_nested_array(param_type):
                    properties[param.name]["type"] = "array"
                    properties[param.name]["items"] = (
                        Param.format_functions_for_complex(param.schema, {})
                    )
                else:
                    properties[param.name]["type"] = "object"
                    properties[param.name]["properties"] = (
                        Param.format_functions_for_complex(param.schema, {})
                    )
            elif ValueTypeEnum.is_nested_array(param_type):
                properties[param.name] = {}
                properties[param.name]["description"] = param.description
                properties[param.name]["type"] = "array"
                _, sub_type = ValueTypeEnum.split_nested_type(param_type)
                properties[param.name]["items"] = {
                    DESCRIPTION: param.description,
                    TYPE: sub_type.value,
                }
            else:
                properties[param.name] = {
                    DESCRIPTION: param.description,
                    TYPE: param_type,
                }
            properties["required"] = required
        return properties

    @staticmethod
    def format_functions(tool, **kwargs):
        """format function info for LLM"""
        properties = {}
        params = tool.params
        properties = Param.format_functions_for_complex(params, properties)
        required = properties.pop("required", [])
        # 处理工具名的特殊规则
        tool_name = tool.name
        format_tool_name = tool_name
        if "#*" in tool_name:  # 处理工具名称中的后续字符问题
            split_list = tool_name.split("#*", 1)
            if split_list:
                format_tool_name = split_list[0].strip()
        function = dict(name=format_tool_name, description=tool.description)
        if format_tool_name == "python_interpreter":
            function.update(
                dict(parameters=dict(type="string", description="python代码"))
            )
        else:
            function.update(
                dict(
                    parameters=dict(
                        type="object", properties=properties, required=required
                    )
                )
            )

        output_properties = {}
        output_params = tool.response if hasattr(tool, "response") else []
        for param in output_params:
            output_properties[param.name] = {
                DESCRIPTION: param.description,
                TYPE: param.type,
            }
        if hasattr(tool, "principle") and tool.principle:
            function["principle"] = tool.principle
        if (
            output_properties and RESULTS in output_properties
        ):  # 只添加输出结果中的"results"字段
            function[RESULTS] = output_properties[RESULTS]
        return function

    @staticmethod
    def _format_schema(schema: list):
        params = []
        for item in schema:
            if isinstance(item, dict):
                if (
                    ValueTypeEnum.is_object(item.get("type", "string"))
                    and "schema" not in item
                ):
                    raise PluginCommonException(
                        code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                        message=(
                            f"The schema field is missing for object parameter "
                            f"'{item.get('name')}'."
                        ),
                    )
                sub_schema = item.get("schema", [])
                sub_params = Param._format_schema(sub_schema) if sub_schema else []
                param_kwargs = {
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "param_type": item.get("type"),
                    "required": item.get("required", True),
                    "visible": item.get("visible", True),
                    "method": item.get("method", "Body"),
                    "default_value": item.get("default_value"),
                }
                if sub_params:
                    param_kwargs["schema"] = sub_params
                params.append(Param(**param_kwargs))
            if isinstance(item, Param):
                params.append(item)
        return params
