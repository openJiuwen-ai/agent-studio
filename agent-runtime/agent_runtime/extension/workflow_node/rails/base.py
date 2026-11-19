# agent_runtime/extension/workflow_node/rails/base.py
"""
Rails Action 基类和装饰器
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict


class ActionConfig:
    """Action 配置类，封装 action_extra_args"""

    def __init__(self, action_extra_args: Dict[str, Any] = None):
        self.action_extra_args = action_extra_args or {}

    def get_extra_arg(self, key: str, default: Any = None) -> Any:
        """获取指定字段的额外参数"""
        return self.action_extra_args.get(key, default)

    def get_field_extra_args(self, field_name: str) -> Any:
        """获取指定字段的额外参数"""
        return self.action_extra_args.get(field_name)


class RailsAction:
    """Rails Action 基类"""

    def __init__(self, config: ActionConfig = None):
        self.config = config or ActionConfig()
        self.extra_args = self.config.action_extra_args or {}

    async def async_execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行入口（子类可重写）"""
        raise NotImplementedError

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """同步执行入口（子类可重写）"""
        raise NotImplementedError


def action(name: str = None):
    """Action 装饰器，用于标记和注册 action 函数"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # 标记为 action
        sync_wrapper._is_action = True
        sync_wrapper._action_name = name or func.__name__
        async_wrapper._is_action = True
        async_wrapper._action_name = name or func.__name__

        return async_wrapper

    return decorator


class ValidateAction(RailsAction):
    """校验型 Action 基类"""

    def validate_field(self, field_name: str, value: Any) -> tuple[bool, Any]:
        """校验字段值

        Returns:
            tuple: (是否有效, 校验后的值)
        """
        raise NotImplementedError

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行校验"""
        args = context.get("arguments", {})
        # 以原始参数为基底：只覆盖配置了校验的字段，未配置校验的字段原样保留，
        # 避免部分字段勾选校验时其余字段被丢弃导致误触发重复追问
        validated_args = dict(args)

        for key in self.extra_args.keys():
            value = args.get(key)
            if value is None:
                validated_args[key] = None
                continue

            is_valid, validated_value = self.validate_field(key, value)
            if is_valid:
                validated_args[key] = validated_value
            else:
                # 校验失败，置为 None
                validated_args[key] = None

        return {"arguments": validated_args}

    async def async_execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行校验"""
        return self.execute(context)


class FormatAction(RailsAction):
    """格式化型 Action 基类"""

    def format_field(self, field_name: str, value: Any) -> Any:
        """格式化字段值"""
        raise NotImplementedError

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行格式化"""
        args = context.get("arguments", {})
        # 以原始参数为基底：只覆盖配置了格式化的字段，未配置的字段原样保留
        formatted_args = dict(args)

        for key in self.extra_args.keys():
            value = args.get(key)
            if value is None:
                formatted_args[key] = None
                continue

            formatted_args[key] = self.format_field(key, value)

        return {"arguments": formatted_args}

    async def async_execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行格式化"""
        return self.execute(context)
