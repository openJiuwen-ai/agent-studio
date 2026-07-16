# 永久性覆盖重写九问agent_builder代码中DSL模型相关内容
# 增加了多个函数参数，将请求体的模型信息传入框架内的modelConfig实现模型配置运行时修改
# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import base64
import json
import os
import random
import re
import string
from dataclasses import dataclass, field
from typing import Optional, Literal, List, Dict, Any

import requests
from agent_builder.common.exception.status_code import StatusCode
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.logger_bridge import logger

BRANCH_CONDITION = [
    "not_eq",
    "eq",
    "not_contain",
    "contain",
    "longer_than_or_eq",
    "longer_than",
    "shorter_than_or_eq",
    "shorter_than",
    "is_empty",
    "is_not_empty",
]
AGENT_MANAGER_HOST = os.getenv("AGENT_MANAGER_HOST", "")


def convert_sandbox_to_fg_code(sandbox_code: str) -> str:
    """
    将简单的安全沙箱代码（仅包含业务逻辑）包装成 FunctionGraph 标准代码
    """

    # 1. 定义 FunctionGraph 的标准“壳” (Boilerplate)
    # 这部分负责：导入库、处理Base64、解析HTTP请求、调用main、返回JSON
    # 注意：这里假设你的沙箱代码入口永远是 def main(args):

    fg_template_header = """# -*- coding:utf-8 -*-
import json
import base64

# --- 辅助函数：解析请求参数 ---
def extractRequestParam(rawValue, encoded, defaultValue):
    if encoded and rawValue:
        try:
            # 兼容处理，防止本来就是str报错
            if isinstance(rawValue, bytes):
                rawValue = rawValue.decode("utf-8")
            rawValue = str(base64.b64decode(rawValue), "utf-8")
        except Exception as e:
            print(f"Base64 decode failed: {e}")
    return json.loads(rawValue) if rawValue else defaultValue

# --- 用户业务逻辑区域开始 ---
"""

    fg_template_footer = """
# --- 用户业务逻辑区域结束 ---

# --- 标准 Handler 入口 ---
def handler(event, context):
    \"\"\"
    FunctionGraph 的标准入口函数
    \"\"\"
    # 1. 提取标识：是否经过 Base64 编码 (API 网关触发通常会有)
    isBase64Encoded = event.get('isBase64Encoded', False)

    # 2. 提取 Body (对应沙箱的 inputs/args)
    # 这里的 logic 对应将 HTTP body 转为 main(args) 中的 args
    input_args = extractRequestParam(event.get('body'), isBase64Encoded, {})

    # 4. 调用用户的业务逻辑
    return main(input_args)

"""

    # 3. 拼接：头 + 用户代码 + 尾
    # 确保用户代码能够直接嵌入，并且缩进没有大问题（通常 def main 是顶格写的）
    full_code = fg_template_header + "\n" + sandbox_code + "\n" + fg_template_footer

    return full_code


def get_function_graph_payload(node, function_graph_code):
    # 1. 构建base64代码
    encoded_code = base64.b64encode(function_graph_code.encode("utf-8")).decode("utf-8")
    # 2. 构建 Input Schema (function_input)
    # 对应原代码 _create_code_config(inputs, 'input') 的逻辑变体
    input_properties = {}
    inputs = node.get("parameters", {}).get("inputs", [])
    required_inputs = []

    for item in inputs:
        # 这里简化了 _extract_var_type 的逻辑，假设 item 中已有 type
        prop_name = item.get("name", "")
        prop_type = item.get("type", "string")  # 默认为 string

        input_properties[prop_name] = {
            "description": item.get("description", ""),
            "type": prop_type,
            "default": "",
            "x-hw-default": "",
            "x-hw-label": prop_name,
            "x-hw-visibility": "none",
            "format": "input",  # 示例中的固定值
            "x-hw-format": "input",
            "x-hw-select-options": [],
            # 可以根据需要添加 format 等其他 schema 字段
        }
        if item.get("required", True):  # 假设默认为必填
            required_inputs.append(prop_name)

    function_input = {
        "in": "body",
        "name": "body",
        "required": False,
        "description": "default",
        "schema": {
            "properties": input_properties,
            "required": required_inputs,
            "type": "object",
        },
        "cdm-type": "",
    }

    # 3. 构建 Output Schema (function_output)
    # 对应原代码 _create_code_config(outputs, 'output') 的逻辑变体
    output_properties = {}
    outputs = node.get("parameters", {}).get("outputs", [])
    required_outputs = []

    for item in outputs:
        prop_name = item.get("name", "output")
        prop_type = item.get("type", "string")

        # 目标 JSON 中 output 字段包含特定的 x-hw 扩展字段
        output_properties[prop_name] = {
            "description": item.get("description", "output"),
            "type": prop_type,
            "default": "",
            "x-hw-default": "",
            "x-hw-label": prop_name,
            "x-hw-visibility": "none",
            "format": "input",  # 示例中的固定值
            "x-hw-format": "input",
            "x-hw-select-options": [],
        }
        required_outputs.append(prop_name)

    function_output = {
        "description": "default",
        "schema": {
            "properties": output_properties,
            "required": required_outputs,
            "type": "object",
        },
        "cdm-type": "",
    }

    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))

    # 处理functionName超长问题
    raw_prefix = node.get("id", f"default_{random_str}")
    for p in ["node_code_", "node_"]:
        if raw_prefix.startswith(p):
            raw_prefix = raw_prefix.removeprefix(p)
            break

    clean_prefix = raw_prefix[:27]
    function_name = f"{clean_prefix}_{random_str}"
    function_name = function_name.replace("__", "_").strip("_")

    # 4. 组装最终 Payload
    payload = {
        "dependencies": [],
        "description": node.get("description", "functionGraphdescirbe"),
        "function_name": function_name,  # 使用 ID 或 Name
        "function_input": function_input,
        "function_output": function_output,
        "runtime": "Python3.9",  # 硬编码或从 node 配置读取
        "status": "",
        "type": "function",
        "handler": "mssi.handler",  # 必须与代码中的入口函数一致
        "memory_size": 128,
        "time_out": 30,
        "concurrent_num": 1,
        "code": encoded_code,
        "code_type": "inline",
        "template_version": "v1",
    }

    return payload


class ConvertToEicloud:
    def __init__(self, original_data, plugin_dict, workflow_dict, model_dict):
        self.original_data = original_data
        self.plugin_dict = plugin_dict
        self.workflow_dict = workflow_dict
        self.convert_res = Workflow()
        self.convert_res.nodes = []
        self.convert_res.edges = []
        self.convert_res.layouts = {}
        self.node_dict = {}
        self.model_config_llm = {
            "model_id": model_dict.get("agentBuilder_model_name"),
            "model_name": model_dict.get("model_explicit_name"),
            "model_type": model_dict.get("nl2_model_type"),
            "model_deployment_id": model_dict.get("agentBuilder_model_name"),
            "auth_id": model_dict.get("auth_id"),
        }
        self.metadata = {
            "x_auth_token": model_dict.get("x_auth_token"),
            "workspace_id": model_dict.get("workspace_id"),
            "project_id": model_dict.get("project_id"),
        }

        for node in self.original_data:
            self.node_dict[node["id"]] = node

    @staticmethod
    def _plugin_output_generator(
        schema_str: str, resource_type: str = "plugin"
    ) -> List[Dict[str, Any]]:
        def process_property(
            name: str, prop_schema: Dict[str, Any], is_required: bool
        ) -> Dict[str, Any]:
            """处理单个属性"""
            prop_type = prop_schema.get("type", "")
            description = prop_schema.get("description", "")

            result = {
                "name": name,
                "type": prop_type,
                "description": description,
                "required": is_required,
                "source": "system"
                if resource_type == "workflow" and name == "response_content"
                else "user",
                "schema": [],
                "reflection": False,
                "value": {"default": "", "type": "generated", "hint": ""},
            }

            # 处理 object 类型的嵌套属性
            if prop_type == "object" and "properties" in prop_schema:
                nested_props = prop_schema.get("properties", {})
                nested_required = prop_schema.get("required", [])

                for nested_name, nested_schema in nested_props.items():
                    nested_is_required = nested_name in nested_required
                    nested_prop = process_property(
                        nested_name, nested_schema, nested_is_required
                    )
                    result["schema"].append(nested_prop)

            # 处理 array 类型
            elif prop_type == "array" and "items" in prop_schema:
                items_schema = prop_schema["items"]
                if isinstance(items_schema, dict):
                    if items_schema.get("type") == "object":
                        array_item = process_property("items", items_schema, False)
                        result["schema"].append(array_item)
                    elif items_schema.get("type") in [
                        "string",
                        "integer",
                        "number",
                        "boolean",
                    ]:
                        result["schema"] = {
                            "name": "",
                            "type": items_schema.get("type"),
                        }

            return result

        # 主转换逻辑
        schema = json.loads(schema_str)
        output = []
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        for prop_name, prop_schema in properties.items():
            is_required = prop_name in required_fields
            converted_prop = process_property(prop_name, prop_schema, is_required)
            output.append(converted_prop)

        return output

    @staticmethod
    def _create_intent_output_config():
        """
        生成Intent_detection节点的output的config。固定内容。
        """
        result = [
            {
                "name": "classification_id",
                "type": "integer",
                "description": "intentDetection.outputs_id_description",
                "required": True,
                "source": "system",
                "reflection": False,
                "value": {"type": "generated", "hint": ""},
            },
            {
                "name": "name",
                "type": "string",
                "description": "intentDetection.outputs_name_description",
                "required": True,
                "source": "system",
                "reflection": False,
                "value": {"type": "generated", "hint": ""},
            },
            {
                "name": "result",
                "type": "string",
                "description": "The name of the output classification branch",
                "required": False,
                "source": "system",
                "reflection": False,
                "value": {"type": "generated", "content": "", "hint": ""},
            },
            {
                "name": "reason",
                "type": "string",
                "required": True,
                "source": "system",
                "reflection": False,
                "value": {"type": "generated", "hint": ""},
            },
        ]
        return result

    @staticmethod
    def _extract_var_type(item: dict):
        """
        提取变量类型
        """
        if "array" in item["type"]:
            var_type = "array"
            inner_type = re.findall(r"^array<([^>]+)>", item["type"])[0]
            # 处理 array<object> 类型，生成默认嵌套 schema
            if inner_type == "object":
                var_schema = {"name": "", "type": "object", "schema": []}
            else:
                var_schema = {"name": "", "type": inner_type}
        elif item["type"] == "object":
            # 处理 object 类型，生成默认空对象 schema
            var_type = "object"
            var_schema = []
        else:
            var_type = item["type"]
            var_schema = None
        return {"type": var_type, "schema": var_schema}

    @staticmethod
    def _handle_loop_input(node):
        """
        处理循环输入节点
        """
        return NodeField(id=node["id"], type="LoopInput", name="Loop input")

    @staticmethod
    def _handle_loop_output(node):
        """
        处理循环输出节点
        """
        return NodeField(id=node["id"], type="LoopOutput", name="Loop output")

    def convert(self):
        """
        转换到ei dsl
        """
        self.convert_res.nodes = [self._convert_node(n) for n in self.original_data]
        self._convert_edges()
        self._set_layouts()
        self._set_global_configs()

    def _set_global_configs(self):
        """
        设置全局配置
        """
        self.convert_res.configs["memory"] = []
        for _, node in self.node_dict.items():
            if node["type"] == "SetVariable":
                for variable_detail in node["variables"]:
                    variable = variable_detail.get("name")
                    self.convert_res.configs["memory"].append(
                        {
                            "name": variable[2:-1].split(".")[1]
                            if "${" in variable
                            else variable,
                            "description": variable_detail["description"],
                            "required": True,
                            "type": variable_detail["type"],
                            "source": "pre_defined",
                            "reflection": False,
                            "value": {
                                "type": "generated",
                                "hint": "",
                                "default": variable_detail["default"],
                            },
                            "aging_level": "session",
                            "storage_method": "assignment",
                        }
                    )

    def _determine_ref_value_source(self, input_value_type, ref_value):
        """
        确定输入元素引用值的source
        """
        ref_val_source = "user"
        if input_value_type == "ref":
            ref_node_id, ref_var_name = ref_value[2:-1].split(".", 1)
            if ref_node_id == "memory":
                # 处理全局变量
                ref_val_source = "pre_defined"
            else:
                node_type = self.node_dict[ref_node_id]["type"]
                if node_type == "Start":
                    ref_val_source = "system" if ref_var_name == "query" else "user"
                elif node_type == "Loop":
                    ref_val_source = (
                        "pre_defined"
                        if ref_var_name == "index"
                        or "arr_loop_var" in ref_var_name
                        or "intermediate_loop_var" in ref_var_name
                        else "user"
                    )
                elif node_type == "Workflow":
                    ref_val_source = (
                        "system" if ref_var_name == "response_content" else "user"
                    )
        return ref_val_source

    def _get_input_value(self, variable_value: str):
        """
        提取引用
        """
        if "${" not in variable_value:
            return dict(content=variable_value, hint="", type="literal")

        ref_node_id, ref_var_name = variable_value[2:-1].split(".", 1)
        if ref_node_id == "memory":
            # 处理全局变量
            ref_node_id = [
                node_id for node_id, n in self.node_dict.items() if n["type"] == "Start"
            ][0]
            ref_var_name = f"memory.{ref_var_name}"
        else:
            node_type = self.node_dict[ref_node_id]["type"]
            var_level_list = ref_var_name.split("_of_")[::-1]
            if node_type in ["Plugin", "Workflow"] and len(var_level_list) > 1:
                return_str = ""
                if node_type == "Plugin":
                    resource_id = (
                        self.node_dict[ref_node_id]
                        .get("parameters")
                        .get("configs")
                        .get("apiId")
                    )
                    outputs_dict = self.plugin_dict.get(resource_id).get(
                        "origin_output"
                    )
                else:
                    workflow_id = (
                        self.node_dict[ref_node_id]
                        .get("parameters")
                        .get("configs")
                        .get("workflow_id")
                    )
                    outputs_dict = self.workflow_dict.get(workflow_id).get(
                        "origin_output"
                    )

                for var_name in var_level_list:
                    var_type = outputs_dict.get(var_name).get("type")
                    if var_type == "object":
                        return_str += f"{var_name}."
                        outputs_dict = outputs_dict.get(var_name).get("properties")
                    elif var_type == "array":
                        return_str += f"{var_name}[0]."
                        outputs_dict = (
                            outputs_dict.get(var_name).get("items").get("properties")
                        )
                    else:
                        return_str += f"{var_name}"
                ref_var_name = return_str

        return dict(
            content=dict(
                ref_node_id=ref_node_id,
                ref_var_name=ref_var_name,
                source=self._determine_ref_value_source("ref", variable_value),
            ),
            hint="",
            type="ref",
        )

    def _get_ref_var_type(self, variable_value: str):
        defualt_item = {"type": "string"}
        if "${" not in variable_value:
            return self._extract_var_type(defualt_item)

        ref_node_id, ref_var_name = variable_value[2:-1].split(".", 1)
        if ref_var_name.startswith("arr_loop_var."):
            variable_list = self.node_dict[ref_node_id]["parameters"]["inputs"]
            output_item = next(
                (item for item in variable_list if item.get("name") == "arr_loop_var"),
                defualt_item,
            )
            var_type = self._extract_var_type(output_item)
            # 兼容新的 schema 格式
            schema = var_type.get("schema") or {}
            return {"type": schema.get("type") if schema else "string", "schema": None}

        if ref_var_name.startswith("intermediate_loop_var."):
            variable_list = self.node_dict[ref_node_id]["parameters"]["inputs"]
            output_item = next(
                (
                    item
                    for item in variable_list
                    if item.get("name") == "intermediate_loop_var"
                ),
                defualt_item,
            )
            _, sub_ref_var_name = ref_var_name.split(".", 1)
            sub_output_item = next(
                (
                    item
                    for item in output_item["value"]
                    if isinstance(item, dict) and item.get("name") == sub_ref_var_name
                ),
                defualt_item,
            )
            return self._extract_var_type(sub_output_item)

        if ref_node_id == "memory":
            outputs = []
            memory_var_name = set()
            for _, node in self.node_dict.items():
                if node["type"] != "SetVariable":
                    continue
                for var in node["variables"]:
                    if var["name"] in memory_var_name:
                        continue
                    outputs.append(var)
                    memory_var_name.add(var["name"])
        else:
            outputs = self.node_dict[ref_node_id]["parameters"]["outputs"]
        output_item = next(
            (item for item in outputs if item.get("name") == ref_var_name), defualt_item
        )
        return self._extract_var_type(output_item)

    def _create_start_config(self, configs: list):
        """
        生成start节点outputs的config
        """
        result = []
        for item in configs:
            var_type = self._extract_var_type(item)
            output_field = ConfigField(
                name=item.get("name", ""),
                description=item.get("description", ""),
                source="user",
                type=var_type["type"],
                required=True,
                reflection=False,
                schema=var_type["schema"],
                value={
                    "default": "",
                    "hint": "",
                    "type": "generated",
                },
            )
            result.append(output_field)
        return result

    def _handle_start(self, node):
        """
        处理开始节点
        """
        template_output = ConfigField(
            name="query",
            description="User input",
            source="system",
            type="string",
            field_type="input",
            required=True,
            reflection=False,
            value={"content": "", "hint": "User input", "type": "literal"},
        )
        outputs_filtered = [
            item
            for item in node["parameters"]["outputs"]
            if item.get("name") != "query"
        ]
        return NodeField(
            id=node["id"],
            type="Start",
            name="Start",
            outputs=[template_output] + self._create_start_config(outputs_filtered),
        )

    def _create_intent_input_config(self, input_configs):
        """
        生成Intent_detection节点的input的config。
        """
        result = []
        for item in input_configs:
            var_type = self._extract_var_type(item)
            input_field = ConfigField(
                name=item.get("name", ""),
                description="",
                source="system",
                type=var_type["type"],
                required=False,  # 意图识别required为False
                reflection=False,
                schema=var_type["schema"],
                value=self._get_input_value(item.get("value", "")),
            )
            result.append(input_field)
        return result

    def _handle_intent(self, node):
        """
        处理意图识别节点
        """
        branches = []
        for cond in node["parameters"]["conditions"]:
            category = (
                "Uncertain, other intents"
                if cond["expression"] == "default"
                else cond.get("expression").split(" contain ")[1]
            )
            branches.append({"configs": {"category": category}, "id": cond["branch"]})
            self.convert_res.edges.append(
                EdgeField(
                    branch=cond["branch"],
                    source=node["id"],
                    target=cond["next"],
                )
            )
        intent = NodeField(
            id=node["id"],
            type="IntentDetection",
            name=node["id"],
            branches=branches,
            configs={
                "llm": {
                    "top_p": 0.5,
                    "temperature": 0.5,
                    "max_tokens": 2048,
                    "model": self.model_config_llm,
                },
                "prompt": node["parameters"]["configs"]["prompt"],
                "enable_knowledge": False,
                "chat_history_max_turn": 0,
            },
            inputs=self._create_intent_input_config(node["parameters"]["inputs"]),
            outputs=self._create_intent_output_config(),
        )
        return intent

    def _create_llm_config(self, configs, in_or_out):
        """
        生成LLM节点的input以及output的config
        """
        result = []
        if in_or_out == "input":
            for item in configs:
                var_type = self._extract_var_type(item)
                input_field = ConfigField(
                    name=item.get("name", ""),
                    description="",
                    source="user",  # 输入输出的source均为user。【输入为赋值或引用均为user】
                    type=var_type["type"],
                    required=False,
                    reflection=False,
                    schema=var_type["schema"],
                    value=self._get_input_value(item.get("value", "")),
                )
                result.append(input_field)
        else:
            for item in configs:
                var_type = self._extract_var_type(item)
                output_field = ConfigField(
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    source="user",
                    type=var_type["type"],
                    required=False,
                    reflection=False,
                    schema=var_type["schema"],
                    value={"type": "literal", "content": "", "hint": ""},
                )
                result.append(output_field)
        return result

    def _handle_llm(self, node):
        """
        处理大模型节点
        """
        llm = NodeField(
            id=node["id"],
            type="LLM",
            name=node["id"],
            configs={
                "top_p": 0.5,
                "response_format": "json",
                "template_content": node["parameters"]["configs"]["user_prompt"],
                "system_prompt": node["parameters"]["configs"].get("system_prompt", ""),
                "temperature": 0.5,
                "model": self.model_config_llm,
                "enable_history": False,
            },
            inputs=self._create_llm_config(node["parameters"]["inputs"], "input"),
            outputs=self._create_llm_config(node["parameters"]["outputs"], "output"),
        )
        return llm

    def _create_questioner_config(self, configs, in_or_out):
        """
        生成提问器input以及output的config
        """
        result = []
        if in_or_out == "input":
            for item in configs:
                var_type = self._extract_var_type(item)
                input_field = ConfigField(
                    name=item.get("name", ""),
                    description="",
                    source="user",
                    type=var_type["type"],
                    required=True,
                    reflection=False,
                    schema=var_type["schema"],
                    value=self._get_input_value(item.get("value", "")),
                )
                result.append(input_field)
        else:
            for item in configs:
                var_type = self._extract_var_type(item)
                output_field = ConfigField(
                    name=item.get("name", ""),
                    cn_name=item.get("description", ""),  # 输出时，为输出参数的展示名称
                    description="",
                    source="user",
                    type=var_type["type"],
                    required=True,
                    reflection=True,
                    schema=var_type["schema"],
                    value={"default": "", "hint": "", "type": "generated"},
                    validator=[],
                )
                result.append(output_field)
        return result

    def _handle_questioner(self, node):
        """
        处理提问器节点
        """
        questioner_output = [
            ConfigField(
                name="USER_RESPONSE",
                description="The user input from the most recent conversation",
                required=False,
                source="user",
                type="string",
                value={
                    "content": "",
                    "default": "",
                    "display": None,
                    "hint": "",
                    "type": "literal",
                },
                validator=[],
            ),
            ConfigField(
                name="STATUS",
                description="The status code of the questioner execution",
                required=False,
                source="user",
                type="integer",
                value={
                    "content": "",
                    "default": "",
                    "display": None,
                    "hint": "",
                    "type": "literal",
                },
                validator=[],
            ),
        ]
        questioner = NodeField(
            id=node["id"],
            type="Questioner",
            name=node["id"],
            configs={
                "template_anthropomorphic": False,
                "example_content": "",
                "enum_visible": False,
                "max_tokens": 2048,
                "extra_prompt_for_fields_extraction": "",
                "max_response": 10,
                "auto_ask_template": "",
                "rewrite_chain": [
                    {
                        "type": "rewrite_api",
                        "index": 1,
                        "enabled": False,
                        "args": {"url": ""},
                    }
                ],
                "mode": "effect",
                "top_p": 0.5,
                "extract_fields_from_response": True,
                "with_chat_history": False,
                "temperature": 0.2,
                "question_content": node["parameters"]["configs"]["prompt"],
                "model": self.model_config_llm,
                "allow_node_break": False,
                "allow_node_confirm": False,
            },
            inputs=self._create_questioner_config(
                node["parameters"]["inputs"], "input"
            ),
            outputs=questioner_output
            + self._create_questioner_config(node["parameters"]["outputs"], "output"),
        )
        return questioner

    def _create_condition_content(self, data):
        """
        根据输入情况创建条件内容
        """
        ref_node_id = data[2:-1].split(".")[0]
        ref_var_name = data[2:-1].split(".")[1]
        node_type = self.node_dict[ref_node_id]["type"]
        var_level_list = ref_var_name.split("_of_")[::-1]
        if node_type in ["Plugin", "Workflow"] and len(var_level_list) > 1:
            return_str = ""
            if node_type == "Plugin":
                resource_id = (
                    self.node_dict[ref_node_id]
                    .get("parameters")
                    .get("configs")
                    .get("apiId")
                )
                outputs_dict = self.plugin_dict.get(resource_id).get("origin_output")
            else:
                workflow_id = (
                    self.node_dict[ref_node_id]
                    .get("parameters")
                    .get("configs")
                    .get("workflow_id")
                )
                outputs_dict = self.workflow_dict.get(workflow_id).get("origin_output")

            for var_name in var_level_list:
                var_type = outputs_dict.get(var_name).get("type")
                if var_type == "object":
                    return_str += f"{var_name}."
                    outputs_dict = outputs_dict.get(var_name).get("properties")
                elif var_type == "array":
                    return_str += f"{var_name}[0]."
                    outputs_dict = (
                        outputs_dict.get(var_name).get("items").get("properties")
                    )
                else:
                    return_str += f"{var_name}"
            ref_var_name = return_str

        source = self._determine_ref_value_source("ref", data)
        return {
            "ref_node_id": ref_node_id,
            "ref_var_name": ref_var_name,
            "source": source,
        }

    def _create_branches(self, condition):
        """
        生成分支
        """

        def convert_condition(expression: str):
            operator = next(
                (opt for opt in BRANCH_CONDITION if f" {opt}" in expression), None
            )
            if operator is None:
                return None
            parts = expression.split(operator, 1)
            left = parts[0].strip()
            right = parts[1].strip() if len(parts) > 1 else None
            var_type = self._get_ref_var_type(left)
            right_type = var_type["type"]
            if operator in [
                "longer_than",
                "longer_than_or_eq",
                "shorter_than",
                "shorter_than_or_eq",
            ]:
                right_type = (
                    "number" if right_type in ["integer", "number"] else "integer"
                )
            if right_type == "array" and operator in ["contain", "not_contain"]:
                right_type = var_type["schema"].get("type", "string")
            return {
                "operator": operator,
                "left": {
                    "value": self._get_input_value(left),
                    "source": "user",
                    "required": False,
                    "type": var_type["type"],
                    "schema": var_type["schema"],
                },
                "right": {
                    "value": self._get_input_value(right),
                    "source": "user",
                    "required": False,
                    "type": right_type,
                }
                if right
                else None,
            }

        if "expressions" in condition:
            return dict(
                logic=condition.get("operator", "and"),
                conditions=[
                    convert_condition(expr) for expr in condition["expressions"]
                ],
            )
        return dict(
            logic=condition.get("operator", "and"),
            conditions=[convert_condition(condition.get("expression", ""))],
        )

    def _handle_branch(self, node):
        """
        处理分支节点
        """
        # 生成分支条件
        branches = []
        conditions_without_default = []
        for cond in node["parameters"]["conditions"]:
            if cond.get("expression") == "default":
                self.convert_res.edges.append(
                    EdgeField(
                        branch="default",
                        source=node["id"],
                        target=cond["next"],
                    )
                )
            else:
                conditions_without_default.append(cond)

        for idx, cond in enumerate(conditions_without_default):
            branch_id = "if" if idx == 0 else f"elseIf-{idx}"
            branches.append({"configs": self._create_branches(cond), "id": branch_id})
            self.convert_res.edges.append(
                EdgeField(
                    branch=branch_id,
                    source=node["id"],
                    target=cond["next"],
                )
            )
        branches.append({"configs": None, "id": "default"})
        return NodeField(
            branches=branches,
            id=node["id"],
            type="Branch",
            name=node["id"],
        )

    def _create_code_config(self, configs, in_or_out):
        """
        生成code节点的input以及output的config
        """
        result = []
        if in_or_out == "input":
            for item in configs:
                var_type = self._extract_var_type(item)
                input_field = ConfigField(
                    name=item.get("name", ""),
                    description="",
                    source="user",
                    type=var_type["type"],
                    required=True,
                    reflection=False,
                    schema=var_type["schema"],
                    value=self._get_input_value(item.get("value", "")),
                )
                result.append(input_field)
        else:
            for item in configs:
                var_type = self._extract_var_type(item)
                output_field = ConfigField(
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    source="user",
                    type=var_type["type"],
                    required=True,
                    reflection=False,
                    schema=var_type["schema"],
                    value={"default": "", "hint": "", "type": "generated"},
                )
                result.append(output_field)
        return result

    def _handle_code(self, node):
        """
        处理代码节点
        """
        code = node["parameters"]["configs"]["code"]

        # 如果未显式开启沙箱 (enable_sandbox 为 False)，则生成functionGraph代码节点
        sandbox_enabled = os.getenv("ENABLE_SANDBOX", "true").lower() == "true"
        # 代码节点全局优先级变量CODE_EXECUTOR
        is_local_mode = "local" == os.environ.get("CODE_EXECUTOR", "local")
        # 初始化基础配置
        configs = {"code": code}

        # 仅在非本地执行且禁用沙箱时，切换至 FG 模式
        if not is_local_mode and not sandbox_enabled:
            configs.update(
                {"exec_env": "fg", "fg_id": self._get_function_graph_id(node, code)}
            )

        code = NodeField(
            id=node["id"],
            type="Code",
            name=node["id"],
            configs=configs,
            inputs=self._create_code_config(node["parameters"]["inputs"], "input"),
            outputs=self._create_code_config(node["parameters"]["outputs"], "output"),
        )
        return code

    def _get_function_graph_id(self, node, code):
        function_graph_code = convert_sandbox_to_fg_code(code)

        project_id = self.metadata.get("project_id")
        functiongraph_url = (
            f"{AGENT_MANAGER_HOST}/v1/{project_id}/agent-manager/functions"
        )
        payload = get_function_graph_payload(node, function_graph_code)
        params = {"workspace_id": self.metadata.get("workspace_id")}
        headers = {
            "content-type": "application/json; charset=UTF-8",
            "X-Auth-Token": self.metadata.get("x_auth_token"),
        }
        try:
            response = requests.post(
                url=functiongraph_url,
                params=params,
                json=payload,
                verify=False,
                headers=headers,
                timeout=30,
            )
            rsp = response.json()
            return rsp.get("data").get("id")
        except Exception as e:
            logger.error(f"Failed to create FunctionGraph for the code node: {str(e)}")
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_IR_GENERATION_ERROR.code,
                StatusCode.NL2AGENT_IR_GENERATION_ERROR.errmsg.format(
                    error_msg="Failed to create FunctionGraph for the code node"
                ),
            ) from e

    def _create_plugin_config(self, plugin_info_dict, configs, in_or_out):
        """
        生成plugin input以及output的config
        """
        result = []
        if in_or_out == "input":
            for item in configs:
                var_type = self._extract_var_type(item)
                input_field = ConfigField(
                    name=item.get("name", ""),
                    description="",
                    source="user",
                    type=var_type["type"],
                    value=self._get_input_value(item.get("value", "")),
                )
                result.append(input_field)
        else:
            result = self._plugin_output_generator(plugin_info_dict["output_schema"])
        return result

    def _handle_plugin(self, node):
        """
        处理插件节点
        """
        plugin_info_dict = self.plugin_dict[node["parameters"]["configs"]["apiId"]]
        # decide 'inner' or 'custom': use format to infer
        if len(node["parameters"]["configs"]["apiId"].split("-")) == 5:
            is_inner_type = False
        else:
            is_inner_type = True

        plugin = NodeField(
            id=node["id"],
            type="Plugin",
            name=node["id"],
            configs={
                # 预制插件
                "original_info": {
                    "name": plugin_info_dict["tool_cn_name"],
                    "name_en": plugin_info_dict["tool_name"],
                    "description": plugin_info_dict["tool_desc"],
                    "type": "inner" if is_inner_type else "custom",
                },
                "valid": True,
                "streaming": False,
                "name": plugin_info_dict["tool_cn_name"],
                "tool_id": plugin_info_dict["tool_id"],
                "id": plugin_info_dict["plugin_id"],
                "type": "inner" if is_inner_type else "custom",
                "output_schema": plugin_info_dict["output_schema"],
                "exception_enable": False,
                "version_id": plugin_info_dict["version_id"],
            },
            inputs=self._create_plugin_config(
                plugin_info_dict, node["parameters"]["inputs"], "input"
            ),
            outputs=self._create_plugin_config(
                plugin_info_dict, node["parameters"]["outputs"], "output"
            ),
        )
        return plugin

    def _create_message_end_input_config(self, configs: list):
        """
        生成message和end节点的input config
        """
        result = []
        for item in configs:
            var_type = self._extract_var_type(item)
            input_field = ConfigField(
                name=item.get("name", ""),
                description="",
                source="user",
                type=var_type["type"],  # 如果输入不是引用，type应该为None，实测不影响。
                required=True,
                reflection=False,
                schema=var_type["schema"],
                value=self._get_input_value(item.get("value", "")),
            )
            result.append(input_field)
        return result

    def _handle_message(self, node):
        """
        处理消息节点
        """
        return NodeField(
            id=node["id"],
            type="Message",
            name=node["id"],
            configs={
                "template": node["parameters"]["configs"]["template"],
            },
            inputs=self._create_message_end_input_config(node["parameters"]["inputs"]),
            outputs=[
                ConfigField(
                    name="result",
                    description="Message output",
                    source="system",
                    type="string",
                    required=False,
                    reflection=False,
                    value={"content": "", "hint": "", "type": "generated"},
                )
            ],
        )

    def _handle_end(self, node):
        """
        处理结束节点
        """
        return NodeField(
            id=node["id"],
            type="End",
            name="End",
            configs={
                "is_stream_out": True,
                "response_template": node["parameters"]["configs"]["template"],
                "response_mode": "directResponse",
            },
            inputs=self._create_message_end_input_config(node["parameters"]["inputs"]),
            outputs=[
                ConfigField(
                    name="response_content",
                    description="Message output",
                    source="system",
                    type="string",
                    value={"type": "generated"},
                )
            ],
        )

    def _create_intermediate_loop_var_schema(self, configs):
        """生成loop节点中间变量参数intermediate_loop_var的schema"""
        result = []
        for item in configs:
            result.append(
                dict(
                    name=item.get("name", ""),
                    type=self._extract_var_type(item).get("type", ""),
                    description="",
                    required=True,
                    source="pre_defined",
                    value=self._get_input_value(item.get("value", "")),
                )
            )
        return result

    def _create_loop_config(self, configs, in_or_out: Literal["input", "output"]):
        """
        生成loop节点的input和output的config
        """
        result = []
        for item in configs:
            var_name = item.get("name")
            if var_name == "intermediate_loop_var":
                config_field = ConfigField(
                    name=var_name,
                    type="object",
                    description="Sharing parameters between loops",
                    source="pre_defined",
                    schema=self._create_intermediate_loop_var_schema(
                        item.get("value", [])
                    ),
                    value={"default": "", "type": "nested", "hint": ""},
                )
            else:
                var_type = self._extract_var_type(item)
                desc_content = (
                    "Number of loops"
                    if var_name == "num_loop_var"
                    else item.get("description", "")
                )
                source_content = "pre_defined" if in_or_out == "input" else "user"
                config_field = ConfigField(
                    name=var_name,
                    type=var_type.get("type", ""),
                    description=desc_content,
                    source=source_content,
                    schema=var_type.get("schema"),
                    value=self._get_input_value(item.get("value", "")),
                )
            result.append(config_field)
        return result

    def _handle_loop(self, node):
        """
        处理循环节点
        """
        loop_body = [
            node_id
            for node_id in node["parameters"]["configs"]["loop_body"]
            if self.node_dict.get(node_id, {}).get("type")
            not in ("LoopInput", "LoopOutput")
        ]
        return NodeField(
            id=node["id"],
            type="Loop",
            name=node["id"],
            configs={
                "loop_type": node["parameters"]["configs"]["loop_type"],
                "loop_body": loop_body,
            },
            inputs=self._create_loop_config(node["parameters"]["inputs"], "input"),
            outputs=self._create_loop_config(node["parameters"]["outputs"], "output"),
        )

    def _create_set_variable_input_config(self, configs, variable_dict):
        result = []
        for item in configs:
            ref_var = item["left"]
            var_name = ref_var[2:-1].split(".")[1]
            input_field = ConfigField(
                name=var_name,
                type=variable_dict.get(var_name, {}).get("type", ""),
                description=variable_dict.get(var_name, {}).get("description", ""),
                source="user",
                value=self._get_input_value(ref_var),
            )
            result.append(input_field)
        return result

    def _create_set_variable_setting_config(self, configs, variable_dict):
        """
        生成set variable节点inputs的config
        """
        result = []
        for item in configs:
            ref_var = item["left"]
            var_name = ref_var[2:-1].split(".")[1]
            setting_field = {
                "left": {
                    "type": variable_dict.get(var_name, {}).get("type", ""),
                    "value": self._get_input_value(ref_var),
                },
                "right": {
                    "type": variable_dict.get(var_name, {}).get("type", ""),
                    "value": self._get_input_value(item.get("right", "")),
                },
            }
            result.append(setting_field)
        return result

    def _handle_set_variable(self, node):
        """
        处理变量赋值节点
        """
        variable_dict = {item["name"]: item for item in node.get("variables", [])}
        settings = node["parameters"]["settings"]
        return NodeField(
            id=node["id"],
            type="SetVariable",
            name=node["id"],
            inputs=self._create_set_variable_input_config(settings, variable_dict),
            configs={
                "settings": self._create_set_variable_setting_config(
                    settings, variable_dict
                )
            },
        )

    def _create_workflow_config(
        self, configs, workflow_info_dict, in_or_out: Literal["input", "output"]
    ):
        """
        生成workflow节点的config
        """
        result = []
        if in_or_out == "input":
            for item in configs:
                var_type = self._extract_var_type(item)
                input_field = ConfigField(
                    name=item.get("name", ""),
                    description="",
                    type=var_type["type"],
                    source="system",
                    schema=var_type["schema"],
                    value=self._get_input_value(item.get("value", "")),
                )
                result.append(input_field)
        else:
            # 复用插件复杂类型的输出变量处理
            result = self._plugin_output_generator(
                workflow_info_dict["output_schema"], resource_type="workflow"
            )
        return result

    def _handle_workflow(self, node):
        """
        处理workflow节点
        """
        workflow_id = node["parameters"]["configs"]["workflow_id"]
        workflow_info_dict = self.workflow_dict[workflow_id]
        return NodeField(
            id=node["id"],
            type="Workflow",
            name=node["parameters"]["configs"]["workflow_name"],
            configs={
                "id": node["parameters"]["configs"]["workflow_id"],
                "name": workflow_info_dict.get("name", ""),
                "original_info": {
                    "name": workflow_info_dict.get("name", ""),
                    "name_en": workflow_info_dict.get("name_en", ""),
                    "description": workflow_info_dict.get("description", ""),
                },
                "plugins": [],
                "version_id": workflow_info_dict.get("version_id"),
                "version_name": workflow_info_dict.get("version_name"),
            },
            inputs=self._create_workflow_config(
                node["parameters"]["inputs"], workflow_info_dict, "input"
            ),
            outputs=self._create_workflow_config(
                node["parameters"]["outputs"], workflow_info_dict, "output"
            ),
        )

    def _convert_node(self, node):
        """
        转换节点
        """
        try:
            type_handlers = {
                "Start": self._handle_start,
                "IntentDetection": self._handle_intent,
                "LLM": self._handle_llm,
                "Questioner": self._handle_questioner,
                "Branch": self._handle_branch,
                "Code": self._handle_code,
                "Plugin": self._handle_plugin,
                "Message": self._handle_message,
                "End": self._handle_end,
                "Loop": self._handle_loop,
                "LoopInput": self._handle_loop_input,
                "LoopOutput": self._handle_loop_output,
                "SetVariable": self._handle_set_variable,
                "Workflow": self._handle_workflow,
            }
            return type_handlers.get(node["type"], lambda x: x)(node)
        except Exception as e:
            raise JiuWenBaseException(-1, f"Transform {node['id']} failed.") from e

    def _convert_edges(self):
        """
        转换边
        """
        for node in self.original_data:
            # 处理普通连接
            if "next" in node and node.get("type") != "LoopOutput":
                self.convert_res.edges.append(
                    EdgeField(source=node["id"], target=node["next"])
                )

    def _set_layouts(self):
        """
        进行布局设置
        """
        for node in self.original_data:
            node_id = node["id"]
            self.convert_res.layouts[node_id] = {
                "x": 225,
                "y": 225,
            }


@dataclass
class EdgeField:
    source: str
    target: str
    branch: Optional[str] = None
    id: Optional[str] = None
    source_branch_id: Optional[str] = None
    target_branch_id: Optional[str] = None


@dataclass
class NodeField:
    name: str
    id: str
    type: str = "String"
    inputs: Optional[list] = None
    outputs: Optional[list] = None
    branches: Optional[list] = None
    configs: Optional[dict] = None


@dataclass
class ConfigField:
    name: str
    description: str
    type: str
    source: Literal["user", "system", "pre_defined"]
    cn_name: Optional[str] = None
    memory: Optional[str] = None
    field_type: Optional[str] = None
    reflection: bool = False
    required: bool = True
    schema: Optional[str | dict | list] = None
    value: Optional[dict] = None
    validator: Optional[list] = None


@dataclass
class Workflow:
    layouts: Dict = field(default_factory=dict)
    nodes: List[NodeField] = field(default_factory=list)
    edges: List[EdgeField] = field(default_factory=list)
    configs: Dict = field(default_factory=dict)
