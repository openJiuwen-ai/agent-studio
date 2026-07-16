# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Dict, Any

from agent_builder.common.logging.base import logger
from agent_builder.prompt.mmapo.utils import ApoCaseManager
from agent_builder.prompt.tune.service.validator import (
    TaskParamsValidator,
    OptimizeInfoValidator,
    ModelInfoValidator,
    TaskParamsValidationException,
    validate_parameter,
)


class ApoTaskParamsValidator(TaskParamsValidator):
    @classmethod
    def validate_task_parameters(cls, params: Dict[str, Any]) -> None:
        """validate task parameters"""
        cls._validate_task_name(params)
        cls._validate_task_description(params)
        cls._validate_raw_templates(params)
        ApoOptimizeInfoValidator.validate_optimize_info(params)
        ModelInfoValidator.validate_model_info(params)
        logger.info("Validate task parameters successfully.")


class ApoOptimizeInfoValidator(OptimizeInfoValidator):
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

    @classmethod
    def _validate_cases(cls, optimize_info: Dict[str, Any]) -> None:
        """validate cases"""
        cases = validate_parameter(optimize_info, "cases", list)
        ApoCaseManager.apo_validate_with_convert(cases)
