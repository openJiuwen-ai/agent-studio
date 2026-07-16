#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
modifier
"""

from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.template.base import MetaTemplate
from agent_builder.prompt.tune.base.utils import LLMModelProcess


class Modifier:
    def __init__(self, model_info: LLMModelInfo, meta_prompt_name: str):
        self.model_info = model_info
        self.meta_prompt_name = meta_prompt_name

        self.llm = LLMModelProcess(model_info=self.model_info)

    def get_meta_prompt(self, placeholders=None):
        """get_meta_prompt"""
        meta_template = MetaTemplate.create(
            name=self.meta_prompt_name, stream=False, model_info=self.model_info
        )
        messages = meta_template.get_template_content(
            instruction="", tools=None, **placeholders
        )
        return messages

    def run(self, placeholders, tools=None, stream=False):
        """run"""
        messages = self.get_meta_prompt(placeholders=placeholders)
        """get_llm_result"""
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        if stream:
            return self.get_llm_result_stream(messages, tools)
        return self.get_llm_result(messages, tools)

    def get_llm_result(self, messages, tools=None):
        """get_llm_result"""
        try:
            response = self.llm.chat(messages, tools=tools)
            return {"code": 0, "message": "success", "data": response.get("content")}
        except JiuWenBaseException as e:
            return {
                "code": -1,
                "message": "fail",
                "data": f"LLM model chat failed. error code: {e.error_code}",
            }

    def get_llm_result_stream(self, messages, tools=None):
        """get_llm_result"""
        try:
            for response in self.llm.stream_chat(messages, tools=tools):
                yield {"code": 0, "message": "success", "data": response.get("content")}
        except JiuWenBaseException as e:
            yield {"code": -1, "message": "fail", "data": f"{e.message}"}
