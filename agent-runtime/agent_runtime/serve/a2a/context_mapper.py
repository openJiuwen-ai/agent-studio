# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Map A2A contextId to low-code conversation_id using Redis."""

import uuid

from redis_spi import accessor
from redis_spi.types import Duration

from agent_runtime.serve.apis.publish_version_cache import PublishVersionCache

CONTEXT_KEY_PREFIX = "a2a:context:"
CONTEXT_TTL_SECONDS = 86400  # 24h, aligned with conversation TTL

# appType values that indicate a stateless workflow
_WORKFLOW_APP_TYPES = frozenset({"WORKFLOW", "workflow"})


async def resolve_conversation_id(context_id: str, agent_id: str) -> str:
    """Resolve contextId to conversation_id. Create new mapping if not exists.

    For WORKFLOW type: always return new UUID (stateless — no conversation reuse).
    For AGENT/MULTI_AGENTS: reuse mapped conversation_id across calls with same contextId.
    """
    metadata = await PublishVersionCache.get_publish_metadata(agent_id)
    app_type = (metadata.app_type if metadata else "") or ""

    if app_type in _WORKFLOW_APP_TYPES:
        return str(uuid.uuid4())

    if not accessor.is_initialized():
        return str(uuid.uuid4())

    redis = accessor.get_redis()
    key = f"{CONTEXT_KEY_PREFIX}{context_id}"
    existing = await redis.get(key)
    if existing:
        return existing.decode() if isinstance(existing, bytes) else existing
    new_conv_id = str(uuid.uuid4())
    await redis.set(key, new_conv_id, duration=Duration.seconds(CONTEXT_TTL_SECONDS))
    return new_conv_id
