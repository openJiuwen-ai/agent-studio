#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
prompt builder interface
"""

import traceback
from typing import Union, List

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.common.utils.utils import sanitize_input
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.template.base import MetaTemplate
from agent_builder.adapter.placeholder_editor import TemplateEditor
from pydantic import BaseModel, Field


class PromptBuilder(BaseModel):
    """
    A class for building prompts based on a meta template.
    Mainly used to supplement prompt content, add scenarios, and construct complete prompts for LLM input.
    """

    editor: Union[TemplateEditor, None] = Field(default=None)
    model_info: Union[LLMModelInfo, None] = Field(default=None)

    @staticmethod
    def _result_generator(result):
        """result generator handler"""
        for element in result:
            yield element

    @classmethod
    def initialize(
        cls, model_info: LLMModelInfo = LLMModelInfo(), editor: TemplateEditor = None
    ):
        """initialize for prompt builder"""
        return cls(editor=editor, model_info=model_info)

    def hmi_streaming_build(
        self, meta_template: str, instruction: str, tools: List[dict] = None, **kwargs
    ):
        """hmi_streaming_build"""
        stream_char = MetaTemplate.create(
            name=meta_template, stream=True, model_info=self.model_info
        ).build_prompt(instruction=instruction, tools=tools, **kwargs)
        try:
            if self.editor:
                result = self.editor.stream_run(concrete_template=stream_char)
                return self._result_generator(result=result)
            return self._result_generator(result=stream_char)
        except Exception as _:
            traceback_error_msg = traceback.format_exc()
            code = StatusCode.PROMPT_TEMPLATE_EDITOR_ERROR.code
            msg = StatusCode.PROMPT_TEMPLATE_EDITOR_ERROR.errmsg
            logger.error(
                f"Hmi streaming build failed! code: {code}, detail: {msg},"
                f"traceback: {sanitize_input(traceback_error_msg)}"
            )
            return dict(code=code, message=msg, data="")
