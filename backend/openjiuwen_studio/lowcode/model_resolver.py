#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
模型配置解析器 - 处理模型引用和运行时覆盖
"""

from typing import Any, Dict, Optional
import copy
import logging

from openjiuwen_studio.lowcode.schemas import ModelReference, ModelOverride
from openjiuwen_studio.lowcode.env_config import (
    get_model_config_from_env,
    inject_env_config_to_model_ref
)

logger = logging.getLogger(__name__)


class ModelResolver:
    """
    模型配置解析器
    
    处理模型引用和运行时覆盖
    """
    
    @staticmethod
    def resolve(
        agent_config: Dict[str, Any],
        model_references: Optional[Dict[str, Any]] = None,
        model_overrides: Optional[Dict[str, ModelOverride]] = None,
        use_env_config: bool = True
    ) -> Dict[str, Any]:
        """
        解析模型配置
        
        Args:
            agent_config: Agent 配置
            model_references: 模型引用定义
            model_overrides: 运行时覆盖配置
            use_env_config: 是否使用环境变量配置（默认True）
            
        Returns:
            处理后的配置
        """
        config = copy.deepcopy(agent_config)
        
        model_id = ModelResolver._get_model_id(config)
        
        if model_references:
            model_ref = ModelResolver._find_model_reference(model_references, model_id, config)
            if model_ref:
                logger.debug("Applying model reference for %s", model_id)
                
                if use_env_config:
                    model_name = model_ref.get("model_type") or model_ref.get("name")
                    model_ref = inject_env_config_to_model_ref(model_ref, model_name)
                
                config = ModelResolver._apply_model_reference(config, model_ref)
        
        if model_overrides and model_id:
            override = model_overrides.get(str(model_id))
            if override:
                logger.debug("Applying model override for %s", model_id)
                config = ModelResolver._apply_overrides(config, override)
        
        if use_env_config and not model_references:
            model_name = ModelResolver._get_model_name(config)
            env_config = get_model_config_from_env(model_name)
            if env_config:
                logger.debug("Applying environment config for model")
                config = ModelResolver._apply_env_config(config, env_config)
        
        return config
    
    @staticmethod
    def _find_model_reference(
        model_references: Dict[str, Any],
        model_id: Optional[str],
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        查找模型引用
        
        Args:
            model_references: 模型引用字典
            model_id: 模型 ID
            config: agent 配置
            
        Returns:
            模型引用配置或 None
        """
        if str(model_id) in model_references:
            return model_references[str(model_id)]
        
        if model_id and "/" in model_id and model_id in model_references:
            return model_references[model_id]
        
        provider = config.get("model", {}).get("model_provider", "")
        name = config.get("model", {}).get("model_name", "")
        if provider and name:
            key = f"{provider}/{name}"
            if key in model_references:
                return model_references[key]
        
        if model_references:
            for key, ref in model_references.items():
                if isinstance(ref, dict):
                    return ref
        
        return None
    
    @staticmethod
    def _get_model_id(config: Dict[str, Any]) -> Optional[str]:
        """
        获取模型标识
        
        Args:
            config: agent 配置
            
        Returns:
            模型标识或 None
        """
        # 尝试从 model_id 字段获取
        model_id = config.get("model_id")
        if model_id:
            return str(model_id)
        
        # 从 model 字段构建标识
        model = config.get("model", {})
        if model:
            provider = model.get("model_provider", model.get("provider", ""))
            name = model.get("model_name", model.get("name", ""))
            if provider and name:
                return f"{provider}/{name}"
        
        return None
    
    @staticmethod
    def _apply_model_reference(
        config: Dict[str, Any],
        model_ref: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        应用模型引用
        
        Args:
            config: agent 配置
            model_ref: 模型引用字典
            
        Returns:
            处理后的配置
        """
        config = copy.deepcopy(config)
        
        if "model" not in config:
            config["model"] = {}
        
        model_config = config["model"]
        
        provider = model_ref.get("provider", model_ref.get("model_provider", ""))
        name = model_ref.get("model_type", model_ref.get("name", model_ref.get("model_name", "")))
        
        model_config["model_provider"] = provider
        model_config["model_name"] = name
        
        if "model_info" not in model_config:
            model_config["model_info"] = {}
        
        model_info = model_config["model_info"]
        
        if model_ref.get("base_url"):
            model_info["base_url"] = model_ref["base_url"]
        
        if model_ref.get("api_key"):
            model_info["api_key"] = model_ref["api_key"]
        
        if model_ref.get("timeout"):
            model_info["timeout"] = model_ref["timeout"]
        
        if model_ref.get("parameters"):
            for key, value in model_ref["parameters"].items():
                model_info[key] = value
        
        return config
    
    @staticmethod
    def _apply_overrides(
        config: Dict[str, Any],
        override: ModelOverride
    ) -> Dict[str, Any]:
        """
        应用运行时覆盖
        
        Args:
            config: agent 配置
            override: 覆盖配置
            
        Returns:
            处理后的配置
        """
        config = copy.deepcopy(config)
        
        if "model" not in config:
            config["model"] = {}
        
        model_config = config["model"]
        
        if "model_info" not in model_config:
            model_config["model_info"] = {}
        
        model_info = model_config["model_info"]
        
        if override.provider:
            model_config["model_provider"] = override.provider
        
        if override.model_type:
            model_config["model_type"] = override.model_type
        
        if override.name:
            model_config["model_name"] = override.name
        
        if override.api_key:
            model_info["api_key"] = override.api_key
            logger.info("API key injected successfully")
        
        if override.base_url:
            model_info["base_url"] = override.base_url
        
        if override.timeout:
            model_info["timeout"] = override.timeout
        
        if override.temperature is not None:
            model_info["temperature"] = override.temperature
        
        if override.max_tokens is not None:
            model_info["max_tokens"] = override.max_tokens
        
        if override.top_p is not None:
            model_info["top_p"] = override.top_p
        
        if override.parameters:
            for key, value in override.parameters.items():
                model_info[key] = value
        
        return config
    
    @staticmethod
    def _get_model_name(config: Dict[str, Any]) -> Optional[str]:
        """
        获取模型名称
        
        Args:
            config: agent 配置
            
        Returns:
            模型名称或 None
        """
        model = config.get("model", {})
        if model:
            return model.get("model_type") or model.get("model_name") or model.get("name")
        return None
    
    @staticmethod
    def _apply_env_config(
        config: Dict[str, Any],
        env_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        应用环境变量配置
        
        Args:
            config: agent 配置
            env_config: 环境变量配置
            
        Returns:
            处理后的配置
        """
        config = copy.deepcopy(config)
        
        if "model" not in config:
            config["model"] = {}
        
        model_config = config["model"]
        
        if "model_info" not in model_config:
            model_config["model_info"] = {}
        
        model_info = model_config["model_info"]
        
        if env_config.get("api_key") and not model_info.get("api_key"):
            model_info["api_key"] = env_config["api_key"]
            logger.info("API key injected from environment")
        
        if env_config.get("api_base") and not model_info.get("base_url"):
            model_info["base_url"] = env_config["api_base"]
        
        if env_config.get("provider") and not model_config.get("model_provider"):
            model_config["model_provider"] = env_config["provider"]
        
        if env_config.get("timeout") and not model_info.get("timeout"):
            model_info["timeout"] = env_config["timeout"]
        
        return config
    
    @staticmethod
    def validate_model_config(
        config: Dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        验证模型配置
        
        Args:
            config: agent 配置
            
        Returns:
            (是否有效，错误信息列表)
        """
        errors = []
        
        if "model" not in config:
            errors.append("Missing 'model' configuration")
            return False, errors
        
        model = config["model"]
        
        # 检查必要的字段
        if not model.get("model_provider") and not model.get("provider"):
            errors.append("Missing 'model_provider' or 'provider' in model config")
        
        if not model.get("model_name") and not model.get("name"):
            errors.append("Missing 'model_name' or 'name' in model config")
        
        # 检查 API Key（如果模型需要的话）
        model_info = model.get("model_info", {})
        if not model_info.get("api_key"):
            # 某些模型可能不需要 API Key（如本地模型）
            logger.warning("API key not found in model configuration")
        
        return len(errors) == 0, errors
