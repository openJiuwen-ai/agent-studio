# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
Extractor - 信息提取组件

迁移自 jiuwen Extractor，适配 openjiuwen 框架。

功能特性:
- 从对话历史中提取结构化字段信息
- 支持 LLM 调用进行智能提取
- 支持自定义 prompt 模板
- 支持对话历史轮数限制
- 支持字段描述和默认值

设计说明:
- Extractor 继承 WorkflowComponent
- 使用 session.get_global_state() 获取全局配置
- 使用 context.get_messages() 获取对话历史
- 初始化流程：__init__() -> init() -> invoke()
"""

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from jiuwen.extension.workflow_node.utils import get_workflow_param
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.common.security.user_config import UserConfig
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm import (
    BaseMessage,
    UserMessage,
    SystemMessage,
    ModelRequestConfig,
    ModelClientConfig,
    Model,
)
from openjiuwen.core.foundation.prompt import PromptTemplate
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent
from pydantic import BaseModel, ConfigDict, Field

USER_FIELDS = "userFields"
WORKFLOW_CHAT_MANAGER = "workflow_chat_manager"
WORKFLOW_LLM_EXTRA_CONFIGS = "llm_extra_configs"
LLM_INPUTS = "llm_inputs"
LLM_OUTPUTS = "llm_outputs"

DEFAULT_EXAMPLE_CONTENT = """用户输入: 我是小明，性别是男
指定参数：[name:姓名, age:年龄, gender:性别]
提取结果：{"name":"小明","age":null,"gender":"男"}
"""

DEFAULT_ERROR_INFO = {"message": "", "error_code": 0}

DEFAULT_SYSTEM_EXTRA_PROMPT = """
你是一个信息收集助手，你需要根据指定的参数从用户输入中提取信息。
请注意：不要使用任何工具、不用理会问题的具体含义，并保证你的输出仅有 JSON 格式的结果数据。
请严格遵循如下规则：
  1. 让我们一步一步思考。
  2. 用户输入中没有提及的参数提取为 null。
  3. 通过用户提供的对话历史以及当前输入中提取 {{required_name}}，不要追问任何其他信息。
  4. 参数收集完成后，将收集到的信息通过 JSON 的方式展示给用户。

## 指定参数
{{required_params_list}}

## 约束
{{extra_info}}

## 示例
{{example}}
"""
DEFAULT_USER_EXTRA_PROMPT = """
对话历史
{{dig_history}}

请充分考虑以上对话历史及用户输入，正确提取最符合约束要求的 JSON 格式参数。
"""


class ExtractorKeyword:
    """Keyword of Extractor"""

    DEFAULT_SHOT = DEFAULT_EXAMPLE_CONTENT
    MODEL_MAP = "model_map"
    MODEL = "model"
    HYPER_PARAMETERS = "hyper_parameters"
    HYPER_PARAMETERS_CANAL = "hyperParameters"
    MODEL_NAME = "model_name"
    MODEL_TYPE = "model_type"
    NAME = "name"
    DESCRIPTION = "description"
    DESC = "desc"
    ROLE = "role"
    CONTENT = "content"
    TOP_P_KEYWORD = "top_p"
    USER_RESPONSE = "USER_RESPONSE"
    QUESTION = "question"
    CN_FIELDS_NAME = "cn_fields_name"
    CN_FIELD_NAME = "cn_field_name"
    KEY_FIELDS = "key_fields"
    FIELD_NAME = "field_name"
    CHAT_HISTORY_MAX_ROUNDS = "chat_history_max_rounds"


class ConfigPrevious(Enum):
    """Previous config keys (for compatibility)"""

    TEMPLATE_CONTENT = "templateContent"
    TEMPERATURE = "temperature"
    QUESTION = "question"
    EXTRACONFIG = "extraConfig"
    LLM_MODEL = "llm_model"
    MODEL = "model"
    MODEL_NAME = "model_name"


class ConfigCurrent(Enum):
    """Current config keys"""

    EXTRA_PROMPT_FOR_FIELDS_EXTRACTION = "extra_prompt_for_fields_extraction"
    TEMPERATURE = "temperature"
    QUESTION_CONTENT = "question_content"
    FIELD_NAMES = "field_names"
    WITH_CHAT_HISTORY = "with_chat_history"
    CHAT_HISTORY_MAX_ROUNDS = "chat_history_max_rounds"
    PROMPT_TEMPLATE = "prompt_template"
    EXAMPLE_CONTENT = "example_content"
    MODEL = "model"
    MODEL_NAME = "modelName"
    MODEL_TYPE = "modelType"
    HYPER_PARAMETERS = "hyper_parameters"
    TOP_P = "top_p"


class ExtractorStatusCode(Enum):
    """Extractor 组件专用错误码"""

    WORKFLOW_INITIAL_CONFIG_ERROR = (
        101814,
        "extractor config error, reason: {error_msg}",
    )
    PROMPT_ASSEMBLER_TEMPLATE_FORMAT_ERROR = (
        101815,
        "extractor prompt template format error",
    )
    INVOKE_LLM_FAILED = (
        101816,
        "extractor invoke llm failed",
    )


@dataclass
class ExtractorField:
    """Extractor 组件内部状态"""

    extracted_key_fields: dict = field(default_factory=dict)
    user_response: str = ""
    inputs: dict = field(default_factory=dict)


@dataclass
class ExtractorConfig:
    """Extractor 组件配置"""

    model_name: str = ""
    model_type: str = ""
    with_chat_history: bool = False
    chat_history_max_rounds: int = 0
    extra_prompt_for_fields_extraction: str = None
    question_content: str = None
    cn_fields_name: dict = field(default_factory=dict)
    option_content: list = field(default_factory=list)
    key_fields: list = field(default_factory=list)
    hyper_parameters: dict = None
    extension: dict = None
    prompt_template: list = None
    example_content: str = ExtractorKeyword.DEFAULT_SHOT


class ExtractorOutput(BaseModel):
    """Extractor 组件输出"""

    model_config = ConfigDict(extra="allow")

    user_response: Optional[str] = Field(default=None)
    question: Optional[str] = Field(default=None)
    key_fields: Dict[str, Any] = Field(default_factory=dict)

    def __getattr__(self, item: str) -> Any:
        if item in self.__dict__:
            return self.__dict__[item]
        return self.key_fields.get(item)

    def update_key_field(self, new_key_fields: Optional[Dict[str, Any]]) -> None:
        if new_key_fields:
            self.key_fields.update(new_key_fields)

    def as_dict(self) -> Dict[str, Any]:
        result = {}
        if self.user_response:
            result[ExtractorKeyword.USER_RESPONSE] = self.user_response
        if self.question:
            result[ExtractorKeyword.QUESTION] = self.question
        result.update(self.key_fields)
        return result


def format_extractor_configs(configs: dict) -> dict:
    """
    Preprocessing compatibility configuration information
    """
    formatted_extractor_configs = {}

    if isinstance(configs.get(ConfigCurrent.MODEL.value), dict) and configs.get(
        ConfigCurrent.MODEL.value, {}
    ).get(ConfigCurrent.MODEL_NAME.value, ""):
        formatted_extractor_configs[ExtractorKeyword.MODEL_NAME] = configs.get(
            ConfigCurrent.MODEL.value, {}
        ).get(ConfigCurrent.MODEL_NAME.value, "")
    else:
        formatted_extractor_configs[ExtractorKeyword.MODEL_NAME] = configs.get(
            ConfigPrevious.MODEL.value
        )
    if isinstance(configs.get(ConfigCurrent.MODEL.value), dict) and configs.get(
        ConfigCurrent.MODEL.value, {}
    ).get(ConfigCurrent.MODEL_TYPE.value, ""):
        formatted_extractor_configs[ExtractorKeyword.MODEL_TYPE] = configs.get(
            ConfigCurrent.MODEL.value, {}
        ).get(ConfigCurrent.MODEL_TYPE.value, "")
    formatted_extractor_configs[ExtractorKeyword.HYPER_PARAMETERS] = configs.get(
        ExtractorKeyword.MODEL, {}
    ).get(ExtractorKeyword.HYPER_PARAMETERS_CANAL, {})
    top_p = (
        configs.get(ExtractorKeyword.MODEL, {})
        .get(ExtractorKeyword.HYPER_PARAMETERS_CANAL, {})
        .get(ConfigCurrent.TOP_P.value, 0.15)
    )
    temperature = (
        configs.get(ExtractorKeyword.MODEL, {})
        .get(ExtractorKeyword.HYPER_PARAMETERS_CANAL, {})
        .get(ConfigCurrent.TEMPERATURE.value, 0.1)
    )
    formatted_extractor_configs[ExtractorKeyword.HYPER_PARAMETERS][
        ExtractorKeyword.TOP_P_KEYWORD
    ] = top_p
    formatted_extractor_configs[ExtractorKeyword.HYPER_PARAMETERS][
        ConfigCurrent.TEMPERATURE.value
    ] = temperature
    formatted_extractor_configs["extension"] = configs.get(
        ExtractorKeyword.MODEL, {}
    ).get("extension", {})

    formatted_extractor_configs[ConfigCurrent.QUESTION_CONTENT.value] = configs.get(
        ConfigCurrent.QUESTION_CONTENT.value, configs.get(ConfigPrevious.QUESTION.value)
    )
    if ConfigCurrent.EXTRA_PROMPT_FOR_FIELDS_EXTRACTION.value in configs:
        formatted_extractor_configs[
            ConfigCurrent.EXTRA_PROMPT_FOR_FIELDS_EXTRACTION.value
        ] = configs.get(ConfigCurrent.EXTRA_PROMPT_FOR_FIELDS_EXTRACTION.value)

    if configs.get(ConfigCurrent.FIELD_NAMES.value):
        formatted_extractor_configs[ExtractorKeyword.CN_FIELDS_NAME] = {
            item.get(ExtractorKeyword.FIELD_NAME): item.get(
                ExtractorKeyword.CN_FIELD_NAME
            )
            for item in configs.get(ConfigCurrent.FIELD_NAMES.value)
        }
        formatted_extractor_configs[ExtractorKeyword.KEY_FIELDS] = [
            {
                ExtractorKeyword.NAME: item.get(ExtractorKeyword.FIELD_NAME, ""),
                ExtractorKeyword.DESC: item.get(ExtractorKeyword.DESCRIPTION, ""),
                "default_value": item.get("default_value"),
            }
            for item in configs.get(ConfigCurrent.FIELD_NAMES.value)
        ]
    elif configs.get(ConfigPrevious.EXTRACONFIG.value):
        formatted_extractor_configs[ExtractorKeyword.CN_FIELDS_NAME] = {
            item.get(ExtractorKeyword.NAME): item.get("questionKeyWord")
            for item in configs.get(ConfigPrevious.EXTRACONFIG.value)
        }
        formatted_extractor_configs[ExtractorKeyword.KEY_FIELDS] = [
            {
                ExtractorKeyword.NAME: item.get(ExtractorKeyword.NAME, ""),
                ExtractorKeyword.DESC: item.get(ExtractorKeyword.DESCRIPTION, ""),
            }
            for item in configs.get(ConfigPrevious.EXTRACONFIG.value)
        ]

    if ConfigCurrent.WITH_CHAT_HISTORY.value in configs:
        formatted_extractor_configs[ConfigCurrent.WITH_CHAT_HISTORY.value] = (
            configs.get(ConfigCurrent.WITH_CHAT_HISTORY.value)
        )
    if formatted_extractor_configs.get(ConfigCurrent.WITH_CHAT_HISTORY.value):
        formatted_extractor_configs[ExtractorKeyword.CHAT_HISTORY_MAX_ROUNDS] = (
            configs.get(ConfigCurrent.CHAT_HISTORY_MAX_ROUNDS.value)
        )

    if ConfigCurrent.PROMPT_TEMPLATE.value in configs:
        formatted_extractor_configs[ConfigCurrent.PROMPT_TEMPLATE.value] = configs.get(
            ConfigCurrent.PROMPT_TEMPLATE.value
        )

    if configs.get(ConfigCurrent.EXAMPLE_CONTENT.value):
        formatted_extractor_configs[ConfigCurrent.EXAMPLE_CONTENT.value] = configs.get(
            ConfigCurrent.EXAMPLE_CONTENT.value
        )

    return formatted_extractor_configs


def _filter_enable_history(messages: List[BaseMessage]) -> List[BaseMessage]:
    """过滤 enable_history=False 的消息"""
    filtered = []
    for msg in messages:
        enable_history = getattr(msg, "enable_history", True)
        if enable_history:
            filtered.append(msg)
    return filtered


def _clean_json_response(content: str) -> str:
    """清理 JSON 响应中的 markdown 代码块"""
    content = content.strip()
    content = re.sub(r"^\s*```json\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*```\s*$", "", content)
    content = re.sub(r"^\s*'''json\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*'''\s*$", "", content)
    return content.strip()


def build_extractor_error(
    status: ExtractorStatusCode,
    error_msg: str = "",
    cause: Optional[Exception] = None,
):
    from jiuwen.extension.workflow_node.utils import (
        JiuWenBaseException,
    )

    return JiuWenBaseException(
        error_code=status.value[0],
        message=status.value[1].format(error_msg=error_msg),
    )


class Extractor(WorkflowComponent):
    """
    Extractor is a sub class of WorkflowComponent, as a type of node in workflow.

    初始化流程:
    1. __init__() - 空初始化
    2. init(conf, session, context) - 配置初始化
    3. invoke(inputs, session, context) - 执行
    """

    def __init__(self):
        """
        Initialization of Extractor - 空初始化，只设置默认值
        """
        super().__init__()
        self.component_config = None
        self._workflow_llm_extra_configs = {}
        self.model_map = {}
        self.inputs = dict()
        self.user_response = ""
        self.extractor_config = ExtractorConfig()
        self.chat_manager = None
        self.llm = None
        self.prompt: Optional[PromptTemplate] = None
        self.node_field = ExtractorField()
        self.error_message = DEFAULT_ERROR_INFO

    @staticmethod
    def camel_to_snake(text: str) -> str:
        """
        convert camel format configuration value into snake format
        """
        result = [text[0].lower()]
        for char in text[1:]:
            if char.isupper():
                result.extend(["_", char.lower()])
            else:
                result.append(char)
        return "".join(result)

    @staticmethod
    def get_latest_k_rounds_chat(chat_history: list, k: int) -> list:
        """
        get the chat history of the last k rounds.
        chat_history: [... prev_question, prev_query] + [cur_question, cur_query ...]
        """
        if k is None:
            return chat_history
        return chat_history[-k * 2 - 1 :]

    @staticmethod
    def prompt_template_check(conf: dict):
        """
        check if prompt template is legal
        """
        if conf.get("prompt_template"):
            if not isinstance(conf.get("prompt_template"), list):
                return (
                    True,
                    "Prompt Template should be a list in extractor configuration.",
                )
            for unit in conf["prompt_template"]:
                prompt_template_match = (
                    not isinstance(unit, dict)
                    or not isinstance(unit.get("role"), str)
                    or not isinstance(unit.get("content"), str)
                )
                if prompt_template_match:
                    return (
                        True,
                        "Prompt Template should be with role and content in extractor configuration.",
                    )
        return False, ""

    def init(self, conf: dict, session: Session, context: ModelContext):
        """
        Initialization of Extractor - 真正的初始化方法

        Args:
            conf: 组件配置字典
            session: 工作流会话
            context: 模型上下文
        """
        self.node_field = ExtractorField()
        self.component_config = deepcopy(conf)
        conf = self.dict_keys_camel_to_snake(conf)
        self.check_config(conf)

        self._workflow_llm_extra_configs = (
            get_workflow_param(session, WORKFLOW_LLM_EXTRA_CONFIGS) or {}
        )
        self.model_map = self._workflow_llm_extra_configs.get("model_map", {})

        self.inputs = dict()
        self.user_response = ""

        self.extractor_config = ExtractorConfig(**format_extractor_configs(conf))

        self.chat_manager = session.get_global_state(WORKFLOW_CHAT_MANAGER)

        self.llm = self._create_llm_instance()

        self.node_field = ExtractorField()

        self.initial_prompt()

    def check_config(self, conf: dict):
        """
        check if the conf is legal
        """
        match_result, error_msg = self.match_error_config(conf)
        if match_result:
            raise build_extractor_error(
                ExtractorStatusCode.WORKFLOW_INITIAL_CONFIG_ERROR, error_msg=error_msg
            )

    def match_error_config(self, conf: dict):
        """
        check if the conf is illegal
        """
        if not isinstance(
            conf.get("model", {}).get("modelName"), str
        ) or not isinstance(conf.get("model", {}).get("modelType"), str):
            return True, "Model name or model type is not in extractor configuration."
        temperature = (
            conf.get("model", {}).get("hyperParameters", {}).get("temperature", 0)
        )
        match_temperature = not isinstance(temperature, (int, float))
        if match_temperature:
            return True, "Temperature is illegal in extractor configuration."

        prompt_template_match, prompt_template_str = self.prompt_template_check(conf)
        if prompt_template_match:
            return prompt_template_match, prompt_template_str

        extra_prompt_match = conf.get(
            "extra_prompt_for_fields_extraction"
        ) is not None and (
            not isinstance(conf.get("extra_prompt_for_fields_extraction"), str)
        )
        if extra_prompt_match:
            return True, "Extra prompt is illegal in extractor configuration."

        question_content_match = conf.get("question_content") is not None and (
            not isinstance(conf.get("question_content"), str)
        )
        if question_content_match:
            return True, "Question content is illegal in extractor configuration."

        valid_types = (bool, type(None))
        for key in [
            "input_complement",
            "with_chat_history",
            "extract_fields_from_response",
        ]:
            if not isinstance(conf.get(key), valid_types):
                return True, f"{key} is illegal in extractor configuration."

        if not isinstance(conf.get("field_names"), (list, type(None))):
            return True, "field_names should be a list in extractor configuration."
        for unit in conf.get("field_names", []):
            if not all(
                key in unit for key in ["field_name", "description", "cn_field_name"]
            ):
                return (
                    True,
                    "field_name, description and cn_field_name should be in field_names "
                    "in extractor configuration.",
                )

        return False, ""

    def dict_keys_camel_to_snake(self, input_dict: dict) -> dict:
        """
        convert camel format configuration dictionary into snake format
        """
        output_dict = {}
        for key, value in input_dict.items():
            snake_key = self.camel_to_snake(key)
            output_dict[snake_key] = value
        return output_dict

    def initial_prompt(self):
        """
        initial prompt using PromptTemplate
        """
        if self.extractor_config.prompt_template:
            messages = []
            for p in self.extractor_config.prompt_template:
                role = p.get(ExtractorKeyword.ROLE, "")
                content = p.get(ExtractorKeyword.CONTENT, "")
                if role == "system":
                    messages.append(SystemMessage(content=content))
                elif role == "user":
                    messages.append(UserMessage(content=content))
            self.prompt = PromptTemplate(name="extractor_custom", content=messages)
        else:
            self.prompt = self._get_default_prompt_template()

    def _get_default_prompt_template(self) -> PromptTemplate:
        """获取默认 prompt 模板"""
        return PromptTemplate(
            name="extractor_default",
            content=[
                SystemMessage(content=DEFAULT_SYSTEM_EXTRA_PROMPT),
                UserMessage(content=DEFAULT_USER_EXTRA_PROMPT),
            ],
        )

    def _create_llm_instance(self) -> Model:
        """创建 LLM 实例"""
        model_name = self.extractor_config.model_name
        model_type = self.extractor_config.model_type

        if not model_name or not model_type:
            raise build_extractor_error(
                ExtractorStatusCode.WORKFLOW_INITIAL_CONFIG_ERROR,
                error_msg="model_name and model_type are required",
            )

        hyper_parameters = self.extractor_config.hyper_parameters or {}
        extension = self.extractor_config.extension or {}

        model_config = ModelRequestConfig(
            model=model_name,
            temperature=hyper_parameters.get("temperature", 0.1),
            top_p=hyper_parameters.get("top_p", 0.15),
        )

        api_key = extension.get("api_key")
        api_base = extension.get("api_base")
        verify_ssl = extension.get("verify_ssl", True)

        if api_key and api_base:
            client_config = ModelClientConfig(
                client_provider=model_type,
                api_key=api_key,
                api_base=api_base,
                verify_ssl=verify_ssl,
            )
        elif self.model_map:
            model_config_dict = self.model_map.get(model_name, {})
            if model_config_dict:
                client_config = ModelClientConfig(**model_config_dict)
            else:
                raise build_extractor_error(
                    ExtractorStatusCode.WORKFLOW_INITIAL_CONFIG_ERROR,
                    error_msg=f"model_name '{model_name}' not found in model_map and no extension config provided",
                )
        else:
            raise build_extractor_error(
                ExtractorStatusCode.WORKFLOW_INITIAL_CONFIG_ERROR,
                error_msg="Either extension config (api_key, api_base) or model_map is required",
            )

        return Model(client_config, model_config)

    async def create_prompt_template_input(self, chat_history: list) -> dict:
        """
        create input for prompt template
        """
        required_params = []
        for i, param in enumerate(self.extractor_config.key_fields):
            number = i + 1
            required_params.append(
                f"变量{number}名称：{param.get(ExtractorKeyword.NAME, '')}，变量{number}的描述：{param.get('desc', '')} "
            )

        required_name = []
        for _, item in self.extractor_config.cn_fields_name.items():
            required_name.append(item)
        required_name = (
            "、".join(required_name)
            + f"{len(self.extractor_config.cn_fields_name.items())}个必要信息"
        )

        if self.user_response:
            user_response = self.user_response
        elif chat_history:
            user_response = chat_history[-1].get(ExtractorKeyword.CONTENT)
        else:
            user_response = ""

        required_params_list = []
        for _, param in enumerate(self.extractor_config.key_fields):
            required_params_list.append(
                f"{param.get(ExtractorKeyword.NAME, '')}:{param.get('desc', '')} "
            )
        required_params_list = "\n".join(required_params_list)

        chat_history = _filter_enable_history(chat_history)
        dig_history = "\n".join(
            [
                f"{unit.get(ExtractorKeyword.ROLE)}：{unit.get(ExtractorKeyword.CONTENT)}"
                for unit in chat_history[:-1]
                + [{"role": "user", "content": user_response}]
            ]
        )

        extra_info = (
            self.extractor_config.extra_prompt_for_fields_extraction
            if self.extractor_config.extra_prompt_for_fields_extraction
            else ""
        )

        required_params = " \n " + " \n ".join(required_params)

        return {
            "required_params": required_params,
            "example": self.extractor_config.example_content,
            "dig_history": dig_history,
            "required_name": required_name,
            "extra_info": extra_info,
            "required_params_list": required_params_list,
        }

    async def extract_key_fields(self, chat_history: list, session: Session) -> dict:
        """
        extract key fields from chat history
        """
        prompt_template_input = await self.create_prompt_template_input(chat_history)

        messages = self._format_prompt(prompt_template_input)

        await session.trace({LLM_INPUTS: [msg.model_dump() for msg in messages]})

        try:
            response = await self._invoke_llm(messages)
        except Exception as e:
            raise build_extractor_error(
                ExtractorStatusCode.INVOKE_LLM_FAILED, cause=e
            ) from e

        await session.trace({LLM_OUTPUTS: response})

        try:
            cleaned = _clean_json_response(response)
            parsed_data = json.loads(cleaned)

            cur_extracted_key_fields = {
                k: v if v is not None and str(v) else "" for k, v in parsed_data.items()
            }

            return cur_extracted_key_fields

        except json.JSONDecodeError:
            workflow_logger.error(
                "Failed to parse LLM response as JSON",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="Extractor",
                metadata={"error": "JSON parse failed"},
            )
            return {}
        except Exception:
            workflow_logger.error(
                "An unknown error occurred during parsing",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_type_str="Extractor",
                metadata={"error": "Unknown parse error"},
            )
            return {}

    def _format_prompt(self, template_input: dict) -> List[BaseMessage]:
        """格式化 prompt using PromptTemplate"""
        filled_template = self.prompt.format(template_input)
        return filled_template.to_messages()

    async def _invoke_llm(self, messages: List[BaseMessage]) -> str:
        """调用 LLM"""
        workflow_logger.info(
            "Extractor LLM invoke started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="Extractor",
            metadata={
                "has_inputs": bool(messages),
                "input_count": len(messages),
                "sensitive_mode": UserConfig.is_sensitive(),
            },
        )

        response = await self.llm.invoke(messages=messages)
        content = response.content

        workflow_logger.info(
            "Extractor LLM invoke completed",
            event_type=LogEventType.WORKFLOW_COMPONENT_END,
            component_type_str="Extractor",
            metadata={
                "has_response": bool(content),
                "response_length": len(content) if content else 0,
                "sensitive_mode": UserConfig.is_sensitive(),
            },
        )

        return content

    def get_latest_chat_history(self, context: ModelContext, k=None) -> list:
        """
        get the latest chat history from context
        """
        if not self.extractor_config.with_chat_history:
            k = 0

        messages = context.get_messages()

        chat_history = []
        for msg in messages:
            chat_history.append(
                {
                    ExtractorKeyword.ROLE: getattr(msg, "role", ""),
                    ExtractorKeyword.CONTENT: getattr(msg, "content", ""),
                    "enable_history": getattr(msg, "enable_history", True),
                }
            )

        chat_history = self.get_latest_k_rounds_chat(chat_history, k)

        for history in chat_history:
            history.update(
                {ExtractorKeyword.CONTENT: history.get(ExtractorKeyword.CONTENT)}
            )

        return chat_history

    async def update_key_fields(self, context: ModelContext, session: Session):
        """
        updating key fields
        """
        chat_history = self.get_latest_chat_history(
            context, k=self.extractor_config.chat_history_max_rounds
        )
        cur_extracted_key_fields = await self.extract_key_fields(chat_history, session)
        cur_extracted_key_fields = {
            k: v
            for k, v in cur_extracted_key_fields.items()
            if k in self.extractor_config.cn_fields_name
        }
        self.node_field.extracted_key_fields.update(cur_extracted_key_fields)

    async def reply_key_fields(
        self, context: ModelContext, session: Session
    ) -> ExtractorOutput:
        """
        Reply key fields output.
        """
        extractor_output = ExtractorOutput(user_response=self.user_response)
        await self.update_key_fields(context, session)
        extractor_output.update_key_field(self.node_field.extracted_key_fields)
        return extractor_output

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """
        Extractor invoke - 执行入口

        Args:
            inputs: 输入数据，格式: {"userFields": {...}}
            session: 工作流会话
            context: 模型上下文

        Returns:
            Output: 输出数据，格式: {"userFields": {"user_response": str, ...}}
        """
        if not self.llm:
            conf = inputs.get("config", {})
            self.init(conf, session, context)

        workflow_logger.info(
            "Extractor start invoke",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="Extractor",
            metadata={
                "session_id": session.get_session_id(),
            },
        )

        inputs_data = inputs.get(USER_FIELDS)

        conv_history = self.get_latest_chat_history(context)

        workflow_logger.info(
            "Extractor invoke with chat history",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_type_str="Extractor",
            metadata={
                "history_count": len(conv_history),
            },
        )

        self.user_response = (
            conv_history[-1].get(ExtractorKeyword.CONTENT) if conv_history else ""
        )

        await session.trace({"user": self.user_response})

        self.inputs = inputs_data or {}

        res = await self.reply_key_fields(context, session)

        return {USER_FIELDS: res.as_dict()}
