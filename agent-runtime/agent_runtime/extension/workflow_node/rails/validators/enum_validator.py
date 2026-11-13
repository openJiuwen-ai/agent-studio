# agent_runtime/extension/workflow_node/rails/validators/enum_validator.py
"""
枚举值校验器 - enum_legality_validate

校验字段值是否在允许的枚举值列表中
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_runtime.extension.workflow_node.rails.base import (
    ActionConfig,
    ValidateAction,
)


class EnumLegalityValidateAction(ValidateAction):
    """枚举值校验 Action

    配置示例:
    ```json
    {
        "action": "enum_legality_validate",
        "action_extra_args": {
            "place": ["上海", "南京", "北京"],
            "status": ["active", "inactive"]
        }
    }
    ```
    """

    def validate_field(self, field_name: str, value: Any) -> Tuple[bool, Any]:
        """校验字段值是否在枚举列表中"""
        allowed_values = self.extra_args.get(field_name, [])

        if not isinstance(allowed_values, list):
            return True, value

        # 精确匹配
        if value in allowed_values:
            return True, value

        return False, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行枚举校验"""
        args = context.get("arguments", {})
        # 以原始参数为基底：只覆盖配置了校验的字段，未配置校验的字段原样保留，
        # 避免部分字段勾选校验时其余字段被丢弃导致误触发重复追问
        validated_args = dict(args)
        user_input = context.get("user_input", "")

        for field_name, allowed_values in self.extra_args.items():
            value = args.get(field_name)
            if value is None:
                validated_args[field_name] = None
                continue

            # 1. 首先检查模型提取的值是否精确匹配枚举值
            if value not in allowed_values:
                validated_args[field_name] = None
                continue

            # 2. 如果匹配了枚举值，再检查是否包含在用户原始输入中
            if isinstance(user_input, str) and isinstance(value, str):
                if value not in user_input:
                    validated_args[field_name] = None
                    continue

            validated_args[field_name] = value

        return {"arguments": validated_args}


# 装饰器风格的 action 函数（备用）
async def enum_legality_validate(
    context: Dict[str, Any] = None, config: ActionConfig = None
) -> Dict[str, Any]:
    """枚举校验 action 函数"""
    if config is None and context is not None:
        # 从 context 中推断 config
        component_config = context.get("component_config", {})
        rails_config = component_config.get("railsConfig", {})
        actions_config = rails_config.get("actions_config", [])
        for ac in actions_config:
            if ac.get("action") == "enum_legality_validate":
                config = ActionConfig(ac.get("action_extra_args", {}))
                break

    if config is None:
        return {"arguments": context.get("arguments", {})}

    action = EnumLegalityValidateAction(config)
    return await action.async_execute(context or {})
