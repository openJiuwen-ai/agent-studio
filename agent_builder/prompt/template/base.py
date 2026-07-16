#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
meta template base

Local implementation using adapter's template_adapter instead of jiuwen.
"""

from abc import abstractmethod
from typing import List, Union

from agent_builder.adapter.template_adapter import (
    MetaTemplate as AdapterMetaTemplate,
    StandardMeta as AdapterStandardMeta,
    Template,
)
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.template.llm_service import LLMServiceManager
from pydantic import Field


class MetaTemplate(AdapterMetaTemplate):
    """
    meta template base

    Extends the adapter's MetaTemplate with agent_builder-specific model_info.
    """

    model_info: Union[LLMModelInfo, None] = Field(default=None)

    @classmethod
    def create(cls, name: str, stream: bool = False, model_info: LLMModelInfo = None):
        """create meta template"""
        return StandardMeta(name=name, stream=stream, model_info=model_info)

    @abstractmethod
    def _assemble_input_value(
        self,
        template: Template,
        instruction: str = "",
        tools: List[dict] = None,
        **kwargs,
    ):
        raise NotImplementedError("Not Implemented")

    @abstractmethod
    def _streaming_build(self, content: str) -> str:
        raise NotImplementedError("Not Implemented")

    @abstractmethod
    def _full_build(self, content: str) -> str:
        raise NotImplementedError("Not Implemented")


class StandardMeta(AdapterStandardMeta):
    """standard meta implement"""

    def _streaming_build(self, content: str) -> str:
        messages = [{"role": "user", "content": content}]
        return LLMServiceManager.get_llm_backend().chat(
            messages, method="stream", model_info=self.model_info
        )

    def _full_build(self, content: str) -> str:
        messages = [{"role": "user", "content": content}]
        result = LLMServiceManager.get_llm_backend().chat(
            messages, model_info=self.model_info
        )
        if isinstance(result, dict):
            if "latency" in result:
                result.pop("latency")
            return result.get("data", result.get("content", "content not exit"))
        return str(result)
