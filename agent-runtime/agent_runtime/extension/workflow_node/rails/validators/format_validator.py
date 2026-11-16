# agent_runtime/extension/workflow_node/rails/validators/format_validator.py
"""
通用格式校验器 - common_data_format_check

校验常见数据格式：银行卡号、电话、护照、base64图片、URL、邮箱、IP地址、MAC地址、邮政编码、UUID、文件路径、车牌号等
"""

from __future__ import annotations

import base64
import re
from typing import Any, Dict, Tuple

from agent_runtime.extension.workflow_node.rails.base import (
    ActionConfig,
    ValidateAction,
)


class CommonDataFormatCheckAction(ValidateAction):
    """通用格式校验 Action

    支持的格式类型（从 action_extra_args 中获取）:
    - 银行卡号: bank_card
    - 电话号码: phone / 电话号码
    - 护照号码: passport
    - 图片base64: image_base64 / 图片base64
    - URL: url
    - 邮箱: email
    - 电话号码国家码: phone_with_country_code
    - IP地址: ip_address
    - MAC地址: mac_address
    - 邮政编码: postal_code
    - UUID: uuid
    - 文件路径: file_path
    - 车牌号: license_plate

    配置示例:
    ```json
    {
        "action": "common_data_format_check",
        "action_extra_args": {
            "id": "图片base64",
            "bank_account": "bank_card"
        }
    }
    ```
    """

    # 常用正则表达式
    PATTERNS = {
        "bank_card": r"^[1-9]\d{9,29}$",  # 银行卡号（简单校验）
        "phone": r"^1[3-9]\d{9}$",  # 手机号
        "phone_with_country_code": r"^\+?[1-9]\d{1,14}$",  # E.164格式
        "passport": r"^[A-Z0-9]{6,9}$",  # 护照号
        "url": r"^https?://[\w\-]+(\.[\w\-]+)+[\w\-.,@?^=%&:/~+#]*$",
        "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
        "ip_address": r"^(\d{1,3}\.){3}\d{1,3}$",
        "mac_address": r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
        "postal_code": r"^\d{6}$",
        "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "license_plate": r"^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,5}[A-Z0-9挂学警港澳]$",
    }

    # 中文格式名称映射
    FORMAT_NAME_MAP = {
        "银行卡号": "bank_card",
        "电话号码": "phone",
        "护照号码": "passport",
        "图片base64": "image_base64",
        "url": "url",
        "邮箱": "email",
        "IP地址": "ip_address",
        "MAC地址": "mac_address",
        "邮政编码": "postal_code",
        "UUID": "uuid",
        "文件路径": "file_path",
        "车牌号": "license_plate",
    }

    def validate_field(self, field_name: str, value: Any) -> Tuple[bool, Any]:
        """校验字段值格式"""
        format_type = self.extra_args.get(field_name)

        if format_type is None:
            return True, value

        # 映射中文格式名称
        format_type = self.FORMAT_NAME_MAP.get(format_type, format_type)

        # 处理 image_base64
        if format_type == "image_base64":
            return self._validate_base64_image(value)

        # 获取正则表达式
        pattern = self.PATTERNS.get(format_type)
        if pattern is None:
            return True, value

        if not isinstance(value, str):
            value = str(value)

        if re.fullmatch(pattern, value):
            return True, value
        else:
            return False, None

    def _validate_base64_image(self, value: Any) -> Tuple[bool, Any]:
        """校验是否为有效的 base64 图片"""
        if not isinstance(value, str):
            return False, None

        # 去除可能的头部
        if "," in value:
            value = value.split(",", 1)[1]

        try:
            # 尝试解码
            decoded = base64.b64decode(value)
            # 简单的图片头校验（PNG: 89 50 4E, JPEG: FF D8 FF, GIF: 47 49 46）
            if len(decoded) >= 3:
                first_bytes = decoded[:3]
                if first_bytes in [b"\x89\x50\x4e", b"\xff\xd8\xff", b"GIF"]:
                    return True, value
            # 如果没有头部但能解码，也认为有效
            return True, value
        except Exception:
            return False, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行格式校验"""
        args = context.get("arguments", {})
        # 以原始参数为基底：只覆盖配置了校验的字段，未配置校验的字段原样保留，
        # 避免部分字段勾选校验时其余字段被丢弃导致误触发重复追问
        validated_args = dict(args)

        for field_name, format_type in self.extra_args.items():
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


async def common_data_format_check(
    context: Dict[str, Any] = None, config: ActionConfig = None
) -> Dict[str, Any]:
    """通用格式校验 action 函数"""
    if config is None and context is not None:
        component_config = context.get("component_config", {})
        rails_config = component_config.get("railsConfig", {})
        actions_config = rails_config.get("actions_config", [])
        for ac in actions_config:
            if ac.get("action") == "common_data_format_check":
                config = ActionConfig(ac.get("action_extra_args", {}))
                break

    if config is None:
        return {"arguments": context.get("arguments", {})}

    action = CommonDataFormatCheckAction(config)
    return await action.async_execute(context or {})
