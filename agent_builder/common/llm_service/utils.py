#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
"""
Message conversion utilities.

With the OpenAI-compatible adapter, messages are already plain dicts.
This module provides backward-compatible conversion for any code that
still passes message objects.
"""

from typing import Dict, Any


def convert_message_to_dict(message) -> Dict[str, Any]:
    """Convert a message to a dictionary.

    If the message is already a dict, return it as-is.
    If it has 'role' and 'content' attributes, extract them.

    Args:
        message: The message (dict or message-like object).

    Returns:
        The dictionary.
    """
    if isinstance(message, dict):
        return message

    # Handle message-like objects with role/content attributes
    role_str = "role"
    content_str = "content"

    role = getattr(message, "role", None)
    content = getattr(message, "content", "")

    if role:
        message_dict = {role_str: role, content_str: content}
    else:
        # Fallback: check type name
        type_name = type(message).__name__
        if "Human" in type_name or "User" in type_name:
            message_dict = {role_str: "user", content_str: content}
        elif "AI" in type_name or "Assistant" in type_name:
            message_dict = {role_str: "assistant", content_str: content}
        elif "System" in type_name:
            message_dict = {role_str: "system", content_str: content}
        elif "Tool" in type_name or "Function" in type_name:
            message_dict = {
                role_str: "function",
                content_str: content,
                "name": getattr(message, "name", ""),
            }
        else:
            raise ValueError(f"Got unknown message type: {type_name}")

    return message_dict
