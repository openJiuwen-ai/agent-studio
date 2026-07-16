# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agent builder chain Template optimizer
"""

import json
import re
from datetime import datetime, timezone, timedelta
from os.path import dirname, join, exists
from typing import List, Dict, Optional, Any, Union

import yaml
from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.template.llm_service import LLMServiceManager
from agent_builder.prompt.tune.base.case import Case
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.check_info import CheckInfo
from pydantic import BaseModel, field_validator, Field, FieldValidationInfo

# 将prompt_template存为常量
_prompt_pool: Dict[str, str] = None


class Placeholder(BaseModel):
    """Definition of prompt placeholder."""

    name: str = Field(...)
    content: str = Field(...)
    need_optimize: bool = False


class OptimizeInfo(BaseModel):
    """Definition of prompt optimization info."""

    cases: List[Case] = Field(default=[])
    num_iter: int = Field(default=TuneConstant.DEFAULT_ITERATIONS)
    llm_parallel: Optional[int] = Field(
        default=TuneConstant.DEFAULT_LLM_PARALLEL_DEGREE, gt=0
    )
    example_num: Optional[int] = Field(default=TuneConstant.DEFAULT_EXAMPLE_NUM, ge=0)
    cot_example_num: Optional[int] = Field(default=None, ge=0)
    retry_times: Optional[int] = Field(
        default=TuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES, ge=0
    )
    optimize_method: Optional[str] = Field(default="JOINT")
    placeholder: Optional[List] = Field(default=[])
    eval_mode: Optional[str] = Field(default="LLM", alias="evaluation_method")
    tools: Union[List[Dict[str, Any]], str] = Field(default=[])
    user_compare_rules: str = Field(default="None")
    user_compare_options: str = Field(
        default=TuneConstant.LLM_EVALUATION_TYPE_OBJECTIVE
    )
    early_stop_score: Optional[float] = Field(default=1.0)
    optimize_algo: Optional[str] = Field(default="greedy", alias="optimize_algorithm")
    external_knowledge: Optional[str] = Field(default="None")

    @field_validator("num_iter")
    @classmethod
    def check_int_content(cls, value: int, info: FieldValidationInfo) -> int:
        """check num_iter"""
        return CheckInfo.check_int_content(value, info.field_name)

    @field_validator("cases")
    @classmethod
    def check_list_info(
        cls, value: List[Case], info: FieldValidationInfo
    ) -> List[Case]:
        """check cases"""
        return CheckInfo.check_list_content(value, info.field_name)

    def example_num_assign(self):
        """assign example num and cot example num"""
        if (
            self.cot_example_num is not None
            or self.cot_example_num == TuneConstant.DEFAULT_COT_EXAMPLE_NUM
        ):
            return

        self.cot_example_num = int(
            self.example_num * TuneConstant.DEFAULT_COT_EXAMPLE_RATIO
        )
        self.example_num = self.example_num - self.cot_example_num


class JointParams(BaseModel):
    """Joint parameters."""

    example_num: int = TuneConstant.DEFAULT_EXAMPLE_NUM
    cot_example_num: int = TuneConstant.DEFAULT_COT_EXAMPLE_NUM
    base_instruction: str = ""
    filled_instruction: str = ""
    full_prompt: str = ""
    answer_format: str = ""
    task_description: str = ""
    num_iter: int = TuneConstant.DEFAULT_ITERATIONS
    opt_schema: list = []
    placeholder: list = []
    opt_placeholder: str = ""
    original_placeholder: list = []
    examples: list = []
    cot_examples: list = []
    external_knowledge: str = ""
    early_stop_score: float = TuneConstant.DEFAULT_STOP_SCORE


class OnStopException(JiuWenBaseException):
    def __init__(self, message: str) -> None:
        super().__init__(StatusCode.SUCCESS.code, message)


class LLMModelProcess:
    """Definition of LLM invoke process."""

    chat_llm = None

    def __init__(self, model_info: LLMModelInfo):
        """init"""
        if model_info is None:
            raise JiuWenBaseException(
                error_code=StatusCode.LLM_CONFIG_MISS_ERROR.code,
                message=StatusCode.LLM_CONFIG_MISS_ERROR.errmsg.format(
                    error_msg="the model info input is missing."
                ),
            )
        self.chat_llm = LLMServiceManager.get_llm_backend()
        self.model_info = model_info

    def chat(self, messages: List[dict], tools=None):
        """chat"""
        result = self.chat_llm.chat(
            messages=messages,
            extra_info={"tools": tools},
            model_info=self.model_info,
            add_prefix=False,
            method="full_chat",
        )
        if result.get("code") != 0:
            raise JiuWenBaseException(result.get("code"), result.get("message"))
        return dict(content=result.get("data"))

    def stream_chat(self, messages: List[dict], tools=None):
        """chat"""
        for result in self.chat_llm.chat(
            messages=messages,
            extra_info={"tools": tools},
            model_info=self.model_info,
            add_prefix=False,
            method="stream",
        ):
            if result.get("code") != 0:
                raise JiuWenBaseException(result.get("code"), result.get("message"))
            yield dict(content=result.get("data"))


def check_not_none_with_alias(value, alias):
    """
    Validates that the given value is not None, and raises a specific exception
    with a descriptive message if it is.
    """
    if value is None:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                error_msg=f"{alias} is None"
            ),
        )


def yaml_to_dict(file_path: str) -> Dict:
    """load yaml"""
    with open(file_path, "r", encoding="utf-8") as yaml_file:
        yaml_string = yaml_file.read()
        try:
            parsed_dict = yaml.safe_load(yaml_string)
        except Exception as e:
            raise Exception(
                f"There could be some syntax error in yaml written in {file_path}"
            ) from e

    return parsed_dict


def load_prompt_pool_from_yaml() -> Dict:
    """load_prompt_pool"""
    global _prompt_pool

    if _prompt_pool is not None:
        return _prompt_pool  # 已加载，直接返回

    current_dir = dirname(__file__)
    default_yaml_path = join(current_dir, "../joint_prompt_pool.yaml")
    if not exists(default_yaml_path):
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                error_msg=f"Prompt pool YAML not found: {default_yaml_path}"
            ),
        )
    prompt_pool = yaml_to_dict(default_yaml_path)
    return prompt_pool


def calc_run_time(create_time: str) -> int:
    """Calculate the duration in seconds between the given create_time and the current time."""
    if not create_time:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                error_msg="invalid create_time"
            ),
        )
    try:
        # calculate run time, simple calculation here
        create_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
        cur_time = datetime.now(tz=timezone(timedelta(hours=8))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cur_time = datetime.strptime(cur_time, "%Y-%m-%d %H:%M:%S")
    except Exception as error:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                error_msg="invalid time format"
            ),
        ) from error
    return int((cur_time - create_time).total_seconds())


def placeholder_to_dict(placeholder_list: List, select_all: bool = False) -> Dict:
    """transform placeholder list to dict"""
    if not placeholder_list:
        return {}

    placeholder_dict = {}
    for placeholder in placeholder_list:
        if select_all or placeholder.get("need_optimize"):
            placeholder_dict[placeholder["name"]] = placeholder["content"]
    return placeholder_dict


def example_to_string_list(example_list: List) -> List[str]:
    """transform example list to string"""
    if not example_list:
        return []
    example_format = "[query]: {question}\n[assistant answer]: {answer}"
    example_string_list = []
    for example in example_list:
        example_string_list.append(
            example_format.format(question=example["question"], answer=example["label"])
        )
    return example_string_list


def find_schema(content, start_tag, end_tag):
    """
    find_schema
    """
    start_idx = content.find(start_tag)
    if start_idx == -1:
        return ""

    end_idx = content.find(end_tag, start_idx + len(start_tag))
    if end_idx == -1:
        return ""

    inner_content = content[start_idx + len(start_tag) : end_idx].strip()

    return inner_content


def parse_json(input_string, max_length=10000):
    """Extract a dictionary from a JSON-formatted string"""
    pattern = rf"```json(.{{1,{max_length}}}?)```"
    try:
        match = re.search(pattern, input_string, re.DOTALL)

        if match:
            json_string = match.group(1).strip()
            parsed_data = json.loads(json_string)
            return parsed_data
        logger.info("No ```json...``` block found in input string.")
        return {}
    except json.JSONDecodeError:
        logger.info("An error occurred when JSON parsing")
        return {}
    except Exception:
        logger.info("An error occurred when parse intent JSON from message")
        return {}
