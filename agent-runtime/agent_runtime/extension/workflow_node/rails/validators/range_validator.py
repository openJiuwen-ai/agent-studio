# agent_runtime/extension/workflow_node/rails/validators/range_validator.py
"""
数值范围校验器 - number_range_validate

校验数值类型字段是否在指定范围内
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from agent_runtime.extension.workflow_node.rails.base import (
    ActionConfig,
    ValidateAction,
)


class NumberRangeValidateAction(ValidateAction):
    """数值范围校验 Action

    配置示例:
    ```json
    {
        "action": "number_range_validate",
        "action_extra_args": {
            "age": [0, 150],
            "price": [0, 1000000]
        }
    }
    ```
    """

    def validate_field(self, field_name: str, value: Any) -> Tuple[bool, Any]:
        """校验数值是否在指定范围内"""
        range_spec = self.extra_args.get(field_name)

        if range_spec is None:
            return True, value

        if not isinstance(range_spec, (list, tuple)) or len(range_spec) != 2:
            return True, value

        min_val, max_val = range_spec

        # 尝试转换为数值
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, None

        # 检查范围
        if min_val <= num_value <= max_val:
            # 如果原值是整数且范围也是整数，返回整数
            if (
                isinstance(value, int)
                and isinstance(min_val, int)
                and isinstance(max_val, int)
            ):
                return True, int(num_value)
            return True, num_value
        else:
            return False, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行范围校验"""
        args = context.get("arguments", {})
        # 以原始参数为基底：只覆盖配置了校验的字段，未配置校验的字段原样保留，
        # 避免部分字段勾选校验时其余字段被丢弃导致误触发重复追问
        
        validated_args = dict(args)

        for field_name, range_spec in self.extra_args.items():
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


async def number_range_validate(
    context: Dict[str, Any] = None, config: ActionConfig = None
) -> Dict[str, Any]:
    """数值范围校验 action 函数"""
    if config is None and context is not None:
        component_config = context.get("component_config", {})
        rails_config = component_config.get("railsConfig", {})
        actions_config = rails_config.get("actions_config", [])
        for ac in actions_config:
            if ac.get("action") == "number_range_validate":
                config = ActionConfig(ac.get("action_extra_args", {}))
                break

    if config is None:
        return {"arguments": context.get("arguments", {})}

    action = NumberRangeValidateAction(config)
    return await action.async_execute(context or {})
