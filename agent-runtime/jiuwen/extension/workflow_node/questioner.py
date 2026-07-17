# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
Questioner - 提问者节点组件

迁移自商用版本 questioner.py，适配开源版本 openjiuwen Studio 框架。

功能特性:
- 主动询问用户获取必要信息
- 支持 LLM 从对话中自动提取关键字段
- 支持规则构建问题和 LLM 构建问题
- 支持多轮对话，直到获取所有必要信息
- 支持流式/非流式输出模式
- 支持字段类型验证和转换
- 支持自定义提示词模板
- 支持对话历史上下文
- 支持 Rails 护栏系统
- 支持反射机制

设计说明:
- 直接继承 WorkflowComponent（单一继承）
- 通过 Session 管理状态
- 使用 openjiuwen 核心库的 LLM 功能
- 适配 openjiuwen 框架的会话和状态管理
"""

from __future__ import annotations

import ast
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.common.security.exception_utils import ExceptionUtils
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm import (
    BaseMessage,
    UserMessage,
    SystemMessage,
    AssistantMessage,
    Model,
)
from openjiuwen.core.foundation.prompt import PromptTemplate
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.graph.pregel import GraphInterrupt
from openjiuwen.core.session.stream.base import CustomSchema
from openjiuwen.core.workflow import WorkflowComponent
from openjiuwen.core.workflow.components import Session
from pydantic import BaseModel, Field, ConfigDict, ValidationError

# =============================================================================
# 常量定义
# =============================================================================

START_STR = "start"
END_STR = "end"
USER_INTERACT_STR = "user_interact"
PARTIAL_CONTENT = "partial_content"
MESSAGE_NODE_END = "message_end"
WORKFLOW_END = "workflow_end"
WORKFLOW_FINAL = "workflow_final"
JIUWEN_QUESTIONER_TYPE = "jiuwen.questioner"
SUB_WORKFLOW_TYPE = "jiuwen.workflowComposite"

SUB_PLACEHOLDER_PATTERN = r"\{\{([^}]*)\}\}"
CONTINUE_ASK_STATEMENT_ZH = "请您提供{non_extracted_key_fields_names}相关的信息"
CONTINUE_ASK_STATEMENT_EN = (
    "Please provide information related to: {non_extracted_key_fields_names}"
)
WORKFLOW_CHAT_HISTORY = "workflow_chat_history"
TEMPLATE_NAME = "questioner"
QUESTIONER_STATE_KEY = "questioner_state"
USER_FIELDS = "userFields"

QUESTIONER_SYSTEM_TEMPLATE_ZH = """\
你是一个信息收集助手，你需要根据指定的参数收集用户的信息，然后提交到系统。
请注意：不要使用任何工具、不用理会问题的具体含义，并保证你的输出仅有 JSON 格式的结果数据。
请严格遵循如下规则：
  1. 让我们一步一步思考。
  2. 用户输入中没有提及的参数提取为 null，并直接向询问用户没有明确提供的参数。
  3. 通过用户提供的对话历史以及当前输入中提取 {{required_name}}，不要追问任何其他信息。
  4. 参数收集完成后，将收集到的信息通过 JSON 的方式展示给用户。

## Specified Parameters
{{required_params_list}}

## Constraints
{{extra_info}}

## Examples
{{example}}
"""

QUESTIONER_USER_TEMPLATE_ZH = """\
对话历史
{{dialogue_history}}

请充分考虑以上对话历史及用户输入，正确提取最符合约束要求的 JSON 格式参数。
"""

QUESTIONER_SYSTEM_TEMPLATE_EN = """\
You are an information collection assistant. You need to collect user information based on the specified parameters and submit it to the system.
Please note: Do not use any tools, do not consider the specific meaning of the questions, and ensure your output contains only JSON-formatted result data.
Strictly follow these rules:
  1. Let's think step by step.
  2. Parameters not mentioned in user input should be extracted as null, and directly ask the user for parameters not explicitly provided.
  3. Extract {{required_name}} from the conversation history and current user input. Do not ask for any other information.
  4. After parameter collection is complete, display the collected information in JSON format.

## Specified Parameters
{{required_params_list}}

## Constraints
{{extra_info}}

## Examples
{{example}}
"""

QUESTIONER_USER_TEMPLATE_EN = """\
Conversation History
{{dialogue_history}}

Please fully consider the above conversation history and user input, and correctly extract the JSON-formatted parameters that best meet the constraints.
"""

CONTINUE_ASK_SYSTEM_TEMPLATE_ZH = """\
你是一个信息收集助手。根据对话历史和已收集信息，你需要生成一个自然、友好的问题，向用户询问尚未提供的信息。

规则：
1. 只询问还没有提供的信息
2. 保持问题自然、清晰
3. 一次只问一个问题，保持简洁
4. 参考已有的对话上下文

需要询问的信息：
{{required_fields}}

对话历史：
{{dialogue_history}}
"""

CONTINUE_ASK_SYSTEM_TEMPLATE_EN = """\
You are an information collection assistant. Based on the conversation history and collected information, you need to generate a natural and friendly question to ask the user for information not yet provided.

Rules:
1. Only ask for information not yet provided
2. Keep questions natural and clear
3. Ask one question at a time, keep it concise
4. Refer to existing conversation context

Information to ask for:
{{required_fields}}

Conversation history:
{{dialogue_history}}
"""

REFLECTION_SYSTEM_TEMPLATE_ZH = """\
你是一个信息验证助手。请验证以下提取的字段值是否正确。

字段名称：{{field_name}}
提取的值：{{response}}

请仔细检查这个值是否合理、格式是否正确。如果需要修正，请返回修正后的值。
返回格式：{"{{field_name}}": "修正后的值"} 或 {"{{field_name}}": "原值"} 如果值正确。
"""

REFLECTION_SYSTEM_TEMPLATE_EN = """\
You are an information verification assistant. Please verify if the following extracted field value is correct.

Field name: {{field_name}}
Extracted value: {{response}}

Please carefully check if this value is reasonable and if the format is correct. If correction is needed, return the corrected value.
Return format: {"{{field_name}}": "corrected value"} or {"{{field_name}}": "original value"} if the value is correct.
"""

DEFAULT_RAILS_CONFIG = {
    "rails": {"execution": [{"action": "parse_time"}]},
    "actions_config": [{"action": "parse_time", "action_extra_args": {"format": ""}}],
}


# =============================================================================
# 枚举定义
# =============================================================================


class ExecutionStatus(Enum):
    START = START_STR
    USER_INTERACT = USER_INTERACT_STR
    END = END_STR


class QuestionerEvent(Enum):
    START_EVENT = START_STR
    END_EVENT = END_STR
    USER_INTERACT_EVENT = USER_INTERACT_STR


class ResponseType(Enum):
    ReplyDirectly = "reply_directly"
    ReplyBasedOnOptions = "reply"


class QuestionConstructionMethod(Enum):
    RuleBased = "rule_based"
    LLMBased = "llm_based"


# =============================================================================
# 数据类定义
# =============================================================================


class FieldInfo(BaseModel):
    field_name: str
    description: str
    type: str = Field(default="string")
    cn_field_name: str = Field(default="")
    required: bool = Field(default=False)
    default_value: Any = Field(default="")
    reflection: bool = Field(default=False)


class QuestionerInput(BaseModel):
    model_config = ConfigDict(extra="allow")
    query: Union[str, dict, None] = Field(default="")


class OutputCache(BaseModel):
    user_response: Union[str, dict] = Field(default="")
    question: str = Field(default="")
    key_fields: dict = Field(default_factory=dict)


@dataclass
class QuestionerConfig:
    model_name: str
    model_type: str = "agentBuilder"
    name: Optional[str] = None
    response_type: str = ResponseType.ReplyDirectly.value
    extract_fields_from_response: bool = True
    with_chat_history: bool = False
    chat_history_max_rounds: int = 5
    extra_prompt_for_fields_extraction: str = ""
    question_content: str = ""
    question_construction_method: str = QuestionConstructionMethod.RuleBased.value
    cn_fields_name: dict = field(default_factory=dict)
    max_response: int = 3
    option_content: list = field(default_factory=list)
    key_fields: List[FieldInfo] = field(default_factory=list)
    input_complement: bool = False
    type_complement: str = ""
    hyper_parameters: dict = None
    extension: dict = None
    prompt_template: List[BaseMessage] = None
    example_content: str = ""
    rails_config: dict = None
    accept_language: str = "zh"
    # 新增字段（补齐缺失的参数配置）
    allow_node_confirm: bool = Field(default=False)
    need_user_confirm: bool = Field(default=True)
    allow_node_break: bool = Field(default=False)
    enum_visible: bool = Field(default=False)
    user_break: bool = Field(default=False)
    auto_ask_template: str = Field(default="")
    mode: str = Field(default="effect")
    assist_recognize: bool = Field(default=False)
    assist_example: str = Field(default="")
    template_anthropomorphic: bool = Field(default=False)


@dataclass
class QuestionerOutput:
    user_response: str = None
    question: str = None
    key_fields: dict = field(default_factory=dict)

    def __getattr__(self, item):
        return self.key_fields.get(item)

    def update_key_field(self, new_key_fields):
        if new_key_fields is not None:
            self.key_fields.update(new_key_fields)

    def as_dict(self):
        questioner_output = {}
        if self.user_response:
            questioner_output["user_response"] = self.user_response
        if self.question:
            questioner_output["question"] = self.question
        questioner_output.update(self.key_fields)
        return questioner_output


class QuestionerState(BaseModel):
    response_num: int = Field(default=0)
    user_response: Union[str, dict] = Field(default="")
    question: str = Field(default="")
    extracted_key_fields: Dict[str, Any] = Field(default_factory=dict)
    reflection_map: dict = Field(default_factory=dict)
    status: ExecutionStatus = Field(default=ExecutionStatus.START)
    inputs: dict = Field(default_factory=dict)

    @classmethod
    def deserialize(cls, raw_state: dict):
        state = cls.model_validate(raw_state)
        return state.handle_event(QuestionerEvent(state.status.value))

    def serialize(self) -> dict:
        return self.model_dump()

    def handle_event(self, event: QuestionerEvent):
        if event == QuestionerEvent.START_EVENT:
            return QuestionerStartState.from_state(self)
        if event == QuestionerEvent.USER_INTERACT_EVENT:
            return QuestionerInteractState.from_state(self)
        if event == QuestionerEvent.END_EVENT:
            return QuestionerEndState.from_state(self)
        return self

    def is_undergoing_interaction(self):
        return self.status in [ExecutionStatus.USER_INTERACT]

    def is_fresh_state(self):
        return self.status == ExecutionStatus.START and self.response_num == 0


class QuestionerStartState(QuestionerState):
    @classmethod
    def from_state(cls, questioner_state: QuestionerState):
        return cls(
            response_num=questioner_state.response_num,
            user_response=questioner_state.user_response,
            question=questioner_state.question,
            extracted_key_fields=questioner_state.extracted_key_fields,
            reflection_map=questioner_state.reflection_map,
            status=ExecutionStatus.START,
            inputs=questioner_state.inputs,
        )

    def handle_event(self, event: QuestionerEvent):
        if event == QuestionerEvent.USER_INTERACT_EVENT:
            return QuestionerInteractState.from_state(self)
        if event == QuestionerEvent.END_EVENT:
            return QuestionerEndState.from_state(self)
        return self


class QuestionerInteractState(QuestionerState):
    status: ExecutionStatus = Field(default=ExecutionStatus.USER_INTERACT)

    @classmethod
    def from_state(cls, questioner_state: QuestionerState):
        return cls(
            response_num=questioner_state.response_num,
            user_response=questioner_state.user_response,
            question=questioner_state.question,
            extracted_key_fields=questioner_state.extracted_key_fields,
            reflection_map=questioner_state.reflection_map,
            status=ExecutionStatus.USER_INTERACT,
            inputs=questioner_state.inputs,
        )

    def handle_event(self, event: QuestionerEvent):
        if event == QuestionerEvent.END_EVENT:
            return QuestionerEndState.from_state(self)
        return self


class QuestionerEndState(QuestionerState):
    status: ExecutionStatus = Field(default=ExecutionStatus.END)

    @classmethod
    def from_state(cls, questioner_state: QuestionerState):
        return cls(
            response_num=questioner_state.response_num,
            user_response=questioner_state.user_response,
            question=questioner_state.question,
            extracted_key_fields=questioner_state.extracted_key_fields,
            reflection_map=questioner_state.reflection_map,
            status=ExecutionStatus.END,
            inputs=questioner_state.inputs,
        )

    def handle_event(self, event: QuestionerEvent):
        if event == QuestionerEvent.START_EVENT:
            return QuestionerState().handle_event(event)
        return self


# =============================================================================
# 工具类
# =============================================================================


class QuestionerUtils:
    @staticmethod
    def questioner_default_template(accept_language: str = "zh"):
        if accept_language == "en":
            return [
                SystemMessage(content=QUESTIONER_SYSTEM_TEMPLATE_EN),
                UserMessage(content=QUESTIONER_USER_TEMPLATE_EN),
            ]
        return [
            SystemMessage(content=QUESTIONER_SYSTEM_TEMPLATE_ZH),
            UserMessage(content=QUESTIONER_USER_TEMPLATE_ZH),
        ]

    @staticmethod
    def reflection_default_template(accept_language: str = "zh"):
        if accept_language == "en":
            return [SystemMessage(content=REFLECTION_SYSTEM_TEMPLATE_EN)]
        return [SystemMessage(content=REFLECTION_SYSTEM_TEMPLATE_ZH)]

    @staticmethod
    def format_template(template: str, user_fields: dict):
        def replace(match):
            key = match.group(1)
            return str(user_fields.get(key, ""))

        try:
            result = re.sub(SUB_PLACEHOLDER_PATTERN, replace, template)
            return result
        except (KeyError, TypeError, AttributeError):
            return ""

    @staticmethod
    def format_continue_ask_question(
        non_extracted_key_fields: List[FieldInfo], accept_language: str = "zh"
    ):
        non_extracted_key_fields_names = list()
        for param in non_extracted_key_fields:
            non_extracted_key_fields_names.append(
                param.cn_field_name or param.description
            )
        result = ", ".join(non_extracted_key_fields_names)
        template = (
            CONTINUE_ASK_STATEMENT_EN
            if accept_language == "en"
            else CONTINUE_ASK_STATEMENT_ZH
        )
        return template.format(non_extracted_key_fields_names=result)

    @staticmethod
    def format_questioner_output(output_cache: OutputCache) -> Dict:
        output = QuestionerOutput()
        output.update_key_field(output_cache.key_fields)
        output.user_response = output_cache.user_response
        output.question = output_cache.question
        return output.as_dict()

    @staticmethod
    def validate_inputs(inputs):
        try:
            return QuestionerInput.model_validate(inputs)
        except ValidationError as e:
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INPUT_PARAM_ERROR,
                error_msg=ExceptionUtils.format_validation_error(e),
                cause=e,
            ) from e

    @staticmethod
    def is_valid_value(input_value):
        if input_value is None:
            return False
        if input_value in ("", {}, []):
            return False
        if isinstance(input_value, str):
            value = input_value.strip().lower()
            return value not in ("null", "none")
        return True

    @staticmethod
    def validate_and_convert_type(value: Any, expected_type: str) -> Tuple[Any, bool]:
        if value is None:
            return None, False

        try:
            if expected_type == "string":
                return str(value), True

            elif expected_type == "integer":
                if isinstance(value, bool):
                    return None, False
                if isinstance(value, int):
                    return value, True
                if isinstance(value, float):
                    if value == int(value):
                        return int(value), True
                    return None, False
                if isinstance(value, str):
                    cleaned = value.strip()
                    return int(cleaned), True
                return None, False

            elif expected_type == "number":
                if isinstance(value, bool):
                    return None, False
                if isinstance(value, (int, float)):
                    return float(value), True
                if isinstance(value, str):
                    cleaned = value.strip()
                    return float(cleaned), True
                return None, False

            elif expected_type == "boolean":
                if isinstance(value, bool):
                    return value, True
                if isinstance(value, str):
                    cleaned = value.strip().lower()
                    if cleaned == "true":
                        return True, True
                    if cleaned == "false":
                        return False, True
                    return None, False
                return None, False

            else:
                return str(value), True

        except (ValueError, TypeError):
            return None, False

    @staticmethod
    def camel_to_snake(text):
        result = [text[0].lower()]
        for char in text[1:]:
            if char.isupper():
                result.extend(["_", char.lower()])
            else:
                result.append(char)
        return "".join(result)

    @staticmethod
    def dict_keys_camel_to_snake(input_dict):
        output_dict = {}
        for key, value in input_dict.items():
            snake_key = QuestionerUtils.camel_to_snake(key)
            output_dict[snake_key] = value
        return output_dict

    @staticmethod
    def get_latest_k_rounds_chat(chat_history: list, k: int) -> list:
        if k is None:
            return chat_history
        return chat_history[-k * 2 - 1 :]


# =============================================================================
# 直接回复处理器
# =============================================================================


class QuestionerDirectReplyHandler:
    """处理直接回复模式的处理器"""

    def __init__(self):
        self._config = None
        self._model = None
        self._state = None
        self._prompt = None
        self._reflection_prompt = None
        self._query = ""
        self._default_rail = None
        self._execute_rail = None
        self._input_rail = None
        self._session = None

    def config(self, config: QuestionerConfig):
        self._config = config
        return self

    def model(self, model: Model):
        self._model = model
        return self

    def state(self, state: QuestionerState):
        self._state = state
        return self

    def get_state(self):
        return self._state

    def prompt(self, prompt):
        self._prompt = prompt
        return self

    def reflection_prompt(self, reflection_prompt):
        self._reflection_prompt = reflection_prompt
        return self

    def rails(self, default_rail=None, execute_rail=None, input_rail=None):
        self._default_rail = default_rail
        self._execute_rail = execute_rail
        self._input_rail = input_rail
        return self

    async def handle(self, inputs: Input, session: Session, context):
        self._session = session
        if self._state.status == ExecutionStatus.START:
            return await self._handle_start_state(inputs, session, context)
        if self._state.status == ExecutionStatus.USER_INTERACT:
            return await self._handle_user_interact_state(inputs, session, context)
        if self._state.status == ExecutionStatus.END:
            return self._handle_end_state(inputs, session, context)
        return dict()

    async def _handle_start_state(self, inputs, session, context):
        questioner_input = QuestionerUtils.validate_inputs(inputs)
        output = OutputCache()
        self._query = questioner_input.query or ""

        await self._write_user_message_to_context(self._query, context)

        chat_history = await self._get_latest_chat_history(context)

        if self._is_set_question_content():
            user_fields = questioner_input.model_dump(exclude={"query"})
            output.question = QuestionerUtils.format_template(
                self._config.question_content, user_fields
            )
            self._update_questioner_states_question(output.question)
            self._state = self._state.handle_event(QuestionerEvent.USER_INTERACT_EVENT)

            await session.trace(data={"user": self._query})
            await session.trace(data={"assistant": output.question})
            await self._write_assistant_message_to_context(output.question, context)
            return QuestionerUtils.format_questioner_output(output)

        if self._config.extract_fields_from_response:
            if self._need_extract_fields():
                is_continue_ask = await self._initial_extract_from_chat_history(
                    chat_history, output
                )
                event = (
                    QuestionerEvent.USER_INTERACT_EVENT
                    if is_continue_ask
                    else QuestionerEvent.END_EVENT
                )
                if is_continue_ask:
                    self._update_questioner_states_question(output.question)
                    await session.trace(data={"user": self._query})
                    await session.trace(data={"assistant": output.question})
                    await self._write_assistant_message_to_context(output.question, context)
                else:
                    await session.trace(data={"user": self._query})
                    await self._write_assistant_message_to_context(
                        json.dumps(output.key_fields, ensure_ascii=False), context
                    )
                self._state = self._state.handle_event(event)
            else:
                self._state = self._state.handle_event(QuestionerEvent.END_EVENT)
        else:
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INPUT_INVALID,
                error_msg="question_content is empty and no extractable fields are configured"
            )
        return QuestionerUtils.format_questioner_output(output)

    async def _handle_user_interact_state(self, inputs, session, context):
        await self._get_latest_human_feedback(session)
        output = OutputCache(question=self._state.question, user_response=self._query)

        # Write user feedback message to context at USER_INTERACT state
        await self._write_user_message_to_context(self._query, context)

        chat_history = await self._get_latest_chat_history(context)
        user_response = chat_history[-1].content if chat_history else ""

        if self._is_set_question_content() and not self._need_extract_fields():
            output.user_response = user_response
            await session.trace(data={"user": user_response})
            self._state = self._state.handle_event(QuestionerEvent.END_EVENT)
            return QuestionerUtils.format_questioner_output(output)

        if self._config.extract_fields_from_response:
            if self._need_extract_fields():
                is_continue_ask = await self._initial_extract_from_chat_history(chat_history, output)
                event = QuestionerEvent.USER_INTERACT_EVENT if is_continue_ask else QuestionerEvent.END_EVENT
                if is_continue_ask:
                    self._update_questioner_states_question(output.question)
                    await session.trace(data={"user": user_response})
                    await session.trace(data={"assistant": output.question})
                    await self._write_assistant_message_to_context(output.question, context)
                else:
                    await session.trace(data={"user": user_response})
                    await self._write_assistant_message_to_context(
                        json.dumps(output.key_fields, ensure_ascii=False), context
                    )
                self._state = self._state.handle_event(event)
            else:
                self._state = self._state.handle_event(QuestionerEvent.END_EVENT)
        else:
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INPUT_INVALID,
                error_msg="question_content is empty and no extractable fields are configured"
            )
        return QuestionerUtils.format_questioner_output(output)

    def _handle_end_state(self, inputs, session, context):
        output = QuestionerOutput()
        output.update_key_field(self._state.extracted_key_fields)
        output.user_response = self._state.user_response
        output.question = self._state.question
        return output.as_dict()

    def _is_set_question_content(self):
        return (
            isinstance(self._config.question_content, str)
            and len(self._config.question_content) > 0
        )

    def _need_extract_fields(self):
        return self._config.extract_fields_from_response and len(
            self._config.key_fields
        ) > len(self._state.extracted_key_fields)

    async def _initial_extract_from_chat_history(
        self, chat_history, output: OutputCache
    ) -> bool:
        await self._invoke_llm_and_parse_result(chat_history, output)

        self._update_param_default_value(output)
        self._update_state_of_key_fields(output.key_fields)

        return self._check_if_continue_ask(output)

    async def _repeat_extract_from_chat_history(
        self, chat_history, output: OutputCache
    ) -> bool:
        await self._invoke_llm_and_parse_result(chat_history, output)

        self._update_param_default_value(output)
        self._update_state_of_key_fields(output.key_fields)

        return self._check_if_continue_ask(output)

    async def _get_latest_chat_history(self, context) -> List:
        result = list()
        if self._config.with_chat_history and context is not None:
            dialogue_round = (
                self._config.chat_history_max_rounds
                if self._config.chat_history_max_rounds > 0
                else None
            )
            context_window = await context.get_context_window(
                dialogue_round=dialogue_round
            )
            if context_window is not None:
                result = context_window.get_messages()

        if not result or result[-1].role in ["assistant"]:
            content = self._query
            if isinstance(content, dict):
                content = [content]
            result.append(UserMessage(role="user", content=content))
        return result

    def _build_llm_inputs(self, chat_history: list = None) -> List[BaseMessage]:
        prompt_template_input = self._create_prompt_template_keywords(chat_history)
        formatted_template: PromptTemplate = self._prompt.format(prompt_template_input)
        return formatted_template.to_messages()

    def _create_prompt_template_keywords(self, chat_history: List[BaseMessage]):
        params_list, required_name_list = list(), list()
        for param in self._config.key_fields:
            params_list.append(f"{param.field_name}: {param.description}")
            if param.required:
                required_name_list.append(param.cn_field_name or param.description)

        lang = self._config.accept_language
        if lang == "en":
            required_name_str = (
                ", ".join(required_name_list)
                + f" ({len(required_name_list)} required field(s))"
            )
            dialogue_history_str = "\n".join(
                [f"{_.role}: {_.content}" for _ in chat_history]
            )
        else:
            required_name_str = (
                "、".join(required_name_list) + f"{len(required_name_list)}个必要信息"
            )
            dialogue_history_str = "\n".join(
                [f"{_.role}：{_.content}" for _ in chat_history]
            )

        return dict(
            required_name=required_name_str,
            required_params_list="\n".join(params_list),
            extra_info=self._config.extra_prompt_for_fields_extraction or "",
            example=self._config.example_content or "",
            dialogue_history=dialogue_history_str,
        )

    async def _invoke_llm_for_extraction(self, llm_inputs: List[BaseMessage]) -> dict:
        response = ""

        workflow_logger.info(
            "Questioner LLM extraction started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="Questioner",
        )

        await self._session.trace(data={"llm_inputs": llm_inputs})

        try:
            response = (await self._model.invoke(messages=llm_inputs)).content
        except Exception as e:
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INVOKE_CALL_FAILED,
                error_msg="failed to invoke llm for extraction",
                cause=e,
            ) from e

        await self._session.trace(data={"llm_outputs": response})

        workflow_logger.info(
            "Questioner LLM extraction completed",
            event_type=LogEventType.WORKFLOW_COMPONENT_END,
            component_type_str="Questioner",
        )

        result = dict()
        try:
            cleaned = self._extract_json_from_text(response)
            result = json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            try:
                cleaned = self._extract_json_from_text(response)
                result = ast.literal_eval(cleaned)
            except (SyntaxError, ValueError):
                workflow_logger.error(
                    "Questioner JSON parse failed",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="Questioner",
                )
                return result

        if not isinstance(result, dict):
            return {}

        result = {k: v for k, v in result.items() if QuestionerUtils.is_valid_value(v)}

        result = await self._reflection(result)

        result = await self._apply_rails(result)

        result = self._validate_and_convert_fields(result)
        return result

    def _extract_json_from_text(self, text: str) -> str:
        text = text.strip()

        json_patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"'''json\s*([\s\S]*?)\s*'''",
            r"```\s*([\s\S]*?)\s*```",
            r"'''\s*([\s\S]*?)\s*'''",
        ]

        for pattern in json_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        start_brace = text.find("{")
        end_brace = text.rfind("}")
        if start_brace != -1 and end_brace != -1 and start_brace < end_brace:
            return text[start_brace : end_brace + 1]

        return text

    async def _reflection(self, cur_extracted_key_fields: dict) -> dict:
        """反射机制：对提取的字段进行二次验证"""
        if not self._reflection_prompt:
            return cur_extracted_key_fields

        try:
            for field_info in self._config.key_fields:
                extract_value = cur_extracted_key_fields.get(field_info.field_name)
                if (
                    extract_value
                    and field_info.reflection
                    and self._state.reflection_map.get(field_info.field_name)
                    != extract_value
                ):
                    prompt_template_input = {
                        "field_name": field_info.field_name,
                        "response": {field_info.field_name: extract_value},
                    }

                    formatted_template: PromptTemplate = self._reflection_prompt.format(
                        prompt_template_input
                    )
                    llm_inputs = formatted_template.to_messages()

                    new_response = (
                        await self._model.invoke(messages=llm_inputs)
                    ).content
                    try:
                        cleaned = self._extract_json_from_text(new_response)
                        new_result = json.loads(cleaned, strict=False)
                        if isinstance(new_result, dict):
                            new_result = {
                                k: v
                                for k, v in new_result.items()
                                if k == field_info.field_name
                            }
                            self._state.reflection_map.update(new_result)
                            cur_extracted_key_fields.update(new_result)
                    except (SyntaxError, ValueError):
                        pass

        except Exception as e:
            workflow_logger.warning(
                "Questioner reflection failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=e,
            )

        return cur_extracted_key_fields

    async def _apply_rails(self, cur_extracted_key_fields: dict) -> dict:
        """应用 Rails 护栏进行值转换"""
        if self._config.input_complement and self._default_rail:
            try:
                output = await self._default_rail.ainvoke(
                    {"arguments": cur_extracted_key_fields}
                )
                result = output.get("arguments")
                if result:
                    cur_extracted_key_fields = result
            except Exception as e:
                workflow_logger.warning(
                    "Questioner default rail failed",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    exception=e,
                )

        if self._execute_rail and self._config.rails_config:
            try:
                rail_result = await self._execute_rail.ainvoke(
                    {
                        "arguments": cur_extracted_key_fields,
                        "inputs": self._state.inputs,
                        "outputs": [f.model_dump() for f in self._config.key_fields],
                        "extracted_args": self._state.extracted_key_fields,
                    }
                )
                result = rail_result.get("arguments")
                if result and isinstance(result, dict):
                    cur_extracted_key_fields = result
            except Exception as e:
                workflow_logger.warning(
                    "Questioner custom rail failed",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    exception=e,
                )

        return cur_extracted_key_fields

    def _validate_and_convert_fields(self, extracted_result: dict) -> dict:
        field_type_map = {f.field_name: f.type for f in self._config.key_fields}

        validated_result = {}
        for field_name, value in extracted_result.items():
            expected_type = field_type_map.get(field_name, "string")
            converted_value, is_valid = QuestionerUtils.validate_and_convert_type(
                value, expected_type
            )

            if is_valid:
                validated_result[field_name] = converted_value
            else:
                workflow_logger.warning(
                    "Questioner field validation failed",
                    event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                    component_type_str="Questioner",
                    metadata={
                        "field_name": field_name,
                        "value": str(value),
                        "expected_type": expected_type,
                    },
                )

        return validated_result

    def _filter_non_extracted_key_fields(self) -> List[FieldInfo]:
        result = []
        for item in self._config.key_fields:
            if (
                item.required
                and item.field_name not in self._state.extracted_key_fields
            ):
                result.append(item)
        return result

    def _update_state_of_key_fields(self, key_fields):
        for k, v in key_fields.items():
            if v:
                self._state.extracted_key_fields.update({k: v})

    def _update_param_default_value(self, output: OutputCache):
        result = dict()
        extracted_key_fields = self._state.extracted_key_fields
        for param in self._config.key_fields:
            param_name = param.field_name
            default_value = param.default_value
            if default_value and param_name not in extracted_key_fields:
                result.update({param_name: default_value})
        output.key_fields.update(result)

    def _increment_state_of_response_num(self):
        self._state.response_num += 1

    def _exceed_max_response(self):
        return self._state.response_num >= self._config.max_response

    def _check_if_continue_ask(self, output: OutputCache):
        is_continue_ask = False
        non_extracted_key_fields: List[FieldInfo] = (
            self._filter_non_extracted_key_fields()
        )
        if non_extracted_key_fields:
            if not self._exceed_max_response():
                if (
                    self._config.question_construction_method
                    == QuestionConstructionMethod.RuleBased.value
                ):
                    output.question = QuestionerUtils.format_continue_ask_question(
                        non_extracted_key_fields, self._config.accept_language
                    )
                else:
                    output.question = self._generate_question_with_llm_sync(
                        non_extracted_key_fields
                    )
                is_continue_ask = True
            else:
                raise build_error(
                    StatusCode.COMPONENT_QUESTIONER_RUNTIME_ERROR,
                    error_msg="max_response reached before all required fields were extracted",
                )
        if is_continue_ask:
            output.key_fields.clear()
        else:
            output.key_fields.update(self._state.extracted_key_fields)
        return is_continue_ask

    def _generate_question_with_llm_sync(
        self, non_extracted_key_fields: List[FieldInfo]
    ) -> str:
        """同步生成问题（简化版本）"""
        return QuestionerUtils.format_continue_ask_question(
            non_extracted_key_fields, self._config.accept_language
        )

    async def _invoke_llm_and_parse_result(self, chat_history, output):
        llm_inputs = self._build_llm_inputs(chat_history=chat_history)
        extracted_key_fields = await self._invoke_llm_for_extraction(llm_inputs)
        for k, v in extracted_key_fields.items():
            if v:
                output.key_fields.update({k: v})

        self._update_state_of_key_fields(extracted_key_fields)

    async def _get_latest_human_feedback(self, session):
        for _ in range(self._state.response_num + 1):
            self._query = await session.interact(self._state.question)
        self._increment_state_of_response_num()

    def _update_questioner_states_question(self, question):
        self._state.question = question

    async def _write_user_message_to_context(self, content, context):
        if context is None or not self._config.with_chat_history:
            return

        if not content:
            return

        user_message = UserMessage(role="user", content=content)
        await context.add_messages([user_message])

    async def _write_assistant_message_to_context(self, content, context):
        if context is None or not self._config.with_chat_history:
            return

        if not content:
            return

        assistant_message = AssistantMessage(role="assistant", content=content)
        await context.add_messages([assistant_message])


# =============================================================================
# 主组件类
# =============================================================================


class Questioner(WorkflowComponent):
    """工作流提问者节点组件

    迁移自商用版本 Questioner，适配开源版本框架。

    职责:
    1. 主动询问用户获取必要信息
    2. 通过 LLM 从对话中自动提取关键字段
    3. 支持多轮对话，直到获取所有必要信息
    4. 支持字段类型验证和转换
    5. 支持自定义提示词模板
    6. 支持 Rails 护栏系统
    7. 支持反射机制
    """

    def __init__(self, conf: Union[QuestionerConfig, dict]):
        super().__init__()
        if isinstance(conf, dict):
            self._outputs = conf.get("userFields", {}).get("outputs", [])
            conf.pop("userFields", None)
            conf.pop("systemFields", None)
        else:
            self._outputs = []
        self._config = (
            conf if isinstance(conf, QuestionerConfig) else QuestionerConfig(**conf)
        )
        self._node_state = QuestionerState()
        self._model: Optional[Model] = None
        self._prompt: Optional[PromptTemplate] = None
        self._reflection_prompt: Optional[PromptTemplate] = None
        self._initialized = False
        self._default_rail = None
        self._execute_rail = None
        self._input_rail = None
        self._stream_output: Optional[dict] = None
        self._node_name: Optional[str] = self._config.name or None

        self._init_prompt()

    def _init_prompt(self):
        if self._config.prompt_template:
            prompt_content = self._config.prompt_template
        else:
            prompt_content = QuestionerUtils.questioner_default_template(
                self._config.accept_language
            )
        self._prompt = PromptTemplate(content=prompt_content)

        self._reflection_prompt = PromptTemplate(
            content=QuestionerUtils.reflection_default_template(
                self._config.accept_language
            )
        )

    async def _initialize_model(self):
        if self._initialized:
            return

        try:
            from agent_runtime.common.model_adapters import adapt_questioner_config
            from agent_runtime.common.model_providers import IRModelConfigProvider

            adapted_conf = adapt_questioner_config(
                model_name=self._config.model_name,
                hyper_parameters=self._config.hyper_parameters or {},
                extension=self._config.extension or {},
            )

            from jiuwen.serve.controllers.execution.ir_converter import _get_model_config_provider

            provider = _get_model_config_provider()
            llm_comp_config = await provider.get_llm_config(adapted_conf)

            self._model = Model(
                model_client_config=llm_comp_config.model_client_config,
                model_config=llm_comp_config.model_config,
            )
            self._initialized = True
        except Exception as e:
            workflow_logger.error(
                "Failed to initialize model",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=e,
            )
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INVOKE_CALL_FAILED,
                error_msg="failed to initialize model",
                cause=e,
            ) from e

    @staticmethod
    def _load_state_from_session(session: Session) -> QuestionerState:
        questioner_state = session.get_state()
        state_dict = None
        if isinstance(questioner_state, dict):
            state_dict = questioner_state.get(QUESTIONER_STATE_KEY)
        if state_dict:
            return QuestionerState.deserialize(state_dict)
        return QuestionerState()

    @staticmethod
    def _store_state_to_session(state: QuestionerState, session: Session):
        state_dict = state.serialize()
        session.update_state({QUESTIONER_STATE_KEY: state_dict})

    def should_interrupt(self) -> bool:
        return self._node_state.status == ExecutionStatus.USER_INTERACT

    def get_state(self) -> QuestionerState:
        return self._node_state

    def get_stream_output(self):
        return self._stream_output

    def load_state(self, state: QuestionerState) -> None:
        self._node_state = deepcopy(state)

    def get_node_status(self) -> ExecutionStatus:
        return self._node_state.status

    def error_to_output(self) -> None:
        self._node_state.status = ExecutionStatus.END

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        try:
            await self._initialize_model()

            state_from_session = self._load_state_from_session(session)
            has_saved_state = state_from_session.is_undergoing_interaction()
            if has_saved_state:
                current_state = state_from_session
            else:
                current_state = QuestionerState()

            self._node_state = current_state

            invoke_result = dict()
            if self._config.response_type == ResponseType.ReplyDirectly.value:
                if not has_saved_state:
                    temp_state = QuestionerState()
                    invoke_result = await self._handle_questioner_direct_reply_safe(
                        inputs, session, context, temp_state
                    )
                    current_state = invoke_result.pop("_state", temp_state)
                    self._node_state = current_state
                else:
                    # 恢复执行：使用保存的状态继续处理用户的回复
                    invoke_result = await self._handle_questioner_direct_reply_safe(
                        inputs, session, context, current_state
                    )
                    current_state = invoke_result.pop("_state", current_state)
                    self._node_state = current_state

            if current_state.is_undergoing_interaction():
                self._store_state_to_session(current_state, session)
                # 写入 CustomSchema（由 WorkflowWrapper 转换为旧框架 StreamData）
                node_id = session.get_component_id()
                parent_id = None
                if getattr(getattr(session, "_inner", None), "_parent_id"):
                    parent_id = getattr(getattr(session, "_inner", None), "_parent_id")
                # 构建 user_fields，包含配置的 outputs 字段和当前提取的 key_fields
                user_fields = {}
                for output_def in self._outputs:
                    field_id = output_def.get("id") if isinstance(output_def, dict) else output_def
                    if field_id:
                        if field_id == "USER_RESPONSE" or field_id == "QUESTION" and\
                            not current_state.extracted_key_fields.get(field_id, ""):
                            continue
                        user_fields[field_id] = current_state.extracted_key_fields.get(field_id, "")
                # 合并 Start 节点写入 global_state 的 userFields
                # 匹配旧框架 final_output 累积行为：Start 写入 card_id 后，
                # Questioner 中断不会覆盖 final_output，所以 FINISH 保留了 Start 的 userFields
                start_user_fields = session.get_global_state("start_user_fields") or {}
                if isinstance(start_user_fields, dict):
                    user_fields = {**start_user_fields, **user_fields}
                custom_data = {
                    "answer": invoke_result.get("question", ""),
                    "result": invoke_result.get("question", ""),
                    "node_id": node_id,
                    "node_name": self._node_name or node_id,
                    "node_type": JIUWEN_QUESTIONER_TYPE,
                    "should_interrupt": True,
                    "userFields": user_fields,
                }
                if parent_id:
                    custom_data["parentNodeId"] = parent_id
                    custom_data["workflow_id"] = session.get_workflow_id()
                await session.write_custom_stream(
                    CustomSchema(
                        type=PARTIAL_CONTENT, index=0, data=custom_data
                    ).model_dump(by_alias=True, exclude_none=False, exclude_unset=False)
                )
                await session.write_custom_stream(
                    CustomSchema(
                        type=MESSAGE_NODE_END, index=1, data=custom_data
                    ).model_dump(by_alias=True, exclude_none=False, exclude_unset=False)
                )
                self._stream_output = custom_data
                self._node_state.status = ExecutionStatus.END
                # 使用 session.interact() 替代手动 raise GraphInterrupt
                # session.interact() 会自动执行 commit_cmp() + OutputSchema(INTERACTION) + raise GraphInterrupt
                if not parent_id:
                    session.update_global_state({"has_interaction": True})
                await session.interact(invoke_result.get("question", ""))
            else:
                new_state = QuestionerState()
                self._node_state = new_state
                self._store_state_to_session(new_state, session)
                # 转换字段名以适配 IR 配置（例如 user_response -> USER_RESPONSE）
                invoke_result = self._convert_output_field_names(invoke_result)
                # 包裹 userFields 命名空间，与旧框架输出格式一致
                # End 节点通过 ${node_id.userFields.field_name} 引用
                invoke_result = {USER_FIELDS: invoke_result}

            return invoke_result

        except GraphInterrupt:
            raise  # 向上传播，由框架处理 checkpoint 保存
        except Exception as e:
            workflow_logger.error(
                "Questioner invoke failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                exception=e,
            )
            self.error_to_output()
            raise build_error(
                StatusCode.COMPONENT_QUESTIONER_INVOKE_CALL_FAILED,
                error_msg="questioner invoke failed",
                cause=e,
            ) from e

    async def _handle_questioner_direct_reply_safe(
        self, inputs: Input, session: Session, context, current_state: QuestionerState
    ):
        handler = (
            QuestionerDirectReplyHandler()
            .config(self._config)
            .model(self._model)
            .state(current_state)
            .prompt(self._prompt)
            .reflection_prompt(self._reflection_prompt)
            .rails(self._default_rail, self._execute_rail, self._input_rail)
        )
        result = await handler.handle(inputs, session, context)
        result["_state"] = handler.get_state()
        return result

    def _convert_output_field_names(self, invoke_result: dict) -> dict:
        """
        将输出字段名从代码中的小写形式转换为 IR 配置中的形式。

        例如: {"user_response": "张三", "question": "你是谁"}
              -> {"USER_RESPONSE": "张三", "QUESTION": "你是谁"}

        Args:
            invoke_result: 原始输出字典

        Returns:
            转换后的输出字典
        """
        # 硬编码的字段名映射：代码中的小写字段名 -> IR 配置中的大写字段名
        field_mapping = {
            "user_response": "USER_RESPONSE",
            "status": "STATUS",
            "question": "QUESTION",
        }

        converted = {}
        for key, value in invoke_result.items():
            if key in field_mapping:
                converted[field_mapping[key]] = value
            else:
                converted[key] = value
        return converted

    @property
    def node_type(self) -> str:
        return JIUWEN_QUESTIONER_TYPE

    @property
    def config(self) -> QuestionerConfig:
        return self._config


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "Questioner",
    "QuestionerConfig",
    "QuestionerState",
    "QuestionerOutput",
    "FieldInfo",
    "ExecutionStatus",
    "QuestionerEvent",
    "ResponseType",
    "QuestionConstructionMethod",
    "QuestionerUtils",
    "QuestionerInput",
    "OutputCache",
    "QuestionerStartState",
    "QuestionerInteractState",
    "QuestionerEndState",
    "QuestionerDirectReplyHandler",
]
