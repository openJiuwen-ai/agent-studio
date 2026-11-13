# agent_runtime/extension/workflow_node/rails/validators/length_validator.py
"""
长度限制校验器 - length_limit_validate

校验字符串长度是否超过限制
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_runtime.extension.workflow_node.rails.base import (
    ActionConfig,
    ValidateAction,
)


class LengthLimitValidateAction(ValidateAction):
    """长度限制校验 Action

    配置示例:
    ```json
    {
        "action": "length_limit_validate",
        "action_extra_args": {
            "name": 100,
            "description": 500
        }
    }
    ```
    """

    def validate_field(self, field_name: str, value: Any) -> Tuple[bool, Any]:
        """校验字段值长度是否超过限制"""
        max_length = self.extra_args.get(field_name)

        if max_length is None:
            return True, value

        try:
            max_length = int(max_length)
        except (ValueError, TypeError):
            return True, value

        if isinstance(value, str):
            if len(value) <= max_length:
                return True, value
            else:
                # 截断到最大长度
                return False, None

        # 非字符串类型转为字符串后校验
        str_value = str(value)
        if len(str_value) <= max_length:
            return True, str_value
        else:
            return False, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行长度校验"""
        args = context.get("arguments", {})
        # 以原始参数为基底：只覆盖配置了校验的字段，未配置校验的字段原样保留，
        # 避免部分字段勾选校验时其余字段被丢弃导致误触发重复追问
        validated_args = dict(args)

        for field_name, max_length in self.extra_args.items():
            value = args.get(field_name)
            if value is None:
                validated_args[field_name] = None
                continue

            is_valid, validated_value = self.validate_field(field_name, value)
            if is_valid:
                validated_args[field_name] = validated_value
            else:
                validated_args[field_name] = None

        return {"arguments": validated_args}


async def length_limit_validate(
    context: Dict[str, Any] = None, config: ActionConfig = None
) -> Dict[str, Any]:
    """长度限制校验 action 函数"""
    if config is None and context is not None:
        component_config = context.get("component_config", {})
        rails_config = component_config.get("railsConfig", {})
        actions_config = rails_config.get("actions_config", [])
        for ac in actions_config:
            if ac.get("action") == "length_limit_validate":
                config = ActionConfig(ac.get("action_extra_args", {}))
                break

    if config is None:
        return {"arguments": context.get("arguments", {})}

    action = LengthLimitValidateAction(config)
    return await action.async_execute(context or {})
