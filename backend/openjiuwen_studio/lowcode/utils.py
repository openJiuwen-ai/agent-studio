#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
低代码模块工具函数
"""

from typing import Any, Dict
import hashlib
from datetime import datetime, timezone


def generate_agent_id(agent_name: str) -> str:
    """
    生成Agent ID
    
    Args:
        agent_name: Agent名称
        
    Returns:
        Agent ID
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    hash_input = f"{agent_name}_{timestamp}"
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"agent_{hash_value}"


def merge_configs(
    base_config: Dict[str, Any],
    override_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    合并配置
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
        
    Returns:
        合并后的配置
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    清理配置（移除敏感信息）
    
    Args:
        config: 原始配置
        
    Returns:
        清理后的配置
    """
    sensitive_keys = ['api_key', 'api_secret', 'password', 'token', 'secret']
    
    def _sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if any(sk in k.lower() for sk in sensitive_keys):
                    result[k] = '***'
                else:
                    result[k] = _sanitize(v)
            return result
        elif isinstance(obj, list):
            return [_sanitize(item) for item in obj]
        else:
            return obj
    
    return _sanitize(config)


def format_error_response(error: Exception) -> Dict[str, Any]:
    """
    格式化错误响应
    
    Args:
        error: 异常对象
        
    Returns:
        错误响应字典
    """
    return {
        "error": True,
        "error_type": type(error).__name__,
        "message": str(error),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def parse_model_reference(model_ref_str: str) -> Dict[str, str]:
    """
    解析模型引用字符串
    
    Args:
        model_ref_str: 模型引用字符串（如 "OpenAI/gpt-4"）
        
    Returns:
        解析结果字典
    """
    parts = model_ref_str.split('/')
    if len(parts) >= 2:
        return {
            'provider': parts[0],
            'name': parts[1]
        }
    return {'provider': '', 'name': model_ref_str}


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: list[str]
) -> list[str]:
    """
    验证必需字段
    
    Args:
        data: 数据字典
        required_fields: 必需字段列表
        
    Returns:
        缺失字段列表
    """
    missing = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing.append(field)
    return missing
