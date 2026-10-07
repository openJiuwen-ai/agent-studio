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
OPEN_COMPRESS = "openCompress"
COMPRESS_CONFIG = "compressConfig"

VARIABLE_NAME_KEY = "name"
VARIABLE_DESC_KEY = "description"
VARIABLE_DEFAULT_KEY = "defaultValue"
VARIABLE_NAME_MAX_LENGTH = 100
VARIABLE_DESC_MAX_LENGTH = 500
VARIABLE_DEFAULT_MAX_LENGTH = 500

DEFAULT_OPEN_MEMORY_CONFIG = False
DEFAULT_OPEN_COMPRESS_CONFIG = False

COMPRESS_TRIGGER_TOKEN_NUM_KEY = "triggerTokenNum"
COMPRESS_KEEP_RECENT_TURNS_KEY = "keepRecentTurns"
COMPRESS_STRATEGY_KEY = "strategy"
COMPRESS_SUMMARY_PROMPT_KEY = "summaryPrompt"

COMPRESS_STRATEGY_SUMMARIZE = "summarize"
COMPRESS_STRATEGY_TRUNCATE = "truncate"
DEFAULT_COMPRESS_KEEP_RECENT_TURNS = 5
COMPRESS_SUMMARY_PROMPT_MAX_LENGTH = 8000


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
    enable_compression: bool = False  # enable long-context compression
    compress_config: Dict[str, Any] = Field(default_factory=dict)

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

    @staticmethod
    def _validate_open_compress(open_compress: bool):
        """validate open compress field"""
        if not isinstance(open_compress, bool):
            raise JiuWenBaseException(
                error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                    error_msg="the value of openCompress should be of boolean type."
                ),
            )

    @staticmethod
    def _parse_compress_config(compress_config: Dict[str, Any]) -> Dict[str, Any]:
        """校验并归一化压缩配置（IR 驼峰键 -> 处理器蛇形键）

        Returns:
            Dict[str, Any]: {
                "trigger_token_num": int, "keep_recent_turns": int,
                "strategy": "summarize" | "truncate", "summary_prompt": str
            }
        """
        if compress_config is None:
            compress_config = {}
        if not isinstance(compress_config, dict):
            raise JiuWenBaseException(
                error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                    error_msg="the value of compressConfig should be of dict type."
                ),
            )

        def _get_positive_int(key: str, default: int) -> int:
            value = compress_config.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise JiuWenBaseException(
                    error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                    message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                        error_msg=f"compressConfig.{key} should be a positive int."
                    ),
                )
            return value

        trigger_token_num = _get_positive_int(
            COMPRESS_TRIGGER_TOKEN_NUM_KEY,
            ContextConstant.DEFAULT_ASYNC_COMPRESS_TRIGGER_TOKEN_NUM,
        )
        keep_recent_turns = _get_positive_int(
            COMPRESS_KEEP_RECENT_TURNS_KEY, DEFAULT_COMPRESS_KEEP_RECENT_TURNS
        )

        strategy = compress_config.get(COMPRESS_STRATEGY_KEY, COMPRESS_STRATEGY_SUMMARIZE)
        if strategy not in (COMPRESS_STRATEGY_SUMMARIZE, COMPRESS_STRATEGY_TRUNCATE):
            raise JiuWenBaseException(
                error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                    error_msg=f"compressConfig.strategy should be one of "
                    f"'{COMPRESS_STRATEGY_SUMMARIZE}', '{COMPRESS_STRATEGY_TRUNCATE}'."
                ),
            )

        summary_prompt = compress_config.get(COMPRESS_SUMMARY_PROMPT_KEY, "")
        if not isinstance(summary_prompt, str) or len(summary_prompt) > (
            COMPRESS_SUMMARY_PROMPT_MAX_LENGTH
        ):
            raise JiuWenBaseException(
                error_code=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.code,
                message=StatusCode.CONTEXT_ENGINE_CONFIG_ERROR.errmsg.format(
                    error_msg=f"compressConfig.{COMPRESS_SUMMARY_PROMPT_KEY} should "
                    f"be a string with length < {COMPRESS_SUMMARY_PROMPT_MAX_LENGTH}."
                ),
            )

        normalized = {
            "trigger_token_num": trigger_token_num,
            "keep_recent_turns": keep_recent_turns,
            "strategy": strategy,
        }
        if summary_prompt:
            normalized["summary_prompt"] = summary_prompt
        return normalized

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
        open_compress = context_config.get(OPEN_COMPRESS, DEFAULT_OPEN_COMPRESS_CONFIG)
        cls._validate_open_compress(open_compress)
        compress_config = cls._parse_compress_config(
            context_config.get(COMPRESS_CONFIG, {})
        )
        return cls(
            enable_memory=open_memory,
            mem_variables=conversation_variables,
            enable_compression=open_compress,
            compress_config=compress_config,
        )
