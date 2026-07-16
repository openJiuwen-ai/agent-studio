# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
prompt tuning service interface definition
"""

import re
from typing import List, Optional, Dict

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.tune.base.utils import OptimizeInfo
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.check_info import CheckInfo
from pydantic import BaseModel, Field, FieldValidationInfo, field_validator

TASK_NAME_LENGTH_MIN_LIMIT = 1
TASK_NAME_LENGTH_MAX_LIMIT = 32

TASK_DESC_LENGTH_MIN_LIMIT = 1
TASK_DESC_LENGTH_MAX_LIMIT = 256

GET_JOBS_UPPER_BOUND = 50
GET_JOBS_MIN_LIMIT = 1
GET_JOBS_MAX_LIMIT = 50
GET_JOBS_LIMIT_DEFAULT = 10


class OptimizeTaskCreationRequest(BaseModel):
    """
    A request class for creating a prompt optimization task.
    This class defines the structure of the input data required to create a prompt optimization task,
    including task name, description, raw templates, optimization configuration, model information,
    assistant model information, and agent tools.
    """

    name: str = Field(
        min_length=TASK_NAME_LENGTH_MIN_LIMIT, max_length=TASK_NAME_LENGTH_MAX_LIMIT
    )
    desc: str = Field(
        min_length=TASK_DESC_LENGTH_MIN_LIMIT, max_length=TASK_DESC_LENGTH_MAX_LIMIT
    )
    raw_templates: str = Field(default="", alias="rawTemplates")
    optimize_info: OptimizeInfo = Field(default=OptimizeInfo(), alias="optimizeInfo")
    model_info: LLMModelInfo = Field(
        default=LLMModelInfo(url="", token=""), alias="modelInfo"
    )
    assistant_info: Optional[LLMModelInfo] = Field(default=None, alias="assistantInfo")
    agent_tools: List[Dict] = Field(default=[], alias="agentTools")

    @field_validator("raw_templates")
    @classmethod
    def check_str_content(
        cls, value: List[str], info: FieldValidationInfo
    ) -> List[str]:
        """check raw_templates"""
        check_value = CheckInfo.check_str_content(value, info.field_name)
        ground_placeholder = sorted(re.findall(r"{{([^{}]*?)}}", check_value[0]))
        if not all(
            [
                sorted(re.findall(r"{{([^{}]*?)}}", v)) == ground_placeholder
                for v in check_value
            ]
        ):
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="The number or content of placeholders in rawTemplates are inconsistent"
                ),
            )
        return check_value

    @classmethod
    def strong_field_verification(cls, inputs: dict):
        """strong_field_verification"""
        supported_fields = cls.__fields__
        aliases = [
            field.alias for field in cls.__fields__.values() if field.alias is not None
        ]
        extra_fields = [
            key for key in inputs if key not in supported_fields and key not in aliases
        ]
        if extra_fields:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg="One or more field name is not supported."
                ),
            )


class OptimizeTaskGetInfoRequest(BaseModel):
    """Definition of get jobs request rag."""

    id_list: List[str] = Field(default=[])
