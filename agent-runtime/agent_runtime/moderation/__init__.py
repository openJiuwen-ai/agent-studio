# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""内容审核模块 — AC 自动机引擎 + 流式审核状态机 + 配置解析"""

from agent_runtime.moderation.engine import ActionType, ModerationEngineDynamicAC
from agent_runtime.moderation.stream_state import StreamModeratorState
from agent_runtime.moderation.schema import normalize_content_review
from agent_runtime.moderation.stream_moderation import (
    apply_stream_moderation,
    block_event_generator,
    init_moderation_from_ir,
)

__all__ = [
    "ActionType",
    "ModerationEngineDynamicAC",
    "StreamModeratorState",
    "normalize_content_review",
    "apply_stream_moderation",
    "block_event_generator",
    "init_moderation_from_ir",
]
