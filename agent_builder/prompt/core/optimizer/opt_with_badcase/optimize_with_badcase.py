#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
optimizer base
"""

from typing import List, Union, Any, Dict

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.core.modifier.modifier import Modifier
from agent_builder.prompt.core.optimizer.analyzer import BaseAnalyzer
from agent_builder.prompt.core.optimizer.dataset import BaseCaseData
from agent_builder.prompt.core.optimizer.optimizer_base import BaseOptimizer
from agent_builder.adapter.exception_bridge import JiuWenBaseException


class OptimizeWithBadcase(BaseOptimizer):
    """
    A class for optimizing prompts based on bad case analysis.
    """

    def __init__(
        self,
        input_prompt_list: Union[str, Dict[str, Any]],
        bad_case_list: List[BaseCaseData],
        model_info: LLMModelInfo,
        meta_prompt_name: List[str],
    ):
        """
        Args
            input_prompt_list: currently only support a single prompt
            bad_case_list: list of bad cases, formatted with `BaseCaseData`
            model_info: model info for analyzer and modifier, respectively
            meta_prompt_name: meta prompt for analyzer and modifier, respectively
        """
        if len(meta_prompt_name) != 2:
            raise JiuWenBaseException(
                StatusCode.PROMPT_TEMPLATE_NOT_FOUND_ERROR.code,
                StatusCode.PROMPT_TEMPLATE_NOT_FOUND_ERROR.errmsg.format(
                    error_msg="please check meta prompt size equal tow piece"
                ),
            )
        modifier = Modifier(model_info=model_info, meta_prompt_name=meta_prompt_name[1])
        super().__init__(input_prompt_list, model_info, modifier)
        self.bad_case_list = bad_case_list
        self.analyzer = BaseAnalyzer(
            input_prompt=input_prompt_list,
            bad_case_list=bad_case_list,
            model_info=model_info,
            meta_prompt_name=meta_prompt_name[0],
        )

    def run(self):
        feedback_from_case = self.analyzer.run_analyze()
        placeholders = {
            "original_prompt": self.input_prompt_list,
            "feedbacks": feedback_from_case,
        }
        llm_response = self.modifier.run(placeholders, stream=True)
        return llm_response
