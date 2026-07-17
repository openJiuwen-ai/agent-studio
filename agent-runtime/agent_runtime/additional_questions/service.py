# agent_runtime/additional_questions/service.py
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""追问生成服务 — 编排会话获取、prompt 构建、模型调用、结果解析。

核心流程：
1. 校验请求（name 非空、enable 为 True）
2. 从 Redis 读取历史会话
3. 取最近 2 条消息拼成 historyMessages
4. 渲染追问 prompt 模板（CN/EN）
5. 从 OBS/IR 读取模型配置（Strategy：agent→modelConfig，workflow→model）
6. 调用 LLM（最多重试 MODEL_CALLS 次）
7. 解析 JSON 返回，截断到 MAX_QUESTIONS 条
"""

import json
import logging

from agent_runtime.schemas.additional_questions import (
    AdditionalQuestionsContext,
    AdditionalQuestionsModelConfig,
    AdditionalQuestionsRequest,
    AdditionalQuestionsResponse,
)
from agent_runtime.additional_questions.conversation_reader import (
    ConversationReader,
)
from agent_runtime.additional_questions.model_invoker import (
    AdditionalQuestionsModelInvoker,
)
from agent_runtime.additional_questions.prompt_builder import (
    AdditionalQuestionsPromptBuilder,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from openjiuwen.core.common.logging import workflow_logger

logger = logging.getLogger(__name__)

# Agent/Workflow 对应的 IR 配置 key
IR_CONFIG_KEY_MAP = {
    "agent": "modelConfig",
    "workflow": "model",
}


class AdditionalQuestionsService:
    """追问生成服务 — 编排完整管道。"""

    MODEL_CALLS = 3  # 最大重试次数
    MAX_QUESTIONS = 3  # 最大追问数
    MIN_HISTORY_MESSAGES = 2  # 最少历史消息数

    def __init__(self):
        self.conversation_reader = ConversationReader()
        self.prompt_builder = AdditionalQuestionsPromptBuilder()
        self.model_invoker = AdditionalQuestionsModelInvoker()

    async def generate(
        self,
        ctx: AdditionalQuestionsContext,
        request: AdditionalQuestionsRequest,
        headers: dict,
    ) -> AdditionalQuestionsResponse:
        """生成追问建议列表。"""
        # 1. 校验
        if not request.name:
            raise JiuWenBaseException(
                error_code=StatusCode.PARAM_CHECK_FAILED_ERROR.code,
                message="name is required for additional questions",
            )
        if not request.enable:
            # 与 Java AgentRuntimeService 行为一致：enable=False 视为接口调用异常
            # （Java 抛出 INTERFACE_CALL_EXCEPTION）
            raise JiuWenBaseException(
                error_code=StatusCode.PARAM_CHECK_FAILED_ERROR.code,
                message="additional questions is not enabled",
            )

        # 2. 获取历史会话
        messages = await self.conversation_reader.get_history(
            ctx.resource_id, ctx.conversation_id, request.version_id,
        )

        # 3. 历史消息不足
        if len(messages) < self.MIN_HISTORY_MESSAGES:
            workflow_logger.info(
                "Not enough history messages for additional questions: "
                "resource_id=%s, conversation_id=%s, count=%d",
                ctx.resource_id, ctx.conversation_id, len(messages),
            )
            return AdditionalQuestionsResponse(questions=[])

        # 4. 格式化历史文本（取最后 2 条消息内容）
        history_text = self._format_history(messages)

        # 5. 构建 prompt
        language = self._detect_language(headers)
        query = self.prompt_builder.build(
            name=request.name,
            history_messages=history_text,
            user_prompt=request.prompt,
            language=language,
        )

        # 6. 获取模型配置
        model_config = await self._resolve_model_config(
            ctx.resource_type, ctx.resource_id, headers,
        )

        # 7. 调用模型（最多重试 MODEL_CALLS 次）
        questions = []
        for attempt in range(self.MODEL_CALLS):
            try:
                raw_content = await self.model_invoker.invoke(
                    model_config, query, headers,
                )
                questions = self._parse_response(raw_content)
                if questions:
                    break
            except Exception as e:
                workflow_logger.warning(
                    "LLM call failed on attempt %d/%d for additional questions: %s",
                    attempt + 1, self.MODEL_CALLS, e,
                )

        # 8. 截断并返回
        questions = questions[: self.MAX_QUESTIONS]
        workflow_logger.info(
            "Additional questions generated: resource_type=%s, resource_id=%s, "
            "conversation_id=%s, count=%d",
            ctx.resource_type, ctx.resource_id, ctx.conversation_id, len(questions),
        )
        return AdditionalQuestionsResponse(questions=questions)

    @staticmethod
    def _format_history(messages: list[dict]) -> str:
        """取最后 2 条消息内容拼接为文本。"""
        last_two = messages[-2:]
        return "\n".join(m.get("content", "") for m in last_two)

    @staticmethod
    def _parse_response(content: str) -> list[str]:
        """解析 LLM 返回的 JSON 数组。兼容 markdown 代码块包裹。"""
        content = content.strip()
        # 剥离 markdown 代码块包裹（```json ... ```）
        if content.startswith("```"):
            lines = content.split("\n")
            # 去掉首行 ```json 和末行 ```
            lines = [line for line in lines if not line.strip().startswith("```")]
            content = "\n".join(lines).strip()
        # 尝试提取 JSON 数组
        if content.startswith("["):
            try:
                result = json.loads(content)
                if isinstance(result, list):
                    return [str(q) for q in result if isinstance(q, (str, int, float))]
            except json.JSONDecodeError:
                pass
        return []

    async def _resolve_model_config(
        self, resource_type: str, resource_id: str, headers: dict,
    ) -> AdditionalQuestionsModelConfig:
        """从 OBS 读取 IR，提取模型配置。"""
        ir_data = await self._load_ir(resource_id, resource_type)
        config_key = IR_CONFIG_KEY_MAP.get(resource_type)
        if not config_key:
            raise ValueError(f"Unsupported resource_type: {resource_type}")

        configs = ir_data.get("configs", {})
        # Agent 场景兼容旧版 IR：优先 modelConfig，fallback 到 llm_config
        model_config = configs.get(config_key) or configs.get("llm_config", {})
        model_service_id = model_config.get("modelName", "")
        auth_id = model_config.get("extension", {}).get("authId", "")

        if not model_service_id:
            raise ValueError(
                f"Model service ID not found in IR for {resource_type}: "
                f"resource_id={resource_id}, config_key={config_key}"
            )

        return AdditionalQuestionsModelConfig(
            model_service_id=model_service_id,
            auth_id=auth_id,
        )

    @staticmethod
    async def _load_ir(resource_id: str, resource_type: str) -> dict:
        """从 OBS 加载 IR JSON。"""
        from agent_runtime.context.request_context import _request_ctx

        ctx = _request_ctx.get()
        ir_path = ""
        if ctx and ctx.headers:
            ir_path = ctx.headers.get("x-ir-path", "") or ctx.headers.get("X-Ir-Path", "")

        if not ir_path:
            obj_type = "agent" if resource_type == "agent" else "workflow"
            ir_path = f"{obj_type}/ir/{resource_id}/{resource_id}.json"

        return await async_ir_load(ir_path)

    @staticmethod
    def _detect_language(headers: dict) -> str:
        """检测语言：检查 x-language 和 accept-language 头。"""
        lang = headers.get("x-language", "") or headers.get("X-Language", "")
        if lang and lang.lower().startswith("zh"):
            return "zh"
        accept = headers.get("accept-language", "") or headers.get("Accept-Language", "")
        if accept and "zh" in accept.lower():
            return "zh"
        return "en"
