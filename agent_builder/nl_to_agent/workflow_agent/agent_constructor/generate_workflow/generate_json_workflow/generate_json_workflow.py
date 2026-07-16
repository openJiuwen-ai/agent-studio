# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import json
import re

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.nl_to_agent.workflow_agent.agent_constructor.generate_workflow.generate_json_workflow.prompt import (
    SYSTEM_PROMPT,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.jiuwen_bridge import HumanMessage, SystemMessage, AIMessage

from .reflector import Reflector


class GenerateJsonWorkflow:
    def __init__(self, inputs, mermaid_code, model, input_adapter, controller):
        plugin_info = controller.resource_config.get("plugin", "")
        workflow_info = controller.resource_config.get("workflow", "")
        self.user_prompt = (
            f"{inputs.query}\n\n"
            f"## 当前Mermaid格式的工作流任务流程图：\n{mermaid_code}\n"
            f"## 可使用的插件列表：\n{plugin_info}\n"
            f"## 可使用的工作流列表：\n{workflow_info}"
        )
        self.plugin_dict = controller.plugin_dict
        self.model = model
        self.jiuwen_info = input_adapter.detail_config
        self.controller = controller
        self.reflector = Reflector(
            self.model, controller.plugin_dict, controller.workflow_dict
        )

    @staticmethod
    def _extend_val_name(index):
        if index == 0:
            return ""
        return f"_{str(index)}"

    @staticmethod
    def _replace_common_fragment(source, target):
        # 匹配所有变量格式的片段
        pattern = re.compile(r"(\$\{\w+\}|\{\{\w+\}\})")
        # 提取b中的所有变量
        vars_in_b = pattern.findall(target)
        # 生成所有可能的连续变量组合（按长度降序排列）
        candidates = []
        n = len(vars_in_b)
        for length in range(n, 0, -1):
            for start in range(n - length + 1):
                candidate = "".join(vars_in_b[start : start + length])
                if candidate not in candidates:
                    candidates.append(candidate)
        # 检查候选是否存在于a中，优先替换最长的
        for candidate in candidates:
            if candidate in source:
                return target.replace(candidate, source, 1)  # 仅替换第一个匹配项
        return target

    @staticmethod
    def _process_inputs_list(inputs_list):
        """节点的输入信息后处理，防止引用出错"""
        if not inputs_list:
            return inputs_list
        pattern = r"\$\{((?:(?!\$\{|\}).)*)\}"
        for input_param in inputs_list:
            for key, value in input_param.items():
                if "${" in value and "${" not in value.strip()[:2]:
                    matches = re.findall(pattern, value)
                    value = (
                        " ".join(f"${{{match}}}" for match in matches)
                        if matches
                        else value
                    )
                    input_param[key] = value
        return inputs_list

    def generate(self):
        """生成结果"""
        try:
            prompt = SYSTEM_PROMPT
            for tmp in ("components", "examples", "schema"):
                prompt = prompt.replace(f"{{{{{tmp}}}}}", self.jiuwen_info.get(tmp, ""))
            ir_prompts = [
                SystemMessage(content=prompt),
                HumanMessage(content=self.user_prompt),
            ]
            return self.model.chat(
                ir_prompts, method="stream", add_prefix=False, type="message"
            ), ir_prompts
        except Exception as e:
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_IR_GENERATION_ERROR.code,
                StatusCode.NL2AGENT_IR_GENERATION_ERROR.errmsg.format(
                    error_msg=f"IR生成失败：{str(e)}"
                ),
            ) from e

    async def generate_async(self):
        """生成结果"""
        try:
            prompt = SYSTEM_PROMPT
            for tmp in ("components", "examples", "schema"):
                prompt = prompt.replace(f"{{{{{tmp}}}}}", self.jiuwen_info.get(tmp, ""))
            ir_prompts = [
                SystemMessage(content=prompt),
                HumanMessage(content=self.user_prompt),
            ]
            return self.model.achat(
                ir_prompts, method="stream", add_prefix=False, type="message"
            ), ir_prompts
        except Exception as e:
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_IR_GENERATION_ERROR.code,
                StatusCode.NL2AGENT_IR_GENERATION_ERROR.errmsg.format(
                    error_msg=f"IR生成失败：{str(e)}"
                ),
            ) from e

    def reflect(self, full_response, llm_messages):
        """反思"""
        try:
            llm_messages.append(AIMessage(content=full_response))
            return self.reflector.stream_reflect(full_response, llm_messages)
        except Exception as e:
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_IR_REFLECT_ERROR.code,
                StatusCode.NL2AGENT_IR_REFLECT_ERROR.errmsg.format(
                    error_msg=f"反思失败：{str(e)}"
                ),
            ) from e

    async def reflect_async(self, full_response, llm_messages):
        """反思"""
        try:
            llm_messages.append(AIMessage(content=full_response))
            async for chunk in self.reflector.stream_reflect_async(
                full_response, llm_messages
            ):
                yield chunk

        except JiuWenBaseException as e:
            raise e

        except Exception as e:
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_IR_REFLECT_ERROR.code,
                StatusCode.NL2AGENT_IR_REFLECT_ERROR.errmsg.format(
                    error_msg=f"反思失败：{str(e)}"
                ),
            ) from e

    def post_process(self, content):
        """后处理，解决节点输入信息可能存在的错误，转换成字典"""
        json_data = json.loads(content)
        for data in json_data:
            inputs = data.get("parameters", {}).get("inputs")
            self._process_inputs_list(inputs)
        return json_data
