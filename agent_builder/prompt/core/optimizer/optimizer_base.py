#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
optimizer base
"""

from abc import abstractmethod
from typing import Union, Any, Dict

from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.core.modifier.modifier import Modifier


class BaseOptimizer:
    def __init__(
        self,
        input_prompt_list: Union[str, Dict[str, Any]],
        model_info: LLMModelInfo,
        modifier: Modifier,
        meta_prompt_name: str = None,
    ):
        self.input_prompt_list = input_prompt_list
        self.model_info = model_info
        self.modifier = modifier
        self.meta_prompt_name = meta_prompt_name

    @abstractmethod
    def run(self) -> Union[str, Dict[str, Any]]:
        pass
