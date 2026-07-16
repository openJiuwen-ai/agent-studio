#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
analyzer
"""

import re
from typing import List

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.core.modifier.modifier import Modifier
from agent_builder.prompt.core.optimizer.dataset import BaseCaseData
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class BaseAnalyzer(Modifier):
    def __init__(
        self,
        input_prompt: str,
        bad_case_list: List[BaseCaseData],
        model_info: LLMModelInfo,
        meta_prompt_name: str,
    ):
        super().__init__(model_info=model_info, meta_prompt_name=meta_prompt_name)
        self.input_prompt = input_prompt
        self.bad_case_list = bad_case_list

    def create_placeholders(self):
        """assemble prompt"""
        bad_cases = "\n\n".join(
            f"<bad_case>\n{case}\n</bad_case>" for case in self.bad_case_list
        )
        placeholders = {"original_prompt": self.input_prompt, "bad_cases": bad_cases}
        return placeholders

    def run_analyze(
        self,
    ):
        """Run analysis by LLM. Extract `summary` text as feedback message."""
        placeholders = self.create_placeholders()
        llm_response = self.run(placeholders)
        intent = re.findall(
            r"<intent>((?:(?!<intent>).)*?)</intent>",
            llm_response.get("data", ""),
            re.DOTALL,
        )
        intent = [intent_text.strip() for intent_text in intent]
        if "false" in intent:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_BAD_CASE_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_BAD_CASE_ERROR.errmsg.format(
                    error_msg="Optimize bad case is unuseful"
                ),
            )
        text_match = re.findall(
            r"<summary>((?:(?!<summary>).)*?)</summary>",
            llm_response.get("data", ""),
            re.DOTALL,
        )
        feedback_summary = (
            text_match[-1].strip()
            if len(text_match) >= 1
            else llm_response.get("content", "")
        )
        return feedback_summary.replace(" ", "")
