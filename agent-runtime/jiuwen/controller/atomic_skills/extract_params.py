#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import ast
import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.controller.atomic_skills.base import Skill
from jiuwen.controller.task_planner.planning_modules.prompt_module import ChatContent
from jiuwen.planner.planning_modules.base import PromptPlanningModule
from jiuwen.prompt import TemplateManager


@dataclass
class ExtractParamsState:
    key_fields_dict: dict = field(default_factory=dict)
    extracted_key_fields_dict: dict = field(default_factory=dict)
    extracted_fields_des_dict: dict = field(default_factory=dict)
    un_extracted_key_fields_dict: dict = field(default_factory=dict)
    max_response: int = 20
    response_num: int = 0


class ExtractParams(Skill):
    """参数提取和追问原子能力"""

    def __init__(self, tools, llm, context_manager):
        super().__init__(tools, llm, context_manager)
        self.prompt_engine = PromptPlanningModule()
        prompt = TemplateManager().get(
            name="questioner", filters={"tag": llm.model_name}
        )
        if prompt is not None and hasattr(prompt, "content"):
            self.prompt = prompt.content

    @staticmethod
    def _is_not_none(value):
        """非None判断"""
        if value is None or (isinstance(value, str) and value.upper() == "NONE"):
            return False
        return True

    def parse_llm_response(self, response: str) -> dict:
        """
        Parse LLM response and extract key fields

        Args:
            response: Raw response from LLM

        Returns:
            Dictionary of extracted key fields with non-None and non-empty values
        """
        # 预处理响应，处理可能的markdown代码块
        cleaned_response = response
        if "```" in response:
            code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
            if code_block_match:
                cleaned_response = code_block_match.group(1).strip()
        # 如果看起来像JSON且包含null，先替换为None
        if cleaned_response.strip().startswith("{"):
            # 替换null为None
            if "null" in cleaned_response:
                cleaned_response = cleaned_response.replace("null", "None")
            # 替换true为True
            if "true" in cleaned_response:
                cleaned_response = re.sub(r"\btrue\b", "True", cleaned_response)
            # 替换false为False
            if "false" in cleaned_response:
                cleaned_response = re.sub(r"\bfalse\b", "False", cleaned_response)
        # 尝试解析响应内容
        try:
            # 首先尝试使用literal_eval，它可以处理Python的None值
            parsed_data = ast.literal_eval(cleaned_response)
            # 过滤掉值为None的键
            return {
                k: v for k, v in parsed_data.items() if self._is_not_none(v) and str(v)
            }
        except (SyntaxError, AttributeError, ValueError) as e:
            # 如果literal_eval失败，尝试预处理后用JSON解析
            try:
                # 将Python风格的None替换为JSON的null
                processed_text = re.sub(r"\bNone\b", "null", cleaned_response)

                # 尝试解析处理后的JSON
                parsed_data = json.loads(processed_text)
                # 过滤掉值为None的键
                return {
                    k: v
                    for k, v in parsed_data.items()
                    if self._is_not_none(v) and str(v)
                }
            except json.JSONDecodeError:
                logger.error(str(e), simple_log="parse llm_response JSONDecodeError")
                return {}
        except Exception as e:
            import traceback

            error_msg = f"原子能力执行失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg, simple_log=f"原子能力执行失败: {type(e)}")
            raise JiuWenBaseException(
                message=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.errmsg,
                error_code=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.code,
            ) from e

    def invoke(self, context: Optional[Dict[str, Any]] = None):
        """
        提问器原子操作
        Args:
            context: 上下文信息
        Returns:
            Event
        """
        # 收到参数缺失事件，基于对话历史提取参数，若全部参数提取完成则重新规划执行，若有参数未提取成功，则提问
        try:
            task_id = context.get("conversation_id", "")
            missing_params_dict = context.get("missing_parameters", {})
            workflow_name = context.get("workflow_name", "")
            prompt_template = context.get("prompt_template", None)
            # 拼接参数名称和描述
            task_state = self.context_manager.get_param_extraction_context(
                task_id, workflow_name
            )
            task_state.key_fields_dict.update(missing_params_dict)
            # 记录已提取过参数的描述
            task_state.extracted_fields_des_dict.update(missing_params_dict)
            self.context_manager.set_param_extraction_context(
                task_id, workflow_name, task_state
            )
            question, extracted_key_fields_dict = (
                self.extraction_rule_base_construction(
                    task_id, workflow_name, task_state, prompt_template
                )
            )
            un_extracted_key_fields = self.get_extract_all_key_fields(
                task_state.key_fields_dict, task_state.extracted_key_fields_dict
            )
            task_state.key_fields_dict = {
                k: v
                for k, v in task_state.key_fields_dict.items()
                if k not in task_state.extracted_key_fields_dict
            }
            self.context_manager.set_param_extraction_context(
                task_id, workflow_name, task_state
            )
            if un_extracted_key_fields:
                return question, extracted_key_fields_dict
            return "", extracted_key_fields_dict
        except Exception as e:
            error_msg = "原子能力执行失败"
            logger.error(error_msg)
            raise JiuWenBaseException(
                message=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.errmsg,
                error_code=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.code,
            ) from e

    def extraction_rule_base_construction(
        self,
        task_id,
        workflow_name,
        task_state: ExtractParamsState,
        prompt_template=None,
    ):
        """
        Construct question in rule-based approach in processing branch of replying directly with
         key fields extractions.
        """
        self.update_key_fields(
            task_id,
            workflow_name,
            task_state.key_fields_dict,
            task_state.extracted_key_fields_dict,
        )
        un_extracted_key_fields = self.get_extract_all_key_fields(
            task_state.key_fields_dict, task_state.extracted_key_fields_dict
        )

        while (
            task_state.response_num < task_state.max_response
            and un_extracted_key_fields
        ):
            question = self.construct_question_based_on_rule(
                task_id,
                workflow_name,
                un_extracted_key_fields,
                task_state.extracted_key_fields_dict,
            )
            task_state.response_num += 1
            logger.info(
                f"question is {question}, extracted_key_fields_dict is {task_state.extracted_key_fields_dict}",
                simple_log="get question and extracted_key_fields_dict content successfully",
            )
            self.context_manager.set_param_extraction_context(
                task_id, workflow_name, task_state
            )
            task_state.un_extracted_key_fields_dict = un_extracted_key_fields
            return question, task_state.extracted_key_fields_dict
        self.context_manager.set_param_extraction_context(
            task_id, workflow_name, task_state
        )
        return "", task_state.extracted_key_fields_dict

    def construct_question_based_on_llm(
        self, task_id, workflow_name, un_extracted_key_fields, extracted_key_fields_dict
    ) -> str:
        """construct question based on llm"""
        try:
            chat_history = self.context_manager.get_message_by_intent(workflow_name)
            dialogue_history = "\n".join(
                [
                    "{role}：{content}".format(
                        role=unit.get("role"), content=unit.get("content")
                    )
                    for unit in chat_history
                ]
            )
            prompt_inputs = {
                "dialogue_history": dialogue_history,
                "system_knowledge": self.get_system_knowledge(
                    task_id=task_id, workflow_name=workflow_name
                ),
                "extracted_params": extracted_key_fields_dict,
                "missing_params": un_extracted_key_fields,
            }
            prompt_template = [
                ChatContent(role=p.get("role"), content=p.get("content"))
                for p in self.prompt_proactive
            ]
            prompt = self.prompt_engine.format(
                keywords=prompt_inputs, prompt_template=prompt_template
            )
            logger.info(f"construct_question_based_on_llm input:{type(prompt)}")
            llm_inputs = LanguageModelInput(
                messages=ModelUtil.switch_message(prompt), tools=[]
            )
            question = self.llm.invoke(llm_inputs).content
        except Exception as e:
            import traceback

            error_msg = f"原子能力执行失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg, simple_log="construct question based on llm error")
            raise JiuWenBaseException(
                message=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.errmsg,
                error_code=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.code,
            ) from e
        return question

    def construct_question_based_on_rule(
        self, task_id, workflow_name, un_extracted_key_fields, extracted_key_fields_dict
    ) -> str:
        """
        construct question based on rule for extracting key fields
        """
        unextracted_cn_field_names = []
        for ky in un_extracted_key_fields:
            for _, value in ky.items():
                unextracted_cn_field_names.append(value)
        question = "请您提供{unextracted_cn_field_names}相关的信息".format(
            unextracted_cn_field_names=", ".join(unextracted_cn_field_names)
        )
        return question

    def update_key_fields(
        self, task_id, workflow_name, key_fields, extracted_key_fields
    ):
        """
        updating key fields
        """
        related_history = self.context_manager.get_message_by_intent(workflow_name)
        cur_extracted_key_fields = self.extract_key_fields(related_history, key_fields)
        cur_extracted_key_fields = {
            k: v for k, v in cur_extracted_key_fields.items() if k in key_fields
        }
        extracted_key_fields.update(cur_extracted_key_fields)

    def extract_key_fields(self, chat_history: list, key_fields) -> dict:
        """
        extract key fields from chat history
        """
        prompt_template_input = self.create_prompt_template_input(
            chat_history, key_fields
        )
        prompt_template = [
            ChatContent(role=p.get("role"), content=p.get("content"))
            for p in self.prompt
        ]
        prompt = self.prompt_engine.format(
            keywords=prompt_template_input, prompt_template=prompt_template
        )
        logger.info(f"QUERY LLM Input {type(prompt)}")
        llm_inputs = LanguageModelInput(
            messages=ModelUtil.switch_message(prompt), tools=[]
        )
        # llm invoke
        try:
            response = self.llm.invoke(llm_inputs).content
        except Exception as e:
            error_msg = "原子能力执行失败"
            logger.error(error_msg)
            raise JiuWenBaseException(
                message=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.errmsg,
                error_code=StatusCode.CONTROLLER_EXTRACT_PARAMS_INVOKE_ERROR.code,
            ) from e
        # 处理LLM的响应并提取字段
        logger.info(f"QUERY LLM Output {type(response)}")
        processed_extracted_key_fields = self.parse_llm_response(response)
        logger.info(
            f"QUERY processed_extracted_key_fields Output {type(processed_extracted_key_fields)}"
        )
        return processed_extracted_key_fields

    def create_prompt_template_input(self, chat_history: list, key_fields) -> dict:
        """
        create input for prompt template
        """
        required_params = []
        for i, (name, desc) in enumerate(key_fields.items(), 1):
            required_params.append(
                "变量{number}名称：{name}，变量{number}的描述：{desc}".format(
                    number=i, name=name, desc=desc
                )
            )

        required_name = []
        for _, item in key_fields.items():
            required_name.append(item)
        required_name = "、".join(required_name) + f"{len(key_fields)}个必要信息"
        logger.info(f"提问器对话历史：\n{type(chat_history)}")
        # input rails for preprocessing
        required_params_list = []
        for name, desc in key_fields.items():
            required_params_list.append("{name}:{desc} ".format(name=name, desc=desc))
        required_params_list = "\n".join(required_params_list)
        required_params = " \n " + " \n ".join(required_params)

        dig_history = self.generate_dig_history(chat_history)

        return {
            "required_params": required_params,
            "dig_history": dig_history,
            "required_name": required_name,
            "required_params_list": required_params_list,
        }

    def generate_dig_history(self, chat_history):
        """优化对话历史拼接逻辑"""
        history_messages = []
        # 处理对话历史
        for unit in chat_history:
            role = unit.get("role", "")
            content = unit.get("content", "")

            # 只有当content不为空时才添加到历史记录
            if content:
                history_messages.append(
                    "{role}：{content}".format(role=role, content=content)
                )
        # 获取最后一条用户消息（如果存在）
        user_response = ""
        if chat_history:
            last_message = chat_history[-1]
            if last_message.get("role") == "user":
                user_response = last_message.get("content", "")
            else:
                # 如果最后一条不是用户消息，不需要额外添加
                user_response = ""
        # 如果有有效的用户响应且不是重复的（不是历史记录的最后一条），添加到历史
        if user_response and (
            not history_messages or not history_messages[-1].endswith(user_response)
        ):
            history_messages.append(f"user：{user_response}")
        # 将历史消息合并为字符串
        dig_history = "\n".join(history_messages) if history_messages else ""
        return dig_history

    def get_extract_all_key_fields(self, key_fields, extracted_key_fields):
        """
        check whether extract all key fields
        """
        un_extracted_key_fields = []
        for name, _ in key_fields.items():
            value = key_fields.get(name)
            if name not in extracted_key_fields or value is None:
                un_extracted_key_fields.append({name: value})
        return un_extracted_key_fields

    def get_system_knowledge(self, task_id, workflow_name):
        """
        获取系统通过工具调用获得但用户尚未感知的信息

        Args:
            task_id: 当前任务ID

        Returns:
            系统已知但用户尚未感知的信息，格式化为字符串
        """
        # 这里你需要根据实际情况实现如何获取系统知识
        # 可能的来源包括：
        # 1. 工具调用结果
        # 2. 数据库查询结果
        # 3. API调用返回的信息
        # 4. 系统内部处理生成的信息

        # 示例实现
        knowledge = []
        # 获取工具调用结果
        tool_results = self.context_manager.get_tool_results(task_id, workflow_name)
        if tool_results:
            for result in tool_results:
                if not result.get(
                    "shared_with_user", False
                ):  # 检查该信息是否已与用户分享
                    knowledge.append(f"{result['name']}: {result['result']}")

        # 获取其他系统知识来源...
        return "\n".join(knowledge) if knowledge else None
