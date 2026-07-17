#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
common llm service

使用 model_providers.get_prompt_optimize_model() 获取九问平台 Model 实例，
替代原来通过 OpenAICompatibleService 的调用方式。
"""

import json
import traceback
from abc import abstractmethod
from typing import List, Dict

from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.llm_bridge import _run_async, _collect_async_gen
from agent_builder.adapter.logger_bridge import logger
from agent_builder.common.exception.status_code import StatusCode
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.adapter.model_bridge import get_prompt_optimize_model
from pydantic import BaseModel, Field


class BaseLLMService(BaseModel):
    """base llm service"""

    add_prefix: bool = Field(default=True)
    model_info: LLMModelInfo = Field(default=LLMModelInfo())

    @abstractmethod
    def streaming_chat(self, messages: List[dict], extra_info: Dict = None):
        """streaming chat abstract method"""

    @abstractmethod
    def astreaming_chat(self, messages: List[dict], extra_info: Dict = None):
        """streaming chat abstract method"""


class EiCloudLLMService(BaseLLMService):
    """
    Ei cloud service using agent-core Model via PromptOptimizeModelProvider.

    通过 get_prompt_optimize_model() 获取九问平台的 Model 实例，
    配置逻辑由 PromptOptimizeModelProvider 统一管理（settings.llm + modelInfo + 认证头）。
    """

    system_message: list = Field(default=[])

    def full_chat(
        self, messages: List[dict], extra_info: Dict = None
    ) -> Dict[str, str]:
        """full chat using agent-core Model (sync bridge)"""
        if self.add_prefix:
            messages = self.system_message + messages
        try:
            model = _run_async(get_prompt_optimize_model(self.model_info))
            response = _run_async(model.invoke(messages))
            content = response.content if hasattr(response, "content") else str(response)
            return dict(code=0, message="success", data=content)
        except JiuWenBaseException as error:
            traceback_error_msg = traceback.format_exc()
            code = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.code
            msg = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.errmsg.format(
                error_msg="Inner exception"
            )
            logger.error(
                f"Full request agent builder llm failed! code: {error.error_code}, detail: {error.message}, "
                f"traceback: {traceback_error_msg}"
            )
            raise JiuWenBaseException(error_code=code, message=msg) from error
        except Exception as error:
            traceback_error_msg = traceback.format_exc()
            code = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.code
            msg = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.errmsg.format(
                error_msg="Inner exception"
            )
            logger.error(
                f"Full request agent builder llm failed! Inner code: {code}, detail: {msg}, traceback: {traceback_error_msg}"
            )
            raise JiuWenBaseException(error_code=code, message=msg) from error

    def streaming_chat(
        self, messages: List[dict], extra_info: Dict = None
    ) -> Dict[str, str]:
        """streaming chat using agent-core Model (sync bridge)"""
        if self.add_prefix:
            messages = self.system_message + messages
        try:
            model = _run_async(get_prompt_optimize_model(self.model_info))
            chunks = _collect_async_gen(model.stream(messages))
            for chunk in chunks:
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    yield dict(code=0, message="success", data=content)
        except JiuWenBaseException as error:
            logger.error(
                f"request agent builder llm failed! code: {error.error_code}, detail: {error.message}"
            )
            yield dict(code=error.error_code, message=error.message, data="")
        except Exception as _:
            code = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.code
            msg = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.errmsg.format(
                error_msg="Inner exception"
            )
            logger.error(
                f"request agent builder llm failed! code: {code}, detail: {msg}"
            )
            yield dict(code=code, message=msg, data="")

    async def astreaming_chat(
        self, messages: List[dict], extra_info: Dict = None
    ):
        """async streaming chat using agent-core Model (native async)"""
        if self.add_prefix:
            messages = self.system_message + messages
        try:
            model = await get_prompt_optimize_model(self.model_info)
            async for chunk in model.stream(messages):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    yield dict(code=0, message="success", data=content)
        except JiuWenBaseException as error:
            logger.error(
                f"request agent builder llm failed! code: {error.error_code}, detail: {error.message}"
            )
            yield dict(code=error.error_code, message=error.message, data="")
        except Exception as _:
            code = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.code
            msg = StatusCode.PROMPT_LLM_GENERATION_FAILED_ERROR.errmsg.format(
                error_msg="Inner exception"
            )
            logger.error(
                f"request agent builder llm failed! code: {code}, detail: {msg}"
            )
            yield dict(code=code, message=msg, data="")


class LLMServiceManager(BaseModel):
    """LLMServiceManager"""

    llm_service: BaseLLMService

    @classmethod
    def get_llm_backend(cls):
        """get llm backend interface"""
        return cls(llm_service=EiCloudLLMService())

    def chat(
        self,
        messages: List[dict],
        extra_info: Dict = None,
        model_info: LLMModelInfo = None,
        method: str = "stream",
        add_prefix: bool = True,
    ):
        """llm service manager chat interface"""
        self.llm_service.add_prefix = add_prefix
        if model_info:
            self.llm_service.model_info = model_info
        if method == "stream":
            return self.llm_service.streaming_chat(
                messages=messages, extra_info=extra_info
            )
        if method == "full_chat":
            return self.llm_service.full_chat(messages=messages, extra_info=extra_info)
        raise JiuWenBaseException(
            StatusCode.LLM_FALSE_RESULT_ERROR.code,
            StatusCode.LLM_FALSE_RESULT_ERROR.errmsg.format(
                error_msg="llm service should be stream call"
            ),
        )

    def achat(
        self,
        messages: List[dict],
        extra_info: Dict = None,
        model_info: LLMModelInfo = None,
        method: str = "stream",
        add_prefix: bool = True,
    ):
        """llm service manager chat interface"""
        self.llm_service.add_prefix = add_prefix
        if model_info:
            self.llm_service.model_info = model_info
        if method == "stream":
            return self.llm_service.astreaming_chat(
                messages=messages, extra_info=extra_info
            )
        if method == "full_chat":
            return self.llm_service.full_chat(messages=messages, extra_info=extra_info)
        raise JiuWenBaseException(
            StatusCode.LLM_FALSE_RESULT_ERROR.code,
            StatusCode.LLM_FALSE_RESULT_ERROR.errmsg.format(
                error_msg="llm service should be stream call"
            ),
        )
