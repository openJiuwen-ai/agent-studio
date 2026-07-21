# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
环境变量加载工具

根据 environment_id 从 Redis 加载环境变量配置，解析为工作流执行所需的格式。
"""

import json
from typing import Any, Dict, List, Optional

from openjiuwen.core.common.logging import workflow_logger

from agent_runtime.common.redis_manager import get_redis_client
from agent_runtime.utils.crypto_tool import decrypt


# Redis key: environment:{envId}:workspaceId:{wsId}
_ENV_VAR_KEY_TEMPLATE = "environment:%s:workspaceId:%s"

# 环境变量解析结果 key
_PLUGIN_URL_PARAMS_KEY = "plugin_url_params"
_SECRET_ENV_KEYS_KEY = "_secretEnvKeys"


async def load_environment_variables(
    environment_id: Optional[str],
    workspace_id: Optional[str],
) -> Dict[str, Any]:
    """从 Redis 加载环境变量。

    Args:
        environment_id: 环境 ID，为空时返回空 dict。
        workspace_id: 工作空间 ID。

    Returns:
        {"plugin_url_params": {name: value, ...}, "_secretEnvKeys": [...]}
    """
    if not environment_id:
        return {}

    workspace_id = workspace_id or ""
    redis_key = _ENV_VAR_KEY_TEMPLATE % (environment_id, workspace_id)

    try:
        redis_client = get_redis_client()
        raw = await redis_client.get(redis_key)
    except Exception as e:
        workflow_logger.error(
            "Failed to load environment variables from redis: key=%s, error=%s",
            redis_key, e,
        )
        return {}

    if raw is None:
        return {}

    raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    if not raw_str or not raw_str.strip():
        return {}

    return _parse_env_variables(raw_str)


def _parse_env_variables(raw_json: str) -> Dict[str, Any]:
    """解析环境变量 JSON 字符串。

    输入格式（EnvVariablesDto）：
    [{"name":"xxx","value":{"content":"yyy","type":"string","secret":false}}]

    输出格式：
    {"plugin_url_params": {name: value, ...}, "_secretEnvKeys": [...]}
    """
    try:
        items: List[dict] = json.loads(raw_json)
    except ValueError as e:
        workflow_logger.error("Failed to parse environment variables JSON: %s", e)
        return {}

    # Redis 中可能双重编码：外层 JSON string 包裹内层 JSON array
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except ValueError as e:
            workflow_logger.error("Failed to parse double-encoded environment variables JSON: %s", e)
            return {}

    if not isinstance(items, list):
        return {}

    var_map: Dict[str, Any] = {}
    secret_keys: List[str] = []

    for item in items:
        name = item.get("name")
        value_obj = item.get("value")
        if not name or value_obj is None or value_obj.get("content") is None:
            continue

        content = value_obj.get("content", "")
        is_secret = value_obj.get("secret", False)
        value_type = value_obj.get("type", "string")

        if is_secret and content:
            content = decrypt(content)
            secret_keys.append(name)

        if value_type == "number" and content:
            try:
                content = float(content)
                if content == int(content):
                    content = int(content)
            except (ValueError, TypeError):
                pass

        var_map[name] = content

    return {_PLUGIN_URL_PARAMS_KEY: var_map, _SECRET_ENV_KEYS_KEY: secret_keys}
