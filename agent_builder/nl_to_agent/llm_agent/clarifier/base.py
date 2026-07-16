# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import json
import re

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.nl_to_agent.base import OperatorInput
from agent_builder.nl_to_agent.llm_agent.utils import call_model, call_model_async
from agent_builder.adapter.exception_bridge import JiuWenBaseException

from .prompt import update_clarifier_system_prompt, PREFIX_ASK, REFLEXION

MAX_PARSE_OPTIONS_LENGTH = 100


class AgentClarifier:
    def __init__(self, llm, controller):
        self.controller = controller
        self.model = llm
        self.need_clarification = True

    @staticmethod
    def format_validation(data):
        """需求澄清输出格式验证"""
        formatted_data = []
        pattern = re.compile(
            r"(（例如：(.*?)等）|例如：(.*?)等|（例如(.*?)等）|例如(.*?)等|（例如：(.*?)）|例如：([^。等]+)|（例如(.*?)）|"
            r"例如([^。等]+)|（比如：(.*?)等）|比如：(.*?)等|（比如(.*?)等）|比如(.*?)等|（比如：(.*?)）|比如：([^。等]+)|"
            r"（比如(.*?)）|比如([^。等]+)|（如：(.*?)等）|如：(.*?)等|（如(.*?)等）|如(.*?)等|（如：(.*?)）|如：([^。等]+)|"
            r"（如(.*?)）|如([^。等]+))"
        )
        try:
            for item in data:
                question = item["question"]
                if len(question.split("？")) == 1:
                    possible_options = str(question.split("：")[1])
                else:
                    possible_options = str(question.split("？")[1])
                original_options = item["options"]
                # 提取示例选项
                example_match = None
                if (
                    possible_options
                    and len(possible_options) < MAX_PARSE_OPTIONS_LENGTH
                ):
                    example_match = pattern.search(possible_options)
                extracted_options = []
                if example_match:
                    example_content = ""
                    for i in range(2, 26):
                        if example_match.group(i):
                            example_content = example_match.group(i)
                            break
                    # 分割示例选项（中文顿号或 / 分割）
                    extracted_options1 = [
                        opt.strip() for opt in example_content.split("、") if opt
                    ]
                    extracted_options2 = [
                        opt.strip() for opt in example_content.split("/") if opt
                    ]
                    extracted_options = (
                        extracted_options1
                        if len(extracted_options1) > len(extracted_options2)
                        else extracted_options2
                    )
                    if len(extracted_options) == 1 or len(extracted_options) < len(
                        original_options
                    ):
                        extracted_options = original_options
                    # 清理question中的示例部分（保留其他括号内容）
                    question = pattern.sub("", question).strip()
                question = question.split("？")[0]
                # 优先使用提取的选项（规则要求覆盖原始options）
                final_options = extracted_options if example_match else original_options
                # 过滤空字符串并保留原始顺序
                final_options = [opt for opt in final_options if opt.strip()]
                formatted_data.append({"question": question, "options": final_options})
            json_output = json.dumps(formatted_data, ensure_ascii=False)
        except Exception:
            logger.error(
                f"Unparseable model response. The output does not conform to the expected schema. root cause = format_validation input data: {data}",
                exc_info=True,
            )
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_LLM_PARSE_FAILED.code,
                StatusCode.NL2AGENT_LLM_PARSE_FAILED.errmsg.format(
                    error_msg="Question without options"
                ),
            )
        return json_output

    def llm_clarify(self, uml_prompts: list) -> str:
        """进行用户澄清"""
        response = call_model(self.model, uml_prompts)
        messages = ""
        for chunk_message in response:
            if chunk_message:
                messages += chunk_message
        return messages

    async def llm_clarify_async(self, uml_prompts: list) -> str:
        """进行用户澄清"""
        response = call_model_async(self.model, uml_prompts)
        messages = ""
        async for chunk_message in response:
            if chunk_message:
                messages += chunk_message
        return messages

    def run(self, inputs: OperatorInput, for_workflow: bool = False):
        """用户澄清执行"""
        dialogue_history = self.controller.context_manager.get_filtered_messages(
            self.controller.task_id, "分类3"
        )
        if for_workflow:
            dialogue_history = self.controller.context_manager.get_filtered_messages(
                self.controller.task_id, "分类1"
            )
        # 更新系统提示词
        system_prompt = {
            "role": "system",
            "content": update_clarifier_system_prompt(
                inputs.plugin_info, inputs.knowledge_info, inputs.sub_workflow_info
            ),
        }
        # 将系统提示词、对话历史（包含用户最新输入指令）结合
        clarifier_prompt = [system_prompt] + dialogue_history
        # clarifier进行需求澄清。response是完整结果（str）
        clarifier_output = self.llm_clarify(clarifier_prompt)
        # 如果进行需求澄清，则需要校验格式
        if PREFIX_ASK in clarifier_output:
            self.need_clarification = True
            count = 0
            while count < 3:
                try:
                    # 提取有效JSON部分
                    clarifier_output = "]".join(clarifier_output.split("]")[1:])
                    start = clarifier_output.find("[")  # 定位JSON数组起始位置
                    end = clarifier_output.find(REFLEXION)  # 定位JSON数组结束位置
                    clarifier_output = clarifier_output[start:end].strip()
                    clarifier_output = json.loads(clarifier_output)
                    break
                except Exception:
                    logger.error("原始生成的需求澄清问题非json格式")
                    clarifier_output = self.llm_clarify(clarifier_prompt)
                    count += 1
            if count >= 3:
                raise RuntimeError("agent clarifier error")
            clarifier_output = self.format_validation(clarifier_output)
        else:
            self.need_clarification = False
        self.controller.clarify_llm(clarifier_output)
        return clarifier_output

    async def arun(self, inputs: OperatorInput, for_workflow: bool = False):
        """用户澄清执行"""
        dialogue_history = self.controller.context_manager.get_filtered_messages(
            self.controller.task_id, "分类3"
        )
        if for_workflow:
            dialogue_history = self.controller.context_manager.get_filtered_messages(
                self.controller.task_id, "分类1"
            )
        # 更新系统提示词
        system_prompt = {
            "role": "system",
            "content": update_clarifier_system_prompt(
                inputs.plugin_info, inputs.knowledge_info, inputs.sub_workflow_info
            ),
        }
        # 将系统提示词、对话历史（包含用户最新输入指令）结合
        clarifier_prompt = [system_prompt] + dialogue_history
        # clarifier进行需求澄清。response是完整结果（str）
        clarifier_output = await self.llm_clarify_async(clarifier_prompt)
        # 如果进行需求澄清，则需要校验格式
        if PREFIX_ASK in clarifier_output:
            self.need_clarification = True
            count = 0
            while count < 3:
                try:
                    # 提取有效JSON部分
                    clarifier_output = "]".join(clarifier_output.split("]")[1:])
                    start = clarifier_output.find("[")  # 定位JSON数组起始位置
                    end = clarifier_output.find(REFLEXION)  # 定位JSON数组结束位置
                    clarifier_output = clarifier_output[start:end].strip()
                    clarifier_output = json.loads(clarifier_output)
                    break
                except Exception:
                    logger.error("原始生成的需求澄清问题非json格式")
                    clarifier_output = await self.llm_clarify_async(clarifier_prompt)
                    count += 1
            if count >= 3:
                raise RuntimeError("agent clarifier error")
            clarifier_output = self.format_validation(clarifier_output)
        else:
            self.need_clarification = False
        await self.controller.async_clarify_llm(clarifier_output)
        return clarifier_output
