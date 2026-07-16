# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""useful tools."""

import os
import re
from typing import Optional

CODE_FIELD = "code"
MESSAGE_FIELD = "message"


def convert_string(content):
    """定义转换规则"""
    conversion_dict = {"[unused11]": "", "[unused12]": ""}

    # 遍历转换规则，替换字符串
    for old, new in conversion_dict.items():
        content = content.replace(old, new)

    return content


def sanitize_input(input_data):
    """移除 \r 和 \n 防止crlf注入"""
    if isinstance(input_data, str):
        return re.sub(r"[\r\n]", "***", input_data)
    return input_data


def sanitize_ip(ip: Optional[str]) -> str:
    """对 IP 地址进行脱敏：保留前 3 位，其余替换为 *"""
    if not ip:
        return "unknown"
    parts = ip.split(".")
    if len(parts) != 4:
        return "invalid_ip"
    return f"{parts[0]}.{parts[1]}.{parts[2]}.***"


def sanitize_session_id(sid: Optional[str]) -> str:
    """对会话 ID 进行脱敏：保留前 4 位和后 4 位，中间用 * 替代"""
    if not sid or len(sid) <= 8:
        return "****"
    return f"{sid[:4]}***{sid[-4:]}"


def is_valid_path(user_path, allowed_base_dir):
    """
    :param user_path: 用户输入的路径（可能为非可信路径）
    :param allowed_base_dir: 允许的根目录（路径必须在此目录下）
    :return: 路径是否合法
    :raises ValueError: 如果路径不合法或不在允许的根目录下
    """
    if not allowed_base_dir:
        raise ValueError("root path shouldn't be empty")

    try:
        allowed_realpath = os.path.realpath(allowed_base_dir)
        user_realpath = os.path.realpath(user_path)
    except (OSError, IOError) as e:
        raise ValueError("Invalid path or inaccessible") from e
    try:
        common_path = os.path.commonpath([allowed_realpath, user_realpath])
    except ValueError:
        return False
    return common_path == allowed_realpath
