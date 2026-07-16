#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
optimizer base
"""

import json
import re
from typing import Tuple, Optional, Dict, Any, Union

from agent_builder.common.logging.base import logger
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.core.modifier.modifier import Modifier
from agent_builder.prompt.core.optimizer.optimizer_base import BaseOptimizer

ORIGIN_PROMPT = "original_prompt"
FEEDBACKS = "feedbacks"


class OptimizeWithFeedBack(BaseOptimizer):
    """
    An optimizer that enhances prompt quality through user feedback.

    This class extends the base optimizer with support for feedback-driven refinement, enabling:
    - Iterative improvement of prompts based on explicit user feedback.
    - Precise identification of content to be modified via `selected_content_index`.
    - Controlled insertion of new content at a specified position via `insert_pos_index`.

    Ideal for human-in-the-loop prompt engineering workflows where feedback directly guides optimization.

    Attributes:
        feedback (str): The user-provided feedback used to guide prompt refinement.
                        The description must be highly detailed and nuanced, enabling accurate intent recognition.
        selected_content_index (Optional[Tuple[int, int]]):
            The start and end indices (inclusive) of the content to be modified in the prompt list.
        insert_pos_index (Optional[int]): The index in the prompt list where new content should be inserted.
    """

    def __init__(
        self,
        input_prompt_list: Union[str, Dict[str, Any]],
        model_info: LLMModelInfo,
        modifier: Modifier = None,
        feedback: str = None,
        meta_prompt_name: str = None,
        selected_content_index: Optional[Tuple[int, int]] = None,
        insert_pos_index: Optional[int] = None,
    ):
        super().__init__(input_prompt_list, model_info, modifier, meta_prompt_name)
        self.feedback = feedback
        self.selected_content_index = selected_content_index
        self.insert_pos_index = insert_pos_index

    @staticmethod
    def parse_json(input_string, max_length=10000):
        """parse json"""
        pattern = rf"```json(.{{1,{max_length}}}?)```"
        try:
            match = re.search(pattern, input_string, re.DOTALL)
            if match:
                json_string = match.group(1).strip()
                parsed_data = json.loads(json_string)
                return parsed_data
            logger.info("No valid JSON string found")
            return None

        except json.JSONDecodeError:
            logger.info("An error occurred when JSON parsing")
            return None
        except Exception:
            logger.info("An error occurred when parse intent JSON from message")
            return None

    @staticmethod
    def insert_string(original_str, insert_str, position):
        """insert string"""
        if position < 0 or position > len(original_str):
            raise ValueError(
                "The insertion position is out of the range of the original string."
            )

        result_str = original_str[:position] + insert_str + original_str[position:]
        return result_str

    def run(self):
        """run"""
        pass

    def is_feedback_valid(self):
        """feedback_is_valid"""
        modifier = Modifier(
            model_info=self.model_info, meta_prompt_name=self.meta_prompt_name
        )
        placeholders = {ORIGIN_PROMPT: self.input_prompt_list, FEEDBACKS: self.feedback}
        intent_message = modifier.run(placeholders)
        intent_json = self.parse_json(intent_message.get("data"))
        if not intent_json:
            return False, self.feedback
        intent = intent_json.get("intent", False) in ("true", True, "True")
        optimized_feedback = intent_json.get("optimized_feedback", "")
        return intent, optimized_feedback

    def optimize_with_dialog(self, opt_prompt_name):
        """optimize_with_dialog"""
        modifier = Modifier(
            meta_prompt_name=opt_prompt_name, model_info=self.model_info
        )
        placeholders = {"prompt": self.input_prompt_list, "suggestion": self.feedback}
        modified_prompt = modifier.run(placeholders=placeholders, stream=True)
        return modified_prompt

    def optimize_with_insert(self, opt_prompt_name):
        """optimize_with_insert"""
        intent, optimized_feedback = self.is_feedback_valid()
        if not intent:
            logger.warning(
                "Feedback intent recognition failed, will directly using feedback content for reply"
            )

        modifier = Modifier(
            model_info=self.model_info, meta_prompt_name=opt_prompt_name
        )
        original_prompt = self.input_prompt_list
        original_prompt_tag = self.insert_string(
            original_prompt, "[用户要插入的位置]", self.insert_pos_index
        )
        placeholders = {
            ORIGIN_PROMPT: original_prompt_tag,
            FEEDBACKS: optimized_feedback,
        }
        message = modifier.run(placeholders, stream=True)
        return message

    def optimize_with_part(self, opt_prompt_name):
        """optimize_with_part"""
        intent, optimized_feedback = self.is_feedback_valid()
        if not intent:
            logger.warning(
                "Feedback intent recognition failed, will directly using feedback content for reply"
            )

        modifier = Modifier(
            model_info=self.model_info, meta_prompt_name=opt_prompt_name
        )
        original_prompt = self.input_prompt_list
        start, end = self.selected_content_index
        pending_optimized_prompt = original_prompt[start:end]
        placeholders = {
            ORIGIN_PROMPT: original_prompt,
            "pending_optimized_prompt": pending_optimized_prompt,
            FEEDBACKS: optimized_feedback,
        }
        message = modifier.run(placeholders, stream=True)
        return message
