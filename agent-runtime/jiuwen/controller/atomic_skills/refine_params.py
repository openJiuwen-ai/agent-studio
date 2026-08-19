#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Dict, Any, Optional

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.controller.atomic_skills.base import Skill
from jiuwen.controller.atomic_skills.extract_params import (
    ExtractParams,
    ExtractParamsState,
)
from jiuwen.controller.task_planner.planning_modules.prompt_module import ChatContent
from jiuwen.planner.planning_modules.base import PromptPlanningModule
from jiuwen.prompt import TemplateManager


class RefineParams(Skill):
    """参数修正能力"""

    def __init__(self, tools, llm, context_manager):
        super().__init__(tools, llm, context_manager)
        self.prompt_engine = PromptPlanningModule()
        prompt_reflection = TemplateManager().get(name="questioner_update_param")
        if prompt_reflection is not None and hasattr(prompt_reflection, "content"):
            self.prompt_reflection = prompt_reflection.content

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
            task_id = context["conversation_id"]
            workflow_name = context["workflow_name"]
            need_reflection_parameters = context["need_reflection_parameters"]
            parameter_dict = context["param_dict"]

            task_state = self.context_manager.get_param_extraction_context(
                task_id, workflow_name
            )
            extracted_key_fields_dict = self.reflect(
                task_id,
                workflow_name,
                task_state,
                need_reflection_parameters,
                parameter_dict,
            )
            return "", extracted_key_fields_dict
        except Exception as e:
            raise JiuWenBaseException(
                message=f"{StatusCode.CONTROLLER_REFINE_PARAMS_INVOKE_ERROR.errmsg}: {e}",
                error_code=StatusCode.CONTROLLER_REFINE_PARAMS_INVOKE_ERROR.code,
            ) from e

    def reflect(
        self,
        task_id: str,
        workflow_name: str,
        task_state: ExtractParamsState,
        need_reflection_parameters: list,
        original_parameters: dict,
    ):
        """
        reflection at parameters level and improve the result
        """
        try:
            prompt_template_input = self.create_reflect_prompt_input(
                workflow_name, need_reflection_parameters, task_state
            )
            prompt_template = [
                ChatContent(role=p.get("role"), content=p.get("content"))
                for p in self.prompt_reflection
            ]
            prompt = self.prompt_engine.format(
                keywords=prompt_template_input, prompt_template=prompt_template
            )
            logger.info(
                f"QueryOperator Reflect input:{prompt}",
                simple_log="QueryOperator Reflect input",
            )
            llm_inputs = LanguageModelInput(
                messages=ModelUtil.switch_message(prompt), tools=[]
            )
            new_response = self.llm.invoke(llm_inputs).content
            new_response = ExtractParams.parse_llm_response(new_response)
            logger.info(
                f"QueryOperator Reflect Output:{new_response}",
                simple_log="QueryOperator Reflect Output",
            )

            original_parameters.update(new_response)
            task_state.extracted_key_fields_dict.update(original_parameters)
            self.context_manager.set_param_extraction_context(
                task_id, workflow_name, task_state
            )
        except Exception as e:
            raise JiuWenBaseException(
                message=f"{StatusCode.CONTROLLER_REFINE_PARAMS_INVOKE_ERROR.errmsg}: {e}",
                error_code=StatusCode.CONTROLLER_REFINE_PARAMS_INVOKE_ERROR.code,
            ) from e
        return original_parameters

    def create_reflect_prompt_input(
        self, workflow_name, need_reflection_parameters, question_state
    ):
        """create reflection prompt input"""
        chat_history = self.context_manager.get_message_by_intent(workflow_name)
        # 遍历 extracted_key_fields_dict
        required_params_des = {}
        for name in need_reflection_parameters:
            # 获取该字段在 extracted_fields_des_dict 中的描述
            field_description = question_state.extracted_fields_des_dict.get(
                name, "无描述"
            )
            required_params_des.update({name: field_description})
        required_params = []
        for i, (name, desc) in enumerate(required_params_des.items(), 1):
            required_params.append(
                "变量{number}名称：{name}，变量{number}的描述：{desc}".format(
                    number=i, name=name, desc=desc
                )
            )
        dig_history = "\n".join(
            [
                "{role}：{content}".format(
                    role=unit.get("role"), content=unit.get("content")
                )
                for unit in chat_history
            ]
        )
        prompt_template_input = {
            "params_to_reextract": required_params,
            "dialogue_history": dig_history,
        }
        return prompt_template_input
