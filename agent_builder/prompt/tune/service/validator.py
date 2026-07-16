# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
prompt tuning cases
"""

import re
from typing import Dict, Any

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.prompt.tune.base.case import CaseManager
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class TaskParamsValidationException(JiuWenBaseException):
    """Definition of cases validation exception"""

    def __init__(self, message: str):
        super().__init__(
            StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
            StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                error_msg=message
            ),
        )


def validate_parameter(
    params: Dict[str, Any], param_name: str, expected_type, required: bool = True
) -> Any:
    """validate input parameter"""
    if not params:
        raise TaskParamsValidationException("Validation failed while get empty input")
    param = params.get(param_name, None)
    if param is None:
        if required:
            raise TaskParamsValidationException(
                f"Required parameter '{param_name}' is missing"
            )
        return None
    if not isinstance(param, expected_type):
        raise TaskParamsValidationException(
            f"'{param_name}' must be {str(expected_type)}-type"
        )
    return param


class TaskParamsValidator:
    """
    A class for validating the parameters of a task configuration.
    This class provides a set of static and class methods to ensure that all required
    task parameters are present, correctly formatted, and meet the expected constraints.
    """

    @classmethod
    def validate_task_parameters(cls, params: Dict[str, Any]) -> None:
        """validate task parameters"""
        cls._validate_task_name(params)
        cls._validate_task_description(params)
        cls._validate_raw_templates(params)
        OptimizeInfoValidator.validate_optimize_info(params)
        ModelInfoValidator.validate_model_info(params)
        AgentToolsValidator.validate_agent_tools(params)
        logger.info("Validate task parameters successfully.")

    @classmethod
    def _validate_task_name(cls, params: Dict[str, Any]) -> None:
        """validate task name"""
        name = validate_parameter(params, "name", str)
        if not name.strip():
            raise TaskParamsValidationException("task name must not be empty")

    @classmethod
    def _validate_task_description(cls, params: Dict[str, Any]) -> None:
        """validate task description"""
        desc = validate_parameter(params, "desc", str)
        if not desc.strip():
            raise TaskParamsValidationException("task description must not be empty")

    @classmethod
    def _validate_raw_templates(cls, params: Dict[str, Any]) -> None:
        """validate task description"""
        raw_templates = validate_parameter(params, "rawTemplates", str)
        if not raw_templates.strip():
            raise TaskParamsValidationException("raw templates must not be empty")


class OptimizeInfoValidator:
    @classmethod
    def validate_optimize_info(cls, params: Dict[str, Any]) -> None:
        """validate optimize info"""
        optimize_info = params.get("optimizeInfo", None)
        if optimize_info is None:
            raise TaskParamsValidationException(
                "Required parameter 'optimizeInfo' is missing"
            )
        if not isinstance(optimize_info, dict):
            raise TaskParamsValidationException("'optimizeInfo' must be json-type")
        cls._validate_cases(optimize_info)
        cls._validate_iteration_num(optimize_info)
        cls._validate_early_stop_score(optimize_info)
        cls._validate_llm_parallel(optimize_info)
        cls._validate_optimize_method(optimize_info)
        cls._validate_example_num(optimize_info)
        cls._validate_cot_example_num(optimize_info)
        cls._validate_evaluation_method(optimize_info)
        cls._validate_placeholder(optimize_info, params.get("rawTemplates", ""))

    @classmethod
    def _validate_cases(cls, optimize_info: Dict[str, Any]) -> None:
        """validate cases"""
        cases = validate_parameter(optimize_info, "cases", list)
        CaseManager.validate_with_convert(cases)

    @classmethod
    def _validate_iteration_num(cls, optimize_info: Dict[str, Any]) -> None:
        """validate iteration num"""
        num_iter = validate_parameter(optimize_info, "num_iter", int)
        if (
            num_iter < TuneConstant.MIN_ITERATION_NUM
            or num_iter > TuneConstant.MAX_ITERATION_NUM
        ):
            raise TaskParamsValidationException(
                f"num_iter must be in range "
                f"[{TuneConstant.MIN_ITERATION_NUM}, {TuneConstant.MAX_ITERATION_NUM}]"
            )

    @classmethod
    def _validate_early_stop_score(cls, optimize_info: Dict[str, Any]) -> None:
        """validate iteration num"""
        early_stop_score = validate_parameter(
            optimize_info, "early_stop_score", float, required=False
        )
        if early_stop_score is None:
            return
        if (
            early_stop_score < TuneConstant.MIN_EARLY_STOPPING_SCORE
            or early_stop_score > TuneConstant.MAX_EARLY_STOPPING_SCORE
        ):
            raise TaskParamsValidationException(
                f"early_stop_score must be in range "
                f"[{TuneConstant.MIN_EARLY_STOPPING_SCORE},"
                f"{TuneConstant.MAX_EARLY_STOPPING_SCORE}]"
            )

    @classmethod
    def _validate_llm_parallel(cls, optimize_info: Dict[str, Any]) -> None:
        """validate llm parallel""" ""
        llm_parallel = validate_parameter(
            optimize_info, "llm_parallel", int, required=False
        )
        if llm_parallel is None:
            return
        if (
            llm_parallel < TuneConstant.MIN_LLM_PARALLEL_DEGREE
            or llm_parallel > TuneConstant.MAX_LLM_PARALLEL_DEGREE
        ):
            raise TaskParamsValidationException(
                f"llm_parallel must be in range "
                f"[{TuneConstant.MIN_LLM_PARALLEL_DEGREE}, "
                f"{TuneConstant.MAX_LLM_PARALLEL_DEGREE}]"
            )

    @classmethod
    def _validate_optimize_method(cls, optimize_info: Dict[str, Any]) -> None:
        """validate optimize method"""
        optimize_method = validate_parameter(
            optimize_info, "optimize_method", str, required=False
        )
        if not optimize_method:
            return
        if optimize_method != TuneConstant.DEFAULT_OPTIMIZE_METHOD:
            raise TaskParamsValidationException(
                f"optimize_method cannot support type '{optimize_method}'"
            )

    @classmethod
    def _validate_example_num(cls, optimize_info: Dict[str, Any]) -> None:
        """validate example num"""
        example_num = optimize_info.get("example_num", None)
        if example_num is None:
            return
        if isinstance(example_num, str) and example_num.isdigit():
            example_num = int(example_num)
        if not isinstance(example_num, int):
            raise TaskParamsValidationException(
                f"'example_num' must be {str(int)}-type"
            )
        if (
            example_num < TuneConstant.MIN_EXAMPLE_NUM
            or example_num > TuneConstant.MAX_EXAMPLE_NUM
        ):
            raise TaskParamsValidationException(
                f"'example_num' must be in range "
                f"[{TuneConstant.MIN_EXAMPLE_NUM}, {TuneConstant.MAX_EXAMPLE_NUM}]"
            )

    @classmethod
    def _validate_cot_example_num(cls, optimize_info: Dict[str, Any]) -> None:
        """validate cot example num"""
        cot_example_num = optimize_info.get("cot_example_num", None)
        if cot_example_num is None:
            return
        if isinstance(cot_example_num, str) and cot_example_num.isdigit():
            cot_example_num = int(cot_example_num)
        if not isinstance(cot_example_num, int):
            raise TaskParamsValidationException(
                f"'cot_example_num' must be {str(int)}-type"
            )
        if (
            cot_example_num < TuneConstant.MIN_COT_EXAMPLE_NUM
            or cot_example_num > TuneConstant.MAX_COT_EXAMPLE_NUM
        ):
            raise TaskParamsValidationException(
                f"'cot_example_num' must be in range "
                f"[{TuneConstant.MIN_COT_EXAMPLE_NUM}, "
                f"{TuneConstant.MAX_COT_EXAMPLE_NUM}]"
            )

    @classmethod
    def _validate_evaluation_method(cls, optimize_info: Dict[str, Any]) -> None:
        """validate evaluation method"""
        evaluation_method = validate_parameter(
            optimize_info, "evaluation_method", str, required=False
        )
        if evaluation_method is None:
            return
        methods = [
            TuneConstant.EVALUATION_METHOD_TEXT,
            TuneConstant.EVALUATION_METHOD_LLM,
        ]
        if evaluation_method not in methods:
            raise TaskParamsValidationException(
                f"'evaluation_method' must be in {methods}"
            )

    @classmethod
    def _validate_placeholder(cls, optimize_info: Dict[str, Any], prompt: str) -> None:
        """validate placeholder"""
        placeholders = validate_parameter(
            optimize_info, "placeholder", list, required=False
        )
        if not placeholders:
            return
        if not isinstance(placeholders[0], dict):
            raise TaskParamsValidationException("placeholder must be json-type")
        placeholders_in_prompt = re.findall(r"\{\{([\w_]+)\}\}", prompt)
        # 校验占位符中的元素字段
        for ph in placeholders:
            if not ph.get("name"):
                raise TaskParamsValidationException(
                    "Placeholder item 'name' cannot be empty"
                )
            if not ph.get("content"):
                raise TaskParamsValidationException(
                    "Placeholder item 'content' cannot be empty"
                )
            if "need_optimize" not in ph:
                raise TaskParamsValidationException(
                    "Placeholder item 'need_optimize' cannot be empty"
                )

            if not isinstance(ph["name"], str):
                raise TaskParamsValidationException(
                    "Placeholder item 'name' must be a string"
                )
            if not isinstance(ph["content"], str):
                raise TaskParamsValidationException(
                    "Placeholder item 'content' must be a string"
                )
            if not isinstance(ph["need_optimize"], bool):
                raise TaskParamsValidationException(
                    "Placeholder item 'need_optimize' must be a boolean"
                )

        placeholder_names = [ph["name"] for ph in placeholders]
        if len(placeholder_names) != len(set(placeholder_names)):
            raise TaskParamsValidationException(
                "Placeholder name cannot contain duplicates"
            )

        missing_names = [
            name for name in placeholder_names if name not in placeholders_in_prompt
        ]
        if missing_names:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="One or more placeholder names not found in prompt."
                ),
            )


class ModelInfoValidator:
    @classmethod
    def validate_model_info(cls, params: Dict[str, Any]) -> None:
        """validate model info"""
        cls._validate_model_info(params, "modelInfo")
        cls._validate_model_info(params, "assistantInfo")

    @classmethod
    def _validate_model_info(cls, params: Dict[str, Any], model_field: str) -> None:
        """validate model info details"""
        model_info = validate_parameter(params, model_field, dict)
        model_id = validate_parameter(model_info, "model", str)
        if not model_id.strip():
            raise TaskParamsValidationException(
                "Required parameter 'model' cannot be empty"
            )


class AgentToolsValidator:
    @classmethod
    def validate_agent_tools(cls, params: Dict[str, Any]) -> None:
        """validate model info"""
        _ = validate_parameter(params, "agentTools", list, required=False)
