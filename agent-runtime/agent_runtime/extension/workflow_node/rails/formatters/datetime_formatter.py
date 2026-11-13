# agent_runtime/extension/workflow_node/rails/formatters/datetime_formatter.py
"""
日期时间格式校验器 - date_time_format

校验并转换日期时间字符串为指定格式
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple

from agent_runtime.extension.workflow_node.rails.base import (
    ActionConfig,
    ValidateAction,
)

# 常用日期时间格式列表
TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%Y年%m月%d日 %H:%M:%S",
    "%Y年%m月%d日",
    "%Y年%m月%d日 %H点%M分%S秒",
    "%Y年%m月%d日 %H点%M分",
    "%Y年%m月%d日 %H点",
    "%H:%M:%S",
    "%H:%M",
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d",
    "%Y%m%d",
]


class DateTimeFormatValidateAction(ValidateAction):
    """日期时间格式校验 Action

    校验字段值是否符合指定的时间格式，不符合则返回 None（触发追问）

    支持智能解析：
    - 直接解析：用户输入符合目标格式
    - dateutil 解析：支持各种自然语言日期格式
    - 格式列表解析：尝试预定义的常见格式

    配置示例:
    ```json
    {
        "action": "date_time_format",
        "action_extra_args": {
            "time": "%Y-%m-%d %H:%M:%S",
            "date": "%Y-%m-%d"
        }
    }
    ```
    """

    def validate_field(self, field_name: str, value: Any) -> Tuple[bool, Any]:
        """校验字段值是否符合指定的时间格式"""
        target_format = self.extra_args.get(field_name)

        if target_format is None:
            return True, value

        if not isinstance(value, str):
            return False, None

        value = value.strip()
        if not value:
            return False, None

        # 首先尝试用目标格式直接解析
        if self._try_parse_with_format(value, target_format):
            return True, value

        # 尝试 dateutil.parser 解析（支持各种自然语言日期格式）
        parsed_datetime = self._parse_with_dateutil(value)
        if parsed_datetime is not None:
            try:
                formatted_value = parsed_datetime.strftime(target_format)
                return True, formatted_value
            except ValueError:
                pass

        # 尝试用格式列表解析
        for fmt in TIME_FORMATS:
            try:
                parsed_datetime = datetime.strptime(value, fmt)
                try:
                    formatted_value = parsed_datetime.strftime(target_format)
                    return True, formatted_value
                except ValueError:
                    pass
                break
            except ValueError:
                continue

        # 无法解析，校验失败
        return False, None

    def _try_parse_with_format(self, value: str, target_format: str) -> bool:
        """尝试用目标格式解析"""
        try:
            datetime.strptime(value, target_format)
            return True
        except ValueError:
            return False

    def _parse_with_dateutil(self, value: str):
        """使用 dateutil.parser 解析日期"""
        try:
            from dateutil import parser

            return parser.parse(value)
        except Exception:
            return None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行日期时间格式校验"""
        args = context.get("arguments", {})
        # 以原始参数为基底：只覆盖配置了校验的字段，未配置校验的字段原样保留，
        # 避免部分字段勾选校验时其余字段被丢弃导致误触发重复追问
        validated_args = dict(args)

        for field_name, target_format in self.extra_args.items():
            value = args.get(field_name)
            if value is None:
                validated_args[field_name] = None
                continue

            is_valid, validated_value = self.validate_field(field_name, value)
            if is_valid:
                validated_args[field_name] = validated_value
            else:
                # 校验失败，置为 None（触发追问）
                validated_args[field_name] = None

        return {"arguments": validated_args}


async def date_time_format(
    context: Dict[str, Any] = None, config: ActionConfig = None
) -> Dict[str, Any]:
    """日期时间格式校验 action 函数"""
    if config is None and context is not None:
        component_config = context.get("component_config", {})
        rails_config = component_config.get("railsConfig", {})
        actions_config = rails_config.get("actions_config", [])
        for ac in actions_config:
            if ac.get("action") == "date_time_format":
                config = ActionConfig(ac.get("action_extra_args", {}))
                break

    if config is None:
        return {"arguments": context.get("arguments", {})}

    action = DateTimeFormatValidateAction(config)
    return await action.async_execute(context or {})
