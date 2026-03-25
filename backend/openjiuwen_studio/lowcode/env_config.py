#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
环境变量模型配置工具

支持从环境变量注入模型配置信息（API Key、Base URL等）
"""

import os
import re
from typing import Dict, Optional, Any


def model_name_to_prefix(model_name: str) -> str:
    """
    将模型名称转换为环境变量前缀
    
    Args:
        model_name: 模型名称，如 "gpt-4", "Qwen/Qwen3-8B", "deepseek-chat"
        
    Returns:
        环境变量前缀，如 "GPT4", "QWENQWEN38B", "DEEPSEEKCHAT"
        
    Examples:
        >>> model_name_to_prefix("gpt-4")
        'GPT4'
        >>> model_name_to_prefix("Qwen/Qwen3-8B")
        'QWENQWEN38B'
        >>> model_name_to_prefix("deepseek-chat")
        'DEEPSEEKCHAT'
    """
    if not model_name:
        return ""
    
    clean_name = model_name.replace("/", "").replace("-", "").replace("_", "").replace(".", "")
    
    return clean_name.upper()


def get_model_config_from_env(model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    从环境变量获取模型配置
    
    优先级：
    1. 模型特定配置（LLM_{PREFIX}_*）
    2. 通用配置（LLM_*）
    
    Args:
        model_name: 模型名称，如 "Qwen/Qwen3-8B"。如果为None，只返回通用配置
        
    Returns:
        模型配置字典，包含:
        - provider: 提供商
        - api_key: API密钥
        - api_base: API基础URL
        - timeout: 超时时间
        如果没有找到配置则返回None
        
    Examples:
        >>> os.environ["LLM_API_KEY"] = "sk-xxx"
        >>> os.environ["LLM_API_BASE"] = "https://api.example.com/v1"
        >>> os.environ["LLM_PROVIDER"] = "OpenAI"
        >>> config = get_model_config_from_env()
        >>> print(config['api_key'])
        'sk-xxx'
    """
    config = {}
    
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    provider = os.getenv("LLM_PROVIDER")
    timeout_str = os.getenv("LLM_TIMEOUT")
    
    if timeout_str:
        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 300
    else:
        timeout = 300
    
    if not any([api_key, api_base, provider]):
        return None
    
    if api_key:
        config["api_key"] = api_key
    if api_base:
        config["api_base"] = api_base
    if provider:
        config["provider"] = provider
    if timeout:
        config["timeout"] = timeout
    
    if model_name:
        prefix = model_name_to_prefix(model_name)
        
        model_api_key = os.getenv(f"LLM_{prefix}_API_KEY")
        model_api_base = os.getenv(f"LLM_{prefix}_API_BASE")
        model_provider = os.getenv(f"LLM_{prefix}_PROVIDER")
        model_timeout_str = os.getenv(f"LLM_{prefix}_TIMEOUT")
        
        if model_api_key:
            config["api_key"] = model_api_key
        if model_api_base:
            config["api_base"] = model_api_base
        if model_provider:
            config["provider"] = model_provider
        if model_timeout_str:
            try:
                config["timeout"] = int(model_timeout_str)
            except ValueError:
                pass
    
    if not config.get("api_key"):
        return None
    
    return config


def list_available_model_configs() -> Dict[str, Dict[str, Any]]:
    """
    列出所有可用的模型配置
    
    扫描环境变量，找出所有已配置的模型
    
    Returns:
        配置字典，key为前缀，value为配置信息
        
    Examples:
        >>> os.environ["LLM_API_KEY"] = "sk-xxx"
        >>> os.environ["LLM_QWENQWEN38B_API_KEY"] = "sk-yyy"
        >>> configs = list_available_model_configs()
        >>> print(configs.keys())
        dict_keys(['DEFAULT', 'QWENQWEN38B'])
    """
    configs = {}
    
    default_config = get_model_config_from_env()
    if default_config:
        configs["DEFAULT"] = default_config
    
    pattern = re.compile(r'^LLM_([A-Z0-9]+)_API_KEY$')
    
    for key in os.environ:
        match = pattern.match(key)
        if match:
            prefix = match.group(1)
            
            if prefix in ["API"]:
                continue
            
            config = get_model_config_from_env_by_prefix(prefix)
            if config:
                configs[prefix] = config
    
    return configs


def get_model_config_from_env_by_prefix(prefix: str) -> Optional[Dict[str, Any]]:
    """
    根据前缀获取模型配置
    
    Args:
        prefix: 环境变量前缀，如 "QWENQWEN38B"
        
    Returns:
        模型配置字典，如果没有找到则返回None
    """
    api_key = os.getenv(f"LLM_{prefix}_API_KEY")
    api_base = os.getenv(f"LLM_{prefix}_API_BASE")
    provider = os.getenv(f"LLM_{prefix}_PROVIDER")
    timeout_str = os.getenv(f"LLM_{prefix}_TIMEOUT")
    
    if not api_key:
        return None
    
    config = {"api_key": api_key}
    
    if api_base:
        config["api_base"] = api_base
    if provider:
        config["provider"] = provider
    if timeout_str:
        try:
            config["timeout"] = int(timeout_str)
        except ValueError:
            config["timeout"] = 300
    else:
        config["timeout"] = 300
    
    return config


def inject_env_config_to_model_ref(
    model_ref: Dict[str, Any],
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    将环境变量配置注入到模型引用中
    
    Args:
        model_ref: 模型引用配置
        model_name: 模型名称
        
    Returns:
        更新后的模型引用配置
    """
    env_config = get_model_config_from_env(model_name)
    
    if not env_config:
        return model_ref
    
    updated_ref = model_ref.copy()
    
    if env_config.get("api_key") and not updated_ref.get("api_key"):
        updated_ref["api_key"] = env_config["api_key"]
    
    if env_config.get("api_base") and not updated_ref.get("base_url"):
        updated_ref["base_url"] = env_config["api_base"]
    
    if env_config.get("provider") and not updated_ref.get("provider"):
        updated_ref["provider"] = env_config["provider"]
    
    if env_config.get("timeout") and not updated_ref.get("timeout"):
        updated_ref["timeout"] = env_config["timeout"]
    
    return updated_ref
