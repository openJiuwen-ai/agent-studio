# -*- coding: utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

import ast
import os
import random
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from jiuwen.common.configs.env_constants import MULTI_LAYER_INTENT_DETECTION_PROMPT_KEY
from jiuwen.common.intent_detection.config import LLMMatcherConfig
from jiuwen.common.intent_detection.layers.base import (
    BaseMatcher,
    IntentInput,
    IntentOutput,
)
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.common.store.async_redis import get_async_redis_instance
from jiuwen.common.utils.utils import safe_json_loads
from jiuwen.controller.common.constants import IntentionDetectConstants
from jiuwen.planner.common.stream_post_utils import convert_ai_message_to_llm_output
from jiuwen.prompt import Prompt
from jiuwen.prompt import Template, TemplateManager

DECODE_TYPE = "utf-8"
DEFAULT_CLASS = "分类1"
DEFAULT_TEMPLATE = "multi_layer_intent_detection"
DESCRIPTION_KEY = "intent_description"
EXAMPLE_KEY = "intent_example"
EXAMPLE_PER_INTENT = 3


@dataclass
class LLMRetrivalParams:
    intent_detection_template: Template
    default_class: str = field(default=DEFAULT_CLASS)
    enable_history: bool = True
    enable_input: bool = True
    chat_history_max_turn: int = 10
    example_content: List[str] = field(default_factory=list)
    user_prompt: str = ""

    # redis查询配置项
    description_key: str = field(default=DESCRIPTION_KEY)
    example_key: str = field(default=EXAMPLE_KEY)
    example_per_intent: int = EXAMPLE_PER_INTENT


class LLMMatcher(BaseMatcher):
    """
    LLM Matcher
    """

    name = "llm"
    redis_instance = None

    def __init__(self, config: LLMMatcherConfig):
        """
        初始化llm matcher
        Args:
            config:
            llm:
            template_config:
        """
        self.config = config
        self.llm_config = config.llm_config

        self.llm = self._get_llm_instance()
        # 懒加载 Redis 客户端（只在首次创建 LLMMatcher 时初始化）
        if LLMMatcher.redis_instance is None:
            LLMMatcher.redis_instance = get_async_redis_instance()
        self.redis_client = LLMMatcher.redis_instance
        self.llm_retrival_config = self._get_llm_retrival_config()

        self.category_2_intent_map: Dict[str, str] = {}
        self.intent_2_category_map: Dict[str, str] = {}

    async def invoke(
        self, input_data: IntentInput, top_k: Optional[int] = None, **kwargs
    ) -> IntentOutput:
        """
        异步匹配接口
        """

        try:
            candidates = kwargs.get("candidates", [])  # candidate list

            if not candidates:
                logger.info(
                    "No valid candidate from selected candidate layer, using all valid intents as candidates"
                )
                candidates = list(input_data.valid_intents.keys())

            descriptions = {
                key: input_data.valid_intents[key]
                for key in candidates
                if key in input_data.valid_intents
            }
            examples = await self._get_intent_examples(candidates)

            llm_input = await self._build_llm_input(
                input_data, candidates, descriptions, examples
            )
            logger.info(
                f"succeed to build llm input in llm_matcher:{llm_input}",
                simple_log="succeed to build llm input in llm_matcher",
            )
            llm_response = await self.llm.ainvoke(llm_input)
            logger.info(
                f"succeed to get llm response in llm_matcher:{llm_response}",
                simple_log="succeed to get llm response in llm_matcher",
            )
            llm_output = convert_ai_message_to_llm_output(llm_response)

            intent_class = self._post_process(llm_output.content)
            intent_name = self._get_intent_name(intent_class, candidates)

            if not intent_name:
                logger.info("LLM did not match any valid intent")
                return IntentOutput()
            match = re.search(r"\d+$", intent_class)
            if not match:
                logger.info("in llm_match, wrong, intent_class")
                return IntentOutput()
            return IntentOutput(
                intent_id=match.group(),
                intent_name=intent_name,
                score=1.0,
                is_matched=True,
                matched_layer=self.name,
            )

        except Exception as e:
            logger.error(f"Exception in LLM matcher invoke: {e}")
            raise e

    async def _get_intent_info(self, intent_ids):
        descriptions = await self._get_intent_descriptions(intent_ids)
        examples = await self._get_intent_examples(intent_ids)
        return descriptions, examples

    def _get_intent_name(self, intent_class, intent_ids):
        intent_name = self.category_2_intent_map.get(intent_class)
        if not intent_name and intent_class in intent_ids:
            intent_name = intent_class
        return intent_name

    async def _get_intent_examples(self, intent_ids: List[str]) -> Dict[str, List[str]]:
        """
        获取意图示例

        args:
            intent_ids:意图列表

        return:
            意图及对应的示例
        """
        try:
            redis_client = self.redis_client.get_redis_client()
            raw_examples = await redis_client.hmget(
                self.llm_retrival_config.example_key, *intent_ids
            )
            n_per_intent = self.llm_retrival_config.example_per_intent
            filtered_examples = {}

            for intent_id, raw_val in zip(intent_ids, raw_examples):
                if raw_val:
                    try:
                        data_str = (
                            raw_val.decode(DECODE_TYPE)
                            if isinstance(raw_val, bytes)
                            else str(raw_val)
                        )
                        loaded = safe_json_loads(data_str)

                        if isinstance(loaded, list):
                            filtered_examples[intent_id] = random.sample(
                                [str(ex) for ex in loaded if ex], n_per_intent
                            )
                        else:
                            logger.warning(
                                f"Examples for intent '{intent_id}' is not a list: {type(loaded)}"
                            )
                    except (TypeError, ValueError) as e:
                        logger.warning(
                            f"Failed to parse examples for intent '{intent_id}': {e}"
                        )
                else:
                    filtered_examples[intent_id] = []

            return filtered_examples
        except Exception as e:
            logger.error(f"Failed to get intent examples from Redis: {e}")
            raise e

    async def _get_intent_descriptions(self, intent_ids: List[str]) -> Dict[str, str]:
        """
        获取意图描述

        args:
            intent_ids:意图列表

        return:
            意图及对应的描述
        """
        try:
            redis_client = self.redis_client.get_redis_client()
            raw_descriptions = await redis_client.hmget(
                self.llm_retrival_config.description_key, *intent_ids
            )
            descriptions = {}

            for intent_id, raw_val in zip(intent_ids, raw_descriptions):
                try:
                    if not raw_val:
                        descriptions[intent_id] = ""
                        continue
                    desc = (
                        raw_val.decode(DECODE_TYPE)
                        if isinstance(raw_val, bytes)
                        else raw_val
                    )
                    descriptions[intent_id] = desc
                except Exception as e:
                    logger.error(
                        f"Failed to decode description for intent '{intent_id}': {e}",
                        exc_info=True,
                    )
                    raise

            return descriptions
        except Exception as e:
            logger.error(
                f"Failed to get intent descriptions from Redis: {e}", exc_info=True
            )
            raise e

    def _build_category_info(
        self,
        intent_ids: List[str],
        descriptions: Dict[str, str],
        examples: Dict[str, List[str]],
    ):
        """
        创建分类信息

        args:
            intent_ids:意图列表
            descriptions:意图描述
            examples:意图示例

        return:
            意图分类信息和示例
        """

        self.category_2_intent_map = {}
        self.intent_2_category_map = {}

        category_parts = []
        example_parts = []
        for index, intent_id in enumerate(intent_ids, start=1):
            category_id = f"分类{index}"
            self.category_2_intent_map[category_id] = intent_id
            self.intent_2_category_map[intent_id] = category_id

            desc = descriptions.get(
                intent_id, intent_id
            )  # 如果没有描述就直接用意图名作为意图描述
            part = f"{category_id}: {desc}"
            category_parts.append(part)

            intent_examples = examples.get(intent_id, [])
            if intent_examples:
                examples_text = f"{category_id}:\n" + "\n".join(
                    f"  - {example}" for example in intent_examples
                )
                example_parts.append(examples_text)

        if not example_parts:
            example_parts = ["无示例"]

        return "\n".join(category_parts), "\n".join(example_parts)

    def _format_chat_history(
        self, dialogue_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """

        Args:
            dialogue_history:

        Returns:

        """
        if not dialogue_history:
            return ""

        max_turns = self.config.history_max_turns
        history_sliced = dialogue_history[-max_turns:] if max_turns > 0 else []

        formatted_parts = []
        for entry in history_sliced:
            role = entry.get(IntentionDetectConstants.ROLE, "user")
            content = entry.get(IntentionDetectConstants.CONTENT, "")
            role_display = IntentionDetectConstants.ROLE_MAP.get(role, "用户")
            formatted_parts.append(f"{role_display}：{content}")

        return "\n".join(formatted_parts)

    async def _pre_process(self, inputs: Dict[str, Any]) -> Any:
        """
        创建llm inputs

        Args:
            inputs: 提示词模板填充内容

        Returns:
            llm输入
        """
        final_prompts = []
        try:
            for (
                prompt_message
            ) in self.llm_retrival_config.intent_detection_template.content:
                rendered_content = await Prompt(
                    template=Template(name="template", content=[prompt_message])
                ).ainvoke(inputs)

                final_prompts.append(
                    {
                        IntentionDetectConstants.ROLE: prompt_message.get(
                            IntentionDetectConstants.ROLE, ""
                        ),
                        IntentionDetectConstants.CONTENT: rendered_content,
                    }
                )

            llm_inputs = LanguageModelInput(
                messages=ModelUtil.switch_message(final_prompts), tools=[]
            )
            return llm_inputs

        except Exception as e:
            logger.error(f"Failed to pre-process inputs: {e}", exc_info=True)
            raise e

    async def _build_llm_input(
        self,
        input_data: IntentInput,
        intent_ids: List[str],
        descriptions: Dict[str, str],
        examples: Dict[str, List[str]],
    ) -> Any:
        """
        构建llm输入

        Args:
            input_data:输入
            intent_ids:意图列表
            descriptions:对应的意图描述
            examples:对应的意图示例

        Returns:
            llm输入
        """
        category_content, example_content = self._build_category_info(
            intent_ids, descriptions, examples
        )

        dialogue_history = None
        if input_data.dialogue_history:
            dialogue_history = [
                {
                    IntentionDetectConstants.ROLE: msg.role,
                    IntentionDetectConstants.CONTENT: msg.content,
                }
                for msg in input_data.dialogue_history
            ]
        chat_history = self._format_chat_history(dialogue_history)

        current_inputs = {
            IntentionDetectConstants.CATEGORY_INFO: category_content,
            IntentionDetectConstants.DEFAULT_CLASS: self.llm_retrival_config.default_class,
            IntentionDetectConstants.ENABLE_HISTORY: self.llm_retrival_config.enable_history,
            IntentionDetectConstants.ENABLE_INPUT: self.llm_retrival_config.enable_input,
            IntentionDetectConstants.EXAMPLE_CONTENT: example_content,
            IntentionDetectConstants.CHAT_HISTORY_MAX_TURN: self.llm_retrival_config.chat_history_max_turn,
            IntentionDetectConstants.INPUT: input_data.query,
            IntentionDetectConstants.USER_PROMPT: self.llm_retrival_config.user_prompt,
        }

        if self.llm_retrival_config.enable_history and chat_history:
            current_inputs[IntentionDetectConstants.CHAT_HISTORY] = chat_history

        return self._pre_process(current_inputs)

    def _extract_code_block(self, result: str) -> str:
        """
        提取llm返回json内容
        Args:
            result: llm回复

        Returns:
            提取的json内容
        """
        if "```" not in result:
            return result

        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", result)
        if code_block_match:
            return code_block_match.group(1).strip()

        return result

    def _post_process(self, result: str) -> str:
        """
        后处理LLM返回结果

        args:
            result: llm结果

        return:
            意图分类结果
        """
        logger.info("Parsing llm intent detection result")
        result = self._extract_code_block(result)

        try:
            logger.info(f"Trying to parse result with ast: {result}")
            parsed_dict = ast.literal_eval(result)
            if not isinstance(parsed_dict, dict):
                logger.info(f"Failed to parse result with ast: {result}")
                return self.llm_retrival_config.default_class
        except Exception as e:
            logger.info(
                f"Invalid result format, failed to parse result: {e}", exc_info=True
            )
            return self.llm_retrival_config.default_class

        if parsed_dict is None:
            return self.llm_retrival_config.default_class

        # 解析
        intent_class = self._parse_intent_class(parsed_dict)
        if intent_class:
            logger.info(f"Parsed intent class: {intent_class}")
            return intent_class

        return self.llm_retrival_config.default_class

    def _parse_intent_class(self, parsed_dict: dict) -> str:
        """
        解析分类结果
        """

        result_value = parsed_dict.get(IntentionDetectConstants.RESULT)

        if isinstance(result_value, int):
            return f"分类{result_value}"
        if isinstance(result_value, str):
            intent_class = self._clean_class_string(result_value)
            if "分类" not in intent_class:
                if intent_class.isdigit():
                    intent_class = f"分类{intent_class}"
                else:
                    match = re.search(r"分类(\d+)", intent_class)
                    if match:
                        intent_class = f"分类{match.group(1)}"
                    else:
                        return self.llm_retrival_config.default_class
            return intent_class

        return self.llm_retrival_config.default_class

    def _clean_class_string(self, class_str: str) -> str:
        """
        格式化字符串，清除前后空格等
        """
        return (
            class_str.replace("\n", "")
            .replace(" ", "")
            .replace("'", "")
            .replace('"', "")
        )

    def _get_llm_instance(self):
        """
        获取llm实例
        """
        llm_cfg = self.config.llm_config
        llm = ModelFactory().get_model(
            model_name=llm_cfg.model_name,
            model_type=llm_cfg.model_type,
            **llm_cfg.hyper_parameters,
            **llm_cfg.extension,
        )
        return llm

    def _get_llm_retrival_config(self):
        return LLMRetrivalParams(
            default_class=DEFAULT_CLASS,
            enable_history=self.config.use_history,
            enable_input=False,
            chat_history_max_turn=self.config.history_max_turns,
            user_prompt=self.config.user_prompt,
            intent_detection_template=self._get_prompt_template(),
            description_key=DESCRIPTION_KEY,
            example_key=EXAMPLE_KEY,
            example_per_intent=EXAMPLE_PER_INTENT,
        )

    def _get_prompt_template(self):
        template = os.getenv(MULTI_LAYER_INTENT_DETECTION_PROMPT_KEY, DEFAULT_TEMPLATE)
        return TemplateManager().get(
            name=template, filters={"tag": self.llm_config.model_name}
        )
