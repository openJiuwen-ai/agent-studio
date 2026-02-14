#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from __future__ import annotations
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Dict, Any, Literal, Optional

from openai import OpenAI, AsyncOpenAI
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig

from openjiuwen_studio.ops.modules.llm.llm_config_service import LLMConfigService
from openjiuwen_studio.core.utils.compatible_field import compatible_provider

# 全局单例，方便后面拿配置
_config_service: LLMConfigService | None = None


def init_llm_manager(config_service: LLMConfigService) -> None:
    """在应用启动时调用一次，把配置服务注入进来"""
    global _config_service
    _config_service = config_service


@lru_cache(maxsize=32)
def _create_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


@lru_cache(maxsize=32)
def _create_async_client(base_url: str, api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def get_openai_client(model_id: str, source: Literal["db", "config"] = "config") -> OpenAI:
    """业务获取 llm client 唯一需要调用的入口"""
    if _config_service is None:
        raise RuntimeError("LLM manager not initialized, call init_llm_manager() first")

    cfg = _config_service.get_llm_model_info(model_id, source=source)
    protocol = cfg.get("protocol_config", "")
    return _create_client(
        base_url=protocol.get("base_url"),
        api_key=protocol.get("api_key"),
    )


def get_llm_client(model_id: str, source: Literal["db", "config"] = "config"):
    """业务获取 llm client 唯一需要调用的入口"""
    if _config_service is None:
        raise RuntimeError("LLM manager not initialized, call init_llm_manager() first")

    cfg = _config_service.get_llm_model_info(model_id, source=source)
    protocol = cfg.get("protocol_config", "")
    model_client_config = ModelClientConfig(
        client_provider=compatible_provider(protocol.get("provider")),
        api_key=protocol.get("api_key", ""),
        api_base=protocol.get("base_url", ""),
        timeout=protocol.get("timeout", 60),
        verify_ssl=os.getenv("LLM_SSL_VERIFY", "true") == "false",
    )
    model = Model(
        model_client_config=model_client_config,
        model_config=ModelRequestConfig()
    )
    return model


def get_llm_client_by_protocol(protocol: Dict[str, Any]):
    """业务获取 llm client 唯一需要调用的入口"""
    if protocol is None:
        raise RuntimeError("LLM protocol config empty")

    model_client_config = ModelClientConfig(
        client_provider=compatible_provider(protocol.get("provider")),
        api_key=protocol.get("api_key", ""),
        api_base=protocol.get("base_url", ""),
        timeout=protocol.get("timeout", 60),
        verify_ssl=os.getenv("LLM_SSL_VERIFY", "true") == "false",
    )
    model = Model(
        model_client_config=model_client_config,
        model_config=ModelRequestConfig(model=protocol.get("model", ""))
    )
    return model


def get_async_openai_client(model_id: str, source: Literal["db", "config"] = "config") -> AsyncOpenAI:
    """异步客户端"""
    if _config_service is None:
        raise RuntimeError("LLM manager not initialized, call init_llm_manager() first")

    cfg = _config_service.get_llm_model_info(model_id, source=source)
    protocol = cfg.get("protocol_config", {})
    return _create_async_client(
        base_url=protocol.get("base_url", ""),
        api_key=protocol.get("api_key", ""),
    )


@dataclass
class ModelCallParams:
    model_id: str
    model_from: str
    messages: List[Dict[str, Any]]
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


def build_call_kwargs(params: ModelCallParams, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """ 拼接 OpenAI 入参，用于流式输出，优先级：前端显式值 > 配置文件默认值 """

    def _default(param: str, cast: type, default_cast_value: Any):
        for schema in cfg["openModel"]["param_config"]["param_schemas"]:
            if schema["name"] == param:
                return cast(schema["default_val"])
        return default_cast_value

    call_kwargs = {
        "model": cfg["protocol_config"]["model"],
        "model_name": cfg["protocol_config"]["model"],
        "messages": params.messages,
        "temperature": (
            params.temperature if params.temperature is not None
            else _default("temperature", float, 1.0)
        ),
        "top_p": (
            params.top_p if params.top_p is not None
            else _default("top_p", float, 1.0)
        ),
        "max_tokens": (
            params.max_tokens if params.max_tokens is not None
            else _default("max_tokens", int, 2048)
        ),
    }

    if params.tools:
        call_kwargs["tools"] = params.tools
        if params.tool_choice:
            call_kwargs["tool_choice"] = params.tool_choice

    return call_kwargs