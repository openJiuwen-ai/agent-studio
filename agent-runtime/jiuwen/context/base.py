#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import Enum
from typing import Union, Dict, List, Any

from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.context.history import ConversationMessage
from jiuwen.prompt.template.base import Template
from pydantic import BaseModel, Field

OPEN_MEMORY = "openMemory"
CONVERSATION_VARIABLES = "conversationVariables"

VARIABLE_NAME_KEY = "name"
VARIABLE_DESC_KEY = "description"
VARIABLE_DEFAULT_KEY = "defaultValue"
VARIABLE_NAME_MAX_LENGTH = 100
VARIABLE_DESC_MAX_LENGTH = 500
VARIABLE_DEFAULT_MAX_LENGTH = 500

DEFAULT_OPEN_MEMORY_CONFIG = False


class ContextConstant:
    DEFAULT_ASYNC_PROCESS_TIMEOUT: float = 10.0
    DEFAULT_ASYNC_TASK_LOOP_PERIOD: float = 0.5

    """compressor config default value"""
    DEFAULT_ASYNC_COMPRESS_TRIGGER_TOKEN_NUM: int = 4096


class ContextWindow(BaseModel):
    """context window definition"""

    user_input: Union[str, Dict] = Field(default="")
    prompt: Template = Field(default=Template(name="", content=""))
    chat_history: List[ConversationMessage] = Field(default=[])
    tools: Union[str, List] = Field(default=[])


class ContextHandleType(Enum):
    UPDATE_NOTHING = "update_nothing"
    UPDATE_COMPRESSED_HISTORY = "update_compressed_history"


class ContextConfig(BaseModel):
    """context config definition"""

    enable_memory: bool = False  # enable memory from context ir config
    mem_variables: List[Dict] = Field(default=[])

    @staticmethod
    def _validate_variables(variables: List[Dict]):
        """validate conversation variables"""
        for variable in variables:
            if (
                not isinstance(variable, dict)
                or not isinstance(variable.get(VARIABLE_NAME_KEY), str)
                or not isinstance(variable.get(VARIABLE_DESC_KEY), str)
            ):
                raise JiuWenBaseException(
                    error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                    message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                        error_msg="The value of conversationVariables should be "
                        "an array containing dictionaries with 'name' and 'description' keys."
                    ),
                )
            # validate field: name
            name = variable[VARIABLE_NAME_KEY]
            description = variable[VARIABLE_DESC_KEY]
            if len(name) > VARIABLE_NAME_MAX_LENGTH or name.find("^") != -1:
                raise JiuWenBaseException(
                    error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                    message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                        error_msg="conversationVariables name field required: length < 100, no '^' allowed."
                    ),
                )
            # validate field: description
            if len(description) > VARIABLE_DESC_MAX_LENGTH:
                raise JiuWenBaseException(
                    error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                    message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                        error_msg="conversationVariables description field required: length < 500."
                    ),
                )

            # validate field: defaultValue
            if (
                not isinstance(variable.get(VARIABLE_DEFAULT_KEY), str)
                or len(variable.get(VARIABLE_DEFAULT_KEY, ""))
                > VARIABLE_DEFAULT_MAX_LENGTH
            ):
                raise JiuWenBaseException(
                    error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                    message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                        error_msg="conversationVariables defaultValue field required: type string and length < 500."
                    ),
                )

    @staticmethod
    def _validate_open_memory(open_memory: bool):
        """validate open memory field"""
        if not isinstance(open_memory, bool):
            raise JiuWenBaseException(
                error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                    error_msg="the value of openMemory should be of boolean type."
                ),
            )

    @classmethod
    def from_config_dict(cls, context_config: Dict[str, Any]):
        """construct contextConfig from a dict
        Args:
            context_config (Dict[str, Any]): a dict of ir config
        Returns:
            ContextConfig
        """
        if not isinstance(context_config, dict):
            raise JiuWenBaseException(
                error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                    error_msg="Invalid contex config which should be a dict."
                ),
            )
        if not context_config:
            return cls()
        open_memory = context_config.get(OPEN_MEMORY, DEFAULT_OPEN_MEMORY_CONFIG)
        conversation_variables = context_config.get(CONVERSATION_VARIABLES, [])
        cls._validate_variables(conversation_variables)
        cls._validate_open_memory(open_memory)
        return cls(enable_memory=open_memory, mem_variables=conversation_variables)
