# agent_runtime/serve/apis/additional_questions/model_invoker.py
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""追问功能 — LLM 模型调用器。

通过 model_service 包的 StudioModelClient 调用 LLM，
构建薄 ModelClientConfig（client_provider="studio"），
真实连接信息由 resolver 在 invoke 时解析。
"""

import logging

from openjiuwen.core.foundation.llm import (
    Model,
    ModelClientConfig,
    ModelRequestConfig,
    UserMessage,
)

from agent_runtime.common.config import settings
from agent_runtime.schemas.additional_questions import AdditionalQuestionsModelConfig

logger = logging.getLogger(__name__)


class AdditionalQuestionsModelInvoker:
    """调用 LLM 生成追问建议 — 基于 model_service / StudioModelClient。"""

    async def invoke(
        self,
        model_config: AdditionalQuestionsModelConfig,
        query: str,
        headers: dict,
    ) -> str:
        """调用模型并返回原始响应文本。

        Args:
            model_config: 从 IR 中提取的模型配置（model_service_id + auth_id）
            query: 渲染后的完整 prompt
            headers: HTTP 请求头（透传到 model_service 鉴权）

        Returns:
            LLM 返回的原始文本内容

        Raises:
            Exception: 模型调用失败时向上抛出
        """
        base = settings.llm
        client_config = ModelClientConfig(
            client_provider="studio",
            api_key="sk-placeholder",
            api_base="https://studio-placeholder",
            timeout=base.timeout,
            verify_ssl=base.ssl_verify,
            model_service_id=model_config.model_service_id,
            auth_id=model_config.auth_id,
        )
        request_config = ModelRequestConfig(
            model=model_config.model_service_id,
            temperature=0.3,
            top_p=0.9,
            frequency_penalty=0.1,
        )
        model = Model(
            model_client_config=client_config,
            model_config=request_config,
        )
        logger.info(
            "Invoking model for additional questions: model_service_id=%s",
            model_config.model_service_id,
        )
        result = await model.invoke([UserMessage(content=query)])
        return result.content
