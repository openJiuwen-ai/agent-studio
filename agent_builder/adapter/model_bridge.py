#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
Model providers bridge: full replica of agent_runtime.common.model_providers.

Provides identical classes and functions:
  - EnvVarModelConfigProvider
  - Nl2ModelConfigProvider
  - get_nl2_model()
  - PromptOptimizeModelProvider
  - get_prompt_optimize_model()
  - OBSModelConfigProvider
  - IRModelConfigProvider
  - _normalize_api_base()
  - _extract_auth_headers()
"""

from typing import Optional

from agent_builder.adapter.config_bridge import settings
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.workflow.components.llm.llm_comp import LLMCompConfig


def _normalize_api_base(url: str) -> str:
    """标准化 API base URL，去除末尾的 /chat/completions 路径"""
    url = url.rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    return url


def _extract_auth_headers(headers: dict) -> dict:
    """从 headers 中提取九问平台认证头

    支持两种 key 格式：
    - 下划线格式（modelInfo 原始格式）: auth_id, x_auth_token, deployment_id
    - HTTP 头格式（Flask request.headers 合并后）: X-Auth-Id, X-Auth-Token, X-Deployment-Id

    Returns:
        dict: 仅包含 X-Auth-Id, X-Auth-Token, X-Deployment-Id 的认证头
    """
    if not headers:
        return {}

    custom_headers = {}

    # auth_id
    auth_id = (
        headers.get("auth_id", "")
        or headers.get("Auth_id", "")
        or headers.get("X-Auth-Id", "")
        or headers.get("x-auth-id", "")
    )
    if auth_id:
        custom_headers["X-Auth-Id"] = auth_id

    # x_auth_token
    x_auth_token = (
        headers.get("x_auth_token", "")
        or headers.get("X_auth_token", "")
        or headers.get("X-Auth-Token", "")
        or headers.get("x-auth-token", "")
    )
    if x_auth_token:
        custom_headers["X-Auth-Token"] = x_auth_token

    # deployment_id
    deployment_id = (
        headers.get("deployment_id", "")
        or headers.get("Deployment_id", "")
        or headers.get("X-Deployment-Id", "")
        or headers.get("x-deployment-id", "")
    )
    if deployment_id:
        custom_headers["X-Deployment-Id"] = deployment_id

    return custom_headers


class EnvVarModelConfigProvider:
    """从环境变量读取模型配置"""

    def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        """Get LLM configuration purely from settings/environment variables."""
        base = settings.llm

        # IR override for hyperparameters only
        configs = ir_node.get("configs", {})
        hyper_params = configs.get("hyperParameters", {})

        temperature = hyper_params.get("temperature", base.temperature)
        top_p = hyper_params.get("top_p", base.top_p)

        model_client_config = ModelClientConfig(
            client_provider="openai",
            api_key=base.api_key,
            api_base=base.api_base,
            timeout=base.timeout,
            verify_ssl=base.ssl_verify,
        )

        model_request_config = ModelRequestConfig(
            model=base.model_name,
            temperature=temperature,
            top_p=top_p,
        )

        return LLMCompConfig(
            model_client_config=model_client_config,
            model_config=model_request_config,
            cache_stream=True,
        )


class Nl2ModelConfigProvider:
    """从 NL2 Agent 的 modelInfo 读取模型配置

    适用于 nl_to_agent 模块调用模型的场景：
    - 从前端传入的 modelInfo（LLMModelInfo）中提取模型名称、认证信息等
    - 环境变量作为 api_key、api_base 等连接参数的兜底默认值
    - authId 和 authToken 从 modelInfo.headers 和 HTTP 请求头透传
    """

    @staticmethod
    def get_llm_config(model_info) -> LLMCompConfig:
        """从 modelInfo 构建 LLM 组件配置"""
        base = settings.llm

        headers = model_info.headers or {}
        model_name = model_info.model or base.model_name
        auth_id = headers.get("auth_id", "")
        x_auth_token = headers.get("x_auth_token", "")

        custom_headers = {}
        if auth_id:
            custom_headers["X-Auth-Id"] = auth_id
        if x_auth_token:
            custom_headers["X-Auth-Token"] = x_auth_token
        deployment_id = headers.get("deployment_id", "")
        if deployment_id:
            custom_headers["X-Deployment-Id"] = deployment_id

        model_client_config = ModelClientConfig(
            client_provider="openai",
            api_key=base.api_key,
            api_base=base.api_base,
            timeout=base.timeout,
            verify_ssl=base.ssl_verify,
            custom_headers=custom_headers,
        )

        model_request_config = ModelRequestConfig(
            model=model_name,
            temperature=model_info.temperature if model_info.temperature is not None else base.temperature,
            top_p=model_info.top_p if model_info.top_p is not None else base.top_p,
        )

        return LLMCompConfig(
            model_client_config=model_client_config,
            model_config=model_request_config,
            cache_stream=True,
        )


def get_nl2_model(model_info) -> Model:
    """工厂方法：根据 modelInfo 创建 openjiuwen Model 实例

    用于 nl_to_agent 模块中 Nl2AgentProcessor 获取模型实例，
    替代原来通过 LLMServiceManager -> ModelFactory -> Nl2AgentBuilderModel 的调用链。

    Args:
        model_info: LLMModelInfo 实例，包含 model、model_source、headers 等字段

    Returns:
        Model: openjiuwen 的 Model 实例，支持 invoke/stream 等调用方式
    """
    llm_config = Nl2ModelConfigProvider.get_llm_config(model_info)
    return Model(
        model_client_config=llm_config.model_client_config,
        model_config=llm_config.model_config,
    )


class PromptOptimizeModelProvider:
    """提示词优化专用的模型配置提供者

    适用于 agent_builder 的 prompt 管理特性（prompt.py / mmapo.py）：
    - 从前端传入的 modelInfo（LLMModelInfo）中提取模型名称、温度等参数
    - 环境变量（settings.llm）作为 api_key、api_base 等连接参数的主源
    - authId 和 authToken 从 modelInfo.headers 提取（兼容下划线和 HTTP 头两种格式）
    - 参考 Nl2ModelConfigProvider 的配置逻辑，独立实现以解耦
    """

    @staticmethod
    def get_llm_config(model_info) -> LLMCompConfig:
        """从 modelInfo 构建提示词优化专用的 LLM 组件配置

        Args:
            model_info: LLMModelInfo 实例（agent_builder.prompt.common.config.LLMModelInfo），
                        包含 model、headers、temperature、top_p 等字段

        Returns:
            LLMCompConfig: LLM 组件配置
        """
        base = settings.llm
        headers = model_info.headers or {}

        # --- 连接参数：以 settings.llm 环境变量为主 ---
        api_base = base.api_base or ""
        api_key = base.api_key or ""
        timeout = base.timeout
        verify_ssl = base.ssl_verify

        # 如果 settings.llm 未配置 api_base，回退到 modelInfo.url（向后兼容）
        if not api_base:
            raw_url = getattr(model_info, "url", "") or ""
            api_base = _normalize_api_base(raw_url)
        if not api_key or api_key == "sk-placeholder":
            api_key = getattr(model_info, "api_key", "") or ""

        # 走 Model Router 时，鉴权由 Router 服务端处理，客户端 api_key 仅需通过 agent-core 校验
        api_key = api_key or "sk-placeholder"

        # --- 模型参数：modelInfo 优先，settings.llm 兜底 ---
        model_name = getattr(model_info, "model", "") or base.model_name
        temperature = getattr(model_info, "temperature", None)
        if temperature is None:
            temperature = base.temperature
        top_p = getattr(model_info, "top_p", None)
        if top_p is None:
            top_p = base.top_p

        # --- 认证头：从 modelInfo.headers 提取九问平台标准认证头 ---
        custom_headers = _extract_auth_headers(headers)

        model_client_config = ModelClientConfig(
            client_provider="openai",
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            verify_ssl=verify_ssl,
            custom_headers=custom_headers if custom_headers else None,
        )

        model_request_config = ModelRequestConfig(
            model=model_name,
            temperature=temperature,
            top_p=top_p,
        )

        return LLMCompConfig(
            model_client_config=model_client_config,
            model_config=model_request_config,
            cache_stream=True,
        )


def get_prompt_optimize_model(model_info) -> Model:
    """工厂方法：为提示词优化特性创建 openjiuwen Model 实例

    用于 agent_builder 的 prompt 管理模块（prompt.py / mmapo.py）获取模型实例，
    替代原来通过 LLMServiceManager -> EiCloudLLMService -> OpenAICompatibleService 的调用链。

    Args:
        model_info: LLMModelInfo 实例（agent_builder.prompt.common.config.LLMModelInfo），
                    包含 model、headers、temperature、top_p 等字段

    Returns:
        Model: openjiuwen 的 Model 实例，支持 invoke/stream 等调用方式
    """
    llm_config = PromptOptimizeModelProvider.get_llm_config(model_info)
    return Model(
        model_client_config=llm_config.model_client_config,
        model_config=llm_config.model_config,
    )


class OBSModelConfigProvider:
    """从 OBS 模型网关读取模型配置（后续开发）"""

    def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        raise NotImplementedError("OBSModelConfigProvider 尚未实现")


class IRModelConfigProvider:
    """从 IR 配置读取模型参数，环境变量作为默认值兜底

    适用于商用九问 IR 文件兼容场景：
    - 从 IR 节点的 configs.model/modelConfig 读取模型配置
    - authId 从 IR 配置获取，authToken 从 HTTP 请求头透传
    - 环境变量作为兜底默认值
    """

    def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        """Get LLM configuration from settings with IR override.

        Priority: IR node config > environment variables (via settings) > defaults
        """
        # Extract IR model config
        configs = ir_node.get("configs", {})
        model_config = configs.get("modelConfig") or configs.get("model", {})
        hyper_params = model_config.get("hyperParameters", {})

        # Get base values from settings (environment variables auto-injected)
        base = settings.llm

        # Apply IR override with settings fallback
        model_name = (
            model_config.get("modelName")
            or model_config.get("model_name")
            or base.model_name
        )
        auth_id = model_config.get("extension", {}).get("authId", "")

        temperature = hyper_params.get("temperature", base.temperature)
        top_p = hyper_params.get("top_p", base.top_p)

        # Build auth headers
        custom_headers = {"X-Auth-Id": auth_id}

        # Build client config
        model_client_config = ModelClientConfig(
            client_provider="openai",
            api_key=base.api_key,
            api_base=base.api_base,
            timeout=base.timeout,
            verify_ssl=base.ssl_verify,
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
            extra_body=extra_body,
        )

        return LLMCompConfig(
            model_client_config=model_client_config,
            model_config=model_request_config,
            cache_stream=True,
        )
