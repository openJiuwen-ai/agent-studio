# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import os
from typing import Dict, Any

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class TaskParamsValidationException(JiuWenBaseException):
    """Definition of cases validation exception"""

    def __init__(self, message: str):
        super().__init__(
            StatusCode.NL2AGENT_MODEL_INFO_INVALID_ERROR.code,
            StatusCode.NL2AGENT_MODEL_INFO_INVALID_ERROR.errmsg.format(
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


class AgentModelInfoValidator:
    @classmethod
    def validate_model_info(cls, params: Dict[str, Any]) -> None:
        """validate model info"""
        cls._validate_model_info(params, "modelInfo")

    @classmethod
    def _validate_model_info(cls, params: Dict[str, Any], model_field: str) -> None:
        """validate model info details"""
        model_info = validate_parameter(params, model_field, dict)
        model_id = validate_parameter(model_info, "model", str)
        model_source = validate_parameter(model_info, "model_source", str)
        if not model_id.strip():
            raise TaskParamsValidationException(
                "Required parameter 'model' cannot be empty"
            )
        if not model_source.strip():
            raise TaskParamsValidationException(
                "Required parameter 'model_source' cannot be empty"
            )
        model_dict_str = os.environ.get("DEFAULT_MODELS", "{}")
        model_dict = json.loads(model_dict_str)
        if model_source.strip() not in model_dict:
            raise TaskParamsValidationException(
                "Required parameter 'model_source' has wrong value"
            )
        model_config = model_dict.get(model_source, {})
        if model_id not in model_config:
            raise TaskParamsValidationException(
                "Required parameter 'model' has wrong value"
            )
