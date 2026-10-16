# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""环境变量加载工具（共享层）。

根据 ``environment_id`` 从 Redis 加载环境变量配置，解析为工作流执行 / 模型调用所需的格式。

下沉至 common_utils 使 agent_runtime 与 agent_builder 共用同一实现，避免两份加载逻辑漂移。
agent_runtime 历史上在 ``agent_runtime.common.env_variables_loader`` 维护此逻辑，现以本模块
为单一来源，原模块 re-export 保持向后兼容。

输出结构：
    {"plugin_url_params": {name: value, ...}, "_secretEnvKeys": [...]}

``plugin_url_params`` 供 openjiuwen 的 ``get_by_schema`` 解析 IR 模板字段里的
``${_env.plugin_url_params.VAR}``，以及 ``model_service.env_resolver`` 解析跨环境迁移模型
apiUrl 中的同名占位符。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from common_utils.crypto_tool import decrypt
from common_utils.redis_manager import get_redis_client

_logger = logging.getLogger(__name__)

# Redis key: environment:{envId}:workspaceId:{wsId}
_ENV_VAR_KEY_TEMPLATE = "environment:%s:workspaceId:%s"

# Redis key: project:{projectId}:default_environment（manager 环境管理写入，runtime 直连时读取）
_PROJECT_DEFAULT_ENV_KEY_TEMPLATE = "project:%s:default_environment"

# 环境变量解析结果 key
_PLUGIN_URL_PARAMS_KEY = "plugin_url_params"
_SECRET_ENV_KEYS_KEY = "_secretEnvKeys"


async def load_default_environment_id(project_id: Optional[str]) -> Optional[str]:
    """从 Redis 读取项目默认环境 id（manager 环境管理侧维护）。

    Args:
        project_id: 项目 ID，为空时返回 None。

    Returns:
        默认环境 id；project_id 为空 / Redis 不可达 / key 不存在时返回 None
        （兼容老数据：历史项目从未写入该 key，返回 None 由调用方降级）。
    """
    if not project_id:
        return None

    redis_key = _PROJECT_DEFAULT_ENV_KEY_TEMPLATE % project_id
    try:
        redis_client = get_redis_client()
        raw = await redis_client.get(redis_key)
    except Exception as e:
        _logger.error(
            "Failed to load default environment id from redis: key=%s, error=%s",
            redis_key, e,
        )
        return None

    if raw is None:
        return None

    raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    if not raw_str or not raw_str.strip():
        return None
    # Java Redisson 默认 codec 对 String 做 JSON 编码（存成 "9abd-..." 带引号），
    # 用 json.loads 还原；已是纯字符串（手动写入/其他写入方）则原样返回
    try:
        return json.loads(raw_str)
    except (ValueError, TypeError):
        return raw_str.strip()


async def load_environment_variables(
    environment_id: Optional[str],
    workspace_id: Optional[str],
) -> Dict[str, Any]:
    """从 Redis 加载环境变量。

    Args:
        environment_id: 环境 ID，为空时返回空 dict。
        workspace_id: 工作空间 ID。

    Returns:
        ``{"plugin_url_params": {name: value, ...}, "_secretEnvKeys": [...]}``；
        environment_id 为空 / Redis 不可达 / 数据缺失时返回空 dict（降级，不抛异常）。
    """
    if not environment_id:
        return {}

    workspace_id = workspace_id or ""
    redis_key = _ENV_VAR_KEY_TEMPLATE % (environment_id, workspace_id)

    try:
        redis_client = get_redis_client()
        raw = await redis_client.get(redis_key)
    except Exception as e:
        _logger.error(
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
        _logger.error("Failed to parse environment variables JSON: %s", e)
        return {}

    # Redis 中可能双重编码：外层 JSON string 包裹内层 JSON array
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except ValueError as e:
            _logger.error("Failed to parse double-encoded environment variables JSON: %s", e)
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
