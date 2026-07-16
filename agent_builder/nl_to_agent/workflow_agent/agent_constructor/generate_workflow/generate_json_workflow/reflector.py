# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import json
import re

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.nl_to_agent.workflow_agent.progress_bar import (
    MODIFY_PROMPT,
    modify_msg,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.exception_bridge import JiuWenException
from agent_builder.adapter.jiuwen_bridge import HumanMessage, AIMessage

MAX_TURN = 10


def extract_placeholder_content(input_str: str) -> tuple[bool, list[str]]:
    """从输入字符串中提取特定格式的占位符内容"""
    pattern = r"\$\{([^}]+)\}"
    matches = re.findall(pattern, input_str)
    has_placeholder = len(matches) > 0
    return has_placeholder, matches


def extract_json(full_response: str):
    """提取json的内容"""
    pattern = r"```(?:json)?\s*([^\s](?:[\s\S]*?[^\s])?)\s*```"
    matches = re.findall(pattern, full_response)
    extracted_contents = matches[0]
    return extracted_contents


def extract_array_enclosed_type(type_str: str):
    """提取array类型被尖括号包裹的类型"""
    pattern = r"^array<(.*?)>$"
    match = re.search(pattern, type_str)
    return match.group(1) if match else None


class ReflectionInfo:
    def __init__(self, succeed: bool, errors: list[str]):
        self.succeed = succeed
        self.errors = errors


class Reflector:
    def __init__(self, model, plugin_dict, workflow_dict):
        self.model = model
        self.plugin_dict = plugin_dict
        self.workflow_dict = workflow_dict

        self.max_turns = MAX_TURN
        self.available_node_types = {
            "Start",
            "End",
            "Message",
            "LLM",
            "Questioner",
            "Loop",
            "LoopInput",
            "LoopOutput",
            "SetVariable",
            "Plugin",
            "Workflow",
            "Code",
            "Branch",
            "IntentDetection",
        }
        self.available_variable_types = {
            "string",
            "integer",
            "number",
            "boolean",
            "object",
            "file/default",
            "file/doc",
            "file/txt",
            "file/excel",
            "file/ppt",
            "file/image",
            "file/audio",
            "file/video",
            "array<string>",
            "array<integer>",
            "array<number>",
            "array<boolean>",
            "array<object>",
            "array<file>",
        }
        self.available_condition_operators = {
            "string": {
                "eq",
                "not_eq",
                "contain",
                "not_contain",
                "longer_than",
                "longer_than_or_eq",
                "shorter_than",
                "shorter_than_or_eq",
                "is_empty",
                "is_not_empty",
            },
            "integer": {
                "eq",
                "not_eq",
                "longer_than",
                "longer_than_or_eq",
                "shorter_than",
                "shorter_than_or_eq",
            },
            "number": {
                "eq",
                "not_eq",
                "longer_than",
                "longer_than_or_eq",
                "shorter_than",
                "shorter_than_or_eq",
            },
            "boolean": {"eq"},
            "file": {
                "eq",
                "not_eq",
                "contain",
                "not_contain",
                "longer_than",
                "longer_than_or_eq",
                "shorter_than",
                "shorter_than_or_eq",
                "is_empty",
                "is_not_empty",
            },
            "object": {"is_empty", "is_not_empty"},
            "array": {
                "contain",
                "not_contain",
                "longer_than",
                "longer_than_or_eq",
                "shorter_than",
                "shorter_than_or_eq",
                "is_empty",
                "is_not_empty",
            },
        }
        self.available_node_output_types = dict()
        self.node_info_dict = dict()
        self.node_ids_of_next = set()

        self.errors = []
        self.check_functions = {
            "Start": self._check_start_node,
            "End": self._check_end_node,
            "Message": self._check_message_node,
            "LLM": self._check_llm_node,
            "Questioner": self._check_questioner_node,
            "Plugin": self._check_plugin_node,
            "Code": self._check_code_node,
            "Branch": self._check_branch_node,
            "IntentDetection": self._check_intent_detection_node,
            "Loop": self._check_loop_node,
            "LoopInput": self._check_loop_input_node,
            "LoopOutput": self._check_loop_output_node,
            "SetVariable": self._check_set_variable_node,
            "Workflow": self._check_workflow_node,
        }

    @staticmethod
    def _format_modify_prompt(reflect_errors: list[str]):
        format_query = "请按照如下错误优化json：\n"
        for err in reflect_errors:
            format_query = format_query + err + "\n"
        return format_query

    def stream_reflect(self, full_response, llm_messages):
        """流式反思"""
        turn = 0
        # 初始处理传入的full_response
        while True:
            if turn >= self.max_turns:
                raise JiuWenException("Max turns exceeded.")

            json_data = extract_json(full_response)
            if json_data:
                self.check_format(json_data)
                reflect_result = (
                    ReflectionInfo(succeed=False, errors=self.errors)
                    if self.errors
                    else ReflectionInfo(succeed=True, errors=[])
                )
                if reflect_result.succeed:
                    return
                modify_prompt = self._format_modify_prompt(reflect_result.errors)
                llm_messages.append(HumanMessage(content=modify_prompt))
                logger.error(f"Reflect failed turn {turn}: {reflect_result.errors}")
            else:
                raise JiuWenException("No DSL code generated initially.")

            # 生成新的响应并实时返回每个chunk
            full_response = ""
            for item in self.model.chat(
                llm_messages, method="stream", add_prefix=False, type="message"
            ):
                if item.content:
                    full_response = item.content
                yield item

            llm_messages.append(AIMessage(content=full_response))
            turn += 1

    async def stream_reflect_async(self, full_response, llm_messages):
        """流式反思"""
        turn = 0
        # 初始处理传入的full_response
        while True:
            if turn >= self.max_turns:
                raise JiuWenBaseException(
                    StatusCode.NL2AGENT_LLM_PARSE_FAILED.code,
                    StatusCode.NL2AGENT_LLM_PARSE_FAILED.errmsg.format(
                        error_msg="Max turns exceeded."
                    ),
                )

            json_data = extract_json(full_response)
            if json_data:
                self.check_format(json_data)
                reflect_result = (
                    ReflectionInfo(succeed=False, errors=self.errors)
                    if self.errors
                    else ReflectionInfo(succeed=True, errors=[])
                )
                if reflect_result.succeed:
                    return
                modify_prompt = self._format_modify_prompt(reflect_result.errors)
                yield modify_msg(
                    str(reflect_result.errors), MODIFY_PROMPT, turn, self.max_turns
                )
                llm_messages.append(HumanMessage(content=modify_prompt))
                logger.error(f"Reflect failed turn {turn}: {reflect_result.errors}")
            else:
                raise JiuWenException("No DSL code generated initially.")

            # 生成新的响应并实时返回每个chunk
            full_response = ""
            async for item in self.model.achat(
                llm_messages, method="stream", add_prefix=False, type="message"
            ):
                if item.raw_content:
                    yield item, "dl_flow"  # dl流式输出
                if item.content:
                    full_response = item.content
                    yield item

            llm_messages.append(AIMessage(content=full_response))
            turn += 1

    def check_format(self, generated_dsl: str):
        """通过规则检查生成的SimpleIR是否正确"""
        self.reset()
        try:
            generated_dl_dict = json.loads(generated_dsl)
        except Exception as e:
            self.errors.append(f"JSON格式错误: {str(e)}")
            return

        node_type_nums = {}
        for node_index, node_content in enumerate(generated_dl_dict):
            if "type" in node_content:
                node_type_nums[node_content["type"]] = (
                    node_type_nums.get(node_content["type"], 0) + 1
                )
            basic_has_error = self._check_basic_info(node_content, node_index)
            self.node_info_dict[node_content["id"]] = {
                "content": node_content,
                "index": node_index,
                "checked": False,
                "basic_has_error": basic_has_error,
            }

        if node_type_nums.get("Start", 0) != 1:
            self.errors.append(
                f"Start节点数量错误: 必须有且仅有1个Start节点, 当前有{node_type_nums.get('Start', 0)}个Start节点"
            )
        if node_type_nums.get("End", 0) != 1:
            self.errors.append(
                f"End节点数量错误: 必须有且仅有1个End节点, 当前有{node_type_nums.get('End', 0)}个End节点"
            )

        for _, node_info in self.node_info_dict.items():
            if not node_info.get("checked", False) and not node_info.get(
                "basic_has_error", False
            ):
                node_info["checked"] = True
                node_content = node_info["content"]
                self.check_functions[node_content["type"]](node_content)

        for node_id in self.node_ids_of_next:
            if node_id not in self.node_info_dict:
                self.errors.append(f"节点ID错误: {node_id} 不存在")

    def reset(self):
        """重置状态"""
        self.available_node_output_types = dict()
        self.node_info_dict = dict()
        self.node_ids_of_next = set()
        self.errors = []

    def _check_basic_info(self, node_content: dict, node_index: int) -> bool:
        if not isinstance(node_content, dict):
            self.errors.append(f"第{node_index + 1}个节点类型错误: 必须为字典类型!")
            return True
        for key_item in ["id", "type"]:
            if key_item not in node_content:
                self.errors.append(f"第{node_index + 1}个节点中缺失'{key_item}'属性")
                return True
        if node_content["type"] not in ["LoopInput", "LoopOutput"]:
            if "parameters" not in node_content:
                self.errors.append(f"第{node_index + 1}个节点中缺失'parameters'属性")
                return True
        if node_content["id"] in self.node_info_dict:
            self.errors.append(
                f"第{node_index + 1}个节点ID错误: {node_content['id']} 已存在"
            )
            return True
        if node_content["type"] not in self.available_node_types:
            self.errors.append(
                f"第{node_index + 1}个节点类型错误: {node_content['type']} 不在可用节点类型中"
            )
            return True
        return False

    def _check_start_node(self, node_content: dict):
        self._check_outputs_list(node_content)
        if (
            not self.errors
            and {"name": "query", "type": "string", "description": "用户输入"}
            not in node_content["parameters"]["outputs"]
        ):
            self.errors.append(
                "Start节点的'parameters'中的'outputs'列表中必须包含{'name': 'query', 'type': 'string', 'description': '用户输入'}"
            )
        self._check_next_info(node_content)

    def _check_end_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_config_info(node_content, keys=["template"])
        if (
            "inputs" in node_content["parameters"]
            and "configs" in node_content["parameters"]
            and "template" in node_content["parameters"]["configs"]
        ):
            for input_item in node_content["parameters"]["inputs"]:
                input_name = input_item.get("name", "")
                if input_name not in node_content["parameters"]["configs"]["template"]:
                    self.errors.append(
                        f"End节点的'parameters'中的'configs'中的'template'必须包含所有的inputs参数，缺少：{input_name}"
                    )

    def _check_message_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_config_info(node_content, keys=["template"])
        self._check_next_info(node_content)

    def _check_llm_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_outputs_list(node_content)
        self._check_config_info(node_content, keys=["system_prompt", "user_prompt"])
        self._check_next_info(node_content)

    def _check_questioner_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_outputs_list(node_content)
        self._check_config_info(node_content, keys=["prompt"])
        self._check_next_info(node_content)

    def _check_plugin_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_outputs_list(node_content)
        self._check_config_info(node_content, keys=["tool_name", "apiId"])
        self._check_next_info(node_content)
        self._check_plugin(node_content)

    def _check_code_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_outputs_list(node_content)
        self._check_config_info(node_content, keys=["code"])
        self._check_next_info(node_content)

    def _check_intent_detection_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_config_info(node_content, keys=["prompt"])
        self._check_intent_conditions_list(node_content)

    def _check_loop_input_node(self, node_content: dict):
        self._check_next_info(node_content)

    def _check_loop_output_node(self, node_content: dict):
        self._check_next_info(node_content)

    def _check_loop_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_outputs_list(node_content)
        self._check_config_info(node_content, keys=["loop_type", "loop_body"])
        self._check_next_info(node_content)
        self._check_loop_type(node_content)
        self._check_loop_inputs(node_content)
        self._check_loop_body(node_content)
        self._check_loop_outputs(node_content)

    def _check_set_variable_node(self, node_content: dict):
        self._check_memory_variables(node_content)
        self._check_variable_settings(node_content)
        self._check_next_info(node_content)

    def _check_branch_node(self, node_content: dict):
        if "conditions" not in node_content["parameters"]:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中缺失'conditions'属性"
            )
            return
        if not isinstance(node_content["parameters"]["conditions"], list):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                "'parameters'中的'conditions'属性必须为列表类型"
            )
            return
        has_default_branch = False
        for condition in node_content["parameters"]["conditions"]:
            if not isinstance(condition, dict):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'conditions'列表中的元素必须为字典类型"
                )
                return
            # check branch and description val
            if "branch" not in condition:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']},"
                    f" 'parameters'中的'conditions'列表中的元素缺失'branch'属性"
                )
            # check expression
            if condition.get("expression") == "default":
                has_default_branch = True
            else:
                self._check_branch_expression(condition, node_content)
            # check next
            if "next" not in condition:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'conditions'列表中的元素缺失'next'属性"
                )
            else:
                self.node_ids_of_next.add(condition["next"])
        if not has_default_branch:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                f"'parameters'中的'conditions'列表中缺少default分支"
            )

    def _check_workflow_node(self, node_content: dict):
        self._check_inputs_list(node_content)
        self._check_outputs_list(node_content)
        self._check_config_info(node_content, keys=["workflow_id", "workflow_name"])
        self._check_next_info(node_content)

        if (
            "configs" in node_content["parameters"]
            and isinstance(node_content["parameters"]["configs"], dict)
            and "workflow_id" in node_content["parameters"]["configs"]
        ):
            if (
                node_content["parameters"]["configs"].get("workflow_id")
                not in self.workflow_dict
            ):
                self.errors.append(
                    f"{node_content['type']}节点的['parameters']['configs']中生成了一个错误的'workflow_id'"
                )
                return

            if "outputs" in node_content["parameters"] and isinstance(
                node_content["parameters"]["outputs"], list
            ):
                generated_outputs_list = node_content["parameters"]["outputs"]
                workflow_info_dict = self.workflow_dict.get(
                    node_content["parameters"]["configs"].get("workflow_id")
                )
                expected_outputs_list = workflow_info_dict.get("outputs")
                lost_output_info = []
                for output_info in expected_outputs_list:
                    if output_info not in generated_outputs_list:
                        lost_output_info.append(output_info)
                if lost_output_info:
                    self.errors.append(
                        f"{node_content['id']}节点的['parameters']['outputs']中缺失了以下参数："
                        f"{lost_output_info}。请确保'{node_content['type']}'节点的输出列表和原始输出列表完全相同"
                    )
                not_existed_output_info = []
                for gen_output_info in generated_outputs_list:
                    if gen_output_info not in expected_outputs_list:
                        not_existed_output_info.append(gen_output_info)
                if not_existed_output_info:
                    self.errors.append(
                        f"{node_content['id']}节点的['parameters']['outputs']中生成了不存在的参数："
                        f"{not_existed_output_info}。请确保'{node_content['type']}'节点的输出列表和原始输出列表完全相同"
                    )

    def _check_plugin(self, node_content: dict):
        """检查节点parameters中是configs和outputs是否存在"""
        if (
            "configs" in node_content["parameters"]
            and isinstance(node_content["parameters"]["configs"], dict)
            and "apiId" in node_content["parameters"]["configs"]
        ):
            if (
                node_content["parameters"]["configs"].get("apiId")
                not in self.plugin_dict
            ):
                self.errors.append(
                    f"{node_content['type']}节点的['parameters']['configs']中生成了一个错误的'apiId'"
                )
                return

            if "outputs" in node_content["parameters"] and isinstance(
                node_content["parameters"]["outputs"], list
            ):
                # 检查插件的输出列表是否缺失信息
                generated_outputs_list = node_content["parameters"]["outputs"]
                plugin_info_dict = self.plugin_dict.get(
                    node_content["parameters"]["configs"].get("apiId")
                )
                expected_outputs_list = plugin_info_dict.get("outputs_for_simpleIR")
                lost_output_info = []
                for output_info in expected_outputs_list:
                    if output_info not in generated_outputs_list:
                        lost_output_info.append(output_info)
                if lost_output_info:
                    self.errors.append(
                        (
                            f"{node_content['id']}节点的['parameters']['outputs']中缺失了以下参数："
                            f"{lost_output_info}。请确保插件节点的输出列表和原始插件输出列表完全相同"
                        )
                    )
                not_existed_output_info = []
                for gen_output_info in generated_outputs_list:
                    if gen_output_info not in expected_outputs_list:
                        not_existed_output_info.append(gen_output_info)
                if not_existed_output_info:
                    self.errors.append(
                        (
                            f"{node_content['id']}节点的['parameters']['outputs']中生成了不存在的参数:"
                            f"{not_existed_output_info}。请确保插件节点的输出列表和原始插件输出列表完全相同"
                        )
                    )

    def _check_intent_conditions_list(self, node_content: dict):
        if "conditions" not in node_content["parameters"]:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中缺失'conditions'属性"
            )
            return
        if not isinstance(node_content["parameters"]["conditions"], list):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                f"'parameters'中的'conditions'属性必须为列表类型"
            )
            return
        node_id = node_content["id"]
        has_default_branch = False
        for condition in node_content["parameters"]["conditions"]:
            if not isinstance(condition, dict):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'conditions'列表中的元素必须为字典类型"
                )
                return
            # check branch and description val

            if "branch" not in condition:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'conditions'列表中的元素缺失'branch'属性"
                )
            # check next
            if "next" not in condition:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中的'conditions'列表中的元素缺失'next'属性"
                )
            else:
                self.node_ids_of_next.add(condition["next"])
            # check expression
            if "expression" not in condition:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'conditions'列表中的元素缺失'expression'属性"
                )
            else:
                expression = condition["expression"]
                if not isinstance(expression, str):
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'conditions'列表中的元素的'expression'属性必须为字符串类型"
                    )
                    return
                if expression == "default":
                    has_default_branch = True
                else:
                    left_val = "${" + node_id + ".rawOutput}"
                    if left_val not in expression:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'conditions'列表中的元素的'expression'的表达式变量错误"
                        )
                    if "contain" not in expression:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'conditions'列表中的元素的'expression'的表达式必须使用contain"
                        )
        if not has_default_branch:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                f"'parameters'中的'conditions'列表中缺少default分支"
            )

    def _check_branch_expression(self, condition_branch: dict, node_content: dict):
        if "expression" in condition_branch:
            expression = condition_branch["expression"]
            if not isinstance(expression, str):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'conditions'列表中的元素的'expression'属性必须为字符串类型"
                )
            else:
                _, placeholder_content = extract_placeholder_content(expression)
                for content in placeholder_content:
                    if content not in self.available_node_output_types:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'conditions'列表中的元素的'expression'的表达式中引用了不存在的变量"
                        )
                    else:
                        self._check_branch_operator(
                            expression, placeholder_content[0], node_content
                        )
        elif "expressions" in condition_branch:
            expressions = condition_branch["expressions"]
            if not isinstance(expressions, list):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'conditions'列表中的元素的'expression'属性必须为列表类型"
                )
            else:
                for expression in expressions:
                    _, placeholder_content = extract_placeholder_content(expression)
                    for content in placeholder_content:
                        if content not in self.available_node_output_types:
                            self.errors.append(
                                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                                f"'parameters'中的'conditions'列表中的元素的'expression'的表达式中引用了不存在的变量"
                            )
                        else:
                            self._check_branch_operator(
                                expression, placeholder_content[0], node_content
                            )
        else:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                f"'parameters'中的'conditions'列表中的元素缺失'expression'或'expressions'属性"
            )

    def _check_branch_operator(
        self, expression: str, ref_node_var: str, node_content: dict
    ):
        var_type = self.available_node_output_types[ref_node_var]
        if var_type.startswith("array"):
            var_type = "array"
        elif var_type.startswith("file"):
            var_type = "file"
        condition_operators = self.available_condition_operators[var_type]
        expression_list = expression.strip().split(" ")
        if expression_list[1] not in condition_operators:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                f"'parameters'中的'conditions'列表中的元素的'expression'的表达式使用了"
                f"'{var_type}'类型变量不支持的关系运算符'{expression_list[1]}'"
            )
        elif (
            var_type == "boolean"
            and len(expression_list) > 2
            and expression_list[2] not in ["true", "false"]
        ):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                f"'parameters'中的'conditions'列表中的元素的'expression'的表达式使用了"
                f"'{var_type}'类型变量不支持的值'{expression_list[2]}'，只能使用'true'或'false'"
            )

    def _check_loop_type(self, node_content: dict):
        loop_type = node_content["parameters"].get("configs", {}).get("loop_type")
        if loop_type and loop_type != "arrayLoop":
            self.errors.append(
                "Loop节点的'parameters'中的'configs'中的'loop_type'字段值必须是'arrayLoop'"
            )

    def _check_loop_body(self, node_content: dict):
        loop_body = node_content["parameters"].get("configs", {}).get("loop_body")
        if not isinstance(loop_body, list):
            self.errors.append(
                "Loop节点的'parameters'中的'configs'中的'loop_body'属性必须为列表类型"
            )
            return

        if len(loop_body) <= 2:
            self.errors.append(
                "Loop节点的'parameters'中的'configs'中的'loop_body'字段值中除LoopInput和LoopOutput节点外必须包含至少一个节点"
            )

        for node_id in loop_body:
            node_info = self.node_info_dict.get(node_id)
            if node_info is None:
                self.errors.append(
                    f"Loop节点的'parameters'中的'configs'中的'loop_body'包含不存在节点'{node_id}'"
                )
            elif not node_info.get("checked", False) and not node_info.get(
                "basic_has_error", False
            ):
                node_info["checked"] = True
                self.check_functions[node_info["content"]["type"]](node_info["content"])

    def _check_loop_inputs(self, node_content: dict):
        inputs = node_content["parameters"].get("inputs")
        self.available_node_output_types[f"{node_content['id']}.index"] = "integer"
        if isinstance(inputs, list):
            if not inputs:
                self.errors.append("Loop节点的'parameters'中的'inputs'列表不能为空")
            elif len(node_content["parameters"]["inputs"]) > 1:
                self.errors.append(
                    "Loop节点的'parameters'中的'inputs'列表只能存在一个输入参数"
                )
            else:
                input_item = inputs[0]
                is_arr_loop_var = input_item.get("name") == "arr_loop_var"
                array_item_type = extract_array_enclosed_type(
                    input_item.get("type", "").strip()
                )
                if not (is_arr_loop_var and array_item_type is not None):
                    self.errors.append(
                        "Loop节点的'parameters'中的'inputs'列表只能存在一个'type'是数组，'name'为'arr_loop_type'的参数"
                    )
                    return
                self.available_node_output_types[
                    f"{node_content['id']}.arr_loop_var.item"
                ] = array_item_type

    def _check_loop_outputs(self, node_content: dict):
        outputs = node_content["parameters"].get("outputs")
        if not isinstance(outputs, list) or not outputs:
            self.errors.append(
                "Loop节点的'parameters'中的'outputs'列表必须至少存在一个参数"
            )
            return

        for item in node_content["parameters"]["outputs"]:
            value = item["value"]
            has_placeholder, placeholder_content = extract_placeholder_content(value)
            if has_placeholder:
                ref_node, _ = placeholder_content[0].split(".", 1)
                if len(placeholder_content) > 1:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'outputs'列表中的元素'value'属性值中有多个引用变量：{value}"
                    )
                elif len(placeholder_content) == 1:
                    if (
                        placeholder_content[0] not in self.available_node_output_types
                        or ref_node
                        not in node_content["parameters"]["configs"].get(
                            "loop_body", []
                        )
                    ):
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'outputs'列表中的元素'value'属性引用了循环体内不存在的变量：{value}"
                        )
                    elif (
                        f"array<{self.available_node_output_types[placeholder_content[0]]}>"
                        != item.get("type", "array<string>")
                    ):
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'outputs'列表中的元素与引用的循环体内节点变量存在类型不一致：{value}"
                        )
                    elif len(placeholder_content[0]) != len(value.strip()[2:-1]):
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'outputs'列表中的元素'value'属性引用格式错误：{value}"
                        )

    def _check_memory_variables(self, node_content: dict, check_type: bool = True):
        if "variables" not in node_content:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 缺失'variables'属性"
            )
            return
        if not isinstance(node_content["variables"], list):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'variables'属性必须为列表类型"
            )
            return
        variable_names = set()
        # check each item in the 'variables' list
        for variable in node_content["variables"]:
            if not isinstance(variable, dict):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'variables'列表中的元素必须为字典类型：{variable}"
                )
                return

            if "name" not in variable:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'variables'列表中的元素缺失'name'属性：{variable}"
                )
            else:
                if variable["name"] in variable_names:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'variables'列表中的元素'name'属性值必须唯一：{variable['name']}"
                    )
                variable_names.add(variable["name"])
                self.available_node_output_types[f"memory.{variable['name']}"] = (
                    variable.get("type", "string")
                )

            if "description" not in variable:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'variables'列表中的元素缺失'description'属性：{variable}"
                )
            if check_type:
                if "type" not in variable:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'variables'列表中的元素缺失'type'属性：{variable}"
                    )
                else:
                    if variable["type"] not in self.available_variable_types:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'variables'列表中的元素'type'属性值必须为{self.available_variable_types}中的一个："
                            f"{variable['type']}"
                        )

    def _check_variable_settings(self, node_content: dict):
        if "settings" not in node_content["parameters"]:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中缺失'settings'属性"
            )
            return
        if not isinstance(node_content["parameters"]["settings"], list):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中的'settings'属性必须为列表类型"
            )
            return
        for setting in node_content["parameters"]["settings"]:
            if not isinstance(setting, dict):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'settings'列表中的元素必须为字典类型：{setting}"
                )
                return
            # check left and right val
            for key in ["left", "right"]:
                if key not in setting:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'settings'列表中的元素缺失'{key}'属性：{setting}"
                    )
                value = setting[key]
                has_placeholder, placeholder_content = extract_placeholder_content(
                    value
                )
                if has_placeholder:
                    if len(placeholder_content) > 1:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'settings'列表中的元素'{key}'属性值中有多个引用变量：{value}"
                        )
                    elif (
                        len(placeholder_content) == 1
                        and placeholder_content[0]
                        not in self.available_node_output_types
                    ):
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'settings'列表中的元素'{key}'属性引用了不存在的变量：{value}"
                        )
                    elif len(placeholder_content) == 1 and len(
                        placeholder_content[0]
                    ) != len(value.strip()[2:-1]):
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'settings'列表中的元素'{key}'属性引用格式错误：{value}"
                        )
                else:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'settings'列表中的元素'{key}'属性不符合引用赋值形式：{value}"
                    )

    def _check_inputs_list(self, node_content: dict, check_type: bool = True):
        def check_array_object_value(item: dict):
            type_content = item.get("type", "")
            value_content = item.get("value", "")
            if (
                type_content.startswith("array")
                and value_content.startswith("[")
                and value_content.endswith("]")
            ):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'inputs'列表中的元素为'array'类型时，不能使用直接赋值"
                )
            elif (
                type_content == "object"
                and value_content.startswith("{")
                and value_content.endswith("}")
            ):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'inputs'列表中的元素为'object'类型时，不能使用直接赋值"
                )

        if "inputs" not in node_content["parameters"]:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中缺失'inputs'属性"
            )
            return
        if not isinstance(node_content["parameters"]["inputs"], list):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中的'inputs'属性必须为列表类型"
            )
            return
        input_names = set()
        # check each item in the 'inputs' list
        for input_item in node_content["parameters"]["inputs"]:
            if not isinstance(input_item, dict):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'inputs'列表中的元素必须为字典类型"
                )
                return

            if "name" not in input_item:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'inputs'列表中的元素缺失'name'属性：{input_item}"
                )
            else:
                if input_item["name"] in input_names:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'inputs'列表中的元素'name'属性值必须唯一：{input_item['name']}"
                    )
                input_names.add(input_item["name"])
            if "value" not in input_item:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'inputs'列表中的元素缺失'value'属性：{input_item}"
                )
            else:
                value = input_item["value"]
                has_placeholder, placeholder_content = extract_placeholder_content(
                    value
                )
                if has_placeholder:
                    if len(placeholder_content) > 1:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'inputs'列表中的元素'value'属性值中有多个引用变量：{value}"
                        )
                    elif len(placeholder_content) == 1:
                        if (
                            placeholder_content[0]
                            not in self.available_node_output_types
                        ):
                            self.errors.append(
                                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                                f"'parameters'中的'inputs'列表中的元素'value'属性引用了不存在的变量：{value}"
                            )
                        elif self.available_node_output_types[
                            placeholder_content[0]
                        ] != input_item.get("type", "string"):
                            self.errors.append(
                                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                                f"'parameters'中的'inputs'列表中的元素与引用的变量类型不一致：{value}"
                            )
                        elif len(placeholder_content[0]) != len(value.strip()[2:-1]):
                            self.errors.append(
                                f"{node_content['id']}节点, 类型为{node_content['type']}, "
                                f"'parameters'中的'inputs'列表中的元素'value'属性引用格式错误：{value}"
                            )
            if check_type:
                if "type" not in input_item:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'inputs'列表中的元素缺失'type'属性：{input_item}"
                    )
                else:
                    if input_item["type"] not in self.available_variable_types:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}"
                            f"'parameters'中的'inputs'列表中的元素'type'属性值必须为{self.available_variable_types}中的一个："
                            f"{input_item['type']}"
                        )
            check_array_object_value(input_item)

    def _check_outputs_list(self, node_content: dict, check_type: bool = True):
        if "outputs" not in node_content["parameters"]:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中缺失'outputs'属性"
            )
            return
        if not isinstance(node_content["parameters"]["outputs"], list):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中的'outputs'属性必须为列表类型"
            )
            return
        output_names = set()
        # check each item in the 'outputs' list
        for output_item in node_content["parameters"]["outputs"]:
            if not isinstance(output_item, dict):
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'outputs'列表中的元素必须为字典类型：{output_item}"
                )
                return
            if "name" not in output_item:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'outputs'列表中的元素缺失'name'属性：{output_item}"
                )
            else:
                if output_item["name"] in output_names:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'outputs'列表中的元素'name'属性值必须唯一：{output_item['name']}"
                    )
                output_names.add(output_item["name"])
                self.available_node_output_types[
                    f"{node_content['id']}.{output_item['name']}"
                ] = output_item.get("type", "string")
            if "description" not in output_item:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'outputs'列表中的元素缺失'description'属性：{output_item}"
                )
            if check_type:
                if "type" not in output_item:
                    self.errors.append(
                        f"{node_content['id']}节点, 类型为{node_content['type']}, "
                        f"'parameters'中的'outputs'列表中的元素缺失'type'属性：{output_item}"
                    )
                else:
                    if output_item["type"] not in self.available_variable_types:
                        self.errors.append(
                            f"{node_content['id']}节点, 类型为{node_content['type']}, "
                            f"'parameters'中的'outputs'列表中的元素'type'属性值必须为{self.available_variable_types}中的一个"
                            f"：{output_item['type']}"
                        )

    def _check_config_info(self, node_content: dict, keys: list):
        if "configs" not in node_content["parameters"]:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中缺失'configs'属性"
            )
            return
        if not isinstance(node_content["parameters"]["configs"], dict):
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 'parameters'中的'configs'属性必须为字典类型"
            )
            return
        configs_keys = node_content["parameters"]["configs"].keys()
        for key in keys:
            if key not in configs_keys:
                self.errors.append(
                    f"{node_content['id']}节点, 类型为{node_content['type']}, "
                    f"'parameters'中的'configs'字典中缺失'{key}'属性"
                )

    def _check_next_info(self, node_content: dict):
        if "next" not in node_content:
            self.errors.append(
                f"{node_content['id']}节点, 类型为{node_content['type']}, 缺失'next'属性"
            )
        else:
            self.node_ids_of_next.add(node_content["next"])
