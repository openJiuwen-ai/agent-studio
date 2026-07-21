#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
模型配置提供者 — 部署级别的模型配置实现

提供可插拔的模型配置来源：
1. EnvVarModelConfigProvider - 从环境变量读取
2. OBSModelConfigProvider - 从 OBS 对象存储读取模型服务元数据和认证信息
3. IRModelConfigProvider - 从 IR 配置读取，环境变量作为默认值兜底（推荐用于旧版九问 IR 兼容）
4. Nl2ModelConfigProvider - 从 NL2 Agent 的 modelInfo 读取模型配置，用于 nl_to_agent 模块调用模型
"""

from typing import Optional

from agent_runtime.common.config import settings
from agent_runtime.common.ir_interfaces import ModelConfigProvider
from agent_runtime.context.request_context import _request_ctx
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.workflow.components.llm.llm_comp import LLMCompConfig

import model_service  # noqa: F401  -- 触发 StudioModelClient 注册进 openjiuwen registry（client_provider="studio" 须先注册）


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


class EnvVarModelConfigProvider(ModelConfigProvider):
    """从环境变量读取模型配置"""

    async def get_llm_config(
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
        max_tokens = hyper_params.get("max_tokens", None)
        frequency_penalty = hyper_params.get("frequency_penalty", None)

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
            max_tokens=max_tokens,
        )
        # frequency_penalty 通过 extra="allow" 机制传入 ModelRequestConfig
        if frequency_penalty is not None:
            model_request_config.frequency_penalty = frequency_penalty

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
    async def get_llm_config(model_info) -> LLMCompConfig:
        """从 modelInfo 构建 LLM 组件配置

        Args:
            model_info: LLMModelInfo 实例，包含 model、model_source、headers 等字段

        Returns:
            LLMCompConfig: LLM 组件配置
        """
        base = settings.llm

        headers = model_info.headers or {}
        # 模型路由服务需要用 deploymentId（UUID）作为 model 参数
        model_name = model_info.model or base.model_name
        auth_id = headers.get("auth_id", "")
        x_auth_token = headers.get("x_auth_token", "")

        ctx = _request_ctx.get()
        if ctx and ctx.headers:
            if not x_auth_token:
                x_auth_token = ctx.headers.get("x-auth-token", "") or ctx.headers.get("X-Auth-Token", "")

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


async def get_nl2_model(model_info) -> Model:
    """工厂方法：根据 modelInfo 创建 openjiuwen Model 实例

    用于 nl_to_agent 模块中 Nl2AgentProcessor 获取模型实例，
    替代原来通过 LLMServiceManager -> ModelFactory -> Nl2AgentBuilderModel 的调用链。

    Args:
        model_info: LLMModelInfo 实例，包含 model、model_source、headers 等字段

    Returns:
        Model: openjiuwen 的 Model 实例，支持 invoke/stream 等调用方式
    """
    llm_config = await Nl2ModelConfigProvider.get_llm_config(model_info)
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
    async def get_llm_config(model_info) -> LLMCompConfig:
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
        # model_info.model 已是 UUID（deploymentId），模型路由服务需要 UUID 作为 model 参数
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


async def get_prompt_optimize_model(model_info) -> Model:
    """工厂方法：为提示词优化特性创建 openjiuwen Model 实例

    用于 agent_builder 的 prompt 管理模块（prompt.py / mmapo.py）获取模型实例，
    替代原来通过 LLMServiceManager -> EiCloudLLMService -> OpenAICompatibleService 的调用链。

    Args:
        model_info: LLMModelInfo 实例（agent_builder.prompt.common.config.LLMModelInfo），
                    包含 model、headers、temperature、top_p 等字段

    Returns:
        Model: openjiuwen 的 Model 实例，支持 invoke/stream 等调用方式
    """
    llm_config = await PromptOptimizeModelProvider.get_llm_config(model_info)
    return Model(
        model_client_config=llm_config.model_client_config,
        model_config=llm_config.model_config,
    )


class OBSModelConfigProvider(ModelConfigProvider):
    """从 OBS 对象存储读取模型配置（薄配置）。

    IR 节点的 modelName 存储的是 modelServiceId（UUID），据此定位 OBS 元数据：

    - ``model-service/ir/{modelServiceId}.json``：模型服务信息（apiUrl / modelName / providerId /
      projectId）。
    - ``model-auth/auth/{projectId}/{providerId}/{authId}.json``：鉴权信息（authType / authInfo）。

    本 provider 只构建薄 ``LLMCompConfig``（``client_provider="studio"`` + extra 字段携带
    model_service_id / auth_id / refresh），真实解析延迟到 ``StudioModelClient.invoke`` 时由
    ``model_service.resolver`` 完成，以支持 refresh / failover 重解析。projectId / workspace_id
    不放入 config，由 ``StudioModelClient`` 从请求头取。
    """

    async def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        """构建薄 ``LLMCompConfig``，真实解析延迟到 ``StudioModelClient.invoke`` 时完成。

        不在此解析真实 api_base / api_key，仅把解析所需输入放入 ``ModelClientConfig`` extra 字段
        （model_service_id / auth_id / refresh）；连接信息由 ``model_service.resolver`` 在 invoke
        时解析，支持 refresh / failover 重解析。
        """
        # 1. 从 IR 节点提取 modelServiceId 和超参数
        configs = ir_node.get("configs", {})
        model_config = configs.get("modelConfig") or configs.get("model", {})
        hyper_params = model_config.get("hyperParameters", {})

        raw_model_name = (
            model_config.get("modelName")
            or model_config.get("model_name")
            or ""
        )

        if not raw_model_name:
            raise ValueError(
                "OBSModelConfigProvider: modelName (modelServiceId) is required in IR node"
            )

        # pipe-delimited 格式 "deploymentId|serviceId" 取首段作为 modelServiceId
        model_service_id = raw_model_name.split("|")[0]

        # 2. 提取 auth_id / refresh（解析延迟到 invoke 时）
        extension = model_config.get("extension", {})
        auth_id = extension.get("authId", "")
        refresh = bool(model_config.get("refresh") or extension.get("refresh"))

        # 3. 薄配置：api_base / api_key 为占位（BaseModelClient._validate_config 要求非空），
        #    真实连接信息由 resolver 在 invoke 时解析。
        base = settings.llm
        model_client_config = ModelClientConfig(
            client_provider="studio",
            api_key="sk-placeholder",
            api_base="https://studio-placeholder",
            timeout=base.timeout,
            verify_ssl=base.ssl_verify,
            model_service_id=model_service_id,   # extra 字段，供 StudioModelClient 解析
            auth_id=auth_id,
            refresh=refresh,
        )

        # 4. 请求级超参数；真实 model_name 由 resolver 解析后在 _invoke_one_model 覆盖。
        temperature = hyper_params.get("temperature", base.temperature)
        top_p = hyper_params.get("top_p", base.top_p)
        max_tokens = hyper_params.get("max_tokens", None)
        frequency_penalty = hyper_params.get("frequency_penalty", None)

        extra_body = None
        thinking = hyper_params.get("thinking")
        if thinking and isinstance(thinking, dict) and "type" in thinking:
            extra_body = {"thinking": thinking}

        model_request_config = ModelRequestConfig(
            model=model_service_id,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
        if frequency_penalty is not None:
            model_request_config.frequency_penalty = frequency_penalty

        return LLMCompConfig(
            model_client_config=model_client_config,
            model_config=model_request_config,
            cache_stream=True,
        )



class IRModelConfigProvider(ModelConfigProvider):
    """从 IR 配置读取模型参数，环境变量作为默认值兜底

    适用于商用九问 IR 文件兼容场景：
    - 从 IR 节点的 configs.model/modelConfig 读取模型配置
    - authId 从 IR 配置获取，authToken 从 HTTP 请求头透传
    - 环境变量作为兜底默认值
    """

    async def get_llm_config(
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

        # max_tokens: IR hyperParameters 优先，否则使用 settings 默认值
        max_tokens = hyper_params.get("max_tokens", None)
        # frequency_penalty: 仅从 IR hyperParameters 获取（settings 无此字段）
        frequency_penalty = hyper_params.get("frequency_penalty", None)

        # Build auth headers
        ctx = _request_ctx.get()
        auth_token = ctx.headers.get("X-Auth-Token", "") if ctx else ""
        custom_headers = {"X-Auth-Id": auth_id, "X-Auth-Token": auth_token}

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

        # 构建 ModelRequestConfig，传递所有已知的超参数
        # ModelRequestConfig 定义了 model_name(aliased as "model"), temperature, top_p, max_tokens, stop
        # 并设置了 extra="allow"，因此 frequency_penalty 等额外字段会被保留
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
