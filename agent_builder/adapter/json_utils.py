# coding=utf-8
"""
JSON utilities: local replacement for jiuwen.common.utils.utils.safe_json_loads_raise_exception.
"""

import json

from agent_builder.adapter.exception_bridge import JiuWenBaseException


def safe_json_loads_raise_exception(json_str: str) -> dict:
    """
    Safely parse a JSON string, raising JiuWenBaseException on failure.

    Args:
        json_str: JSON string to parse

    Returns:
        Parsed dict/list

    Raises:
        JiuWenBaseException: If JSON parsing fails
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        raise JiuWenBaseException(
            error_code=-1,
            message=f"Failed to parse JSON: {str(e)}",
        ) from e
