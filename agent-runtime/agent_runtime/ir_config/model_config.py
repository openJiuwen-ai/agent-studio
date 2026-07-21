#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
模型配置提供者 — 部署级别的模型配置实现

提供可插拔的模型配置来源：
1. EnvVarModelConfigProvider - 从环境变量读取
2. OBSModelConfigProvider - 从 OBS 对象存储读取模型服务元数据和认证信息
"""

import os
from typing import Optional

from agent_runtime.common.config import settings
from agent_runtime.common.ir_interfaces import ModelConfigProvider
from agent_runtime.context.request_context import _request_ctx
from openjiuwen.core.foundation.llm import ModelClientConfig, ModelRequestConfig
from openjiuwen.core.workflow.components.llm.llm_comp import LLMCompConfig


class EnvVarModelConfigProvider(ModelConfigProvider):
    """从环境变量读取模型配置"""

    async def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        provider = "openai"
        api_key = os.environ.get("IR_LLM_API_KEY")
        if not api_key:
            raise ValueError("IR_LLM_API_KEY 环境变量未设置")
        api_base = os.environ.get("IR_LLM_API_BASE", "https://api.deepseek.com")
        model_name = os.environ.get("IR_LLM_MODEL_NAME", "deepseek-chat")
        temperature = float(os.getenv("IR_LLM_TEMPERATURE", "0.5"))
        top_p = float(os.getenv("IR_LLM_TOP_P", "0.5"))
        verify_ssl = os.getenv("IR_LLM_SSL_VERIFY", "false").lower() == "true"

        # 从 IR 节点覆盖（如果存在）
        configs = ir_node.get("configs", {})
        hyper_params = configs.get("hyperParameters", {})

        # 优先级：IR configs > 环境变量 > 默认值
        temperature = float(hyper_params.get("temperature", temperature))
        top_p = float(hyper_params.get("top_p", top_p))
        max_tokens = hyper_params.get("max_tokens", None)
        frequency_penalty = hyper_params.get("frequency_penalty", None)

        model_client_config = ModelClientConfig(
            client_provider=provider,
            api_key=api_key,
            api_base=api_base,
            timeout=settings.llm.timeout,
            verify_ssl=verify_ssl,
        )

        model_request_config = ModelRequestConfig(
            model=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        # frequency_penalty 通过 extra="allow" 机制传入 ModelRequestConfig
        if frequency_penalty is not None:
            model_request_config.frequency_penalty = frequency_penalty

        cache_stream = True

        return LLMCompConfig(
            model_client_config=model_client_config,
            model_config=model_request_config,
            cache_stream=cache_stream,
        )


class OBSModelConfigProvider(ModelConfigProvider):
    """从 OBS 模型网关读取模型配置

    实际实现位于 agent_runtime.common.model_providers.OBSModelConfigProvider，
    此处仅做别名导出，保持向后兼容。
    """

    async def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        from agent_runtime.common.model_providers import OBSModelConfigProvider as _OBSProvider
        return await _OBSProvider().get_llm_config(ir_node, global_config)


class IRModelConfigProvider(ModelConfigProvider):
    """从 IR 配置读取模型参数，环境变量作为默认值兜底"""

    async def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        api_key = os.environ.get("IR_LLM_API_KEY", "mock_key")
        api_base = os.environ.get("MODEL_ROUTER_API", "https://api.deepseek.com")
        temperature = float(os.getenv("IR_LLM_TEMPERATURE", "0.5"))
        top_p = float(os.getenv("IR_LLM_TOP_P", "0.5"))
        verify_ssl = os.getenv("IR_LLM_SSL_VERIFY", "false").lower() == "true"

        # 从 IR 节点读取模型配置（节点级别的 configs.model 或 configs.modelConfig）
        configs = ir_node.get("configs", {})
        # 兼容两种字段名：modelConfig（商用九问）和 model（openjiuwen）
        model_config = configs.get("modelConfig") or configs.get("model", {})
        hyper_params = model_config.get("hyperParameters", {})

        # 提取具体参数
        model_name = (
            model_config.get("modelName")
            or model_config.get("model_name")
            or os.environ.get("IR_LLM_MODEL_NAME")
        )
        auth_id = model_config.get("extension", {}).get("authId", "")

        # IR hyper_params 优先级最高
        temperature = float(hyper_params.get("temperature", temperature))
        top_p = float(hyper_params.get("top_p", top_p))
        max_tokens = hyper_params.get("max_tokens", None)
        frequency_penalty = hyper_params.get("frequency_penalty", None)

        # custom_headers 自定义请求头
        # x-auth-id 从 IR 文件读取，x-auth-token 从 HTTP 请求头透传
        ctx = _request_ctx.get()
        auth_token = ctx.headers.get("X-Auth-Token", "")
        custom_headers = {"X-Auth-Id": auth_id, "X-Auth-Token": auth_token}
        model_client_config = ModelClientConfig(
            client_provider="openai",
            api_key=api_key,
            api_base=api_base,
            timeout=settings.llm.timeout,
            verify_ssl=verify_ssl,
            custom_headers=custom_headers,
        )

        extra_body = None
        thinking = hyper_params.get("thinking")
        if thinking and isinstance(thinking, dict) and "type" in thinking:
            extra_body = {"thinking": thinking}

        model_request_config = ModelRequestConfig(
            model=model_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
        # frequency_penalty 通过 extra="allow" 机制传入 ModelRequestConfig
        if frequency_penalty is not None:
            model_request_config.frequency_penalty = frequency_penalty

        return LLMCompConfig(
            model_client_config=model_client_config,
            model_config=model_request_config,
            cache_stream=True,
        )
