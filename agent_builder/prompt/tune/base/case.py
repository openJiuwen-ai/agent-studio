# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
prompt tuning cases
"""

from typing import List, Dict, Optional, Any, Callable

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.check_info import CheckInfo
from pydantic import BaseModel, field_validator, Field, FieldValidationInfo


class Case(BaseModel):
    """Definition of prompt optimization user cases."""

    messages: List[Dict] = Field(default=[])
    tools: Optional[List[Dict]] = Field(default=None)

    @field_validator("messages")
    @classmethod
    def check_message_list_content(
        cls, value: List[Dict], info: FieldValidationInfo
    ) -> List[Dict]:
        """check messages"""
        return CheckInfo.check_message_list_content(value, info.field_name)


class CaseValidationException(JiuWenBaseException):
    """
    A custom exception class used to indicate errors that occur during the validation of test cases.
    """

    def __init__(self, message: str, index: int = TuneConstant.ROOT_CASE_INDEX):
        super().__init__(
            StatusCode.PROMPT_OPTIMIZE_CASE_VALIDATION_ERROR.code,
            StatusCode.PROMPT_OPTIMIZE_CASE_VALIDATION_ERROR.errmsg.format(
                error_msg=message
            ),
        )
        self._index = index

    @property
    def error_index(self):
        """Return the index of the error case"""
        return self._index


class CaseInfo(BaseModel):
    """Case information"""

    role: str
    name: str
    content: str
    tools: Any
    tool_calls: Any
    variable: Any


class CaseManager:
    """
    A class for managing and validating case data used in prompt optimization.
    It provides functions for data conversion, validation, and structure checking.
    """

    ROLE_SET = {
        TuneConstant.USER_ROLE,
        TuneConstant.SYSTEM_ROLE,
        TuneConstant.ASSISTANT_ROLE,
        TuneConstant.TOOL_ROLE,
    }

    @staticmethod
    def validate_with_convert(
        data: List[Dict[str, Any]],
        convert_func: Optional[Callable] = None,
        default_tools: Optional[List[Dict]] = None,
    ) -> List:
        """validate with convert"""
        converted_cases = []
        if not data:
            raise CaseValidationException(
                "Input case is empty", TuneConstant.ROOT_CASE_INDEX
            )

        if len(data) > TuneConstant.DEFAULT_MAX_CASE_NUM:
            raise CaseValidationException(
                f"The number of input cases should be less than {TuneConstant.DEFAULT_MAX_CASE_NUM}",
                TuneConstant.ROOT_CASE_INDEX,
            )

        if not isinstance(data, list) or not isinstance(data[0], dict):
            raise CaseValidationException(
                "Input type is not json-list", TuneConstant.ROOT_CASE_INDEX
            )

        for case_idx, case in enumerate(data):
            messages = CaseManager._get_case_value_with_check(
                case, TuneConstant.MESSAGE_KEY, case_idx
            )
            if not isinstance(messages, list):
                raise CaseValidationException(
                    "Input type is not json-list", TuneConstant.ROOT_CASE_INDEX
                )
            tools = case.get(TuneConstant.TOOLS_KEY, None) or default_tools
            role = ""
            for msg_idx, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    raise CaseValidationException(
                        "message in messages is not json-object",
                        TuneConstant.ROOT_CASE_INDEX,
                    )
                role = CaseManager._get_case_value_with_check(
                    msg, TuneConstant.MESSAGE_ROLE_KEY, case_idx
                )
                if role not in CaseManager.ROLE_SET:
                    raise CaseValidationException(
                        f'Invalid role type "{role}" in case-{case_idx}', case_idx
                    )

                content = CaseManager._get_case_value_with_check(
                    msg, TuneConstant.MESSAGE_CONTENT_KEY, case_idx
                )
                tool_calls = msg.get(TuneConstant.MESSAGE_TOOL_CALLS_KEY, [])
                if not tool_calls and not content.strip():
                    raise CaseValidationException(
                        f"Empty message content in case-{case_idx}", case_idx
                    )

                tool_name = msg.get(TuneConstant.NAME_KEY, "")
                variable = msg.get(TuneConstant.VARIABLE_KEY, {})
                if convert_func:
                    convert_func(
                        converted_cases,
                        case_idx,
                        msg_idx == (len(messages) - 1),
                        CaseInfo(
                            role=role,
                            content=content,
                            tools=tools,
                            name=tool_name,
                            tool_calls=tool_calls,
                            variable=variable,
                        ),
                    )

            # 数据集最后一个消息必须为assistant类型
            if role != TuneConstant.ASSISTANT_ROLE:
                raise CaseValidationException(
                    f'The last message role should be "assistant" in case-{case_idx}',
                    case_idx,
                )
        return converted_cases

    @staticmethod
    def convert(cases: List, idx: int, is_last: bool, info: CaseInfo):
        """convert cases"""
        if len(cases) <= idx:
            cases.append(dict(question="", label="", tools=info.tools, variable={}))
        case = cases[-1]
        if info.variable:
            case[TuneConstant.VARIABLE_KEY] = info.variable
        if info.role == TuneConstant.ASSISTANT_ROLE:
            if is_last:
                if not case.get(TuneConstant.QUESTION_KEY, ""):
                    raise CaseValidationException(
                        f"Case-{idx} is not a question-label pair", idx
                    )
                content = str(info.tool_calls) if info.tool_calls else info.content
                case[TuneConstant.LABEL_KEY] = content
            else:
                content = str(info.tool_calls) if info.tool_calls else info.content
                case[TuneConstant.QUESTION_KEY] += f"{info.role}: {content}\n"
        elif info.role == TuneConstant.TOOL_ROLE:
            content = f"{info.role}: name={info.name}, content={info.content}\n"
            case[TuneConstant.QUESTION_KEY] += content
        else:
            content = str(info.tool_calls) if info.tool_calls else info.content
            case[TuneConstant.QUESTION_KEY] += f"{info.role}: {content}\n"

    @staticmethod
    def _get_case_value_with_check(data: Dict[str, Any], key: str, index: int) -> Any:
        """get case value with existence check"""
        value = data.get(key, None)
        if value is None:
            raise CaseValidationException(f'{key} is not in "case-{index}"', index)
        return value
