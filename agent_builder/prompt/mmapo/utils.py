# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.prompt.mmapo.constant import ApoTuneConstant
from agent_builder.prompt.tune.base.case import (
    Case,
    CaseValidationException,
    CaseManager,
)
from agent_builder.prompt.tune.base.utils import JointParams
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from pydantic import BaseModel

JNT_MODE = "JNT"
MMAPO_MODE = "MMAPO"
WORKERS_NUM = os.environ.get("WORKERS_NUM", 2)


class ProblemExample(BaseModel):
    question: Dict[str, Any]
    image: List[str]
    answer: str
    variable_dict: Dict[str, Any]
    variable_type_dict: Dict[str, Any]


class ApoParams(JointParams):
    minibatch_size: int = ApoTuneConstant.DEFAULT_MINIBATCH_SIZE
    sampled_error_num: int = ApoTuneConstant.DEFAULT_SAMPLED_ERROR_NUM
    gradients_per_error: int = ApoTuneConstant.DEFAULT_GRADIENTS_PER_ERROR
    mc_samples_per_step: bool = ApoTuneConstant.DEFAULT_MC_SAMPLES_PER_STEP
    max_expansion_factor: int = ApoTuneConstant.DEFAULT_MAX_EXPANSION_FACTOR
    eval_budget: int = ApoTuneConstant.DEFAULT_EVAL_BUDGET
    n_gradients: int = ApoTuneConstant.DEFAULT_N_GRADIENTS
    beam_size: int = ApoTuneConstant.DEFAULT_BEAM_SIZE
    num_iter: int = ApoTuneConstant.DEFAULT_NUM_ITER
    early_stop_score: float = ApoTuneConstant.DEFAULT_STOP_SCORE


def get_dataset_multi_modal(cases: List[Case]) -> List[ProblemExample]:
    """get_dataset_multi_modal"""
    dataset = []
    for line in cases:
        # 提取 user 和 assistant 的message
        user_msg = next(
            (
                msg
                for msg in line.messages
                if msg[ApoTuneConstant.MESSAGE_ROLE_KEY] == ApoTuneConstant.USER_ROLE
            ),
            {},
        )
        assistant_msg = next(
            (
                msg
                for msg in line.messages
                if msg[ApoTuneConstant.MESSAGE_ROLE_KEY]
                == ApoTuneConstant.ASSISTANT_ROLE
            ),
            {},
        )

        variable = user_msg.get(ApoTuneConstant.VARIABLE_KEY, {})
        variable_type = user_msg.get(ApoTuneConstant.VARIABLE_TYPE_KEY, {})
        image_names = [
            value
            for key, value in variable.items()
            if variable_type.get(key).lower() == ApoTuneConstant.IMAGE_TYPE_VAR_KEY
            and value
        ]
        text_variable = {
            key: value
            for key, value in variable.items()
            if variable_type.get(key).lower() == ApoTuneConstant.TEXT_TYPE_VAR_KEY
            and value
        }
        answer = assistant_msg.get(ApoTuneConstant.MESSAGE_CONTENT_KEY, "")

        dataset.append(
            ProblemExample(
                image=image_names,
                question=text_variable,
                answer=answer,
                variable_dict=variable,
                variable_type_dict=variable_type,
            )
        )
    return dataset


def is_network_image(image_name: str) -> bool:
    """
    is network image or local image file name
    Args:
        image_name (str): image naem or url
    Returns:
        bool:
    """
    if not isinstance(image_name, str):
        return False
    result = urlparse(image_name)
    # 简单判断：协议为http或https且有网络路径
    return result.scheme in ("http", "https") and bool(result.netloc)


def chat_completion(user_prompt, model):
    """model_inference"""
    messages = [{"role": "user", "content": user_prompt}]
    for attempt in range(ApoTuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES):
        try:
            messages_output = model.chat(messages)
            if not messages_output or messages_output.get("content") is None:
                raise JiuWenBaseException(
                    StatusCode.LLM_FALSE_RESULT_ERROR.code,
                    StatusCode.LLM_FALSE_RESULT_ERROR.errmsg.format(
                        error_msg="call llm service failed."
                    ),
                )
            return messages_output.get("content")
        except (KeyError, AttributeError, TypeError, JiuWenBaseException) as e:
            logger.info(
                f"Inference failed at round {attempt}/{ApoTuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES}: "
                f"{type(e).__name__}"
            )
            if attempt == ApoTuneConstant.DEFAULT_LLM_CHAT_RETRY_TIMES - 1:
                raise e
    return None


class ApoCaseManager(CaseManager):
    """
    A class for managing and validating case data used in prompt optimization.
    It provides functions for data conversion, validation, and structure checking.
    """

    ROLE_SET = {
        ApoTuneConstant.USER_ROLE,
        ApoTuneConstant.SYSTEM_ROLE,
        ApoTuneConstant.ASSISTANT_ROLE,
    }

    @staticmethod
    def apo_validate_with_convert(
        data: List[Dict[str, Any]], original_prompt_placeholder=None
    ) -> List:
        """validate with convert"""
        converted_cases = []
        if not data:
            raise CaseValidationException(
                "Input case is empty", ApoTuneConstant.ROOT_CASE_INDEX
            )

        if len(data) > ApoTuneConstant.DEFAULT_MAX_CASE_NUM:
            raise CaseValidationException(
                f"The number of input cases should be less than {ApoTuneConstant.DEFAULT_MAX_CASE_NUM}",
                ApoTuneConstant.ROOT_CASE_INDEX,
            )

        if not isinstance(data, list) or not isinstance(data[0], dict):
            raise CaseValidationException(
                "Input type is not json-list", ApoTuneConstant.ROOT_CASE_INDEX
            )

        for case_idx, case in enumerate(data):
            messages = ApoCaseManager._get_case_value_with_check(
                case, ApoTuneConstant.MESSAGE_KEY, case_idx
            )
            if not isinstance(messages, list):
                raise CaseValidationException(
                    "Input type is not json-list", ApoTuneConstant.ROOT_CASE_INDEX
                )
            role = ""
            for msg_index, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    raise CaseValidationException(
                        "message in messages is not json-object",
                        ApoTuneConstant.ROOT_CASE_INDEX,
                    )
                role = ApoCaseManager._get_case_value_with_check(
                    msg, ApoTuneConstant.MESSAGE_ROLE_KEY, case_idx
                )
                if role not in ApoCaseManager.ROLE_SET:
                    raise CaseValidationException(
                        f'Invalid role type "{role}" in case-{case_idx}',
                        ApoTuneConstant.ROOT_CASE_INDEX,
                    )

                content = ApoCaseManager._get_case_value_with_check(
                    msg, ApoTuneConstant.MESSAGE_CONTENT_KEY, case_idx
                )
                if not isinstance(content, str):
                    raise CaseValidationException(
                        "content type is not string", ApoTuneConstant.ROOT_CASE_INDEX
                    )
                variable = msg.get(ApoTuneConstant.VARIABLE_KEY, {})
                if not isinstance(variable, dict):
                    raise CaseValidationException(
                        "variable type is not dict", ApoTuneConstant.ROOT_CASE_INDEX
                    )
                variable_type = msg.get(ApoTuneConstant.VARIABLE_TYPE_KEY, {})
                if not isinstance(variable_type, dict):
                    raise CaseValidationException(
                        "variable_type type is not dict",
                        ApoTuneConstant.ROOT_CASE_INDEX,
                    )
                if msg_index < len(messages) - 1:
                    ApoCaseManager.validate_prompt_inputs(
                        variable, variable_type, original_prompt_placeholder, case_idx
                    )

            # 数据集最后一个消息必须为assistant类型
            if role != ApoTuneConstant.ASSISTANT_ROLE:
                raise CaseValidationException(
                    f'The last message role should be "assistant" in case-{case_idx}.',
                    ApoTuneConstant.ROOT_CASE_INDEX,
                )
        return converted_cases

    @staticmethod
    def validate_prompt_inputs(
        variable_dict: Dict[str, Any],
        variable_type_dict: Dict[str, Any],
        original_prompt_placeholder: Optional[List[str]] = None,
        case_idx: int = None,
    ):
        """validate_prompt_inputs"""
        # 1. 检查 key 是否一致
        if not original_prompt_placeholder:
            return
        dict_keys = set(variable_dict.keys())
        type_keys = set(variable_type_dict.keys())
        original_placeholders = set(original_prompt_placeholder)
        if (
            dict_keys != original_placeholders
            or type_keys != original_prompt_placeholder
        ):
            missing_in_dict = (
                type_keys - original_placeholders or original_placeholders - type_keys
            )
            missing_in_type = (
                dict_keys - original_placeholders or original_placeholders - dict_keys
            )

            if missing_in_dict or missing_in_type:
                raise CaseValidationException(
                    f"Variable dictionary and variable type "
                    f"dictionary have mismatched keys in cases {case_idx}.",
                    ApoTuneConstant.ROOT_CASE_INDEX,
                )

        for key, var_type in variable_type_dict.items():
            if not isinstance(var_type, str):
                raise CaseValidationException(
                    f"Variable type for key '{key}' must "
                    f"be a string in cases {case_idx}.",
                    ApoTuneConstant.ROOT_CASE_INDEX,
                )

            lower_type = var_type.lower()
            if lower_type not in [
                ApoTuneConstant.IMAGE_TYPE_VAR_KEY,
                ApoTuneConstant.TEXT_TYPE_VAR_KEY,
            ]:
                raise CaseValidationException(
                    f"Invalid variable type for key '{key}': '{var_type}' "
                    f"in cases {case_idx}.",
                    ApoTuneConstant.ROOT_CASE_INDEX,
                )

            invalid_char_regex = re.compile(r"[^\w\u4e00-\u9fa5]")
            if invalid_char_regex.search(key):
                # 保留原始字符以便诊断
                raise CaseValidationException(
                    f"Invalid characters in key '{key}' in cases {case_idx} "
                    f"Only letters, numbers, underscore '_' and chinese characters are allowed in cases.",
                    ApoTuneConstant.ROOT_CASE_INDEX,
                )
